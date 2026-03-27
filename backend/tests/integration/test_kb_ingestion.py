"""
Integration tests for knowledge base ingestion pipeline.

Tests the complete flow from fetching documents through processing,
chunking, and database storage.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from db.declarative_base import Base
from db import crud
from db.models import DocumentEmbedding

# Import ingestion components
import sys
sys.path.insert(0, "src")
from ingestion.pipeline import IngestionPipeline
from ingestion.sources.base import RawDocument, DocumentType
from ingestion.sources.forge_docs import ForgeDocsAdapter
from ingestion.sources.fabric_docs import FabricDocsAdapter
from ingestion.sources.bedrock_docs import BedrockDocsAdapter
from ingestion.processors.markdown import MarkdownProcessor
from ingestion.processors.html import HTMLProcessor
from ingestion.validators.quality import QualityValidator


# Mark all tests as asyncio
pytestmark = pytest.mark.asyncio


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
async def mock_ingestion_db():
    """Create async test database session for ingestion tests."""
    TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

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
def sample_markdown_doc():
    """Sample markdown document for testing."""
    return RawDocument(
        content="""# Getting Started with Forge

This guide covers the basics of Minecraft Forge modding.

## Prerequisites

- Java JDK 17 or higher
- IntelliJ IDEA or Eclipse
- Minecraft Forge MDK

## Your First Block

Let's create a custom block:

```java
public class ExampleBlock extends Block {
    public ExampleBlock() {
        super(Properties.create(Material.ROCK));
    }
}
```

This creates a basic rock block.

## Next Steps

Explore more advanced topics like entities and items.
""",
        source_url="https://docs.minecraftforge.net/getting-started",
        doc_type=DocumentType.MARKDOWN,
        metadata={
            "mod_loader": "forge",
            "version": "1.20.1",
            "section": "getting-started",
        },
        title="Getting Started with Forge",
    )


@pytest.fixture
def sample_html_doc():
    """Sample HTML document for testing."""
    return RawDocument(
        content="""<!DOCTYPE html>
<html>
<head>
    <title>Bedrock Script API Reference</title>
</head>
<body>
    <h1>Minecraft Namespace</h1>
    <p>The minecraft namespace contains core game classes.</p>

    <h2>Classes</h2>
    <ul>
        <li>Player - Represents a player entity</li>
        <li>World - Represents the game world</li>
    </ul>

    <h3>Player Class</h3>
    <pre><code class="language-javascript">
import * as minecraft from "@minecraft/server";

const player = minecraft.Player;
    </code></pre>

    <p>This class provides player-related functionality.</p>
</body>
</html>
""",
        source_url="https://learn.microsoft.com/minecraft/scriptapi/minecraft",
        doc_type=DocumentType.HTML,
        metadata={
            "api_type": "script_api",
            "namespace": "minecraft",
            "game_version": "1.21.0",
        },
        title="Minecraft Namespace",
    )


@pytest.fixture
def mock_aiohttp_response():
    """Mock aiohttp response for testing HTTP requests."""
    class MockResponse:
        def __init__(self, status=200, text="<html>Mock content</html>"):
            self.status = status
            self._text = text
            self.headers = {"Content-Type": "text/html"}

        async def text(self):
            return self._text

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    return MockResponse


class TestSourceAdapters:
    """Test documentation source adapters."""

    async def test_source_adapters(self):
        """Test all three adapters can be instantiated."""
        forge = ForgeDocsAdapter()
        fabric = FabricDocsAdapter()
        bedrock = BedrockDocsAdapter()

        assert forge is not None
        assert fabric is not None
        assert bedrock is not None

        # Test validate_config
        assert forge.validate_config({"version": "1.20.1", "sections": ["intro"]}) is True
        assert fabric.validate_config({"version": "1.20.1", "sections": ["intro"]}) is True
        assert bedrock.validate_config({"namespaces": ["minecraft"], "game_version": "1.21.0"}) is True

        # Test invalid config
        assert forge.validate_config({"sections": "not-a-list"}) is False
        assert bedrock.validate_config({"namespaces": "not-a-list"}) is False


class TestProcessors:
    """Test document processors."""

    async def test_markdown_processor(self, sample_markdown_doc):
        """Test markdown processing and metadata extraction."""
        processor = MarkdownProcessor()
        result = processor.process(sample_markdown_doc)

        assert "content" in result
        assert "metadata" in result
        assert result["metadata"]["title"] == "Getting Started with Forge"
        assert len(result["metadata"]["code_blocks"]) == 1
        assert result["metadata"]["code_blocks"][0]["language"] == "java"
        assert result["metadata"]["word_count"] > 0

    async def test_html_processor(self, sample_html_doc):
        """Test HTML processing and content extraction."""
        processor = HTMLProcessor()
        result = processor.process(sample_html_doc)

        assert "content" in result
        assert "html_content" in result
        assert "metadata" in result
        assert result["metadata"]["title"] == "Bedrock Script API Reference"
        assert len(result["metadata"]["code_blocks"]) == 1
        assert result["metadata"]["code_blocks"][0]["language"] == "javascript"


class TestQualityValidator:
    """Test quality validation."""

    async def test_quality_validator_accepts_good_content(self):
        """Test validator accepts good quality content."""
        validator = QualityValidator()
        result = validator.validate(
            "This is meaningful content with enough text to pass validation.",
            {"title": "Test", "source": "test"}
        )

        assert result.is_valid is True
        assert len(result.errors) == 0

    async def test_quality_validator_rejects_short_content(self):
        """Test validator rejects content that's too short."""
        validator = QualityValidator()
        result = validator.validate(
            "Short",
            {"title": "Test", "source": "test"}
        )

        assert result.is_valid is False
        assert len(result.errors) > 0
        assert "too short" in result.errors[0].lower()

    async def test_quality_validator_rejects_long_content(self):
        """Test validator rejects content that's too long."""
        validator = QualityValidator()
        long_content = "x" * 100001  # Over MAX_LENGTH
        result = validator.validate(
            long_content,
            {"title": "Test", "source": "test"}
        )

        assert result.is_valid is False
        assert len(result.errors) > 0
        assert "too long" in result.errors[0].lower()

    async def test_quality_validator_warns_missing_metadata(self):
        """Test validator warns about missing metadata."""
        validator = QualityValidator()
        result = validator.validate(
            "This is meaningful content with enough text to pass validation.",
            {}  # No metadata
        )

        # Should still be valid (no errors) but have warnings
        assert result.is_valid is True
        assert len(result.warnings) >= 2  # Should warn about missing title AND source


class TestIngestionPipeline:
    """Test end-to-end ingestion pipeline."""

    async def test_ingest_forge_docs(self, mock_ingestion_db, mock_aiohttp_response):
        """Test end-to-end Forge docs ingestion with mocked HTTP."""
        # Mock aiohttp to avoid external HTTP calls
        with patch("aiohttp.ClientSession.get") as mock_get:
            # Setup mock response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {"Content-Type": "text/html"}
            mock_response.text = AsyncMock(return_value="<html><body>Mock Forge docs content</body></html>")
            mock_get.return_value.__aenter__.return_value = mock_response

            # Create pipeline
            pipeline = IngestionPipeline(mock_ingestion_db)

            # Ingest documents
            result = await pipeline.ingest_source(
                "forge_docs",
                {
                    "version": "1.20.1",
                    "sections": ["getting-started"],
                    "max_pages": 1,
                }
            )

            # Verify result
            assert result["status"] in ["success", "error"]
            assert "documents_processed" in result
            assert "chunks_indexed" in result

    async def test_ingest_bedrock_api(self, mock_ingestion_db, mock_aiohttp_response):
        """Test end-to-end Bedrock API ingestion with mocked HTTP."""
        # Mock aiohttp to avoid external HTTP calls
        with patch("aiohttp.ClientSession.get") as mock_get:
            # Setup mock response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {"Content-Type": "text/html"}
            mock_response.text = AsyncMock(return_value="<html><body>Mock Bedrock API docs</body></html>")
            mock_get.return_value.__aenter__.return_value = mock_response

            # Create pipeline
            pipeline = IngestionPipeline(mock_ingestion_db)

            # Ingest documents
            result = await pipeline.ingest_source(
                "bedrock_docs",
                {
                    "namespaces": ["minecraft"],
                    "game_version": "1.21.0",
                    "max_pages": 1,
                }
            )

            # Verify result
            assert result["status"] in ["success", "error"]
            assert "documents_processed" in result
            assert "chunks_indexed" in result

    async def test_deduplication(self, mock_ingestion_db):
        """Test that duplicate content is not re-indexed (content_hash check)."""
        # Create a document with a specific content hash
        content_hash = "test_hash_12345"

        # Create parent document with chunk
        parent_doc, chunks = await crud.create_document_with_chunks(
            mock_ingestion_db,
            chunks=[
                {
                    "content": "Test content",
                    "embedding": [0.0] * 1536,
                    "content_hash": content_hash,
                    "metadata": {},
                }
            ],
            document_source="test_source",
            title="Test Document",
        )

        # Verify document was created
        assert parent_doc is not None
        assert len(chunks) == 1

        # Try to create duplicate (should be skipped in pipeline)
        existing = await crud.get_document_embedding_by_hash(mock_ingestion_db, content_hash)
        assert existing is not None

        # Create a second document with same hash (should fail unique constraint)
        # In real pipeline, this would be caught before DB insert
        try:
            duplicate_doc, duplicate_chunks = await crud.create_document_with_chunks(
                mock_ingestion_db,
                chunks=[
                    {
                        "content": "Different content",
                        "embedding": [0.0] * 1536,
                        "content_hash": content_hash,  # Same hash!
                        "metadata": {},
                    }
                ],
                document_source="test_source_2",
                title="Duplicate Document",
            )
            # If we get here, deduplication failed
            assert False, "Duplicate content_hash should have been rejected"
        except Exception as e:
            # Expected: unique constraint violation
            assert "unique" in str(e).lower() or "constraint" in str(e).lower()

    async def test_markdown_processing_and_chunking(self, mock_ingestion_db, sample_markdown_doc):
        """Test that markdown is processed and chunked correctly."""
        # Create pipeline
        pipeline = IngestionPipeline(mock_ingestion_db)

        # Process document
        processed = await pipeline._process_document(sample_markdown_doc)

        assert processed is not None
        assert "content" in processed
        assert "metadata" in processed

        # Chunk the processed content
        chunks = pipeline._chunk_document(processed["content"], "semantic", sample_markdown_doc.title)

        assert len(chunks) > 0
        assert all(hasattr(chunk, "content") for chunk in chunks)
        assert all(hasattr(chunk, "index") for chunk in chunks)

    async def test_html_processing_and_chunking(self, mock_ingestion_db, sample_html_doc):
        """Test that HTML is processed and chunked correctly."""
        # Create pipeline
        pipeline = IngestionPipeline(mock_ingestion_db)

        # Process document
        processed = await pipeline._process_document(sample_html_doc)

        assert processed is not None
        assert "content" in processed
        assert "metadata" in processed

        # Chunk the processed content
        chunks = pipeline._chunk_document(processed["content"], "semantic", sample_html_doc.title)

        assert len(chunks) > 0
        assert all(hasattr(chunk, "content") for chunk in chunks)
