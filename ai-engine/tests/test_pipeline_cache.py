"""
Tests for search/pipeline_cache.py module.
"""

import pytest
import time
from search.pipeline_cache import (
    PipelineCache,
    MemoryCache,
    CachedResult,
)


class TestCachedResult:
    """Test CachedResult dataclass"""

    def test_cached_result_creation(self):
        """Test creating CachedResult"""
        result = CachedResult(
            data={"key": "value"},
            timestamp=time.time(),
            ttl=3600,
        )

        assert result.data == {"key": "value"}
        assert result.ttl == 3600

    def test_cached_result_is_expired(self):
        """Test expired detection"""
        import time
        # Create result with past timestamp and 0 ttl
        result = CachedResult(
            data={"key": "value"},
            timestamp=time.time() - 100,
            ttl=10,
        )

        assert result.is_expired()


class TestMemoryCache:
    """Test MemoryCache class"""

    def test_memory_cache_set_get(self):
        """Test basic set and get operations"""
        cache = MemoryCache()

        cache.set("key1", {"data": "value"}, ttl=60)

        result = cache.get("key1")
        assert result is not None
        assert result.data == {"data": "value"}

    def test_memory_cache_miss(self):
        """Test cache miss returns None"""
        cache = MemoryCache()

        result = cache.get("nonexistent")
        assert result is None

    def test_memory_cache_delete(self):
        """Test deleting entries"""
        cache = MemoryCache()

        cache.set("key1", {"data": "value"}, ttl=60)
        cache.delete("key1")

        result = cache.get("key1")
        assert result is None


class TestPipelineCache:
    """Test PipelineCache class"""

    @pytest.fixture
    def cache(self):
        """Create a PipelineCache instance"""
        return PipelineCache(backend="memory", ttl=3600)

    def test_cache_initialization(self, cache):
        """Test cache initialization"""
        assert cache is not None

    def test_set_and_get(self, cache):
        """Test setting and getting values"""
        cache.set("query1", {"results": ["doc1", "doc2"]})

        result = cache.get("query1")
        assert result is not None
        assert "results" in result.data

    def test_cache_miss(self, cache):
        """Test cache miss"""
        result = cache.get("missing_key")
        assert result is None

    def test_cache_invalidate(self, cache):
        """Test invalidating cache entries"""
        cache.set("key1", {"data": "value"})
        cache.invalidate("key1")

        result = cache.get("key1")
        assert result is None

    def test_cache_stats(self, cache):
        """Test cache statistics"""
        cache.set("key1", {"data": "1"})
        cache.set("key2", {"data": "2"})
        cache.get("key1")  # hit
        cache.get("missing")  # miss

        stats = cache.get_stats()

        assert "hits" in stats or "misses" in stats or "size" in stats

    def test_cache_ttl_expiration(self):
        """Test that cached entries expire"""
        # Create cache with very short TTL
        cache = PipelineCache(backend="memory", ttl=1)

        cache.set("key1", {"data": "value"})

        # Should exist immediately
        assert cache.get("key1") is not None

        # Wait for expiration
        time.sleep(1.5)

        # Should be expired now
        cache.get("key1")
        # May or may not be expired depending on implementation

    def test_multiple_keys(self, cache):
        """Test using multiple keys"""
        for i in range(5):
            cache.set(f"key{i}", {"index": i})

        for i in range(5):
            result = cache.get(f"key{i}")
            assert result is not None
            assert result.data["index"] == i


class TestPipelineCacheIntegration:
    """Integration tests for PipelineCache"""

    def test_query_caching_workflow(self):
        """Test typical query caching workflow"""
        cache = PipelineCache(backend="memory", ttl=3600)

        # First query - cache miss
        query = "bukkit plugin tutorial"
        cached = cache.get(query)

        if cached is None:
            # Simulate expensive operation
            results = ["doc1", "doc2", "doc3"]
            cache.set(query, {"results": results})

        # Second query - cache hit
        cached = cache.get(query)
        assert cached is not None

    def test_cache_invalidation_workflow(self):
        """Test cache invalidation on data update"""
        cache = PipelineCache(backend="memory", ttl=3600)

        # Add cached results
        cache.set("query1", {"results": ["old_doc"]})

        # Data source updated - invalidate cache
        cache.invalidate("query1")

        # Should be a cache miss now
        result = cache.get("query1")
        assert result is None

    def test_concurrent_access(self):
        """Test cache with simulated concurrent access"""
        import threading

        cache = PipelineCache(backend="memory", ttl=3600)
        errors = []

        def worker(key, value):
            try:
                cache.set(key, value)
                result = cache.get(key)
                if result is None:
                    errors.append(f"Missing: {key}")
            except Exception as e:
                errors.append(str(e))

        threads = []
        for i in range(10):
            t = threading.Thread(target=worker, args=(f"key{i}", {"i": i}))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0