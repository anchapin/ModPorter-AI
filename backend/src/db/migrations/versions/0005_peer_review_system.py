"""Peer Review System

Revision ID: 0005_peer_review_system
Revises: 0004_knowledge_graph
Create Date: 2025-11-09 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0005_peer_review_system"
down_revision = "0004_knowledge_graph"
branch_labels = None
depends_on = None


def upgrade():
    """Create peer review system tables."""

    # Create peer_reviews table
    op.create_table(
        "peer_reviews",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("contribution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_id", sa.String(), nullable=False),
        sa.Column(
            "review_type", sa.String(length=20), nullable=False, default="community"
        ),
        sa.Column("status", sa.String(length=20), nullable=False, default="pending"),
        sa.Column("overall_score", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("technical_accuracy", sa.Integer(), nullable=True),
        sa.Column("documentation_quality", sa.Integer(), nullable=True),
        sa.Column("minecraft_compatibility", sa.Integer(), nullable=True),
        sa.Column("innovation_value", sa.Integer(), nullable=True),
        sa.Column("review_comments", sa.Text(), nullable=False, default=""),
        sa.Column(
            "suggestions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default="[]",
        ),
        sa.Column(
            "approval_conditions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default="[]",
        ),
        sa.Column(
            "automated_checks",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default="{}",
        ),
        sa.Column(
            "reviewer_confidence", sa.Numeric(precision=3, scale=2), nullable=True
        ),
        sa.Column("review_time_minutes", sa.Integer(), nullable=True),
        sa.Column("review_round", sa.Integer(), nullable=False, default=1),
        sa.Column("is_final_review", sa.Boolean(), nullable=False, default=False),
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
            ["contribution_id"], ["community_contributions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_peer_reviews_id"), "peer_reviews", ["id"], unique=False)
    op.create_index(
        op.f("ix_peer_reviews_contribution_id"),
        "peer_reviews",
        ["contribution_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_peer_reviews_reviewer_id"),
        "peer_reviews",
        ["reviewer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_peer_reviews_status"), "peer_reviews", ["status"], unique=False
    )

    # Create review_workflows table
    op.create_table(
        "review_workflows",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("contribution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "workflow_type", sa.String(length=30), nullable=False, default="standard"
        ),
        sa.Column("status", sa.String(length=20), nullable=False, default="active"),
        sa.Column(
            "current_stage",
            sa.String(length=30),
            nullable=False,
            default="initial_review",
        ),
        sa.Column("required_reviews", sa.Integer(), nullable=False, default=2),
        sa.Column("completed_reviews", sa.Integer(), nullable=False, default=0),
        sa.Column(
            "approval_threshold",
            sa.Numeric(precision=3, scale=2),
            nullable=False,
            default=7.0,
        ),
        sa.Column(
            "auto_approve_score",
            sa.Numeric(precision=3, scale=2),
            nullable=False,
            default=8.5,
        ),
        sa.Column(
            "reject_threshold",
            sa.Numeric(precision=3, scale=2),
            nullable=False,
            default=3.0,
        ),
        sa.Column(
            "assigned_reviewers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default="[]",
        ),
        sa.Column(
            "reviewer_pool",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default="[]",
        ),
        sa.Column("escalation_level", sa.Integer(), nullable=False, default=0),
        sa.Column("deadline_minutes", sa.Integer(), nullable=True),
        sa.Column(
            "automation_rules",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default="{}",
        ),
        sa.Column(
            "stage_history",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default="[]",
        ),
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
            ["contribution_id"], ["community_contributions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_review_workflows_id"), "review_workflows", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_review_workflows_contribution_id"),
        "review_workflows",
        ["contribution_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_review_workflows_status"), "review_workflows", ["status"], unique=False
    )

    # Create reviewer_expertise table
    op.create_table(
        "reviewer_expertise",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("reviewer_id", sa.String(), nullable=False),
        sa.Column(
            "expertise_areas",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default="[]",
        ),
        sa.Column(
            "minecraft_versions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default="[]",
        ),
        sa.Column("java_experience_level", sa.Integer(), nullable=False, default=1),
        sa.Column("bedrock_experience_level", sa.Integer(), nullable=False, default=1),
        sa.Column("review_count", sa.Integer(), nullable=False, default=0),
        sa.Column(
            "average_review_score", sa.Numeric(precision=3, scale=2), nullable=True
        ),
        sa.Column("approval_rate", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("response_time_avg", sa.Integer(), nullable=True),
        sa.Column("expertise_score", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("is_active_reviewer", sa.Boolean(), nullable=False, default=True),
        sa.Column("max_concurrent_reviews", sa.Integer(), nullable=False, default=3),
        sa.Column("current_reviews", sa.Integer(), nullable=False, default=0),
        sa.Column(
            "special_permissions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default="[]",
        ),
        sa.Column("reputation_score", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("last_active_date", sa.DateTime(timezone=True), nullable=True),
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
        op.f("ix_reviewer_expertise_id"), "reviewer_expertise", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_reviewer_expertise_reviewer_id"),
        "reviewer_expertise",
        ["reviewer_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_reviewer_expertise_is_active_reviewer"),
        "reviewer_expertise",
        ["is_active_reviewer"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reviewer_expertise_expertise_score"),
        "reviewer_expertise",
        ["expertise_score"],
        unique=False,
    )

    # Create review_templates table
    op.create_table(
        "review_templates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("template_name", sa.String(length=100), nullable=False),
        sa.Column("template_type", sa.String(length=30), nullable=False),
        sa.Column(
            "contribution_types",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default="[]",
        ),
        sa.Column(
            "review_criteria",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default="[]",
        ),
        sa.Column(
            "scoring_weights",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default="{}",
        ),
        sa.Column(
            "required_checks",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default="[]",
        ),
        sa.Column(
            "automated_tests",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default="[]",
        ),
        sa.Column(
            "approval_conditions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default="[]",
        ),
        sa.Column(
            "reviewer_qualifications",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default="[]",
        ),
        sa.Column(
            "default_workflow",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default="{}",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("version", sa.String(length=10), nullable=False, default="1.0"),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=False, default=0),
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
        op.f("ix_review_templates_id"), "review_templates", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_review_templates_template_type"),
        "review_templates",
        ["template_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_review_templates_is_active"),
        "review_templates",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_review_templates_usage_count"),
        "review_templates",
        ["usage_count"],
        unique=False,
    )

    # Create review_analytics table
    op.create_table(
        "review_analytics",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("contributions_submitted", sa.Integer(), nullable=False, default=0),
        sa.Column("contributions_approved", sa.Integer(), nullable=False, default=0),
        sa.Column("contributions_rejected", sa.Integer(), nullable=False, default=0),
        sa.Column(
            "contributions_needing_revision", sa.Integer(), nullable=False, default=0
        ),
        sa.Column(
            "avg_review_time_hours", sa.Numeric(precision=5, scale=2), nullable=True
        ),
        sa.Column("avg_review_score", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("active_reviewers", sa.Integer(), nullable=False, default=0),
        sa.Column(
            "reviewer_utilization", sa.Numeric(precision=3, scale=2), nullable=True
        ),
        sa.Column("auto_approvals", sa.Integer(), nullable=False, default=0),
        sa.Column("auto_rejections", sa.Integer(), nullable=False, default=0),
        sa.Column("manual_reviews", sa.Integer(), nullable=False, default=0),
        sa.Column("escalation_events", sa.Integer(), nullable=False, default=0),
        sa.Column(
            "quality_score_distribution",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default="{}",
        ),
        sa.Column(
            "reviewer_performance",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default="{}",
        ),
        sa.Column(
            "bottlenecks",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default="[]",
        ),
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
        op.f("ix_review_analytics_id"), "review_analytics", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_review_analytics_date"), "review_analytics", ["date"], unique=True
    )

    # Create triggers for updated_at columns
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # Add triggers to all tables with updated_at columns
    op.execute(
        "CREATE TRIGGER update_peer_reviews_updated_at BEFORE UPDATE ON peer_reviews FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();"
    )
    op.execute(
        "CREATE TRIGGER update_review_workflows_updated_at BEFORE UPDATE ON review_workflows FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();"
    )
    op.execute(
        "CREATE TRIGGER update_reviewer_expertise_updated_at BEFORE UPDATE ON reviewer_expertise FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();"
    )
    op.execute(
        "CREATE TRIGGER update_review_templates_updated_at BEFORE UPDATE ON review_templates FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();"
    )
    op.execute(
        "CREATE TRIGGER update_review_analytics_updated_at BEFORE UPDATE ON review_analytics FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();"
    )


def downgrade():
    """Remove peer review system tables."""

    # Drop triggers first
    op.execute("DROP TRIGGER IF EXISTS update_peer_reviews_updated_at ON peer_reviews;")
    op.execute(
        "DROP TRIGGER IF EXISTS update_review_workflows_updated_at ON review_workflows;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS update_reviewer_expertise_updated_at ON reviewer_expertise;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS update_review_templates_updated_at ON review_templates;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS update_review_analytics_updated_at ON review_analytics;"
    )

    # Drop tables
    op.drop_table("review_analytics")
    op.drop_table("review_templates")
    op.drop_table("reviewer_expertise")
    op.drop_table("review_workflows")
    op.drop_table("peer_reviews")

    # Drop the function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
