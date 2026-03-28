"""
Pipeline Cache - Caching layer for RAG pipeline results.

This module provides caching capabilities to improve RAG pipeline performance
by caching results for repeated queries.
"""

import logging
import hashlib
from typing import Optional, Dict, Any, Protocol
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import OrderedDict
import threading

logger = logging.getLogger(__name__)


@dataclass
class CachedResult:
    """Cached result from pipeline execution."""

    results: Any
    query_analysis: Any
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ttl: int = 3600


class CacheBackend(Protocol):
    """Protocol for cache backends."""

    def get(self, key: str) -> Optional[CachedResult]: ...

    def set(self, key: str, result: CachedResult) -> None: ...

    def invalidate(self, pattern: str = None) -> None: ...


class MemoryCache:
    """In-memory LRU cache implementation."""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: OrderedDict = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

        logger.info(f"MemoryCache initialized (max_size={max_size}, ttl={ttl}s)")

    def get(self, key: str) -> Optional[CachedResult]:
        """Get cached result."""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            cached = self._cache[key]

            if self._is_expired(cached):
                del self._cache[key]
                self._misses += 1
                return None

            self._cache.move_to_end(key)
            self._hits += 1
            return cached

    def set(self, key: str, result: CachedResult) -> None:
        """Set cached result."""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)

            self._cache[key] = result

            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

    def invalidate(self, pattern: str = None) -> None:
        """Invalidate cache entries."""
        with self._lock:
            if pattern is None:
                self._cache.clear()
            else:
                keys_to_remove = [k for k in self._cache.keys() if pattern in k]
                for key in keys_to_remove:
                    del self._cache[key]

    def _is_expired(self, cached: CachedResult) -> bool:
        """Check if cached result is expired."""
        age = (datetime.now(timezone.utc) - cached.timestamp).total_seconds()
        return age > self.ttl

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0.0

            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl": self.ttl,
            }


class RedisCache:
    """Redis-backed cache implementation."""

    def __init__(self, redis_client=None, ttl: int = 3600, prefix: str = "rag:"):
        self.redis_client = redis_client
        self.ttl = ttl
        self.prefix = prefix

        if redis_client is None:
            logger.warning("Redis client not available, falling back to memory cache")
            self._fallback = MemoryCache(ttl=ttl)
        else:
            self._fallback = None

        logger.info(f"RedisCache initialized (ttl={ttl}s, prefix={prefix})")

    def get(self, key: str) -> Optional[CachedResult]:
        """Get cached result from Redis."""
        if self._fallback:
            return self._fallback.get(key)

        try:
            import json

            full_key = f"{self.prefix}{key}"
            data = self.redis_client.get(full_key)

            if not data:
                return None

            cached_data = json.loads(data)
            return CachedResult(
                results=cached_data["results"],
                query_analysis=cached_data["query_analysis"],
                timestamp=datetime.fromisoformat(cached_data["timestamp"]),
                ttl=cached_data["ttl"],
            )
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
            return None

    def set(self, key: str, result: CachedResult) -> None:
        """Set cached result in Redis."""
        if self._fallback:
            self._fallback.set(key, result)
            return

        try:
            import json

            full_key = f"{self.prefix}{key}"
            data = {
                "results": result.results,
                "query_analysis": result.query_analysis,
                "timestamp": result.timestamp.isoformat(),
                "ttl": result.ttl,
            }

            self.redis_client.setex(full_key, self.ttl, json.dumps(data))
        except Exception as e:
            logger.warning(f"Redis set failed: {e}")

    def invalidate(self, pattern: str = None) -> None:
        """Invalidate cache entries in Redis."""
        if self._fallback:
            self._fallback.invalidate(pattern)
            return

        try:
            full_pattern = f"{self.prefix}{pattern or '*'}"
            keys = self.redis_client.keys(full_pattern)

            if keys:
                self.redis_client.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis invalidate failed: {e}")


class PipelineCache:
    """
    Pipeline cache with pluggable backends.

    Provides caching for RAG pipeline results with support for
    both in-memory and Redis backends.
    """

    def __init__(self, backend: str = "memory", ttl: int = 3600, **kwargs):
        self.ttl = ttl

        if backend == "memory":
            max_size = kwargs.get("max_size", 1000)
            self._backend = MemoryCache(max_size=max_size, ttl=ttl)
        elif backend == "redis":
            redis_client = kwargs.get("redis_client")
            self._backend = RedisCache(redis_client=redis_client, ttl=ttl)
        else:
            logger.warning(f"Unknown backend '{backend}', using memory")
            self._backend = MemoryCache(ttl=ttl)

        logger.info(f"PipelineCache initialized with {backend} backend")

    def get(self, key: str) -> Optional[CachedResult]:
        """Get cached result."""
        return self._backend.get(key)

    def set(self, key: str, result: Any) -> None:
        """Set cached result."""
        cached = CachedResult(
            results=result.results, query_analysis=result.query_analysis, ttl=self.ttl
        )
        self._backend.set(key, cached)

    def invalidate(self, pattern: str = None) -> None:
        """Invalidate cache entries."""
        self._backend.invalidate(pattern)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if hasattr(self._backend, "get_stats"):
            return self._backend.get_stats()

        return {"backend": type(self._backend).__name__, "ttl": self.ttl}
