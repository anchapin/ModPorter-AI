"""
Platform Integration and Team Models

Database models for:
- Platform OAuth connections (Modrinth, CurseForge)
- Teams and team membership
- Role-based permissions
- Shared projects
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List
from enum import Enum
from sqlalchemy import (
    Boolean,
    String,
    Integer,
    ForeignKey,
    DateTime,
    func,
    text,
    Column,
    Text,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from db.declarative_base import Base


class PlatformType(str, Enum):
    """Supported platforms for mod publishing"""
    MODRINTH = "modrinth"
    CURSEFORGE = "curseforge"


class TeamRole(str, Enum):
    """Team member roles"""
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class PlatformConnection(Base):
    """Stores OAuth connections for platforms (Modrinth, CurseForge)"""
    __tablename__ = "platform_connections"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    platform: Mapped[PlatformType] = mapped_column(
        SQLEnum(PlatformType),
        nullable=False,
    )
    platform_user_id: Mapped[str] = mapped_column(String, nullable=False)
    platform_username: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Team(Base):
    """Team model for collaborative work"""
    __tablename__ = "teams"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[str] = mapped_column(String, nullable=False)
    settings: Mapped[dict] = mapped_column(JSONB, nullable=True, default={})
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    projects = relationship("SharedProject", back_populates="team", cascade="all, delete-orphan")


class TeamMember(Base):
    """Team member association with roles"""
    __tablename__ = "team_members"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    team_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[TeamRole] = mapped_column(
        SQLEnum(TeamRole),
        nullable=False,
        default=TeamRole.VIEWER,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    invited_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    team = relationship("Team", back_populates="members")


class TeamInvitation(Base):
    """Pending team invitations"""
    __tablename__ = "team_invitations"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    team_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[TeamRole] = mapped_column(
        SQLEnum(TeamRole),
        nullable=False,
        default=TeamRole.VIEWER,
    )
    invited_by: Mapped[str] = mapped_column(String, nullable=False)
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class SharedProject(Base):
    """Shared conversion project accessible by team members"""
    __tablename__ = "shared_projects"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    team_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    owner_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    settings: Mapped[dict] = mapped_column(JSONB, nullable=True, default={})
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    team = relationship("Team", back_populates="projects")
    activities = relationship("ProjectActivity", back_populates="project", cascade="all, delete-orphan")


class ProjectActivity(Base):
    """Activity feed for shared projects"""
    __tablename__ = "project_activities"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shared_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, nullable=True, default={})
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    project = relationship("SharedProject", back_populates="activities")


class PublishedProject(Base):
    """Track published projects on platforms"""
    __tablename__ = "published_projects"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shared_projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    conversion_job_id: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )
    platform: Mapped[PlatformType] = mapped_column(
        SQLEnum(PlatformType),
        nullable=False,
    )
    platform_project_id: Mapped[str] = mapped_column(String, nullable=False)
    platform_project_slug: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    platform_version_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    version_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="published")
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


# Permission constants for role-based access control
class Permission:
    """Permission constants"""
    # Admin permissions
    ADMIN_ALL = "admin:all"
    ADMIN_TEAM_MANAGE = "admin:team:manage"
    ADMIN_TEAM_BILLING = "admin:team:billing"
    ADMIN_PROJECT_DELETE = "admin:project:delete"
    
    # Editor permissions
    EDITOR_CONVERT = "editor:convert"
    EDITOR_PROJECT_EDIT = "editor:project:edit"
    EDITOR_PROJECT_PUBLISH = "editor:project:publish"
    EDITOR_PROJECT_VIEW = "editor:project:view"
    
    # Viewer permissions
    VIEWER_PROJECT_VIEW = "viewer:project:view"


# Role to permission mapping
ROLE_PERMISSIONS = {
    TeamRole.ADMIN: [
        Permission.ADMIN_ALL,
        Permission.ADMIN_TEAM_MANAGE,
        Permission.ADMIN_TEAM_BILLING,
        Permission.ADMIN_PROJECT_DELETE,
        Permission.EDITOR_CONVERT,
        Permission.EDITOR_PROJECT_EDIT,
        Permission.EDITOR_PROJECT_PUBLISH,
        Permission.EDITOR_PROJECT_VIEW,
        Permission.VIEWER_PROJECT_VIEW,
    ],
    TeamRole.EDITOR: [
        Permission.EDITOR_CONVERT,
        Permission.EDITOR_PROJECT_EDIT,
        Permission.EDITOR_PROJECT_PUBLISH,
        Permission.EDITOR_PROJECT_VIEW,
        Permission.VIEWER_PROJECT_VIEW,
    ],
    TeamRole.VIEWER: [
        Permission.VIEWER_PROJECT_VIEW,
    ],
}


def has_permission(role: TeamRole, permission: str) -> bool:
    """Check if a role has a specific permission"""
    return permission in ROLE_PERMISSIONS.get(role, [])
