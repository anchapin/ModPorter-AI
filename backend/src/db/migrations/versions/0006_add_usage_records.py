"""Add usage_records table for metering subscription tier limits

Revision ID: 0006_add_usage_records
Revises: 0005_add_subscription_fields
Create Date: 2026-04-18

Issue: #977 - Implement usage limits and metering per subscription tier
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0006_add_usage_records"
down_revision = "0005_add_subscription_fields"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "usage_records",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("period_year", sa.Integer(), nullable=False),
        sa.Column("period_month", sa.Integer(), nullable=False),
        sa.Column(
            "web_conversions",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "api_conversions",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_usage_user_period",
        "usage_records",
        ["user_id", "period_year", "period_month"],
        unique=True,
    )


def downgrade():
    op.drop_index("ix_usage_user_period", table_name="usage_records")
    op.drop_table("usage_records")
