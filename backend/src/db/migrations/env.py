from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import sys
import os

# Must modify sys.path before importing custom modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

# Now import custom modules
from config import settings  # noqa: E402
from src.db.declarative_base import Base  # noqa: E402

# Import models to ensure they are registered with the Base metadata
import src.db.models  # noqa: E402 F401

# this is the Alembic Config object, which provides access to the values within the .ini file in use.
config = context.config
fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    # Use sync database URL for migrations
    url = settings.sync_database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    # Use sync database URL for migrations
    database_url = settings.sync_database_url
    connectable = engine_from_config(
        {"sqlalchemy.url": database_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
