
import pytest
import time
import shutil
import os
from pathlib import Path
from utils.conversion_cache import (
    ConversionCache, 
    ParallelProcessor, 
    PerformanceMonitor, 
    ConversionOptimizer,
    cached,
    timed
)

@pytest.fixture
def cache_dir():
    dir_path = ".test_conversion_cache"
    yield dir_path
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)

class TestConversionCache:
    def test_cache_set_get(self, cache_dir):
        cache = ConversionCache(cache_dir=cache_dir)
        key = "test_key"
        value = {"result": "success"}
        
        cache.set(key, value)
        assert cache.get(key) == value
        
        # Test persistence
        cache2 = ConversionCache(cache_dir=cache_dir)
        assert cache2.get(key) == value

    def test_cache_key_generation(self, cache_dir):
        cache = ConversionCache(cache_dir=cache_dir)
        data1 = {"a": 1, "b": 2}
        data2 = {"b": 2, "a": 1}
        
        key1 = cache._get_cache_key(data1)
        key2 = cache._get_cache_key(data2)
        
        assert key1 == key2
        assert len(key1) == 16

    def test_cache_invalidate(self, cache_dir):
        cache = ConversionCache(cache_dir=cache_dir)
        key = "to_be_deleted"
        cache.set(key, "value")
        assert cache.get(key) == "value"
        
        cache.invalidate(key)
        assert cache.get(key) is None

    def test_cache_clear(self, cache_dir):
        cache = ConversionCache(cache_dir=cache_dir)
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        
        cache.clear()
        assert cache.get("k1") is None
        assert cache.get("k2") is None
        assert cache.get_stats()["hits"] == 0

    def test_cached_decorator(self, cache_dir):
        cache = ConversionCache(cache_dir=cache_dir)
        
        call_count = 0
        @cached(cache=cache)
        def expensive_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2
            
        assert expensive_func(5) == 10
        assert expensive_func(5) == 10
        assert call_count == 1

class TestParallelProcessor:
    def test_parallel_map(self):
        processor = ParallelProcessor(max_workers=2)
        items = [1, 2, 3, 4]
        
        def square(x):
            return x * x
            
        results = processor.map(square, items)
        assert results == [1, 4, 9, 16]

    def test_parallel_map_empty(self):
        processor = ParallelProcessor()
        assert processor.map(lambda x: x, []) == []

class TestPerformanceMonitor:
    def test_monitor_start_end(self):
        monitor = PerformanceMonitor()
        monitor.start("op1")
        time.sleep(0.01)
        duration = monitor.end("op1")
        
        assert duration >= 0.01
        stats = monitor.get_stats("op1")
        assert stats["count"] == 1
        assert stats["mean"] >= 0.01

    def test_monitor_no_start(self):
        monitor = PerformanceMonitor()
        assert monitor.end("unknown") == 0.0
        assert monitor.get_stats("unknown") is None

    def test_timed_decorator(self):
        monitor = PerformanceMonitor()
        
        @timed("test_op", monitor=monitor)
        def func():
            time.sleep(0.01)
            return True
            
        assert func() is True
        assert monitor.get_stats("test_op")["count"] == 1

class TestConversionOptimizer:
    def test_optimize_conversion_sequential(self, cache_dir):
        optimizer = ConversionOptimizer()
        optimizer.cache = ConversionCache(cache_dir=cache_dir)
        
        def convert(x):
            return x.upper()
            
        items = ["a", "b", "c"]
        results = optimizer.optimize_conversion(convert, items, use_parallel=False)
        assert results == ["A", "B", "C"]
        assert optimizer.cache.get_stats()["saves"] == 3

    def test_optimize_conversion_parallel(self, cache_dir):
        optimizer = ConversionOptimizer(max_workers=2)
        optimizer.cache = ConversionCache(cache_dir=cache_dir)
        
        def convert(x):
            return x.upper()
            
        items = ["x", "y", "z"]
        results = optimizer.optimize_conversion(convert, items, use_parallel=True)
        assert results == ["X", "Y", "Z"]
        # In parallel mode, it checks cache first then saves back
        assert optimizer.cache.get_stats()["saves"] == 3
