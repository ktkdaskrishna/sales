"""
Odoo Backfill Service
Automatically backfills existing records when new field mappings are added.
Prevents need for manual full sync after configuration changes.
"""
import logging
from typing import List
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


async def trigger_backfill(
    db: AsyncIOMotorDatabase,
    mapping_id: str,
    new_fields: List[str]
):
    """
    Backfill existing records with new field mappings.
    
    This runs as a background task after field mappings are updated.
    Only fetches and updates the new fields (not full record sync).
    
    Args:
        db: Database connection
        mapping_id: Entity mapping ID
        new_fields: List of newly added source field names
    """
    logger.info(f"🔄 Starting backfill for mapping {mapping_id}, new fields: {new_fields}")
    
    try:
        # Get mapping configuration
        sys_config = await db.system_config.find_one({"id": "system_config"})
        if not sys_config:
            logger.error("System config not found")
            return
        
        entity_mappings = sys_config.get("odoo_integration", {}).get("entity_mappings", [])
        mapping = next((m for m in entity_mappings if m.get("id") == mapping_id), None)
        
        if not mapping:
            logger.error(f"Mapping {mapping_id} not found")
            return
        
        odoo_model = mapping.get("odoo_model")
        target_collection = mapping.get("target_collection")
        
        logger.info(f"Backfilling {odoo_model} → {target_collection} for fields: {new_fields}")
        
        # Get Odoo configuration
        intg = await db.integrations.find_one({"integration_type": "odoo"})
        if not intg or not intg.get("config"):
            logger.error("Odoo integration not configured")
            return
        
        odoo_config = intg["config"]
        
        # Use v3.1 adapter to sync just this entity
        from services.odoo.v3_adapter import OdooV3Adapter
        adapter = OdooV3Adapter(db)
        
        # Map Odoo model to entity type
        model_to_entity = {
            "res.partner": "account",
            "crm.lead": "opportunity",
            "mail.activity": "activity",
            "account.move": "invoice",
            "res.users": "user"
        }
        
        entity_type = model_to_entity.get(odoo_model)
        if not entity_type:
            logger.error(f"Unknown Odoo model: {odoo_model}")
            return
        
        # Execute sync for this entity (will fetch all records with new field mappings)
        await adapter._init_pipeline()
        result = await adapter._pipeline.execute(entity_type, mode="full")
        
        logger.info(f"✅ Backfill complete: {result.created_count} created, {result.updated_count} updated, {result.failed_count} failed")
        
        # Update health metrics
        health_update_path = f"odoo_integration.entity_mappings.{entity_mappings.index(mapping)}.health_metrics"
        await db.system_config.update_one(
            {"id": "system_config"},
            {"$set": {
                f"{health_update_path}.last_batch_sync": datetime.now(timezone.utc),
                f"{health_update_path}.last_successful_sync": datetime.now(timezone.utc),
                f"{health_update_path}.total_records": result.total_count
            }}
        )
        
    except Exception as e:
        logger.error(f"Backfill failed: {e}", exc_info=True)
