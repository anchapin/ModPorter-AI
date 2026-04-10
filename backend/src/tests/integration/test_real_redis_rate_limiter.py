"""
Real-service integration tests for Redis-backed operations.

These tests verify ACTUAL Redis behavior, testing cache operations
and rate limiter integration.

To run: USE_REAL_SERVICES=1 pytest tests/integration/test_real_redis_rate_limiter.py -v
"""

import pytest
import time


pytestmark = pytest.mark.real_service


class TestRealRedisCache:
    """Integration tests for Redis cache operations."""

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, real_redis_cache):
        """Test basic cache operations."""
        cache = real_redis_cache

        # Set a value
        await cache.set("test_key", "test_value", ex=60)

        # Get it back
        value = await cache.get("test_key")
        assert value == "test_value"

    @pytest.mark.asyncio
    async def test_cache_delete(self, real_redis_cache):
        """Test cache deletion."""
        cache = real_redis_cache

        # Set and delete
        await cache.set("delete_key", "delete_value")
        await cache.delete("delete_key")

        value = await cache.get("delete_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_cache_expiry(self, real_redis_cache):
        """Test cache expiry (using short TTL for testing)."""
        cache = real_redis_cache

        # Set with 1 second expiry
        await cache.set("expiry_key", "expiry_value", ex=1)

        # Should exist immediately
        value = await cache.get("expiry_key")
        assert value == "expiry_value"

        # Wait for expiry
        time.sleep(1.5)

        # Should be gone
        value = await cache.get("expiry_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_cache_hash_operations(self, real_redis_cache):
        """Test Redis hash operations."""
        cache = real_redis_cache

        hash_key = f"hash_test_{id(self)}"

        # Set hash fields
        await cache.hset(hash_key, "field1", "value1")
        await cache.hset(hash_key, "field2", "value2")

        # Get all
        all_data = await cache.hgetall(hash_key)
        assert all_data["field1"] == "value1"
        assert all_data["field2"] == "value2"

        # Get single field
        field1 = await cache.hget(hash_key, "field1")
        assert field1 == "value1"

    @pytest.mark.asyncio
    async def test_cache_list_operations(self, real_redis_cache):
        """Test Redis list operations for queue-like behavior."""
        cache = real_redis_cache

        list_key = f"list_test_{id(self)}"

        # Push items
        await cache.lpush(list_key, "item1", "item2", "item3")

        # Get length
        length = await cache.llen(list_key)
        assert length == 3

        # Pop items
        item = await cache.rpop(list_key)
        assert item == "item1"


class TestRealRedisRateLimiterIntegration:
    """Integration tests verifying rate limiter can connect to Redis."""

    @pytest.mark.asyncio
    async def test_rate_limiter_redis_connection(self, real_rate_limiter):
        """Test that rate limiter successfully connects to Redis."""
        limiter = real_rate_limiter

        # Verify Redis connection is established
        assert limiter._redis is not None
        assert limiter._use_redis is True

        # Verify we can ping Redis through the limiter
        result = await limiter._redis.ping()
        assert result is True

    @pytest.mark.asyncio
    async def test_rate_limiter_increment_counter(self, real_rate_limiter):
        """Test rate limiter counter operations in Redis."""
        limiter = real_rate_limiter
        client_id = f"test_client_{id(self)}"

        # Use the internal Redis to simulate rate limit check
        key = f"rate_limit:{client_id}"

        # Increment the counter
        count = await limiter._redis.incr(key)
        assert count == 1

        # Increment again
        count = await limiter._redis.incr(key)
        assert count == 2

        # Set expiry
        await limiter._redis.expire(key, 60)

        # Verify TTL
        ttl = await limiter._redis.ttl(key)
        assert ttl > 0

    @pytest.mark.asyncio
    async def test_rate_limiter_reset(self, real_rate_limiter):
        """Test rate limiter state reset."""
        limiter = real_rate_limiter
        client_id = f"test_client_{id(self)}"

        key = f"rate_limit:{client_id}"

        # Set up some state
        await limiter._redis.set(key, "5")
        await limiter._redis.expire(key, 60)

        # Delete the key (simulating reset)
        await limiter._redis.delete(key)

        # Verify it's gone
        value = await limiter._redis.get(key)
        assert value is None
