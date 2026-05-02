from db.base import async_engine
from db.declarative_base import Base
import logging
import asyncio
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError, OperationalError

logger = logging.getLogger(__name__)


async def run_byok_migration(conn) -> None:
    """Run BYOK-specific migrations (Issue #1227)"""
    logger.info("Running BYOK migration...")

    # Add BYOK columns if they don't exist
    try:
        # Check if columns exist
        result = await conn.execute(
            text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'llm_api_key_encrypted'
        """)
        )
        exists = result.fetchone() is not None

        if not exists:
            logger.info("Adding BYOK columns to users table...")
            await conn.execute(
                text("""
                ALTER TABLE users
                ADD COLUMN llm_api_key_encrypted BYTEA,
                ADD COLUMN llm_api_key_provider VARCHAR(20),
                ADD COLUMN byok_enabled BOOLEAN NOT NULL DEFAULT FALSE
            """)
            )
            logger.info("BYOK columns added successfully")
        else:
            logger.info("BYOK columns already exist, skipping migration")
    except Exception as e:
        logger.warning(f"BYOK migration warning (may be safe to ignore): {e}")


async def init_db() -> None:
    """Initialize database with retry logic for extensions and tables."""

    max_retries = 5
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            async with async_engine.begin() as conn:
                # First, ensure required extensions are installed
                logger.info("Creating database extensions...")
                await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
                await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "vector"'))

                # Now create all tables
                logger.info("Creating database tables...")
                await conn.run_sync(Base.metadata.create_all)

                # Run BYOK migrations
                await run_byok_migration(conn)

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
                logger.error(f"Database initialization failed after {max_retries} attempts: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error during database initialization: {e}")
            raise

    raise Exception("Failed to initialize database after all retry attempts")
