"""
Test fixtures for knowledge base ingestion tests.

Provides sample documents and mock HTTP responses for testing.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from ingestion.sources.base import RawDocument, DocumentType


@pytest.fixture
async def mock_ingestion_db():
    """
    Create async test database session for ingestion tests.

    Uses in-memory SQLite for isolation.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
    from sqlalchemy.pool import StaticPool
    from db.declarative_base import Base

    TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

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
    """
    Mock aiohttp response for testing HTTP requests.

    Returns a mock that simulates successful HTTP responses.
    """

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
