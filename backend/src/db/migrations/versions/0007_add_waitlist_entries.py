"""Add waitlist_entries table for pre-launch signups

Revision ID: 0007_add_waitlist_entries
Revises: 0006_add_usage_records
Create Date: 2026-04-24
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_add_waitlist_entries"
down_revision = "0006_add_usage_records"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "waitlist_entries",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "email",
            sa.String(255),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "name",
            sa.String(255),
            nullable=True,
        ),
        sa.Column(
            "source",
            sa.String(100),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_waitlist_entries_email", "waitlist_entries", ["email"], unique=True)


def downgrade():
    op.drop_index("ix_waitlist_entries_email", table_name="waitlist_entries")
    op.drop_table("waitlist_entries")
