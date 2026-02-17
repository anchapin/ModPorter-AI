import json
import redis.asyncio as aioredis
from config import settings
from typing import Optional
from datetime import datetime
import logging
import base64
import os
from models.cache_models import CacheStats

logger = logging.getLogger(__name__)


class CacheService:
    CACHE_MOD_ANALYSIS_PREFIX = "cache:mod_analysis:"
    CACHE_CONVERSION_RESULT_PREFIX = "cache:conversion_result:"
    CACHE_ASSET_CONVERSION_PREFIX = "cache:asset_conversion:"
    
    # Default TTL configurations (in seconds)
    DEFAULT_TTL_MOD_ANALYSIS = int(os.getenv("CACHE_TTL_MOD_ANALYSIS", "3600"))  # 1 hour
    DEFAULT_TTL_CONVERSION_RESULT = int(os.getenv("CACHE_TTL_CONVERSION_RESULT", "7200"))  # 2 hours
    DEFAULT_TTL_ASSET_CONVERSION = int(os.getenv("CACHE_TTL_ASSET_CONVERSION", "3600"))  # 1 hour
    DEFAULT_TTL_JOB_STATUS = int(os.getenv("CACHE_TTL_JOB_STATUS", "300"))  # 5 minutes
    
    # Cache size limits
    MAX_CACHE_ITEMS = int(os.getenv("CACHE_MAX_ITEMS", "1000"))

    def __init__(self) -> None:
        # Check if Redis is disabled for tests
        self._redis_disabled = os.getenv("DISABLE_REDIS", "false").lower() == "true"

        if self._redis_disabled:
            self._client = None
            self._redis_available = False
            logger.info("Redis disabled for tests")
        else:
            try:
                self._client = aioredis.from_url(
                    settings.redis_url, decode_responses=True
                )
                self._redis_available = True
                logger.info("Redis cache initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis client: {e}")
                self._client = None
                self._redis_available = False

        self._cache_hits = 0
        self._cache_misses = 0

    def _json_encoder_default(self, obj):
        """
        Default encoder for json.dumps to handle non-serializable types.
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    async def set_job_status(self, job_id: str, status: dict) -> None:
        if not self._redis_available or self._redis_disabled:
            return
        try:
            await self._client.set(
                f"conversion_jobs:{job_id}:status",
                json.dumps(status, default=self._json_encoder_default),
            )
        except Exception as e:
            logger.warning(f"Redis operation failed for set_job_status: {e}")
            self._redis_available = False

    async def get_job_status(self, job_id: str) -> Optional[dict]:
        if not self._redis_available or self._redis_disabled:
            return None
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
        if not self._redis_available or self._redis_disabled:
            return
        try:
            await self._client.set(f"conversion_jobs:{job_id}:progress", progress)
            await self._client.sadd("conversion_jobs:active", job_id)
        except Exception as e:
            logger.warning(f"Redis operation failed for set_progress: {e}")
            self._redis_available = False

    async def cache_mod_analysis(
        self, mod_hash: str, analysis: dict, ttl_seconds: Optional[int] = 3600
    ) -> None:
        try:
            key = f"{self.CACHE_MOD_ANALYSIS_PREFIX}{mod_hash}"
            await self._client.set(
                key, json.dumps(analysis, default=self._json_encoder_default), ex=ttl_seconds
            )
        except Exception as e:
            logger.warning(f"Redis operation failed for cache_mod_analysis: {e}")

    async def get_mod_analysis(self, mod_hash: str) -> Optional[dict]:
        try:
            key = f"{self.CACHE_MOD_ANALYSIS_PREFIX}{mod_hash}"
            raw = await self._client.get(key)
            if raw:
                self._cache_hits += 1
                return json.loads(raw)
            self._cache_misses += 1
            return None
        except Exception as e:
            logger.warning(f"Redis operation failed for get_mod_analysis: {e}")
            self._cache_misses += 1
            return None

    async def cache_conversion_result(
        self, mod_hash: str, result: dict, ttl_seconds: Optional[int] = 3600
    ) -> None:
        try:
            key = f"{self.CACHE_CONVERSION_RESULT_PREFIX}{mod_hash}"
            await self._client.set(
                key, json.dumps(result, default=self._json_encoder_default), ex=ttl_seconds
            )
        except Exception as e:
            logger.warning(f"Redis operation failed for cache_conversion_result: {e}")

    async def get_conversion_result(self, mod_hash: str) -> Optional[dict]:
        try:
            key = f"{self.CACHE_CONVERSION_RESULT_PREFIX}{mod_hash}"
            raw = await self._client.get(key)
            if raw:
                self._cache_hits += 1
                return json.loads(raw)
            self._cache_misses += 1
            return None
        except Exception as e:
            logger.warning(f"Redis operation failed for get_conversion_result: {e}")
            self._cache_misses += 1
            return None

    async def cache_asset_conversion(
        self, asset_hash: str, converted_asset: bytes, ttl_seconds: Optional[int] = 3600
    ) -> None:
        try:
            key = f"{self.CACHE_ASSET_CONVERSION_PREFIX}{asset_hash}"
            encoded_asset = base64.b64encode(converted_asset).decode("utf-8")
            await self._client.set(key, encoded_asset, ex=ttl_seconds)
        except Exception as e:
            logger.warning(f"Redis operation failed for cache_asset_conversion: {e}")

    async def get_asset_conversion(self, asset_hash: str) -> Optional[bytes]:
        try:
            key = f"{self.CACHE_ASSET_CONVERSION_PREFIX}{asset_hash}"
            raw = await self._client.get(key)
            if raw:
                self._cache_hits += 1
                return base64.b64decode(raw.encode("utf-8"))
            self._cache_misses += 1
            return None
        except Exception as e:
            logger.warning(f"Redis operation failed for get_asset_conversion: {e}")
            self._cache_misses += 1
            return None

    async def invalidate_cache(self, cache_key: str) -> None:
        try:
            await self._client.delete(cache_key)
        except Exception as e:
            logger.warning(
                f"Redis operation failed for invalidate_cache for key {cache_key}: {e}"
            )

    async def get_cache_stats(self) -> CacheStats:
        try:
            mod_analysis_keys = await self._client.keys(
                f"{self.CACHE_MOD_ANALYSIS_PREFIX}*"
            )
            conversion_result_keys = await self._client.keys(
                f"{self.CACHE_CONVERSION_RESULT_PREFIX}*"
            )
            asset_conversion_keys = await self._client.keys(
                f"{self.CACHE_ASSET_CONVERSION_PREFIX}*"
            )

            current_items = (
                len(mod_analysis_keys)
                + len(conversion_result_keys)
                + len(asset_conversion_keys)
            )

            info = await self._client.info("memory")
            total_size_bytes = info.get("used_memory", 0)

            stats = CacheStats(
                hits=self._cache_hits,
                misses=self._cache_misses,
                current_items=current_items,
                total_size_bytes=total_size_bytes,
            )

        except Exception as e:
            logger.warning(f"Redis operation failed for get_cache_stats: {e}")
            stats = CacheStats(
                hits=self._cache_hits,
                misses=self._cache_misses,
                current_items=0,
                total_size_bytes=0,
            )
        return stats

    async def set_export_data(self, conversion_id: str, export_data: bytes, ttl_seconds: int = 3600) -> None:
        """
        Store exported behavior pack data in cache.
        """
        if not self._redis_available or self._redis_disabled:
            return
        try:
            # Store binary data as base64 string
            encoded_data = base64.b64encode(export_data).decode('utf-8')
            await self._client.setex(
                f"export:{conversion_id}:data",
                ttl_seconds,
                encoded_data
            )
        except Exception as e:
            logger.warning(f"Redis operation failed for set_export_data: {e}")
            self._redis_available = False

    async def get_export_data(self, conversion_id: str) -> Optional[bytes]:
        """
        Retrieve exported behavior pack data from cache.
        """
        if not self._redis_available or self._redis_disabled:
            return None
        try:
            encoded_data = await self._client.get(f"export:{conversion_id}:data")
            if encoded_data:
                return base64.b64decode(encoded_data.encode('utf-8'))
            return None
        except Exception as e:
            logger.warning(f"Redis operation failed for get_export_data: {e}")
            self._redis_available = False
            return None

    async def delete_export_data(self, conversion_id: str) -> None:
        """
        Delete exported behavior pack data from cache.
        """
        if not self._redis_available or self._redis_disabled:
            return
        try:
            await self._client.delete(f"export:{conversion_id}:data")
        except Exception as e:
            logger.warning(f"Redis operation failed for delete_export_data: {e}")
            self._redis_available = False

    # Enhanced caching methods for Issue #381
    
    async def cache_conversion_by_hash(
        self, mod_content: bytes, result: dict, ttl_seconds: Optional[int] = None
    ) -> str:
        """
        Cache conversion result by computing hash of mod content.
        
        Args:
            mod_content: The mod file content bytes
            result: The conversion result to cache
            ttl_seconds: Optional TTL, defaults to DEFAULT_TTL_CONVERSION_RESULT
            
        Returns:
            The hash key used for caching
        """
        import hashlib
        
        if ttl_seconds is None:
            ttl_seconds = self.DEFAULT_TTL_CONVERSION_RESULT
        
        # Compute SHA256 hash of mod content
        mod_hash = hashlib.sha256(mod_content).hexdigest()
        
        # Cache the result
        await self.cache_conversion_result(mod_hash, result, ttl_seconds)
        
        logger.info(f"Cached conversion result with hash: {mod_hash[:16]}...")
        return mod_hash

    async def get_cached_conversion_by_hash(self, mod_content: bytes) -> Optional[dict]:
        """
        Retrieve cached conversion result by computing hash of mod content.
        
        Args:
            mod_content: The mod file content bytes
            
        Returns:
            Cached conversion result or None if not found
        """
        import hashlib
        
        mod_hash = hashlib.sha256(mod_content).hexdigest()
        result = await self.get_conversion_result(mod_hash)
        
        if result:
            logger.info(f"Cache hit for conversion hash: {mod_hash[:16]}...")
        else:
            logger.info(f"Cache miss for conversion hash: {mod_hash[:16]}...")
            
        return result

    async def invalidate_conversion_cache(self, mod_hash: str) -> None:
        """
        Invalidate a specific conversion result cache.
        
        Args:
            mod_hash: The hash key of the conversion to invalidate
        """
        key = f"{self.CACHE_CONVERSION_RESULT_PREFIX}{mod_hash}"
        await self.invalidate_cache(key)
        logger.info(f"Invalidated conversion cache for hash: {mod_hash[:16]}...")

    async def invalidate_mod_analysis_cache(self, mod_hash: str) -> None:
        """
        Invalidate a specific mod analysis cache.
        
        Args:
            mod_hash: The hash key of the mod analysis to invalidate
        """
        key = f"{self.CACHE_MOD_ANALYSIS_PREFIX}{mod_hash}"
        await self.invalidate_cache(key)
        logger.info(f"Invalidated mod analysis cache for hash: {mod_hash[:16]}...")

    async def clear_all_caches(self) -> None:
        """
        Clear all cached data (use with caution).
        """
        if not self._redis_available or self._redis_disabled:
            return
        try:
            patterns = [
                f"{self.CACHE_MOD_ANALYSIS_PREFIX}*",
                f"{self.CACHE_CONVERSION_RESULT_PREFIX}*",
                f"{self.CACHE_ASSET_CONVERSION_PREFIX}*",
            ]
            for pattern in patterns:
                keys = await self._client.keys(pattern)
                if keys:
                    await self._client.delete(*keys)
            logger.warning("All caches cleared")
        except Exception as e:
            logger.error(f"Failed to clear caches: {e}")

    def get_cache_hit_rate(self) -> float:
        """
        Calculate cache hit rate.
        
        Returns:
            Hit rate as a percentage (0-100)
        """
        total = self._cache_hits + self._cache_misses
        if total == 0:
            return 0.0
        return (self._cache_hits / total) * 100

    # Progress tracking from AI Engine
    
    async def get_ai_engine_progress(self, job_id: str) -> Optional[dict]:
        """
        Get the latest progress update from AI Engine for a job.
        
        Args:
            job_id: The conversion job ID
            
        Returns:
            Progress data dict or None if not available
        """
        if not self._redis_available or self._redis_disabled:
            return None
        try:
            key = f"ai_engine:progress:{job_id}"
            raw = await self._client.get(key)
            return json.loads(raw) if raw else None
        except Exception as e:
            logger.warning(f"Redis operation failed for get_ai_engine_progress: {e}")
            return None

    async def subscribe_to_ai_engine_progress(self, job_id: str):
        """
        Subscribe to real-time progress updates from AI Engine.
        
        Args:
            job_id: The conversion job ID
            
        Returns:
            Redis pub/sub channel for progress updates
        """
        if not self._redis_available or self._redis_disabled:
            return None
        try:
            pubsub = self._client.pubsub()
            channel = f"ai_engine:progress:{job_id}"
            await pubsub.subscribe(channel)
            logger.info(f"Subscribed to AI Engine progress channel: {channel}")
            return pubsub
        except Exception as e:
            logger.warning(f"Failed to subscribe to AI Engine progress: {e}")
            return None
