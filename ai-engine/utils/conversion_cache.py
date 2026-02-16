"""
Performance optimization utilities for conversion pipeline.

This module provides caching, parallel processing, and optimization utilities
to achieve <30s per conversion target.
"""

import hashlib
import json
import logging
import os
import pickle
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from functools import lru_cache, wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ConversionCache:
    """
    Persistent cache for conversion results to avoid repeated operations.
    
    Uses file-based caching with content hashing for invalidation.
    """
    
    def __init__(self, cache_dir: str = ".conversion_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache = {}
        self._stats = {'hits': 0, 'misses': 0, 'saves': 0}
    
    def _get_cache_key(self, data: Any) -> str:
        """Generate a cache key from data."""
        if isinstance(data, (str, bytes)):
            content = data if isinstance(data, bytes) else data.encode()
        else:
            content = json.dumps(data, sort_keys=True).encode()
        return hashlib.sha256(content).hexdigest()[:16]
    
    def _get_cache_path(self, key: str) -> Path:
        """Get the file path for a cache key."""
        return self.cache_dir / f"{key}.cache"
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        # Check memory cache first
        if key in self._memory_cache:
            self._stats['hits'] += 1
            return self._memory_cache[key]
        
        # Check disk cache
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            try:
                with open(cache_path, 'rb') as f:
                    value = pickle.load(f)
                self._memory_cache[key] = value
                self._stats['hits'] += 1
                return value
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
        
        self._stats['misses'] += 1
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Set a value in cache."""
        self._memory_cache[key] = value
        cache_path = self._get_cache_path(key)
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(value, f)
            self._stats['saves'] += 1
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
    
    def invalidate(self, key: str) -> None:
        """Invalidate a cache entry."""
        if key in self._memory_cache:
            del self._memory_cache[key]
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            cache_path.unlink()
    
    def clear(self) -> None:
        """Clear all caches."""
        self._memory_cache.clear()
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_file.unlink()
        self._stats = {'hits': 0, 'misses': 0, 'saves': 0}
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total = self._stats['hits'] + self._stats['misses']
        hit_rate = self._stats['hits'] / total if total > 0 else 0
        return {
            **self._stats,
            'total_requests': total,
            'hit_rate': round(hit_rate * 100, 2)
        }


# Global cache instance
_global_cache = ConversionCache()


def get_cache() -> ConversionCache:
    """Get the global cache instance."""
    return _global_cache


def cached(cache_key: Optional[str] = None, cache: Optional[ConversionCache] = None):
    """
    Decorator to cache function results.
    
    Args:
        cache_key: Optional function to generate cache key from args
        cache: Optional cache instance (uses global if not provided)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_instance = cache or _global_cache
            
            # Generate cache key
            if cache_key:
                key_data = cache_key(*args, **kwargs)
            else:
                key_data = f"{func.__name__}:{args}:{kwargs}"
            
            key = cache_instance._get_cache_key(key_data)
            
            # Try to get from cache
            cached_result = cache_instance.get(key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Compute result
            result = func(*args, **kwargs)
            
            # Store in cache
            cache_instance.set(key, result)
            logger.debug(f"Cache miss for {func.__name__}, computed and cached")
            
            return result
        return wrapper
    return decorator


class ParallelProcessor:
    """
    Process items in parallel for performance optimization.
    """
    
    def __init__(self, max_workers: int = 4, use_processes: bool = False):
        self.max_workers = max_workers
        self.use_processes = use_processes
    
    def map(self, func: Callable[[Any], Any], items: List[Any], 
            progress_callback: Optional[Callable[[int, int], None]] = None) -> List[Any]:
        """
        Process items in parallel.
        
        Args:
            func: Function to apply to each item
            items: List of items to process
            progress_callback: Optional callback(completed, total)
            
        Returns:
            List of results in same order as input
        """
        if not items:
            return []
        
        executor_class = ProcessPoolExecutor if self.use_processes else ThreadPoolExecutor
        
        results = [None] * len(items)
        completed = 0
        
        with executor_class(max_workers=self.max_workers) as executor:
            future_to_index = {executor.submit(func, item): i for i, item in enumerate(items)}
            
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    results[index] = future.result()
                except Exception as e:
                    logger.error(f"Error processing item {index}: {e}")
                    results[index] = {'error': str(e)}
                
                completed += 1
                if progress_callback:
                    progress_callback(completed, len(items))
        
        return results
    
    def map_with_timeout(self, func: Callable[[Any], Any], items: List[Any], 
                        timeout: float = 30.0) -> List[Any]:
        """Process items with timeout."""
        if not items:
            return []
        
        executor_class = ProcessPoolExecutor if self.use_processes else ThreadPoolExecutor
        
        results = [None] * len(items)
        
        with executor_class(max_workers=self.max_workers) as executor:
            future_to_index = {executor.submit(func, item): i for i, item in enumerate(items)}
            
            for future in as_completed(future_to_index, timeout=timeout):
                index = future_to_index[future]
                try:
                    results[index] = future.result()
                except Exception as e:
                    logger.error(f"Error processing item {index}: {e}")
                    results[index] = {'error': str(e)}
        
        return results


class PerformanceMonitor:
    """Monitor performance metrics for conversions."""
    
    def __init__(self):
        self._timings: Dict[str, List[float]] = {}
        self._start_times: Dict[str, float] = {}
    
    def start(self, operation: str) -> None:
        """Start timing an operation."""
        self._start_times[operation] = time.time()
    
    def end(self, operation: str) -> float:
        """End timing an operation and return duration."""
        if operation not in self._start_times:
            logger.warning(f"No start time for operation: {operation}")
            return 0.0
        
        duration = time.time() - self._start_times[operation]
        
        if operation not in self._timings:
            self._timings[operation] = []
        
        self._timings[operation].append(duration)
        del self._start_times[operation]
        
        return duration
    
    def get_stats(self, operation: str) -> Optional[Dict]:
        """Get statistics for an operation."""
        if operation not in self._timings or not self._timings[operation]:
            return None
        
        timings = self._timings[operation]
        return {
            'count': len(timings),
            'total': sum(timings),
            'mean': sum(timings) / len(timings),
            'min': min(timings),
            'max': max(timings),
            'last': timings[-1]
        }
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """Get statistics for all operations."""
        return {op: self.get_stats(op) for op in self._timings if self._timings[op]}
    
    def reset(self) -> None:
        """Reset all timings."""
        self._timings.clear()
        self._start_times.clear()


# Global performance monitor
_performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor."""
    return _performance_monitor


def timed(operation: str, monitor: Optional[PerformanceMonitor] = None):
    """Decorator to time function execution."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            perf_monitor = monitor or _performance_monitor
            perf_monitor.start(operation)
            try:
                return func(*args, **kwargs)
            finally:
                duration = perf_monitor.end(operation)
                logger.debug(f"{operation} completed in {duration:.3f}s")
        return wrapper
    return decorator


class ConversionOptimizer:
    """
    Main optimizer class for conversion pipeline.
    Combines caching, parallel processing, and performance monitoring.
    """
    
    def __init__(self, max_workers: int = 4):
        self.cache = get_cache()
        self.parallel = ParallelProcessor(max_workers=max_workers)
        self.monitor = get_performance_monitor()
    
    def optimize_conversion(self, convert_func: Callable, items: List[Any],
                           use_cache: bool = True, use_parallel: bool = True) -> List[Any]:
        """
        Optimize conversion of multiple items.
        
        Args:
            convert_func: Function to convert a single item
            items: List of items to convert
            use_cache: Whether to use caching
            use_parallel: Whether to use parallel processing
            
        Returns:
            List of converted items
        """
        if not items:
            return []
        
        if use_parallel and len(items) > 1:
            return self._parallel_convert(convert_func, items, use_cache)
        else:
            return self._sequential_convert(convert_func, items, use_cache)
    
    def _sequential_convert(self, convert_func: Callable, items: List[Any],
                          use_cache: bool) -> List[Any]:
        """Convert items sequentially with optional caching."""
        results = []
        for item in items:
            if use_cache:
                cache_key = self.cache._get_cache_key(str(item))
                cached = self.cache.get(cache_key)
                if cached is not None:
                    results.append(cached)
                    continue
            
            result = convert_func(item)
            if use_cache:
                self.cache.set(cache_key, result)
            results.append(result)
        
        return results
    
    def _parallel_convert(self, convert_func: Callable, items: List[Any],
                         use_cache: bool) -> List[Any]:
        """Convert items in parallel with caching."""
        # First pass: check cache
        results = [None] * len(items)
        uncached_indices = []
        uncached_items = []
        
        if use_cache:
            for i, item in enumerate(items):
                cache_key = self.cache._get_cache_key(str(item))
                cached = self.cache.get(cache_key)
                if cached is not None:
                    results[i] = cached
                else:
                    uncached_indices.append(i)
                    uncached_items.append((cache_key, item))
            
            # Convert uncached items
            if uncached_items:
                converted = self.parallel.map(
                    lambda x: convert_func(x[1]), 
                    uncached_items,
                    progress_callback=lambda c, t: logger.info(f"Conversion progress: {c}/{t}")
                )
                
                for (idx, (_, item)), result in zip(uncached_items, converted):
                    results[idx] = result
                    if use_cache:
                        cache_key = self.cache._get_cache_key(str(item))
                        self.cache.set(cache_key, result)
        else:
            results = self.parallel.map(convert_func, items)
        
        return results
    
    def get_optimization_report(self) -> Dict:
        """Get a report of optimization effectiveness."""
        return {
            'cache_stats': self.cache.get_stats(),
            'performance_stats': self.monitor.get_all_stats()
        }


def optimize_conversion_pipeline():
    """Factory function to create an optimized conversion pipeline."""
    return ConversionOptimizer()
