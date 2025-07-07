import json
import redis.asyncio as aioredis
from src.config import settings
from typing import Optional
from datetime import datetime
import logging
import base64
from src.models.cache_models import CacheStats

logger = logging.getLogger(__name__)

class CacheService:
    CACHE_MOD_ANALYSIS_PREFIX = "cache:mod_analysis:"
    CACHE_CONVERSION_RESULT_PREFIX = "cache:conversion_result:"
    CACHE_ASSET_CONVERSION_PREFIX = "cache:asset_conversion:"

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

    async def cache_mod_analysis(self, mod_hash: str, analysis: dict, ttl_seconds: Optional[int] = 3600) -> None:
        try:
            key = f"{self.CACHE_MOD_ANALYSIS_PREFIX}{mod_hash}"
            await self._client.set(key, json.dumps(self._make_json_serializable(analysis)), ex=ttl_seconds)
        except Exception as e:
            logger.warning(f"Redis operation failed for cache_mod_analysis: {e}")

    async def get_mod_analysis(self, mod_hash: str) -> Optional[dict]:
        try:
            key = f"{self.CACHE_MOD_ANALYSIS_PREFIX}{mod_hash}"
            raw = await self._client.get(key)
            if raw:
                return json.loads(raw)
            return None
        except Exception as e:
            logger.warning(f"Redis operation failed for get_mod_analysis: {e}")
            return None

    async def cache_conversion_result(self, mod_hash: str, result: dict, ttl_seconds: Optional[int] = 3600) -> None:
        try:
            key = f"{self.CACHE_CONVERSION_RESULT_PREFIX}{mod_hash}"
            await self._client.set(key, json.dumps(self._make_json_serializable(result)), ex=ttl_seconds)
        except Exception as e:
            logger.warning(f"Redis operation failed for cache_conversion_result: {e}")

    async def get_conversion_result(self, mod_hash: str) -> Optional[dict]:
        try:
            key = f"{self.CACHE_CONVERSION_RESULT_PREFIX}{mod_hash}"
            raw = await self._client.get(key)
            if raw:
                return json.loads(raw)
            return None
        except Exception as e:
            logger.warning(f"Redis operation failed for get_conversion_result: {e}")
            return None

    async def cache_asset_conversion(self, asset_hash: str, converted_asset: bytes, ttl_seconds: Optional[int] = 3600) -> None:
        try:
            key = f"{self.CACHE_ASSET_CONVERSION_PREFIX}{asset_hash}"
            encoded_asset = base64.b64encode(converted_asset).decode('utf-8')
            await self._client.set(key, encoded_asset, ex=ttl_seconds)
        except Exception as e:
            logger.warning(f"Redis operation failed for cache_asset_conversion: {e}")

    async def get_asset_conversion(self, asset_hash: str) -> Optional[bytes]:
        try:
            key = f"{self.CACHE_ASSET_CONVERSION_PREFIX}{asset_hash}"
            raw = await self._client.get(key)
            if raw:
                return base64.b64decode(raw.encode('utf-8'))
            return None
        except Exception as e:
            logger.warning(f"Redis operation failed for get_asset_conversion: {e}")
            return None

    async def invalidate_cache(self, cache_key: str) -> None:
        try:
            await self._client.delete(cache_key)
        except Exception as e:
            logger.warning(f"Redis operation failed for invalidate_cache for key {cache_key}: {e}")

    async def get_cache_stats(self) -> CacheStats:
        stats = CacheStats()
        try:
            mod_analysis_keys = await self._client.keys(f"{self.CACHE_MOD_ANALYSIS_PREFIX}*")
            conversion_result_keys = await self._client.keys(f"{self.CACHE_CONVERSION_RESULT_PREFIX}*")
            asset_conversion_keys = await self._client.keys(f"{self.CACHE_ASSET_CONVERSION_PREFIX}*")

            stats.current_items = len(mod_analysis_keys) + len(conversion_result_keys) + len(asset_conversion_keys)

            info = await self._client.info('memory')
            stats.total_size_bytes = info.get('used_memory', 0)

        except Exception as e:
            logger.warning(f"Redis operation failed for get_cache_stats: {e}")
        return stats