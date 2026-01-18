"""
Integration Routes
API endpoints for managing integrations (Odoo, Salesforce, etc.)
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid

from models.base import (
    IntegrationType, EntityType, IntegrationConfig,
    FieldMapping, IntegrationMapping, SyncJob, SyncStatus, UserRole
)
from services.auth.jwt_handler import get_current_user_from_token, require_role
from services.odoo.connector import OdooConnector
from services.ai_mapping.mapper import AIFieldMapper, get_canonical_schema
from services.data_lake.manager import DataLakeManager
from core.database import Database
from core.config import settings

router = APIRouter(prefix="/integrations", tags=["Integrations"])


# ===================== REQUEST/RESPONSE MODELS =====================

class OdooConfigRequest(BaseModel):
    url: str
    database: str
    username: str
    api_key: str
    enabled_entities: List[EntityType] = [EntityType.ACCOUNT, EntityType.OPPORTUNITY]


class O365ConfigRequest(BaseModel):
    client_id: str
    tenant_id: str
    client_secret: str


class IntegrationResponse(BaseModel):
    id: str
    integration_type: str
    enabled: bool
    last_sync: Optional[datetime] = None
    sync_status: str
    error_message: Optional[str] = None
    config_summary: Dict[str, Any] = {}
    connection: Optional[Dict[str, Any]] = None  # NEW: Connection details for Odoo


class TestConnectionResponse(BaseModel):
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class FieldMappingRequest(BaseModel):
    entity_type: EntityType
    mappings: List[FieldMapping]


class AutoMapRequest(BaseModel):
    entity_type: EntityType


class SyncRequest(BaseModel):
    entity_types: Optional[List[EntityType]] = None


# ===================== INTEGRATION CONFIG ROUTES =====================

@router.get("/", response_model=List[IntegrationResponse])
async def list_integrations(
    token_data: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.CEO]))
):
    """List all configured integrations"""
    db = Database.get_db()
    
    integrations = await db.integrations.find({}, {"_id": 0}).to_list(100)
    
    result = []
    for intg in integrations:
        # Don't expose sensitive config
        config_summary = {}
        if intg.get("config"):
            config = intg["config"]
            if "url" in config:
                config_summary["url"] = config["url"]
            if "database" in config:
                config_summary["database"] = config["database"]
        
        result.append(IntegrationResponse(
            id=intg.get("id", ""),
            integration_type=intg.get("integration_type", ""),
            enabled=intg.get("enabled", False),
            last_sync=intg.get("last_sync"),
            sync_status=intg.get("sync_status", "pending"),
            error_message=intg.get("error_message"),
            config_summary=config_summary
        ))
    
    return result


@router.get("/{integration_type}", response_model=IntegrationResponse)
async def get_integration(
    integration_type: IntegrationType,
    token_data: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.ADMIN]))
):
    """Get integration configuration"""
    db = Database.get_db()
    
    intg = await db.integrations.find_one(
        {"integration_type": integration_type.value},
        {"_id": 0}
    )
    
    if not intg:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    config_summary = {}
    connection_status = {}
    
    if intg.get("config"):
        config = intg["config"]
        if "url" in config:
            config_summary["url"] = config["url"]
        if "database" in config:
            config_summary["database"] = config["database"]
        
        # For Odoo, check if we have credentials to determine connection status
        if integration_type == IntegrationType.ODOO:
            has_credentials = all([
                config.get("url"),
                config.get("database"),
                config.get("username"),
                config.get("api_key")
            ])
            connection_status = {
                "is_connected": has_credentials and intg.get("sync_status") != "error",
                "url": config.get("url"),
                "database": config.get("database"),
                "username": config.get("username"),
                "api_key": "***" + config.get("api_key", "")[-4:] if config.get("api_key") else None,
                "odoo_version": "17+"  # Default, can be updated after test
            }
    
    # Build response with additional connection info for frontend compatibility
    response_data = {
        "id": intg.get("id", ""),
        "integration_type": intg.get("integration_type", ""),
        "enabled": intg.get("enabled", False),
        "last_sync": intg.get("last_sync"),
        "sync_status": intg.get("sync_status", "pending"),
        "error_message": intg.get("error_message"),
        "config_summary": config_summary,
        "connection": connection_status if connection_status else None
    }
    
    return response_data


# ===================== ODOO SPECIFIC ROUTES =====================

@router.post("/odoo/configure")
async def configure_odoo(
    config: OdooConfigRequest,
    token_data: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.ADMIN]))
):
    """Configure Odoo integration"""
    db = Database.get_db()
    
    now = datetime.now(timezone.utc)
    intg_id = str(uuid.uuid4())
    
    # Check if already exists
    existing = await db.integrations.find_one({"integration_type": "odoo"})
    
    intg_doc = {
        "id": existing["id"] if existing else intg_id,
        "integration_type": "odoo",
        "enabled": True,
        "config": {
            "url": config.url,
            "database": config.database,
            "username": config.username,
            "api_key": config.api_key,  # Should encrypt in production
            "enabled_entities": [e.value for e in config.enabled_entities]
        },
        "sync_status": "pending",
        "updated_at": now
    }
    
    if existing:
        await db.integrations.update_one(
            {"integration_type": "odoo"},
            {"$set": intg_doc}
        )
    else:
        intg_doc["created_at"] = now
        await db.integrations.insert_one(intg_doc)
    
    return {"message": "Odoo integration configured", "id": intg_doc["id"]}


@router.post("/odoo/test", response_model=TestConnectionResponse)
async def test_odoo_connection(
    config: OdooConfigRequest,
    token_data: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.ADMIN]))
):
    """Test Odoo connection"""
    try:
        async with OdooConnector(
            url=config.url,
            database=config.database,
            username=config.username,
            api_key=config.api_key
        ) as connector:
            result = await connector.test_connection()
            
            if result.get("connected"):
                return TestConnectionResponse(
                    success=True,
                    message=f"Connected to Odoo {result.get('server_version', 'unknown')}",
                    details=result
                )
            else:
                return TestConnectionResponse(
                    success=False,
                    message=f"Connection failed: {result.get('error', 'Unknown error')}",
                    details=result
                )
    except Exception as e:
        return TestConnectionResponse(
            success=False,
            message=f"Connection error: {str(e)}"
        )


@router.get("/odoo/fields/{model}")
async def get_odoo_fields(
    model: str,
    token_data: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.ADMIN]))
):
    """Get available fields from an Odoo model"""
    db = Database.get_db()
    
    # Get Odoo config
    intg = await db.integrations.find_one({"integration_type": "odoo"})
    if not intg or not intg.get("config"):
        raise HTTPException(status_code=400, detail="Odoo not configured")
    
    config = intg["config"]
    
    try:
        async with OdooConnector(
            url=config["url"],
            database=config["database"],
            username=config["username"],
            api_key=config["api_key"]
        ) as connector:
            fields = await connector.fields_get(model)
            return {"model": model, "fields": fields}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===================== MICROSOFT 365 ROUTES =====================

@router.post("/ms365/configure")
async def configure_ms365(
    config: O365ConfigRequest,
    token_data: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.ADMIN]))
):
    """Configure Microsoft 365 integration"""
    db = Database.get_db()
    
    now = datetime.now(timezone.utc)
    intg_id = str(uuid.uuid4())
    
    # Check if already exists
    existing = await db.integrations.find_one({"integration_type": "ms365"})
    
    intg_doc = {
        "id": existing["id"] if existing else intg_id,
        "integration_type": "ms365",
        "enabled": True,
        "config": {
            "client_id": config.client_id,
            "tenant_id": config.tenant_id,
            "client_secret": config.client_secret,  # Should encrypt in production
        },
        "sync_status": "pending",
        "updated_at": now
    }
    
    if existing:
        await db.integrations.update_one(
            {"integration_type": "ms365"},
            {"$set": intg_doc}
        )
    else:
        intg_doc["created_at"] = now
        await db.integrations.insert_one(intg_doc)
    
    return {"message": "Microsoft 365 integration configured", "id": intg_doc["id"]}


@router.post("/ms365/test", response_model=TestConnectionResponse)
async def test_ms365_connection(
    config: O365ConfigRequest,
    token_data: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.ADMIN]))
):
    """Test Microsoft 365 connection by validating credentials with Azure AD"""
    import aiohttp
    
    try:
        # Try to get an access token from Azure AD using client credentials
        token_url = f"https://login.microsoftonline.com/{config.tenant_id}/oauth2/v2.0/token"
        
        data = {
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=data) as response:
                result = await response.json()
                
                if response.status == 200 and "access_token" in result:
                    # Test the token by calling Graph API
                    headers = {"Authorization": f"Bearer {result['access_token']}"}
                    async with session.get(
                        "https://graph.microsoft.com/v1.0/organization",
                        headers=headers
                    ) as org_response:
                        if org_response.status == 200:
                            org_data = await org_response.json()
                            org_name = org_data.get("value", [{}])[0].get("displayName", "Unknown")
                            return TestConnectionResponse(
                                success=True,
                                message=f"Connected to Microsoft 365 - Organization: {org_name}",
                                details={
                                    "organization": org_name,
                                    "tenant_id": config.tenant_id
                                }
                            )
                        else:
                            return TestConnectionResponse(
                                success=True,
                                message="Connected to Azure AD (Graph API access may need admin consent)",
                                details={"tenant_id": config.tenant_id}
                            )
                else:
                    error_desc = result.get("error_description", result.get("error", "Unknown error"))
                    return TestConnectionResponse(
                        success=False,
                        message=f"Authentication failed: {error_desc}"
                    )
                    
    except Exception as e:
        return TestConnectionResponse(
            success=False,
            message=f"Connection error: {str(e)}"
        )


# ===================== ODOO DEPARTMENT & USER SYNC =====================

class DepartmentSyncResponse(BaseModel):
    synced: int
    created: int
    updated: int
    deactivated: int
    errors: List[str] = []

class UserSyncResponse(BaseModel):
    synced: int
    created: int
    updated: int
    deactivated: int
    errors: List[str] = []

@router.post("/odoo/sync-departments", response_model=DepartmentSyncResponse)
async def sync_departments_from_odoo(
    token_data: dict = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """
    Sync departments from Odoo hr.department.
    Departments are SOURCE OF TRUTH from Odoo - CRM departments are read-only.
    """
    from services.odoo.sync_pipeline import OdooSyncPipelineService
    
    db = Database.get_db()
    pipeline = OdooSyncPipelineService(db)
    
    try:
        result = await pipeline.sync_departments(user_id=token_data["id"])
        
        return DepartmentSyncResponse(
            synced=result.synced,
            created=result.created,
            updated=result.updated,
            deactivated=result.deactivated,
            errors=result.errors
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/odoo/sync-users", response_model=UserSyncResponse)
async def sync_users_from_odoo(
    token_data: dict = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """
    Sync users from Odoo hr.employee.
    Users are SOURCE OF TRUTH from Odoo - manual user creation is blocked.
    Users synced here are set to 'pending' approval status.
    """
    from services.odoo.sync_pipeline import OdooSyncPipelineService
    
    db = Database.get_db()
    pipeline = OdooSyncPipelineService(db)
    
    try:
        result = await pipeline.sync_users(user_id=token_data["id"])
        
        return UserSyncResponse(
            synced=result.synced,
            created=result.created,
            updated=result.updated,
            deactivated=result.deactivated,
            errors=result.errors
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class OdooFullSyncResponse(BaseModel):
    """Response for full Odoo sync"""
    success: bool
    message: str
    synced_entities: Dict[str, int] = {}
    errors: List[str] = []
    duration_seconds: float = 0


@router.post("/odoo/sync-all", response_model=OdooFullSyncResponse)
async def sync_all_from_odoo(
    background_tasks: BackgroundTasks,
    token_data: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.ADMIN]))
):
    """
    Trigger a full sync of all entities from Odoo.
    Syncs: Accounts (Partners), Opportunities (CRM Leads), Invoices, Users to data_lake_serving.
    """
    from services.odoo.sync_pipeline import OdooSyncPipelineService
    
    db = Database.get_db()
    pipeline = OdooSyncPipelineService(db)
    
    try:
        result = await pipeline.sync_data_lake(user_id=token_data["id"])
        
        return OdooFullSyncResponse(
            success=result["success"],
            message=result["message"],
            synced_entities=result["synced_entities"],
            errors=result["errors"],
            duration_seconds=result["duration_seconds"]
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/departments")
async def get_synced_departments(
    token_data: dict = Depends(get_current_user_from_token)
):
    """Get all departments (synced from Odoo)"""
    db = Database.get_db()
    departments = await db.departments.find({"active": True}, {"_id": 0}).to_list(100)
    return departments


# ===================== FIELD MAPPING ROUTES =====================

@router.get("/mappings/{integration_type}/{entity_type}")
async def get_field_mappings(
    integration_type: IntegrationType,
    entity_type: EntityType,
    token_data: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.ADMIN]))
):
    """Get field mappings for an integration"""
    db = Database.get_db()
    
    mapping = await db.field_mappings.find_one({
        "integration_type": integration_type.value,
        "entity_type": entity_type.value
    }, {"_id": 0})
    
    canonical_schema = get_canonical_schema(entity_type)
    
    return {
        "integration_type": integration_type.value,
        "entity_type": entity_type.value,
        "mappings": mapping.get("mappings", []) if mapping else [],
        "canonical_schema": canonical_schema
    }


@router.post("/mappings/{integration_type}")
async def save_field_mappings(
    integration_type: IntegrationType,
    request: FieldMappingRequest,
    token_data: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.ADMIN]))
):
    """Save field mappings for an integration"""
    db = Database.get_db()
    
    now = datetime.now(timezone.utc)
    mapping_id = str(uuid.uuid4())
    
    existing = await db.field_mappings.find_one({
        "integration_type": integration_type.value,
        "entity_type": request.entity_type.value
    })
    
    mapping_doc = {
        "id": existing["id"] if existing else mapping_id,
        "integration_type": integration_type.value,
        "entity_type": request.entity_type.value,
        "mappings": [m.model_dump() for m in request.mappings],
        "is_active": True,
        "updated_at": now,
        "updated_by": token_data["id"]
    }
    
    if existing:
        await db.field_mappings.update_one(
            {"id": existing["id"]},
            {"$set": mapping_doc}
        )
    else:
        mapping_doc["created_at"] = now
        mapping_doc["created_by"] = token_data["id"]
        await db.field_mappings.insert_one(mapping_doc)
    
    return {"message": "Mappings saved", "count": len(request.mappings)}


@router.post("/mappings/{integration_type}/auto-map")
async def auto_map_fields(
    integration_type: IntegrationType,
    request: AutoMapRequest,
    token_data: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.ADMIN]))
):
    """Use AI to automatically map fields"""
    db = Database.get_db()
    
    # Get integration config
    intg = await db.integrations.find_one({"integration_type": integration_type.value})
    if not intg or not intg.get("config"):
        raise HTTPException(status_code=400, detail=f"{integration_type.value} not configured")
    
    config = intg["config"]
    
    # Get source fields based on integration type
    source_fields = {}
    
    if integration_type == IntegrationType.ODOO:
        try:
            # Map entity type to Odoo model
            model_map = {
                EntityType.ACCOUNT: "res.partner",
                EntityType.OPPORTUNITY: "crm.lead",
                EntityType.CONTACT: "res.partner",
                EntityType.ORDER: "sale.order",
                EntityType.INVOICE: "account.move"
            }
            
            model = model_map.get(request.entity_type)
            if not model:
                raise HTTPException(status_code=400, detail=f"Unsupported entity type: {request.entity_type}")
            
            async with OdooConnector(
                url=config["url"],
                database=config["database"],
                username=config["username"],
                api_key=config["api_key"]
            ) as connector:
                source_fields = await connector.fields_get(model)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get Odoo fields: {e}")
    
    # Use AI mapper
    api_key = settings.EMERGENT_LLM_KEY or settings.OPENAI_API_KEY
    mapper = AIFieldMapper(api_key=api_key, model=settings.AI_MODEL)
    
    mappings = await mapper.auto_map_fields(
        source_fields=source_fields,
        entity_type=request.entity_type,
        integration_type=integration_type
    )
    
    return {
        "entity_type": request.entity_type.value,
        "suggested_mappings": [m.model_dump() for m in mappings],
        "source_field_count": len(source_fields),
        "mapped_count": len(mappings)
    }



@router.get("/odoo/data-lake-stats")
async def get_odoo_data_lake_stats(
    token_data: dict = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """Get Odoo-specific Data Lake stats for group settings."""
    db = Database.get_db()
    raw_collection = db[Database.RAW_ZONE]
    canonical_collection = db[Database.CANONICAL_ZONE]
    serving_collection = db[Database.SERVING_ZONE]

    raw_total = await raw_collection.count_documents({"source": "odoo"})
    canonical_total = await canonical_collection.count_documents({
        "source_refs": {"$elemMatch": {"source": "odoo"}}
    })
    serving_total = await serving_collection.count_documents({"source": "odoo"})

    entity_types = ["account", "opportunity", "activity", "invoice", "order", "user"]
    entity_counts = {}
    for entity_type in entity_types:
        entity_counts[entity_type] = await serving_collection.count_documents({
            "source": "odoo",
            "entity_type": entity_type
        })

    groups = [
        {"id": "crm", "name": "CRM Core", "entities": ["account", "opportunity", "activity"]},
        {"id": "finance", "name": "Finance", "entities": ["invoice", "order"]},
        {"id": "people", "name": "People", "entities": ["user"]},
    ]

    return {
        "raw_zone": {"total_records": raw_total},
        "canonical_zone": {"total_records": canonical_total},
        "serving_zone": {"total_records": serving_total},
        "entity_counts": entity_counts,
        "groups": groups
    }


# ===================== SYNC ROUTES =====================

@router.post("/sync/{integration_type}")
async def trigger_sync(
    integration_type: IntegrationType,
    background_tasks: BackgroundTasks,
    request: Optional[SyncRequest] = None,
    token_data: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.ADMIN]))
):
    """Trigger a sync job for an integration"""
    from services.sync.service import run_sync_job
    
    db = Database.get_db()
    
    # Get integration config
    intg = await db.integrations.find_one({"integration_type": integration_type.value})
    if not intg or not intg.get("enabled"):
        raise HTTPException(status_code=400, detail=f"{integration_type.value} not enabled")
    
    if not intg.get("config"):
        raise HTTPException(status_code=400, detail=f"{integration_type.value} not configured")
    
    # Validate config based on integration type
    config = intg["config"]
    if integration_type == IntegrationType.ODOO:
        if not config.get("url"):
            raise HTTPException(status_code=400, detail="Odoo URL not configured")
    elif integration_type == IntegrationType.MS365:
        if not config.get("client_id") or not config.get("tenant_id"):
            raise HTTPException(status_code=400, detail="Microsoft 365 credentials not configured")
    
    # Get entity types from request body or use defaults based on integration type
    if request and request.entity_types:
        entity_types = request.entity_types
    elif integration_type == IntegrationType.MS365:
        entity_types = [EntityType.EMAIL, EntityType.CALENDAR]
    else:
        entity_types = [EntityType.ACCOUNT, EntityType.OPPORTUNITY]
    
    # Create sync job
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    job = SyncJob(
        id=job_id,
        integration_type=integration_type,
        entity_types=entity_types,
        status=SyncStatus.PENDING,
        created_at=now,
        created_by=token_data["id"]
    )
    
    await db.sync_jobs.insert_one(job.model_dump())
    
    # Update integration status
    await db.integrations.update_one(
        {"integration_type": integration_type.value},
        {"$set": {"sync_status": "in_progress"}}
    )
    
    # Run sync in background
    background_tasks.add_task(run_sync_job, job_id)
    
    return {"message": "Sync job started", "job_id": job_id}


@router.get("/sync/status")
async def get_sync_status(
    token_data: dict = Depends(get_current_user_from_token)
):
    """Get status of recent sync jobs"""
    db = Database.get_db()
    
    jobs = await db.sync_jobs.find(
        {},
        {"_id": 0}
    ).sort("created_at", -1).limit(10).to_list(10)
    
    return {"jobs": jobs}


# ===================== BACKGROUND SYNC SERVICE =====================

# User-level rate limiting for sync requests
_user_sync_timestamps = {}

@router.post("/user-sync/refresh")
async def user_trigger_sync_refresh(
    token_data: dict = Depends(get_current_user_from_token)
):
    """
    User-accessible sync trigger with rate limiting.
    Any approved user can trigger a data refresh (max once per 30 seconds).
    """
    import time
    from services.sync.background_sync import sync_service
    
    user_id = token_data.get("id")
    current_time = time.time()
    
    # Check rate limit (30 seconds between syncs per user)
    last_sync = _user_sync_timestamps.get(user_id, 0)
    if current_time - last_sync < 30:
        remaining = int(30 - (current_time - last_sync))
        raise HTTPException(
            status_code=429, 
            detail=f"Please wait {remaining} seconds before syncing again."
        )
    
    # Update timestamp
    _user_sync_timestamps[user_id] = current_time
    
    # Trigger sync
    result = await sync_service.trigger_sync_now()
    result["triggered_by"] = token_data.get("email")
    result["rate_limit_remaining"] = 30
    
    return result


@router.get("/background-sync/status")
async def get_background_sync_status(
    token_data: dict = Depends(get_current_user_from_token)
):
    """
    Get status of the background sync service.
    Available to all authenticated users.
    """
    from services.sync.background_sync import sync_service
    return await sync_service.get_status()


@router.post("/background-sync/trigger")
async def trigger_background_sync(
    token_data: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.ADMIN]))
):
    """
    Manually trigger a background sync immediately.
    Admin-only endpoint.
    """
    from services.sync.background_sync import sync_service
    result = await sync_service.trigger_sync_now()
    return result


@router.post("/background-sync/start")
async def start_background_sync_service(
    interval_minutes: int = 5,
    token_data: dict = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """
    Start the background sync service.
    Super Admin only.
    """
    from services.sync.background_sync import sync_service
    await sync_service.start(interval_minutes)
    return {"message": f"Background sync started with {interval_minutes} minute interval"}


@router.post("/background-sync/stop")
async def stop_background_sync_service(
    token_data: dict = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """
    Stop the background sync service.
    Super Admin only.
    """
    from services.sync.background_sync import sync_service
    await sync_service.stop()
    return {"message": "Background sync stopped"}


@router.get("/background-sync/health")
async def get_background_sync_health(
    token_data: dict = Depends(get_current_user_from_token)
):
    """
    Get comprehensive health status of the background sync service.
    Includes metrics, failure counts, and health assessment.
    Available to all authenticated users.
    """
    from services.sync.background_sync import sync_service
    return await sync_service.get_sync_health()


@router.get("/sync/logs")
async def get_sync_logs(
    limit: int = 20,
    status: Optional[str] = None,
    token_data: dict = Depends(get_current_user_from_token)
):
    """
    Get recent sync logs for monitoring.
    Optional status filter: 'completed', 'failed', 'running'
    """
    db = Database.get_db()
    
    query = {}
    if status:
        query["status"] = status
    
    logs = await db.sync_logs.find(
        query,
        {"_id": 0}
    ).sort("started_at", -1).limit(limit).to_list(limit)
    
    # Convert datetime to ISO strings
    for log in logs:
        if log.get("started_at"):
            log["started_at"] = log["started_at"].isoformat()
        if log.get("completed_at"):
            log["completed_at"] = log["completed_at"].isoformat()
    
    return {"logs": logs, "count": len(logs)}


@router.get("/sync/{job_id}")
async def get_sync_job(
    job_id: str,
    token_data: dict = Depends(get_current_user_from_token)
):
    """Get details of a specific sync job"""
    db = Database.get_db()
    
    job = await db.sync_jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Sync job not found")
    
    return job

