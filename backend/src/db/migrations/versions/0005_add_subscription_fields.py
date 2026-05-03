"""Add subscription and billing fields to users table

Revision ID: 0005_add_subscription_fields
Revises: 0004_add_document_embedding_hierarchy
Create Date: 2026-04-17

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0005_add_subscription_fields"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column(
            "subscription_tier",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'free'"),
        ),
    )
    op.add_column(
        "users",
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True, unique=True),
    )
    op.add_column(
        "users",
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True, unique=True),
    )
    op.add_column(
        "users",
        sa.Column("subscription_status", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column("users", "trial_ends_at")
    op.drop_column("users", "subscription_status")
    op.drop_column("users", "stripe_subscription_id")
    op.drop_column("users", "stripe_customer_id")
    op.drop_column("users", "subscription_tier")
