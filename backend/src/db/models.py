from typing import Optional
from sqlalchemy import (
    String,
    Integer,
    ForeignKey,
    DateTime,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from src.db.declarative_base import Base

class ConversionJob(Base):
    __tablename__ = "conversion_jobs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'queued'"),
    )
    input_data: Mapped[dict] = mapped_column(
        JSONB, nullable=False
    )
    created_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationship: one job -> many results and progress
    results = relationship("ConversionResult", back_populates="job", cascade="all, delete-orphan")
    progress = relationship("JobProgress", back_populates="job", cascade="all, delete-orphan", uselist=False)

class ConversionResult(Base):
    __tablename__ = "conversion_results"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    job_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversion_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    output_data: Mapped[dict] = mapped_column(
        JSONB, nullable=False
    )
    created_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    job = relationship("ConversionJob", back_populates="results")

class JobProgress(Base):
    __tablename__ = "job_progress"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    job_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversion_jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    progress: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    last_update: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    job = relationship("ConversionJob", back_populates="progress")


# New Addon Management Models

class Addon(Base):
    __tablename__ = "addons"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False) # Assuming user_id is a string for now
    created_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    blocks = relationship("AddonBlock", back_populates="addon", cascade="all, delete-orphan")
    assets = relationship("AddonAsset", back_populates="addon", cascade="all, delete-orphan")
    recipes = relationship("AddonRecipe", back_populates="addon", cascade="all, delete-orphan")


class AddonBlock(Base):
    __tablename__ = "addon_blocks"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    addon_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("addons.id", ondelete="CASCADE"), nullable=False
    )
    identifier: Mapped[str] = mapped_column(String, nullable=False)
    properties: Mapped[dict] = mapped_column(JSONB, nullable=True, server_default=text("'{}'::jsonb"))
    created_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    addon = relationship("Addon", back_populates="blocks")
    behavior = relationship("AddonBehavior", back_populates="block", uselist=False, cascade="all, delete-orphan")


class AddonAsset(Base):
    __tablename__ = "addon_assets"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    addon_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("addons.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String, nullable=False)  # E.g., "texture", "sound", "script"
    path: Mapped[str] = mapped_column(String, nullable=False) # Relative path within the addon structure
    original_filename: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationship
    addon = relationship("Addon", back_populates="assets")


class AddonBehavior(Base):
    __tablename__ = "addon_behaviors"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    block_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("addon_blocks.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb")) # Behavior components, events, etc.
    created_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationship
    block = relationship("AddonBlock", back_populates="behavior")


class AddonRecipe(Base):
    __tablename__ = "addon_recipes"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    addon_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("addons.id", ondelete="CASCADE"), nullable=False
    )
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb")) # Crafting recipe definition
    created_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationship
    addon = relationship("Addon", back_populates="recipes")