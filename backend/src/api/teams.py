"""
Team Management API Endpoints

Endpoints for:
- Team creation and management
- Team member invitation and management
- Team settings
- Team deletion
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from db.models import User
from security.auth import create_access_token
from models.platform_models import (
    Team,
    TeamMember,
    TeamInvitation,
    SharedProject,
    ProjectActivity,
    TeamRole,
    PlatformType,
    Permission,
    has_permission,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/teams", tags=["Teams"])
security = HTTPBearer()

# ============================================
# Request/Response Models
# ============================================


class CreateTeamRequest(BaseModel):
    """Request to create a new team"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)


class UpdateTeamRequest(BaseModel):
    """Request to update team settings"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    settings: Optional[dict] = None


class TeamResponse(BaseModel):
    """Team information response"""
    id: str
    name: str
    slug: str
    description: Optional[str]
    owner_id: str
    settings: dict
    member_count: int
    created_at: str
    updated_at: str


class InviteMemberRequest(BaseModel):
    """Request to invite a team member"""
    email: EmailStr
    role: TeamRole = TeamRole.VIEWER


class InviteResponse(BaseModel):
    """Invitation response"""
    invitation_id: str
    email: str
    role: str
    expires_at: str


class UpdateMemberRequest(BaseModel):
    """Request to update member role"""
    role: TeamRole


class MemberResponse(BaseModel):
    """Team member response"""
    id: str
    user_id: str
    role: str
    status: str
    joined_at: str


class SharedProjectRequest(BaseModel):
    """Request to create a shared project"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    settings: Optional[dict] = None


class SharedProjectResponse(BaseModel):
    """Shared project response"""
    id: str
    team_id: str
    owner_id: str
    name: str
    description: Optional[str]
    settings: dict
    created_at: str
    updated_at: str


class ActivityResponse(BaseModel):
    """Activity feed response"""
    id: str
    user_id: str
    action: str
    details: dict
    created_at: str


# ============================================
# Helper Functions
# ============================================


async def get_current_user(
    credentials: HTTPBearer = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current authenticated user"""
    from security.auth import verify_token
    
    token = credentials.credentials
    user_id = verify_token(token, "access")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def get_team_with_permission(
    team_id: str,
    db: AsyncSession,
    user_id: str,
    required_permission: str,
) -> Team:
    """Get team and verify user has required permission"""
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )
    
    # Check user's role in team
    member_result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
            TeamMember.status == "active",
        )
    )
    member = member_result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this team",
        )
    
    if not has_permission(member.role, required_permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You don't have permission to perform this action",
        )
    
    return team


def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from team name"""
    import re
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s-]+', '-', slug)
    slug = slug.strip('-')
    return slug


# ============================================
# Team Endpoints
# ============================================


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    request: CreateTeamRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new team.
    
    The current user becomes the team admin.
    """
    # Generate unique slug
    base_slug = generate_slug(request.name)
    slug = base_slug
    
    # Check for existing slug
    result = await db.execute(select(Team).where(Team.slug == slug))
    counter = 1
    while result.scalar_one_or_none():
        slug = f"{base_slug}-{counter}"
        result = await db.execute(select(Team).where(Team.slug == slug))
        counter += 1
    
    team = Team(
        name=request.name,
        slug=slug,
        description=request.description,
        owner_id=str(current_user.id),
        settings={},
    )
    
    db.add(team)
    await db.flush()
    
    # Add owner as admin member
    member = TeamMember(
        team_id=team.id,
        user_id=str(current_user.id),
        role=TeamRole.ADMIN,
        status="active",
    )
    db.add(member)
    
    await db.commit()
    await db.refresh(team)
    
    return TeamResponse(
        id=str(team.id),
        name=team.name,
        slug=team.slug,
        description=team.description,
        owner_id=team.owner_id,
        settings=team.settings or {},
        member_count=1,
        created_at=team.created_at.isoformat(),
        updated_at=team.updated_at.isoformat(),
    )


@router.get("", response_model=List[TeamResponse])
async def list_teams(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all teams the current user is a member of.
    """
    result = await db.execute(
        select(Team)
        .join(TeamMember, Team.id == TeamMember.team_id)
        .where(TeamMember.user_id == str(current_user.id))
        .where(TeamMember.status == "active")
    )
    teams = result.scalars().all()
    
    response = []
    for team in teams:
        # Get member count
        member_result = await db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team.id,
                TeamMember.status == "active",
            )
        )
        member_count = len(member_result.scalars().all())
        
        response.append(TeamResponse(
            id=str(team.id),
            name=team.name,
            slug=team.slug,
            description=team.description,
            owner_id=team.owner_id,
            settings=team.settings or {},
            member_count=member_count,
            created_at=team.created_at.isoformat(),
            updated_at=team.updated_at.isoformat(),
        ))
    
    return response


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific team"""
    team = await get_team_with_permission(
        team_id, db, str(current_user.id), Permission.VIEWER_PROJECT_VIEW
    )
    
    # Get member count
    member_result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team.id,
            TeamMember.status == "active",
        )
    )
    member_count = len(member_result.scalars().all())
    
    return TeamResponse(
        id=str(team.id),
        name=team.name,
        slug=team.slug,
        description=team.description,
        owner_id=team.owner_id,
        settings=team.settings or {},
        member_count=member_count,
        created_at=team.created_at.isoformat(),
        updated_at=team.updated_at.isoformat(),
    )


@router.patch("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: str,
    request: UpdateTeamRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update team settings (admin only)"""
    team = await get_team_with_permission(
        team_id, db, str(current_user.id), Permission.ADMIN_TEAM_MANAGE
    )
    
    if request.name is not None:
        team.name = request.name
    if request.description is not None:
        team.description = request.description
    if request.settings is not None:
        team.settings = request.settings
    
    await db.commit()
    await db.refresh(team)
    
    # Get member count
    member_result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team.id,
            TeamMember.status == "active",
        )
    )
    member_count = len(member_result.scalars().all())
    
    return TeamResponse(
        id=str(team.id),
        name=team.name,
        slug=team.slug,
        description=team.description,
        owner_id=team.owner_id,
        settings=team.settings or {},
        member_count=member_count,
        created_at=team.created_at.isoformat(),
        updated_at=team.updated_at.isoformat(),
    )


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a team (owner only)"""
    team = await get_team_with_permission(
        team_id, db, str(current_user.id), Permission.ADMIN_ALL
    )
    
    # Only owner can delete
    if team.owner_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the team owner can delete the team",
        )
    
    await db.delete(team)
    await db.commit()


# ============================================
# Team Member Endpoints
# ============================================


@router.post("/{team_id}/members/invite", response_model=InviteResponse)
async def invite_member(
    team_id: str,
    request: InviteMemberRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Invite a new member to the team"""
    team = await get_team_with_permission(
        team_id, db, str(current_user.id), Permission.ADMIN_TEAM_MANAGE
    )
    
    # Generate invitation token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    invitation = TeamInvitation(
        team_id=team.id,
        email=request.email,
        role=request.role,
        invited_by=str(current_user.id),
        token=token,
        expires_at=expires_at,
    )
    
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)
    
    return InviteResponse(
        id=str(invitation.id),
        email=invitation.email,
        role=invitation.role.value,
        expires_at=invitation.expires_at.isoformat(),
    )


@router.get("/{team_id}/members", response_model=List[MemberResponse])
async def list_team_members(
    team_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all team members"""
    await get_team_with_permission(
        team_id, db, str(current_user.id), Permission.VIEWER_PROJECT_VIEW
    )
    
    result = await db.execute(
        select(TeamMember)
        .where(TeamMember.team_id == team_id)
        .where(TeamMember.status == "active")
    )
    members = result.scalars().all()
    
    return [
        MemberResponse(
            id=str(m.id),
            user_id=m.user_id,
            role=m.role.value,
            status=m.status,
            joined_at=m.joined_at.isoformat(),
        )
        for m in members
    ]


@router.patch("/{team_id}/members/{member_id}")
async def update_member_role(
    team_id: str,
    member_id: str,
    request: UpdateMemberRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a team member's role"""
    await get_team_with_permission(
        team_id, db, str(current_user.id), Permission.ADMIN_TEAM_MANAGE
    )
    
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.id == member_id,
            TeamMember.team_id == team_id,
        )
    )
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )
    
    # Cannot change own role
    if member.user_id == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role",
        )
    
    member.role = request.role
    await db.commit()
    
    return {"message": "Member role updated", "member_id": member_id}


@router.delete("/{team_id}/members/{member_id}")
async def remove_member(
    team_id: str,
    member_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member from the team"""
    await get_team_with_permission(
        team_id, db, str(current_user.id), Permission.ADMIN_TEAM_MANAGE
    )
    
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.id == member_id,
            TeamMember.team_id == team_id,
        )
    )
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )
    
    # Cannot remove yourself
    if member.user_id == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself. Use leave team instead.",
        )
    
    await db.delete(member)
    await db.commit()
    
    return {"message": "Member removed"}


# ============================================
# Shared Project Endpoints
# ============================================


@router.post("/{team_id}/projects", response_model=SharedProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_shared_project(
    team_id: str,
    request: SharedProjectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a shared project in the team"""
    await get_team_with_permission(
        team_id, db, str(current_user.id), Permission.EDITOR_PROJECT_EDIT
    )
    
    project = SharedProject(
        team_id=team_id,
        owner_id=str(current_user.id),
        name=request.name,
        description=request.description,
        settings=request.settings or {},
    )
    
    db.add(project)
    
    # Log activity
    activity = ProjectActivity(
        project_id=project.id,
        user_id=str(current_user.id),
        action="created",
        details={"name": request.name},
    )
    db.add(activity)
    
    await db.commit()
    await db.refresh(project)
    
    return SharedProjectResponse(
        id=str(project.id),
        team_id=str(project.team_id),
        owner_id=project.owner_id,
        name=project.name,
        description=project.description,
        settings=project.settings or {},
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
    )


@router.get("/{team_id}/projects", response_model=List[SharedProjectResponse])
async def list_shared_projects(
    team_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all shared projects in the team"""
    await get_team_with_permission(
        team_id, db, str(current_user.id), Permission.VIEWER_PROJECT_VIEW
    )
    
    result = await db.execute(
        select(SharedProject).where(SharedProject.team_id == team_id)
    )
    projects = result.scalars().all()
    
    return [
        SharedProjectResponse(
            id=str(p.id),
            team_id=str(p.team_id),
            owner_id=p.owner_id,
            name=p.name,
            description=p.description,
            settings=p.settings or {},
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
        )
        for p in projects
    ]


@router.get("/{team_id}/projects/{project_id}/activity", response_model=List[ActivityResponse])
async def get_project_activity(
    team_id: str,
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get activity feed for a shared project"""
    await get_team_with_permission(
        team_id, db, str(current_user.id), Permission.VIEWER_PROJECT_VIEW
    )
    
    result = await db.execute(
        select(ProjectActivity)
        .where(ProjectActivity.project_id == project_id)
        .order_by(ProjectActivity.created_at.desc())
        .limit(50)
    )
    activities = result.scalars().all()
    
    return [
        ActivityResponse(
            id=str(a.id),
            user_id=a.user_id,
            action=a.action,
            details=a.details or {},
            created_at=a.created_at.isoformat(),
        )
        for a in activities
    ]
