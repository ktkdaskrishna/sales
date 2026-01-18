"""
Admin Routes
API endpoints for Super Admin functionality
- User Management
- Role & Permission Management
- Department Management
- System Configuration
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
import uuid
import logging

from models.rbac import (
    RoleCreateRequest, RoleUpdateRequest,
    UserCreateRequest, UserUpdateRequest,
    DepartmentCreateRequest
)
from services.rbac.service import RBACService
from services.auth.jwt_handler import get_current_user_from_token, hash_password
from core.database import Database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


# ===================== MIDDLEWARE =====================

async def require_super_admin(token_data: dict = Depends(get_current_user_from_token)):
    """Require super admin privileges"""
    db = Database.get_db()
    user = await db.users.find_one({"id": token_data["id"]}, {"is_super_admin": 1})
    
    if not user or not user.get("is_super_admin"):
        raise HTTPException(status_code=403, detail="Super admin access required")
    
    return token_data


# ===================== PERMISSIONS =====================

@router.get("/permissions")
async def get_all_permissions(token_data: dict = Depends(require_super_admin)):
    """Get all available permissions"""
    db = Database.get_db()
    rbac = RBACService(db)
    permissions = await rbac.get_all_permissions()
    
    # Group by module
    grouped = {}
    for perm in permissions:
        module = perm.get("module", "other")
        if module not in grouped:
            grouped[module] = []
        grouped[module].append(perm)
    
    return {"permissions": permissions, "grouped": grouped}


class PermissionCreateRequest(BaseModel):
    code: str
    name: str
    module: str
    resource: str
    action: str
    description: Optional[str] = None


@router.post("/permissions")
async def create_permission(
    request: PermissionCreateRequest,
    token_data: dict = Depends(require_super_admin)
):
    """Create a new custom permission"""
    db = Database.get_db()
    
    # Check if code exists
    existing = await db.permissions.find_one({"code": request.code})
    if existing:
        raise HTTPException(status_code=400, detail="Permission code already exists")
    
    now = datetime.now(timezone.utc)
    permission = {
        "id": str(__import__("uuid").uuid4()),
        "code": request.code,
        "name": request.name,
        "module": request.module,
        "resource": request.resource,
        "action": request.action,
        "description": request.description,
        "is_active": True,
        "is_custom": True,  # Mark as custom permission
        "created_at": now,
        "created_by": token_data["id"]
    }
    
    await db.permissions.insert_one(permission)
    del permission["_id"]
    return {"message": "Permission created", "permission": permission}


@router.delete("/permissions/{perm_id}")
async def delete_permission(
    perm_id: str,
    token_data: dict = Depends(require_super_admin)
):
    """Delete a custom permission"""
    db = Database.get_db()
    
    perm = await db.permissions.find_one({"id": perm_id})
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")
    
    if not perm.get("is_custom"):
        raise HTTPException(status_code=400, detail="Cannot delete system permissions")
    
    await db.permissions.delete_one({"id": perm_id})
    return {"message": "Permission deleted"}


@router.get("/permissions/{module}")
async def get_permissions_by_module(
    module: str,
    token_data: dict = Depends(require_super_admin)
):
    """Get permissions for a specific module"""
    db = Database.get_db()
    rbac = RBACService(db)
    return await rbac.get_permissions_by_module(module)


# ===================== ROLES =====================

@router.get("/roles")
async def get_all_roles(token_data: dict = Depends(require_super_admin)):
    """Get all roles with their permissions"""
    db = Database.get_db()
    rbac = RBACService(db)
    roles = await rbac.get_all_roles()
    return {"roles": roles, "count": len(roles)}


@router.get("/roles/{role_id}")
async def get_role(role_id: str, token_data: dict = Depends(require_super_admin)):
    """Get a specific role"""
    db = Database.get_db()
    rbac = RBACService(db)
    role = await rbac.get_role_by_id(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.post("/roles")
async def create_role(
    request: RoleCreateRequest,
    token_data: dict = Depends(require_super_admin)
):
    """Create a new role"""
    db = Database.get_db()
    rbac = RBACService(db)
    
    # Check if code exists
    existing = await rbac.get_role_by_code(request.code)
    if existing:
        raise HTTPException(status_code=400, detail="Role code already exists")
    
    role = await rbac.create_role(request, token_data["id"])
    return {"message": "Role created", "role": role}


@router.put("/roles/{role_id}")
async def update_role(
    role_id: str,
    request: RoleUpdateRequest,
    token_data: dict = Depends(require_super_admin)
):
    """Update a role"""
    db = Database.get_db()
    rbac = RBACService(db)
    
    role = await rbac.get_role_by_id(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    success = await rbac.update_role(role_id, updates)
    return {"message": "Role updated" if success else "No changes made"}


@router.delete("/roles/{role_id}")
async def delete_role(role_id: str, token_data: dict = Depends(require_super_admin)):
    """Delete a role"""
    db = Database.get_db()
    rbac = RBACService(db)
    
    role = await rbac.get_role_by_id(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    if role.get("is_system"):
        raise HTTPException(status_code=400, detail="Cannot delete system roles")
    
    # Check if any users have this role
    user_count = await db.users.count_documents({"role_id": role_id})
    if user_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete role: {user_count} users have this role"
        )
    
    success = await rbac.delete_role(role_id)
    return {"message": "Role deleted" if success else "Failed to delete role"}


# ===================== DEPARTMENTS =====================

@router.get("/departments")
async def get_all_departments(token_data: dict = Depends(require_super_admin)):
    """Get all departments"""
    db = Database.get_db()
    rbac = RBACService(db)
    departments = await rbac.get_all_departments()
    return {"departments": departments, "count": len(departments)}


@router.post("/departments")
async def create_department(
    request: DepartmentCreateRequest,
    token_data: dict = Depends(require_super_admin)
):
    """Create a new department"""
    db = Database.get_db()
    
    # Check if code exists
    existing = await db.departments.find_one({"code": request.code})
    if existing:
        raise HTTPException(status_code=400, detail="Department code already exists")
    
    now = datetime.now(timezone.utc)
    department = {
        "id": str(__import__("uuid").uuid4()),
        "code": request.code,
        "name": request.name,
        "description": request.description,
        "parent_id": request.parent_id,
        "manager_id": request.manager_id,
        "is_active": True,
        "created_at": now
    }
    
    await db.departments.insert_one(department)
    del department["_id"]
    return {"message": "Department created", "department": department}


@router.put("/departments/{dept_id}")
async def update_department(
    dept_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    manager_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    token_data: dict = Depends(require_super_admin)
):
    """Update a department"""
    db = Database.get_db()
    
    updates = {}
    if name is not None:
        updates["name"] = name
    if description is not None:
        updates["description"] = description
    if manager_id is not None:
        updates["manager_id"] = manager_id
    if is_active is not None:
        updates["is_active"] = is_active
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    result = await db.departments.update_one({"id": dept_id}, {"$set": updates})
    return {"message": "Department updated" if result.modified_count else "No changes made"}


# ===================== USER MANAGEMENT =====================

@router.get("/users")
async def get_all_users(
    role_id: Optional[str] = None,
    department_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    token_data: dict = Depends(require_super_admin)
):
    """Get all users with optional filters"""
    db = Database.get_db()
    rbac = RBACService(db)
    
    query = {}
    if role_id:
        query["role_id"] = role_id
    if department_id:
        query["department_id"] = department_id
    if is_active is not None:
        query["is_active"] = is_active
    
    cursor = db.users.find(query, {"_id": 0, "password_hash": 0, "ms_access_token": 0})
    users = await cursor.to_list(500)
    
    # Resolve role and department names
    roles = {r["id"]: r for r in await rbac.get_all_roles()}
    depts = {d["id"]: d for d in await rbac.get_all_departments()}
    
    for user in users:
        if user.get("role_id") and user["role_id"] in roles:
            user["role_name"] = roles[user["role_id"]].get("name")
            user["role_code"] = roles[user["role_id"]].get("code")
        if user.get("department_id") and user["department_id"] in depts:
            user["department_name"] = depts[user["department_id"]].get("name")
    
    return {"users": users, "count": len(users)}


@router.get("/users/{user_id}")
async def get_user(user_id: str, token_data: dict = Depends(require_super_admin)):
    """Get a specific user with resolved role"""
    db = Database.get_db()
    rbac = RBACService(db)
    
    user_with_role = await rbac.get_user_with_role(user_id)
    if not user_with_role:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user_with_role.model_dump()


@router.post("/users")
async def create_user(
    request: UserCreateRequest,
    token_data: dict = Depends(require_super_admin)
):
    """Create a new user"""
    db = Database.get_db()
    
    # Check if email exists
    existing = await db.users.find_one({"email": request.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Validate role if provided
    if request.role_id:
        role = await db.roles.find_one({"id": request.role_id})
        if not role:
            raise HTTPException(status_code=400, detail="Invalid role_id")
    
    # Validate department if provided
    if request.department_id:
        dept = await db.departments.find_one({"id": request.department_id})
        if not dept:
            raise HTTPException(status_code=400, detail="Invalid department_id")
    
    now = datetime.now(timezone.utc)
    user = {
        "id": str(__import__("uuid").uuid4()),
        "email": request.email,
        "name": request.name,
        "password_hash": hash_password(request.password) if request.password else "",
        "role_id": request.role_id,
        "department_id": request.department_id,
        "is_super_admin": request.is_super_admin,
        "is_active": True,
        "job_title": request.job_title,
        "auth_provider": "local",
        "created_at": now,
        "updated_at": now
    }
    
    await db.users.insert_one(user)
    
    # Return without sensitive data
    del user["_id"]
    del user["password_hash"]
    return {"message": "User created", "user": user}


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    request: UserUpdateRequest,
    token_data: dict = Depends(require_super_admin)
):
    """Update a user"""
    db = Database.get_db()
    
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    # Validate role if being updated
    if "role_id" in updates and updates["role_id"]:
        role = await db.roles.find_one({"id": updates["role_id"]})
        if not role:
            raise HTTPException(status_code=400, detail="Invalid role_id")
    
    # Validate department if being updated
    if "department_id" in updates and updates["department_id"]:
        dept = await db.departments.find_one({"id": updates["department_id"]})
        if not dept:
            raise HTTPException(status_code=400, detail="Invalid department_id")
    
    updates["updated_at"] = datetime.now(timezone.utc)
    
    result = await db.users.update_one({"id": user_id}, {"$set": updates})
    return {"message": "User updated" if result.modified_count else "No changes made"}


@router.post("/users/{user_id}/approve")
async def approve_user(
    user_id: str,
    token_data: dict = Depends(require_super_admin)
):
    """
    Approve a pending user and enrich with Odoo data.
    
    This is the KEY integration point:
    1. User logged in via Azure AD (has email, name from Microsoft)
    2. On approval, we match email with Odoo users/employees
    3. Enrich user with Odoo: department, salesperson_id, team_id
    4. This enables Odoo-based access control (users see only their data)
    """
    db = Database.get_db()
    
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("approval_status") != "pending":
        raise HTTPException(status_code=400, detail="User is not in pending state")
    
    user_email = user.get("email", "").lower()
    odoo_enrichment = {}
    odoo_match_status = "not_matched"
    
    # === ODOO ENRICHMENT: Match user email with Odoo ===
    try:
        # 1. Check if we have Odoo users synced in data_lake_serving
        odoo_user_doc = await db.data_lake_serving.find_one({
            "entity_type": "user",
            "$or": [
                {"data.email": {"$regex": f"^{user_email}$", "$options": "i"}},
                {"data.login": {"$regex": f"^{user_email}$", "$options": "i"}},
                {"data.work_email": {"$regex": f"^{user_email}$", "$options": "i"}}
            ]
        })
        
        if odoo_user_doc:
            odoo_data = odoo_user_doc.get("data", {})
            odoo_enrichment = {
                "odoo_user_id": odoo_data.get("id"),
                "odoo_employee_id": odoo_data.get("employee_id"),
                "odoo_department_id": odoo_data.get("department_id"),
                "odoo_department_name": odoo_data.get("department_name"),
                "odoo_team_id": odoo_data.get("team_id"),
                "odoo_team_name": odoo_data.get("team_name"),
                "odoo_job_title": odoo_data.get("job_title"),
                "odoo_salesperson_name": odoo_data.get("name"),  # The salesperson name used in opportunities
                "odoo_matched": True,
                "odoo_match_email": user_email,
            }
            odoo_match_status = "matched_from_sync"
        
        # 2. Also check synced users collection (from /sync/users endpoint)
        if not odoo_enrichment:
            synced_user = await db.users.find_one({
                "source": "odoo",
                "email": {"$regex": f"^{user_email}$", "$options": "i"}
            })
            if synced_user:
                odoo_enrichment = {
                    "odoo_user_id": synced_user.get("odoo_user_id"),
                    "odoo_employee_id": synced_user.get("odoo_employee_id"),
                    "odoo_department_id": synced_user.get("department_id"),
                    "odoo_department_name": synced_user.get("department_name"),
                    "odoo_job_title": synced_user.get("job_title"),
                    "odoo_matched": True,
                    "odoo_match_email": user_email,
                }
                odoo_match_status = "matched_from_users"
        
        # 3. Check if user's email appears as salesperson in any opportunity
        if not odoo_enrichment:
            opp_with_user = await db.data_lake_serving.find_one({
                "entity_type": "opportunity",
                "$or": [
                    {"data.salesperson_name": {"$regex": user_email, "$options": "i"}},
                    {"data.user_id.1": {"$regex": user_email, "$options": "i"}}  # Odoo often stores [id, name]
                ]
            })
            if opp_with_user:
                opp_data = opp_with_user.get("data", {})
                odoo_enrichment = {
                    "odoo_salesperson_name": user_email,  # Use email as salesperson identifier
                    "odoo_team_id": opp_data.get("team_id"),
                    "odoo_team_name": opp_data.get("team_name"),
                    "odoo_matched": True,
                    "odoo_match_email": user_email,
                }
                odoo_match_status = "matched_from_opportunities"
        
        # 4. Check synced departments and match by department name from Azure AD
        if not odoo_enrichment.get("odoo_department_id") and user.get("ad_department"):
            dept = await db.departments.find_one({
                "name": {"$regex": user.get("ad_department"), "$options": "i"},
                "source": "odoo"
            })
            if dept:
                odoo_enrichment["department_id"] = dept.get("id")
                odoo_enrichment["odoo_department_id"] = dept.get("odoo_id")
                odoo_enrichment["odoo_department_name"] = dept.get("name")
                if not odoo_enrichment.get("odoo_matched"):
                    odoo_match_status = "matched_department_only"
    
    except Exception as e:
        logger.error(f"Error enriching user from Odoo: {e}")
        odoo_match_status = f"error: {str(e)}"
    
    # CRITICAL: Enforce workflow - Role and Department required before approval
    
    # Check if user has a role assigned
    user_role = user.get("role")
    if not user_role or user_role == "pending":
        raise HTTPException(
            status_code=400,
            detail="Cannot approve user without a role. Please assign a role first using PUT /admin/users/{user_id}"
        )
    
    # Check if user has a department (recommended, warning only)
    if not user.get("department_id") and not odoo_enrichment.get("odoo_department_id"):
        logger.warning(f"Approving user {user_email} without department assignment")
        # Don't block approval, but log warning
    
    # Build update payload
    update_data = {
        "approval_status": "approved",
        "is_active": True,  # IMPORTANT: Activate user on approval
        "updated_at": datetime.now(timezone.utc),
        "odoo_match_status": odoo_match_status,
        **odoo_enrichment
    }
    
    await db.users.update_one({"id": user_id}, {"$set": update_data})
    
    # Log the enrichment for audit
    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "action": "user_approved",
        "user_id": user_id,
        "approved_by": token_data["id"],
        "odoo_match_status": odoo_match_status,
        "odoo_enrichment": odoo_enrichment,
        "timestamp": datetime.now(timezone.utc),
    })
    
    return {
        "message": "User approved",
        "user_email": user.get("email"),
        "odoo_match_status": odoo_match_status,
        "odoo_enrichment": odoo_enrichment if odoo_enrichment else "No Odoo match found - user will need manual assignment"
    }


@router.post("/users/{user_id}/reject")
async def reject_user(
    user_id: str,
    reason: Optional[str] = None,
    token_data: dict = Depends(require_super_admin)
):
    """Reject a pending user"""
    db = Database.get_db()
    
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("approval_status") != "pending":
        raise HTTPException(status_code=400, detail="User is not in pending state")
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {
            "approval_status": "rejected",
            "rejection_reason": reason,
            "is_active": False,
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    return {
        "message": "User rejected",
        "user_email": user.get("email")
    }




@router.patch("/users/{user_id}/assign-role")
async def assign_role_to_user(
    user_id: str,
    role_id: str,
    department_id: Optional[str] = None,
    token_data: dict = Depends(require_super_admin)
):
    """
    Assign role and optionally department to a pending user.
    This must be done BEFORE approval.
    
    Workflow: Role Assignment → Department Assignment → Approval → Active
    """
    db = Database.get_db()
    
    # Get user
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify role exists
    role = await db.roles.find_one({"id": role_id})
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Verify department if provided
    if department_id:
        dept = await db.departments.find_one({"id": department_id})
        if not dept:
            raise HTTPException(status_code=404, detail="Department not found")
    
    # Update user
    update_data = {
        "role": role.get("code"),
        "role_id": role_id,
        "role_name": role.get("name"),
        "updated_at": datetime.now(timezone.utc)
    }
    
    if department_id:
        dept = await db.departments.find_one({"id": department_id})
        update_data["department_id"] = department_id
        update_data["department_name"] = dept.get("name") if dept else None
    
    await db.users.update_one({"id": user_id}, {"$set": update_data})
    
    logger.info(f"Assigned role {role.get('name')} to user {user.get('email')}")
    
    return {
        "message": "Role assigned successfully",
        "user_id": user_id,
        "role": role.get("name"),
        "department": dept.get("name") if department_id and dept else None,
        "next_step": "User can now be approved"
    }


@router.post("/users/cleanup-inconsistent")
async def cleanup_inconsistent_users(
    token_data: dict = Depends(require_super_admin)
):
    """
    Cleanup users with inconsistent states.
    
    Fixes:
    - Users with "No Role" + "Approved" → Set to pending
    - Users with "Approved" + "Inactive" → Set is_active=True
    - TEST users → Deactivate if not needed
    """
    db = Database.get_db()
    
    stats = {
        "no_role_approved": 0,
        "approved_inactive": 0,
        "test_users_deactivated": 0
    }
    
    # Fix 1: Users approved without role → Set back to pending
    result1 = await db.users.update_many(
        {
            "approval_status": "approved",
            "$or": [
                {"role": {"$exists": False}},
                {"role": None},
                {"role": "pending"}
            ]
        },
        {
            "$set": {
                "approval_status": "pending",
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    stats["no_role_approved"] = result1.modified_count
    
    # Fix 2: Users approved but inactive → Activate them
    result2 = await db.users.update_many(
        {
            "approval_status": "approved",
            "is_active": False
        },
        {
            "$set": {
                "is_active": True,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    stats["approved_inactive"] = result2.modified_count
    
    # Fix 3: TEST users → Deactivate
    result3 = await db.users.update_many(
        {
            "email": {"$regex": "^test_", "$options": "i"},
            "is_active": True
        },
        {
            "$set": {
                "is_active": False,
                "approval_status": "rejected",
                "rejection_reason": "Test user - automated cleanup",
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    stats["test_users_deactivated"] = result3.modified_count
    
    logger.info(f"User cleanup complete: {stats}")
    
    return {
        "message": "User cleanup complete",
        "statistics": stats,
        "actions_taken": [
            f"Set {stats['no_role_approved']} users without roles back to pending",
            f"Activated {stats['approved_inactive']} approved users",
            f"Deactivated {stats['test_users_deactivated']} test users"
        ]
    }

        "user_id": user_id,
        "role": role.get("name"),
        "department": dept.get("name") if department_id and dept else None,
        "next_step": "User can now be approved"
    }


@router.post("/users/{user_id}/relink")
async def relink_user_to_odoo(
    user_id: str,
    force_email: Optional[str] = None,
    token_data: dict = Depends(require_super_admin)
):
    """
    Re-attempt to link a user to their Odoo profile.
    This can be called if:
    - Odoo sync has completed after user approval
    - User was approved before Odoo data was available
    - Email matching needs to be re-attempted
    
    Optionally provide force_email to override the user's email for matching
    """
    db = Database.get_db()
    
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("approval_status") != "approved":
        raise HTTPException(status_code=400, detail="Only approved users can be re-linked")
    
    user_email = (force_email or user.get("email", "")).lower()
    odoo_enrichment = {}
    odoo_match_status = "not_matched"
    
    try:
        # 1. Check data_lake_serving for users
        odoo_user_doc = await db.data_lake_serving.find_one({
            "entity_type": "user",
            "$or": [
                {"data.email": {"$regex": f"^{user_email}$", "$options": "i"}},
                {"data.login": {"$regex": f"^{user_email}$", "$options": "i"}},
                {"data.work_email": {"$regex": f"^{user_email}$", "$options": "i"}}
            ]
        })
        
        if odoo_user_doc:
            odoo_data = odoo_user_doc.get("data", {})
            odoo_enrichment = {
                "odoo_user_id": odoo_data.get("odoo_user_id") or odoo_data.get("id"),
                "odoo_employee_id": odoo_data.get("odoo_employee_id") or odoo_data.get("employee_id"),
                "odoo_department_id": odoo_data.get("department_odoo_id") or odoo_data.get("department_id"),
                "odoo_department_name": odoo_data.get("department_name"),
                "odoo_team_id": odoo_data.get("team_id"),
                "odoo_team_name": odoo_data.get("team_name"),
                "odoo_job_title": odoo_data.get("job_title"),
                "odoo_salesperson_name": odoo_data.get("name"),
                "odoo_matched": True,
                "odoo_match_email": user_email,
            }
            odoo_match_status = "matched_from_sync"
        
        # 2. Check by name if email didn't match
        if not odoo_enrichment and user.get("name"):
            user_name = user.get("name")
            odoo_user_by_name = await db.data_lake_serving.find_one({
                "entity_type": "user",
                "data.name": {"$regex": f"^{user_name}$", "$options": "i"}
            })
            if odoo_user_by_name:
                odoo_data = odoo_user_by_name.get("data", {})
                odoo_enrichment = {
                    "odoo_user_id": odoo_data.get("odoo_user_id") or odoo_data.get("id"),
                    "odoo_employee_id": odoo_data.get("odoo_employee_id"),
                    "odoo_department_id": odoo_data.get("department_odoo_id"),
                    "odoo_department_name": odoo_data.get("department_name"),
                    "odoo_job_title": odoo_data.get("job_title"),
                    "odoo_salesperson_name": odoo_data.get("name"),
                    "odoo_matched": True,
                    "odoo_match_email": odoo_data.get("email") or odoo_data.get("work_email"),
                }
                odoo_match_status = "matched_by_name"
        
        # 3. Check by salesperson in opportunities
        if not odoo_enrichment:
            opp = await db.data_lake_serving.find_one({
                "entity_type": "opportunity",
                "$or": [
                    {"data.salesperson_name": {"$regex": user_email, "$options": "i"}},
                    {"data.salesperson_name": {"$regex": user.get("name", "NOMATCH"), "$options": "i"}}
                ]
            })
            if opp:
                opp_data = opp.get("data", {})
                odoo_enrichment = {
                    "odoo_salesperson_name": opp_data.get("salesperson_name") or user.get("name"),
                    "odoo_team_id": opp_data.get("team_id"),
                    "odoo_team_name": opp_data.get("team_name"),
                    "odoo_matched": True,
                    "odoo_match_email": user_email,
                }
                odoo_match_status = "matched_from_opportunities"
        
    except Exception as e:
        logger.error(f"Error re-linking user to Odoo: {e}")
        odoo_match_status = f"error: {str(e)}"
    
    if odoo_enrichment:
        # Update user with Odoo data
        update_data = {
            "updated_at": datetime.now(timezone.utc),
            "odoo_match_status": odoo_match_status,
            **odoo_enrichment
        }
        await db.users.update_one({"id": user_id}, {"$set": update_data})
        
        # Log the re-link
        await db.audit_log.insert_one({
            "id": str(uuid.uuid4()),
            "action": "user_relinked",
            "user_id": user_id,
            "relinked_by": token_data["id"],
            "odoo_match_status": odoo_match_status,
            "odoo_enrichment": odoo_enrichment,
            "timestamp": datetime.now(timezone.utc),
        })
        
        return {
            "message": "User re-linked successfully",
            "user_email": user.get("email"),
            "odoo_match_status": odoo_match_status,
            "odoo_enrichment": odoo_enrichment
        }
    else:
        return {
            "message": "No Odoo match found",
            "user_email": user.get("email"),
            "odoo_match_status": odoo_match_status,
            "suggestion": "Ensure Odoo users are synced first, or check the user's email matches their Odoo work email"
        }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str, 
    permanent: bool = False,
    token_data: dict = Depends(require_super_admin)
):
    """
    Delete a user.
    - Default: Soft delete (sets is_active=False)
    - With ?permanent=true: Hard delete (removes from database completely)
    """
    db = Database.get_db()
    
    if user_id == token_data["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if permanent:
        # Hard delete - completely remove from database
        result = await db.users.delete_one({"id": user_id})
        
        # Log the deletion
        await db.audit_log.insert_one({
            "id": str(uuid.uuid4()),
            "action": "user_hard_deleted",
            "user_id": user_id,
            "user_email": user.get("email"),
            "deleted_by": token_data["id"],
            "timestamp": datetime.now(timezone.utc),
        })
        
        return {"message": f"User {user.get('email')} permanently deleted" if result.deleted_count else "No user deleted"}
    else:
        # Soft delete - just deactivate
        result = await db.users.update_one(
            {"id": user_id},
            {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}}
        )
        return {"message": "User deactivated" if result.modified_count else "No changes made"}


# ===================== BULK OPERATIONS =====================

@router.post("/users/bulk-assign-role")
async def bulk_assign_role(
    user_ids: List[str],
    role_id: str,
    token_data: dict = Depends(require_super_admin)
):
    """Assign role to multiple users"""
    db = Database.get_db()
    
    # Validate role
    role = await db.roles.find_one({"id": role_id})
    if not role:
        raise HTTPException(status_code=400, detail="Invalid role_id")
    
    result = await db.users.update_many(
        {"id": {"$in": user_ids}},
        {"$set": {"role_id": role_id, "updated_at": datetime.now(timezone.utc)}}
    )
    
    return {
        "message": f"Updated {result.modified_count} users",
        "role_name": role.get("name")
    }


@router.post("/users/bulk-assign-department")
async def bulk_assign_department(
    user_ids: List[str],
    department_id: str,
    token_data: dict = Depends(require_super_admin)
):
    """Assign department to multiple users"""
    db = Database.get_db()
    
    # Validate department
    dept = await db.departments.find_one({"id": department_id})
    if not dept:
        raise HTTPException(status_code=400, detail="Invalid department_id")
    
    result = await db.users.update_many(
        {"id": {"$in": user_ids}},
        {"$set": {"department_id": department_id, "updated_at": datetime.now(timezone.utc)}}
    )
    
    return {
        "message": f"Updated {result.modified_count} users",
        "department_name": dept.get("name")
    }


# ===================== CURRENT USER ROLE INFO =====================

@router.get("/me/permissions")
async def get_my_permissions(token_data: dict = Depends(get_current_user_from_token)):
    """Get current user's resolved permissions"""
    db = Database.get_db()
    rbac = RBACService(db)
    
    user_with_role = await rbac.get_user_with_role(token_data["id"])
    if not user_with_role:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "user_id": user_with_role.id,
        "role_code": user_with_role.role_code,
        "role_name": user_with_role.role_name,
        "is_super_admin": user_with_role.is_super_admin,
        "data_scope": user_with_role.data_scope,
        "permissions": user_with_role.permissions
    }


# ===================== ODOO SYNC ROUTES =====================

@router.post("/sync-odoo-departments")
async def sync_odoo_departments(
    token_data: dict = Depends(require_super_admin)
):
    """
    Sync departments from Odoo HR module.
    Creates/updates departments in our system based on Odoo data.
    """
    from services.odoo.connector import OdooConnector
    import uuid
    
    db = Database.get_db()
    
    # Get Odoo integration config
    odoo_intg = await db.integrations.find_one({"integration_type": "odoo"})
    if not odoo_intg or not odoo_intg.get("enabled") or not odoo_intg.get("config"):
        raise HTTPException(
            status_code=400,
            detail="Odoo integration not configured. Please configure Odoo first."
        )
    
    config = odoo_intg["config"]
    
    try:
        async with OdooConnector(
            url=config["url"],
            database=config["database"],
            username=config["username"],
            api_key=config["api_key"]
        ) as connector:
            # Fetch all departments from Odoo
            odoo_departments = await connector.get_departments(limit=500)
            
            now = datetime.now(timezone.utc)
            created = 0
            updated = 0
            skipped = 0
            
            # Create a mapping of Odoo dept IDs to our dept IDs for parent references
            odoo_to_our_id = {}
            
            # First pass: Create/update all departments
            for odoo_dept in odoo_departments:
                if not odoo_dept.get("name"):
                    skipped += 1
                    continue
                
                # Generate a code from name
                code = odoo_dept["name"].lower().replace(" ", "_").replace("-", "_")
                
                # Check if department exists by Odoo ID or code
                existing = await db.departments.find_one({
                    "$or": [
                        {"odoo_id": odoo_dept["id"]},
                        {"code": code}
                    ]
                })
                
                dept_data = {
                    "name": odoo_dept["name"],
                    "code": code,
                    "description": odoo_dept.get("complete_name", ""),
                    "odoo_id": odoo_dept["id"],
                    "is_active": True,
                    "updated_at": now
                }
                
                if existing:
                    # Update existing department
                    await db.departments.update_one(
                        {"id": existing["id"]},
                        {"$set": dept_data}
                    )
                    odoo_to_our_id[odoo_dept["id"]] = existing["id"]
                    updated += 1
                else:
                    # Create new department
                    dept_id = str(uuid.uuid4())
                    dept_data["id"] = dept_id
                    dept_data["created_at"] = now
                    dept_data["parent_id"] = None  # Will update in second pass
                    
                    await db.departments.insert_one(dept_data)
                    odoo_to_our_id[odoo_dept["id"]] = dept_id
                    created += 1
            
            # Second pass: Update parent relationships
            parent_updates = 0
            for odoo_dept in odoo_departments:
                if odoo_dept.get("parent_id") and isinstance(odoo_dept["parent_id"], list):
                    odoo_parent_id = odoo_dept["parent_id"][0]  # Odoo returns [id, name]
                    
                    if odoo_parent_id in odoo_to_our_id:
                        our_dept_id = odoo_to_our_id[odoo_dept["id"]]
                        our_parent_id = odoo_to_our_id[odoo_parent_id]
                        
                        await db.departments.update_one(
                            {"id": our_dept_id},
                            {"$set": {"parent_id": our_parent_id}}
                        )
                        parent_updates += 1
            
            return {
                "message": "Odoo departments synced successfully",
                "total_fetched": len(odoo_departments),
                "created": created,
                "updated": updated,
                "skipped": skipped,
                "parent_links": parent_updates
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync Odoo departments: {str(e)}"
        )


@router.post("/sync-odoo-users")
async def sync_odoo_users(
    token_data: dict = Depends(require_super_admin)
):
    """
    Sync users/employees from Odoo HR module.
    Creates/updates users in our system based on Odoo employee data.
    Note: Roles must still be assigned manually by Super Admin for security.
    """
    from services.odoo.connector import OdooConnector
    import uuid
    
    db = Database.get_db()
    
    # Get Odoo integration config
    odoo_intg = await db.integrations.find_one({"integration_type": "odoo"})
    if not odoo_intg or not odoo_intg.get("enabled") or not odoo_intg.get("config"):
        raise HTTPException(
            status_code=400,
            detail="Odoo integration not configured. Please configure Odoo first."
        )
    
    config = odoo_intg["config"]
    
    try:
        async with OdooConnector(
            url=config["url"],
            database=config["database"],
            username=config["username"],
            api_key=config["api_key"]
        ) as connector:
            # Fetch all employees from Odoo
            odoo_employees = await connector.get_employees(limit=500)
            
            now = datetime.now(timezone.utc)
            created = 0
            updated = 0
            skipped = 0
            
            for odoo_emp in odoo_employees:
                email = odoo_emp.get("work_email")
                if not email:
                    skipped += 1
                    continue
                
                # Try to match department
                dept_id = None
                if odoo_emp.get("department_id") and isinstance(odoo_emp["department_id"], list):
                    odoo_dept_id = odoo_emp["department_id"][0]
                    dept = await db.departments.find_one({"odoo_id": odoo_dept_id})
                    if dept:
                        dept_id = dept["id"]
                
                # Check if user exists
                existing_user = await db.users.find_one({"email": email})
                
                user_data = {
                    "name": odoo_emp.get("name", email.split("@")[0]),
                    "job_title": odoo_emp.get("job_title"),
                    "department_id": dept_id,
                    "odoo_user_id": odoo_emp.get("id"),
                    "is_active": odoo_emp.get("active", True),
                    "updated_at": now
                }
                
                if existing_user:
                    # Update existing user (don't overwrite role or approval status)
                    await db.users.update_one(
                        {"email": email},
                        {"$set": user_data}
                    )
                    updated += 1
                else:
                    # Create new user
                    user_id = str(uuid.uuid4())
                    user_data.update({
                        "id": user_id,
                        "email": email,
                        "password_hash": "",  # No password for synced users
                        "role_id": None,  # Must be assigned by admin
                        "is_super_admin": False,
                        "approval_status": "approved",  # Auto-approve Odoo users
                        "auth_provider": "odoo",
                        "created_at": now
                    })
                    
                    await db.users.insert_one(user_data)
                    created += 1
            
            return {
                "message": "Odoo users synced successfully",
                "total_fetched": len(odoo_employees),
                "created": created,
                "updated": updated,
                "skipped": skipped,
                "note": "Roles must be assigned manually by Super Admin"
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync Odoo users: {str(e)}"
        )


# ===================== AZURE AD USER DIRECTORY SYNC =====================

@router.post("/sync-azure-users")
async def sync_azure_ad_users(
    token_data: dict = Depends(require_super_admin)
):
    """
    Sync users from Azure AD directory into the application.
    This syncs ONLY identity information (name, email, department, job title).
    Does NOT sync personal emails, calendar, or files.
    
    Uses the most recently logged-in MS365 user's token.
    For full directory sync, admin consent with User.Read.All is required.
    """
    from services.ms365.connector import MS365Connector
    import uuid
    
    db = Database.get_db()
    
    # Get MS365 token from any user who has logged in via SSO
    ms_user = await db.users.find_one(
        {"ms_access_token": {"$exists": True, "$ne": ""}},
        {"ms_access_token": 1},
        sort=[("last_login", -1)]
    )
    
    if not ms_user or not ms_user.get("ms_access_token"):
        raise HTTPException(
            status_code=400,
            detail="No Microsoft 365 token available. A user must first login with Microsoft SSO."
        )
    
    try:
        async with MS365Connector(ms_user["ms_access_token"]) as connector:
            # Fetch users from Azure AD
            ad_users = await connector.get_organization_users(top=200)
            
            now = datetime.now(timezone.utc)
            created = 0
            updated = 0
            skipped = 0
            
            for ad_user in ad_users:
                email = ad_user.get("email")
                if not email:
                    skipped += 1
                    continue
                
                # Check if user exists
                existing = await db.users.find_one({"email": email})
                
                # Try to match department from our departments collection
                dept_id = None
                if ad_user.get("department"):
                    dept = await db.departments.find_one({
                        "$or": [
                            {"name": {"$regex": ad_user["department"], "$options": "i"}},
                            {"code": {"$regex": ad_user["department"], "$options": "i"}}
                        ]
                    })
                    if dept:
                        dept_id = dept["id"]
                
                if existing:
                    # Update existing user with Azure AD info
                    updates = {
                        "ms_id": ad_user.get("ms_id"),
                        "name": ad_user.get("display_name") or existing.get("name"),
                        "job_title": ad_user.get("job_title") or existing.get("job_title"),
                        "updated_at": now
                    }
                    
                    # Only update department if we found a match
                    if dept_id:
                        updates["department_id"] = dept_id
                    
                    await db.users.update_one({"email": email}, {"$set": updates})
                    updated += 1
                else:
                    # Create new user (without password - SSO only)
                    new_user = {
                        "id": str(uuid.uuid4()),
                        "email": email,
                        "name": ad_user.get("display_name", email.split("@")[0]),
                        "password_hash": "",
                        "ms_id": ad_user.get("ms_id"),
                        "job_title": ad_user.get("job_title"),
                        "department_id": dept_id,
                        "role_id": None,  # Super admin assigns role later
                        "is_super_admin": False,
                        "is_active": ad_user.get("is_active", True),
                        "auth_provider": "microsoft",
                        "created_at": now,
                        "updated_at": now
                    }
                    await db.users.insert_one(new_user)
                    created += 1
            
            return {
                "message": "Azure AD user sync completed",
                "total_fetched": len(ad_users),
                "created": created,
                "updated": updated,
                "skipped": skipped
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync Azure AD users: {str(e)}"
        )
