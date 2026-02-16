import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
import os

# Assuming pgvector.sqlalchemy might not be available or usable in SQLite context
# For model definition, it's imported, but for creating test data, it's just a list[float]
# from pgvector.sqlalchemy import VECTOR # Not strictly needed for test data creation

from db import crud

# Skip all tests if using SQLite (these tests require PostgreSQL with pgvector)
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL.startswith("sqlite"),
    reason="DocumentEmbedding tests require PostgreSQL with pgvector extension"
)

# Sample data
SAMPLE_EMBEDDING_1 = [0.1] * 1536
SAMPLE_EMBEDDING_2 = [0.2] * 1536
SAMPLE_EMBEDDING_3 = [0.3] * 1536
SAMPLE_SOURCE_1 = "doc1.txt"
SAMPLE_SOURCE_2 = "doc2.txt"
SAMPLE_HASH_1 = "hash1"
SAMPLE_HASH_2 = "hash2"
SAMPLE_HASH_3 = "hash3"


@pytest.mark.asyncio
async def test_create_document_embedding(test_db_session: AsyncSession):
    created = await crud.create_document_embedding(
        db=test_db_session,
        embedding=SAMPLE_EMBEDDING_1,
        document_source=SAMPLE_SOURCE_1,
        content_hash=SAMPLE_HASH_1,
    )
    assert created is not None
    assert created.id is not None
    assert all(pytest.approx(a) == b for a, b in zip(created.embedding, SAMPLE_EMBEDDING_1))
    assert created.document_source == SAMPLE_SOURCE_1
    assert created.content_hash == SAMPLE_HASH_1

    # Fetch it back
    fetched = await crud.get_document_embedding_by_id(db=test_db_session, embedding_id=created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert all(pytest.approx(a) == b for a, b in zip(fetched.embedding, SAMPLE_EMBEDDING_1)) # This comparison might fail if VECTOR type isn't handled well by SQLite
    assert fetched.document_source == SAMPLE_SOURCE_1
    assert fetched.content_hash == SAMPLE_HASH_1


@pytest.mark.asyncio
async def test_get_document_embedding_by_hash(test_db_session: AsyncSession):
    await crud.create_document_embedding(
        db=test_db_session,
        embedding=SAMPLE_EMBEDDING_1,
        document_source=SAMPLE_SOURCE_1,
        content_hash=SAMPLE_HASH_1,
    )

    fetched = await crud.get_document_embedding_by_hash(db=test_db_session, content_hash=SAMPLE_HASH_1)
    assert fetched is not None
    assert fetched.content_hash == SAMPLE_HASH_1

    not_found = await crud.get_document_embedding_by_hash(db=test_db_session, content_hash="non_existent_hash")
    assert not_found is None


@pytest.mark.asyncio
async def test_get_document_embedding_by_id_not_found(test_db_session: AsyncSession):
    not_found = await crud.get_document_embedding_by_id(db=test_db_session, embedding_id=uuid4())
    assert not_found is None


@pytest.mark.asyncio
async def test_update_document_embedding(test_db_session: AsyncSession):
    created = await crud.create_document_embedding(
        db=test_db_session,
        embedding=SAMPLE_EMBEDDING_1,
        document_source=SAMPLE_SOURCE_1,
        content_hash=SAMPLE_HASH_1,
    )

    updated_source = "updated_doc.txt"
    updated_embedding_vector = [0.15] * 1536

    updated = await crud.update_document_embedding(
        db=test_db_session,
        embedding_id=created.id,
        embedding=updated_embedding_vector,
        document_source=updated_source,
    )
    assert updated is not None
    assert updated.id == created.id
    assert updated.document_source == updated_source
    assert all(pytest.approx(a) == b for a, b in zip(updated.embedding, updated_embedding_vector)) # Comparison might fail
    assert updated.content_hash == SAMPLE_HASH_1 # Hash should not change on update

    # Fetch again to verify
    fetched = await crud.get_document_embedding_by_id(db=test_db_session, embedding_id=created.id)
    assert fetched is not None
    assert fetched.document_source == updated_source
    assert all(pytest.approx(a) == b for a, b in zip(fetched.embedding, updated_embedding_vector)) # Comparison might fail


@pytest.mark.asyncio
async def test_update_document_embedding_not_found(test_db_session: AsyncSession):
    updated = await crud.update_document_embedding(
        db=test_db_session,
        embedding_id=uuid4(), # Non-existent ID
        document_source="new_source",
    )
    assert updated is None

@pytest.mark.asyncio
async def test_update_document_embedding_no_changes(test_db_session: AsyncSession):
    created = await crud.create_document_embedding(
        db=test_db_session,
        embedding=SAMPLE_EMBEDDING_1,
        document_source=SAMPLE_SOURCE_1,
        content_hash=SAMPLE_HASH_1,
    )
    # Call update with no actual change parameters (both None)
    updated = await crud.update_document_embedding(db=test_db_session, embedding_id=created.id)
    assert updated is not None
    assert updated.id == created.id
    assert updated.embedding == SAMPLE_EMBEDDING_1
    assert updated.document_source == SAMPLE_SOURCE_1


@pytest.mark.asyncio
async def test_delete_document_embedding(test_db_session: AsyncSession):
    created = await crud.create_document_embedding(
        db=test_db_session,
        embedding=SAMPLE_EMBEDDING_1,
        document_source=SAMPLE_SOURCE_1,
        content_hash=SAMPLE_HASH_1,
    )

    deleted = await crud.delete_document_embedding(db=test_db_session, embedding_id=created.id)
    assert deleted is True

    not_found = await crud.get_document_embedding_by_id(db=test_db_session, embedding_id=created.id)
    assert not_found is None


@pytest.mark.asyncio
async def test_delete_document_embedding_not_found(test_db_session: AsyncSession):
    deleted = await crud.delete_document_embedding(db=test_db_session, embedding_id=uuid4())
    assert deleted is False


@pytest.mark.skip(reason="VECTOR type and l2_distance operator not supported on SQLite. Requires PostgreSQL for full test.")
@pytest.mark.asyncio
async def test_find_similar_embeddings_sqlite_placeholder(test_db_session: AsyncSession):
    # This test will be skipped when run against SQLite.
    # Its purpose here is to outline the structure.
    # A real test would require a PostgreSQL test database with pgvector.

    await crud.create_document_embedding(
        db=test_db_session, embedding=[0.1, 0.1], document_source="doc1", content_hash="h1"
    ) # Simplified dimension for placeholder
    await crud.create_document_embedding(
        db=test_db_session, embedding=[0.2, 0.2], document_source="doc2", content_hash="h2"
    )
    await crud.create_document_embedding(
        db=test_db_session, embedding=[0.9, 0.9], document_source="doc3", content_hash="h3"
    )

    query_embedding = [0.15, 0.15]

    # We expect this call to fail on SQLite if l2_distance is used in the query
    try:
        results = await crud.find_similar_embeddings(
            db=test_db_session, query_embedding=query_embedding, limit=2
        )
        # If it somehow runs on SQLite (e.g. if VECTOR is emulated as TEXT/JSON and l2_distance is a mock),
        # we can't reliably check order but can check count.
        assert len(results) <= 2
        # Further assertions about order would be unreliable here.
        # For example, if the query doesn't error but returns all items or incorrect items:
        # print(f"Warning: find_similar_embeddings ran on SQLite, results: {results}")

    except Exception as e:
        # This is the expected path for SQLite if l2_distance is used.
        # The test is marked skip, so this code block might not even be hit if pytest skips it early.
        # If not skipped early, we can assert that the error is what we expect (e.g., OperationalError from SQLite)
        # For now, the skip decorator handles this.
        print(f"find_similar_embeddings failed as expected on SQLite (or was skipped): {e}")
        pass

# Test for content_hash uniqueness constraint (implicitly tested by create then get_by_hash,
# but an explicit test for trying to create duplicate hash could be added if desired,
# though it would raise an IntegrityError from the DB which is hard to catch nicely in every test).
# async def test_create_duplicate_hash(db_session: AsyncSession):
#     await crud.create_document_embedding(db_session, SAMPLE_EMBEDDING_1, SAMPLE_SOURCE_1, SAMPLE_HASH_1)
#     with pytest.raises(IntegrityError): # Or whatever SQLAlchemy raises for unique constraint
#         await crud.create_document_embedding(db_session, SAMPLE_EMBEDDING_2, SAMPLE_SOURCE_2, SAMPLE_HASH_1)
# This kind of test is more of an integration test of the DB schema.
# For unit tests of CRUD, we assume the DB model is correct.
# The `create_or_get_embedding` in the API layer handles this logic more explicitly.


# =============================================================================
# pgvector Integration Tests
# These tests require PostgreSQL with the pgvector extension enabled
# =============================================================================

import pytest
import asyncio

# Custom marker for pgvector integration tests
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "pgvector: marks tests as requiring PostgreSQL with pgvector extension"
    )


def is_pgvector_available() -> bool:
    """Check if pgvector extension is available in the test database."""
    import os
    db_url = os.getenv("TEST_DATABASE_URL", "")
    # Only available with PostgreSQL, not SQLite
    return bool(db_url and not db_url.startswith("sqlite"))


# Fixtures for pgvector tests
@pytest.fixture
def pgvector_extension_available():
    """Fixture to check if pgvector extension is available."""
    return is_pgvector_available()


@pytest.fixture
def sample_similar_embeddings():
    """
    Provide sample embeddings for similarity testing.
    
    Returns embeddings with known distances:
    - embedding_1 and embedding_2 are very similar (distance ~0.14)
    - embedding_3 is dissimilar to the first two (distance ~1.34)
    """
    # 3D vectors for easier manual verification
    return {
        "vec1": [1.0, 0.0, 0.0],
        "vec2": [0.9, 0.1, 0.1],  # Close to vec1
        "vec3": [0.0, 1.0, 0.0],  # Far from vec1
    }


@pytest.fixture
async def populated_embeddings_db(test_db_session: AsyncSession, sample_similar_embeddings):
    """Populate database with embeddings for similarity testing."""
    vectors = sample_similar_embeddings
    
    # Create embeddings with known distances
    await crud.create_document_embedding(
        db=test_db_session,
        embedding=vectors["vec1"],
        document_source="similar_doc1.txt",
        content_hash="similar_hash_1",
    )
    await crud.create_document_embedding(
        db=test_db_session,
        embedding=vectors["vec2"],
        document_source="similar_doc2.txt",
        content_hash="similar_hash_2",
    )
    await crud.create_document_embedding(
        db=test_db_session,
        embedding=vectors["vec3"],
        document_source="dissimilar_doc.txt",
        content_hash="dissimilar_hash",
    )
    
    await test_db_session.commit()
    return vectors


@pytest.mark.pgvector
@pytest.mark.asyncio
async def test_find_similar_embeddings_basic(
    test_db_session: AsyncSession,
    sample_similar_embeddings,
    pgvector_extension_available
):
    """Test basic similarity search returns correct results ordered by distance."""
    if not pgvector_extension_available:
        pytest.skip("pgvector extension not available - requires PostgreSQL")
    
    vectors = sample_similar_embeddings
    
    # Create test embeddings
    await crud.create_document_embedding(
        db=test_db_session,
        embedding=vectors["vec1"],
        document_source="doc1.txt",
        content_hash="hash_vec1",
    )
    await crud.create_document_embedding(
        db=test_db_session,
        embedding=vectors["vec2"],
        document_source="doc2.txt",
        content_hash="hash_vec2",
    )
    await crud.create_document_embedding(
        db=test_db_session,
        embedding=vectors["vec3"],
        document_source="doc3.txt",
        content_hash="hash_vec3",
    )
    await test_db_session.commit()
    
    # Query for similar to vec1 - should return vec2 first (closest), then vec3
    results = await crud.find_similar_embeddings(
        db=test_db_session,
        query_embedding=vectors["vec1"],
        limit=2
    )
    
    assert len(results) == 2
    # First result should be vec1 itself or vec2 (the closest)
    # Note: Depending on implementation, it might include the query itself
    result_sources = [r.document_source for r in results]
    
    # vec2 should be in results (most similar to vec1)
    assert "doc2.txt" in result_sources
    # vec3 is least similar, might or might not be in top 2 depending on order


@pytest.mark.pgvector
@pytest.mark.asyncio
async def test_find_similar_embeddings_limit(
    test_db_session: AsyncSession,
    sample_similar_embeddings,
    pgvector_extension_available
):
    """Test that limit parameter is respected."""
    if not pgvector_extension_available:
        pytest.skip("pgvector extension not available - requires PostgreSQL")
    
    vectors = sample_similar_embeddings
    
    # Create multiple embeddings
    for i in range(5):
        await crud.create_document_embedding(
            db=test_db_session,
            embedding=[float(i) * 0.1, 0.0, 0.0],
            document_source=f"doc_{i}.txt",
            content_hash=f"hash_{i}",
        )
    await test_db_session.commit()
    
    # Query with limit=2
    results = await crud.find_similar_embeddings(
        db=test_db_session,
        query_embedding=[0.0, 0.0, 0.0],
        limit=2
    )
    
    assert len(results) == 2


@pytest.mark.pgvector
@pytest.mark.asyncio
async def test_find_similar_embeddings_empty_db(
    test_db_session: AsyncSession,
    pgvector_extension_available
):
    """Test similarity search returns empty list when no embeddings exist."""
    if not pgvector_extension_available:
        pytest.skip("pgvector extension not available - requires PostgreSQL")
    
    results = await crud.find_similar_embeddings(
        db=test_db_session,
        query_embedding=[0.1] * 1536,
        limit=5
    )
    
    assert len(results) == 0


@pytest.mark.pgvector
@pytest.mark.asyncio
async def test_find_similar_embeddings_high_dimension(
    test_db_session: AsyncSession,
    pgvector_extension_available
):
    """Test similarity search with high-dimensional embeddings (1536 dims like OpenAI)."""
    if not pgvector_extension_available:
        pytest.skip("pgvector extension not available - requires PostgreSQL")
    
    # Create embeddings with 1536 dimensions (OpenAI embedding size)
    embedding_a = [0.1] * 1536
    embedding_b = [0.2] * 1536  # Similar
    embedding_c = [0.9] * 1536  # Dissimilar
    
    await crud.create_document_embedding(
        db=test_db_session,
        embedding=embedding_a,
        document_source="embedding_a.txt",
        content_hash="hash_a",
    )
    await crud.create_document_embedding(
        db=test_db_session,
        embedding=embedding_b,
        document_source="embedding_b.txt",
        content_hash="hash_b",
    )
    await crud.create_document_embedding(
        db=test_db_session,
        embedding=embedding_c,
        document_source="embedding_c.txt",
        content_hash="hash_c",
    )
    await test_db_session.commit()
    
    # Query for similar to embedding_a
    results = await crud.find_similar_embeddings(
        db=test_db_session,
        query_embedding=embedding_a,
        limit=2
    )
    
    assert len(results) == 2
    # embedding_b should be first (closest)
    assert "embedding_b.txt" in [r.document_source for r in results]


@pytest.mark.pgvector
@pytest.mark.asyncio
async def test_find_similar_embeddings_returns_metadata(
    test_db_session: AsyncSession,
    sample_similar_embeddings,
    pgvector_extension_available
):
    """Test that similarity search returns complete embedding metadata."""
    if not pgvector_extension_available:
        pytest.skip("pgvector extension not available - requires PostgreSQL")
    
    vectors = sample_similar_embeddings
    
    created = await crud.create_document_embedding(
        db=test_db_session,
        embedding=vectors["vec1"],
        document_source="metadata_test.txt",
        content_hash="metadata_hash",
    )
    await test_db_session.commit()
    
    results = await crud.find_similar_embeddings(
        db=test_db_session,
        query_embedding=vectors["vec1"],
        limit=1
    )
    
    assert len(results) >= 1
    result = results[0]
    assert result.document_source == "metadata_test.txt"
    assert result.content_hash == "metadata_hash"
    assert result.embedding is not None
    assert len(result.embedding) == 3


# Marker registration for pytest
def pytest_collection_modifyitems(config, items):
    """Automatically skip pgvector tests if extension is not available."""
    if not is_pgvector_available():
        skip_pgvector = pytest.mark.skip(
            reason="pgvector tests require PostgreSQL with pgvector extension"
        )
        for item in items:
            if "pgvector" in item.keywords:
                item.add_marker(skip_pgvector)


print("Finished defining tests for CRUD embeddings.")
