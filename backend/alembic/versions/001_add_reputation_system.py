"""Add reputation system tables

Revision ID: 001_add_reputation_system
Revises:
Create Date: 2025-11-18 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_add_reputation_system'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create reputation system tables."""

    # Import the models to get table definitions

    # Create user_reputations table
    op.create_table('user_reputations',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('reputation_score', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('level', sa.String(length=20), nullable=False),
        sa.Column('feedback_count', sa.Integer(), nullable=False),
        sa.Column('approved_feedback', sa.Integer(), nullable=False),
        sa.Column('helpful_votes_received', sa.Integer(), nullable=False),
        sa.Column('total_votes_cast', sa.Integer(), nullable=False),
        sa.Column('moderation_actions', sa.Integer(), nullable=False),
        sa.Column('quality_bonus_total', sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column('penalties_total', sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column('last_activity_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('consecutive_days_active', sa.Integer(), nullable=False),
        sa.Column('badges_earned', sa.JSON(), nullable=False),
        sa.Column('privileges', sa.JSON(), nullable=False),
        sa.Column('restrictions', sa.JSON(), nullable=False),
        sa.Column('reputation_history', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_user_reputations_user_id'), 'user_reputations', ['user_id'], unique=False)

    # Create reputation_bonuses table
    op.create_table('reputation_bonuses',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('bonus_type', sa.String(length=50), nullable=False),
        sa.Column('amount', sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('related_entity_id', sa.String(), nullable=True),
        sa.Column('awarded_by', sa.String(), nullable=True),
        sa.Column('is_manual', sa.Boolean(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.Column('awarded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reputation_bonuses_user_id'), 'reputation_bonuses', ['user_id'], unique=False)

    # Create quality_assessments table
    op.create_table('quality_assessments',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('feedback_id', sa.String(), nullable=False),
        sa.Column('quality_score', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('quality_grade', sa.String(length=15), nullable=False),
        sa.Column('issues_detected', sa.JSON(), nullable=False),
        sa.Column('warnings', sa.JSON(), nullable=False),
        sa.Column('auto_actions', sa.JSON(), nullable=False),
        sa.Column('assessor_type', sa.String(length=20), nullable=False),
        sa.Column('assessor_id', sa.String(), nullable=True),
        sa.Column('confidence_score', sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column('requires_human_review', sa.Boolean(), nullable=False),
        sa.Column('reviewed_by_human', sa.Boolean(), nullable=False),
        sa.Column('human_reviewer_id', sa.String(), nullable=True),
        sa.Column('human_override_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('human_override_reason', sa.Text(), nullable=True),
        sa.Column('assessment_data', sa.JSON(), nullable=False),
        sa.Column('assessment_version', sa.String(length=10), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('feedback_id')
    )
    op.create_index(op.f('ix_quality_assessments_feedback_id'), 'quality_assessments', ['feedback_id'], unique=False)

    # Create reputation_events table
    op.create_table('reputation_events',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('score_change', sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column('previous_score', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('new_score', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('related_entity_type', sa.String(length=30), nullable=True),
        sa.Column('related_entity_id', sa.String(), nullable=True),
        sa.Column('triggered_by', sa.String(), nullable=True),
        sa.Column('context_data', sa.JSON(), nullable=False),
        sa.Column('is_reversible', sa.Boolean(), nullable=False),
        sa.Column('reversed_by', sa.String(), nullable=True),
        sa.Column('event_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reputation_events_user_id'), 'reputation_events', ['user_id'], unique=False)
    op.create_index(op.f('ix_reputation_events_event_date'), 'reputation_events', ['event_date'], unique=False)

    # Create quality_metrics table
    op.create_table('quality_metrics',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('metric_date', sa.Date(), nullable=False),
        sa.Column('total_feedback_assessed', sa.Integer(), nullable=False),
        sa.Column('average_quality_score', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('quality_distribution', sa.JSON(), nullable=False),
        sa.Column('issue_type_counts', sa.JSON(), nullable=False),
        sa.Column('auto_action_counts', sa.JSON(), nullable=False),
        sa.Column('human_review_rate', sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column('false_positive_rate', sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column('processing_time_avg', sa.Numeric(precision=8, scale=3), nullable=False),
        sa.Column('assessment_count_by_user_level', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('metric_date')
    )
    op.create_index(op.f('ix_quality_metrics_metric_date'), 'quality_metrics', ['metric_date'], unique=False)


def downgrade():
    """Drop reputation system tables."""

    # Drop tables in reverse order of creation
    op.drop_index(op.f('ix_quality_metrics_metric_date'), table_name='quality_metrics')
    op.drop_table('quality_metrics')

    op.drop_index(op.f('ix_reputation_events_event_date'), table_name='reputation_events')
    op.drop_index(op.f('ix_reputation_events_user_id'), table_name='reputation_events')
    op.drop_table('reputation_events')

    op.drop_index(op.f('ix_quality_assessments_feedback_id'), table_name='quality_assessments')
    op.drop_table('quality_assessments')

    op.drop_index(op.f('ix_reputation_bonuses_user_id'), table_name='reputation_bonuses')
    op.drop_table('reputation_bonuses')

    op.drop_index(op.f('ix_user_reputations_user_id'), table_name='user_reputations')
    op.drop_table('user_reputations')