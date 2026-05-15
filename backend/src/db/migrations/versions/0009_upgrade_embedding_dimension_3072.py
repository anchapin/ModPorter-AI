"""upgrade embedding dimension from 1536 to 3072

Revision ID: 0009_upgrade_embedding_dimension_3072
Revises: 0008_add_batch_user_to_jobs
Create Date: 2026-05-15 10:00:00.000000

Upgrade from text-embedding-3-small (1536d) to text-embedding-3-large (3072d)
for improved RAG retrieval quality (issue #1496).

NOTE: This migration clears existing embedding vectors because pgvector does not
support in-place dimension changes. Embeddings must be regenerated after migration.
"""

from alembic import op
import sqlalchemy as sa

revision = "0009_upgrade_embedding_dimension_3072"
down_revision = "0008_add_batch_user_to_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE document_embeddings ALTER COLUMN embedding TYPE VECTOR(3072)")
    op.execute("ALTER TABLE patterns ALTER COLUMN embedding TYPE VECTOR(3072)")
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE VECTOR(3072)")
    op.execute("ALTER TABLE search_index ALTER COLUMN embedding TYPE VECTOR(3072)")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION match_patterns(
            query_embedding VECTOR(3072),
            match_threshold FLOAT = 0.7,
            match_count INT = 5
        )
        RETURNS TABLE (
            id UUID,
            name VARCHAR(255),
            description TEXT,
            category VARCHAR(100),
            content TEXT,
            similarity FLOAT
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RETURN QUERY
            SELECT
                p.id,
                p.name,
                p.description,
                p.category,
                p.content,
                1 - (p.embedding <=> query_embedding) AS similarity
            FROM patterns p
            WHERE p.embedding IS NOT NULL
            AND 1 - (p.embedding <=> query_embedding) > match_threshold
            ORDER BY p.embedding <=> query_embedding
            LIMIT match_count;
        END;
        $$;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION match_chunks(
            query_embedding VECTOR(3072),
            match_threshold FLOAT = 0.7,
            match_count INT = 5
        )
        RETURNS TABLE (
            id UUID,
            document_id UUID,
            content TEXT,
            similarity FLOAT
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RETURN QUERY
            SELECT
                dc.id,
                dc.document_id,
                dc.content,
                1 - (dc.embedding <=> query_embedding) AS similarity
            FROM document_chunks dc
            WHERE dc.embedding IS NOT NULL
            AND 1 - (dc.embedding <=> query_embedding) > match_threshold
            ORDER BY dc.embedding <=> query_embedding
            LIMIT match_count;
        END;
        $$;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE search_index ALTER COLUMN embedding TYPE VECTOR(1536)")
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE VECTOR(1536)")
    op.execute("ALTER TABLE patterns ALTER COLUMN embedding TYPE VECTOR(1536)")
    op.execute("ALTER TABLE document_embeddings ALTER COLUMN embedding TYPE VECTOR(1536)")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION match_patterns(
            query_embedding VECTOR(1536),
            match_threshold FLOAT = 0.7,
            match_count INT = 5
        )
        RETURNS TABLE (
            id UUID,
            name VARCHAR(255),
            description TEXT,
            category VARCHAR(100),
            content TEXT,
            similarity FLOAT
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RETURN QUERY
            SELECT
                p.id,
                p.name,
                p.description,
                p.category,
                p.content,
                1 - (p.embedding <=> query_embedding) AS similarity
            FROM patterns p
            WHERE p.embedding IS NOT NULL
            AND 1 - (p.embedding <=> query_embedding) > match_threshold
            ORDER BY p.embedding <=> query_embedding
            LIMIT match_count;
        END;
        $$;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION match_chunks(
            query_embedding VECTOR(1536),
            match_threshold FLOAT = 0.7,
            match_count INT = 5
        )
        RETURNS TABLE (
            id UUID,
            document_id UUID,
            content TEXT,
            similarity FLOAT
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RETURN QUERY
            SELECT
                dc.id,
                dc.document_id,
                dc.content,
                1 - (dc.embedding <=> query_embedding) AS similarity
            FROM document_chunks dc
            WHERE dc.embedding IS NOT NULL
            AND 1 - (dc.embedding <=> query_embedding) > match_threshold
            ORDER BY dc.embedding <=> query_embedding
            LIMIT match_count;
        END;
        $$;
        """
    )
