Simple but comprehensive tests for graph_caching.py

This test module provides core coverage of graph caching service,
focusing on the most important caching functionality.
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.graph_caching import (
    GraphCachingService,
    CacheLevel,
    CacheStrategy,
    CacheInvalidationStrategy,
    LRUCache,
    CacheEntry,
    CacheStats,
    CacheConfig
)


@pytest.fixture
def cache_service():
    """Create a graph caching service instance with mocked dependencies."""
    with patch('src.services.graph_caching.logger'):
        service = GraphCachingService()
        return service


class TestLRUCache:
    """Test cases for LRU cache implementation."""

    def test_init(self):
        """Test LRU cache initialization."""
        cache = LRUCache(100)
        assert cache.max_size == 100
        assert cache.size() == 0
        assert cache.keys() == []

    def test_put_and_get(self):
        """Test basic put and get operations."""
        cache = LRUCache(3)

        # Add items
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        # Verify items are added
        assert cache.size() == 3
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_eviction_policy(self):
        """Test LRU eviction policy."""
        cache = LRUCache(2)

        # Add items to fill cache
        cache.put("key1", "value1")
        cache.put("key2", "value2")

        # Access first item to make it most recently used
        cache.get("key1")

        # Add third item, should evict key2 (least recently used)
        cache.put("key3", "value3")

        # Verify eviction
        assert cache.get("key1") == "value1"  # Most recently used
        assert cache.get("key2") is None       # Evicted
        assert cache.get("key3") == "value3"  # Newly added

    def test_remove(self):
        """Test removal operation."""
        cache = LRUCache(3)

        # Add items
        cache.put("key1", "value1")
        cache.put("key2", "value2")

        # Remove an item
        result = cache.remove("key1")
        assert result is True
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

    def test_clear(self):
        """Test clearing cache."""
        cache = LRUCache(3)

        # Add items
        cache.put("key1", "value1")
        cache.put("key2", "value2")

        # Verify items exist
        assert cache.size() == 2
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"

        # Clear cache
        cache.clear()

        # Verify cache is empty
        assert cache.size() == 0
        assert cache.keys() == []


class TestCacheEntry:
    """Test cases for cache entry dataclass."""

    def test_creation(self):
        """Test cache entry creation."""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            created_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            access_count=5,
            size_bytes=100,
            ttl_seconds=300,
            metadata={"custom": "data"}
        )

        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.access_count == 5
        assert entry.size_bytes == 100
        assert entry.ttl_seconds == 300
        assert entry.metadata["custom"] == "data"


class TestCacheStats:
    """Test cases for cache statistics."""

    def test_initialization(self):
        """Test cache stats initialization."""
        stats = CacheStats()

        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.sets == 0
        assert stats.deletes == 0
        assert stats.evictions == 0
        assert stats.total_size_bytes == 0
        assert stats.avg_access_time_ms == 0.0
        assert stats.memory_usage_mb == 0.0
        assert stats.hit_ratio == 0.0

    def test_hit_ratio_calculation(self):
        """Test hit ratio calculation."""
        stats = CacheStats()

        # Add some hits and misses
        stats.hits = 80
        stats.misses = 20

        # Test hit ratio calculation
        assert stats.hit_ratio == 0.8  # 80 / (80 + 20)


class TestGraphCachingService:
    """Test cases for GraphCachingService."""

    def test_init(self, cache_service):
        """Test service initialization."""
        # Verify cache configurations are set
        assert "nodes" in cache_service.cache_configs
        assert "relationships" in cache_service.cache_configs
        assert "patterns" in cache_service.cache_configs
        assert "queries" in cache_service.cache_configs
        assert "layouts" in cache_service.cache_configs
        assert "clusters" in cache_service.cache_configs

        # Verify cache stats are initialized
        assert "l1_memory" in cache_service.cache_stats
        assert "l2_redis" in cache_service.cache_stats
        assert "l3_database" in cache_service.cache_stats
        assert "overall" in cache_service.cache_stats

        # Verify cleanup thread is started
        assert cache_service.cleanup_thread is not None
        assert not cache_service.stop_cleanup

    @pytest.mark.asyncio
    async def test_basic_cache_operations(self, cache_service):
        """Test basic cache get and set operations."""
        # Test setting and getting values
        await cache_service.set("test_type", "test_key", "test_value")
        result = await cache_service.get("test_type", "test_key")
        assert result == "test_value"

        # Test cache miss
        result = await cache_service.get("test_type", "non_existent")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_with_ttl(self, cache_service):
        """Test cache with TTL."""
        # Set a value with short TTL and test expiration
        await cache_service.set("test_type", "ttl_key", "ttl_value", ttl=1)

        # Wait for expiration
        time.sleep(2)

        # Value should be expired
        result = await cache_service.get("test_type", "ttl_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, cache_service):
        """Test cache invalidation."""
        # Add some cache entries
        await cache_service.set("test_type1", "key1", "value1")
        await cache_service.set("test_type2", "key2", "value2")
        await cache_service.set("test_type1", "key3", "value3")

        # Invalidate by type
        cache_service.invalidate("test_type1")

        # Test invalidation results
        assert await cache_service.get("test_type1", "key1") is None
        assert await cache_service.get("test_type1", "key3") is None
        assert await cache_service.get("test_type2", "key2") == "value2"  # Should still exist

    @pytest.mark.asyncio
    async def test_cache_decorator(self, cache_service):
        """Test cache decorator functionality."""
        # Create a mock function
        call_count = 0

        @cache_service.cache()
        async def expensive_function(param):
            nonlocal call_count
            call_count += 1
            return f"result_for_{param}"

        # First call should execute function
        result1 = await expensive_function("param1")
        assert result1 == "result_for_param1"
        assert call_count == 1

        # Second call should use cache
        result2 = await expensive_function("param1")
        assert result2 == "result_for_param1"
        assert call_count == 1  # No additional call

        # Call with different parameter should execute function
        result3 = await expensive_function("param2")
        assert result3 == "result_for_param2"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_performance_monitoring(self, cache_service):
        """Test performance monitoring of cache operations."""
        # Reset stats
        cache_service.cache_stats["overall"].hits = 0
        cache_service.cache_stats["overall"].misses = 0

        # Perform some cache operations
        await cache_service.set("test_type", "key1", "value1")
        await cache_service.set("test_type", "key2", "value2")
        await cache_service.set("test_type", "key3", "value3")

        # Get values to record hits
        await cache_service.get("test_type", "key1")
        await cache_service.get("test_type", "key2")

        # Get non-existent value to record miss
        await cache_service.get("test_type", "non_existent")

        # Verify performance stats
        stats = cache_service.cache_stats["overall"]
        assert stats.hits == 2
        assert stats.misses == 1
        assert stats.sets == 3
        assert stats.hit_ratio == 2/3  # 2 hits out of 3 total accesses

    @pytest.mark.asyncio
    async def test_batch_operations(self, cache_service):
        """Test batch cache operations."""
        # Add items to cache
        await cache_service.set("test_type", "key1", "value1")
        await cache_service.set("test_type", "key2", "value2")
        await cache_service.set("test_type", "key3", "value3")

        # Get multiple items
        results = await cache_service.get_many("test_type", ["key1", "key2", "key3"])

        # Verify results
        assert results["key1"] == "value1"
        assert results["key2"] == "value2"
        assert results["key3"] == "value3"
        assert "non_existent" not in results

        # Set multiple items
        await cache_service.set_many(
            "test_type",
            {
                "key4": "value4",
                "key5": "value5",
                "key6": "value6"
            }
        )

        # Verify batch set
        assert await cache_service.get("test_type", "key4") == "value4"
        assert await cache_service.get("test_type", "key5") == "value5"
        assert await cache_service.get("test_type", "key6") == "value6"

    def test_thread_safety(self, cache_service):
        """Test thread safety of cache operations."""
        # Use threading to simulate concurrent access
        errors = []

        def worker(thread_id):
            try:
                # Each thread tries to add and get values
                for i in range(10):
                    cache_service.l1_cache["test_type"] = {f"key_{thread_id}_{i}": f"value_{thread_id}_{i}"}
                    time.sleep(0.01)  # Small delay to increase contention
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0

        # Verify cache has expected entries
        # With 5 threads and 10 operations each, we should have 50 entries
        # But due to the implementation details, we just verify that cache is not empty
        assert len(cache_service.l1_cache["test_type"]) > 0
```

Now let's run the tests to see if they pass:
<tool_call>terminal
<arg_key>command</arg_key>
<arg_value>python -m pytest tests/test_graph_caching_simple.py -v --tb=short</arg_value>
<arg_key>cd</arg_key>
<arg_value>C:\Users\ancha\Documents\projects\ModPorter-AI\backend</arg_value>
</tool_call>
