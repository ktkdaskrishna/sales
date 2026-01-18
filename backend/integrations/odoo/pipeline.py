"""
Odoo Sync Pipeline
Complete sync pipeline for Odoo ERP integration
"""

from datetime import datetime
from typing import Any, Dict, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

from sync_engine.pipeline import SyncPipeline
from sync_engine.base_components import BaseLoader, BaseSyncLogger
from core.interfaces import ISyncPipeline
from core.base import SyncBatch, RawRecord
from core.enums import IntegrationSource, EntityType

from .connector import OdooConnector
from .mapper import (
    OdooContactMapper,
    OdooAccountMapper,
    OdooOpportunityMapper,
    OdooActivityMapper,
    OdooUserMapper,
    OdooInvoiceMapper,
)
from .validator import OdooValidator
from .normalizer import OdooNormalizer


logger = logging.getLogger(__name__)


class OdooLoader(BaseLoader):
    """Odoo-specific loader with entity type awareness"""
    
    def _get_entity_type(self, record: RawRecord) -> EntityType:
        """Determine entity type from raw record"""
        data = record.raw_data
        
        # Check for specific markers
        if 'is_company' in data:
            return EntityType.ACCOUNT if data.get('is_company') else EntityType.CONTACT
        
        if 'expected_revenue' in data or 'probability' in data:
            return EntityType.OPPORTUNITY
        
        if 'activity_type_id' in data:
            return EntityType.ACTIVITY
        
        if 'login' in data:
            return EntityType.USER
        
        return EntityType.CONTACT


class OdooSyncPipeline(ISyncPipeline):
    """
    Complete Odoo sync pipeline.
    Handles all Odoo entity types with appropriate mappers.
    """
    
    ENTITY_MAPPERS = {
        'contact': OdooContactMapper,
        'account': OdooAccountMapper,
        'opportunity': OdooOpportunityMapper,
        'activity': OdooActivityMapper,
        'user': OdooUserMapper,
        'invoice': OdooInvoiceMapper,
    }
    
    def __init__(self, config: Dict[str, Any], db: AsyncIOMotorDatabase):
        self.config = config
        self.db = db
        
        # Initialize components
        self._connector = OdooConnector(config)
        self._validator = OdooValidator()
        self._normalizer = OdooNormalizer(db)
        self._sync_logger = BaseSyncLogger(db)
        
        # Data lake manager for loading
        from data_lake import DataLakeManager
        self._data_lake = DataLakeManager(db)
        self._loader = OdooLoader(self._data_lake)
        
        # Store pipelines for each entity type
        self._pipelines: Dict[str, SyncPipeline] = {}
    
    @property
    def connector(self):
        return self._connector
    
    @property
    def source_name(self) -> str:
        return IntegrationSource.ODOO.value
    
    def _get_pipeline(self, entity_type: str) -> SyncPipeline:
        """Get or create pipeline for entity type"""
        if entity_type not in self._pipelines:
            mapper_class = self.ENTITY_MAPPERS.get(entity_type)
            if not mapper_class:
                raise ValueError(f"No mapper for entity type: {entity_type}")
            
            mapper = mapper_class()
            
            self._pipelines[entity_type] = SyncPipeline(
                connector=self._connector,
                mapper=mapper,
                validator=self._validator,
                normalizer=self._normalizer,
                loader=self._loader,
                sync_logger=self._sync_logger,
                batch_size=self.config.get('batch_size', 100)
            )
        
        return self._pipelines[entity_type]
    
    async def execute(
        self,
        entity_type: str,
        mode: str = "full",
        since: Optional[datetime] = None
    ) -> SyncBatch:
        """Execute sync for a specific entity type"""
        pipeline = self._get_pipeline(entity_type)
        return await pipeline.execute(entity_type, mode, since)
    
    async def sync_all(
        self,
        mode: str = "full",
        since: Optional[datetime] = None
    ) -> Dict[str, SyncBatch]:
        """Sync all entity types"""
        results = {}
        
        # Sync order matters - users first, then accounts, then contacts, etc.
        entity_order = ['user', 'account', 'contact', 'opportunity', 'activity']
        
        for entity_type in entity_order:
            try:
                logger.info(f"Starting {entity_type} sync...")
                results[entity_type] = await self.execute(entity_type, mode, since)
            except Exception as e:
                logger.error(f"Failed to sync {entity_type}: {e}")
                results[entity_type] = SyncBatch(
                    source=self.source_name,
                    entity_type=entity_type,
                    status="failed",
                    errors=[{"error": str(e)}]
                )
        
        # Clear normalizer cache after full sync
        self._normalizer.clear_cache()
        
        return results
    
    async def replay(self, batch_id: str) -> SyncBatch:
        """Replay a previous sync batch"""
        # Get batch info
        batch_doc = await self.db["sync_batches"].find_one({"id": batch_id})
        if not batch_doc:
            raise ValueError(f"Batch not found: {batch_id}")
        
        entity_type = batch_doc["entity_type"]
        
        # Get raw records from batch
        raw_records = await self._data_lake.raw.get_by_batch(
            IntegrationSource.ODOO,
            EntityType(entity_type),
            batch_id
        )
        
        # Create new replay batch
        replay_batch = SyncBatch(
            source=self.source_name,
            entity_type=entity_type,
            metadata={"replay_of": batch_id, "mode": "replay"}
        )
        
        await self._sync_logger.log_sync_start(replay_batch)
        
        pipeline = self._get_pipeline(entity_type)
        
        # Reprocess each record
        for raw_doc in raw_records:
            try:
                raw_record = RawRecord(
                    source=raw_doc["_source"],
                    source_id=raw_doc["_source_id"],
                    raw_data=raw_doc["_raw_data"],
                    sync_batch_id=replay_batch.id
                )
                
                # Map to canonical
                entity = pipeline._mapper.map_to_canonical(raw_record)
                
                # Normalize
                entity = await self._normalizer.normalize(entity)
                await self._normalizer.deduplicate(entity)
                entity = await self._normalizer.resolve_references(entity)
                
                # Load to canonical (skip raw since already exists)
                await self._loader.load_canonical(entity)
                await self._loader.load_serving(entity)
                
                replay_batch.records_processed += 1
                replay_batch.records_updated += 1
                
            except Exception as e:
                replay_batch.records_processed += 1
                replay_batch.records_failed += 1
                replay_batch.errors.append({
                    "source_id": raw_doc.get("_source_id"),
                    "error": str(e)
                })
        
        replay_batch.status = "completed" if replay_batch.records_failed == 0 else "partial"
        await self._sync_logger.log_sync_complete(replay_batch)
        
        return replay_batch
    
    async def sync_single(
        self,
        entity_type: str,
        source_id: Any
    ) -> Optional[Any]:
        """Sync a single record"""
        pipeline = self._get_pipeline(entity_type)
        return await pipeline.sync_single(entity_type, source_id)
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test Odoo connection"""
        return await self._connector.test_connection()


def create_odoo_pipeline(config: Dict[str, Any], db: AsyncIOMotorDatabase) -> OdooSyncPipeline:
    """Factory function to create Odoo pipeline"""
    return OdooSyncPipeline(config, db)
