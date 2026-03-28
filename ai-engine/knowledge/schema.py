"""
Database schema for concept graph relationships.

This module defines the database models for storing concept nodes and their
relationships in the knowledge base cross-reference system.
"""

import uuid
from datetime import datetime
from typing import Optional, List
from enum import Enum

from sqlalchemy import (
    String,
    ForeignKey,
    DateTime,
    func,
    Text,
    Float,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column


class ConceptType(str, Enum):
    """Types of concepts that can be stored in the graph."""

    CLASS = "class"
    METHOD = "method"
    EVENT = "event"
    PROPERTY = "property"
    CONCEPT = "concept"
    IMPORT = "import"
    INTERFACE = "interface"


class RelationshipType(str, Enum):
    """Types of relationships between concepts."""

    EXTENDS = "extends"
    IMPLEMENTS = "implements"
    CALLS = "calls"
    USES = "uses"
    RELATED_TO = "related_to"
    CONTAINS = "contains"
    IMPORTED_BY = "imported_by"


class Base:
    """Base class for SQLAlchemy models."""

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ConceptNode(Base):
    """
    Represents a concept node in the knowledge graph.

    A concept can be a class, method, event, property, or general concept
    extracted from documents in the knowledge base.
    """

    __tablename__ = "concept_nodes"
    __table_args__ = (
        Index("ix_concept_nodes_name", "name"),
        Index("ix_concept_nodes_type", "type"),
        Index("ix_concept_nodes_document_id", "document_id"),
        {"extend_existing": True},
    )

    name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ConceptType.CONCEPT.value,
    )
    document_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    metadata: Mapped[Optional[dict]] = mapped_column(
        nullable=True,
    )

    outgoing_relationships: Mapped[List["ConceptRelationship"]] = relationship(
        "ConceptRelationship",
        foreign_keys="ConceptRelationship.source_node_id",
        back_populates="source_node",
        cascade="all, delete-orphan",
    )
    incoming_relationships: Mapped[List["ConceptRelationship"]] = relationship(
        "ConceptRelationship",
        foreign_keys="ConceptRelationship.target_node_id",
        back_populates="target_node",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ConceptNode(id={self.id}, name={self.name}, type={self.type})>"


class ConceptRelationship(Base):
    """
    Represents a relationship between two concept nodes.

    Relationships have a type (extends, implements, calls, uses, related_to)
    and a confidence score indicating the strength of the relationship.
    """

    __tablename__ = "concept_relationships"
    __table_args__ = (
        Index("ix_concept_relationships_source", "source_node_id"),
        Index("ix_concept_relationships_target", "target_node_id"),
        Index("ix_concept_relationships_type", "relationship_type"),
        Index("ix_concept_relationships_confidence", "confidence"),
        {"extend_existing": True},
    )

    source_node_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("concept_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_node_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("concept_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    relationship_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=RelationshipType.RELATED_TO.value,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5,
    )
    metadata: Mapped[Optional[dict]] = mapped_column(
        nullable=True,
    )

    source_node: Mapped["ConceptNode"] = relationship(
        "ConceptNode",
        foreign_keys=[source_node_id],
        back_populates="outgoing_relationships",
    )
    target_node: Mapped["ConceptNode"] = relationship(
        "ConceptNode",
        foreign_keys=[target_node_id],
        back_populates="incoming_relationships",
    )

    def __repr__(self) -> str:
        return (
            f"<ConceptRelationship("
            f"source={self.source_node_id}, "
            f"target={self.target_node_id}, "
            f"type={self.relationship_type}, "
            f"confidence={self.confidence})>"
        )


def get_concept_types() -> List[str]:
    """Get list of valid concept types."""
    return [ct.value for ct in ConceptType]


def get_relationship_types() -> List[str]:
    """Get list of valid relationship types."""
    return [rt.value for rt in RelationshipType]
