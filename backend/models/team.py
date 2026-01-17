"""
Team Models
Define team structures and validation
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class TeamType:
    """Team type constants"""
    PRODUCT = "product"
    SALES = "sales"
    STRATEGIC = "strategic"
    OPS = "ops"


class TeamMember(BaseModel):
    """Team member model"""
    user_id: str
    name: str
    email: str
    role: str = "member"  # member | admin | owner
    joined_at: datetime


class TeamCreate(BaseModel):
    """Request model for creating a team"""
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., pattern="^(product|sales|strategic|ops)$")
    description: Optional[str] = None
    initial_members: List[str] = Field(default_factory=list)  # User IDs


class TeamUpdate(BaseModel):
    """Request model for updating a team"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    type: Optional[str] = Field(None, pattern="^(product|sales|strategic|ops)$")


class TeamAddMembers(BaseModel):
    """Request model for adding team members"""
    user_ids: List[str] = Field(..., min_items=1, max_items=50)
    role: str = Field(default="member", pattern="^(member|admin)$")


class TeamResponse(BaseModel):
    """Response model for team data"""
    id: str
    name: str
    type: str
    owner_id: str
    description: Optional[str] = None
    member_count: int
    created_at: datetime
    updated_at: datetime
    is_active: bool = True


class TeamDetailResponse(TeamResponse):
    """Detailed team response with members"""
    owner: dict  # {id, name, email}
    members: List[TeamMember]
    portfolios_count: int = 0
    initiatives_count: int = 0
