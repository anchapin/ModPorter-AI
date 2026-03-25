"""Add hierarchical indexing fields to document_embeddings

Revision ID: 0004
Revises: 0003_add_behavior_templates
Create Date: 2026-03-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, None] = '0003_add_behavior_templates'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to document_embeddings table
    op.add_column('document_embeddings', 
        sa.Column('parent_document_id', 
                 postgresql.UUID(as_uuid=True), 
                 nullable=True))
    op.add_column('document_embeddings', 
        sa.Column('chunk_index', 
                 sa.Integer(), 
                 nullable=True))
    op.add_column('document_embeddings', 
        sa.Column('hierarchy_level', 
                 sa.Integer(), 
                 nullable=False, 
                 server_default='2'))
    op.add_column('document_embeddings', 
        sa.Column('title', 
                 sa.String(), 
                 nullable=True))
    op.add_column('document_embeddings', 
        sa.Column('metadata', 
                 postgresql.JSONB(), 
                 nullable=True))
    
    # Create indexes for new fields
    op.create_index('ix_document_embeddings_parent_document_id', 
                    'document_embeddings', 
                    ['parent_document_id'])
    op.create_index('ix_document_embeddings_chunk_index', 
                    'document_embeddings', 
                    ['chunk_index'])
    op.create_index('ix_document_embeddings_title', 
                    'document_embeddings', 
                    ['title'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_document_embeddings_title', 'document_embeddings')
    op.drop_index('ix_document_embeddings_chunk_index', 'document_embeddings')
    op.drop_index('ix_document_embeddings_parent_document_id', 'document_embeddings')
    
    # Drop columns
    op.drop_column('document_embeddings', 'metadata')
    op.drop_column('document_embeddings', 'title')
    op.drop_column('document_embeddings', 'hierarchy_level')
    op.drop_column('document_embeddings', 'chunk_index')
    op.drop_column('document_embeddings', 'parent_document_id')
