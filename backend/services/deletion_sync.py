"""
Deletion Sync Service
Automatically syncs deletion status from data_lake_serving to CQRS projections
"""
import logging
from datetime import datetime, timezone
from typing import List, Dict
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class DeletionSyncService:
    """
    Service to sync deletion status from data_lake_serving to CQRS projections.
    
    This ensures that when Odoo records are deleted and marked is_active=False
    in data_lake_serving, the CQRS read models (opportunity_view, etc.) are
    also updated to hide these records from the UI.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def sync_opportunity_deletions(self) -> Dict[str, int]:
        """
        Sync deleted opportunities from data_lake_serving to opportunity_view.
        
        Returns:
            Dictionary with sync statistics
        """
        logger.info("Starting opportunity deletion sync...")
        
        # Find opportunities marked inactive in data_lake_serving
        inactive_in_lake = await self.db.data_lake_serving.find({
            "entity_type": "opportunity",
            "is_active": False,
            "source": "odoo"
        }, {"_id": 0, "data.id": 1, "data.name": 1, "deleted_at": 1}).to_list(1000)
        
        logger.info(f"Found {len(inactive_in_lake)} inactive opportunities in data_lake_serving")
        
        synced_count = 0
        now = datetime.now(timezone.utc)
        
        for opp_doc in inactive_in_lake:
            opp_id = opp_doc.get("data", {}).get("id")
            deleted_at = opp_doc.get("deleted_at")
            
            if not opp_id:
                continue
            
            # Mark as inactive in opportunity_view (CQRS read model)
            result = await self.db.opportunity_view.update_one(
                {"odoo_id": opp_id},
                {
                    "$set": {
                        "is_active": False,
                        "deleted_at": deleted_at or now.isoformat(),
                        "delete_reason": "odoo_deleted"
                    }
                }
            )
            
            if result.modified_count > 0:
                synced_count += 1
                logger.debug(f"Marked opportunity {opp_id} as inactive in opportunity_view")
        
        logger.info(f"Synced {synced_count} opportunity deletions to opportunity_view")
        
        return {
            "entity": "opportunity",
            "inactive_in_lake": len(inactive_in_lake),
            "synced_to_view": synced_count
        }
    
    async def sync_account_deletions(self) -> Dict[str, int]:
        """Sync deleted accounts from data_lake_serving to any account views"""
        logger.info("Starting account deletion sync...")
        
        inactive_accounts = await self.db.data_lake_serving.find({
            "entity_type": "account",
            "is_active": False,
            "source": "odoo"
        }, {"_id": 0, "data.id": 1}).to_list(1000)
        
        logger.info(f"Found {len(inactive_accounts)} inactive accounts")
        
        return {
            "entity": "account",
            "inactive_in_lake": len(inactive_accounts),
            "synced_to_view": 0  # No account_view yet
        }
    
    async def sync_all_deletions(self) -> Dict[str, any]:
        """
        Sync all entity deletions from data_lake_serving to CQRS views.
        Run this after every Odoo sync to ensure consistency.
        """
        logger.info("=== Starting comprehensive deletion sync ===")
        
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "entities": {}
        }
        
        # Sync opportunities
        opp_result = await self.sync_opportunity_deletions()
        results["entities"]["opportunities"] = opp_result
        
        # Sync accounts
        acc_result = await self.sync_account_deletions()
        results["entities"]["accounts"] = acc_result
        
        # Calculate totals
        results["total_synced"] = sum(
            entity.get("synced_to_view", 0) 
            for entity in results["entities"].values()
        )
        
        logger.info(f"=== Deletion sync complete. Total synced: {results['total_synced']} ===")
        
        return results


async def sync_deletions_after_odoo_sync(db: AsyncIOMotorDatabase):
    """
    Helper function to run deletion sync after Odoo sync.
    Call this at the end of OdooSyncPipelineService.sync_data_lake()
    """
    deletion_service = DeletionSyncService(db)
    return await deletion_service.sync_all_deletions()
