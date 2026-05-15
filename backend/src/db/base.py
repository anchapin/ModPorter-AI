from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from config import settings

# Base is imported in models.py and migrations
# from .declarative_base import Base

# Primary database engine (writes)
database_url = settings.database_url
if database_url.startswith("sqlite"):
    # SQLite configuration - no pool settings
    async_engine = create_async_engine(
        database_url,
        echo=False,
    )
else:
    # PostgreSQL configuration - with pool settings
    async_engine = create_async_engine(
        database_url,
        echo=False,
        pool_size=10,
        max_overflow=20,
    )

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, expire_on_commit=False, class_=AsyncSession
)

# Alias for backwards compatibility
async_session_factory = AsyncSessionLocal


# Read replica database engine (reads only - SELECT queries)
def _init_readonly_engine():
    """Initialize the readonly engine, falling back to primary if no replica configured."""
    global async_engine_readonly, AsyncSessionLocalReadonly
    readonly_url = settings.readonly_database_url
    if readonly_url and readonly_url != settings.database_url:
        if readonly_url.startswith("sqlite"):
            async_engine_readonly = create_async_engine(
                readonly_url,
                echo=False,
            )
        else:
            async_engine_readonly = create_async_engine(
                readonly_url,
                echo=False,
                pool_size=5,
                max_overflow=10,
            )
        AsyncSessionLocalReadonly = async_sessionmaker(
            bind=async_engine_readonly, expire_on_commit=False, class_=AsyncSession
        )
    else:
        # No replica configured - use primary for reads
        async_engine_readonly = async_engine
        AsyncSessionLocalReadonly = AsyncSessionLocal


# Initialize readonly engine at module load
_init_readonly_engine()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Primary database session - use for write operations."""
    async with AsyncSessionLocal() as session:
        yield session


async def get_readonly_db() -> AsyncGenerator[AsyncSession, None]:
    """Readonly database session - use for SELECT queries only.
    
    Routes SELECT queries to the read replica when configured,
    falling back to primary if replica is unavailable.
    """
    async with AsyncSessionLocalReadonly() as session:
        yield session