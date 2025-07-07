from src.db.base import async_engine
from src.db.declarative_base import Base

async def init_db() -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)