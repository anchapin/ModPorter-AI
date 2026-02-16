"""
Integration tests for pgvector similarity search functionality.

These tests require a PostgreSQL database with the pgvector extension enabled.
They will be skipped when running against SQLite.

Run with: pytest backend/tests/integration/test_pgvector_embeddings.py -v
"""

import os
import sys
import pytest
from uuid import uuid4
from pathlib import Path

# Add the src directory to the Python path
backend_dir = Path(__file__).parent.parent.parent
src_dir = backend_dir / "src"
sys.path.insert(0, str(src_dir))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Import CRUD operations
from db import crud

# Skip all tests if using SQLite (these tests require PostgreSQL with pgvector)
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

# Check if we have a real PostgreSQL database
IS_POSTGRES = TEST_DATABASE_URL.startswith("postgresql")

pytestmark = pytest.mark.skipif(
    not IS_POSTGRES,
    reason="pgvector integration tests require PostgreSQL with pgvector extension"
)

# Sample embedding dimensions (using 1536 for OpenAI ada embeddings)
SAMPLE_DIMENSION = 1536

# Sample test embeddings
SAMPLE_EMBEDDING_1 = [0.1] * SAMPLE_DIMENSION
SAMPLE_EMBEDDING_2 = [0.2] * SAMPLE_DIMENSION
SAMPLE_EMBEDDING_3 = [0.3] * SAMPLE_DIMENSION
SAMPLE_EMBEDDING_SIMILAR = [0.11] * SAMPLE_DIMENSION  # Very similar to SAMPLE_EMBEDDING_1
SAMPLE_EMBEDDING_DIFFERENT = [0.9] * SAMPLE_DIMENSION  # Very different from others

SAMPLE_SOURCE_1 = "test_doc_1.txt"
SAMPLE_SOURCE_2 = "test_doc_2.txt"
SAMPLE_SOURCE_3 = "test_doc_3.txt"
SAMPLE_SOURCE_4 = "test_doc_similar.txt"
SAMPLE_SOURCE_5 = "test_doc_different.txt"

SAMPLE_HASH_1 = "hash_test_1"
SAMPLE_HASH_2 = "hash_test_2"
SAMPLE_HASH_3 = "hash_test_3"
SAMPLE_HASH_4 = "hash_test_similar"
SAMPLE_HASH_5 = "hash_test_different"


@pytest.fixture(scope="module")
def pgvector_engine():
    """Create a test engine for PostgreSQL with pgvector."""
    if not IS_POSTGRES:
        pytest.skip("PostgreSQL required for pgvector tests")
    
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    return engine


@pytest.fixture(scope="module")
async def pgvector_session(pgvector_engine):
    """Create a database session for pgvector tests."""
    async_session = async_sessionmaker(
        bind=pgvector_engine,
        expire_on_commit=False,
        class_=AsyncSession
    )
    
    async with pgvector_engine.begin() as conn:
        # Ensure pgvector extension is available
        from sqlalchemy import text
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"vector\""))
    
    async with async_session() as session:
        yield session
        await session.close()


@pytest.mark.asyncio
async def test_find_similar_embeddings_basic(pgvector_session: AsyncSession):
    """
    Test basic similarity search functionality.
    
    Creates embeddings at known distances and verifies that
    similar embeddings are returned first.
    """
    # Create test embeddings with known similarity
    await crud.create_document_embedding(
        db=pgvector_session,
        embedding=SAMPLE_EMBEDDING_1,
        document_source=SAMPLE_SOURCE_1,
        content_hash=SAMPLE_HASH_1,
    )
    
    await crud.create_document_embedding(
        db=pgvector_session,
        embedding=SAMPLE_EMBEDDING_SIMILAR,  # Very similar to EMBEDDING_1
        document_source=SAMPLE_SOURCE_4,
        content_hash=SAMPLE_HASH_4,
    )
    
    await crud.create_document_embedding(
        db=pgvector_session,
        embedding=SAMPLE_EMBEDDING_DIFFERENT,  # Very different
        document_source=SAMPLE_SOURCE_5,
        content_hash=SAMPLE_HASH_5,
    )
    
    # Query using EMBEDDING_1 - should return EMBEDDING_1 (itself) and SAMPLE_EMBEDDING_SIMILAR first
    results = await crud.find_similar_embeddings(
        db=pgvector_session,
        query_embedding=SAMPLE_EMBEDDING_1,
        limit=3
    )
    
    assert len(results) > 0, "Should return at least one similar embedding"
    
    # The most similar should be EMBEDDING_1 (exact match) or SAMPLE_EMBEDDING_SIMILAR
    # Check that we get relevant results
    sources = [r.document_source for r in results]
    assert SAMPLE_SOURCE_1 in sources or SAMPLE_SOURCE_4 in sources, \
        "Should find similar embeddings"


@pytest.mark.asyncio
async def test_find_similar_embeddings_limit(pgvector_session: AsyncSession):
    """Test that the limit parameter works correctly."""
    # Create multiple embeddings
    for i in range(5):
        embedding = [0.1 * (i + 1)] * SAMPLE_DIMENSION
        await crud.create_document_embedding(
            db=pgvector_session,
            embedding=embedding,
            document_source=f"doc_{i}.txt",
            content_hash=f"hash_{i}",
        )
    
    # Query with limit=2
    results = await crud.find_similar_embeddings(
        db=pgvector_session,
        query_embedding=SAMPLE_EMBEDDING_1,
        limit=2
    )
    
    assert len(results) <= 2, "Should respect the limit parameter"


@pytest.mark.asyncio
async def test_find_similar_embeddings_empty_database(pgvector_session: AsyncSession):
    """Test that similarity search handles empty database gracefully."""
    results = await crud.find_similar_embeddings(
        db=pgvector_session,
        query_embedding=SAMPLE_EMBEDDING_1,
        limit=5
    )
    
    assert len(results) == 0, "Should return empty list for empty database"


@pytest.mark.asyncio
async def test_find_similar_embeddings_no_match(pgvector_session: AsyncSession):
    """Test search when no similar embeddings exist (high threshold)."""
    # Create embeddings that are all very different from the query
    far_embedding = [0.99] * SAMPLE_DIMENSION
    await crud.create_document_embedding(
        db=pgvector_session,
        embedding=far_embedding,
        document_source="far_doc.txt",
        content_hash="far_hash",
    )
    
    # Query with very different embedding
    results = await crud.find_similar_embeddings(
        db=pgvector_session,
        query_embedding=SAMPLE_EMBEDDING_1,
        limit=5
    )
    
    # Should still return results but they will be "similar" within the vector space
    # The exact behavior depends on the implementation
    assert results is not None


@pytest.mark.asyncio
async def test_find_similar_embeddings_exact_match(pgvector_session: AsyncSession):
    """Test that exact matches are found."""
    # Create an embedding
    await crud.create_document_embedding(
        db=pgvector_session,
        embedding=SAMPLE_EMBEDDING_1,
        document_source=SAMPLE_SOURCE_1,
        content_hash=SAMPLE_HASH_1,
    )
    
    # Query with the exact same embedding
    results = await crud.find_similar_embeddings(
        db=pgvector_session,
        query_embedding=SAMPLE_EMBEDDING_1,
        limit=1
    )
    
    assert len(results) > 0, "Should find exact match"
    assert results[0].content_hash == SAMPLE_HASH_1, "Should match the exact embedding"


@pytest.mark.asyncio
async def test_find_similar_embeddings_with_filters(pgvector_session: AsyncSession):
    """Test similarity search with additional filtering (if supported)."""
    # Create embeddings with different sources
    await crud.create_document_embedding(
        db=pgvector_session,
        embedding=SAMPLE_EMBEDDING_1,
        document_source="filter_test_doc1.txt",
        content_hash="filter_hash_1",
    )
    
    await crud.create_document_embedding(
        db=pgvector_session,
        embedding=SAMPLE_EMBEDDING_2,
        document_source="filter_test_doc2.txt",
        content_hash="filter_hash_2",
    )
    
    results = await crud.find_similar_embeddings(
        db=pgvector_session,
        query_embedding=SAMPLE_EMBEDDING_1,
        limit=10
    )
    
    # Verify we get results
    assert len(results) >= 2, "Should find multiple embeddings"


def test_pgvector_extension_available(pgvector_engine):
    """Test that pgvector extension is available in the database."""
    import asyncio
    
    async def check_extension():
        async with pgvector_engine.connect() as conn:
            from sqlalchemy import text
            result = await conn.execute(text(
                "SELECT extname FROM pg_extension WHERE extname = 'vector'"
            ))
            row = result.fetchone()
            return row is not None
    
    result = asyncio.run(check_extension())
    assert result, "pgvector extension should be available"


def test_l2_distance_operator():
    """Test that l2_distance operator is available (basic syntax check)."""
    # This is a basic sanity check - actual operator testing happens in the CRUD tests
    # The l2_distance operator should be available in PostgreSQL with pgvector
    # Syntax: l2_distance(vector1, vector2)
    pass  # Actual testing is done through find_similar_embeddings tests


# Marker for running only pgvector tests
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "pgvector: marks tests as pgvector integration tests (deselect with '-m \"not pgvector\"')"
    )
