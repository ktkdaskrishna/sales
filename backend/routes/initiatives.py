"""
Initiative Routes
API endpoints for initiative/campaign management
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import logging

from core.database import Database
from services.auth.jwt_handler import get_current_user_from_token
from models.initiative import InitiativeCreate, InitiativeUpdate, InitiativeResponse

router = APIRouter(prefix="/initiatives", tags=["Initiatives"])
logger = logging.getLogger(__name__)


async def require_approved_user(token_data: dict = Depends(get_current_user_from_token)):
    db = Database.get_db()
    user = await db.users.find_one({"id": token_data["id"]})
    if not user or user.get("approval_status") == "pending":
        raise HTTPException(status_code=403, detail="User pending approval")
    return token_data


@router.post("", response_model=InitiativeResponse)
async def create_initiative(
    initiative_data: InitiativeCreate,
    token_data: dict = Depends(require_approved_user)
):
    """Create a new initiative/campaign"""
    db = Database.get_db()
    user_id = token_data["id"]
    
    # Verify portfolio exists
    portfolio = await db.portfolios.find_one({"id": initiative_data.portfolio_id})
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    # Check permission
    is_portfolio_owner = portfolio["owner_id"] == user_id
    is_team_member = user_id in (await db.teams.find_one({"id": portfolio["team_id"]}) or {}).get("member_ids", [])
    
    if not is_portfolio_owner and not is_team_member and not token_data.get("is_super_admin"):
        raise HTTPException(status_code=403, detail="Must be portfolio owner or team member")
    
    now = datetime.now(timezone.utc)
    initiative_id = str(uuid.uuid4())
    
    # Build activity template with completion tracking
    activity_template = {}
    if initiative_data.activity_template:
        for activity_type, target in initiative_data.activity_template.items():
            activity_template[activity_type] = {
                "target": target,
                "completed": 0
            }
    
    initiative = {
        "id": initiative_id,
        "name": initiative_data.name,
        "portfolio_id": initiative_data.portfolio_id,
        "team_id": portfolio["team_id"],
        "owner_id": user_id,
        "type": initiative_data.type,
        "start_date": initiative_data.start_date,
        "end_date": initiative_data.end_date,
        "status": "planning",
        "description": initiative_data.description,
        "activity_template": activity_template,
        "milestones": initiative_data.milestones,
        "goals": [],
        "kpis": [],
        "metadata": {
            "total_activities": 0,
            "opportunities_created": 0,
            "pipeline_generated": 0.0
        },
        "created_at": now,
        "updated_at": now,
        "is_active": True
    }
    
    await db.initiatives.insert_one(initiative)
    
    # Update portfolio metadata
    await db.portfolios.update_one(
        {"id": initiative_data.portfolio_id},
        {"$inc": {"metadata.total_initiatives": 1}}
    )
    
    logger.info(f"Initiative created: {initiative_data.name} in portfolio {initiative_data.portfolio_id}")
    
    return InitiativeResponse(
        id=initiative_id,
        name=initiative_data.name,
        portfolio_id=initiative_data.portfolio_id,
        owner_id=user_id,
        type=initiative_data.type,
        start_date=initiative_data.start_date,
        end_date=initiative_data.end_date,
        status="planning",
        description=initiative_data.description,
        created_at=now,
        updated_at=now,
        is_active=True
    )


@router.get("", response_model=List[InitiativeResponse])
async def get_initiatives(
    portfolio_id: Optional[str] = None,
    status: Optional[str] = None,
    token_data: dict = Depends(require_approved_user)
):
    """Get all initiatives with optional filters"""
    db = Database.get_db()
    
    query = {"is_active": True}
    if portfolio_id:
        query["portfolio_id"] = portfolio_id
    if status:
        query["status"] = status
    
    initiatives = await db.initiatives.find(query, {"_id": 0}).to_list(100)
    
    return [InitiativeResponse(**{k: v for k, v in i.items() if k not in ["activity_template", "milestones", "metadata", "goals", "kpis"]}) for i in initiatives]


@router.get("/{initiative_id}/progress")
async def get_initiative_progress(
    initiative_id: str,
    token_data: dict = Depends(require_approved_user)
):
    """Get detailed initiative progress"""
    db = Database.get_db()
    
    initiative = await db.initiatives.find_one({"id": initiative_id}, {"_id": 0})
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")
    
    # Calculate activity progress
    activity_template = initiative.get("activity_template", {})
    overall_progress = 0.0
    
    if activity_template:
        total_target = sum(act["target"] for act in activity_template.values())
        total_completed = sum(act["completed"] for act in activity_template.values())
        overall_progress = (total_completed / total_target * 100) if total_target > 0 else 0.0
    
    # Get linked goals
    goal_ids = initiative.get("goals", [])
    goals = await db.goals.find({"id": {"$in": goal_ids}}, {"_id": 0}).to_list(100) if goal_ids else []
    
    return {
        "initiative": initiative,
        "progress": {
            "overall": round(overall_progress, 2),
            "activity_completion": {
                act_type: {
                    "completed": act_data["completed"],
                    "target": act_data["target"],
                    "percentage": round((act_data["completed"] / act_data["target"] * 100) if act_data["target"] > 0 else 0, 2)
                }
                for act_type, act_data in activity_template.items()
            }
        },
        "goals": goals,
        "kpis": [],
        "recent_activities": []
    }


@router.patch("/{initiative_id}/status")
async def update_initiative_status(
    initiative_id: str,
    status: str,
    token_data: dict = Depends(require_approved_user)
):
    """Update initiative status (planning/active/completed/paused/cancelled)"""
    db = Database.get_db()
    
    valid_statuses = ["planning", "active", "completed", "paused", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    result = await db.initiatives.update_one(
        {"id": initiative_id},
        {"$set": {"status": status, "updated_at": datetime.now(timezone.utc)}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Initiative not found")
    
    return {"initiative_id": initiative_id, "status": status, "updated": True}
