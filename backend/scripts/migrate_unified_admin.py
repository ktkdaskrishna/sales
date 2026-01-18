"""
Migration Scripts for Unified Admin Architecture
Run these scripts to migrate existing data to new architecture
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone


async def migrate_llm_config():
    """Migrate old llm_config to system_config.llm"""
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.test_database
    
    print("=== Migrating LLM Configuration ===")
    
    # Check if old config exists
    old_config = await db.llm_config.find_one({}, {"_id": 0})
    
    if old_config:
        print(f"Found old LLM config: {old_config.get('provider')}")
        
        # Migrate to system_config
        new_llm_config = {
            "provider": old_config.get("provider", "openai"),
            "api_key": old_config.get("api_key", ""),
            "default_model": old_config.get("model", "gpt-4"),
            "base_url": "https://api.openai.com/v1",
            "features": {
                "deal_confidence": {"enabled": True, "model": old_config.get("model", "gpt-4")},
                "field_mapping": {"enabled": True, "model": old_config.get("model", "gpt-4")},
                "chat": {"enabled": True, "model": old_config.get("model", "gpt-4")},
                "data_quality": {"enabled": True, "model": old_config.get("model", "gpt-4")}
            },
            "migrated_at": datetime.now(timezone.utc).isoformat(),
            "migration_source": "llm_config"
        }
        
        result = await db.system_config.update_one(
            {},
            {"$set": {"llm": new_llm_config}},
            upsert=True
        )
        
        print(f"✅ Migrated to system_config.llm: {result.matched_count or result.upserted_id}")
    else:
        print("No old LLM config found")
    
    client.close()


async def migrate_commission_base_rate():
    """Update commission templates from 5% to 1% base rate"""
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.test_database
    
    print("\\n=== Migrating Commission Base Rates ===")
    
    # Find templates with old 5% rate
    old_templates = await db.commission_templates.find(
        {"base_rate": 0.05},
        {"_id": 0, "name": 1}
    ).to_list(100)
    
    if old_templates:
        print(f"Found {len(old_templates)} templates with 5% base rate")
        
        # Update to 1%
        result = await db.commission_templates.update_many(
            {"base_rate": 0.05},
            {
                "$set": {
                    "base_rate": 0.01,
                    "migrated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        print(f"✅ Updated {result.modified_count} templates to 1% base rate")
    else:
        print("No templates with 5% rate found (already migrated or not created)")
    
    client.close()


async def init_integration_registry():
    """Initialize integration registry with Odoo"""
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.test_database
    
    print("\\n=== Initializing Integration Registry ===")
    
    # Get existing Odoo integration config
    odoo_intg = await db.integrations.find_one({"integration_type": "odoo"}, {"_id": 0})
    
    if odoo_intg:
        print("Found existing Odoo integration")
        
        # Create registry entry
        registry_entry = {
            "id": "odoo-erp",
            "name": "Odoo ERP",
            "type": "crm",
            "version": "19.0",
            "status": "active",
            "enabled": odoo_intg.get("enabled", False),
            "config": odoo_intg.get("config", {}),
            "capabilities": {
                "api_sync": True,
                "webhooks": True,
                "field_mapping": True,
                "realtime": True
            },
            "entities": ["account", "opportunity", "invoice", "activity", "user"],
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "migration_source": "integrations_collection"
        }
        
        # Add to system_config
        result = await db.system_config.update_one(
            {},
            {"$set": {"integrations": [registry_entry]}},
            upsert=True
        )
        
        print(f"✅ Integration registry initialized")
    else:
        print("No Odoo integration found to migrate")
    
    client.close()


async def cleanup_test_users():
    """Deactivate test users with inconsistent states"""
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.test_database
    
    print("\\n=== Cleaning Up Test Users ===")
    
    # Deactivate users with test_ emails
    result = await db.users.update_many(
        {"email": {"$regex": "^test_", "$options": "i"}},
        {
            "$set": {
                "is_active": False,
                "approval_status": "rejected",
                "rejection_reason": "Test user - automated cleanup",
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    print(f"✅ Deactivated {result.modified_count} test users")
    
    client.close()


async def verify_data_consistency():
    """Verify data lake and CQRS views are consistent"""
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.test_database
    
    print("\\n=== Verifying Data Consistency ===")
    
    # Check opportunities
    inactive_in_lake = await db.data_lake_serving.count_documents({
        "entity_type": "opportunity",
        "is_active": False
    })
    
    inactive_in_view = await db.opportunity_view.count_documents({
        "is_active": False
    })
    
    print(f"Inactive opportunities:")
    print(f"  data_lake_serving: {inactive_in_lake}")
    print(f"  opportunity_view: {inactive_in_view}")
    
    if inactive_in_lake != inactive_in_view:
        print(f"  ⚠️  INCONSISTENCY DETECTED!")
        print(f"  Run deletion sync to fix")
    else:
        print(f"  ✅ Consistent")
    
    # Check accounts
    inactive_accounts = await db.data_lake_serving.count_documents({
        "entity_type": "account",
        "is_active": False
    })
    
    print(f"\\nInactive accounts: {inactive_accounts}")
    
    client.close()


async def run_all_migrations():
    """Run all migration scripts"""
    print("="*60)
    print("RUNNING ALL MIGRATION SCRIPTS")
    print("="*60)
    
    await migrate_llm_config()
    await migrate_commission_base_rate()
    await init_integration_registry()
    await cleanup_test_users()
    await verify_data_consistency()
    
    print("\\n" + "="*60)
    print("MIGRATION COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(run_all_migrations())
