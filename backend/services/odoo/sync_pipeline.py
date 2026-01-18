"""
Odoo Sync Pipeline Service
Centralized service for all Odoo sync operations to eliminate code duplication
and standardize error handling, logging, and integration status updates.

This service consolidates sync logic that was previously scattered across route handlers.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from integrations.odoo.connector import OdooConnector

logger = logging.getLogger(__name__)


class SyncResult:
    """Standardized sync result object"""
    def __init__(self):
        self.synced = 0
        self.created = 0
        self.updated = 0
        self.deactivated = 0
        self.errors: List[str] = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "synced": self.synced,
            "created": self.created,
            "updated": self.updated,
            "deactivated": self.deactivated,
            "errors": self.errors
        }


class OdooSyncPipelineService:
    """
    Centralized Odoo sync pipeline service.
    
    Responsibilities:
    - Manage Odoo connector lifecycle
    - Execute sync operations for different entity types
    - Standardize error handling and recovery
    - Update integration status consistently
    - Log all sync activities to audit log
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.connector: Optional[OdooConnector] = None
    
    async def _get_odoo_config(self) -> Dict[str, Any]:
        """
        Get and validate Odoo configuration from database.
        
        Raises:
            RuntimeError: If Odoo is not configured or not enabled
        """
        intg = await self.db.integrations.find_one({"integration_type": "odoo"})
        
        if not intg or not intg.get("enabled"):
            raise RuntimeError("Odoo integration not enabled")
        
        config = intg.get("config", {})
        if not config.get("url"):
            raise RuntimeError("Odoo not configured - missing URL")
        
        return config
    
    async def _create_connector(self) -> OdooConnector:
        """Create and return Odoo connector with current config"""
        config = await self._get_odoo_config()
        return OdooConnector(config)
    
    async def _update_integration_status(
        self,
        status: str,
        error_message: Optional[str] = None,
        last_sync: Optional[datetime] = None
    ):
        """
        Update integration status in database.
        
        Args:
            status: One of 'success', 'partial', 'failed', 'running'
            error_message: Error message if status is 'failed' or 'partial'
            last_sync: Timestamp of last successful sync
        """
        update_doc = {
            "sync_status": status,
        }
        
        if error_message:
            update_doc["error_message"] = error_message
        
        if last_sync:
            update_doc["last_sync"] = last_sync
        
        await self.db.integrations.update_one(
            {"integration_type": "odoo"},
            {"$set": update_doc}
        )
    
    async def _log_sync_event(
        self,
        action: str,
        user_id: str,
        details: Dict[str, Any]
    ):
        """
        Log sync event to audit log.
        
        Args:
            action: Action name (e.g., 'sync_departments', 'sync_all')
            user_id: ID of user who triggered sync
            details: Sync result details
        """
        await self.db.audit_log.insert_one({
            "id": str(uuid.uuid4()),
            "action": action,
            "source": "odoo",
            "user_id": user_id,
            "details": details,
            "timestamp": datetime.now(timezone.utc),
        })
        
        logger.info(f"Odoo sync event logged: {action} by user {user_id}")
    
    async def sync_departments(self, user_id: str) -> SyncResult:
        """
        Sync departments from Odoo hr.department.
        
        Departments are SOURCE OF TRUTH from Odoo - CRM departments are read-only.
        
        Args:
            user_id: ID of user triggering the sync (for audit log)
        
        Returns:
            SyncResult with sync statistics
        """
        result = SyncResult()
        connector = None
        
        try:
            # Connect to Odoo
            connector = await self._create_connector()
            departments = await connector.fetch_departments()
            
            result.synced = len(departments)
            odoo_ids = []
            
            # Sync each department
            for dept in departments:
                odoo_id = dept['odoo_id']
                odoo_ids.append(odoo_id)
                
                try:
                    existing = await self.db.departments.find_one({"odoo_id": odoo_id})
                    
                    if existing:
                        # Update existing
                        await self.db.departments.update_one(
                            {"odoo_id": odoo_id},
                            {"$set": {
                                "name": dept['name'],
                                "complete_name": dept.get('complete_name'),
                                "parent_odoo_id": dept.get('parent_id'),
                                "manager_odoo_id": dept.get('manager_id'),
                                "active": dept.get('active', True),
                                "synced_at": datetime.now(timezone.utc),
                                "source": "odoo",
                            }}
                        )
                        result.updated += 1
                    else:
                        # Create new
                        await self.db.departments.insert_one({
                            "id": str(uuid.uuid4()),
                            "odoo_id": odoo_id,
                            "name": dept['name'],
                            "complete_name": dept.get('complete_name'),
                            "parent_odoo_id": dept.get('parent_id'),
                            "manager_odoo_id": dept.get('manager_id'),
                            "active": dept.get('active', True),
                            "source": "odoo",
                            "synced_at": datetime.now(timezone.utc),
                            "created_at": datetime.now(timezone.utc),
                        })
                        result.created += 1
                        
                except Exception as e:
                    error_msg = f"Failed to sync department {dept.get('name')}: {str(e)}"
                    result.errors.append(error_msg)
                    logger.error(error_msg)
            
            # Deactivate departments no longer in Odoo (soft delete)
            deactivate_result = await self.db.departments.update_many(
                {"source": "odoo", "odoo_id": {"$nin": odoo_ids}, "active": True},
                {"$set": {"active": False, "deactivated_at": datetime.now(timezone.utc)}}
            )
            result.deactivated = deactivate_result.modified_count
            
            # Log sync event
            await self._log_sync_event("sync_departments", user_id, result.to_dict())
            
            logger.info(f"Department sync completed: {result.synced} synced, {result.created} created, {result.updated} updated, {result.deactivated} deactivated")
            
        except Exception as e:
            error_msg = f"Failed to fetch from Odoo: {str(e)}"
            result.errors.append(error_msg)
            logger.error(f"Department sync failed: {e}")
            raise RuntimeError(error_msg)
        
        finally:
            if connector:
                await connector.disconnect()
        
        return result
    
    async def sync_users(self, user_id: str) -> SyncResult:
        """
        Sync users from Odoo hr.employee.
        
        Users are SOURCE OF TRUTH from Odoo - manual user creation is blocked.
        Users synced here are set to 'pending' approval status.
        
        Args:
            user_id: ID of user triggering the sync (for audit log)
        
        Returns:
            SyncResult with sync statistics
        """
        result = SyncResult()
        connector = None
        
        try:
            # Connect to Odoo
            connector = await self._create_connector()
            odoo_users = await connector.fetch_users()
            
            result.synced = len(odoo_users)
            odoo_ids = []
            
            # Sync each user
            for odoo_user in odoo_users:
                employee_id = odoo_user.get('odoo_employee_id')
                odoo_user_id = odoo_user.get('odoo_user_id')
                odoo_ids.append(employee_id or odoo_user_id)
                
                if not odoo_user.get('email'):
                    result.errors.append(f"Skipped user {odoo_user.get('name')}: no email")
                    continue
                
                try:
                    # Find by email ONLY (most reliable) - prevents cross-user data corruption
                    existing = await self.db.users.find_one({
                        "email": {"$regex": f"^{odoo_user['email']}$", "$options": "i"}
                    })
                    
                    # If not found by email, try by odoo_employee_id
                    if not existing and employee_id:
                        existing = await self.db.users.find_one({"odoo_employee_id": employee_id})
                    
                    # If still not found, try by odoo_user_id
                    if not existing and odoo_user_id:
                        existing = await self.db.users.find_one({"odoo_user_id": odoo_user_id})
                    
                    # Map department
                    dept = None
                    if odoo_user.get('department_odoo_id'):
                        dept = await self.db.departments.find_one({"odoo_id": odoo_user['department_odoo_id']})
                    
                    if existing:
                        # Verify this is the correct match (prevent data corruption)
                        existing_email = existing.get('email', '').lower()
                        odoo_email = odoo_user['email'].lower()
                        existing_odoo_id = existing.get('odoo_employee_id') or existing.get('odoo_user_id')
                        
                        if existing_email != odoo_email and existing_odoo_id != employee_id and existing_odoo_id != odoo_user_id:
                            # Different user - don't update, create new instead
                            logger.warning(f"Email mismatch: local={existing_email}, odoo={odoo_email}. Creating new user.")
                            existing = None
                    
                    if existing:
                        # Update existing user
                        update_data = {
                            "odoo_employee_id": employee_id,
                            "odoo_user_id": odoo_user_id,
                            "job_title": odoo_user.get('job_title'),
                            "phone": odoo_user.get('phone'),
                            "department_id": dept['id'] if dept else existing.get('department_id'),
                            "department_name": dept['name'] if dept else existing.get('department_name'),
                            "odoo_department_id": odoo_user.get('department_odoo_id'),
                            "odoo_department_name": odoo_user.get('department_name'),
                            "odoo_team_id": odoo_user.get('team_id'),
                            "odoo_team_name": odoo_user.get('team_name'),
                            "manager_odoo_id": odoo_user.get('manager_odoo_id'),
                            "odoo_matched": True,
                            "odoo_match_email": odoo_user['email'].lower(),
                            "updated_at": datetime.now(timezone.utc),
                        }
                        
                        # Only update name if not super_admin
                        if existing.get('role') != 'super_admin':
                            update_data["name"] = odoo_user.get('name')
                        
                        await self.db.users.update_one(
                            {"id": existing["id"]},
                            {"$set": update_data}
                        )
                        result.updated += 1
                        
                    else:
                        # Create new user (pending approval)
                        from services.auth.jwt_handler import hash_password
                        
                        new_user = {
                            "id": str(uuid.uuid4()),
                            "email": odoo_user['email'].lower(),
                            "password_hash": hash_password(f"temp_{uuid.uuid4().hex[:8]}"),
                            "name": odoo_user.get('name', 'Unknown'),
                            "role": None,
                            "job_title": odoo_user.get('job_title'),
                            "phone": odoo_user.get('phone'),
                            "department_id": dept['id'] if dept else None,
                            "department_name": dept['name'] if dept else None,
                            "odoo_employee_id": employee_id,
                            "odoo_user_id": odoo_user_id,
                            "odoo_department_id": odoo_user.get('department_odoo_id'),
                            "odoo_department_name": odoo_user.get('department_name'),
                            "odoo_team_id": odoo_user.get('team_id'),
                            "odoo_team_name": odoo_user.get('team_name'),
                            "manager_odoo_id": odoo_user.get('manager_odoo_id'),
                            "is_active": False,
                            "is_approved": False,
                            "approval_status": "pending",
                            "odoo_matched": True,
                            "odoo_match_email": odoo_user['email'].lower(),
                            "created_at": datetime.now(timezone.utc),
                            "updated_at": datetime.now(timezone.utc),
                        }
                        
                        await self.db.users.insert_one(new_user)
                        result.created += 1
                        
                except Exception as e:
                    error_msg = f"Failed to sync user {odoo_user.get('name')}: {str(e)}"
                    result.errors.append(error_msg)
                    logger.error(error_msg)
            
            # Deactivate users no longer in Odoo (soft delete)
            deactivate_result = await self.db.users.update_many(
                {
                    "odoo_matched": True,
                    "$or": [
                        {"odoo_employee_id": {"$nin": odoo_ids}},
                        {"odoo_user_id": {"$nin": odoo_ids}}
                    ],
                    "is_approved": True
                },
                {"$set": {"is_approved": False, "approval_status": "deactivated", "deactivated_at": datetime.now(timezone.utc)}}
            )
            result.deactivated = deactivate_result.modified_count
            
            # Log sync event
            await self._log_sync_event("sync_users", user_id, result.to_dict())
            
            logger.info(f"User sync completed: {result.synced} synced, {result.created} created, {result.updated} updated, {result.deactivated} deactivated")
            
        except Exception as e:
            error_msg = f"Failed to fetch users from Odoo: {str(e)}"
            result.errors.append(error_msg)
            logger.error(f"User sync failed: {e}")
            raise RuntimeError(error_msg)
        
        finally:
            if connector:
                await connector.disconnect()
        
        return result
    
    async def sync_data_lake(self, user_id: str) -> Dict[str, Any]:
        """
        Sync all data lake entities from Odoo.
        
        Syncs: Accounts, Opportunities, Invoices, Users/Employees to data_lake_serving.
        
        Args:
            user_id: ID of user triggering the sync (for audit log)
        
        Returns:
            Dict with sync statistics and errors
        """
        import time
        start_time = time.time()
        
        synced_entities = {}
        errors = []
        connector = None
        
        try:
            # Connect to Odoo
            connector = await self._create_connector()
            
            # Update status to running
            await self._update_integration_status("running")
            
            # 1. Sync Accounts (res.partner)
            try:
                accounts = await connector.fetch_accounts()
                account_odoo_ids = [acc.get('id') for acc in accounts if acc.get('id')]
                
                for acc in accounts:
                    serving_doc = {
                        "entity_type": "account",
                        "serving_id": f"odoo_account_{acc.get('id')}",
                        "source": "odoo",
                        "last_aggregated": datetime.now(timezone.utc).isoformat(),
                        "data": acc,
                        "is_active": True  # Mark as active
                    }
                    await self.db.data_lake_serving.update_one(
                        {"serving_id": serving_doc["serving_id"]},
                        {"$set": serving_doc},
                        upsert=True
                    )
                synced_entities["accounts"] = len(accounts)
                
                # Soft-delete accounts no longer in Odoo
                delete_result = await self.db.data_lake_serving.update_many(
                    {
                        "entity_type": "account",
                        "source": "odoo",
                        "is_active": True,
                        "data.id": {"$nin": account_odoo_ids}
                    },
                    {
                        "$set": {
                            "is_active": False,
                            "deleted_at": datetime.now(timezone.utc).isoformat()
                        }
                    }
                )
                deleted_accounts = delete_result.modified_count
                
                logger.info(f"Synced {len(accounts)} accounts, soft-deleted {deleted_accounts}")
            except Exception as e:
                error_msg = f"Account sync error: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
            
            # 2. Sync Opportunities (crm.lead)
            try:
                opportunities = await connector.fetch_opportunities()
                opp_odoo_ids = [opp.get('id') for opp in opportunities if opp.get('id')]
                
                for opp in opportunities:
                    serving_doc = {
                        "entity_type": "opportunity",
                        "serving_id": f"odoo_opportunity_{opp.get('id')}",
                        "source": "odoo",
                        "last_aggregated": datetime.now(timezone.utc).isoformat(),
                        "data": opp,
                        "is_active": True  # Mark as active
                    }
                    await self.db.data_lake_serving.update_one(
                        {"serving_id": serving_doc["serving_id"]},
                        {"$set": serving_doc},
                        upsert=True
                    )
                synced_entities["opportunities"] = len(opportunities)
                
                # Soft-delete opportunities no longer in Odoo
                delete_result = await self.db.data_lake_serving.update_many(
                    {
                        "entity_type": "opportunity",
                        "source": "odoo",
                        "is_active": True,
                        "data.id": {"$nin": opp_odoo_ids}
                    },
                    {
                        "$set": {
                            "is_active": False,
                            "deleted_at": datetime.now(timezone.utc).isoformat()
                        }
                    }
                )
                deleted_opps = delete_result.modified_count
                
                logger.info(f"Synced {len(opportunities)} opportunities, soft-deleted {deleted_opps}")
            except Exception as e:
                error_msg = f"Opportunity sync error: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
            
            # 3. Sync Invoices (account.move)
            try:
                invoices = await connector.fetch_invoices()
                invoice_odoo_ids = [inv.get('id') for inv in invoices if inv.get('id')]
                
                for inv in invoices:
                    serving_doc = {
                        "entity_type": "invoice",
                        "serving_id": f"odoo_invoice_{inv.get('id')}",
                        "source": "odoo",
                        "last_aggregated": datetime.now(timezone.utc).isoformat(),
                        "data": inv,
                        "is_active": True  # Mark as active
                    }
                    await self.db.data_lake_serving.update_one(
                        {"serving_id": serving_doc["serving_id"]},
                        {"$set": serving_doc},
                        upsert=True
                    )
                synced_entities["invoices"] = len(invoices)
                
                # Soft-delete invoices no longer in Odoo
                delete_result = await self.db.data_lake_serving.update_many(
                    {
                        "entity_type": "invoice",
                        "source": "odoo",
                        "is_active": True,
                        "data.id": {"$nin": invoice_odoo_ids}
                    },
                    {
                        "$set": {
                            "is_active": False,
                            "deleted_at": datetime.now(timezone.utc).isoformat()
                        }
                    }
                )
                deleted_invoices = delete_result.modified_count
                
                logger.info(f"Synced {len(invoices)} invoices, soft-deleted {deleted_invoices}")
            except Exception as e:
                error_msg = f"Invoice sync error: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)

            
            # 5. Sync Chatter Messages (Communication History)
            try:
                messages = await connector.fetch_messages(res_model='crm.lead')
                message_odoo_ids = [msg.get('id') for msg in messages if msg.get('id')]
                
                for msg in messages:
                    serving_doc = {
                        "entity_type": "message",
                        "serving_id": f"odoo_message_{msg.get('id')}",
                        "source": "odoo",
                        "last_aggregated": datetime.now(timezone.utc).isoformat(),
                        "data": msg,
                        "is_active": True
                    }
                    await self.db.data_lake_serving.update_one(
                        {"serving_id": serving_doc["serving_id"]},
                        {"$set": serving_doc},
                        upsert=True
                    )
                synced_entities["messages"] = len(messages)
                
                # Soft-delete messages no longer in Odoo
                delete_result = await self.db.data_lake_serving.update_many(
                    {
                        "entity_type": "message",
                        "source": "odoo",
                        "is_active": True,
                        "data.id": {"$nin": message_odoo_ids}
                    },
                    {
                        "$set": {
                            "is_active": False,
                            "deleted_at": datetime.now(timezone.utc).isoformat()
                        }
                    }
                )
                deleted_messages = delete_result.modified_count
                
                logger.info(f"Synced {len(messages)} chatter messages, soft-deleted {deleted_messages}")
            except Exception as e:
                error_msg = f"Message sync error: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)

            
            # 4. Sync Users/Employees (for user matching)
            try:
                users = await connector.fetch_users()
                for usr in users:
                    serving_doc = {
                        "entity_type": "user",
                        "serving_id": f"odoo_user_{usr.get('odoo_user_id', usr.get('id'))}",
                        "source": "odoo",
                        "last_aggregated": datetime.now(timezone.utc).isoformat(),
                        "data": {
                            "id": usr.get("odoo_user_id", usr.get("id")),
                            "name": usr.get("name"),
                            "email": usr.get("email", "").lower(),
                            "login": usr.get("login", "").lower(),
                            "work_email": usr.get("work_email", "").lower(),
                            "job_title": usr.get("job_title"),
                            "department_id": usr.get("department_odoo_id"),
                            "department_name": usr.get("department_name"),
                            "team_id": usr.get("team_id"),
                            "team_name": usr.get("team_name"),
                            "active": usr.get("active", True),
                        }
                    }
                    await self.db.data_lake_serving.update_one(
                        {"serving_id": serving_doc["serving_id"]},
                        {"$set": serving_doc},
                        upsert=True
                    )
                synced_entities["users"] = len(users)
                logger.info(f"Synced {len(users)} users to data lake")
            except Exception as e:
                error_msg = f"User sync error: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
            
            # Update integration status
            status = "success" if not errors else "partial"
            error_message = "; ".join(errors) if errors else None
            await self._update_integration_status(
                status,
                error_message=error_message,
                last_sync=datetime.now(timezone.utc)
            )
            
            duration = time.time() - start_time
            
            # Log sync event
            await self._log_sync_event("full_odoo_sync", user_id, {
                "synced_entities": synced_entities,
                "errors": errors,
                "duration_seconds": round(duration, 2)
            })
            
            logger.info(f"Data lake sync completed in {duration:.2f}s: {sum(synced_entities.values())} total records")
            
            # CRITICAL: Sync deletions to CQRS projections
            logger.info("Syncing deletions to CQRS views...")
            from services.deletion_sync import sync_deletions_after_odoo_sync
            
            deletion_results = await sync_deletions_after_odoo_sync(self.db)
            
            logger.info(f"Deletion sync complete: {deletion_results.get('total_synced', 0)} records updated")
            
            return {
                "success": len(errors) == 0,
                "message": f"Sync completed. Synced {sum(synced_entities.values())} records." if not errors else f"Sync completed with {len(errors)} error(s)",
                "synced_entities": synced_entities,
                "deletion_sync": deletion_results,  # NEW: Include deletion sync results
                "errors": errors,
                "duration_seconds": round(duration, 2)
            }
            
        except Exception as e:
            error_msg = f"Connection error: {str(e)}"
            errors.append(error_msg)
            logger.error(f"Data lake sync failed: {e}")
            
            # Update integration status to failed
            await self._update_integration_status("failed", error_message=str(e))
            
            raise RuntimeError(error_msg)
        
        finally:
            if connector:
                await connector.disconnect()
