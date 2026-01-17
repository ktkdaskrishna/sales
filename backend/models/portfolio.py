"""
Portfolio Models
Define portfolio structures for Product Directors
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class PortfolioCreate(BaseModel):
    """Request model for creating a portfolio"""
    name: str = Field(..., min_length=1, max_length=100)
    team_id: str
    product_lines: List[str] = Field(default_factory=list, max_items=10)
    strategic_priority: str = Field(default="medium", pattern="^(high|medium|low)$")
    description: Optional[str] = None
    fiscal_year: Optional[str] = None


class PortfolioUpdate(BaseModel):
    """Request model for updating a portfolio"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    strategic_priority: Optional[str] = Field(None, pattern="^(high|medium|low)$")
    product_lines: Optional[List[str]] = None


class PortfolioResponse(BaseModel):
    """Response model for portfolio data"""
    id: str
    name: str
    team_id: str
    owner_id: str
    product_lines: List[str]
    strategic_priority: str
    description: Optional[str] = None
    fiscal_year: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool = True


class PortfolioDashboardResponse(BaseModel):
    """Complete portfolio dashboard"""
    portfolio: dict
    initiatives: List[dict] = []
    kpis: List[dict] = []
    metrics: dict
    recent_activities: List[dict] = []
    top_opportunities: List[dict] = []
