import json
import redis.asyncio as aioredis
from config import settings

class CacheService:
    def __init__(self) -> None:
        self._client = aioredis.from_url(settings.redis_url, decode_responses=True)

    async def set_job_status(self, job_id: str, status: dict) -> None:
        await self._client.set(f"conversion_jobs:{job_id}:status", json.dumps(status))

    async def get_job_status(self, job_id: str) -> dict | None:
        raw = await self._client.get(f"conversion_jobs:{job_id}:status")
        return json.loads(raw) if raw else None

    async def track_progress(self, job_id: str, progress: int) -> None:
        await self._client.set(f"conversion_jobs:{job_id}:progress", progress)