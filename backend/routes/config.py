"""
Role Configuration Routes
API endpoints for managing roles, navigation, and dashboard configuration
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid
import logging

from core.database import Database
from services.auth.jwt_handler import get_current_user_from_token, require_role
from middleware.rbac import require_approved
from models.base import UserRole

router = APIRouter(prefix="/config", tags=["Configuration"])
logger = logging.getLogger(__name__)

# ===================== MODELS =====================

class NavigationItem(BaseModel):
    id: str
    label: str
    icon: str
    path: str
    enabled: bool = True
    order: int = 0

class DashboardWidget(BaseModel):
    widget: str
    x: int
    y: int
    w: int
    h: int

class RoleNavigationConfig(BaseModel):
    main_menu: List[NavigationItem] = []
    admin_menu: List[NavigationItem] = []

class RoleDashboardConfig(BaseModel):
    layout: List[DashboardWidget] = []

class RoleIncentiveConfig(BaseModel):
    commission_template_id: Optional[str] = None
    show_earnings: bool = True
    show_team_earnings: bool = False

class RoleConfigUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    data_scope: Optional[str] = None
    permissions: Optional[List[str]] = None
    navigation: Optional[RoleNavigationConfig] = None
    default_dashboard: Optional[RoleDashboardConfig] = None
    incentive_config: Optional[RoleIncentiveConfig] = None

class RoleCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    data_scope: str = "own"
    permissions: List[str] = []
    navigation: Optional[RoleNavigationConfig] = None
    default_dashboard: Optional[RoleDashboardConfig] = None
    incentive_config: Optional[RoleIncentiveConfig] = None

class UserDashboardLayout(BaseModel):
    layout: List[DashboardWidget]

# ===================== DEFAULT CONFIGURATIONS =====================

DEFAULT_NAV_ITEMS = [
    {"id": "dashboard", "label": "Dashboard", "icon": "LayoutDashboard", "path": "/dashboard", "order": 1},
    {"id": "accounts", "label": "Accounts", "icon": "Building2", "path": "/accounts", "order": 2},
    {"id": "opportunities", "label": "Opportunities", "icon": "Target", "path": "/opportunities", "order": 3},
    {"id": "teams", "label": "Teams", "icon": "Users", "path": "/teams", "order": 4},
    {"id": "portfolios", "label": "Portfolios", "icon": "Briefcase", "path": "/portfolios", "order": 5},
    {"id": "initiatives", "label": "Initiatives", "icon": "Rocket", "path": "/initiatives", "order": 6},
    {"id": "goals", "label": "Goals", "icon": "Award", "path": "/goals", "order": 7},
    {"id": "activity", "label": "Activity", "icon": "Activity", "path": "/activity", "order": 8},
    {"id": "invoices", "label": "Invoices", "icon": "FileText", "path": "/invoices", "order": 9},
    {"id": "kpis", "label": "KPIs", "icon": "BarChart3", "path": "/kpis", "order": 10},
    {"id": "email", "label": "Email & Calendar", "icon": "Mail", "path": "/my-outlook", "order": 8},
]

ADMIN_NAV_ITEMS = [
    {"id": "system-config", "label": "System Config", "icon": "Settings", "path": "/admin", "order": 1},
    {"id": "integrations", "label": "Integrations", "icon": "Plug2", "path": "/integrations", "order": 2},
    {"id": "data-lake", "label": "Data Lake", "icon": "Database", "path": "/data-lake", "order": 3},
    {"id": "field-mapping", "label": "Field Mapping", "icon": "Wand2", "path": "/field-mapping", "order": 4},
]

# Widget definitions for the registry
WIDGET_REGISTRY = {
    # KPI Cards
    "pipeline_value": {"name": "Pipeline Value", "category": "kpi", "minW": 2, "minH": 2, "description": "Total active pipeline value"},
    "won_revenue": {"name": "Won Revenue", "category": "kpi", "minW": 2, "minH": 2, "description": "Revenue from closed deals"},
    "quota_gauge": {"name": "Quota Attainment", "category": "kpi", "minW": 2, "minH": 2, "description": "Progress towards quota"},
    "active_opportunities": {"name": "Active Opportunities", "category": "kpi", "minW": 2, "minH": 2, "description": "Count of open deals"},
    "activity_completion": {"name": "Activity Completion", "category": "kpi", "minW": 2, "minH": 2, "description": "Task completion rate"},
    "win_rate": {"name": "Win Rate", "category": "kpi", "minW": 2, "minH": 2, "description": "Deal win percentage"},
    
    # Charts
    "pipeline_by_stage": {"name": "Pipeline by Stage", "category": "chart", "minW": 4, "minH": 3, "description": "Deals grouped by stage"},
    "revenue_by_product": {"name": "Revenue by Service Line", "category": "chart", "minW": 4, "minH": 3, "description": "Revenue breakdown by product"},
    "win_rate_trend": {"name": "Win Rate Trend", "category": "chart", "minW": 4, "minH": 3, "description": "Win rate over time"},
    "forecast_vs_actual": {"name": "Forecast vs Actual", "category": "chart", "minW": 6, "minH": 3, "description": "Projected vs actual revenue"},
    "monthly_revenue": {"name": "Monthly Revenue", "category": "chart", "minW": 4, "minH": 3, "description": "Revenue trend by month"},
    
    # Lists
    "upcoming_activities": {"name": "Upcoming Activities", "category": "list", "minW": 3, "minH": 4, "description": "Pending tasks and meetings"},
    "recent_emails": {"name": "Recent Emails", "category": "list", "minW": 3, "minH": 4, "description": "Latest email messages"},
    "team_leaderboard": {"name": "Team Leaderboard", "category": "list", "minW": 4, "minH": 4, "description": "Top performers ranking"},
    "collection_aging": {"name": "Collection Aging", "category": "list", "minW": 4, "minH": 3, "description": "Outstanding payments by age"},
    "recent_opportunities": {"name": "Recent Opportunities", "category": "list", "minW": 4, "minH": 3, "description": "Latest deals created/updated"},
    
    # Mini Kanban
    "pipeline_kanban": {"name": "Pipeline Mini Kanban", "category": "kanban", "minW": 8, "minH": 5, "description": "Compact pipeline view"},
}

DEFAULT_SALES_DASHBOARD = [
    {"widget": "pipeline_value", "x": 0, "y": 0, "w": 3, "h": 2},
    {"widget": "won_revenue", "x": 3, "y": 0, "w": 3, "h": 2},
    {"widget": "active_opportunities", "x": 6, "y": 0, "w": 3, "h": 2},
    {"widget": "activity_completion", "x": 9, "y": 0, "w": 3, "h": 2},
    {"widget": "pipeline_kanban", "x": 0, "y": 2, "w": 8, "h": 5},
    {"widget": "upcoming_activities", "x": 8, "y": 2, "w": 4, "h": 5},
]

DEFAULT_EXECUTIVE_DASHBOARD = [
    {"widget": "pipeline_value", "x": 0, "y": 0, "w": 3, "h": 2},
    {"widget": "won_revenue", "x": 3, "y": 0, "w": 3, "h": 2},
    {"widget": "quota_gauge", "x": 6, "y": 0, "w": 3, "h": 2},
    {"widget": "win_rate", "x": 9, "y": 0, "w": 3, "h": 2},
    {"widget": "pipeline_by_stage", "x": 0, "y": 2, "w": 6, "h": 4},
    {"widget": "revenue_by_product", "x": 6, "y": 2, "w": 6, "h": 4},
    {"widget": "team_leaderboard", "x": 0, "y": 6, "w": 6, "h": 4},
    {"widget": "forecast_vs_actual", "x": 6, "y": 6, "w": 6, "h": 4},
]

# ===================== WIDGET REGISTRY =====================

@router.get("/widgets")
async def get_widget_registry(
    token_data: dict = Depends(require_approved())
):
    """Get all available dashboard widgets"""
    return {
        "widgets": WIDGET_REGISTRY,
        "categories": ["kpi", "chart", "list", "kanban"]
    }

# ===================== NAVIGATION ITEMS =====================

@router.get("/navigation-items")
async def get_available_navigation_items(
    token_data: dict = Depends(require_approved())
):
    """Get all available navigation items for role configuration"""
    return {
        "main_menu": DEFAULT_NAV_ITEMS,
        "admin_menu": ADMIN_NAV_ITEMS
    }

# ===================== ROLE CONFIGURATION =====================

@router.get("/roles")
async def get_all_roles(
    token_data: dict = Depends(require_approved())
):
    """Get all roles with their configurations"""
    db = Database.get_db()
    roles = await db.roles.find({}, {"_id": 0}).to_list(100)
    return roles

@router.get("/roles/{role_id}")
async def get_role_config(
    role_id: str,
    token_data: dict = Depends(require_approved())
):
    """Get a specific role's configuration"""
    db = Database.get_db()
    role = await db.roles.find_one({"id": role_id}, {"_id": 0})
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role

@router.post("/roles")
async def create_role(
    data: RoleCreate,
    token_data: dict = Depends(require_approved())
):
    """Create a new role with full configuration"""
    db = Database.get_db()
    
    # Check if code exists
    existing = await db.roles.find_one({"code": data.code})
    if existing:
        raise HTTPException(status_code=400, detail="Role code already exists")
    
    now = datetime.now(timezone.utc)
    role_id = str(uuid.uuid4())
    
    # Set default navigation if not provided
    navigation = data.navigation.model_dump() if data.navigation else {
        "main_menu": [{"id": item["id"], **item, "enabled": True} for item in DEFAULT_NAV_ITEMS],
        "admin_menu": []
    }
    
    # Set default dashboard if not provided
    default_dashboard = data.default_dashboard.model_dump() if data.default_dashboard else {
        "layout": DEFAULT_SALES_DASHBOARD
    }
    
    # Set default incentive config
    incentive_config = data.incentive_config.model_dump() if data.incentive_config else {
        "commission_template_id": None,
        "show_earnings": True,
        "show_team_earnings": False
    }
    
    role = {
        "id": role_id,
        "code": data.code,
        "name": data.name,
        "description": data.description,
        "data_scope": data.data_scope,
        "permissions": data.permissions,
        "navigation": navigation,
        "default_dashboard": default_dashboard,
        "incentive_config": incentive_config,
        "is_system": False,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
        "created_by": token_data["id"]
    }
    
    await db.roles.insert_one(role)
    role.pop("_id", None)
    return role

@router.put("/roles/{role_id}")
async def update_role_config(
    role_id: str,
    data: RoleConfigUpdate,
    token_data: dict = Depends(require_approved())
):
    """Update a role's configuration (navigation, dashboard, permissions, etc.)"""
    db = Database.get_db()
    
    role = await db.roles.find_one({"id": role_id})
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    update_data = {"updated_at": datetime.now(timezone.utc)}
    
    if data.name is not None:
        update_data["name"] = data.name
    if data.description is not None:
        update_data["description"] = data.description
    if data.data_scope is not None:
        update_data["data_scope"] = data.data_scope
    if data.permissions is not None:
        update_data["permissions"] = data.permissions
    if data.navigation is not None:
        update_data["navigation"] = data.navigation.model_dump()
    if data.default_dashboard is not None:
        update_data["default_dashboard"] = data.default_dashboard.model_dump()
    if data.incentive_config is not None:
        update_data["incentive_config"] = data.incentive_config.model_dump()
    
    await db.roles.update_one({"id": role_id}, {"$set": update_data})
    
    updated_role = await db.roles.find_one({"id": role_id}, {"_id": 0})
    return updated_role

@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: str,
    token_data: dict = Depends(require_approved())
):
    """Delete a role (cannot delete system roles)"""
    db = Database.get_db()
    
    role = await db.roles.find_one({"id": role_id})
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    if role.get("is_system"):
        raise HTTPException(status_code=400, detail="Cannot delete system roles")
    
    # Check if any users have this role
    user_count = await db.users.count_documents({"role_id": role_id})
    if user_count > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete role: {user_count} users assigned")
    
    await db.roles.delete_one({"id": role_id})
    return {"message": "Role deleted"}

# ===================== USER DASHBOARD PREFERENCES =====================

@router.get("/user/dashboard")
async def get_user_dashboard_layout(
    token_data: dict = Depends(require_approved())
):
    """Get current user's dashboard layout (or role default)"""
    db = Database.get_db()
    user_id = token_data["id"]
    
    # Check for user-specific layout
    user_pref = await db.user_preferences.find_one(
        {"user_id": user_id, "type": "dashboard_layout"},
        {"_id": 0}
    )
    
    if user_pref:
        return {
            "layout": user_pref.get("layout", []),
            "source": "user"
        }
    
    # Fall back to role default
    user = await db.users.find_one({"id": user_id}, {"role_id": 1})
    if user and user.get("role_id"):
        role = await db.roles.find_one({"id": user["role_id"]}, {"_id": 0})
        if role and role.get("default_dashboard"):
            return {
                "layout": role["default_dashboard"].get("layout", DEFAULT_SALES_DASHBOARD),
                "source": "role"
            }
    
    # Ultimate fallback
    return {
        "layout": DEFAULT_SALES_DASHBOARD,
        "source": "default"
    }

@router.put("/user/dashboard")
async def save_user_dashboard_layout(
    data: UserDashboardLayout,
    token_data: dict = Depends(require_approved())
):
    """Save user's custom dashboard layout"""
    db = Database.get_db()
    user_id = token_data["id"]
    now = datetime.now(timezone.utc)
    
    await db.user_preferences.update_one(
        {"user_id": user_id, "type": "dashboard_layout"},
        {"$set": {
            "user_id": user_id,
            "type": "dashboard_layout",
            "layout": [w.model_dump() for w in data.layout],
            "updated_at": now
        }},
        upsert=True
    )
    
    return {"message": "Dashboard layout saved", "layout": data.layout}

@router.delete("/user/dashboard")
async def reset_user_dashboard_layout(
    token_data: dict = Depends(require_approved())
):
    """Reset user's dashboard to role default"""
    db = Database.get_db()
    user_id = token_data["id"]
    
    await db.user_preferences.delete_one(
        {"user_id": user_id, "type": "dashboard_layout"}
    )
    
    return {"message": "Dashboard reset to default"}

# ===================== USER NAVIGATION =====================

@router.get("/user/navigation")
async def get_user_navigation(
    token_data: dict = Depends(require_approved())
):
    """Get navigation items for current user based on their role"""
    db = Database.get_db()
    user_id = token_data["id"]
    
    user = await db.users.find_one({"id": user_id}, {"role_id": 1, "is_super_admin": 1})
    
    # Super admin gets everything
    if user and user.get("is_super_admin"):
        return {
            "main_menu": [{"id": item["id"], **item, "enabled": True} for item in DEFAULT_NAV_ITEMS],
            "admin_menu": [{"id": item["id"], **item, "enabled": True} for item in ADMIN_NAV_ITEMS]
        }
    
    # Get role-specific navigation
    if user and user.get("role_id"):
        role = await db.roles.find_one({"id": user["role_id"]}, {"_id": 0})
        if role and role.get("navigation"):
            return role["navigation"]
    
    # Default navigation (no admin)
    return {
        "main_menu": [{"id": item["id"], **item, "enabled": True} for item in DEFAULT_NAV_ITEMS],
        "admin_menu": []
    }

# ===================== SERVICE LINES (PRODUCT LINES) =====================

@router.get("/service-lines")
async def get_service_lines(
    token_data: dict = Depends(require_approved())
):
    """Get all service/product lines"""
    db = Database.get_db()
    lines = await db.service_lines.find({}, {"_id": 0}).to_list(100)
    
    # Seed Securado defaults if none exist
    if not lines:
        default_lines = [
            {"id": str(uuid.uuid4()), "code": "MCD", "name": "Managed Cyber Defense", "commission_weight": 1.3, "is_recurring": True, "order": 1},
            {"id": str(uuid.uuid4()), "code": "ACS", "name": "Adaptive Cloud Security", "commission_weight": 1.2, "is_recurring": True, "order": 2},
            {"id": str(uuid.uuid4()), "code": "GRC", "name": "IT GRC Services", "commission_weight": 1.1, "is_recurring": False, "order": 3},
            {"id": str(uuid.uuid4()), "code": "CONSULTING", "name": "Security Consulting", "commission_weight": 1.0, "is_recurring": False, "order": 4},
            {"id": str(uuid.uuid4()), "code": "MSSP", "name": "Managed Security Services", "commission_weight": 1.25, "is_recurring": True, "order": 5},
            {"id": str(uuid.uuid4()), "code": "ACADEMY", "name": "Securado Academy", "commission_weight": 0.8, "is_recurring": False, "order": 6},
        ]
        now = datetime.now(timezone.utc)
        for line in default_lines:
            line["created_at"] = now
            line["is_active"] = True
        await db.service_lines.insert_many(default_lines)
        lines = default_lines
    
    return lines

@router.post("/service-lines")
async def create_service_line(
    code: str = Query(...),
    name: str = Query(...),
    commission_weight: float = Query(default=1.0),
    is_recurring: bool = Query(default=False),
    token_data: dict = Depends(require_approved())
):
    """Create a new service line"""
    db = Database.get_db()
    
    existing = await db.service_lines.find_one({"code": code})
    if existing:
        raise HTTPException(status_code=400, detail="Service line code already exists")
    
    now = datetime.now(timezone.utc)
    max_order = await db.service_lines.find_one(sort=[("order", -1)])
    next_order = (max_order.get("order", 0) + 1) if max_order else 1
    
    line = {
        "id": str(uuid.uuid4()),
        "code": code,
        "name": name,
        "commission_weight": commission_weight,
        "is_recurring": is_recurring,
        "is_active": True,
        "order": next_order,
        "created_at": now
    }
    
    await db.service_lines.insert_one(line)
    line.pop("_id", None)
    return line

@router.put("/service-lines/{line_id}")
async def update_service_line(
    line_id: str,
    name: Optional[str] = Query(default=None),
    commission_weight: Optional[float] = Query(default=None),
    is_recurring: Optional[bool] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    token_data: dict = Depends(require_approved())
):
    """Update a service line"""
    db = Database.get_db()
    
    update_data = {}
    if name is not None:
        update_data["name"] = name
    if commission_weight is not None:
        update_data["commission_weight"] = commission_weight
    if is_recurring is not None:
        update_data["is_recurring"] = is_recurring
    if is_active is not None:
        update_data["is_active"] = is_active
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    result = await db.service_lines.update_one({"id": line_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Service line not found")
    
    updated = await db.service_lines.find_one({"id": line_id}, {"_id": 0})
    return updated

# ===================== PIPELINE STAGES =====================

@router.get("/pipeline-stages")
async def get_pipeline_stages(
    token_data: dict = Depends(require_approved())
):
    """Get all pipeline stages"""
    db = Database.get_db()
    stages = await db.pipeline_stages.find({}, {"_id": 0}).sort("order", 1).to_list(100)
    return stages

@router.put("/pipeline-stages/{stage_id}")
async def update_pipeline_stage(
    stage_id: str,
    name: Optional[str] = Query(default=None),
    color: Optional[str] = Query(default=None),
    probability_default: Optional[int] = Query(default=None),
    order: Optional[int] = Query(default=None),
    token_data: dict = Depends(require_approved())
):
    """Update a pipeline stage"""
    db = Database.get_db()
    
    update_data = {}
    if name is not None:
        update_data["name"] = name
    if color is not None:
        update_data["color"] = color
    if probability_default is not None:
        update_data["probability_default"] = probability_default
    if order is not None:
        update_data["order"] = order
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    result = await db.pipeline_stages.update_one({"id": stage_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Stage not found")
    
    updated = await db.pipeline_stages.find_one({"id": stage_id}, {"_id": 0})
    return updated

@router.post("/pipeline-stages")
async def create_pipeline_stage(
    name: str = Query(...),
    color: str = Query(default="#6B7280"),
    probability_default: int = Query(default=25),
    token_data: dict = Depends(require_approved())
):
    """Create a new pipeline stage"""
    db = Database.get_db()
    
    # Get max order
    max_stage = await db.pipeline_stages.find_one(sort=[("order", -1)])
    next_order = (max_stage.get("order", 0) + 1) if max_stage else 1
    
    stage = {
        "id": name.lower().replace(" ", "_"),
        "name": name,
        "color": color,
        "probability_default": probability_default,
        "order": next_order,
        "is_won": False,
        "is_lost": False
    }
    
    await db.pipeline_stages.insert_one(stage)
    stage.pop("_id", None)
    return stage


# ===================== BLUE SHEET WEIGHTS CONFIGURATION =====================

DEFAULT_BLUESHEET_WEIGHTS = {
    # Buying Influences (positive)
    "economic_buyer_identified": 10,
    "economic_buyer_favorable": 10,
    "user_buyer_favorable_each": 3,  # Per favorable user buyer (max 3)
    "technical_buyer_favorable_each": 3,  # Per favorable tech buyer (max 2)
    "coach_identified": 3,
    "coach_engaged": 2,
    # Red Flags (negative)
    "no_access_to_economic_buyer": -15,
    "reorganization_pending": -10,
    "budget_not_confirmed": -12,
    "competition_preferred": -15,
    "timeline_unclear": -8,
    # Win Results (positive)
    "clear_business_results": 12,
    "quantifiable_value": 8,
    # Action Plan (positive)
    "next_steps_defined": 8,
    "mutual_action_plan": 7,
    # Max caps
    "max_user_buyers": 3,
    "max_technical_buyers": 2,
    "max_possible_score": 75
}

class BlueSheetWeightsUpdate(BaseModel):
    economic_buyer_identified: Optional[int] = None
    economic_buyer_favorable: Optional[int] = None
    user_buyer_favorable_each: Optional[int] = None
    technical_buyer_favorable_each: Optional[int] = None
    coach_identified: Optional[int] = None
    coach_engaged: Optional[int] = None
    no_access_to_economic_buyer: Optional[int] = None
    reorganization_pending: Optional[int] = None
    budget_not_confirmed: Optional[int] = None
    competition_preferred: Optional[int] = None
    timeline_unclear: Optional[int] = None
    clear_business_results: Optional[int] = None
    quantifiable_value: Optional[int] = None
    next_steps_defined: Optional[int] = None
    mutual_action_plan: Optional[int] = None
    max_user_buyers: Optional[int] = None
    max_technical_buyers: Optional[int] = None
    max_possible_score: Optional[int] = None

@router.get("/bluesheet-weights")
async def get_bluesheet_weights(
    token_data: dict = Depends(require_approved())
):
    """Get Blue Sheet probability calculation weights (Super Admin configurable)"""
    db = Database.get_db()
    
    weights = await db.bluesheet_config.find_one({}, {"_id": 0})
    if not weights:
        # Seed defaults
        weights = {
            "id": str(uuid.uuid4()),
            **DEFAULT_BLUESHEET_WEIGHTS,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        await db.bluesheet_config.insert_one(weights)
        weights.pop("_id", None)
    
    return weights

@router.put("/bluesheet-weights")
async def update_bluesheet_weights(
    data: BlueSheetWeightsUpdate,
    token_data: dict = Depends(require_approved())
):
    """Update Blue Sheet weights (Super Admin only)"""
    db = Database.get_db()
    
    # Check if user is super admin
    user = await db.users.find_one({"id": token_data["id"]})
    if not user or not user.get("is_super_admin"):
        raise HTTPException(status_code=403, detail="Only Super Admin can modify Blue Sheet weights")
    
    # Get existing config
    config = await db.bluesheet_config.find_one({})
    if not config:
        # Create with defaults
        config = {
            "id": str(uuid.uuid4()),
            **DEFAULT_BLUESHEET_WEIGHTS,
            "created_at": datetime.now(timezone.utc)
        }
        await db.bluesheet_config.insert_one(config)
    
    # Update only provided fields
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    await db.bluesheet_config.update_one({}, {"$set": update_data})
    
    updated = await db.bluesheet_config.find_one({}, {"_id": 0})
    return updated

# ===================== TARGET ASSIGNMENT CONFIGURATION =====================
# Targets are ROLE-BASED, not user-specific
# Users inherit targets from their assigned role
# This allows dynamic target assignment as users change roles

class RoleTargetCreate(BaseModel):
    """Role-based target definition"""
    role_id: str  # Required - targets are per role
    period_type: str = "monthly"  # monthly, quarterly, yearly
    period_start: datetime
    period_end: datetime
    # Revenue targets
    target_revenue: float = 0
    target_deals: int = 0
    # Activity targets (role-specific)
    target_activities: int = 0
    target_demos: int = 0  # For presales
    target_support_tickets: int = 0  # For support
    target_meetings: int = 0  # For managers
    # Product line specific targets
    product_line_targets: Dict[str, float] = {}
    # Metadata
    notes: Optional[str] = None


class UserTargetOverride(BaseModel):
    """User-specific target override (exception to role-based)"""
    user_id: str
    role_target_id: str  # Reference to the role target being overridden
    override_revenue: Optional[float] = None
    override_deals: Optional[int] = None
    override_activities: Optional[int] = None
    reason: str  # Required explanation for override


# Legacy target create model (for backwards compatibility)
class TargetCreate(BaseModel):
    user_id: Optional[str] = None
    role_id: Optional[str] = None
    period_type: str = "monthly"
    period_start: datetime
    period_end: datetime
    target_revenue: float = 0
    target_deals: int = 0
    target_activities: int = 0
    product_line_targets: Dict[str, float] = {}


@router.get("/role-targets")
async def get_role_targets(
    role_id: Optional[str] = Query(default=None),
    period_type: Optional[str] = Query(default=None),
    active_only: bool = Query(default=True),
    token_data: dict = Depends(require_approved())
):
    """
    Get role-based targets.
    Returns targets that apply to roles, not individual users.
    """
    db = Database.get_db()
    
    query = {}
    if role_id:
        query["role_id"] = role_id
    if period_type:
        query["period_type"] = period_type
    if active_only:
        now = datetime.now(timezone.utc)
        query["period_end"] = {"$gte": now}
    
    targets = await db.role_targets.find(query, {"_id": 0}).to_list(100)
    
    # Enrich with role names
    for target in targets:
        role = await db.roles.find_one({"id": target.get("role_id")})
        target["role_name"] = role.get("name") if role else "Unknown Role"
    
    return targets


@router.post("/role-targets")
async def create_role_target(
    data: RoleTargetCreate,
    token_data: dict = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """
    Create a role-based target.
    All users with this role will inherit this target.
    """
    db = Database.get_db()
    
    # Verify role exists
    role = await db.roles.find_one({"id": data.role_id})
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Check for existing target for same role/period
    existing = await db.role_targets.find_one({
        "role_id": data.role_id,
        "period_type": data.period_type,
        "period_start": {"$lte": data.period_end},
        "period_end": {"$gte": data.period_start}
    })
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Target already exists for role '{role.get('name')}' in overlapping period"
        )
    
    target = {
        "id": str(uuid.uuid4()),
        **data.model_dump(),
        "created_at": datetime.now(timezone.utc),
        "created_by": token_data["id"]
    }
    
    await db.role_targets.insert_one(target)
    
    # Audit log
    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "action": "create_role_target",
        "entity_type": "role_target",
        "entity_id": target["id"],
        "user_id": token_data["id"],
        "details": {"role_id": data.role_id, "role_name": role.get("name")},
        "timestamp": datetime.now(timezone.utc),
    })
    
    target.pop("_id", None)
    target["role_name"] = role.get("name")
    return target


@router.put("/role-targets/{target_id}")
async def update_role_target(
    target_id: str,
    target_revenue: Optional[float] = Query(default=None),
    target_deals: Optional[int] = Query(default=None),
    target_activities: Optional[int] = Query(default=None),
    target_demos: Optional[int] = Query(default=None),
    target_support_tickets: Optional[int] = Query(default=None),
    target_meetings: Optional[int] = Query(default=None),
    notes: Optional[str] = Query(default=None),
    token_data: dict = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """Update a role-based target"""
    db = Database.get_db()
    
    update_data = {"updated_at": datetime.now(timezone.utc)}
    if target_revenue is not None:
        update_data["target_revenue"] = target_revenue
    if target_deals is not None:
        update_data["target_deals"] = target_deals
    if target_activities is not None:
        update_data["target_activities"] = target_activities
    if target_demos is not None:
        update_data["target_demos"] = target_demos
    if target_support_tickets is not None:
        update_data["target_support_tickets"] = target_support_tickets
    if target_meetings is not None:
        update_data["target_meetings"] = target_meetings
    if notes is not None:
        update_data["notes"] = notes
    
    result = await db.role_targets.update_one(
        {"id": target_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Target not found")
    
    return {"message": "Target updated"}


@router.delete("/role-targets/{target_id}")
async def delete_role_target(
    target_id: str,
    token_data: dict = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """Delete a role-based target"""
    db = Database.get_db()
    
    result = await db.role_targets.delete_one({"id": target_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Target not found")
    
    return {"message": "Target deleted"}


@router.get("/user-targets/{user_id}")
async def get_user_effective_targets(
    user_id: str,
    period_type: Optional[str] = Query(default="monthly"),
    token_data: dict = Depends(require_approved())
):
    """
    Get effective targets for a specific user.
    Resolves role-based targets + any user-specific overrides.
    """
    db = Database.get_db()
    
    # Get user and their role
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    role_id = user.get("role_id")
    if not role_id:
        return {
            "user_id": user_id,
            "user_name": user.get("name"),
            "role_id": None,
            "role_name": None,
            "targets": None,
            "message": "User has no assigned role"
        }
    
    # Get role info
    role = await db.roles.find_one({"id": role_id})
    role_name = role.get("name") if role else "Unknown"
    
    # Get role-based targets for current period
    now = datetime.now(timezone.utc)
    role_target = await db.role_targets.find_one({
        "role_id": role_id,
        "period_type": period_type,
        "period_start": {"$lte": now},
        "period_end": {"$gte": now}
    }, {"_id": 0})
    
    if not role_target:
        return {
            "user_id": user_id,
            "user_name": user.get("name"),
            "role_id": role_id,
            "role_name": role_name,
            "targets": None,
            "message": f"No {period_type} targets defined for role '{role_name}'"
        }
    
    # Check for user-specific overrides
    override = await db.target_overrides.find_one({
        "user_id": user_id,
        "role_target_id": role_target["id"]
    }, {"_id": 0})
    
    # Merge override into target
    effective_target = {**role_target}
    if override:
        if override.get("override_revenue") is not None:
            effective_target["target_revenue"] = override["override_revenue"]
        if override.get("override_deals") is not None:
            effective_target["target_deals"] = override["override_deals"]
        if override.get("override_activities") is not None:
            effective_target["target_activities"] = override["override_activities"]
        effective_target["has_override"] = True
        effective_target["override_reason"] = override.get("reason")
    else:
        effective_target["has_override"] = False
    
    return {
        "user_id": user_id,
        "user_name": user.get("name"),
        "role_id": role_id,
        "role_name": role_name,
        "targets": effective_target
    }


@router.get("/target-progress-report")
async def get_target_progress_report(
    period_type: Optional[str] = Query(default=None, description="monthly, quarterly, yearly"),
    role_id: Optional[str] = Query(default=None, description="Filter by specific role"),
    token_data: dict = Depends(require_approved())
):
    """
    Get aggregated target progress report for all salespeople.
    Shows each user's progress against their role-based targets.
    
    Returns:
    - Individual progress per salesperson
    - Team-wide aggregated metrics
    - Variance analysis (above/below target)
    """
    db = Database.get_db()
    
    now = datetime.now(timezone.utc)
    
    # Get active role targets
    target_query = {"period_end": {"$gte": now}}
    if period_type:
        target_query["period_type"] = period_type
    if role_id:
        target_query["role_id"] = role_id
    
    role_targets = await db.role_targets.find(target_query, {"_id": 0}).to_list(100)
    
    # Create a map of role_id to target
    role_target_map = {t["role_id"]: t for t in role_targets}
    
    # Get roles
    roles = await db.roles.find({}, {"_id": 0}).to_list(100)
    role_map = {r["id"]: r for r in roles}
    
    # Get all sales users (users with roles that have targets)
    role_ids_with_targets = list(role_target_map.keys())
    users_query = {"is_active": True}
    if role_ids_with_targets:
        users_query["role_id"] = {"$in": role_ids_with_targets}
    
    users = await db.users.find(users_query, {"_id": 0, "password_hash": 0}).to_list(500)
    
    # Calculate actual performance for each user
    user_progress = []
    team_totals = {
        "target_revenue": 0,
        "actual_revenue": 0,
        "target_deals": 0,
        "actual_deals": 0,
        "target_activities": 0,
        "actual_activities": 0,
    }
    
    for user in users:
        user_role_id = user.get("role_id")
        if not user_role_id or user_role_id not in role_target_map:
            continue
        
        target = role_target_map[user_role_id]
        role = role_map.get(user_role_id, {})
        
        # Get user's Odoo data for matching
        odoo_user_id = user.get("odoo_user_id")
        odoo_salesperson_name = user.get("odoo_salesperson_name", "").lower()
        
        # Calculate actual performance from data_lake_serving
        # Won opportunities (revenue)
        won_match = {
            "entity_type": "opportunity",
            "is_active": {"$ne": False},
            "$or": [
                {"data.stage_name": {"$regex": "won", "$options": "i"}},
                {"data.stage_id": {"$in": [4, "won"]}}  # Common won stage IDs
            ]
        }
        
        # Add user filter
        if odoo_user_id:
            won_match["data.salesperson_id"] = odoo_user_id
        elif odoo_salesperson_name:
            won_match["data.salesperson_name"] = {"$regex": f"^{odoo_salesperson_name}$", "$options": "i"}
        else:
            continue  # Skip users without Odoo mapping
        
        won_opps = await db.data_lake_serving.find(won_match, {"data.amount": 1}).to_list(1000)
        actual_revenue = sum(o.get("data", {}).get("amount", 0) or 0 for o in won_opps)
        
        # Active opportunities (deals in pipeline)
        active_match = {
            "entity_type": "opportunity",
            "is_active": {"$ne": False},
        }
        if odoo_user_id:
            active_match["data.salesperson_id"] = odoo_user_id
        elif odoo_salesperson_name:
            active_match["data.salesperson_name"] = {"$regex": f"^{odoo_salesperson_name}$", "$options": "i"}
        
        actual_deals = await db.data_lake_serving.count_documents(active_match)
        
        # Activities count
        activity_match = {
            "entity_type": "activity",
            "is_active": {"$ne": False},
        }
        if odoo_user_id:
            activity_match["data.user_id"] = odoo_user_id
        
        actual_activities = await db.data_lake_serving.count_documents(activity_match)
        
        # Calculate progress percentages
        target_revenue = target.get("target_revenue", 0)
        target_deals = target.get("target_deals", 0)
        target_activities = target.get("target_activities", 0)
        
        revenue_progress = round((actual_revenue / target_revenue * 100), 1) if target_revenue > 0 else 0
        deals_progress = round((actual_deals / target_deals * 100), 1) if target_deals > 0 else 0
        activities_progress = round((actual_activities / target_activities * 100), 1) if target_activities > 0 else 0
        
        # Overall progress (weighted average)
        weights = {"revenue": 0.5, "deals": 0.3, "activities": 0.2}
        overall_progress = round(
            revenue_progress * weights["revenue"] +
            deals_progress * weights["deals"] +
            activities_progress * weights["activities"],
            1
        )
        
        # Determine status
        if overall_progress >= 100:
            status = "achieved"
        elif overall_progress >= 70:
            status = "on_track"
        elif overall_progress >= 40:
            status = "at_risk"
        else:
            status = "behind"
        
        user_progress.append({
            "user_id": user["id"],
            "user_name": user.get("name", "Unknown"),
            "user_email": user.get("email"),
            "role_id": user_role_id,
            "role_name": role.get("name", "Unknown"),
            "target": {
                "revenue": target_revenue,
                "deals": target_deals,
                "activities": target_activities,
                "period_type": target.get("period_type"),
                "period_start": target.get("period_start"),
                "period_end": target.get("period_end"),
            },
            "actual": {
                "revenue": actual_revenue,
                "deals": actual_deals,
                "activities": actual_activities,
            },
            "progress": {
                "revenue": revenue_progress,
                "deals": deals_progress,
                "activities": activities_progress,
                "overall": overall_progress,
            },
            "variance": {
                "revenue": actual_revenue - target_revenue,
                "deals": actual_deals - target_deals,
                "activities": actual_activities - target_activities,
            },
            "status": status,
        })
        
        # Aggregate team totals
        team_totals["target_revenue"] += target_revenue
        team_totals["actual_revenue"] += actual_revenue
        team_totals["target_deals"] += target_deals
        team_totals["actual_deals"] += actual_deals
        team_totals["target_activities"] += target_activities
        team_totals["actual_activities"] += actual_activities
    
    # Calculate team-level progress
    team_progress = {
        "revenue": round((team_totals["actual_revenue"] / team_totals["target_revenue"] * 100), 1) if team_totals["target_revenue"] > 0 else 0,
        "deals": round((team_totals["actual_deals"] / team_totals["target_deals"] * 100), 1) if team_totals["target_deals"] > 0 else 0,
        "activities": round((team_totals["actual_activities"] / team_totals["target_activities"] * 100), 1) if team_totals["target_activities"] > 0 else 0,
    }
    
    # Sort users by overall progress (descending)
    user_progress.sort(key=lambda x: x["progress"]["overall"], reverse=True)
    
    # Calculate summary stats
    achieved_count = sum(1 for u in user_progress if u["status"] == "achieved")
    on_track_count = sum(1 for u in user_progress if u["status"] == "on_track")
    at_risk_count = sum(1 for u in user_progress if u["status"] == "at_risk")
    behind_count = sum(1 for u in user_progress if u["status"] == "behind")
    
    return {
        "generated_at": now.isoformat(),
        "period_filter": period_type,
        "role_filter": role_id,
        "summary": {
            "total_salespeople": len(user_progress),
            "achieved": achieved_count,
            "on_track": on_track_count,
            "at_risk": at_risk_count,
            "behind": behind_count,
        },
        "team_totals": team_totals,
        "team_progress": team_progress,
        "individual_progress": user_progress,
    }


# Legacy endpoints - kept for backwards compatibility
@router.get("/targets")
async def get_targets(
    user_id: Optional[str] = Query(default=None),
    period_type: Optional[str] = Query(default=None),
    token_data: dict = Depends(require_approved())
):
    """Get sales targets (legacy - use /role-targets instead)"""
    db = Database.get_db()
    
    query = {}
    if user_id:
        query["user_id"] = user_id
    if period_type:
        query["period_type"] = period_type
    
    targets = await db.targets.find(query, {"_id": 0}).to_list(100)
    return targets


@router.post("/targets")
async def create_target(
    data: TargetCreate,
    token_data: dict = Depends(require_approved())
):
    """Create a new target (legacy - use /role-targets instead)"""
    db = Database.get_db()
    
    # Check if user is super admin
    user = await db.users.find_one({"id": token_data["id"]})
    if not user or not user.get("is_super_admin"):
        raise HTTPException(status_code=403, detail="Only Super Admin can create targets")
    
    target = {
        "id": str(uuid.uuid4()),
        **data.model_dump(),
        "created_at": datetime.now(timezone.utc),
        "created_by": token_data["id"]
    }
    
    await db.targets.insert_one(target)
    target.pop("_id", None)
    return target


@router.put("/targets/{target_id}")
async def update_target(
    target_id: str,
    target_revenue: Optional[float] = Query(default=None),
    target_deals: Optional[int] = Query(default=None),
    target_activities: Optional[int] = Query(default=None),
    token_data: dict = Depends(require_approved())
):
    """Update a target"""
    db = Database.get_db()
    
    user = await db.users.find_one({"id": token_data["id"]})
    if not user or not user.get("is_super_admin"):
        raise HTTPException(status_code=403, detail="Only Super Admin can modify targets")
    
    update_data = {"updated_at": datetime.now(timezone.utc)}
    if target_revenue is not None:
        update_data["target_revenue"] = target_revenue
    if target_deals is not None:
        update_data["target_deals"] = target_deals
    if target_activities is not None:
        update_data["target_activities"] = target_activities
    
    result = await db.targets.update_one({"id": target_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Target not found")
    
    updated = await db.targets.find_one({"id": target_id}, {"_id": 0})
    return updated

@router.delete("/targets/{target_id}")
async def delete_target(
    target_id: str,
    token_data: dict = Depends(require_approved())
):
    """Delete a target"""
    db = Database.get_db()
    
    user = await db.users.find_one({"id": token_data["id"]})
    if not user or not user.get("is_super_admin"):
        raise HTTPException(status_code=403, detail="Only Super Admin can delete targets")
    
    result = await db.targets.delete_one({"id": target_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Target not found")
    
    return {"message": "Target deleted"}
