# ===================== ODOO API CLIENT & SYNC ENGINE =====================
# JSON-RPC based Odoo client compatible with Odoo 17/18

import json
import uuid
import httpx
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from odoo_models import (
    OdooIntegrationConfig, OdooConnectionConfig, EntityMapping, FieldMapping,
    SyncLog, OdooModel, SyncDirection, FieldTransformType,
    get_default_odoo_integration, get_odoo_fields_for_model,
    ODOO_PARTNER_FIELDS, ODOO_LEAD_FIELDS, ODOO_ACTIVITY_FIELDS
)

# ===================== ODOO JSON-RPC CLIENT =====================

class OdooClient:
    """Odoo JSON-RPC API Client - Compatible with Odoo 17/18"""
    
    def __init__(self, url: str, database: str, username: str, api_key: str):
        self.url = url.rstrip('/')
        self.database = database
        self.username = username
        self.api_key = api_key
        self.uid = None
        self.version = None
        
    async def _jsonrpc_call(self, endpoint: str, service: str, method: str, args: List[Any]) -> Any:
        """Make a JSON-RPC call to Odoo"""
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": service,
                "method": method,
                "args": args
            },
            "id": str(uuid.uuid4())
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.url}{endpoint}",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            result = response.json()
            
            if "error" in result:
                error_data = result["error"]
                # Log the full error for debugging
                error_message = error_data.get('message', 'Unknown error')
                error_debug = error_data.get('data', {}).get('message', '')
                full_error = f"{error_message}: {error_debug}" if error_debug else error_message
                raise Exception(f"Odoo Error: {full_error}")
            
            return result.get("result")
    
    async def authenticate(self) -> Tuple[bool, str]:
        """Authenticate with Odoo and get UID"""
        try:
            # Get version info first
            version_info = await self._jsonrpc_call(
                "/jsonrpc", "common", "version", []
            )
            self.version = version_info.get("server_version", "Unknown")
            
            # Authenticate
            self.uid = await self._jsonrpc_call(
                "/jsonrpc", "common", "authenticate",
                [self.database, self.username, self.api_key, {}]
            )
            
            if not self.uid:
                return False, "Authentication failed. Check credentials."
            
            return True, f"Connected to Odoo {self.version}"
            
        except Exception as e:
            return False, str(e)
    
    async def search_read(
        self, 
        model: str, 
        domain: List[Any] = None, 
        fields: List[str] = None,
        limit: int = 100,
        offset: int = 0,
        order: str = None
    ) -> List[Dict]:
        """Search and read records from Odoo"""
        if not self.uid:
            raise Exception("Not authenticated")
        
        kwargs = {"limit": limit, "offset": offset}
        if fields:
            kwargs["fields"] = fields
        if order:
            kwargs["order"] = order
            
        return await self._jsonrpc_call(
            "/jsonrpc", "object", "execute_kw",
            [self.database, self.uid, self.api_key, model, "search_read", [domain or []], kwargs]
        )
    
    async def read(self, model: str, ids: List[int], fields: List[str] = None) -> List[Dict]:
        """Read specific records by ID"""
        if not self.uid:
            raise Exception("Not authenticated")
            
        kwargs = {}
        if fields:
            kwargs["fields"] = fields
            
        return await self._jsonrpc_call(
            "/jsonrpc", "object", "execute_kw",
            [self.database, self.uid, self.api_key, model, "read", [ids], kwargs]
        )
    
    async def create(self, model: str, values: Dict) -> int:
        """Create a record in Odoo"""
        if not self.uid:
            raise Exception("Not authenticated")
            
        return await self._jsonrpc_call(
            "/jsonrpc", "object", "execute_kw",
            [self.database, self.uid, self.api_key, model, "create", [values]]
        )
    
    async def write(self, model: str, ids: List[int], values: Dict) -> bool:
        """Update records in Odoo"""
        if not self.uid:
            raise Exception("Not authenticated")
            
        return await self._jsonrpc_call(
            "/jsonrpc", "object", "execute_kw",
            [self.database, self.uid, self.api_key, model, "write", [ids, values]]
        )
    
    async def get_model_fields(self, model: str) -> Dict[str, Any]:
        """Get field definitions for a model (for dynamic field discovery)"""
        if not self.uid:
            raise Exception("Not authenticated")
            
        return await self._jsonrpc_call(
            "/jsonrpc", "object", "execute_kw",
            [self.database, self.uid, self.api_key, model, "fields_get", [], {"attributes": ["string", "type", "relation", "required", "selection"]}]
        )
    
    async def count(self, model: str, domain: List[Any] = None) -> int:
        """Count records matching domain"""
        if not self.uid:
            raise Exception("Not authenticated")
            
        return await self._jsonrpc_call(
            "/jsonrpc", "object", "execute_kw",
            [self.database, self.uid, self.api_key, model, "search_count", [domain or []]]
        )


# ===================== SYNC ENGINE =====================

class OdooSyncEngine:
    """Engine for syncing data between Odoo and local database"""
    
    def __init__(self, db: AsyncIOMotorDatabase, client: OdooClient):
        self.db = db
        self.client = client
    
    async def transform_value(self, value: Any, mapping: FieldMapping, odoo_record: Dict) -> Any:
        """Transform a value according to field mapping rules"""
        if value is None:
            return mapping.default_value
        
        transform_type = mapping.transform_type
        config = mapping.transform_config
        
        if transform_type == FieldTransformType.DIRECT:
            return value
        
        elif transform_type == FieldTransformType.LOOKUP:
            # Handle many2one fields (returns [id, name])
            if isinstance(value, list) and len(value) == 2:
                lookup_field = config.get("lookup_field", "name")
                if lookup_field == "name":
                    return value[1]  # Return the name
                elif lookup_field == "id":
                    return value[0]  # Return the ID
                
                # Check for value mapping
                value_mapping = config.get("value_mapping", {})
                if value[1] in value_mapping:
                    return value_mapping[value[1]]
                return value[1]
            elif isinstance(value, (int, str)):
                return value
            return None
        
        elif transform_type == FieldTransformType.FORMAT:
            # Format transformations
            if config.get("strip_html"):
                import re
                return re.sub('<[^<]+?>', '', str(value)) if value else None
            return value
        
        elif transform_type == FieldTransformType.DEFAULT:
            return value if value else mapping.default_value
        
        elif transform_type == FieldTransformType.CONCATENATE:
            # Concatenate multiple fields
            fields_to_concat = config.get("fields", [])
            separator = config.get("separator", " ")
            values = [str(odoo_record.get(f, "")) for f in fields_to_concat]
            return separator.join(filter(None, values))
        
        return value
    
    async def map_record(self, odoo_record: Dict, entity_mapping: EntityMapping) -> Dict:
        """Map an Odoo record to local format"""
        local_record = {
            "odoo_id": str(odoo_record.get("id")),
            "odoo_model": entity_mapping.odoo_model.value,
            "last_synced_at": datetime.now(timezone.utc),
        }
        
        for field_mapping in entity_mapping.field_mappings:
            if not field_mapping.enabled:
                continue
            
            odoo_value = odoo_record.get(field_mapping.source_field)
            local_value = await self.transform_value(odoo_value, field_mapping, odoo_record)
            
            if local_value is not None or field_mapping.is_required:
                local_record[field_mapping.target_field] = local_value
        
        return local_record
    
    async def sync_entity(self, entity_mapping: EntityMapping, batch_size: int = 100) -> SyncLog:
        """Sync a single entity type from Odoo"""
        log = SyncLog(
            id=str(uuid.uuid4()),
            entity_mapping_id=entity_mapping.id,
            started_at=datetime.now(timezone.utc),
            status="running"
        )
        
        try:
            # Get fields to fetch from Odoo
            odoo_fields = [m.source_field for m in entity_mapping.field_mappings if m.enabled]
            if "id" not in odoo_fields:
                odoo_fields.append("id")
            
            # Build domain filter - Odoo expects list of tuples like [("field", "op", "value")]
            domain = []
            if entity_mapping.sync_filter:
                for key, value in entity_mapping.sync_filter.items():
                    domain.append((key, "=", value))
            
            # Count total records
            total_count = await self.client.count(entity_mapping.odoo_model.value, domain)
            
            # Fetch and process in batches
            offset = 0
            while offset < total_count:
                odoo_records = await self.client.search_read(
                    entity_mapping.odoo_model.value,
                    domain=domain,
                    fields=odoo_fields,
                    limit=batch_size,
                    offset=offset,
                    order="id asc"
                )
                
                for odoo_record in odoo_records:
                    try:
                        log.records_processed += 1
                        local_record = await self.map_record(odoo_record, entity_mapping)
                        
                        # Find existing record by odoo_id
                        existing = await self.db[entity_mapping.local_collection].find_one(
                            {"odoo_id": local_record["odoo_id"]}
                        )
                        
                        if existing:
                            # Update existing
                            local_record["updated_at"] = datetime.now(timezone.utc)
                            await self.db[entity_mapping.local_collection].update_one(
                                {"odoo_id": local_record["odoo_id"]},
                                {"$set": local_record}
                            )
                            log.records_updated += 1
                        else:
                            # Create new
                            local_record["id"] = str(uuid.uuid4())
                            local_record["created_at"] = datetime.now(timezone.utc)
                            local_record["updated_at"] = datetime.now(timezone.utc)
                            await self.db[entity_mapping.local_collection].insert_one(local_record)
                            log.records_created += 1
                            
                    except Exception as e:
                        log.records_failed += 1
                        log.errors.append({
                            "odoo_id": odoo_record.get("id"),
                            "error": str(e)
                        })
                
                offset += batch_size
            
            log.status = "success" if log.records_failed == 0 else "partial"
            log.completed_at = datetime.now(timezone.utc)
            
        except Exception as e:
            log.status = "failed"
            log.completed_at = datetime.now(timezone.utc)
            log.errors.append({"error": str(e)})
        
        # Save sync log
        await self.db.odoo_sync_logs.insert_one(log.model_dump())
        
        return log
    
    async def sync_users_from_odoo(self, config: "OdooIntegrationConfig") -> Dict[int, str]:
        """Fetch Odoo users and create/map to platform users"""
        user_map = {}  # odoo_user_id -> platform_user_id
        
        if not self.client:
            return user_map
        
        # Fetch Odoo users
        odoo_users = await self.client.search_read(
            "res.users",
            domain=[("share", "=", False)],  # Only internal users
            fields=["id", "name", "login", "email"],
            limit=100
        )
        
        for odoo_user in odoo_users:
            odoo_id = odoo_user.get("id")
            email = odoo_user.get("email") or odoo_user.get("login")
            name = odoo_user.get("name")
            
            if not email:
                continue
            
            # Check if platform user exists with this email
            platform_user = await self.db.users.find_one({"email": email.lower()})
            
            if platform_user:
                # Map to existing user
                user_map[odoo_id] = platform_user["id"]
                # Update odoo_user_id on the platform user
                await self.db.users.update_one(
                    {"id": platform_user["id"]},
                    {"$set": {"odoo_user_id": odoo_id}}
                )
            elif config.auto_create_users:
                # Create new platform user with bcrypt directly
                import bcrypt
                
                new_user_id = str(uuid.uuid4())
                default_password = "changeme123"
                password_hash = bcrypt.hashpw(default_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                new_user = {
                    "id": new_user_id,
                    "email": email.lower(),
                    "name": name,
                    "password_hash": password_hash,
                    "role": "account_manager",  # Default role for Odoo users
                    "department_id": None,
                    "is_active": True,
                    "odoo_user_id": odoo_id,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }
                await self.db.users.insert_one(new_user)
                user_map[odoo_id] = new_user_id
                print(f"Created platform user: {name} ({email})")
            
        return user_map


# ===================== API ROUTES =====================

def create_odoo_routes(db: AsyncIOMotorDatabase, get_current_user, require_role) -> APIRouter:
    """Create Odoo integration API routes"""
    
    router = APIRouter(prefix="/odoo", tags=["Odoo Integration"])
    
    async def get_odoo_config() -> OdooIntegrationConfig:
        """Get Odoo integration config from database"""
        config = await db.system_config.find_one({"id": "system_config"})
        odoo_config = config.get("odoo_integration") if config else None
        if not odoo_config:
            return get_default_odoo_integration()
        return OdooIntegrationConfig(**odoo_config)
    
    async def save_odoo_config(config: OdooIntegrationConfig):
        """Save Odoo integration config"""
        await db.system_config.update_one(
            {"id": "system_config"},
            {"$set": {"odoo_integration": config.model_dump()}},
            upsert=True
        )
    
    @router.get("/config")
    async def get_integration_config(user: dict = Depends(require_role(["super_admin"]))):
        """Get Odoo integration configuration"""
        config = await get_odoo_config()
        # Mask API key for security
        if config.connection.api_key:
            config.connection.api_key = "***" + config.connection.api_key[-4:] if len(config.connection.api_key) > 4 else "****"
        return config.model_dump()
    
    @router.put("/config/connection")
    async def update_connection(
        connection_data: dict,
        user: dict = Depends(require_role(["super_admin"]))
    ):
        """Update Odoo connection settings"""
        config = await get_odoo_config()
        
        # Update connection fields
        for key, value in connection_data.items():
            if hasattr(config.connection, key) and value is not None:
                # Don't update if it's a masked API key
                if key == "api_key" and value.startswith("***"):
                    continue
                setattr(config.connection, key, value)
        
        config.updated_at = datetime.now(timezone.utc)
        await save_odoo_config(config)
        return {"message": "Connection settings updated"}
    
    @router.post("/test-connection")
    async def test_connection(user: dict = Depends(require_role(["super_admin"]))):
        """Test Odoo connection"""
        config = await get_odoo_config()
        conn = config.connection
        
        if not conn.url or not conn.database or not conn.username or not conn.api_key:
            raise HTTPException(status_code=400, detail="Missing connection settings")
        
        client = OdooClient(conn.url, conn.database, conn.username, conn.api_key)
        success, message = await client.authenticate()
        
        if success:
            # Update connection status
            config.connection.is_connected = True
            config.connection.last_connected_at = datetime.now(timezone.utc)
            config.connection.odoo_version = client.version
            await save_odoo_config(config)
        
        return {
            "success": success,
            "message": message,
            "version": client.version if success else None
        }
    
    @router.get("/fields/{model}")
    async def get_model_fields(
        model: OdooModel,
        user: dict = Depends(require_role(["super_admin"]))
    ):
        """Get available fields for an Odoo model"""
        # First return static field definitions
        static_fields = get_odoo_fields_for_model(model)
        
        # Try to get dynamic fields from Odoo if connected
        config = await get_odoo_config()
        conn = config.connection
        
        dynamic_fields = []
        if conn.is_connected and conn.url and conn.api_key:
            try:
                client = OdooClient(conn.url, conn.database, conn.username, conn.api_key)
                success, _ = await client.authenticate()
                if success:
                    fields_info = await client.get_model_fields(model.value)
                    dynamic_fields = [
                        {
                            "name": name,
                            "type": info.get("type", "char"),
                            "label": info.get("string", name),
                            "required": info.get("required", False),
                            "relation": info.get("relation"),
                            "options": [opt[0] for opt in info.get("selection", [])] if info.get("selection") else None
                        }
                        for name, info in fields_info.items()
                        if not name.startswith("__")  # Skip internal fields
                    ]
            except Exception:
                pass  # Fall back to static fields
        
        return {
            "model": model.value,
            "static_fields": static_fields,
            "dynamic_fields": dynamic_fields,
            "from_odoo": len(dynamic_fields) > 0
        }
    
    @router.get("/mappings")
    async def get_entity_mappings(user: dict = Depends(require_role(["super_admin"]))):
        """Get all entity mappings"""
        config = await get_odoo_config()
        return [m.model_dump() for m in config.entity_mappings]

    @router.get("/data-lake-stats")
    async def get_odoo_data_lake_stats(user: dict = Depends(require_role(["super_admin"]))):
        """Get Odoo-specific Data Lake stats for group settings."""
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
    
    @router.get("/mappings/{mapping_id}")
    async def get_entity_mapping(
        mapping_id: str,
        user: dict = Depends(require_role(["super_admin"]))
    ):
        """Get a specific entity mapping"""
        config = await get_odoo_config()
        mapping = next((m for m in config.entity_mappings if m.id == mapping_id), None)
        if not mapping:
            raise HTTPException(status_code=404, detail="Mapping not found")
        return mapping.model_dump()
    
    @router.put("/mappings/{mapping_id}")
    async def update_entity_mapping(
        mapping_id: str,
        mapping_data: dict,
        user: dict = Depends(require_role(["super_admin"]))
    ):
        """Update an entity mapping"""
        config = await get_odoo_config()
        mapping_idx = next((i for i, m in enumerate(config.entity_mappings) if m.id == mapping_id), None)
        
        if mapping_idx is None:
            raise HTTPException(status_code=404, detail="Mapping not found")
        
        # Update mapping
        existing = config.entity_mappings[mapping_idx].model_dump()
        existing.update(mapping_data)
        config.entity_mappings[mapping_idx] = EntityMapping(**existing)
        config.updated_at = datetime.now(timezone.utc)
        await save_odoo_config(config)
        
        return {"message": "Mapping updated"}
    
    @router.put("/mappings/{mapping_id}/fields")
    async def update_field_mappings(
        mapping_id: str,
        field_mappings: List[dict],
        user: dict = Depends(require_role(["super_admin"]))
    ):
        """Update field mappings for an entity"""
        config = await get_odoo_config()
        mapping = next((m for m in config.entity_mappings if m.id == mapping_id), None)
        
        if not mapping:
            raise HTTPException(status_code=404, detail="Mapping not found")
        
        # Update field mappings
        mapping.field_mappings = [FieldMapping(**fm) for fm in field_mappings]
        config.updated_at = datetime.now(timezone.utc)
        await save_odoo_config(config)
        
        return {"message": "Field mappings updated"}
    
    @router.post("/sync/{mapping_id}")
    async def sync_entity(
        mapping_id: str,
        user: dict = Depends(require_role(["super_admin"]))
    ):
        """Trigger sync for an entity mapping"""
        config = await get_odoo_config()
        conn = config.connection
        
        if not conn.is_connected:
            raise HTTPException(status_code=400, detail="Odoo not connected")
        
        mapping = next((m for m in config.entity_mappings if m.id == mapping_id), None)
        if not mapping:
            raise HTTPException(status_code=404, detail="Mapping not found")
        
        if not mapping.sync_enabled:
            raise HTTPException(status_code=400, detail="Sync disabled for this mapping")
        
        # Create client and sync engine
        client = OdooClient(conn.url, conn.database, conn.username, conn.api_key)
        success, message = await client.authenticate()
        
        if not success:
            raise HTTPException(status_code=500, detail=f"Authentication failed: {message}")
        
        engine = OdooSyncEngine(db, client)
        
        # First sync users to create user mapping
        user_map = await engine.sync_users_from_odoo(config)
        
        log = await engine.sync_entity(mapping, config.global_settings.get("sync_batch_size", 100))
        
        # Post-process: Assign accounts/opportunities to mapped users
        await assign_to_platform_users(db, mapping, user_map)
        
        # Update last sync time
        mapping.last_sync_at = datetime.now(timezone.utc)
        await save_odoo_config(config)
        
        return {
            "status": log.status,
            "processed": log.records_processed,
            "created": log.records_created,
            "updated": log.records_updated,
            "failed": log.records_failed,
            "errors": log.errors[:10] if log.errors else []  # Return first 10 errors
        }
    
    async def assign_to_platform_users(db, mapping: EntityMapping, user_map: Dict[int, str]):
        """Assign synced records to platform users based on Odoo salesperson"""
        collection = db[mapping.local_collection]
        
        # Find records with odoo_salesperson_id (contacts) or owner_id (opportunities)
        if mapping.local_collection == "accounts":
            # For accounts, look for odoo_salesperson_id
            async for record in collection.find({"odoo_salesperson_id": {"$exists": True}}):
                salesperson_data = record.get("odoo_salesperson_id")
                if isinstance(salesperson_data, list) and len(salesperson_data) >= 1:
                    odoo_user_id = salesperson_data[0] if isinstance(salesperson_data[0], int) else None
                elif isinstance(salesperson_data, int):
                    odoo_user_id = salesperson_data
                else:
                    continue
                
                if odoo_user_id and odoo_user_id in user_map:
                    await collection.update_one(
                        {"id": record["id"]},
                        {"$set": {"assigned_am_id": user_map[odoo_user_id]}}
                    )
        
        elif mapping.local_collection == "opportunities":
            # For opportunities, look for owner_id (which comes from user_id)
            async for record in collection.find({"odoo_id": {"$exists": True}}):
                # The owner_id was already mapped during sync, but we need to resolve it
                owner_data = record.get("owner_id")
                if isinstance(owner_data, list) and len(owner_data) >= 1:
                    odoo_user_id = owner_data[0] if isinstance(owner_data[0], int) else None
                elif isinstance(owner_data, int):
                    odoo_user_id = owner_data
                else:
                    continue
                
                if odoo_user_id and odoo_user_id in user_map:
                    await collection.update_one(
                        {"id": record["id"]},
                        {"$set": {"owner_id": user_map[odoo_user_id]}}
                    )
    
    @router.post("/sync-users")
    async def sync_odoo_users(user: dict = Depends(require_role(["super_admin"]))):
        """Sync users from Odoo and create platform accounts"""
        config = await get_odoo_config()
        conn = config.connection
        
        if not conn.is_connected:
            raise HTTPException(status_code=400, detail="Odoo not connected")
        
        client = OdooClient(conn.url, conn.database, conn.username, conn.api_key)
        success, message = await client.authenticate()
        
        if not success:
            raise HTTPException(status_code=500, detail=f"Authentication failed: {message}")
        
        engine = OdooSyncEngine(db, client)
        user_map = await engine.sync_users_from_odoo(config)
        
        return {
            "message": f"Synced {len(user_map)} users from Odoo",
            "user_mappings": [{"odoo_id": k, "platform_id": v} for k, v in user_map.items()]
        }
    
    @router.post("/sync-all")
    async def sync_all_entities(user: dict = Depends(require_role(["super_admin"]))):
        """Sync all enabled entity mappings"""
        config = await get_odoo_config()
        conn = config.connection
        
        if not conn.is_connected:
            raise HTTPException(status_code=400, detail="Odoo not connected")
        
        # Create client
        client = OdooClient(conn.url, conn.database, conn.username, conn.api_key)
        success, message = await client.authenticate()
        
        if not success:
            raise HTTPException(status_code=500, detail=f"Authentication failed: {message}")
        
        engine = OdooSyncEngine(db, client)
        
        # First sync users
        user_map = await engine.sync_users_from_odoo(config)
        
        results = []
        
        for mapping in config.entity_mappings:
            if mapping.sync_enabled:
                log = await engine.sync_entity(mapping, config.global_settings.get("sync_batch_size", 100))
                
                # Assign to platform users
                await assign_to_platform_users(db, mapping, user_map)
                
                mapping.last_sync_at = datetime.now(timezone.utc)
                results.append({
                    "entity": mapping.name,
                    "status": log.status,
                    "processed": log.records_processed,
                    "created": log.records_created,
                    "updated": log.records_updated,
                    "failed": log.records_failed
                })
        
        await save_odoo_config(config)
        return {"results": results, "users_synced": len(user_map)}
    
    @router.get("/sync-logs")
    async def get_sync_logs(
        limit: int = 20,
        user: dict = Depends(require_role(["super_admin"]))
    ):
        """Get recent sync logs"""
        logs = await db.odoo_sync_logs.find(
            {},
            {"_id": 0}
        ).sort("started_at", -1).limit(limit).to_list(limit)
        return logs
    
    @router.get("/preview/{mapping_id}")
    async def preview_sync(
        mapping_id: str,
        limit: int = 5,
        user: dict = Depends(require_role(["super_admin"]))
    ):
        """Preview data that would be synced (without actually syncing)"""
        config = await get_odoo_config()
        conn = config.connection
        
        if not conn.is_connected:
            raise HTTPException(status_code=400, detail="Odoo not connected")
        
        mapping = next((m for m in config.entity_mappings if m.id == mapping_id), None)
        if not mapping:
            raise HTTPException(status_code=404, detail="Mapping not found")
        
        # Create client
        client = OdooClient(conn.url, conn.database, conn.username, conn.api_key)
        success, message = await client.authenticate()
        
        if not success:
            raise HTTPException(status_code=500, detail=f"Authentication failed: {message}")
        
        # Get fields to fetch
        odoo_fields = [m.source_field for m in mapping.field_mappings if m.enabled]
        if "id" not in odoo_fields:
            odoo_fields.append("id")
        
        # Log for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Preview: model={mapping.odoo_model.value}, fields={odoo_fields}")
        
        # Build domain filter - Odoo expects list of tuples/lists like [("field", "op", "value")]
        domain = []
        if mapping.sync_filter:
            for key, value in mapping.sync_filter.items():
                domain.append((key, "=", value))
        
        logger.info(f"Preview: domain={domain}")
        
        # Fetch sample records
        odoo_records = await client.search_read(
            mapping.odoo_model.value,
            domain=domain,
            fields=odoo_fields,
            limit=limit
        )
        
        # Transform records
        engine = OdooSyncEngine(db, client)
        preview_data = []
        
        for odoo_record in odoo_records:
            local_record = await engine.map_record(odoo_record, mapping)
            preview_data.append({
                "odoo": odoo_record,
                "mapped": local_record
            })
        
        return {
            "total_in_odoo": await client.count(mapping.odoo_model.value, domain),
            "preview": preview_data
        }
    
    # ===================== TOGGLE SYNC ENDPOINT =====================
    
    @router.put("/mappings/{mapping_id}/toggle")
    async def toggle_entity_sync(
        mapping_id: str,
        toggle_data: dict,
        user: dict = Depends(require_role(["super_admin"]))
    ):
        """Toggle sync enabled/disabled for an entity mapping"""
        config = await get_odoo_config()
        
        # Find and update the mapping
        mapping_found = False
        for mapping in config.entity_mappings:
            if mapping.id == mapping_id:
                mapping.sync_enabled = toggle_data.get("sync_enabled", True)
                mapping_found = True
                break
        
        if not mapping_found:
            raise HTTPException(status_code=404, detail="Mapping not found")
        
        # Save config
        await db.system_config.update_one(
            {"id": "system_config"},
            {"$set": {"odoo_integration": config.model_dump()}},
            upsert=True
        )
        
        return {"message": f"Sync {'enabled' if toggle_data.get('sync_enabled') else 'disabled'} for {mapping_id}"}
    
    # ===================== WEBHOOK ENDPOINT (Odoo → Platform) =====================
    
    @router.post("/webhook/incoming")
    async def receive_odoo_webhook(
        payload: dict,
    ):
        """
        Receive webhook from Odoo for real-time sync.
        Odoo should be configured to send webhooks on create/update/delete events.
        
        Expected payload format:
        {
            "model": "res.partner",
            "event": "create" | "update" | "delete",
            "record_id": 123,
            "data": { ... record fields ... },
            "timestamp": "2024-01-01T00:00:00Z"
        }
        """
        try:
            model = payload.get("model")
            event = payload.get("event", "update")
            record_id = payload.get("record_id")
            data = payload.get("data", {})
            source = payload.get("source", "odoo")
            
            # Prevent loops - don't process if this originated from our platform
            if source == "platform":
                return {"status": "skipped", "reason": "Loop prevention - originated from platform"}
            
            if not model or not record_id:
                raise HTTPException(status_code=400, detail="Missing model or record_id")
            
            # Find the mapping for this model
            config = await get_odoo_config()
            mapping = None
            for em in config.entity_mappings:
                if em.odoo_model.value == model:
                    mapping = em
                    break
            
            if not mapping:
                return {"status": "skipped", "reason": f"No mapping configured for model {model}"}
            
            if not mapping.sync_enabled:
                return {"status": "skipped", "reason": f"Sync disabled for {model}"}
            
            # Get the target collection
            collection = db[mapping.local_collection]
            
            if event == "delete":
                # Delete the local record
                result = await collection.delete_one({"odoo_id": record_id})
                return {
                    "status": "success",
                    "event": "delete",
                    "deleted": result.deleted_count
                }
            
            # For create/update, we need to map the data
            # Use a minimal engine without full client
            engine = OdooSyncEngine(db, None)
            
            # Add id to data for mapping
            data["id"] = record_id
            local_record = await engine.map_record(data, mapping)
            
            # Check if record exists
            existing = await collection.find_one({"odoo_id": record_id})
            
            if existing:
                # Update
                local_record["updated_at"] = datetime.now(timezone.utc)
                await collection.update_one(
                    {"odoo_id": record_id},
                    {"$set": local_record}
                )
                return {"status": "success", "event": "update", "odoo_id": record_id}
            else:
                # Create
                local_record["created_at"] = datetime.now(timezone.utc)
                local_record["updated_at"] = datetime.now(timezone.utc)
                await collection.insert_one(local_record)
                return {"status": "success", "event": "create", "odoo_id": record_id}
                
        except Exception as e:
            # Log the error but don't fail - webhooks should be resilient
            print(f"Webhook processing error: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    return router
