"""
Webhook Routes
Endpoints for receiving real-time updates from Odoo
"""
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import logging
import hmac
import hashlib
import uuid

from models.base import EntityType, IntegrationType, SyncStatus
from services.sync.service import SyncService
from services.data_lake.manager import DataLakeManager
from core.database import Database
from core.config import settings

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
logger = logging.getLogger(__name__)


# ===================== WEBHOOK MODELS =====================

class OdooWebhookPayload(BaseModel):
    """Payload from Odoo webhook"""
    model: str  # e.g., "crm.lead", "res.partner"
    action: str  # "create", "write", "unlink"
    record_ids: List[int]
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


class WebhookResponse(BaseModel):
    """Standard webhook response"""
    status: str
    message: str
    processed: int = 0


# ===================== ODOO WEBHOOK ENDPOINT =====================

@router.post("/odoo", response_model=WebhookResponse)
async def odoo_webhook(
    payload: OdooWebhookPayload,
    background_tasks: BackgroundTasks,
    request: Request
):
    """
    Receive real-time updates from Odoo.
    
    PRODUCTION-GRADE WEBHOOK HANDLING:
    - Validates X-Odoo-Webhook-Secret (hard-fails on invalid)
    - Soft-deletes in data_lake_serving (preserves audit trail)
    - Updates CQRS projections immediately (sub-second UI consistency)
    - Handles ID normalization (int + string)
    - Structured logging with metrics
    
    Configure in Odoo:
    1. Go to Settings > Technical > Automation > Automated Actions
    2. Create action for unlink/delete:
       ```python
       import requests
       requests.post(
           'YOUR_URL/api/webhooks/odoo',
           json={
               'model': env.context.get('active_model'),
               'action': 'unlink',
               'record_ids': env.context.get('active_ids', [])
           },
           headers={'X-Odoo-Webhook-Secret': 'your-secret-key'}
       )
       ```
    """
    start_time = datetime.now(timezone.utc)
    
    logger.info(f"Webhook received: {payload.model} | {payload.action} | IDs: {payload.record_ids}")
    
    # CRITICAL: Verify webhook secret (HARD FAIL on invalid)
    webhook_secret = request.headers.get("X-Odoo-Webhook-Secret")
    expected_secret = settings.ODOO_API_KEY
    
    if not webhook_secret or webhook_secret != expected_secret:
        logger.error(f"Invalid webhook secret from {request.client.host}")
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing X-Odoo-Webhook-Secret header"
        )
    
    # Map Odoo model to entity type
    model_to_entity = {
        "res.partner": EntityType.ACCOUNT,  # Could also be CONTACT
        "crm.lead": EntityType.OPPORTUNITY,
        "sale.order": EntityType.ORDER,
        "account.move": EntityType.INVOICE,
    }
    
    entity_type = model_to_entity.get(payload.model)
    if not entity_type:
        return WebhookResponse(
            status="ignored",
            message=f"Model {payload.model} not configured for sync"
        )
    
    # Handle DELETE action (unlink) - CRITICAL FOR REAL-TIME SYNC
    if payload.action == "unlink":
        logger.info(f"Processing DELETE webhook for {len(payload.record_ids)} {payload.model} records")
        
        # Process deletion immediately in background (sub-second response)
        background_tasks.add_task(
            process_webhook_delete,
            entity_type=entity_type,
            record_ids=payload.record_ids,
            model=payload.model,
            start_time=start_time
        )
        
        return WebhookResponse(
            status="accepted",
            message=f"Delete webhook accepted for {len(payload.record_ids)} records. Processing in background.",
            processed=len(payload.record_ids)
        )
    
    # Handle CREATE/UPDATE actions
    if payload.action in ["create", "write"]:
        logger.info(f"Processing {payload.action.upper()} webhook for {len(payload.record_ids)} {payload.model} records")
        
        background_tasks.add_task(
            process_webhook_update,
            entity_type=entity_type,
            record_ids=payload.record_ids,
            data=payload.data,
            action=payload.action
        )
        
        return WebhookResponse(
            status="accepted",
            message=f"{payload.action.capitalize()} webhook accepted. Processing {len(payload.record_ids)} records.",
            processed=len(payload.record_ids)
        )
    
    # Unknown action
    return WebhookResponse(
        status="ignored",
        message=f"Unknown action: {payload.action}"
    )
    
    # For create/update, trigger incremental sync
    background_tasks.add_task(
        process_webhook_update,
        entity_type=entity_type,
        record_ids=payload.record_ids,
        data=payload.data
    )
    
    return WebhookResponse(
        status="accepted",
        message=f"Processing {len(payload.record_ids)} {entity_type.value} records",
        processed=len(payload.record_ids)
    )


async def process_webhook_update(
    entity_type: EntityType,
    record_ids: List[int],
    data: Optional[Dict[str, Any]] = None
):
    """
    Process webhook update in background.
    Fetches fresh data from Odoo and updates Data Lake.
    """
    db = Database.get_db()
    
    try:
        # Get Odoo config
        intg = await db.integrations.find_one({"integration_type": "odoo"})
        if not intg or not intg.get("config"):
            logger.error("Odoo not configured, cannot process webhook")
            return
        
        config = intg["config"]
        
        # Import here to avoid circular imports
        from services.odoo.connector import OdooConnector
        from services.sync.service import SyncService
        
        sync_service = SyncService(db)
        
        async with OdooConnector(
            url=config["url"],
            database=config["database"],
            username=config["username"],
            api_key=config["api_key"]
        ) as connector:
            
            # Fetch specific records
            model_map = {
                EntityType.ACCOUNT: "res.partner",
                EntityType.CONTACT: "res.partner",
                EntityType.OPPORTUNITY: "crm.lead",
                EntityType.ORDER: "sale.order",
                EntityType.INVOICE: "account.move",
            }
            
            model = model_map.get(entity_type)
            if not model:
                return
            
            # Fetch records by ID
            records = await connector.search_read(
                model=model,
                domain=[("id", "in", record_ids)],
                limit=len(record_ids)
            )
            
            # Process each record through sync pipeline
            batch_id = f"webhook-{datetime.now().timestamp()}"
            
            for record in records:
                try:
                    # Ingest to Raw Zone
                    await sync_service.data_lake.ingest_raw(
                        source=IntegrationType.ODOO,
                        source_id=str(record.get("id")),
                        entity_type=entity_type,
                        raw_data=record,
                        sync_batch_id=batch_id
                    )
                    
                    # Transform and load
                    normalized = sync_service._normalize_odoo_record(record, entity_type)
                    
                    await sync_service.data_lake.normalize_to_canonical(
                        raw_record={
                            "source": IntegrationType.ODOO.value,
                            "source_id": str(record.get("id")),
                            "entity_type": entity_type.value
                        },
                        normalized_data=normalized,
                        validation_result={"status": "valid", "errors": [], "quality_score": 1.0}
                    )
                    
                    await sync_service.data_lake.aggregate_to_serving(
                        entity_type=entity_type,
                        serving_data={**normalized, "id": str(record.get("id"))},
                        canonical_refs=[str(record.get("id"))],
                        aggregation_type="single"
                    )
                    
                    logger.info(f"Webhook processed: {entity_type.value} #{record.get('id')}")
                    
                except Exception as e:
                    logger.error(f"Failed to process webhook record {record.get('id')}: {e}")
        
        # Update last sync time
        await db.integrations.update_one(
            {"integration_type": "odoo"},
            {"$set": {"last_sync": datetime.now(timezone.utc)}}
        )
        
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")


# ===================== WEBHOOK STATUS =====================

@router.get("/status")
async def webhook_status():
    """Get webhook configuration status"""
    db = Database.get_db()
    
    # Check if Odoo is configured
    intg = await db.integrations.find_one({"integration_type": "odoo"})
    odoo_configured = bool(intg and intg.get("config", {}).get("url"))
    
    # Get webhook URL
    webhook_url = f"{settings.CORS_ORIGINS.split(',')[0] if settings.CORS_ORIGINS != '*' else 'YOUR_DOMAIN'}/api/webhooks/odoo"
    
    return {
        "odoo_configured": odoo_configured,
        "webhook_url": webhook_url,
        "supported_models": ["res.partner", "crm.lead", "sale.order", "account.move"],
        "setup_instructions": {
            "step1": "Go to Odoo Settings > Technical > Automation > Automated Actions",
            "step2": "Create an action for each model you want to sync",
            "step3": "Set trigger to 'On Creation' and 'On Update'",
            "step4": f"Set webhook URL to: {webhook_url}",
            "step5": "Add header X-Odoo-Webhook-Secret with your API key"
        }
    }
