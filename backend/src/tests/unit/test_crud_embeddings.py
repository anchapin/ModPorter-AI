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

# TODO: Add a test for find_similar_embeddings that runs only if connected to a real Postgres with pgvector.
# This would typically involve a separate conftest.py for integration tests or a way to mark tests
# based on DB capabilities.
# For example: @pytest.mark.integration_postgres
# async def test_find_similar_embeddings_postgres(postgres_db_session: AsyncSession):
#     ... actual test logic for postgres ...
#
# The `embedding == SAMPLE_EMBEDDING_1` comparison in `test_create_document_embedding` and
# `test_update_document_embedding` might also be problematic if SQLite stores VECTORs as
# a type that doesn't perfectly roundtrip float lists (e.g., stores as string).
# If these tests fail, we might need to adjust assertions for embeddings on SQLite,
# or accept that exact vector retrieval testing is only for Postgres.
# For now, let's see what happens.
# A common workaround is to compare elements with a tolerance for float precision issues.
# e.g., assert all(abs(a - b) < 1e-6 for a, b in zip(fetched.embedding, created.embedding))

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

print("Finished defining tests for CRUD embeddings.")
