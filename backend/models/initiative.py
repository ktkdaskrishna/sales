"""
Initiative Models
Define initiative/campaign structures
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime


class InitiativeCreate(BaseModel):
    """Request model for creating an initiative"""
    name: str = Field(..., min_length=1, max_length=200)
    portfolio_id: str
    type: str = Field(default="campaign", pattern="^(campaign|program|project)$")
    start_date: str
    end_date: str
    description: Optional[str] = None
    activity_template: Optional[Dict[str, int]] = None
    milestones: List[Dict[str, str]] = Field(default_factory=list)


class InitiativeUpdate(BaseModel):
    """Request model for updating an initiative"""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(planning|active|completed|paused|cancelled)$")
    end_date: Optional[str] = None


class InitiativeResponse(BaseModel):
    """Response model for initiative data"""
    id: str
    name: str
    portfolio_id: str
    owner_id: str
    type: str
    start_date: str
    end_date: str
    status: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool = True


class InitiativeProgressResponse(BaseModel):
    """Initiative progress with activity tracking"""
    initiative: dict
    progress: dict
    goals: List[dict]
    kpis: List[dict]
    recent_activities: List[dict]
