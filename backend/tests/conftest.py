import os
import sys
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Add src directory to Python path
backend_dir = Path(__file__).parent.parent
src_dir = backend_dir / "src"
sys.path.insert(0, str(src_dir))

from config import settings

# Set testing environment variable BEFORE importing main
os.environ["TESTING"] = "true"
os.environ["TEST_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

# Set up async engine for tests
test_engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600
)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine, expire_on_commit=False, class_=AsyncSession
)

# Global flag to track database initialization
_db_initialized = False

def pytest_sessionstart(session):
    """Initialize database once at the start of the test session."""
    global _db_initialized
    print("pytest_sessionstart called")
    if not _db_initialized:
        print("Initializing test database...")
        try:
            # Run database initialization synchronously
            import asyncio

            async def init_test_db():
                from db.declarative_base import Base
                # from db import models  # Import all models to ensure they're registered
                # # Import models.py file directly to ensure all models are registered
                # import db.models
                from sqlalchemy import text
                print(f"Database URL: {test_engine.url}")
                print("Available models:")
                for table_name in Base.metadata.tables.keys():
                    print(f"  - {table_name}")

                async with test_engine.begin() as conn:
                    print("Connection established")
                    # Check if we're using SQLite
                    if "sqlite" in str(test_engine.url).lower():
                        print("Using SQLite - skipping extensions")
                        # SQLite doesn't support extensions, so we skip them
                        await conn.run_sync(Base.metadata.create_all)
                        print("Tables created successfully")

                        # Verify tables were created
                        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                        tables = [row[0] for row in result.fetchall()]
                        print(f"Created tables: {tables}")
                    else:
                        print("Using PostgreSQL - creating extensions")
                        # PostgreSQL specific extensions
                        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"pgcrypto\""))
                        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"vector\""))
                        await conn.run_sync(Base.metadata.create_all)
                        print("Extensions and tables created successfully")

            # Create a new event loop for this operation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(init_test_db())
                _db_initialized = True
                print("Test database initialized successfully")
            finally:
                loop.close()
        except Exception as e:
            print(f"⚠️ Warning: Database initialization failed: {e}")
            import traceback
            traceback.print_exc()
            _db_initialized = False

@pytest.fixture
def project_root():
    """Get project root directory for accessing test fixtures."""
    # Navigate from backend/src/tests/conftest.py to project root
    current_dir = Path(__file__).parent  # tests/
    src_dir = current_dir.parent         # src/
    backend_dir = src_dir.parent         # backend/
    project_root = backend_dir.parent    # project root
    return project_root

@pytest.fixture(scope="function")
async def db_session():
    """Create a database session for each test with transaction rollback."""
    # Ensure models are imported
    # from db import models
    # Ensure tables are created
    from db.declarative_base import Base
    async with test_engine.begin() as conn:
        # Check if we're using SQLite
        if "sqlite" in str(test_engine.url).lower():
            # SQLite doesn't support extensions, so we skip them
            await conn.run_sync(Base.metadata.create_all)
        else:
            # PostgreSQL specific extensions
            from sqlalchemy import text
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"pgcrypto\""))
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"vector\""))
            await conn.run_sync(Base.metadata.create_all)

    async with test_engine.begin() as connection:
        session = AsyncSession(bind=connection, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()

@pytest.fixture
def client():
    """Create a test client for FastAPI app with proper test database."""
    # Set testing environment variable
    os.environ["TESTING"] = "true"

    # Import app and database dependencies
    from main import app
    from db.base import get_db

    # Override database dependency to use our test engine
    test_session_maker = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        class_=AsyncSession
    )

    def override_get_db():
        # Create a new session for each request
        session = test_session_maker()
        try:
            yield session
        finally:
            session.close()

    # Ensure tables are created
    import asyncio
    from db.declarative_base import Base
    # from db import models

    async def ensure_tables():
        async with test_engine.begin() as conn:
            if "sqlite" in str(test_engine.url).lower():
                await conn.run_sync(Base.metadata.create_all)
            else:
                from sqlalchemy import text
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"pgcrypto\""))
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"vector\""))
                await conn.run_sync(Base.metadata.create_all)

    # Run table creation synchronously
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(ensure_tables())
    finally:
        loop.close()

    # Override dependency
    app.dependency_overrides[get_db] = override_get_db

    # Create TestClient
    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
async def async_client():
    """Create an async test client for FastAPI app."""
    # Import modules to create fresh app instance
    import asyncio
    import sys
    from pathlib import Path
    
    # Add src to path (needed for CI environment)
    backend_dir = Path(__file__).parent.parent
    src_dir = backend_dir / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    
    from fastapi import FastAPI
    from db.base import get_db
    from api import performance, behavioral_testing, validation, comparison, embeddings, feedback, experiments, behavior_files, behavior_templates, behavior_export, advanced_events
    from api import knowledge_graph_fixed as knowledge_graph, expert_knowledge, peer_review_fixed as peer_review, conversion_inference_fixed as conversion_inference, version_compatibility_fixed as version_compatibility
    from sqlalchemy.ext.asyncio import AsyncSession
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi import FastAPI
    import os
    from dotenv import load_dotenv
    from datetime import datetime
    
    # Load environment variables
    load_dotenv()
    
    # Create fresh FastAPI app
    app = FastAPI(title="ModPorter AI Backend Test")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routers
    app.include_router(performance.router, prefix="/api/v1/performance", tags=["performance"])
    app.include_router(behavioral_testing.router, prefix="/api/v1", tags=["behavioral-testing"])
    app.include_router(validation.router, prefix="/api/v1/validation", tags=["validation"])
    app.include_router(comparison.router, prefix="/api/v1/comparison", tags=["comparison"])
    app.include_router(embeddings.router, prefix="/api/v1/embeddings", tags=["embeddings"])
    app.include_router(feedback.router, prefix="/api/v1", tags=["feedback"])
    app.include_router(experiments.router, prefix="/api/v1/experiments", tags=["experiments"])
    app.include_router(behavior_files.router, prefix="/api/v1", tags=["behavior-files"])
    app.include_router(behavior_templates.router, prefix="/api/v1", tags=["behavior-templates"])
    app.include_router(behavior_export.router, prefix="/api/v1", tags=["behavior-export"])
    app.include_router(advanced_events.router, prefix="/api/v1", tags=["advanced-events"])
    app.include_router(knowledge_graph.router, prefix="/api/v1/knowledge-graph", tags=["knowledge-graph"])
    app.include_router(expert_knowledge.router, prefix="/api/v1/expert-knowledge", tags=["expert-knowledge"])
    app.include_router(peer_review.router, prefix="/api/v1/peer-review", tags=["peer-review"])
    app.include_router(conversion_inference.router, prefix="/api/v1/conversion-inference", tags=["conversion-inference"])
    app.include_router(version_compatibility.router, prefix="/api/v1/version-compatibility", tags=["version-compatibility"])
    
    # Add main health endpoint
    from pydantic import BaseModel
    
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
            timestamp=datetime.utcnow().isoformat()
        )
    
    # Override database dependency to use our test engine
    test_session_maker = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        class_=AsyncSession
    )

    def override_get_db():
        # Create a new session for each request
        session = test_session_maker()
        try:
            yield session
        finally:
            session.close()

    # Ensure tables are created
    from db.declarative_base import Base
    # from db import models

    async def ensure_tables():
        async with test_engine.begin() as conn:
            if "sqlite" in str(test_engine.url).lower():
                await conn.run_sync(Base.metadata.create_all)
            else:
                from sqlalchemy import text
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"pgcrypto\""))
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"vector\""))
                await conn.run_sync(Base.metadata.create_all)

    await ensure_tables()

    # Override dependency
    app.dependency_overrides[get_db] = override_get_db

    # Create AsyncClient using httpx
    import httpx
    try:
        # Debug: print available routes
        print(f"DEBUG: Available routes in test client setup: {len(app.routes)} total routes")
        print(f"DEBUG: Sample routes: {[route.path for route in app.routes[:10]]}")
        print(f"DEBUG: Conversion inference routes: {[route.path for route in app.routes if '/conversion-inference' in route.path]}")
        print(f"DEBUG: Expert knowledge routes: {[route.path for route in app.routes if '/expert' in route.path]}")
        print(f"DEBUG: Peer review routes: {[route.path for route in app.routes if '/peer-review' in route.path]}")
        print(f"DEBUG: Knowledge graph routes: {[route.path for route in app.routes if '/knowledge-graph' in route.path]}")
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as test_client:
            yield test_client
    finally:
        # Clean up dependency override
        app.dependency_overrides.clear()

@pytest.fixture(scope="function")
async def async_test_db():
    """Create an async database session for tests."""
    async with TestAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
