"""
Redis configuration and client management for ModPorter-AI.

This module provides:
- Connection pooling for Redis
- Queue patterns for job processing
- Rate limiting utilities
- Caching layer with serialization
"""

import json
import os
from typing import Optional, Any, List
import logging
from datetime import datetime, timedelta

import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from config import settings

logger = logging.getLogger(__name__)


class RedisConfig:
    """Redis connection configuration"""

    def __init__(self):
        self.url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.max_connections: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "20"))
        self.socket_timeout: int = int(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))
        self.socket_connect_timeout: int = int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "5"))
        self.socket_keepalive: bool = os.getenv("REDIS_SOCKET_KEEPALIVE", "true").lower() == "true"
        self.retry_on_timeout: bool = os.getenv("REDIS_RETRY_ON_TIMEOUT", "true").lower() == "true"
        self.health_check_interval: int = int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL", "30"))
        self.decode_responses: bool = True


class RedisClient:
    """
    Async Redis client with connection pooling and error handling.

    Usage:
        client = RedisClient()
        await client.connect()
        await client.set("key", "value")
        value = await client.get("key")
        await client.disconnect()
    """

    def __init__(self, config: Optional[RedisConfig] = None):
        self.config = config or RedisConfig()
        self._pool: Optional[aioredis.ConnectionPool] = None
        self._client: Optional[Redis] = None
        self._connected = False

    async def connect(self) -> bool:
        """Establish connection to Redis"""
        if self._connected and self._client:
            return True

        try:
            self._pool = aioredis.ConnectionPool.from_url(
                self.config.url,
                max_connections=self.config.max_connections,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                socket_keepalive=self.config.socket_keepalive,
                retry_on_timeout=self.config.retry_on_timeout,
                decode_responses=self.config.decode_responses,
                health_check_interval=self.config.health_check_interval,
            )
            self._client = Redis(connection_pool=self._pool)

            # Test connection
            await self._client.ping()
            self._connected = True
            logger.info(f"Redis connected successfully: {self.config.url}")
            return True

        except RedisConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connected = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to Redis: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Close Redis connection"""
        if self._client:
            await self._client.close()
        if self._pool:
            await self._pool.disconnect()
        self._connected = False
        logger.info("Redis disconnected")

    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        return self._connected and self._client is not None

    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        if not self.is_connected:
            logger.warning("Redis not connected, cannot get value")
            return None
        try:
            return await self._client.get(key)
        except RedisError as e:
            logger.error(f"Redis get error: {e}")
            return None

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None, json_encode: bool = True
    ) -> bool:
        """Set key-value pair with optional TTL"""
        if not self.is_connected:
            logger.warning("Redis not connected, cannot set value")
            return False
        try:
            if json_encode and not isinstance(value, str):
                value = json.dumps(value, default=str)
            return await self._client.set(key, value, ex=ttl)
        except RedisError as e:
            logger.error(f"Redis set error: {e}")
            return False

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys"""
        if not self.is_connected:
            return 0
        try:
            return await self._client.delete(*keys)
        except RedisError as e:
            logger.error(f"Redis delete error: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.is_connected:
            return False
        try:
            return await self._client.exists(key) > 0
        except RedisError as e:
            logger.error(f"Redis exists error: {e}")
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for key"""
        if not self.is_connected:
            return False
        try:
            return await self._client.expire(key, ttl)
        except RedisError as e:
            logger.error(f"Redis expire error: {e}")
            return False


class JobQueue:
    """
    Redis-based job queue for background processing.

    Usage:
        queue = JobQueue(queue_name="conversions")
        await queue.enqueue({"job_id": "123", "type": "convert"})
        job = await queue.dequeue()
    """

    def __init__(self, queue_name: str = "default"):
        self.queue_name = f"queue:{queue_name}"
        self.processing_set = f"queue:{queue_name}:processing"
        self.client = RedisClient()

    async def connect(self) -> bool:
        """Connect to Redis"""
        return await self.client.connect()

    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        await self.client.disconnect()

    async def enqueue(self, job_data: dict, priority: int = 0) -> bool:
        """Add job to queue"""
        if not self.client.is_connected:
            return False

        import uuid

        job_id = job_data.get("job_id") or str(uuid.uuid4())
        job_payload = json.dumps({**job_data, "job_id": job_id})

        # Use sorted set for priority queue
        score = priority * 1_000_000_000 + int(datetime.utcnow().timestamp() * 1000)

        try:
            await self.client._client.zadd(self.queue_name, {job_payload: score})
            logger.info(f"Job {job_id} enqueued with priority {priority}")
            return True
        except RedisError as e:
            logger.error(f"Failed to enqueue job: {e}")
            return False

    async def dequeue(self, timeout: int = 0) -> Optional[dict]:
        """Remove and return highest priority job"""
        if not self.client.is_connected:
            return None

        try:
            # Get highest priority job
            result = await self.client._client.zpopmax(self.queue_name)
            if not result:
                return None

            job_data, _ = result[0]
            job = json.loads(job_data)

            # Add to processing set for tracking
            await self.client._client.sadd(self.processing_set, job.get("job_id", ""))

            return job
        except RedisError as e:
            logger.error(f"Failed to dequeue job: {e}")
            return None

    async def complete_job(self, job_id: str) -> bool:
        """Mark job as completed"""
        if not self.client.is_connected:
            return False

        try:
            await self.client._client.srem(self.processing_set, job_id)
            return True
        except RedisError as e:
            logger.error(f"Failed to complete job: {e}")
            return False

    async def get_queue_size(self) -> int:
        """Get number of jobs in queue"""
        if not self.client.is_connected:
            return 0
        try:
            return await self.client._client.zcard(self.queue_name)
        except RedisError as e:
            logger.error(f"Failed to get queue size: {e}")
            return 0


class RateLimiter:
    """
    Redis-based rate limiter using sliding window algorithm.

    Usage:
        limiter = RateLimiter(limit=100, window=60)  # 100 requests per minute
        allowed = await limiter.check("user_id:123")
    """

    def __init__(self, limit: int = 100, window: int = 60):
        self.limit = limit
        self.window = window
        self.client = RedisClient()

    async def connect(self) -> bool:
        """Connect to Redis"""
        return await self.client.connect()

    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        await self.client.disconnect()

    async def check(self, key: str) -> bool:
        """
        Check if request is allowed under rate limit.
        Returns True if allowed, False if limit exceeded.
        """
        if not self.client.is_connected:
            return True  # Allow if Redis unavailable

        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window)

        try:
            redis_client = self.client._client
            pipe = redis_client.pipeline()

            # Remove old entries outside window
            pipe.zremrangebyscore(key, 0, window_start.timestamp())

            # Count current requests in window
            pipe.zcard(key)

            # Add current request
            pipe.zadd(key, {f"{now.timestamp()}:{now.microsecond}": now.timestamp()})

            # Set expiration
            pipe.expire(key, self.window)

            results = await pipe.execute()
            current_count = results[1]

            return current_count < self.limit

        except RedisError as e:
            logger.error(f"Rate limiter error: {e}")
            return True  # Allow on error

    async def get_remaining(self, key: str) -> int:
        """Get remaining requests in current window"""
        if not self.client.is_connected:
            return self.limit

        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window)

        try:
            await self.client._client.zremrangebyscore(key, 0, window_start.timestamp())
            count = await self.client._client.zcard(key)
            return max(0, self.limit - count)
        except RedisError as e:
            logger.error(f"Rate limiter get remaining error: {e}")
            return self.limit


# Global instances
_redis_client: Optional[RedisClient] = None
_job_queue: Optional[JobQueue] = None
_rate_limiter: Optional[RateLimiter] = None


async def get_redis_client() -> RedisClient:
    """Get global Redis client instance"""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
        await _redis_client.connect()
    return _redis_client


async def get_job_queue(queue_name: str = "default") -> JobQueue:
    """Get job queue instance"""
    global _job_queue
    if _job_queue is None or _job_queue.queue_name != f"queue:{queue_name}":
        _job_queue = JobQueue(queue_name)
        await _job_queue.connect()
    return _job_queue


async def get_rate_limiter(limit: int = 100, window: int = 60) -> RateLimiter:
    """Get rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(limit, window)
        await _rate_limiter.connect()
    return _rate_limiter


async def close_redis() -> None:
    """Close all Redis connections"""
    global _redis_client, _job_queue, _rate_limiter

    if _redis_client:
        await _redis_client.disconnect()
        _redis_client = None

    if _job_queue:
        await _job_queue.disconnect()
        _job_queue = None

    if _rate_limiter:
        await _rate_limiter.disconnect()
        _rate_limiter = None

    logger.info("All Redis connections closed")
