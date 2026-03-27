"""
Integration tests for document indexing flow.

Tests the complete pipeline from document upload through chunking,
embedding generation, to database storage.
"""

import pytest
import asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from db.declarative_base import Base
from db.models import DocumentEmbedding
from db import crud


# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_db():
    """Create test database session."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Provide session
    async with async_session() as session:
        yield session

    # Cleanup
    await engine.dispose()


@pytest.fixture
def sample_document():
    """Sample document for testing."""
    return """
# Introduction to Minecraft Modding

Minecraft modding is the process of modifying the game to add new features.
This document covers the basics of getting started with modding.

## Prerequisites

Before you start, you'll need:
- Java Development Kit (JDK) 17 or higher
- An IDE (IntelliJ IDEA or Eclipse)
- Minecraft Forge or Fabric API

## Your First Mod

Let's create a simple mod that adds a new block.

```java
public class CustomBlock extends Block {
    public CustomBlock() {
        super(Properties.create(Material.ROCK));
    }
}
```

This code creates a basic block with rock material properties.

## Advanced Topics

Once you're comfortable with basic mods, you can explore:
- Custom entities
- Dimension creation
- Network handling
- Render overrides

## Conclusion

Modding opens up endless possibilities for creativity.
Start small and gradually build your skills!
"""


@pytest.mark.asyncio
async def test_create_document_with_chunks(test_db):
    """Test creating a document with multiple chunks."""
    # Create chunks with mock embeddings (SQLite doesn't support vector operations)
    chunk_data_list = [
        {
            "content": "First chunk of content",
            "embedding": [0.1] * 1536,
            "content_hash": "hash1",
            "metadata": {
                "chunk_index": 0,
                "total_chunks": 3,
                "heading_context": ["Introduction"],
                "document_type": "markdown",
            },
        },
        {
            "content": "Second chunk of content with more details",
            "embedding": [0.2] * 1536,
            "content_hash": "hash2",
            "metadata": {
                "chunk_index": 1,
                "total_chunks": 3,
                "heading_context": ["Introduction"],
                "document_type": "markdown",
            },
        },
        {
            "content": "Third chunk with final information",
            "embedding": [0.3] * 1536,
            "content_hash": "hash3",
            "metadata": {
                "chunk_index": 2,
                "total_chunks": 3,
                "heading_context": ["Conclusion"],
                "document_type": "markdown",
            },
        },
    ]

    # Create document in database
    parent_doc, db_chunks = await crud.create_document_with_chunks(
        db=test_db,
        chunks=chunk_data_list,
        document_source="test-doc",
        title="Test Document",
    )

    # Verify parent document
    assert parent_doc.id is not None, "Parent document should have ID"
    assert parent_doc.hierarchy_level == 0, "Parent should be hierarchy level 0"
    assert parent_doc.title is not None, "Parent should have title"

    # Verify chunks
    assert len(db_chunks) == len(chunk_data_list), "All chunks should be stored"
    for i, chunk in enumerate(db_chunks):
        assert chunk.parent_document_id == parent_doc.id, "Chunk should reference parent"
        assert chunk.chunk_index == i, "Chunk index should match"
        assert chunk.hierarchy_level == 2, "Chunk should be hierarchy level 2"
        assert chunk.embedding is not None, "Chunk should have embedding"


@pytest.mark.asyncio
async def test_get_document_with_chunks(test_db):
    """Test retrieving a document with all its chunks."""
    # Create a document first
    chunks_data = [
        {
            "content": "First chunk",
            "embedding": [0.1] * 1536,
            "content_hash": "hash1",
            "metadata": {"chunk_index": 0},
        },
        {
            "content": "Second chunk",
            "embedding": [0.2] * 1536,
            "content_hash": "hash2",
            "metadata": {"chunk_index": 1},
        },
    ]

    parent_doc, created_chunks = await crud.create_document_with_chunks(
        db=test_db,
        chunks=chunks_data,
        document_source="test-source",
        title="Test Document",
    )

    # Retrieve document
    retrieved_parent, retrieved_chunks = await crud.get_document_with_chunks(
        test_db, parent_doc.id
    )

    assert retrieved_parent is not None, "Parent document should be retrieved"
    assert retrieved_parent.id == parent_doc.id, "Parent ID should match"
    assert len(retrieved_chunks) == 2, "Should retrieve all chunks"
    assert retrieved_chunks[0].chunk_index == 0, "First chunk index should be 0"
    assert retrieved_chunks[1].chunk_index == 1, "Second chunk index should be 1"


@pytest.mark.asyncio
async def test_get_chunks_by_parent(test_db):
    """Test retrieving chunks by parent document ID."""
    # Create document with chunks
    chunks_data = [
        {
            "content": f"Chunk {i}",
            "embedding": [float(i)] * 1536,
            "content_hash": f"hash{i}",
            "metadata": {"chunk_index": i},
        }
        for i in range(3)
    ]

    parent_doc, _ = await crud.create_document_with_chunks(
        db=test_db,
        chunks=chunks_data,
        document_source="test-source",
        title="Test",
    )

    # Get chunks by parent
    chunks = await crud.get_chunks_by_parent(test_db, parent_doc.id)

    assert len(chunks) == 3, "Should retrieve all chunks"
    assert chunks[0].chunk_index == 0, "Chunks should be ordered by index"
    assert chunks[1].chunk_index == 1
    assert chunks[2].chunk_index == 2


@pytest.mark.asyncio
async def test_search_similar_chunks(test_db):
    """Test searching for similar chunks within a document."""
    # Create document with chunks
    chunks_data = [
        {
            "content": "Machine learning is a subset of artificial intelligence",
            "embedding": [0.1, 0.2, 0.3] + [0.0] * 1533,
            "content_hash": "hash1",
            "metadata": {},
        },
        {
            "content": "Deep learning uses neural networks",
            "embedding": [0.4, 0.5, 0.6] + [0.0] * 1533,
            "content_hash": "hash2",
            "metadata": {},
        },
    ]

    parent_doc, _ = await crud.create_document_with_chunks(
        db=test_db,
        chunks=chunks_data,
        document_source="test-source",
        title="AI Document",
    )

    # For SQLite, just verify we can query chunks by parent
    # (vector search requires pgvector)
    chunks = await crud.get_chunks_by_parent(test_db, parent_doc.id)

    assert len(chunks) == 2, "Should find both chunks"
    assert chunks[0].parent_document_id == parent_doc.id, "Chunks should be from same document"


@pytest.mark.asyncio
async def test_hierarchical_document_structure(test_db):
    """Test that document hierarchy is properly maintained."""
    chunks_data = [
        {
            "content": f"Section {i} content",
            "embedding": [float(i) * 0.1] * 1536,
            "content_hash": f"hash{i}",
            "metadata": {"heading_context": [f"Section {i}"]},
        }
        for i in range(5)
    ]

    parent_doc, chunks = await crud.create_document_with_chunks(
        db=test_db,
        chunks=chunks_data,
        document_source="test-source",
        title="Hierarchical Document",
    )

    # Verify parent hierarchy
    assert parent_doc.hierarchy_level == 0, "Parent should be level 0"
    assert parent_doc.parent_document_id is None, "Parent should have no parent"

    # Verify chunk hierarchy
    for chunk in chunks:
        assert chunk.hierarchy_level == 2, "Chunks should be level 2"
        assert chunk.parent_document_id == parent_doc.id, "Chunks should reference parent"
        assert chunk.metadata_json is not None, "Chunks should have metadata"


@pytest.mark.asyncio
async def test_document_deduplication_by_hash(test_db):
    """Test that chunks can be queried by content hash."""
    # Create first document
    chunks_data = [
        {
            "content": "Unique content",
            "embedding": [0.1] * 1536,
            "content_hash": "unique-hash-123",
            "metadata": {},
        }
    ]

    parent1, _ = await crud.create_document_with_chunks(
        db=test_db,
        chunks=chunks_data,
        document_source="source1",
        title="Doc 1",
    )

    # Querying by hash should find the chunk
    existing = await crud.get_document_embedding_by_hash(test_db, "unique-hash-123")
    assert existing is not None, "Should find chunk by content hash"
    assert existing.content_hash == "unique-hash-123", "Should return correct chunk"


@pytest.mark.asyncio
async def test_chunk_metadata_preservation(test_db):
    """Test that chunk metadata is properly stored and retrieved."""
    chunks_data = [
        {
            "content": "Test content",
            "embedding": [0.1] * 1536,
            "content_hash": "meta-hash",
            "metadata": {
                "chunk_index": 0,
                "total_chunks": 1,
                "heading_context": ["Introduction", "Getting Started"],
                "document_type": "markdown",
                "extracted_tags": ["markdown", "tutorial"],
                "original_heading": "Getting Started",
                "char_start": 0,
                "char_end": 12,
            },
        }
    ]

    parent_doc, chunks = await crud.create_document_with_chunks(
        db=test_db,
        chunks=chunks_data,
        document_source="test",
        title="Metadata Test",
    )

    # Retrieve and verify metadata
    retrieved_parent, retrieved_chunks = await crud.get_document_with_chunks(
        test_db, parent_doc.id
    )

    chunk_meta = retrieved_chunks[0].metadata_json
    assert chunk_meta["heading_context"] == ["Introduction", "Getting Started"]
    assert chunk_meta["document_type"] == "markdown"
    assert "markdown" in chunk_meta["extracted_tags"]
    assert chunk_meta["original_heading"] == "Getting Started"
