"""
Sales Routes - Account Manager Dashboard APIs
Provides endpoints for opportunities, pipeline management, blue sheet analysis,
incentive calculations, and sales metrics.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone, timedelta
import uuid
import os
import logging

from core.database import Database
from services.auth.jwt_handler import get_current_user_from_token
from middleware.rbac import require_approved
from core.config import settings

router = APIRouter(tags=["Sales"])
logger = logging.getLogger(__name__)


# ===================== HELPER FUNCTIONS =====================

def active_entity_filter(entity_type: str, additional_filters: dict = None) -> dict:
    """
    Create a filter for active (non-deleted) records from data_lake_serving.
    Soft-deleted records (is_active=False) are completely hidden from users.
    
    Handles three cases:
    - is_active=True: explicitly active
    - is_active=None: not yet set (legacy/seeded data, treated as active)
    - is_active does not exist: old records (treated as active)
    """
    base_filter = {
        "entity_type": entity_type,
        # Exclude only explicitly deleted records (is_active=False)
        "is_active": {"$ne": False}
    }
    if additional_filters:
        base_filter.update(additional_filters)
    return base_filter


# ===================== MODELS =====================

class OpportunityCreate(BaseModel):
    name: str
    account_id: str
    value: float = 0
    stage: str = "qualification"
    probability: int = 10
    expected_close_date: Optional[datetime] = None
    product_lines: List[str] = []
    description: Optional[str] = None
    single_sales_objective: Optional[str] = None
    competition: Optional[str] = None

class OpportunityUpdate(BaseModel):
    name: Optional[str] = None
    value: Optional[float] = None
    stage: Optional[str] = None
    probability: Optional[int] = None
    expected_close_date: Optional[datetime] = None
    product_lines: Optional[List[str]] = None
    description: Optional[str] = None
    single_sales_objective: Optional[str] = None
    competition: Optional[str] = None

class BlueSheetAnalysis(BaseModel):
    opportunity_id: str
    # Buying Influences
    economic_buyer_identified: bool = False
    economic_buyer_favorable: bool = False
    user_buyers_identified: int = 0
    user_buyers_favorable: int = 0
    technical_buyers_identified: int = 0
    technical_buyers_favorable: int = 0
    coach_identified: bool = False
    coach_engaged: bool = False
    # Red Flags
    no_access_to_economic_buyer: bool = False
    reorganization_pending: bool = False
    budget_not_confirmed: bool = False
    competition_preferred: bool = False
    timeline_unclear: bool = False
    # Win Results
    clear_business_results: bool = False
    quantifiable_value: bool = False
    # Action Plan
    next_steps_defined: bool = False
    mutual_action_plan: bool = False

class CommissionTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    template_type: str = "tiered_attainment"  # flat, tiered_attainment, tiered_revenue, gross_margin
    base_rate: float = 0.01  # Changed from 0.05 (5%) to 0.01 (1%)
    tiers: List[Dict] = []
    product_weights: Dict[str, float] = {}
    new_logo_multiplier: float = 1.5

class ActivityCreate(BaseModel):
    title: str
    description: Optional[str] = None
    activity_type: str = "task"
    priority: str = "medium"
    status: str = "pending"
    due_date: Optional[datetime] = None
    account_id: Optional[str] = None
    opportunity_id: Optional[str] = None

# ===================== PIPELINE STAGES =====================

DEFAULT_STAGES = [
    {"id": "lead", "name": "Lead", "order": 1, "color": "#6366F1", "probability_default": 5},
    {"id": "qualification", "name": "Qualification", "order": 2, "color": "#8B5CF6", "probability_default": 10},
    {"id": "discovery", "name": "Discovery", "order": 3, "color": "#3B82F6", "probability_default": 25},
    {"id": "proposal", "name": "Proposal", "order": 4, "color": "#F59E0B", "probability_default": 50},
    {"id": "negotiation", "name": "Negotiation", "order": 5, "color": "#F97316", "probability_default": 75},
    {"id": "closed_won", "name": "Closed Won", "order": 6, "color": "#10B981", "probability_default": 100, "is_won": True},
    {"id": "closed_lost", "name": "Closed Lost", "order": 7, "color": "#EF4444", "probability_default": 0, "is_lost": True},
]

# Cybersecurity Product Line Weights
PRODUCT_LINE_WEIGHTS = {
    "MSSP": 1.2,  # Recurring revenue premium
    "Application Security": 1.0,
    "Network Security": 1.0,
    "GRC": 1.1,  # Consulting margin premium
}

# ===================== OPPORTUNITIES =====================

@router.post("/opportunities")
async def create_opportunity(
    data: OpportunityCreate,
    token_data: dict = Depends(require_approved())
):
    """Create a new opportunity"""
    db = Database.get_db()
    user_id = token_data["id"]
    
    # Verify account exists
    account = await db.accounts.find_one({"id": data.account_id})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    now = datetime.now(timezone.utc)
    opp_id = str(uuid.uuid4())
    
    opportunity = {
        "id": opp_id,
        "name": data.name,
        "account_id": data.account_id,
        "account_name": account.get("name", ""),
        "value": data.value,
        "stage": data.stage,
        "probability": data.probability,
        "expected_close_date": data.expected_close_date,
        "product_lines": data.product_lines,
        "description": data.description,
        "single_sales_objective": data.single_sales_objective,
        "competition": data.competition,
        "owner_id": user_id,
        "owner_name": token_data.get("name", ""),
        "blue_sheet_analysis": None,
        "created_at": now,
        "updated_at": now
    }
    
    await db.opportunities.insert_one(opportunity)
    
    # Return without _id
    opportunity.pop("_id", None)
    return opportunity

@router.get("/opportunities")
async def get_opportunities(
    stage: Optional[str] = None,
    product_line: Optional[str] = None,
    token_data: dict = Depends(require_approved())
):
    """Get opportunities from data_lake_serving with proper field mapping"""
    from services.field_mapper import get_field_mapper
    
    db = Database.get_db()
    user_id = token_data["id"]
    user_email = token_data.get("email", "").lower()
    
    # Get user profile from CQRS for proper access control
    user_profile = await db.user_profiles.find_one({"email": user_email}, {"_id": 0})
    
    if not user_profile:
        # User not in CQRS system
        return []
    
    cqrs_user_id = user_profile["id"]
    is_super_admin = user_profile.get("is_super_admin", False)
    
    # Get access matrix for proper multi-level hierarchy support
    access_matrix = await db.user_access_matrix.find_one({"user_id": cqrs_user_id}, {"_id": 0})
    
    if not access_matrix and not is_super_admin:
        logger.warning(f"No access matrix for user {user_email}")
        return []
    
    # Get accessible opportunity IDs from access matrix
    accessible_opp_ids = access_matrix.get("accessible_opportunities", []) if access_matrix else []
    
    # Fetch from data_lake_serving
    opportunities = []
    opp_docs = await db.data_lake_serving.find(active_entity_filter("opportunity")).to_list(1000)
    
    # Get field mapper
    mapper = get_field_mapper()
    
    for doc in opp_docs:
        opp_data = doc.get("data", {})
        
        # Use universal mapper for proper field extraction
        canonical_opp = mapper.map_opportunity(opp_data)
        
        # Access control: Check if user can see this opportunity
        if not is_super_admin:
            opp_odoo_id = canonical_opp.get("odoo_id")
            
            # Convert to int for comparison if needed
            try:
                opp_odoo_id_int = int(opp_odoo_id) if opp_odoo_id else None
            except:
                opp_odoo_id_int = None
            
            # Check if opportunity is in accessible list
            if opp_odoo_id not in accessible_opp_ids and opp_odoo_id_int not in accessible_opp_ids:
                continue  # User can't access this opportunity
        
        # Map stage to internal format (keep existing logic)
        stage_name_lower = canonical_opp.get("stage_name", "").lower()
        if "won" in stage_name_lower:
            mapped_stage = "closed_won"
        elif "lost" in stage_name_lower:
            mapped_stage = "closed_lost"
        elif "negot" in stage_name_lower:
            mapped_stage = "negotiation"
        elif "propos" in stage_name_lower:
            mapped_stage = "proposal"
        elif "discov" in stage_name_lower:
            mapped_stage = "discovery"
        elif "qualif" in stage_name_lower:
            mapped_stage = "qualification"
        else:
            mapped_stage = "lead"
        
        canonical_opp["stage"] = mapped_stage
        canonical_opp["last_synced"] = doc.get("last_aggregated")
        
        # Stage filter
        if stage and mapped_stage != stage:
            continue
        
        opportunities.append(canonical_opp)
    
    # ENHANCED: Aggregate activity counts for each opportunity
    for opp in opportunities:
        try:
            opp_id = opp.get("id")
            
            # Convert to int if possible for matching with Odoo res_id
            try:
                opp_id_int = int(opp_id)
            except (ValueError, TypeError):
                opp_id_int = None
            
            # Build activity query - match by res_id (int or string)
            if opp_id_int:
                activity_query = {
                    "entity_type": "activity",
                    "$or": [{"is_active": True}, {"is_active": {"$exists": False}}],
                    "data.res_model": "crm.lead",
                    "data.res_id": opp_id_int
                }
            else:
                activity_query = {
                    "entity_type": "activity",
                    "$or": [{"is_active": True}, {"is_active": {"$exists": False}}],
                    "data.res_model": "crm.lead",
                    "data.res_id": opp_id
                }
            
            activity_docs = await db.data_lake_serving.find(activity_query).to_list(100)
            
            # Count by status
            activities = [doc.get("data", {}) for doc in activity_docs]
            completed = len([a for a in activities if a.get("state") == "done"])
            pending = len([a for a in activities if a.get("state") not in ["done", "cancel", "cancelled"]])
            
            opp["completed_activities"] = completed
            opp["pending_activities"] = pending
            opp["total_activities"] = len(activities)
            
        except Exception as e:
            logger.error(f"Activity aggregation error for {opp.get('id')}: {e}")
            opp["completed_activities"] = 0
            opp["pending_activities"] = 0
            opp["total_activities"] = 0
    
    return opportunities

@router.get("/opportunities/kanban")
async def get_opportunities_kanban(
    token_data: dict = Depends(require_approved())
):
    """Get opportunities organized by stage for Kanban board"""
    db = Database.get_db()
    user_id = token_data["id"]
    user_role = token_data.get("role", "")
    
    query = {}
    if user_role == "account_manager":
        query["owner_id"] = user_id
    
    opportunities = await db.opportunities.find(query, {"_id": 0}).to_list(10000)
    
    # Get or create stages
    stages = await db.pipeline_stages.find({}, {"_id": 0}).sort("order", 1).to_list(100)
    if not stages:
        # Insert default stages
        for stage in DEFAULT_STAGES:
            await db.pipeline_stages.insert_one(stage)
        stages = DEFAULT_STAGES
    
    # Organize by stage
    kanban_data = {}
    for stage in stages:
        stage_id = stage["id"]
        stage_opps = [o for o in opportunities if o.get("stage") == stage_id]
        
        # Enrich each opportunity
        for opp in stage_opps:
            # Get activity count
            activity_count = await db.activities.count_documents({"opportunity_id": opp["id"]})
            opp["activity_count"] = activity_count
        
        kanban_data[stage_id] = {
            "stage": stage,
            "opportunities": stage_opps,
            "total_value": sum(o.get("value", 0) for o in stage_opps),
            "count": len(stage_opps)
        }
    
    return {"stages": stages, "kanban": kanban_data}

@router.get("/opportunities/{opp_id}")
async def get_opportunity(
    opp_id: str,
    token_data: dict = Depends(require_approved())
):
    """Get a single opportunity by ID"""
    db = Database.get_db()
    
    opportunity = await db.opportunities.find_one({"id": opp_id}, {"_id": 0})
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    return opportunity

@router.put("/opportunities/{opp_id}")
async def update_opportunity(
    opp_id: str,
    data: OpportunityUpdate,
    token_data: dict = Depends(require_approved())
):
    """Update an opportunity"""
    db = Database.get_db()
    
    opportunity = await db.opportunities.find_one({"id": opp_id})
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    await db.opportunities.update_one({"id": opp_id}, {"$set": update_data})
    
    updated = await db.opportunities.find_one({"id": opp_id}, {"_id": 0})
    return updated

# Stage transition rules - defines allowed transitions
# Format: { "from_stage": ["allowed_to_stage1", "allowed_to_stage2", ...] }
STAGE_TRANSITION_RULES = {
    "new": ["qualification", "lost"],
    "lead": ["qualification", "lost"],
    "qualification": ["discovery", "proposal", "lost"],
    "discovery": ["proposal", "negotiation", "lost"],
    "proposal": ["negotiation", "won", "lost"],
    "negotiation": ["won", "lost", "proposal"],  # Can go back to proposal
    "won": [],  # Closed stages cannot transition
    "lost": [],  # Closed stages cannot transition
    "closed_won": [],
    "closed_lost": [],
}

# Stages that are considered "closed" - cannot transition out
CLOSED_STAGES = ["won", "lost", "closed_won", "closed_lost"]


def validate_stage_transition(current_stage: str, new_stage: str) -> tuple[bool, str]:
    """
    Validate if a stage transition is allowed.
    Returns (is_valid, error_message)
    """
    current_normalized = current_stage.lower().replace(" ", "_")
    new_normalized = new_stage.lower().replace(" ", "_")
    
    # Same stage - always allowed (no-op)
    if current_normalized == new_normalized:
        return True, ""
    
    # Check if current stage is closed
    if current_normalized in CLOSED_STAGES:
        return False, f"Cannot move opportunity from '{current_stage}' - deal is already closed"
    
    # Check if transition is allowed
    allowed_transitions = STAGE_TRANSITION_RULES.get(current_normalized, [])
    
    # If no rules defined for this stage, allow any non-closed transition
    if not allowed_transitions and current_normalized not in STAGE_TRANSITION_RULES:
        if new_normalized in CLOSED_STAGES:
            return True, ""  # Allow closing from any undefined stage
        return True, ""  # Allow transition to any stage if not explicitly restricted
    
    if new_normalized not in [t.lower() for t in allowed_transitions]:
        allowed_list = ", ".join(allowed_transitions) if allowed_transitions else "none"
        return False, f"Cannot move from '{current_stage}' to '{new_stage}'. Allowed transitions: {allowed_list}"
    
    return True, ""


@router.patch("/opportunities/{opp_id}/stage")
async def update_opportunity_stage(
    opp_id: str,
    new_stage: str = Query(...),
    token_data: dict = Depends(require_approved())
):
    """
    Update only the stage of an opportunity (for drag-drop).
    Validates stage transitions against defined rules.
    """
    db = Database.get_db()
    
    opportunity = await db.opportunities.find_one({"id": opp_id})
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    current_stage = opportunity.get("stage", "new")
    
    # Validate stage transition
    is_valid, error_message = validate_stage_transition(current_stage, new_stage)
    if not is_valid:
        raise HTTPException(
            status_code=400, 
            detail={
                "error": "INVALID_STAGE_TRANSITION",
                "message": error_message,
                "current_stage": current_stage,
                "requested_stage": new_stage,
            }
        )
    
    # Get stage probability default
    stage = await db.pipeline_stages.find_one({"id": new_stage})
    new_probability = stage.get("probability_default", opportunity.get("probability", 10)) if stage else opportunity.get("probability", 10)
    
    # Log the transition
    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "action": "stage_transition",
        "entity_type": "opportunity",
        "entity_id": opp_id,
        "user_id": token_data["id"],
        "details": {
            "from_stage": current_stage,
            "to_stage": new_stage,
            "opportunity_name": opportunity.get("name"),
        },
        "timestamp": datetime.now(timezone.utc),
    })
    
    await db.opportunities.update_one(
        {"id": opp_id},
        {"$set": {
            "stage": new_stage,
            "probability": new_probability,
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    return {"message": "Stage updated", "stage": new_stage, "probability": new_probability}


@router.get("/stage-transitions")
async def get_stage_transition_rules(
    token_data: dict = Depends(require_approved())
):
    """Get the stage transition rules for frontend validation"""
    return {
        "rules": STAGE_TRANSITION_RULES,
        "closed_stages": CLOSED_STAGES,
    }


# ===================== BLUE SHEET PROBABILITY =====================

@router.post("/opportunities/{opp_id}/calculate-probability")
async def calculate_blue_sheet_probability(
    opp_id: str,
    analysis: BlueSheetAnalysis,
    token_data: dict = Depends(require_approved())
):
    """Calculate opportunity probability using Blue Sheet methodology with AI recommendations"""
    db = Database.get_db()
    
    opportunity = await db.opportunities.find_one({"id": opp_id}, {"_id": 0})
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    # Get configurable weights from database (or use defaults)
    weights_config = await db.bluesheet_config.find_one({}, {"_id": 0})
    if not weights_config:
        weights_config = {
            "economic_buyer_identified": 10,
            "economic_buyer_favorable": 10,
            "user_buyer_favorable_each": 3,
            "technical_buyer_favorable_each": 3,
            "coach_identified": 3,
            "coach_engaged": 2,
            "no_access_to_economic_buyer": -15,
            "reorganization_pending": -10,
            "budget_not_confirmed": -12,
            "competition_preferred": -15,
            "timeline_unclear": -8,
            "clear_business_results": 12,
            "quantifiable_value": 8,
            "next_steps_defined": 8,
            "mutual_action_plan": 7,
            "max_user_buyers": 3,
            "max_technical_buyers": 2,
            "max_possible_score": 75
        }
    
    # Base scoring
    score_breakdown = {}
    total_score = 0
    
    # Buying Influences (configurable weights)
    buying_influence_score = 0
    if analysis.economic_buyer_identified:
        buying_influence_score += weights_config.get("economic_buyer_identified", 10)
    if analysis.economic_buyer_favorable:
        buying_influence_score += weights_config.get("economic_buyer_favorable", 10)
    
    max_user = weights_config.get("max_user_buyers", 3)
    user_weight = weights_config.get("user_buyer_favorable_each", 3)
    buying_influence_score += min(analysis.user_buyers_favorable, max_user) * user_weight
    
    max_tech = weights_config.get("max_technical_buyers", 2)
    tech_weight = weights_config.get("technical_buyer_favorable_each", 3)
    buying_influence_score += min(analysis.technical_buyers_favorable, max_tech) * tech_weight
    
    if analysis.coach_identified:
        buying_influence_score += weights_config.get("coach_identified", 3)
    if analysis.coach_engaged:
        buying_influence_score += weights_config.get("coach_engaged", 2)
    score_breakdown["buying_influences"] = buying_influence_score
    total_score += buying_influence_score
    
    # Red Flags (negative points with configurable weights)
    red_flag_penalty = 0
    if analysis.no_access_to_economic_buyer:
        red_flag_penalty += weights_config.get("no_access_to_economic_buyer", -15)
    if analysis.reorganization_pending:
        red_flag_penalty += weights_config.get("reorganization_pending", -10)
    if analysis.budget_not_confirmed:
        red_flag_penalty += weights_config.get("budget_not_confirmed", -12)
    if analysis.competition_preferred:
        red_flag_penalty += weights_config.get("competition_preferred", -15)
    if analysis.timeline_unclear:
        red_flag_penalty += weights_config.get("timeline_unclear", -8)
    score_breakdown["red_flags"] = red_flag_penalty
    total_score += red_flag_penalty
    
    # Win Results (configurable weights)
    win_results_score = 0
    if analysis.clear_business_results:
        win_results_score += weights_config.get("clear_business_results", 12)
    if analysis.quantifiable_value:
        win_results_score += weights_config.get("quantifiable_value", 8)
    score_breakdown["win_results"] = win_results_score
    total_score += win_results_score
    
    # Action Plan (configurable weights)
    action_score = 0
    if analysis.next_steps_defined:
        action_score += weights_config.get("next_steps_defined", 8)
    if analysis.mutual_action_plan:
        action_score += weights_config.get("mutual_action_plan", 7)
    score_breakdown["action_plan"] = action_score
    total_score += action_score
    
    # Calculate probability (scale to 0-100) using configurable max
    max_possible = weights_config.get("max_possible_score", 75)
    calculated_probability = max(0, min(100, int((total_score / max_possible) * 100)))
    
    # Confidence level
    confidence = "low"
    if analysis.economic_buyer_identified and analysis.coach_identified:
        confidence = "medium"
    if analysis.economic_buyer_favorable and analysis.quantifiable_value and analysis.mutual_action_plan:
        confidence = "high"
    
    # Generate AI recommendations using centralized LLM Service
    recommendations = []
    try:
        from services.llm_service import LLMService
        
        context = f"""
        Opportunity: {opportunity.get('name')}
        Value: ${opportunity.get('value', 0):,.0f}
        Current Stage: {opportunity.get('stage')}
        Calculated Probability: {calculated_probability}%
        Product Lines: {', '.join(opportunity.get('product_lines', []))}
        
        Blue Sheet Analysis:
        - Economic Buyer Identified: {analysis.economic_buyer_identified}
        - Economic Buyer Favorable: {analysis.economic_buyer_favorable}
        - Coach Engaged: {analysis.coach_engaged}
        - Budget Confirmed: {not analysis.budget_not_confirmed}
        - Competition Preferred: {analysis.competition_preferred}
        - Clear Business Results: {analysis.clear_business_results}
        - Mutual Action Plan: {analysis.mutual_action_plan}
        
        For a cybersecurity consulting firm (services: MSSP, Application Security, Network Security, GRC),
        provide 3 specific actionable recommendations to improve win probability. Be concise.
        """
        
        # Use centralized LLM Service
        response = await LLMService.call_llm("deal_confidence", context)
        recommendations = [line.strip() for line in response.split("\\n") if line.strip() and len(line) > 10][:3]
        
        logger.info(f"LLM recommendations generated via centralized service: {len(recommendations)}")
        
    except Exception as e:
        logger.warning(f"LLM recommendation error: {e}")
        # Fallback recommendations
        if not analysis.economic_buyer_identified:
            recommendations.append("Identify and engage the Economic Buyer - the person with final budget authority")
        if not analysis.coach_identified:
            recommendations.append("Develop a Coach inside the organization who can guide your strategy")
        if analysis.budget_not_confirmed:
            Blue Sheet Analysis:
            - Economic Buyer Identified: {analysis.economic_buyer_identified}
            - Economic Buyer Favorable: {analysis.economic_buyer_favorable}
            - Coach Engaged: {analysis.coach_engaged}
            - Budget Confirmed: {not analysis.budget_not_confirmed}
            - Competition Preferred: {analysis.competition_preferred}
            - Clear Business Results: {analysis.clear_business_results}
            - Mutual Action Plan: {analysis.mutual_action_plan}
            
            For a cybersecurity consulting firm (services: MSSP, Application Security, Network Security, GRC),
            provide 3 specific actionable recommendations to improve win probability. Be concise.
            """
            
            chat = LlmChat(
                api_key=api_key,
                session_id=f"bluesheet-{opp_id}-{datetime.now().timestamp()}",
                system_message="You are a sales strategy expert specializing in B2B enterprise cybersecurity sales using Miller Heiman Blue Sheet methodology. Provide brief, actionable recommendations."
            ).with_model(model_provider, model_name)
            
            message = UserMessage(text=context)
            # send_message is async
            response = await chat.send_message(message)
            recommendations = [line.strip() for line in response.split("\n") if line.strip() and len(line) > 10][:3]
            logger.info(f"LLM recommendations generated: {len(recommendations)}")
            
    except Exception as e:
        logger.warning(f"LLM recommendation error: {e}")
        # Fallback recommendations
        if not analysis.economic_buyer_identified:
            recommendations.append("Identify and engage the Economic Buyer - the person with final budget authority")
        if not analysis.coach_identified:
            recommendations.append("Develop a Coach inside the organization who can guide your strategy")
        if analysis.budget_not_confirmed:
            recommendations.append("Confirm budget allocation and funding timeline with key stakeholders")
        if not analysis.mutual_action_plan:
            recommendations.append("Create a mutual action plan with clear milestones and commitments")
    
    # Update opportunity
    await db.opportunities.update_one(
        {"id": opp_id},
        {"$set": {
            "probability": calculated_probability,
            "blue_sheet_analysis": analysis.model_dump(),
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    # Generate summary
    summary = f"Based on Blue Sheet analysis, this opportunity has a {calculated_probability}% probability of closing. "
    if calculated_probability >= 70:
        summary += "Strong position with key buying influences engaged."
    elif calculated_probability >= 40:
        summary += "Moderate position - address red flags to improve odds."
    else:
        summary += "Weak position - significant gaps in sales strategy need attention."
    
    return {
        "opportunity_id": opp_id,
        "calculated_probability": calculated_probability,
        "confidence_level": confidence,
        "analysis_summary": summary,
        "recommendations": recommendations,
        "score_breakdown": score_breakdown
    }

# ===================== DASHBOARD STATS =====================

@router.get("/dashboard/stats")
async def get_dashboard_stats(
    token_data: dict = Depends(require_approved())
):
    """Get dashboard statistics for KPI cards"""
    db = Database.get_db()
    user_id = token_data["id"]
    user_role = token_data.get("role", "")
    
    query = {}
    if user_role == "account_manager":
        query["owner_id"] = user_id
    
    # Get all opportunities
    opportunities = await db.opportunities.find(query, {"_id": 0}).to_list(10000)
    
    # Calculate stats
    active_opps = [o for o in opportunities if o.get("stage") not in ["closed_won", "closed_lost"]]
    won_opps = [o for o in opportunities if o.get("stage") == "closed_won"]
    
    total_pipeline_value = sum(o.get("value", 0) for o in active_opps)
    won_revenue = sum(o.get("value", 0) for o in won_opps)
    
    # Activity stats
    activity_query = {}
    if user_role == "account_manager":
        activity_query["$or"] = [{"created_by_id": user_id}, {"assigned_to_id": user_id}]
    
    total_activities = await db.activities.count_documents(activity_query)
    completed_activities = await db.activities.count_documents({**activity_query, "status": "completed"})
    
    now = datetime.now(timezone.utc)
    overdue_activities = await db.activities.count_documents({
        **activity_query,
        "status": {"$in": ["pending", "in_progress"]},
        "due_date": {"$lt": now}
    })
    
    activity_completion_rate = int((completed_activities / total_activities * 100)) if total_activities > 0 else 0
    
    return {
        "total_pipeline_value": total_pipeline_value,
        "won_revenue": won_revenue,
        "active_opportunities": len(active_opps),
        "total_opportunities": len(opportunities),
        "activity_completion_rate": activity_completion_rate,
        "overdue_activities": overdue_activities,
        "total_activities": total_activities,
        "completed_activities": completed_activities
    }

# ===================== SALES METRICS =====================

@router.get("/sales-metrics/{user_id}")
async def get_sales_metrics(
    user_id: str,
    period: str = Query(default="quarterly", regex="^(monthly|quarterly|ytd)$"),
    token_data: dict = Depends(require_approved())
):
    """Get sales metrics for a user"""
    db = Database.get_db()
    
    # Determine period dates
    now = datetime.now(timezone.utc)
    if period == "monthly":
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "quarterly":
        quarter_month = ((now.month - 1) // 3) * 3 + 1
        period_start = now.replace(month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:  # ytd
        period_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Get closed won opportunities
    won_opps = await db.opportunities.find({
        "owner_id": user_id,
        "stage": "closed_won"
    }, {"_id": 0}).to_list(10000)
    
    # Calculate metrics
    orders_won = sum(o.get("value", 0) for o in won_opps)
    orders_booked = orders_won
    orders_invoiced = orders_won * 0.8
    orders_collected = orders_won * 0.6
    
    # Get user quota
    user = await db.users.find_one({"id": user_id}, {"quota": 1})
    quota = user.get("quota", 500000) if user else 500000
    
    attainment = (orders_won / quota * 100) if quota > 0 else 0
    
    # Calculate commission
    commission_earned = await calculate_commission(db, user_id, orders_won, attainment)
    
    return {
        "user_id": user_id,
        "period": period,
        "period_start": period_start.isoformat(),
        "period_end": now.isoformat(),
        "orders_won": orders_won,
        "orders_booked": orders_booked,
        "orders_invoiced": orders_invoiced,
        "orders_collected": orders_collected,
        "quota": quota,
        "attainment_percentage": round(attainment, 1),
        "commission_earned": commission_earned,
        "commission_projected": commission_earned * (100 / max(attainment, 1)) if attainment < 100 else commission_earned
    }

async def calculate_commission(db, user_id: str, revenue: float, attainment: float) -> float:
    """Calculate commission based on user's assigned template"""
    user = await db.users.find_one({"id": user_id}, {"commission_template_id": 1})
    
    if not user or not user.get("commission_template_id"):
        # Default 5% flat
        return revenue * 0.05
    
    template = await db.commission_templates.find_one({"id": user["commission_template_id"]}, {"_id": 0})
    if not template:
        return revenue * 0.05
    
    if template["template_type"] == "flat":
        return revenue * template.get("base_rate", 0.01)  # Default 1%
    
    elif template["template_type"] == "tiered_attainment":
        # Find applicable tier
        commission = revenue * template.get("base_rate", 0.05)
        for tier in sorted(template.get("tiers", []), key=lambda t: t.get("min_attainment", 0)):
            if tier.get("min_attainment", 0) <= attainment <= tier.get("max_attainment", 100):
                commission = revenue * template.get("base_rate", 0.05) * tier.get("multiplier", 1.0)
                break
        return commission
    
    return revenue * 0.05

# ===================== INCENTIVE CALCULATOR =====================

@router.post("/incentive-calculator")
async def calculate_incentive(
    revenue: float = Query(...),
    template_id: Optional[str] = Query(default=None),
    quota: float = Query(default=500000),
    is_new_logo: bool = Query(default=False),
    product_line: Optional[str] = Query(default=None),
    token_data: dict = Depends(require_approved())
):
    """Calculate commission/incentive for a deal"""
    db = Database.get_db()
    
    attainment = (revenue / quota * 100) if quota > 0 else 0
    base_rate = 0.05
    template_name = "Default (5% Flat)"
    multipliers_applied = []
    
    if template_id:
        template = await db.commission_templates.find_one({"id": template_id}, {"_id": 0})
        if template:
            base_rate = template.get("base_rate", 0.05)
            template_name = template.get("name", "Custom Template")
            
            # Apply tiered multiplier
            if template.get("template_type") == "tiered_attainment":
                for tier in sorted(template.get("tiers", []), key=lambda t: t.get("min_attainment", 0)):
                    if tier.get("min_attainment", 0) <= attainment <= tier.get("max_attainment", 100):
                        multipliers_applied.append({
                            "type": "attainment_tier",
                            "value": tier.get("multiplier", 1.0)
                        })
                        break
    
    base_commission = revenue * base_rate
    final_commission = base_commission
    
    # Apply multipliers
    for mult in multipliers_applied:
        final_commission *= mult["value"]
    
    # New logo multiplier (default 1.5x for cybersecurity)
    if is_new_logo:
        new_logo_mult = 1.5
        multipliers_applied.append({"type": "new_logo", "value": new_logo_mult})
        final_commission *= new_logo_mult
    
    # Product line weight
    if product_line and product_line in PRODUCT_LINE_WEIGHTS:
        weight = PRODUCT_LINE_WEIGHTS[product_line]
        if weight != 1.0:
            multipliers_applied.append({"type": f"product_{product_line.lower().replace(' ', '_')}", "value": weight})
            final_commission *= weight
    
    return {
        "revenue": revenue,
        "quota": quota,
        "attainment": round(attainment, 1),
        "template_name": template_name,
        "base_rate": base_rate,
        "base_commission": base_commission,
        "multipliers_applied": multipliers_applied,
        "final_commission": round(final_commission, 2)
    }

# ===================== COMMISSION TEMPLATES =====================

@router.get("/commission-templates")
async def get_commission_templates(
    token_data: dict = Depends(require_approved())
):
    """Get all commission templates"""
    db = Database.get_db()
    templates = await db.commission_templates.find({}, {"_id": 0}).to_list(100)
    
    # Add default templates if none exist
    if not templates:
        default_templates = [
            {
                "id": str(uuid.uuid4()),
                "name": "Cybersecurity Standard",
                "description": "Standard tiered commission for cybersecurity sales",
                "template_type": "tiered_attainment",
                "base_rate": 0.01,  # Changed from 0.05 (5%) to 0.01 (1%)
                "tiers": [
                    {"min_attainment": 0, "max_attainment": 50, "multiplier": 0.5},
                    {"min_attainment": 50, "max_attainment": 100, "multiplier": 1.0},
                    {"min_attainment": 100, "max_attainment": 150, "multiplier": 1.5},
                    {"min_attainment": 150, "max_attainment": 200, "multiplier": 2.0},
                ],
                "product_weights": PRODUCT_LINE_WEIGHTS,
                "new_logo_multiplier": 1.5,
                "created_at": datetime.now(timezone.utc)
            },
            {
                "id": str(uuid.uuid4()),
                "name": "MSSP Recurring Revenue",
                "description": "Higher base rate for managed services with recurring revenue",
                "template_type": "tiered_attainment",
                "base_rate": 0.08,
                "tiers": [
                    {"min_attainment": 0, "max_attainment": 75, "multiplier": 0.8},
                    {"min_attainment": 75, "max_attainment": 100, "multiplier": 1.0}
                ]
            }
        ]


@router.post("/users/{user_id}/commission-template")
async def assign_commission_template_to_user(
    user_id: str,
    template_id: str,
    token_data: dict = Depends(require_approved())
):
    """
    Assign a commission template to a specific user.
    Enables per-person commission rate customization.
    """
    db = Database.get_db()
    
    # Verify user exists
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify template exists
    template = await db.commission_templates.find_one({"id": template_id})
    if not template:
        raise HTTPException(status_code=404, detail="Commission template not found")
    
    # Assign template to user
    await db.users.update_one(
        {"id": user_id},
        {
            "$set": {
                "commission_template_id": template_id,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    logger.info(f"Assigned commission template {template.get('name')} to user {user.get('email')}")
    
    return {
        "message": "Commission template assigned",
        "user_id": user_id,
        "template_name": template.get("name"),
        "base_rate": template.get("base_rate", 0.01)
    }


# ===================== ACCOUNTS =====================
    
    return templates

@router.post("/commission-templates")
async def create_commission_template(
    data: CommissionTemplateCreate,
    token_data: dict = Depends(require_approved())
):
    """Create a new commission template"""
    db = Database.get_db()
    
    template = {
        "id": str(uuid.uuid4()),
        **data.model_dump(),
        "created_at": datetime.now(timezone.utc),
        "created_by": token_data["id"]
    }
    
    await db.commission_templates.insert_one(template)
    template.pop("_id", None)
    return template

# ===================== GLOBAL SEARCH =====================

@router.get("/search")
async def global_search(
    q: str = Query(..., min_length=2),
    token_data: dict = Depends(require_approved())
):
    """Global search across accounts, opportunities, activities"""
    db = Database.get_db()
    user_id = token_data["id"]
    user_role = token_data.get("role", "")
    
    results = []
    search_regex = {"$regex": q, "$options": "i"}
    
    # Search accounts
    account_query = {"$or": [{"name": search_regex}, {"industry": search_regex}]}
    if user_role == "account_manager":
        account_query["assigned_am_id"] = user_id
    
    accounts = await db.accounts.find(account_query, {"_id": 0, "id": 1, "name": 1}).limit(10).to_list(10)
    for acc in accounts:
        results.append({"type": "account", "id": acc["id"], "name": acc["name"]})
    
    # Search opportunities
    opp_query = {"name": search_regex}
    if user_role == "account_manager":
        opp_query["owner_id"] = user_id
    
    opportunities = await db.opportunities.find(opp_query, {"_id": 0, "id": 1, "name": 1}).limit(10).to_list(10)
    for opp in opportunities:
        results.append({"type": "opportunity", "id": opp["id"], "name": opp["name"]})
    
    # Search activities
    activity_query = {"title": search_regex}
    if user_role == "account_manager":
        activity_query["$or"] = [{"created_by_id": user_id}, {"assigned_to_id": user_id}]
    
    activities = await db.activities.find(activity_query, {"_id": 0, "id": 1, "title": 1}).limit(10).to_list(10)
    for act in activities:
        results.append({"type": "activity", "id": act["id"], "name": act["title"]})
    
    return {"results": results, "query": q}

# ===================== ACTIVITIES =====================

@router.get("/activities")
async def get_activities(
    status: Optional[str] = None,
    opportunity_id: Optional[str] = None,
    account_id: Optional[str] = None,
    include_system: bool = False,
    activity_type: Optional[str] = None,
    token_data: dict = Depends(require_approved())
):
    """
    Get activities with filters.
    By default, excludes system events (user_login, data_synced).
    Use include_system=true to see all activities.
    """
    db = Database.get_db()
    user_id = token_data["id"]
    user_role = token_data.get("role", "")
    is_super_admin = token_data.get("is_super_admin", False)
    
    query = {}
    
    # Role-based filtering (admins see all, others see their own)
    if not is_super_admin and user_role == "account_manager":
        query["$or"] = [{"created_by_id": user_id}, {"assigned_to_id": user_id}, {"user_id": user_id}]
    
    # Exclude system events by default (login, sync events)
    system_event_types = ["user_login", "data_synced", "system"]
    if not include_system:
        query["activity_type"] = {"$nin": system_event_types}
    
    # Filter by specific activity type if provided
    if activity_type:
        query["activity_type"] = activity_type
    
    if status:
        query["status"] = status
    if opportunity_id:
        query["opportunity_id"] = opportunity_id
    if account_id:
        query["account_id"] = account_id
    
    # Sort by created_at descending (most recent first), fallback to due_date
    activities = await db.activities.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return activities


@router.get("/activities/stats")
async def get_activity_stats(
    token_data: dict = Depends(require_approved())
):
    """Get activity statistics - counts by type"""
    db = Database.get_db()
    
    # System event types to separate
    system_event_types = ["user_login", "data_synced", "system"]
    
    # Count total
    total = await db.activities.count_documents({})
    
    # Count business activities (non-system)
    business = await db.activities.count_documents({
        "activity_type": {"$nin": system_event_types}
    })
    
    # Count system events
    system = await db.activities.count_documents({
        "activity_type": {"$in": system_event_types}
    })
    
    # Count by type
    pipeline = [
        {"$group": {"_id": "$activity_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    type_counts = {}
    async for doc in db.activities.aggregate(pipeline):
        type_counts[doc["_id"] or "unknown"] = doc["count"]
    
    # Count today's activities
    from datetime import datetime, timezone, timedelta
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_business = await db.activities.count_documents({
        "activity_type": {"$nin": system_event_types},
        "created_at": {"$gte": today_start}
    })
    
    return {
        "total": total,
        "business_activities": business,
        "system_events": system,
        "today_business": today_business,
        "by_type": type_counts
    }


@router.get("/activities/opportunity/{opp_id}")
async def get_activities_for_opportunity(
    opp_id: str,
    token_data: dict = Depends(require_approved())
):
    """
    Get activities linked to a specific opportunity.
    Returns Odoo mail.activity records for this opportunity.
    """
    from services.field_mapper import get_field_mapper
    
    db = Database.get_db()
    mapper = get_field_mapper()
    
    activities = []
    
    # Try to parse as integer for Odoo matching
    try:
        odoo_id = int(opp_id) if opp_id.isdigit() else int(opp_id)
    except (ValueError, TypeError):
        odoo_id = None
    
    if odoo_id:
        # Query Odoo activities from data_lake_serving
        odoo_activities = await db.data_lake_serving.find({
            "entity_type": "activity",
            "$or": [{"is_active": True}, {"is_active": {"$exists": False}}],
            "data.res_model": "crm.lead",
            "data.res_id": odoo_id
        }).to_list(100)
        
        for act_doc in odoo_activities:
            data = act_doc.get("data", {})
            
            # Use mapper to properly extract activity fields
            canonical_activity = mapper.map_activity(data)
            
            # Map state to status for frontend
            state = canonical_activity.get("state", "planned")
            if state == "done":
                status = "completed"
            elif state in ["overdue", "today"]:
                status = "pending"
            else:
                status = "pending"
            
            canonical_activity["status"] = status
            
            activities.append(canonical_activity)
    
    return {
        "opportunity_id": opp_id,
        "activities": activities,
        "count": len(activities)
    }


@router.post("/activities")
async def create_activity(
    data: ActivityCreate,
    token_data: dict = Depends(require_approved())
):
    """Create a new activity"""
    db = Database.get_db()
    user_id = token_data["id"]
    
    now = datetime.now(timezone.utc)
    activity_id = str(uuid.uuid4())
    
    activity = {
        "id": activity_id,
        **data.model_dump(),
        
        # NEW: Multi-dimensional linkages
        "portfolio_id": None,  # Will be set via separate endpoint
        "initiative_id": None,
        "goal_ids": [],
        "kpi_ids": [],
        
        # Outcome tracking
        "outcome": None,
        
        "created_by_id": user_id,
        "created_by_name": token_data.get("name", ""),
        "assigned_to_id": data.account_id or user_id,
        "completed_at": None,
        "created_at": now,
        "updated_at": now
    }
    
    await db.activities.insert_one(activity)
    
    # Log activity creation
    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "action": "activity_created",
        "user_id": user_id,
        "details": {"activity_id": activity_id, "title": data.title},
        "timestamp": now
    })
    
    return {"id": activity_id, "message": "Activity created successfully"}



@router.get("/opportunities/{opp_id}/messages")
async def get_opportunity_messages(
    opp_id: str,
    token_data: dict = Depends(require_approved())
):
    """
    Get chatter messages/communication history for an opportunity.
    Shows notes, emails, status changes from Odoo.
    """
    db = Database.get_db()
    
    # Convert to int for Odoo ID matching
    try:
        opp_odoo_id = int(opp_id)
    except (ValueError, TypeError):
        opp_odoo_id = opp_id
    
    # Query messages from data_lake_serving
    message_docs = await db.data_lake_serving.find({
        "entity_type": "message",
        "$or": [{"is_active": True}, {"is_active": {"$exists": False}}],
        "data.res_model": "crm.lead",
        "data.res_id": opp_odoo_id
    }).sort([("data.date", -1)]).to_list(100)
    
    messages = []
    for doc in message_docs:
        msg = doc.get("data", {})
        
        messages.append({
            "id": msg.get("id"),
            "body": msg.get("body", ""),
            "date": msg.get("date"),
            "message_type": msg.get("message_type"),
            "subtype_name": msg.get("subtype_name"),
            "author_name": msg.get("author_name", "System"),
            "author_id": msg.get("author_id"),
            "email_from": msg.get("email_from"),
            "subject": msg.get("subject"),
        })
    
    return {
        "messages": messages,
        "count": len(messages),
        "opportunity_id": opp_id
    }


@router.patch("/activities/{activity_id}/complete")
async def complete_activity_with_outcome(
    activity_id: str,
    outcome: dict,
    token_data: dict = Depends(require_approved())
):
    """
    Mark activity as completed and record outcome.
    Auto-updates linked initiative progress and goal progress.
    """
    db = Database.get_db()
    user_id = token_data["id"]
    now = datetime.now(timezone.utc)
    
    # Get activity
    activity = await db.activities.find_one({"id": activity_id})
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    # Update activity
    await db.activities.update_one(
        {"id": activity_id},
        {
            "$set": {
                "status": "completed",
                "completed_at": now,
                "outcome": {
                    "recorded": True,
                    "success": outcome.get("success", True),
                    "notes": outcome.get("notes", ""),
                    "next_steps": outcome.get("next_steps", ""),
                    "recorded_at": now,
                    "recorded_by": user_id
                },
                "updated_at": now
            }
        }
    )
    
    # Update linked initiative progress
    initiative_id = activity.get("initiative_id")
    if initiative_id:
        # Increment activity completion count
        activity_type = activity.get("activity_type", "other")
        await db.initiatives.update_one(
            {"id": initiative_id},
            {
                "$inc": {f"activity_template.{activity_type}.completed": 1},
                "$set": {"updated_at": now}
            }
        )
    
    return {
        "activity_id": activity_id,
        "completed_at": now,
        "outcome": outcome,
        "updated_initiative": initiative_id
    }

    activity.pop("_id", None)
    return activity

@router.patch("/activities/{activity_id}/status")
async def update_activity_status(
    activity_id: str,
    status: str = Query(...),
    token_data: dict = Depends(require_approved())
):
    """Update activity status"""
    db = Database.get_db()
    
    update_data = {"status": status, "updated_at": datetime.now(timezone.utc)}
    if status == "completed":
        update_data["completed_at"] = datetime.now(timezone.utc)
    
    result = await db.activities.update_one({"id": activity_id}, {"$set": update_data})
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    return {"message": "Status updated", "status": status}

# ===================== ACCOUNTS =====================

class AccountCreate(BaseModel):
    name: str
    industry: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    annual_revenue: Optional[float] = None
    employee_count: Optional[int] = None

@router.get("/accounts")
async def get_accounts(
    token_data: dict = Depends(require_approved())
):
    """Get accounts"""
    db = Database.get_db()
    user_id = token_data["id"]
    user_role = token_data.get("role", "")
    
    query = {}
    if user_role == "account_manager":
        query["assigned_am_id"] = user_id
    
    accounts = await db.accounts.find(query, {"_id": 0}).to_list(1000)
    return accounts

@router.post("/accounts")
async def create_account(
    data: AccountCreate,
    token_data: dict = Depends(require_approved())
):
    """Create a new account"""
    db = Database.get_db()
    user_id = token_data["id"]
    
    now = datetime.now(timezone.utc)
    account_id = str(uuid.uuid4())
    
    account = {
        "id": account_id,
        **data.model_dump(),
        "assigned_am_id": user_id,
        "assigned_am_name": token_data.get("name", ""),
        "created_at": now,
        "updated_at": now
    }
    
    await db.accounts.insert_one(account)
    account.pop("_id", None)
    return account

# ===================== LLM CONFIG =====================

@router.get("/config/llm")
async def get_llm_config(
    token_data: dict = Depends(require_approved())
):
    """Get LLM configuration"""
    db = Database.get_db()
    config = await db.llm_config.find_one({}, {"_id": 0})
    
    if not config:
        config = {
            "provider": "openai",
            "model": "gpt-4o",
            "api_key_set": bool(settings.EMERGENT_LLM_KEY),
            "use_emergent_key": True
        }
    else:
        # Don't expose API key
        config["api_key_set"] = bool(config.get("api_key") or settings.EMERGENT_LLM_KEY)
        config.pop("api_key", None)
    
    return config

@router.put("/config/llm")
async def update_llm_config(
    provider: str = Query(default="openai"),
    model: str = Query(default="gpt-4o"),
    api_key: Optional[str] = Query(default=None),
    use_emergent_key: bool = Query(default=True),
    token_data: dict = Depends(require_approved())
):
    """Update LLM configuration"""
    db = Database.get_db()
    
    config = {
        "provider": provider,
        "model": model,
        "use_emergent_key": use_emergent_key,
        "updated_at": datetime.now(timezone.utc),
        "updated_by": token_data["id"]
    }
    
    if api_key and not use_emergent_key:
        config["api_key"] = api_key
    
    await db.llm_config.update_one({}, {"$set": config}, upsert=True)
    
    return {"message": "LLM configuration updated", "provider": provider, "model": model}

# ===================== KPIs =====================

class KPICreate(BaseModel):
    name: str
    target_value: float
    current_value: float = 0
    unit: str = "currency"
    period: str = "monthly"
    category: str = "sales"
    product_line: Optional[str] = None

@router.get("/kpis")
async def get_kpis(
    category: Optional[str] = None,
    token_data: dict = Depends(require_approved())
):
    """Get all KPIs"""
    db = Database.get_db()
    user_id = token_data["id"]
    is_super_admin = token_data.get("is_super_admin", False)
    
    # Build query - super admins see all KPIs, others see their own or unassigned
    if is_super_admin:
        query = {}
    else:
        query = {
            "$or": [
                {"owner_id": user_id},
                {"user_id": user_id},
                {"owner_id": {"$exists": False}},
                {"user_id": {"$exists": False}}
            ]
        }
    
    if category:
        query["category"] = category
    
    kpis = await db.kpis.find(query, {"_id": 0}).to_list(100)
    return kpis

@router.post("/kpis")
async def create_kpi(
    data: KPICreate,
    token_data: dict = Depends(require_approved())
):
    """Create a new KPI"""
    db = Database.get_db()
    user_id = token_data["id"]
    now = datetime.now(timezone.utc)
    
    kpi = {
        "id": str(uuid.uuid4()),
        "owner_id": user_id,
        **data.model_dump(),
        "created_at": now,
        "updated_at": now
    }
    
    await db.kpis.insert_one(kpi)
    kpi.pop("_id", None)
    return kpi

@router.put("/kpis/{kpi_id}")
async def update_kpi(
    kpi_id: str,
    data: KPICreate,
    token_data: dict = Depends(require_approved())
):
    """Update a KPI"""
    db = Database.get_db()
    
    update_data = {**data.model_dump(), "updated_at": datetime.now(timezone.utc)}
    result = await db.kpis.update_one({"id": kpi_id}, {"$set": update_data})
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="KPI not found")
    
    updated = await db.kpis.find_one({"id": kpi_id}, {"_id": 0})
    return updated

@router.delete("/kpis/{kpi_id}")
async def delete_kpi(
    kpi_id: str,
    token_data: dict = Depends(require_approved())
):
    """Delete a KPI"""
    db = Database.get_db()
    
    result = await db.kpis.delete_one({"id": kpi_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="KPI not found")
    
    return {"message": "KPI deleted"}


# ===================== DATA LAKE DASHBOARD (REAL ODOO DATA) =====================

@router.get("/dashboard/real")
async def get_real_dashboard(
    token_data: dict = Depends(require_approved())
):
    """
    Get dashboard data from data_lake_serving (real Odoo-synced data).
    This is the source of truth for beta.
    Access is controlled by Odoo salesperson/team assignment AND manager hierarchy.
    
    Manager visibility:
    - Managers can see all records assigned to their direct reports
    - This is based on the manager_odoo_id field in users collection
    """
    db = Database.get_db()
    user_id = token_data["id"]
    user_email = token_data.get("email", "").lower()
    user_role = token_data.get("role", "")
    
    # Get full user details including Odoo enrichment
    user_doc = await db.users.find_one({"id": user_id})
    is_super_admin = user_doc.get("is_super_admin", False) if user_doc else False
    
    # Get Odoo identifiers for filtering
    odoo_salesperson_name = (user_doc.get("odoo_salesperson_name") or "").lower() if user_doc else ""
    odoo_user_id = user_doc.get("odoo_user_id") if user_doc else None
    odoo_employee_id = user_doc.get("odoo_employee_id") if user_doc else None
    odoo_team_id = user_doc.get("odoo_team_id") if user_doc else None
    
    # Build list of subordinate employee IDs (people this user manages)
    subordinate_user_ids = set()
    subordinate_employee_ids = set()
    subordinate_salesperson_names = set()
    subordinate_emails = set()  # ADD: Track subordinate emails
    
    if odoo_employee_id:
        # Find all users where manager_odoo_id matches current user's employee_id
        subordinates = await db.users.find(
            {"manager_odoo_id": odoo_employee_id},
            {"odoo_user_id": 1, "odoo_employee_id": 1, "odoo_salesperson_name": 1, "email": 1}
        ).to_list(100)
        
        for sub in subordinates:
            if sub.get("odoo_user_id"):
                subordinate_user_ids.add(sub["odoo_user_id"])
            if sub.get("odoo_employee_id"):
                subordinate_employee_ids.add(sub["odoo_employee_id"])
            if sub.get("odoo_salesperson_name"):
                subordinate_salesperson_names.add(sub["odoo_salesperson_name"].lower())
            if sub.get("email"):
                subordinate_salesperson_names.add(sub["email"].lower())
                subordinate_emails.add(sub["email"].lower())  # ADD: Store email separately
        
        logger.info(f"User {user_email} (emp_id={odoo_employee_id}) manages {len(subordinates)} subordinates: user_ids={subordinate_user_ids}, emails={subordinate_emails}")
    
    def user_has_access_to_record(record_data):
        """
        Check if current user has access to a record based on Odoo assignment.
        
        Access granted if:
        1. User is super admin
        2. User is the assigned salesperson (by ID, name, or email)
        3. User is on the same team
        4. User is the MANAGER of the assigned salesperson (hierarchy visibility)
        
        CRITICAL: Uses strict matching to prevent cross-user data leaks.
        """
        if is_super_admin:
            return True
        
        salesperson_name = (record_data.get("salesperson_name") or "").lower().strip()
        salesperson_id = record_data.get("salesperson_id")
        record_team_id = record_data.get("team_id")
        
        # STRICT matching by salesperson ID (most reliable)
        if odoo_user_id and salesperson_id:
            try:
                if int(odoo_user_id) == int(salesperson_id):
                    return True
            except (ValueError, TypeError):
                pass
        
        # STRICT matching by salesperson name (exact, case-insensitive)
        if odoo_salesperson_name and salesperson_name and odoo_salesperson_name == salesperson_name:
            return True
        
        # STRICT matching by team
        if odoo_team_id and record_team_id:
            try:
                if int(odoo_team_id) == int(record_team_id):
                    return True
            except (ValueError, TypeError):
                pass
        
        # Fallback: Check if user's email is the salesperson's email
        record_email = (record_data.get("salesperson_email") or salesperson_name or "").lower().strip()
        if user_email and record_email and user_email == record_email:
            return True
        
        # CRITICAL FIX: MANAGER HIERARCHY - Check if current user manages the salesperson
        # This allows managers to see their subordinates' opportunities
        if salesperson_id:
            # Check if this salesperson_id belongs to any of our subordinates
            if salesperson_id in subordinate_user_ids:
                logger.debug(f"Manager access granted: {user_email} manages salesperson_id={salesperson_id}")
                return True
        
        # Also check by salesperson name if ID match didn't work
        if salesperson_name:
            # Check if salesperson name matches any subordinate
            if salesperson_name in subordinate_salesperson_names:
                logger.debug(f"Manager access granted: {user_email} manages {salesperson_name}")
                return True
            
            # Check if salesperson email matches any subordinate
            if any(salesperson_name in sub_name for sub_name in subordinate_salesperson_names):
                logger.debug(f"Manager access granted: {user_email} manages user with name containing {salesperson_name}")
                return True
        
        return False
    
    # ---- OPPORTUNITIES FROM DATA LAKE ----
    opportunities_data = []
    opp_docs = await db.data_lake_serving.find(active_entity_filter("opportunity")).to_list(1000)
    
    for doc in opp_docs:
        opp = doc.get("data", {})
        
        # Odoo-based access control
        if not user_has_access_to_record(opp):
            continue
        
        opportunities_data.append({
            "id": opp.get("id"),
            "name": opp.get("name", ""),
            "account_name": opp.get("partner_name", ""),
            "value": float(opp.get("expected_revenue", 0) or 0),
            "probability": float(opp.get("probability", 0) or 0),
            "stage": opp.get("stage_name", "New"),
            "salesperson": opp.get("salesperson_name", ""),
            "source": "odoo",
            "last_synced": doc.get("last_aggregated"),
        })
    
    # ---- ACCOUNTS FROM DATA LAKE ----
    accounts_data = []
    acc_docs = await db.data_lake_serving.find(active_entity_filter("account")).to_list(1000)
    
    for doc in acc_docs:
        acc = doc.get("data", {})
        
        # Filter accounts by salesperson assignment (if set)
        if not is_super_admin and acc.get("salesperson_name"):
            if not user_has_access_to_record(acc):
                continue
        
        accounts_data.append({
            "id": acc.get("id"),
            "name": acc.get("name", ""),
            "email": acc.get("email", ""),
            "phone": acc.get("phone", ""),
            "city": acc.get("city", ""),
            "source": "odoo",
            "last_synced": doc.get("last_aggregated"),
        })
    
    # ---- INVOICES FROM DATA LAKE ----
    invoices_data = []
    inv_docs = await db.data_lake_serving.find(active_entity_filter("invoice")).to_list(1000)
    
    for doc in inv_docs:
        inv = doc.get("data", {})
        invoices_data.append({
            "id": inv.get("id"),
            "invoice_number": inv.get("invoice_number", inv.get("name", "")),
            "customer_name": inv.get("customer_name", inv.get("partner_name", "")),
            "total_amount": float(inv.get("total_amount", inv.get("amount_total", 0)) or 0),
            "amount_due": float(inv.get("amount_due", inv.get("amount_residual", 0)) or 0),
            "payment_status": inv.get("payment_status", inv.get("payment_state", "pending")),
            "invoice_date": inv.get("invoice_date"),
            "due_date": inv.get("due_date"),
            "source": "odoo",
            "last_synced": doc.get("last_aggregated"),
        })
    
    # ---- CALCULATE METRICS ----
    total_pipeline = sum(o["value"] for o in opportunities_data if o["stage"] not in ["Won", "Lost", "Closed Won", "Closed Lost"])
    won_revenue = sum(o["value"] for o in opportunities_data if o["stage"] in ["Won", "Closed Won"])
    active_opps = len([o for o in opportunities_data if o["stage"] not in ["Won", "Lost", "Closed Won", "Closed Lost"]])
    
    # Invoice metrics
    total_receivables = sum(i["amount_due"] for i in invoices_data)
    pending_invoices = len([i for i in invoices_data if i["payment_status"] not in ["paid", "in_payment"]])
    
    return {
        "source": "data_lake_serving",
        "data_note": "Real Odoo-synced data. More data will sync as integration expands.",
        "metrics": {
            "pipeline_value": total_pipeline,
            "won_revenue": won_revenue,
            "active_opportunities": active_opps,
            "total_receivables": total_receivables,
            "pending_invoices": pending_invoices,
        },
        "opportunities": opportunities_data,
        "accounts": accounts_data,
        "invoices": invoices_data,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

@router.get("/receivables")
async def get_receivables(
    token_data: dict = Depends(require_approved())
):
    """
    Get receivables/invoices from data_lake_serving.
    Shows real Odoo-synced finance data.
    """
    db = Database.get_db()
    
    # Get invoices from data lake
    invoices = []
    inv_docs = await db.data_lake_serving.find(active_entity_filter("invoice")).to_list(1000)
    
    for doc in inv_docs:
        inv = doc.get("data", {})
        
        # Extract salesperson info (Odoo format: [id, "Name"] or just id)
        salesperson_id = inv.get("invoice_user_id") or inv.get("user_id")
        salesperson_name = ""
        if isinstance(salesperson_id, list) and len(salesperson_id) > 1:
            salesperson_name = salesperson_id[1]
        elif isinstance(salesperson_id, str):
            salesperson_name = salesperson_id
        
        # Extract partner/account info
        partner_id = inv.get("partner_id")
        partner_name = inv.get("customer_name") or inv.get("partner_name", "")
        if isinstance(partner_id, list) and len(partner_id) > 1:
            partner_name = partner_id[1]
        
        invoices.append({
            "id": inv.get("id"),
            "invoice_number": inv.get("invoice_number", inv.get("name", "")),
            "customer_name": partner_name,
            "account_id": partner_id[0] if isinstance(partner_id, list) else partner_id,
            "salesperson": salesperson_name,
            "total_amount": float(inv.get("total_amount", inv.get("amount_total", 0)) or 0),
            "amount_due": float(inv.get("amount_due", inv.get("amount_residual", 0)) or 0),
            "amount_paid": float(inv.get("amount_paid", 0) or 0),
            "payment_status": inv.get("payment_status", inv.get("payment_state", "pending")),
            "invoice_date": inv.get("invoice_date"),
            "due_date": inv.get("due_date"),
            "currency": inv.get("currency", "USD"),
            "source": "odoo",
            "last_synced": doc.get("last_aggregated"),
        })
    
    # Calculate summary
    total_receivables = sum(i["amount_due"] for i in invoices)
    total_collected = sum(i["amount_paid"] for i in invoices)
    overdue_count = len([i for i in invoices if i["payment_status"] == "not_paid"])
    
    return {
        "source": "data_lake_serving",
        "data_note": "More invoices will sync as integration expands.",
        "summary": {
            "total_receivables": total_receivables,
            "total_collected": total_collected,
            "pending_count": len([i for i in invoices if i["payment_status"] not in ["paid", "in_payment"]]),
            "overdue_count": overdue_count,
        },
        "invoices": invoices,
    }

@router.get("/opportunities/real")
async def get_real_opportunities(
    token_data: dict = Depends(require_approved())
):
    """
    Get opportunities from data_lake_serving (real Odoo data).
    """
    db = Database.get_db()
    user_id = token_data["id"]
    user_email = token_data.get("email", "")
    user_role = token_data.get("role", "")
    is_super_admin = token_data.get("is_super_admin", False)
    
    opportunities = []
    opp_docs = await db.data_lake_serving.find(active_entity_filter("opportunity")).to_list(1000)
    
    for doc in opp_docs:
        opp = doc.get("data", {})
        
        # Team-based filtering for non-admin users
        if not is_super_admin and user_role == "account_manager":
            salesperson = opp.get("salesperson_name", "")
            if salesperson and user_email not in salesperson:
                continue
        
        opportunities.append({
            "id": opp.get("id"),
            "name": opp.get("name", ""),
            "account_name": opp.get("partner_name", ""),
            "value": float(opp.get("expected_revenue", 0) or 0),
            "probability": float(opp.get("probability", 0) or 0),
            "stage": opp.get("stage_name", "New"),
            "salesperson": opp.get("salesperson_name", ""),
            "expected_close_date": opp.get("date_deadline"),
            "description": opp.get("description") if opp.get("description") != False else None,
            "source": "odoo",
            "last_synced": doc.get("last_aggregated"),
        })
    
    return {
        "source": "data_lake_serving",
        "opportunities": opportunities,
        "count": len(opportunities),
    }

@router.get("/accounts/real")
async def get_real_accounts(
    token_data: dict = Depends(require_approved())
):
    """
    Get accounts from data_lake_serving (real Odoo data).
    Shows synced customer/partner data from ERP.
    Aggregates pipeline and won revenue from related opportunities.
    """
    db = Database.get_db()
    
    # Helper to handle Odoo's False values
    def clean_value(val, default=""):
        if val is False or val is None:
            return default
        return val
    
    # Helper to infer industry from company name
    def infer_industry(name: str) -> str:
        name_lower = name.lower()
        
        # Industry patterns based on common naming conventions
        if any(kw in name_lower for kw in ["tech", "software", "data", "cyber", "cloud", "digital", "systems", "solutions"]):
            return "Technology"
        elif any(kw in name_lower for kw in ["bank", "finance", "capital", "invest", "financial"]):
            return "Financial Services"
        elif any(kw in name_lower for kw in ["health", "medical", "pharma", "bio", "care"]):
            return "Healthcare"
        elif any(kw in name_lower for kw in ["retail", "shop", "store", "commerce", "mart"]):
            return "Retail"
        elif any(kw in name_lower for kw in ["global", "corp", "enterprise", "inc", "llc", "ltd"]):
            return "Enterprise"
        elif any(kw in name_lower for kw in ["security", "secure", "protect"]):
            return "Cybersecurity"
        elif any(kw in name_lower for kw in ["consult", "advisory", "service"]):
            return "Consulting"
        elif any(kw in name_lower for kw in ["manufact", "industrial", "engineering"]):
            return "Manufacturing"
        
        return ""
    
    # First, get all opportunities to calculate account-level metrics
    opp_docs = await db.data_lake_serving.find(active_entity_filter("opportunity")).to_list(1000)
    
    # Build a map of partner_name -> metrics
    account_metrics = {}
    for doc in opp_docs:
        opp = doc.get("data", {})
        partner_name = clean_value(opp.get("partner_name"), "").strip().lower()
        if not partner_name:
            continue
        
        if partner_name not in account_metrics:
            account_metrics[partner_name] = {
                "pipeline_value": 0,
                "won_value": 0,
                "active_count": 0,
                "total_count": 0
            }
        
        value = float(opp.get("expected_revenue", 0) or 0)
        stage = clean_value(opp.get("stage_name"), "").lower()
        
        account_metrics[partner_name]["total_count"] += 1
        
        if "won" in stage:
            account_metrics[partner_name]["won_value"] += value
        elif "lost" not in stage:
            account_metrics[partner_name]["pipeline_value"] += value
            account_metrics[partner_name]["active_count"] += 1
    
    # Get accounts
    accounts = []
    acc_docs = await db.data_lake_serving.find(active_entity_filter("account")).to_list(1000)
    
    for doc in acc_docs:
        acc = doc.get("data", {})
        name = clean_value(acc.get("name"), "")
        
        # Skip accounts with empty names (invalid data)
        if not name.strip():
            continue
        
        # Get metrics for this account
        name_key = name.strip().lower()
        metrics = account_metrics.get(name_key, {
            "pipeline_value": 0,
            "won_value": 0,
            "active_count": 0,
            "total_count": 0
        })
        
        accounts.append({
            "id": str(acc.get("id", doc.get("serving_id", ""))),
            "name": name,
            "email": clean_value(acc.get("email"), ""),
            "phone": clean_value(acc.get("phone"), ""),
            "website": clean_value(acc.get("website"), ""),
            "city": clean_value(acc.get("address_city") or acc.get("city"), ""),
            "country": clean_value(acc.get("address_country") or acc.get("country"), ""),
            "industry": clean_value(acc.get("industry") or acc.get("industry_id"), "") or infer_industry(name),
            # Aggregated metrics
            "pipeline_value": metrics["pipeline_value"],
            "won_value": metrics["won_value"],
            "active_opportunities": metrics["active_count"],
            "total_opportunities": metrics["total_count"],
            # Source info
            "source": "odoo",
            "last_synced": doc.get("last_aggregated"),
        })
    
    # Also get unique account names from opportunities that don't have account records
    existing_names = {a["name"].strip().lower() for a in accounts}
    
    for partner_name, metrics in account_metrics.items():
        if partner_name not in existing_names and partner_name:
            # Create a synthetic account from opportunity data
            display_name = partner_name.title()
            accounts.append({
                "id": f"opp_{partner_name[:20].replace(' ', '_')}",
                "name": display_name,
                "email": "",
                "phone": "",
                "website": "",
                "city": "",
                "country": "",
                "industry": infer_industry(display_name),
                # Aggregated metrics
                "pipeline_value": metrics["pipeline_value"],
                "won_value": metrics["won_value"],
                "active_opportunities": metrics["active_count"],
                "total_opportunities": metrics["total_count"],
                # Source info
                "source": "odoo_opportunity",
                "last_synced": None,
            })
    
    return {
        "source": "data_lake_serving",
        "data_note": "Accounts with aggregated pipeline and revenue metrics.",
        "accounts": accounts,
        "count": len(accounts),
    }


# ===================== 360° ACCOUNT VIEW =====================

@router.get("/accounts/{account_id}/360")
async def get_account_360_view(
    account_id: str,
    token_data: dict = Depends(require_approved())
):
    """
    Get 360° view of an account with all related entities.
    Aggregates opportunities, invoices, activities, and contacts from data_lake_serving.
    """
    db = Database.get_db()
    
    # Find the account - try both data lake and legacy accounts
    account = None
    
    # Handle synthetic IDs (from opportunity-derived accounts like "opp_techcorp_industri")
    account_name = None
    if account_id.startswith("opp_"):
        # Extract name from synthetic ID: opp_techcorp_industri -> techcorp industri
        name_part = account_id[4:].replace("_", " ")
        account_name = name_part.title()
    
    # First check data_lake_serving by ID
    acc_doc = await db.data_lake_serving.find_one({
        "entity_type": "account",
        "$or": [
            {"data.id": account_id},
            {"data.id": int(account_id) if account_id.isdigit() else account_id},
            {"serving_id": account_id}
        ]
    })
    
    # If not found and we have a name, try searching by name
    if not acc_doc and account_name:
        acc_doc = await db.data_lake_serving.find_one({
            "entity_type": "account",
            "data.name": {"$regex": account_name, "$options": "i"}
        })
    
    if acc_doc:
        acc_data = acc_doc.get("data", {})
        account = {
            "id": str(acc_data.get("id", account_id)),
            "name": acc_data.get("name", ""),
            "email": acc_data.get("email", ""),
            "phone": acc_data.get("phone", ""),
            "mobile": acc_data.get("mobile", ""),
            "website": acc_data.get("website", ""),
            "street": acc_data.get("street", ""),
            "city": acc_data.get("city", ""),
            "state": acc_data.get("state", ""),
            "country": acc_data.get("country", ""),
            "zip": acc_data.get("zip", ""),
            "industry": acc_data.get("industry", ""),
            "company_type": acc_data.get("company_type", ""),
            "is_company": acc_data.get("is_company", False),
            "parent_id": acc_data.get("parent_id"),
            "parent_name": acc_data.get("parent_name", ""),
            "credit_limit": float(acc_data.get("credit_limit", 0) or 0),
            "total_invoiced": float(acc_data.get("total_invoiced", 0) or 0),
            "total_due": float(acc_data.get("total_due", 0) or 0),
            "source": "odoo",
            "last_synced": acc_doc.get("last_aggregated"),
        }
    else:
        # Fallback to legacy accounts collection
        legacy_acc = await db.accounts.find_one({"id": account_id}, {"_id": 0})
        if legacy_acc:
            account = {**legacy_acc, "source": "crm"}
    
    # If still not found, try to create account from opportunity partner data
    if not account and account_name:
        # Find opportunities with this partner name to derive account info
        opp_doc = await db.data_lake_serving.find_one({
            "entity_type": "opportunity",
            "data.partner_name": {"$regex": account_name, "$options": "i"}
        })
        
        if opp_doc:
            opp_data = opp_doc.get("data", {})
            account = {
                "id": account_id,
                "name": opp_data.get("partner_name", account_name),
                "email": "",
                "phone": "",
                "mobile": "",
                "website": "",
                "street": "",
                "city": "",
                "state": "",
                "country": "",
                "zip": "",
                "industry": "",
                "company_type": "",
                "is_company": True,
                "source": "opportunity_derived",
                "last_synced": opp_doc.get("last_aggregated"),
            }
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Get related opportunities from data_lake_serving (only active records)
    opportunities = []
    
    # Build search patterns - use name if available, fallback to ID
    account_search_name = account.get("name", "")
    opp_query = {
        "entity_type": "opportunity",
        "$and": [
            # Only show active (non-deleted) records
            {"$or": [{"is_active": True}, {"is_active": {"$exists": False}}]},
            # Match by partner ID or name
            {"$or": [
                {"data.partner_id": account_id},
            ]}
        ]
    }
    
    # Add numeric ID search if applicable
    if account_id.isdigit():
        opp_query["$and"][1]["$or"].append({"data.partner_id": int(account_id)})
    
    # Add name-based search
    if account_search_name:
        opp_query["$and"][1]["$or"].append({"data.partner_name": {"$regex": account_search_name, "$options": "i"}})
    
    # Also search by account_name if we derived it from the synthetic ID
    if account_name and account_name != account_search_name:
        opp_query["$and"][1]["$or"].append({"data.partner_name": {"$regex": account_name, "$options": "i"}})
    
    opp_docs = await db.data_lake_serving.find(opp_query).to_list(100)
    
    for doc in opp_docs:
        opp = doc.get("data", {})
        opportunities.append({
            "id": str(opp.get("id", "")),
            "name": opp.get("name", ""),
            "value": float(opp.get("expected_revenue", 0) or 0),
            "probability": float(opp.get("probability", 0) or 0),
            "stage": opp.get("stage_name", "New"),
            "salesperson": opp.get("salesperson_name", ""),
            "expected_close_date": opp.get("date_deadline"),
            "created_date": opp.get("create_date"),
        })
    
    # Also check legacy opportunities
    legacy_opps = await db.opportunities.find(
        {"account_id": account_id}, 
        {"_id": 0}
    ).to_list(100)
    for opp in legacy_opps:
        if not any(o["id"] == opp.get("id") for o in opportunities):
            opportunities.append({
                "id": opp.get("id", ""),
                "name": opp.get("name", ""),
                "value": float(opp.get("value", 0) or 0),
                "probability": float(opp.get("probability", 0) or 0),
                "stage": opp.get("stage", "lead"),
                "salesperson": opp.get("owner_name", ""),
                "expected_close_date": opp.get("expected_close_date"),
                "created_date": opp.get("created_at"),
            })
    
    # Get related invoices from data_lake_serving
    invoices = []
    inv_docs = await db.data_lake_serving.find({
        "entity_type": "invoice",
        "$or": [
            {"data.partner_id": account_id},
            {"data.partner_id": int(account_id) if account_id.isdigit() else None},
            {"data.partner_name": {"$regex": account.get("name", "NOMATCH"), "$options": "i"}},
            {"data.customer_name": {"$regex": account.get("name", "NOMATCH"), "$options": "i"}}
        ]
    }).to_list(100)
    
    for doc in inv_docs:
        inv = doc.get("data", {})
        invoices.append({
            "id": str(inv.get("id", "")),
            "number": inv.get("name", inv.get("invoice_number", "")),
            "amount_total": float(inv.get("amount_total", 0) or 0),
            "amount_due": float(inv.get("amount_residual", inv.get("amount_due", 0)) or 0),
            "payment_status": inv.get("payment_state", inv.get("payment_status", "pending")),
            "invoice_date": inv.get("invoice_date"),
            "due_date": inv.get("invoice_date_due", inv.get("due_date")),
        })
    
    # Get related activities from BOTH local DB and Odoo (data_lake_serving)
    activities = []
    
    # 1. Get local activities
    activity_docs = await db.activities.find({"account_id": account_id}, {"_id": 0}).to_list(50)
    for act in activity_docs:
        activities.append({
            "id": act.get("id", ""),
            "title": act.get("title", ""),
            "activity_type": act.get("activity_type", "task"),
            "status": act.get("status", "pending"),
            "due_date": act.get("due_date"),
            "priority": act.get("priority", "medium"),
            "source": "crm"
        })
    
    # 2. Get Odoo activities from data_lake_serving
    odoo_activity_docs = await db.data_lake_serving.find(
        active_entity_filter("activity", {
            "$or": [
                {"data.res_id": int(account_id) if account_id.isdigit() else None},
                {"data.res_model": "res.partner"}
            ]
        })
    ).to_list(100)
    
    for doc in odoo_activity_docs:
        act = doc.get("data", {})
        activities.append({
            "id": str(act.get("id", "")),
            "title": act.get("summary") or act.get("note", "Activity"),
            "activity_type": act.get("activity_type_id", ["", ""])[1] if isinstance(act.get("activity_type_id"), list) else "task",
            "status": "done" if act.get("state") == "done" else "pending",
            "due_date": act.get("date_deadline"),
            "priority": "high" if act.get("state") == "overdue" else "medium",
            "source": "odoo",
            "user_name": act.get("user_id", ["", ""])[1] if isinstance(act.get("user_id"), list) else ""
        })
    
    # Calculate activity summary metrics
    now = datetime.now(timezone.utc)
    activity_summary = {
        "total": len(activities),
        "pending": len([a for a in activities if a["status"] == "pending"]),
        "completed": len([a for a in activities if a["status"] == "done"]),
        "overdue": 0,
        "due_soon": 0
    }
    
    # Count overdue and due soon
    for act in activities:
        if act["status"] != "done" and act.get("due_date"):
            try:
                due_date = datetime.fromisoformat(str(act["due_date"]).replace('Z', '+00:00'))
                if due_date < now:
                    activity_summary["overdue"] += 1
                elif (due_date - now).days <= 7:
                    activity_summary["due_soon"] += 1
            except:
                pass
    
    # Get related contacts from data_lake_serving
    # Contacts have entity_type: "contact" with account_id field
    contacts = []
    
    # Helper to clean Odoo False values
    def clean_val(val, default=""):
        if val is False or val is None:
            return default
        return val
    
    # Query contacts - handle different account_id formats:
    # - account_id: false (unlinked)
    # - account_id: [12, "VM"] (array with ID and name)
    # - account_id: 12 (just ID)
    contact_docs = await db.data_lake_serving.find({
        "entity_type": "contact"
    }).to_list(100)
    
    for doc in contact_docs:
        contact = doc.get("data", {})
        contact_account_id = contact.get("account_id")
        
        # Check if contact belongs to this account
        contact_matches = False
        
        if contact_account_id:
            # Handle array format [id, name]
            if isinstance(contact_account_id, list) and len(contact_account_id) >= 1:
                contact_acc_id = str(contact_account_id[0])
                contact_acc_name = contact_account_id[1] if len(contact_account_id) > 1 else ""
                
                # Match by ID or by name
                if contact_acc_id == account_id:
                    contact_matches = True
                elif account.get("name") and contact_acc_name and account.get("name", "").lower() in contact_acc_name.lower():
                    contact_matches = True
            
            # Handle simple ID format
            elif isinstance(contact_account_id, (int, str)):
                if str(contact_account_id) == account_id:
                    contact_matches = True
        
        if contact_matches:
            contacts.append({
                "id": str(contact.get("id", doc.get("serving_id", ""))),
                "name": clean_val(contact.get("name"), "Unknown"),
                "email": clean_val(contact.get("email"), ""),
                "phone": clean_val(contact.get("phone") or contact.get("mobile"), ""),
                "job_title": clean_val(contact.get("title") or contact.get("function"), ""),
            })
    
    # Also check for contacts that match by account name (for opportunities-derived accounts)
    if len(contacts) == 0 and account.get("name"):
        account_name_lower = account.get("name", "").lower()
        for doc in contact_docs:
            contact = doc.get("data", {})
            contact_account_id = contact.get("account_id")
            
            if isinstance(contact_account_id, list) and len(contact_account_id) > 1:
                contact_acc_name = str(contact_account_id[1]).lower()
                if account_name_lower in contact_acc_name or contact_acc_name in account_name_lower:
                    contacts.append({
                        "id": str(contact.get("id", doc.get("serving_id", ""))),
                        "name": clean_val(contact.get("name"), "Unknown"),
                        "email": clean_val(contact.get("email"), ""),
                        "phone": clean_val(contact.get("phone") or contact.get("mobile"), ""),
                        "job_title": clean_val(contact.get("title") or contact.get("function"), ""),
                    })
    
    # Calculate summary metrics
    total_pipeline = sum(o["value"] for o in opportunities if o["stage"] not in ["Won", "Lost", "Closed Won", "Closed Lost"])
    total_won = sum(o["value"] for o in opportunities if o["stage"] in ["Won", "Closed Won"])
    total_invoiced = sum(i["amount_total"] for i in invoices)
    total_outstanding = sum(i["amount_due"] for i in invoices)
    
    return {
        "account": account,
        "summary": {
            "total_opportunities": len(opportunities),
            "total_pipeline_value": total_pipeline,
            "total_won_value": total_won,
            "total_invoiced": total_invoiced,
            "total_outstanding": total_outstanding,
            "total_activities": len(activities),
            "pending_activities": len([a for a in activities if a["status"] == "pending"]),
            "total_contacts": len(contacts),
            # ENHANCED: Activity summary with risk indicators
            "activity_summary": activity_summary,
        },
        "opportunities": sorted(opportunities, key=lambda x: x.get("value", 0), reverse=True),
        "invoices": sorted(invoices, key=lambda x: x.get("invoice_date") or "", reverse=True),
        "activities": sorted(activities, key=lambda x: x.get("due_date") or ""),
        "contacts": contacts,
    }


# ===================== SYNC HEALTH STATUS =====================

@router.get("/sync-status")
async def get_sync_status(
    token_data: dict = Depends(require_approved())
):
    """
    Get health status of all integrations.
    Returns last sync times and status for dashboard widget.
    """
    db = Database.get_db()
    
    # Check Odoo integration status from integrations collection
    odoo_integration = await db.integrations.find_one({"integration_type": "odoo"})
    odoo_status = {
        "name": "Odoo ERP",
        "status": "not_configured",
        "last_sync": None,
        "records_synced": 0,
        "note": None,
    }
    
    if odoo_integration:
        # Check if enabled and configured
        if odoo_integration.get("enabled") and odoo_integration.get("config", {}).get("url"):
            # Check actual sync status
            sync_status = odoo_integration.get("sync_status", "unknown")
            error_message = odoo_integration.get("error_message")
            
            if sync_status == "success":
                odoo_status["status"] = "connected"
            elif sync_status == "failed":
                odoo_status["status"] = "error"
                odoo_status["note"] = error_message or "Sync failed"
            elif sync_status == "partial":
                odoo_status["status"] = "warning"
                odoo_status["note"] = "Some entities failed to sync"
            elif sync_status == "in_progress":
                odoo_status["status"] = "syncing"
                odoo_status["note"] = "Sync in progress..."
            else:
                # Fallback: check if we have any synced data
                latest_odoo = await db.data_lake_serving.find_one(
                    {"source": "odoo"},
                    sort=[("last_aggregated", -1)],
                    projection={"last_aggregated": 1, "_id": 0}
                )
                if latest_odoo:
                    odoo_status["status"] = "connected"
                else:
                    odoo_status["status"] = "no_data"
                    odoo_status["note"] = "No data synced yet"
            
            odoo_status["last_sync"] = odoo_integration.get("last_sync")
            odoo_status["records_synced"] = await db.data_lake_serving.count_documents({"source": "odoo"})
        else:
            odoo_status["status"] = "not_configured"
            odoo_status["note"] = "Odoo integration not configured"
    
    # Check MS365 status
    ms365_integration = await db.integrations.find_one({"integration_type": "ms365"})
    ms365_status = {
        "name": "Microsoft 365",
        "status": "not_connected",
        "last_sync": None,
        "note": None,
    }
    
    # Check if user has MS365 tokens (user-specific)
    user = await db.users.find_one({"id": token_data["id"]})
    if user:
        ms_access_token = user.get("ms_access_token")
        ms365_tokens = user.get("ms365_tokens")
        
        if ms_access_token or ms365_tokens:
            ms365_status["status"] = "connected"
            
            # Check if token needs refresh
            if ms365_tokens and ms365_tokens.get("expires_at"):
                try:
                    expires = datetime.fromisoformat(ms365_tokens["expires_at"].replace("Z", "+00:00"))
                    if expires < datetime.now(timezone.utc):
                        ms365_status["status"] = "needs_refresh"
                        ms365_status["note"] = "Session expired - please re-login"
                except:
                    pass
        else:
            ms365_status["note"] = "Sign in with Microsoft to connect"
    
    # Determine overall health
    statuses = [odoo_status["status"], ms365_status["status"]]
    if "error" in statuses:
        overall_health = "error"
    elif "needs_refresh" in statuses or "warning" in statuses or "no_data" in statuses:
        overall_health = "warning"
    elif all(s == "connected" for s in statuses):
        overall_health = "healthy"
    else:
        overall_health = "partial"
    
    return {
        "integrations": [odoo_status, ms365_status],
        "overall_health": overall_health,
    }
