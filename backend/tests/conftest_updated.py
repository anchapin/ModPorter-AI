"""
Updated pytest configuration and fixtures for backend tests.

This file provides a comprehensive test setup with proper mock initialization,
database fixtures, and test clients for API testing.
"""

import os
import sys
import pytest
import asyncio
from pathlib import Path
from typing import AsyncGenerator, Generator, Dict, Any
from unittest.mock import MagicMock

# Add parent directories to path for imports
backend_dir = Path(__file__).parent.parent
src_dir = backend_dir / "src"
project_root = backend_dir.parent

sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(project_root))

# Apply all mocks before importing any modules
from tests.mocks import setup_test_environment

# Set up the test environment with all mocks
setup_test_environment()

# Now we can safely import from the application
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

# Import application modules after mocks are applied
from db.declarative_base import Base

# Configure test database
os.environ["TEST_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

# Create async engine for tests
test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
    pool_pre_ping=True,
    poolclass=StaticPool,
    connect_args={
        "check_same_thread": False,
    },
)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine, expire_on_commit=False, class_=AsyncSession
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def project_root_dir() -> Path:
    """Get the project root directory for accessing test fixtures."""
    return project_root


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh database session for each test function.

    This fixture:
    1. Creates all tables
    2. Yields a session
    3. Rolls back any changes after the test
    """
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create and yield a session
    async with TestAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            # Rollback any changes and close the session
            await session.rollback()
            await session.close()


@pytest.fixture
def client(db_session: AsyncSession) -> Generator[TestClient, None, None]:
    """
    Create a test client for FastAPI app with test database.

    This fixture:
    1. Overrides the database dependency to use our test session
    2. Creates a TestClient
    3. Cleans up dependency overrides after the test
    """
    # Import app and database dependencies
    from main import app
    from db.base import get_db

    # Override database dependency to use our test session
    def override_get_db():
        return db_session

    # Override dependency
    app.dependency_overrides[get_db] = override_get_db

    # Create TestClient
    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async test client for FastAPI app with test database.

    This fixture:
    1. Creates a fresh FastAPI app instance
    2. Overrides the database dependency
    3. Creates an AsyncClient
    4. Cleans up dependency overrides after the test
    """
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from db.base import get_db
    from httpx import ASGITransport
    import datetime
    from pydantic import BaseModel

    # Create fresh FastAPI app
    app = FastAPI(title="ModPorter AI Backend Test")

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins="http://localhost:3000",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Import and include all API routers
    from api import (
        performance,
        behavioral_testing,
        validation,
        comparison,
        embeddings,
        feedback,
        experiments,
        behavior_files,
        behavior_templates,
        behavior_export,
        advanced_events,
        knowledge_graph_fixed as knowledge_graph,
        expert_knowledge,
        peer_review,
        conversion_inference_fixed as conversion_inference,
        version_compatibility_fixed as version_compatibility,
    )

    # Include API routers
    app.include_router(
        performance.router, prefix="/api/v1/performance", tags=["performance"]
    )
    app.include_router(
        behavioral_testing.router, prefix="/api/v1", tags=["behavioral-testing"]
    )
    app.include_router(
        validation.router, prefix="/api/v1/validation", tags=["validation"]
    )
    app.include_router(
        comparison.router, prefix="/api/v1/comparison", tags=["comparison"]
    )
    app.include_router(
        embeddings.router, prefix="/api/v1/embeddings", tags=["embeddings"]
    )
    app.include_router(feedback.router, prefix="/api/v1", tags=["feedback"])
    app.include_router(
        experiments.router, prefix="/api/v1/experiments", tags=["experiments"]
    )
    app.include_router(behavior_files.router, prefix="/api/v1", tags=["behavior-files"])
    app.include_router(
        behavior_templates.router, prefix="/api/v1", tags=["behavior-templates"]
    )
    app.include_router(
        behavior_export.router, prefix="/api/v1", tags=["behavior-export"]
    )
    app.include_router(
        advanced_events.router, prefix="/api/v1", tags=["advanced-events"]
    )
    app.include_router(
        knowledge_graph.router,
        prefix="/api/v1/knowledge-graph",
        tags=["knowledge-graph"],
    )
    app.include_router(
        expert_knowledge.router,
        prefix="/api/v1/expert-knowledge",
        tags=["expert-knowledge"],
    )
    app.include_router(
        peer_review.router, prefix="/api/v1/peer-review", tags=["peer-review"]
    )
    app.include_router(
        conversion_inference.router,
        prefix="/api/v1/conversion-inference",
        tags=["conversion-inference"],
    )
    app.include_router(
        version_compatibility.router,
        prefix="/api/v1/version-compatibility",
        tags=["version-compatibility"],
    )

    # Add main health endpoint
    class HealthResponse(BaseModel):
        """Health check response model"""

        status: str
        version: str
        timestamp: str

    @app.get("/api/v1/health", response_model=HealthResponse, tags=["health"])
    async def health_check():
        """Check the health status of the API"""
        return HealthResponse(
            status="healthy",
            version="1.0.0",
            timestamp=datetime.datetime.utcnow().isoformat(),
        )

    # Override database dependency to use our test session
    def override_get_db():
        return db_session

    # Override dependency
    app.dependency_overrides[get_db] = override_get_db

    # Create AsyncClient using httpx
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as test_client:
            yield test_client
    finally:
        # Clean up dependency override
        app.dependency_overrides.clear()


@pytest.fixture
def mock_redis():
    """Create a mock Redis client for testing."""
    from tests.mocks.redis_mock import create_mock_redis_client

    return create_mock_redis_client()


@pytest.fixture
def mock_llm():
    """Create a mock LLM client for testing."""
    return MagicMock()


@pytest.fixture
def sample_conversion_job_data() -> Dict[str, Any]:
    """Sample data for a conversion job."""
    return {
        "id": "test-job-123",
        "status": "pending",
        "mod_file": "test_mod.jar",
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_addon_data() -> Dict[str, Any]:
    """Sample data for a converted addon."""
    return {
        "id": "test-addon-123",
        "name": "Test Addon",
        "version": "1.0.0",
        "description": "A test addon",
        "created_at": "2023-01-01T00:00:00Z",
    }


@pytest.fixture
def temp_dir(tmp_path) -> Path:
    """Create a temporary directory for file operations."""
    return tmp_path


@pytest.fixture
def sample_java_file(temp_dir) -> Path:
    """Create a sample Java file for testing."""
    java_file = temp_dir / "TestMod.java"
    java_file.write_text("""
    package com.example.test;

    import net.minecraft.block.Block;
    import net.minecraft.block.material.Material;
    import net.minecraft.item.Item;
    import net.minecraft.item.ItemBlock;
    import net.minecraft.creativetab.CreativeTabs;

    public class TestMod {
        public static final Block TEST_BLOCK = new TestBlock(Material.ROCK);

        public static void init() {
            // Initialize mod
        }

        public static class TestBlock extends Block {
            public TestBlock(Material material) {
                super(material);
                setUnlocalizedName("testBlock");
                setRegistryName("test_block");
                setCreativeTab(CreativeTabs.BUILDING_BLOCKS);
            }
        }

        public static class TestItem extends Item {
            public TestItem() {
                setUnlocalizedName("testItem");
                setRegistryName("test_item");
                setCreativeTab(CreativeTabs.MATERIALS);
            }
        }
    }
    """)
    return java_file


# Add custom pytest marks
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


# Global database setup (run once per session)
@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    """Set up the test database once at the beginning of the test session."""
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Clean up after all tests
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
