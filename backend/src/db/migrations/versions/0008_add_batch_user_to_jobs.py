"""add batch_id and user_id to conversion_jobs

Revision ID: 0008_add_batch_user_to_jobs
Revises: 0007_add_comparison_tables
Create Date: 2025-04-24 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "0008_add_batch_user_to_jobs"
down_revision = "0007_add_comparison_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversion_jobs",
        sa.Column("batch_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "conversion_jobs",
        sa.Column("user_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "ix_conversion_jobs_batch_id",
        "conversion_jobs",
        ["batch_id"],
    )
    op.create_index(
        "ix_conversion_jobs_user_id",
        "conversion_jobs",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_conversion_jobs_user_id", table_name="conversion_jobs")
    op.drop_index("ix_conversion_jobs_batch_id", table_name="conversion_jobs")
    op.drop_column("conversion_jobs", "user_id")
    op.drop_column("conversion_jobs", "batch_id")
