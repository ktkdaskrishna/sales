"""
Odoo Schema Monitor
Detects schema drift between configured field mappings and actual Odoo schema.
Alerts admins when new fields are added to Odoo models.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Set
from motor.motor_asyncio import AsyncIOMotorDatabase

from integrations.odoo.connector import OdooConnector

logger = logging.getLogger(__name__)


class OdooSchemaMonitor:
    """
    Monitors Odoo schema changes and detects drift from configured mappings.
    
    Responsibilities:
    - Fetch current Odoo field schemas
    - Compare with configured field mappings
    - Detect new fields (potential data loss)
    - Detect removed fields (broken mappings)
    - Store drift reports for admin review
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, odoo_config: Dict[str, Any]):
        self.db = db
        self.odoo_config = odoo_config
    
    async def detect_drift_for_all_entities(self) -> Dict[str, Any]:
        """
        Check schema drift for all configured entity mappings.
        
        Returns:
            {
                "total_drift_count": 3,
                "entities_with_drift": ["res.partner", "crm.lead"],
                "drift_reports": [...]
            }
        """
        # Get configured entity mappings
        sys_config = await self.db.system_config.find_one({"id": "system_config"})
        if not sys_config or not sys_config.get("odoo_integration"):
            raise ValueError("Odoo integration not configured")
        
        entity_mappings = sys_config["odoo_integration"].get("entity_mappings", [])
        
        drift_reports = []
        entities_with_drift = []
        total_new_fields = 0
        total_removed_fields = 0
        
        # Connect to Odoo
        connector = OdooConnector(self.odoo_config)
        await connector.connect()
        
        try:
            for mapping in entity_mappings:
                odoo_model = mapping.get("odoo_model")
                if not odoo_model:
                    continue
                
                # Get actual fields from Odoo
                try:
                    actual_fields = await connector.fields_get(odoo_model)
                    
                    # Get configured fields
                    configured_fields = set([
                        fm.get("source_field") 
                        for fm in mapping.get("field_mappings", [])
                    ])
                    
                    actual_field_names = set(actual_fields.keys())
                    
                    # Detect drift
                    new_fields = actual_field_names - configured_fields
                    removed_fields = configured_fields - actual_field_names
                    
                    # Filter out Odoo internal fields
                    new_fields = {f for f in new_fields if not f.startswith('__')}
                    
                    if new_fields or removed_fields:
                        entities_with_drift.append(odoo_model)
                        total_new_fields += len(new_fields)
                        total_removed_fields += len(removed_fields)
                        
                        report = {
                            "entity": mapping.get("name", odoo_model),
                            "odoo_model": odoo_model,
                            "new_fields": list(new_fields),
                            "removed_fields": list(removed_fields),
                            "severity": "critical" if removed_fields else "warning",
                            "detected_at": datetime.now(timezone.utc).isoformat()
                        }
                        drift_reports.append(report)
                        
                except Exception as e:
                    logger.error(f"Failed to check schema for {odoo_model}: {e}")
                    continue
        finally:
            await connector.disconnect()
        
        # Store drift report in database
        if drift_reports:
            await self.db.schema_drift_log.insert_one({
                "integration": "odoo",
                "total_new_fields": total_new_fields,
                "total_removed_fields": total_removed_fields,
                "entities_with_drift": entities_with_drift,
                "reports": drift_reports,
                "checked_at": datetime.now(timezone.utc),
                "acknowledged": False
            })
        
        return {
            "total_drift_count": len(drift_reports),
            "total_new_fields": total_new_fields,
            "total_removed_fields": total_removed_fields,
            "entities_with_drift": entities_with_drift,
            "drift_reports": drift_reports,
            "last_checked": datetime.now(timezone.utc).isoformat()
        }
    
    async def get_latest_drift_report(self) -> Dict[str, Any]:
        """Get the most recent unacknowledged schema drift report"""
        report = await self.db.schema_drift_log.find_one(
            {"integration": "odoo", "acknowledged": False},
            {"_id": 0}
        )
        
        return report or {"total_drift_count": 0, "drift_reports": []}
    
    async def acknowledge_drift(self, drift_id: str) -> bool:
        """Mark a drift report as acknowledged"""
        result = await self.db.schema_drift_log.update_one(
            {"id": drift_id},
            {"$set": {"acknowledged": True, "acknowledged_at": datetime.now(timezone.utc)}}
        )
        return result.modified_count > 0
