"""Knowledge Graph and Community Curation System

Revision ID: 0004_knowledge_graph
Revises: 0003_add_behavior_templates
Create Date: 2025-01-08 18:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0004_knowledge_graph"
down_revision = "0003_add_behavior_templates"
branch_labels = None
depends_on = None


def upgrade():
    # Create knowledge_nodes table
    op.create_table(
        "knowledge_nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("neo4j_id", sa.String(), nullable=True),
        sa.Column("node_type", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "properties", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("minecraft_version", sa.String(length=20), nullable=False),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("expert_validated", sa.Boolean(), nullable=False),
        sa.Column("community_rating", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_knowledge_nodes_id"), "knowledge_nodes", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_knowledge_nodes_node_type"),
        "knowledge_nodes",
        ["node_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_nodes_name"), "knowledge_nodes", ["name"], unique=False
    )
    op.create_index(
        op.f("ix_knowledge_nodes_neo4j_id"),
        "knowledge_nodes",
        ["neo4j_id"],
        unique=False,
    )

    # Create knowledge_relationships table
    op.create_table(
        "knowledge_relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("neo4j_id", sa.String(), nullable=True),
        sa.Column("source_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_type", sa.String(length=100), nullable=False),
        sa.Column("confidence_score", sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column(
            "properties", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("minecraft_version", sa.String(length=20), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("expert_validated", sa.Boolean(), nullable=False),
        sa.Column("community_votes", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_node_id"], ["knowledge_nodes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["target_node_id"], ["knowledge_nodes.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_knowledge_relationships_id"),
        "knowledge_relationships",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_relationships_relationship_type"),
        "knowledge_relationships",
        ["relationship_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_relationships_neo4j_id"),
        "knowledge_relationships",
        ["neo4j_id"],
        unique=False,
    )

    # Create conversion_patterns table
    op.create_table(
        "conversion_patterns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "java_pattern", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "bedrock_pattern", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "graph_representation",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("validation_status", sa.String(length=20), nullable=False),
        sa.Column("community_rating", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("expert_reviewed", sa.Boolean(), nullable=False),
        sa.Column("success_rate", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("usage_count", sa.Integer(), nullable=False),
        sa.Column(
            "minecraft_versions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_conversion_patterns_id"), "conversion_patterns", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_conversion_patterns_name"),
        "conversion_patterns",
        ["name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_conversion_patterns_validation_status"),
        "conversion_patterns",
        ["validation_status"],
        unique=False,
    )

    # Create community_contributions table
    op.create_table(
        "community_contributions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contributor_id", sa.String(), nullable=False),
        sa.Column("contribution_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "contribution_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("review_status", sa.String(length=20), nullable=False),
        sa.Column("votes", sa.Integer(), nullable=False),
        sa.Column("comments", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "validation_results",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("minecraft_version", sa.String(length=20), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_community_contributions_id"),
        "community_contributions",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_community_contributions_contributor_id"),
        "community_contributions",
        ["contributor_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_community_contributions_review_status"),
        "community_contributions",
        ["review_status"],
        unique=False,
    )

    # Create version_compatibility table
    op.create_table(
        "version_compatibility",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("java_version", sa.String(length=20), nullable=False),
        sa.Column("bedrock_version", sa.String(length=20), nullable=False),
        sa.Column(
            "compatibility_score", sa.Numeric(precision=3, scale=2), nullable=False
        ),
        sa.Column(
            "features_supported",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "deprecated_patterns",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "migration_guides", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "auto_update_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "known_issues", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_version_compatibility_id"),
        "version_compatibility",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_version_compatibility_java_version"),
        "version_compatibility",
        ["java_version"],
        unique=False,
    )
    op.create_index(
        op.f("ix_version_compatibility_bedrock_version"),
        "version_compatibility",
        ["bedrock_version"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f("ix_version_compatibility_bedrock_version"),
        table_name="version_compatibility",
    )
    op.drop_index(
        op.f("ix_version_compatibility_java_version"),
        table_name="version_compatibility",
    )
    op.drop_index(
        op.f("ix_version_compatibility_id"), table_name="version_compatibility"
    )
    op.drop_table("version_compatibility")
    op.drop_index(
        op.f("ix_community_contributions_review_status"),
        table_name="community_contributions",
    )
    op.drop_index(
        op.f("ix_community_contributions_contributor_id"),
        table_name="community_contributions",
    )
    op.drop_index(
        op.f("ix_community_contributions_id"), table_name="community_contributions"
    )
    op.drop_table("community_contributions")
    op.drop_index(
        op.f("ix_conversion_patterns_validation_status"),
        table_name="conversion_patterns",
    )
    op.drop_index(op.f("ix_conversion_patterns_name"), table_name="conversion_patterns")
    op.drop_index(op.f("ix_conversion_patterns_id"), table_name="conversion_patterns")
    op.drop_table("conversion_patterns")
    op.drop_index(
        op.f("ix_knowledge_relationships_relationship_type"),
        table_name="knowledge_relationships",
    )
    op.drop_index(
        op.f("ix_knowledge_relationships_id"), table_name="knowledge_relationships"
    )
    op.drop_index(
        op.f("ix_knowledge_relationships_neo4j_id"),
        table_name="knowledge_relationships",
    )
    op.drop_table("knowledge_relationships")
    op.drop_index(op.f("ix_knowledge_nodes_name"), table_name="knowledge_nodes")
    op.drop_index(op.f("ix_knowledge_nodes_node_type"), table_name="knowledge_nodes")
    op.drop_index(op.f("ix_knowledge_nodes_id"), table_name="knowledge_nodes")
    op.drop_index(op.f("ix_knowledge_nodes_neo4j_id"), table_name="knowledge_nodes")
    op.drop_table("knowledge_nodes")
