import json
import redis.asyncio as aioredis
from src.config import settings
from typing import Optional

class CacheService:
    def __init__(self) -> None:
        self._client = aioredis.from_url(settings.redis_url, decode_responses=True)

    async def set_job_status(self, job_id: str, status: dict) -> None:
        await self._client.set(f"conversion_jobs:{job_id}:status", json.dumps(status))

    async def get_job_status(self, job_id: str) -> Optional[dict]:
        raw = await self._client.get(f"conversion_jobs:{job_id}:status")
        return json.loads(raw) if raw else None

    async def track_progress(self, job_id: str, progress: int) -> None:
        await self._client.set(f"conversion_jobs:{job_id}:progress", progress)

    async def set_progress(self, job_id: str, progress: int) -> None:
        """
        Set the progress for a job and add job_id to the active set.
        """
        await self._client.set(f"conversion_jobs:{job_id}:progress", progress)
        await self._client.sadd("conversion_jobs:active", job_id)