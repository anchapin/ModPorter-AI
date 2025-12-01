from src.db.base import async_engine
from src.db.declarative_base import Base
import logging
import asyncio
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError, OperationalError

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Initialize database with retry logic for extensions and tables."""

    max_retries = 5
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            async with async_engine.begin() as conn:
                # First, ensure required extensions are installed
                if conn.dialect.name == "postgresql":
                    logger.info("Creating database extensions...")
                    await conn.execute(
                        text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
                    )
                    await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "vector"'))

                # Now create all tables
                logger.info("Creating database tables...")
                await conn.run_sync(Base.metadata.create_all)

                logger.info("Database initialization completed successfully")
                return

        except (ProgrammingError, OperationalError) as e:
            if attempt < max_retries - 1:
                logger.warning(
                    f"Database initialization attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {retry_delay} seconds..."
                )
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(
                    f"Database initialization failed after {max_retries} attempts: {e}"
                )
                raise
        except Exception as e:
            logger.error(f"Unexpected error during database initialization: {e}")
            raise

    raise Exception("Failed to initialize database after all retry attempts")
