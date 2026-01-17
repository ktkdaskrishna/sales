"""
Portfolio Routes
API endpoints for portfolio management
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import logging

from core.database import Database
from services.auth.jwt_handler import get_current_user_from_token
from models.portfolio import (
    PortfolioCreate, PortfolioUpdate, PortfolioResponse, PortfolioDashboardResponse
)

router = APIRouter(prefix="/portfolios", tags=["Portfolios"])
logger = logging.getLogger(__name__)


async def require_approved_user(token_data: dict = Depends(get_current_user_from_token)):
    db = Database.get_db()
    user = await db.users.find_one({"id": token_data["id"]})
    if not user or user.get("approval_status") == "pending":
        raise HTTPException(status_code=403, detail="User pending approval")
    return token_data


@router.post("", response_model=PortfolioResponse)
async def create_portfolio(
    portfolio_data: PortfolioCreate,
    token_data: dict = Depends(require_approved_user)
):
    """Create a new portfolio"""
    db = Database.get_db()
    user_id = token_data["id"]
    
    # Verify team exists
    team = await db.teams.find_one({"id": portfolio_data.team_id})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Check if user is team member or admin
    is_team_member = user_id in team.get("member_ids", [])
    is_super_admin = token_data.get("is_super_admin", False)
    
    if not is_team_member and not is_super_admin:
        raise HTTPException(status_code=403, detail="Must be team member to create portfolio")
    
    now = datetime.now(timezone.utc)
    portfolio_id = str(uuid.uuid4())
    
    portfolio = {
        "id": portfolio_id,
        "name": portfolio_data.name,
        "team_id": portfolio_data.team_id,
        "owner_id": user_id,
        "product_lines": portfolio_data.product_lines,
        "strategic_priority": portfolio_data.strategic_priority,
        "description": portfolio_data.description,
        "fiscal_year": portfolio_data.fiscal_year or f"FY{datetime.now().year}",
        "metadata": {
            "active_initiatives": 0,
            "total_initiatives": 0,
            "total_activities": 0,
            "pipeline_value": 0.0
        },
        "created_at": now,
        "updated_at": now,
        "is_active": True
    }
    
    await db.portfolios.insert_one(portfolio)
    
    logger.info(f"Portfolio created: {portfolio_data.name} by user {user_id}")
    
    return PortfolioResponse(**{k: v for k, v in portfolio.items() if k != "_id" and k != "metadata"})


@router.get("", response_model=List[PortfolioResponse])
async def get_portfolios(
    team_id: Optional[str] = None,
    owner_id: Optional[str] = None,
    priority: Optional[str] = None,
    token_data: dict = Depends(require_approved_user)
):
    """Get all portfolios with optional filters"""
    db = Database.get_db()
    
    query = {"is_active": True}
    if team_id:
        query["team_id"] = team_id
    if owner_id:
        query["owner_id"] = owner_id
    if priority:
        query["strategic_priority"] = priority
    
    portfolios = await db.portfolios.find(query, {"_id": 0}).to_list(100)
    
    return [PortfolioResponse(**{k: v for k, v in p.items() if k != "metadata"}) for p in portfolios]


@router.get("/{portfolio_id}/dashboard")
async def get_portfolio_dashboard(
    portfolio_id: str,
    token_data: dict = Depends(require_approved_user)
):
    """Get complete portfolio dashboard with initiatives, KPIs, metrics"""
    db = Database.get_db()
    
    portfolio = await db.portfolios.find_one({"id": portfolio_id}, {"_id": 0})
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    # Get initiatives
    initiatives = await db.initiatives.find(
        {"portfolio_id": portfolio_id, "is_active": True},
        {"_id": 0}
    ).to_list(100) if hasattr(db, 'initiatives') else []
    
    # Get KPIs
    kpis = await db.kpis.find(
        {"portfolio_id": portfolio_id, "is_active": {"$ne": False}},
        {"_id": 0}
    ).to_list(100) if 'portfolio_id' in (await db.kpis.find_one({}) or {}) else []
    
    # Calculate metrics
    metrics = {
        "active_initiatives": len([i for i in initiatives if i.get("status") == "active"]),
        "total_initiatives": len(initiatives),
        "total_pipeline": 0.0,
        "win_rate": 0.0,
        "activity_completion_rate": 0.0
    }
    
    return {
        "portfolio": portfolio,
        "initiatives": initiatives,
        "kpis": kpis,
        "metrics": metrics,
        "recent_activities": [],
        "top_opportunities": []
    }
