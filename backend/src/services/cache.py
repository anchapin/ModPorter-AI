import json
import redis.asyncio as aioredis
from src.config import settings
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self) -> None:
        self._client = aioredis.from_url(settings.redis_url, decode_responses=True)
        self._redis_available = True

    def _make_json_serializable(self, obj):
        """
        Recursively convert non-serializable types (e.g., datetime) to JSON-serializable formats.
        """
        if isinstance(obj, dict):
            return {key: self._make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj

    async def set_job_status(self, job_id: str, status: dict) -> None:
        try:
            await self._client.set(f"conversion_jobs:{job_id}:status", json.dumps(self._make_json_serializable(status)))
        except Exception as e:
            logger.warning(f"Redis operation failed for set_job_status: {e}")
            self._redis_available = False

    async def get_job_status(self, job_id: str) -> Optional[dict]:
        try:
            raw = await self._client.get(f"conversion_jobs:{job_id}:status")
            return json.loads(raw) if raw else None
        except Exception as e:
            logger.warning(f"Redis operation failed for get_job_status: {e}")
            self._redis_available = False
            return None

    async def track_progress(self, job_id: str, progress: int) -> None:
        try:
            await self._client.set(f"conversion_jobs:{job_id}:progress", progress)
        except Exception as e:
            logger.warning(f"Redis operation failed for track_progress: {e}")
            self._redis_available = False

    async def set_progress(self, job_id: str, progress: int) -> None:
        """
        Set the progress for a job and add job_id to the active set.
        """
        try:
            await self._client.set(f"conversion_jobs:{job_id}:progress", progress)
            await self._client.sadd("conversion_jobs:active", job_id)
        except Exception as e:
            logger.warning(f"Redis operation failed for set_progress: {e}")
            self._redis_available = False