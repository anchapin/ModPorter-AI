"""Initial revision: create conversion_jobs, conversion_results, job_progress tables

Revision ID: 0001_initial
Revises: 
Create Date: 2024-06-08

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')
    op.create_table(
        'conversion_jobs',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('status', sa.String(length=20), nullable=False, server_default=sa.text("'queued'")),
        sa.Column('input_data', sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_table(
        'conversion_results',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('job_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('conversion_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('output_data', sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_table(
        'job_progress',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('job_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('conversion_jobs.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('progress', sa.Integer, nullable=False, server_default=sa.text('0')),
        sa.Column('last_update', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )

def downgrade():
    op.drop_table('job_progress')
    op.drop_table('conversion_results')
    op.drop_table('conversion_jobs')