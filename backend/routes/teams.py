"""
Team Routes
API endpoints for team management
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import logging

from core.database import Database
from services.auth.jwt_handler import get_current_user_from_token
from models.team import (
    TeamCreate, TeamUpdate, TeamAddMembers, 
    TeamResponse, TeamDetailResponse, TeamMember
)

router = APIRouter(prefix="/teams", tags=["Teams"])
logger = logging.getLogger(__name__)


async def require_approved_user(token_data: dict = Depends(get_current_user_from_token)):
    """Require an approved user"""
    db = Database.get_db()
    user = await db.users.find_one({"id": token_data["id"]})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("approval_status") == "pending":
        raise HTTPException(status_code=403, detail="User pending approval")
    
    return token_data


@router.post("", response_model=TeamResponse)
async def create_team(
    team_data: TeamCreate,
    token_data: dict = Depends(require_approved_user)
):
    """
    Create a new team.
    Current user becomes the team owner.
    """
    db = Database.get_db()
    user_id = token_data["id"]
    
    now = datetime.now(timezone.utc)
    team_id = str(uuid.uuid4())
    
    # Create team document
    team = {
        "id": team_id,
        "name": team_data.name,
        "type": team_data.type,
        "owner_id": user_id,
        "description": team_data.description,
        "member_ids": [user_id],  # Owner is always a member
        "parent_team_id": None,
        "created_at": now,
        "updated_at": now,
        "is_active": True
    }
    
    await db.teams.insert_one(team)
    
    # Add owner as team member
    await db.team_members.insert_one({
        "id": str(uuid.uuid4()),
        "team_id": team_id,
        "user_id": user_id,
        "role": "owner",
        "joined_at": now,
        "is_active": True
    })
    
    # Add initial members if provided
    if team_data.initial_members:
        for member_id in team_data.initial_members:
            if member_id != user_id:  # Skip owner (already added)
                # Verify user exists
                member = await db.users.find_one({"id": member_id})
                if member:
                    await db.team_members.insert_one({
                        "id": str(uuid.uuid4()),
                        "team_id": team_id,
                        "user_id": member_id,
                        "role": "member",
                        "joined_at": now,
                        "is_active": True
                    })
                    
                    # Add to member_ids array
                    await db.teams.update_one(
                        {"id": team_id},
                        {"$addToSet": {"member_ids": member_id}}
                    )
    
    logger.info(f"Team created: {team_data.name} by user {user_id}")
    
    return TeamResponse(
        id=team_id,
        name=team_data.name,
        type=team_data.type,
        owner_id=user_id,
        description=team_data.description,
        member_count=len(team_data.initial_members) + 1,
        created_at=now,
        updated_at=now,
        is_active=True
    )


@router.get("", response_model=List[TeamResponse])
async def get_teams(
    type: Optional[str] = None,
    owner_id: Optional[str] = None,
    member_id: Optional[str] = None,
    token_data: dict = Depends(require_approved_user)
):
    """
    Get all teams with optional filters.
    Returns teams visible to current user.
    """
    db = Database.get_db()
    
    # Build query
    query = {"is_active": True}
    
    if type:
        query["type"] = type
    if owner_id:
        query["owner_id"] = owner_id
    if member_id:
        query["member_ids"] = member_id
    
    teams = await db.teams.find(query, {"_id": 0}).to_list(100)
    
    # Build response
    result = []
    for team in teams:
        result.append(TeamResponse(
            id=team["id"],
            name=team["name"],
            type=team["type"],
            owner_id=team["owner_id"],
            description=team.get("description"),
            member_count=len(team.get("member_ids", [])),
            created_at=team["created_at"],
            updated_at=team["updated_at"],
            is_active=team.get("is_active", True)
        ))
    
    return result


@router.get("/{team_id}", response_model=TeamDetailResponse)
async def get_team(
    team_id: str,
    token_data: dict = Depends(require_approved_user)
):
    """
    Get detailed team information including members.
    """
    db = Database.get_db()
    
    # Get team
    team = await db.teams.find_one({"id": team_id}, {"_id": 0})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Get owner details
    owner = await db.users.find_one({"id": team["owner_id"]}, {"_id": 0, "id": 1, "name": 1, "email": 1})
    owner_data = {
        "id": owner["id"],
        "name": owner.get("name", ""),
        "email": owner.get("email", "")
    } if owner else {"id": team["owner_id"], "name": "Unknown", "email": ""}
    
    # Get team members
    member_docs = await db.team_members.find(
        {"team_id": team_id, "is_active": True},
        {"_id": 0}
    ).to_list(100)
    
    members = []
    for mem_doc in member_docs:
        user = await db.users.find_one({"id": mem_doc["user_id"]}, {"_id": 0, "id": 1, "name": 1, "email": 1})
        if user:
            members.append(TeamMember(
                user_id=user["id"],
                name=user.get("name", ""),
                email=user.get("email", ""),
                role=mem_doc.get("role", "member"),
                joined_at=mem_doc.get("joined_at", datetime.now(timezone.utc))
            ))
    
    # Get portfolio count
    portfolios_count = await db.portfolios.count_documents({"team_id": team_id}) if hasattr(db, 'portfolios') else 0
    
    # Get initiative count  
    initiatives_count = await db.initiatives.count_documents({"team_id": team_id}) if hasattr(db, 'initiatives') else 0
    
    return TeamDetailResponse(
        id=team["id"],
        name=team["name"],
        type=team["type"],
        owner_id=team["owner_id"],
        owner=owner_data,
        description=team.get("description"),
        member_count=len(members),
        members=members,
        portfolios_count=portfolios_count,
        initiatives_count=initiatives_count,
        created_at=team["created_at"],
        updated_at=team["updated_at"],
        is_active=team.get("is_active", True)
    )


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: str,
    team_data: TeamUpdate,
    token_data: dict = Depends(require_approved_user)
):
    """
    Update team information.
    Only team owner can update.
    """
    db = Database.get_db()
    user_id = token_data["id"]
    
    # Get team
    team = await db.teams.find_one({"id": team_id})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Check permission
    if team["owner_id"] != user_id and not token_data.get("is_super_admin"):
        raise HTTPException(status_code=403, detail="Only team owner can update team")
    
    # Build update
    update_data = {}
    if team_data.name:
        update_data["name"] = team_data.name
    if team_data.description is not None:
        update_data["description"] = team_data.description
    if team_data.type:
        update_data["type"] = team_data.type
    
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    # Update team
    await db.teams.update_one({"id": team_id}, {"$set": update_data})
    
    # Get updated team
    updated_team = await db.teams.find_one({"id": team_id}, {"_id": 0})
    
    return TeamResponse(
        id=updated_team["id"],
        name=updated_team["name"],
        type=updated_team["type"],
        owner_id=updated_team["owner_id"],
        description=updated_team.get("description"),
        member_count=len(updated_team.get("member_ids", [])),
        created_at=updated_team["created_at"],
        updated_at=updated_team["updated_at"],
        is_active=updated_team.get("is_active", True)
    )


@router.post("/{team_id}/members")
async def add_team_members(
    team_id: str,
    members_data: TeamAddMembers,
    token_data: dict = Depends(require_approved_user)
):
    """
    Add members to a team.
    Only team owner or admin can add members.
    """
    db = Database.get_db()
    user_id = token_data["id"]
    
    # Get team
    team = await db.teams.find_one({"id": team_id})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Check permission
    is_owner = team["owner_id"] == user_id
    is_admin = await db.team_members.find_one({
        "team_id": team_id,
        "user_id": user_id,
        "role": "admin",
        "is_active": True
    })
    
    if not is_owner and not is_admin and not token_data.get("is_super_admin"):
        raise HTTPException(status_code=403, detail="Only team owner or admin can add members")
    
    # Add members
    added_count = 0
    now = datetime.now(timezone.utc)
    
    for member_id in members_data.user_ids:
        # Verify user exists
        user = await db.users.find_one({"id": member_id})
        if not user:
            logger.warning(f"User {member_id} not found, skipping")
            continue
        
        # Check if already a member
        existing = await db.team_members.find_one({
            "team_id": team_id,
            "user_id": member_id,
            "is_active": True
        })
        
        if existing:
            continue  # Already a member
        
        # Add to team_members
        await db.team_members.insert_one({
            "id": str(uuid.uuid4()),
            "team_id": team_id,
            "user_id": member_id,
            "role": members_data.role,
            "joined_at": now,
            "is_active": True
        })
        
        # Add to team.member_ids array
        await db.teams.update_one(
            {"id": team_id},
            {"$addToSet": {"member_ids": member_id}}
        )
        
        added_count += 1
    
    # Get updated member count
    updated_team = await db.teams.find_one({"id": team_id}, {"_id": 0, "member_ids": 1})
    
    logger.info(f"Added {added_count} members to team {team_id}")
    
    return {
        "team_id": team_id,
        "added": added_count,
        "total_members": len(updated_team.get("member_ids", []))
    }


@router.delete("/{team_id}/members/{user_id}")
async def remove_team_member(
    team_id: str,
    user_id: str,
    token_data: dict = Depends(require_approved_user)
):
    """
    Remove a member from a team.
    Only team owner or admin can remove members.
    Cannot remove team owner.
    """
    db = Database.get_db()
    current_user_id = token_data["id"]
    
    # Get team
    team = await db.teams.find_one({"id": team_id})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Cannot remove owner
    if user_id == team["owner_id"]:
        raise HTTPException(status_code=400, detail="Cannot remove team owner")
    
    # Check permission
    is_owner = team["owner_id"] == current_user_id
    is_admin = await db.team_members.find_one({
        "team_id": team_id,
        "user_id": current_user_id,
        "role": "admin",
        "is_active": True
    })
    
    if not is_owner and not is_admin and not token_data.get("is_super_admin"):
        raise HTTPException(status_code=403, detail="Only team owner or admin can remove members")
    
    # Mark team member as inactive
    await db.team_members.update_one(
        {"team_id": team_id, "user_id": user_id},
        {"$set": {"is_active": False, "removed_at": datetime.now(timezone.utc)}}
    )
    
    # Remove from team.member_ids array
    await db.teams.update_one(
        {"id": team_id},
        {"$pull": {"member_ids": user_id}}
    )
    
    # Get updated member count
    updated_team = await db.teams.find_one({"id": team_id}, {"_id": 0, "member_ids": 1})
    
    logger.info(f"Removed user {user_id} from team {team_id}")
    
    return {
        "removed": True,
        "team_id": team_id,
        "remaining_members": len(updated_team.get("member_ids", []))
    }


@router.get("/my-teams", response_model=List[TeamResponse])
async def get_my_teams(
    token_data: dict = Depends(require_approved_user)
):
    """
    Get all teams the current user is a member of.
    """
    db = Database.get_db()
    user_id = token_data["id"]
    
    # Find teams where user is a member
    teams = await db.teams.find(
        {"member_ids": user_id, "is_active": True},
        {"_id": 0}
    ).to_list(100)
    
    result = []
    for team in teams:
        result.append(TeamResponse(
            id=team["id"],
            name=team["name"],
            type=team["type"],
            owner_id=team["owner_id"],
            description=team.get("description"),
            member_count=len(team.get("member_ids", [])),
            created_at=team["created_at"],
            updated_at=team["updated_at"],
            is_active=team.get("is_active", True)
        ))
    
    return result
