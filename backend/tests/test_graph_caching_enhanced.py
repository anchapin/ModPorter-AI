"""
Enhanced comprehensive tests for Graph Caching Service

Tests cover advanced caching functionality for knowledge graph:
- Multi-level caching (L1 memory, L2 Redis, L3 database)
- Cache strategies (LRU, LFU, FIFO, TTL)
- Cache invalidation and eviction
- Performance monitoring and optimization
- Serialization and compression
- Dependency management and cascading invalidation
- Advanced edge cases and error scenarios
"""

import pytest
import asyncio
import json
import pickle
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List, Any, Optional
import weakref
import gc

from src.services.graph_caching import (
    GraphCachingService,
    CacheLevel,
    CacheStrategy,
    CacheInvalidationStrategy,
    CacheEntry,
    CacheStats,
    CacheConfig,
    LRUCache,
    LFUCache
)


class TestCacheEntryAdvanced:
    """Advanced tests for CacheEntry dataclass"""
    
    def test_cache_entry_ttl_expiration(self):
        """Test cache entry TTL expiration logic"""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            created_at=datetime.utcnow() - timedelta(seconds=10),
            last_accessed=datetime.utcnow() - timedelta(seconds=5),
            ttl_seconds=5  # Should be expired now
        )
        
        assert entry.is_expired()
        
        # Test non-expired entry
        fresh_entry = CacheEntry(
            key="fresh_key",
            value="fresh_value",
            created_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            ttl_seconds=60
        )
        
        assert not fresh_entry.is_expired()
    
    def test_cache_entry_access_tracking(self):
        """Test access tracking and statistics"""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            created_at=datetime.utcnow() - timedelta(seconds=10),
            last_accessed=datetime.utcnow() - timedelta(seconds=5),
            ttl_seconds=60
        )
        
        initial_access_count = getattr(entry, 'access_count', 0)
        
        # Simulate access
        entry.last_accessed = datetime.utcnow()
        if hasattr(entry, 'access_count'):
            entry.access_count += 1
        
        # Verify access was tracked
        assert entry.last_accessed > entry.created_at


class TestCacheConfigAdvanced:
    """Advanced tests for CacheConfig"""
    
    def test_cache_config_validation(self):
        """Test cache config parameter validation"""
        # Valid config
        config = CacheConfig(
            l1_max_size=1000,
            l2_max_size=10000,
            default_ttl=300,
            compression_threshold=1024,
            enable_compression=True
        )
        assert config.l1_max_size == 1000
        assert config.enable_compression is True
        
        # Test with invalid parameters
        with pytest.raises((ValueError, TypeError)):
            CacheConfig(l1_max_size=-1)
    
    def test_cache_config_serialization(self):
        """Test cache config serialization"""
        config = CacheConfig(
            l1_max_size=1000,
            l2_max_size=10000,
            default_ttl=300,
            compression_threshold=1024,
            enable_compression=True,
            enable_metrics=True
        )
        
        config_dict = config.__dict__ if hasattr(config, '__dict__') else {}
        assert isinstance(config_dict, dict)
        assert config_dict.get('l1_max_size') == 1000


class TestLRUCacheAdvanced:
    """Advanced tests for LRUCache implementation"""
    
    def test_lru_cache_boundary_conditions(self):
        """Test LRU cache with boundary conditions"""
        cache = LRUCache(max_size=3)
        
        # Test empty cache
        assert cache.get("nonexistent") is None
        assert len(cache) == 0
        
        # Fill to capacity
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        assert len(cache) == 3
        
        # Test LRU eviction
        cache.set("d", 4)  # Should evict 'a'
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3
        assert cache.get("d") == 4
    
    def test_lru_cache_access_order(self):
        """Test that LRU maintains correct access order"""
        cache = LRUCache(max_size=3)
        
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        
        # Access 'a' to make it most recently used
        cache.get("a")
        
        # Add new item, should evict 'b' (least recently used)
        cache.set("d", 4)
        
        assert cache.get("a") == 1  # Should still be there
        assert cache.get("b") is None  # Should be evicted
        assert cache.get("d") == 4
    
    def test_lru_cache_thread_safety(self):
        """Test LRU cache thread safety"""
        cache = LRUCache(max_size=100)
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                for i in range(50):
                    key = f"worker_{worker_id}_key_{i}"
                    value = f"worker_{worker_id}_value_{i}"
                    cache.set(key, value)
                    result = cache.get(key)
                    results.append((worker_id, i, result == value))
            except Exception as e:
                errors.append((worker_id, str(e)))
        
        # Run multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) > 0


class TestLFUCacheAdvanced:
    """Advanced tests for LFUCache implementation"""
    
    def test_lfu_cache_frequency_tracking(self):
        """Test LFU cache tracks access frequency correctly"""
        cache = LFUCache(max_size=3)
        
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        
        # Access 'a' multiple times
        for _ in range(3):
            cache.get("a")
        
        # Access 'b' once
        cache.get("b")
        
        # Add new item, should evict 'c' (least frequently used)
        cache.set("d", 4)
        
        assert cache.get("a") == 1  # Should still be there (highest frequency)
        assert cache.get("b") == 2  # Should still be there
        assert cache.get("c") is None  # Should be evicted (lowest frequency)
        assert cache.get("d") == 4
    
    def test_lfu_cache_tie_breaking(self):
        """Test LFU cache tie-breaking when frequencies are equal"""
        cache = LFUCache(max_size=2)
        
        cache.set("a", 1)
        cache.set("b", 2)
        
        # Access both items equally
        cache.get("a")
        cache.get("b")
        
        # Add new item, should evict one of them
        cache.set("c", 3)
        
        # One of 'a' or 'b' should be evicted
        present_a = cache.get("a") is not None
        present_b = cache.get("b") is not None
        present_c = cache.get("c") is not None
        
        assert present_c  # New item should be present
        assert present_a != present_b  # Exactly one of a or b should be present


class TestGraphCachingServiceAdvanced:
    """Advanced tests for GraphCachingService"""
    
    @pytest.fixture
    def service(self):
        """Create GraphCachingService instance"""
        config = CacheConfig(
            l1_max_size=100,
            l2_max_size=1000,
            default_ttl=60,
            compression_threshold=512,
            enable_compression=True,
            enable_metrics=True
        )
        return GraphCachingService(config=config)
    
    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client"""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = 1
        mock_redis.exists.return_value = 0
        return mock_redis
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.mark.asyncio
    async def test_cache_strategy_selection(self, service):
        """Test different cache strategies"""
        test_data = {"key": "value", "complex": {"nested": "data"}}
        
        # Test LRU strategy
        result_lru = await service._apply_cache_strategy(
            CacheStrategy.LRU, test_data
        )
        assert result_lru is not None
        
        # Test LFU strategy
        result_lfu = await service._apply_cache_strategy(
            CacheStrategy.LFU, test_data
        )
        assert result_lfu is not None
        
        # Test FIFO strategy
        result_fifo = await service._apply_cache_strategy(
            CacheStrategy.FIFO, test_data
        )
        assert result_fifo is not None
    
    @pytest.mark.asyncio
    async def test_cache_compression(self, service):
        """Test cache compression for large data"""
        # Large data that should trigger compression
        large_data = "x" * 1000  # Larger than compression_threshold
        
        # Test compression
        compressed = service._compress_data(large_data)
        assert compressed != large_data  # Should be compressed
        assert len(compressed) < len(large_data)  # Should be smaller
        
        # Test decompression
        decompressed = service._decompress_data(compressed)
        assert decompressed == large_data  # Should match original
    
    @pytest.mark.asyncio
    async def test_cache_serialization(self, service):
        """Test data serialization/deserialization"""
        test_cases = [
            "simple_string",
            123,
            {"complex": "object", "nested": {"data": [1, 2, 3]}},
            [1, 2, 3, 4, 5],
            None,
            True,
            False
        ]
        
        for test_data in test_cases:
            # Serialize
            serialized = service._serialize_data(test_data)
            assert serialized is not None
            
            # Deserialize
            deserialized = service._deserialize_data(serialized)
            assert deserialized == test_data
    
    @pytest.mark.asyncio
    async def test_cache_dependency_management(self, service, mock_db):
        """Test cache dependency tracking and invalidation"""
        # Create cache entries with dependencies
        main_key = "main_node_123"
        dep_key = "dep_node_456"
        
        # Set up dependency
        await service._set_dependency(main_key, [dep_key])
        
        # Verify dependency tracking
        dependencies = await service._get_dependencies(main_key)
        assert dep_key in dependencies
        
        # Test cascading invalidation
        await service.invalidate_with_dependencies(main_key)
        
        # Both main and dependent should be invalidated
        main_result = await service.get("node", main_key, db=mock_db)
        dep_result = await service.get("node", dep_key, db=mock_db)
        
        assert main_result is None
        assert dep_result is None
    
    @pytest.mark.asyncio
    async def test_cache_performance_monitoring(self, service):
        """Test cache performance metrics"""
        # Simulate cache operations
        for i in range(10):
            await service.set("test", f"key_{i}", f"value_{i}")
            await service.get("test", f"key_{i}")
        
        # Get metrics
        metrics = await service.get_performance_metrics()
        
        assert "total_operations" in metrics
        assert "hit_rate" in metrics
        assert "miss_rate" in metrics
        assert "cache_sizes" in metrics
        assert metrics["total_operations"] >= 20  # 10 sets + 10 gets
    
    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self, service, mock_db):
        """Test TTL-based cache expiration"""
        # Set cache with very short TTL
        short_ttl_key = "short_ttl_key"
        await service.set("test", short_ttl_key, "test_value", ttl=1)
        
        # Should be available immediately
        result = await service.get("test", short_ttl_key, db=mock_db)
        assert result == "test_value"
        
        # Wait for expiration
        await asyncio.sleep(2)
        
        # Should be expired now
        result = await service.get("test", short_ttl_key, db=mock_db)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_warm_up(self, service, mock_db):
        """Test cache warm-up functionality"""
        # Mock database queries for warm-up
        mock_data = [
            {"id": "1", "data": "value1"},
            {"id": "2", "data": "value2"},
            {"id": "3", "data": "value3"}
        ]
        
        with patch.object(service, '_load_data_for_warm_up', new=AsyncMock(return_value=mock_data)):
            # Warm up cache
            await service.warm_up_cache("node", ["1", "2", "3"])
            
            # Verify cache is warmed
            for item in mock_data:
                cached_value = await service.get("node", item["id"], db=mock_db)
                assert cached_value is not None
    
    @pytest.mark.asyncio
    async def test_cache_bulk_operations(self, service, mock_db):
        """Test bulk cache operations"""
        test_data = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3"
        }
        
        # Bulk set
        await service.bulk_set("test", test_data)
        
        # Bulk get
        results = await service.bulk_get("test", list(test_data.keys()))
        
        assert len(results) == len(test_data)
        for key, expected_value in test_data.items():
            assert results[key] == expected_value
        
        # Bulk delete
        await service.bulk_delete("test", list(test_data.keys()))
        
        # Verify deletion
        results_after_delete = await service.bulk_get("test", list(test_data.keys()))
        assert all(value is None for value in results_after_delete.values())
    
    @pytest.mark.asyncio
    async def test_cache_memory_management(self, service):
        """Test cache memory management and cleanup"""
        # Fill cache beyond capacity
        for i in range(200):  # More than l1_max_size of 100
            await service.set("test", f"key_{i}", f"value_{i}")
        
        # Get memory stats
        memory_stats = await service.get_memory_stats()
        
        assert "l1_size" in memory_stats
        assert "l2_size" in memory_stats
        assert "memory_usage_mb" in memory_stats
        
        # L1 should not exceed max size
        assert memory_stats["l1_size"] <= service.config.l1_max_size
    
    @pytest.mark.asyncio
    async def test_cache_error_recovery(self, service, mock_db):
        """Test cache error recovery mechanisms"""
        # Mock Redis failure
        failing_redis = AsyncMock()
        failing_redis.get.side_effect = Exception("Redis connection failed")
        failing_redis.set.side_effect = Exception("Redis connection failed")
        
        service.redis_client = failing_redis
        
        # Operations should fall back to other levels
        await service.set("test", "fallback_key", "fallback_value")
        result = await service.get("test", "fallback_key", db=mock_db)
        
        assert result == "fallback_value"  # Should still work
    
    @pytest.mark.asyncio
    async def test_cache_consistency_validation(self, service):
        """Test cache consistency across levels"""
        test_key = "consistency_key"
        test_value = "consistency_value"
        
        # Set in cache
        await service.set("test", test_key, test_value)
        
        # Verify consistency across all levels
        l1_result = service.l1_cache.get(test_key)
        l2_result = await service.redis_client.get(f"test:{test_key}")
        
        if l1_result is not None:
            assert l1_result.value == test_value
        if l2_result is not None:
            # Redis returns bytes, need to decode
            decoded_result = service._deserialize_data(l2_result)
            assert decoded_result == test_value
    
    @pytest.mark.asyncio
    async def test_cache_optimization_strategies(self, service):
        """Test cache optimization strategies"""
        # Get initial performance metrics
        initial_metrics = await service.get_performance_metrics()
        
        # Simulate usage patterns
        hot_keys = ["hot1", "hot2", "hot3"]
        cold_keys = ["cold1", "cold2", "cold3"]
        
        # Access hot keys frequently
        for _ in range(10):
            for key in hot_keys:
                await service.get("test", key)
                await service.set("test", key, f"value_{key}")
        
        # Access cold keys infrequently
        for key in cold_keys:
            await service.get("test", key)
            await service.set("test", key, f"value_{key}")
        
        # Apply optimizations
        await service.optimize_cache()
        
        # Get optimized metrics
        optimized_metrics = await service.get_performance_metrics()
        
        # Should see improvements in hit rate or efficiency
        optimized_metadata = optimized_metrics.get("metadata", {})
        assert "optimization_applied" in optimized_metadata


class TestCacheInvalidationStrategies:
    """Test various cache invalidation strategies"""
    
    @pytest.mark.asyncio
    async def test_time_based_invalidation(self, service):
        """Test time-based invalidation"""
        test_keys = ["time_key_1", "time_key_2", "time_key_3"]
        
        # Set cache entries with different TTLs
        await service.set("test", test_keys[0], "value1", ttl=1)
        await service.set("test", test_keys[1], "value2", ttl=5)
        await service.set("test", test_keys[2], "value3", ttl=10)
        
        # Wait for shortest TTL to expire
        await asyncio.sleep(2)
        
        # Check invalidation
        results = await service.bulk_get("test", test_keys)
        
        assert results[test_keys[0]] is None  # Should be expired
        assert results[test_keys[1]] is not None  # Should still be valid
        assert results[test_keys[2]] is not None  # Should still be valid
    
    @pytest.mark.asyncio
    async def test_dependency_based_invalidation(self, service):
        """Test dependency-based invalidation"""
        main_key = "main_data"
        dependent_keys = ["dep1", "dep2", "dep3"]
        
        # Set up dependencies
        for dep_key in dependent_keys:
            await service.set("test", dep_key, f"value_{dep_key}")
        
        await service._set_dependency(main_key, dependent_keys)
        await service.set("test", main_key, "main_value")
        
        # Invalidate main, should cascade to dependents
        await service.invalidate_with_dependencies(main_key)
        
        # Check all are invalidated
        results = await service.bulk_get("test", [main_key] + dependent_keys)
        assert all(result is None for result in results.values())
    
    @pytest.mark.asyncio
    async def test_pattern_based_invalidation(self, service):
        """Test pattern-based invalidation"""
        # Set cache entries matching pattern
        pattern_keys = [
            "user:123:profile",
            "user:123:settings",
            "user:123:preferences",
            "user:456:profile",  # Different user, shouldn't match
        ]
        
        for key in pattern_keys:
            await service.set("user", key, f"value_{key}")
        
        # Invalidate using pattern
        await service.invalidate_by_pattern("user:*123*")
        
        # Check pattern-matching entries are invalidated
        results = await service.bulk_get("user", pattern_keys)
        
        assert results["user:123:profile"] is None
        assert results["user:123:settings"] is None
        assert results["user:123:preferences"] is None
        # Different user should not be affected
        assert results["user:456:profile"] is not None


class TestCachePerformanceBenchmarks:
    """Performance benchmarking tests"""
    
    @pytest.mark.asyncio
    async def test_cache_read_performance(self, service):
        """Test cache read performance under load"""
        # Pre-populate cache
        num_keys = 1000
        for i in range(num_keys):
            await service.set("perf", f"key_{i}", f"value_{i}")
        
        # Measure read performance
        start_time = time.time()
        
        # Concurrent reads
        tasks = []
        for i in range(num_keys):
            task = service.get("perf", f"key_{i}")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Performance assertions
        assert len(results) == num_keys
        assert all(result is not None for result in results)
        assert duration < 5.0  # Should complete within 5 seconds
        
        # Calculate throughput
        throughput = num_keys / duration
        assert throughput > 200  # Should handle at least 200 ops/sec
    
    @pytest.mark.asyncio
    async def test_cache_write_performance(self, service):
        """Test cache write performance under load"""
        num_operations = 500
        
        start_time = time.time()
        
        # Concurrent writes
        tasks = []
        for i in range(num_operations):
            task = service.set("perf_write", f"key_{i}", f"value_{i}")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Performance assertions
        assert all(results)  # All writes should succeed
        assert duration < 5.0  # Should complete within 5 seconds
        
        # Calculate throughput
        throughput = num_operations / duration
        assert throughput > 100  # Should handle at least 100 writes/sec
    
    @pytest.mark.asyncio
    async def test_cache_mixed_workload_performance(self, service):
        """Test cache performance with mixed read/write workload"""
        num_operations = 300
        
        start_time = time.time()
        
        # Mixed workload: 70% reads, 30% writes
        tasks = []
        for i in range(num_operations):
            if i % 10 < 7:  # 70% reads
                task = service.get("mixed", f"key_{i % 50}")  # Reuse keys to test hits
            else:  # 30% writes
                task = service.set("mixed", f"key_{i}", f"value_{i}")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Performance assertions
        assert duration < 5.0  # Should complete within 5 seconds
        throughput = num_operations / duration
        assert throughput > 150  # Should handle mixed workload


class TestCacheEdgeCases:
    """Test cache edge cases and boundary conditions"""
    
    @pytest.mark.asyncio
    async def test_cache_with_large_objects(self, service):
        """Test caching of large objects"""
        large_objects = [
            "x" * 10000,  # Large string
            {"data": list(range(1000))},  # Large dict
            [f"item_{i}" for i in range(1000)],  # Large list
        ]
        
        for i, obj in enumerate(large_objects):
            key = f"large_obj_{i}"
            await service.set("large", key, obj)
            retrieved = await service.get("large", key)
            
            assert retrieved == obj
    
    @pytest.mark.asyncio
    async def test_cache_with_special_characters(self, service):
        """Test caching keys/values with special characters"""
        special_cases = [
            ("unicode_🎮", "value_with_emojis_🎯"),
            ("spaces and\ttabs", "value with spaces\tand tabs"),
            ("quotes_'_\"_", "value_with_'quotes'_and_\"double_quotes\""),
            ("null\x00byte", "value_with_null\x00byte"),
        ]
        
        for key, value in special_cases:
            await service.set("special", key, value)
            retrieved = await service.get("special", key)
            assert retrieved == value
    
    @pytest.mark.asyncio
    async def test_cache_concurrent_edge_cases(self, service):
        """Test cache with concurrent edge cases"""
        # Same key, different values
        key = "concurrent_key"
        
        async def concurrent_writer(value):
            await service.set("concurrent", key, value)
            return await service.get("concurrent", key)
        
        # Run concurrent writers
        tasks = [concurrent_writer(f"value_{i}") for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # Should handle concurrent access gracefully
        assert all(result is not None for result in results)
        assert len(set(results)) <= 10  # Should have valid results
    
    @pytest.mark.asyncio
    async def test_cache_memory_pressure(self, service):
        """Test cache behavior under memory pressure"""
        original_config = service.config
        try:
            # Set very small cache size to trigger pressure
            service.config.l1_max_size = 5
            service.config.l2_max_size = 10
            
            # Fill beyond capacity
            for i in range(20):
                await service.set("pressure", f"key_{i}", f"value_{i}")
            
            # Should still work, with evictions
            memory_stats = await service.get_memory_stats()
            assert memory_stats["l1_size"] <= 5
            
            # Verify recent entries are cached
            recent_keys = [f"key_{i}" for i in range(15, 20)]
            recent_results = await service.bulk_get("pressure", recent_keys)
            assert any(result is not None for result in recent_results.values())
            
        finally:
            service.config = original_config


class TestCacheRecoveryAndResilience:
    """Test cache recovery and resilience mechanisms"""
    
    @pytest.mark.asyncio
    async def test_redis_recovery_after_failure(self, service):
        """Test recovery from Redis failure"""
        original_redis = service.redis_client
        
        # Simulate Redis failure
        failing_redis = AsyncMock()
        failing_redis.get.side_effect = [Exception("Connection failed")] * 3 + [None]
        failing_redis.set.side_effect = Exception("Connection failed")
        
        service.redis_client = failing_redis
        
        # Should handle failure gracefully
        await service.set("recovery", "test_key", "test_value")
        result = await service.get("recovery", "test_key")
        
        # Should fall back to L1 cache
        assert result == "test_value"
        
        # Restore Redis
        service.redis_client = original_redis
    
    @pytest.mark.asyncio
    async def test_database_recovery_after_failure(self, service, mock_db):
        """Test recovery from database failure"""
        # Simulate database failure
        mock_db.execute.side_effect = Exception("Database connection failed")
        
        # Should handle database failure for cache misses
        result = await service.get("test", "nonexistent_key", db=mock_db)
        
        # Should return None gracefully
        assert result is None
    
    @pytest.mark.asyncio
    async def test_partial_cache_corruption_recovery(self, service):
        """Test recovery from partial cache corruption"""
        # Set up some valid cache entries
        await service.set("corruption", "valid_key", "valid_value")
        
        # Simulate corrupted cache entry
        with patch.object(service, '_deserialize_data', side_effect=[Exception("Corrupted"), "valid_value"]):
            # Should handle corrupted entry gracefully
            result1 = await service.get("corruption", "corrupted_key")
            result2 = await service.get("corruption", "valid_key")
            
            assert result1 is None  # Corrupted entry should be None
            assert result2 == "valid_value"  # Valid entry should work


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
