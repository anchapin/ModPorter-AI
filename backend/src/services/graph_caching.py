"""
Graph Caching Service for Performance Optimization

This service provides advanced caching strategies for knowledge graph data,
including multi-level caching, cache invalidation, and performance monitoring.
"""

import logging
import json
import pickle
import hashlib
import time
import threading
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, OrderedDict
from functools import wraps
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.knowledge_graph_crud import (
    KnowledgeNodeCRUD, KnowledgeRelationshipCRUD, ConversionPatternCRUD
)

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """Cache levels in the hierarchy."""
    L1_MEMORY = "l1_memory"
    L2_REDIS = "l2_redis"
    L3_DATABASE = "l3_database"


class CacheStrategy(Enum):
    """Caching strategies."""
    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"
    TTL = "ttl"
    WRITE_THROUGH = "write_through"
    WRITE_BEHIND = "write_behind"
    REFRESH_AHEAD = "refresh_ahead"


class CacheInvalidationStrategy(Enum):
    """Cache invalidation strategies."""
    TIME_BASED = "time_based"
    EVENT_DRIVEN = "event_driven"
    MANUAL = "manual"
    PROACTIVE = "proactive"
    ADAPTIVE = "adaptive"


@dataclass
class CacheEntry:
    """Entry in cache."""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    size_bytes: int = 0
    ttl_seconds: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheStats:
    """Statistics for cache performance."""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    avg_access_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    hit_ratio: float = 0.0


@dataclass
class CacheConfig:
    """Configuration for cache."""
    max_size_mb: float = 100.0
    max_entries: int = 10000
    ttl_seconds: Optional[int] = None
    strategy: CacheStrategy = CacheStrategy.LRU
    invalidation_strategy: CacheInvalidationStrategy = CacheInvalidationStrategy.TIME_BASED
    refresh_interval_seconds: int = 300
    enable_compression: bool = True
    enable_serialization: bool = True


class LRUCache:
    """LRU (Least Recently Used) cache implementation."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: OrderedDict = OrderedDict()
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                value = self.cache.pop(key)
                self.cache[key] = value
                return value
            return None
    
    def put(self, key: str, value: Any):
        with self.lock:
            if key in self.cache:
                # Remove and re-add to update order
                self.cache.pop(key)
            elif len(self.cache) >= self.max_size:
                # Remove least recently used
                self.cache.popitem(last=False)
            
            self.cache[key] = value
    
    def remove(self, key: str) -> bool:
        with self.lock:
            if key in self.cache:
                self.cache.pop(key)
                return True
            return False
    
    def clear(self):
        with self.lock:
            self.cache.clear()
    
    def size(self) -> int:
        with self.lock:
            return len(self.cache)
    
    def keys(self) -> List[str]:
        with self.lock:
            return list(self.cache.keys())


class LFUCache:
    """LFU (Least Frequently Used) cache implementation."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: Dict[str, Any] = {}
        self.frequencies: Dict[str, int] = defaultdict(int)
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            if key in self.cache:
                self.frequencies[key] += 1
                return self.cache[key]
            return None
    
    def put(self, key: str, value: Any):
        with self.lock:
            if key in self.cache:
                # Update value
                self.cache[key] = value
                self.frequencies[key] += 1
            else:
                # Add new value
                if len(self.cache) >= self.max_size:
                    # Remove least frequently used
                    lfu_key = min(self.frequencies.keys(), key=lambda k: self.frequencies[k])
                    self.cache.pop(lfu_key)
                    self.frequencies.pop(lfu_key)
                
                self.cache[key] = value
                self.frequencies[key] = 1
    
    def remove(self, key: str) -> bool:
        with self.lock:
            if key in self.cache:
                self.cache.pop(key)
                self.frequencies.pop(key)
                return True
            return False
    
    def clear(self):
        with self.lock:
            self.cache.clear()
            self.frequencies.clear()
    
    def size(self) -> int:
        with self.lock:
            return len(self.cache)
    
    def keys(self) -> List[str]:
        with self.lock:
            return list(self.cache.keys())


class GraphCachingService:
    """Advanced caching service for knowledge graph performance."""
    
    def __init__(self):
        self.l1_cache: Dict[str, CacheEntry] = {}
        self.l2_cache: LRUCache(10000)  # For larger data sets
        self.l3_cache: Dict[str, Any] = {}  # Fallback to memory
        
        self.cache_stats: Dict[str, CacheStats] = {
            "l1_memory": CacheStats(),
            "l2_redis": CacheStats(),
            "l3_database": CacheStats(),
            "overall": CacheStats()
        }
        
        self.cache_configs: Dict[str, CacheConfig] = {
            "nodes": CacheConfig(max_size_mb=50.0, ttl_seconds=600),
            "relationships": CacheConfig(max_size_mb=30.0, ttl_seconds=600),
            "patterns": CacheConfig(max_size_mb=20.0, ttl_seconds=900),
            "queries": CacheConfig(max_size_mb=10.0, ttl_seconds=300),
            "layouts": CacheConfig(max_size_mb=40.0, ttl_seconds=1800),
            "clusters": CacheConfig(max_size_mb=15.0, ttl_seconds=1200)
        }
        
        self.cache_invalidations: Dict[str, List[datetime]] = defaultdict(list)
        self.cache_dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.performance_history: List[Dict[str, Any]] = []
        
        self.lock = threading.RLock()
        self.cleanup_thread: Optional[threading.Thread] = None
        self.stop_cleanup = False
        
        # Start cleanup thread
        self._start_cleanup_thread()
    
    def cache(self, cache_type: str = "default", ttl: Optional[int] = None, 
              size_limit: Optional[int] = None, strategy: CacheStrategy = CacheStrategy.LRU):
        """
        Decorator for caching function results.
        
        Args:
            cache_type: Type of cache to use
            ttl: Time to live in seconds
            size_limit: Maximum size of cache
            strategy: Caching strategy to use
        
        Returns:
            Decorated function with caching
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self._generate_cache_key(func, args, kwargs)
                
                # Check cache first
                cached_result = await self.get(cache_type, cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Execute function
                start_time = time.time()
                result = await func(*args, **kwargs)
                execution_time = (time.time() - start_time) * 1000
                
                # Cache the result
                await self.set(cache_type, cache_key, result, ttl)
                
                # Log performance
                self._log_cache_operation(cache_type, "set", execution_time, len(str(result)))
                
                return result
            return wrapper
        return decorator
    
    async def get(self, cache_type: str, key: str) -> Optional[Any]:
        """
        Get value from cache, checking all levels.
        
        Args:
            cache_type: Type of cache to check
            key: Cache key
        
        Returns:
            Cached value or None if not found
        """
        try:
            start_time = time.time()
            
            with self.lock:
                # Check L1 cache (memory)
                if cache_type in self.l1_cache and key in self.l1_cache[cache_type]:
                    entry = self.l1_cache[cache_type][key]
                    
                    # Check TTL
                    if self._is_entry_valid(entry):
                        entry.last_accessed = datetime.utcnow()
                        entry.access_count += 1
                        
                        access_time = (time.time() - start_time) * 1000
                        self._update_cache_stats(cache_type, "hit", access_time)
                        return entry.value
                    else:
                        # Remove expired entry
                        del self.l1_cache[cache_type][key]
                        self._update_cache_stats(cache_type, "miss", 0)
                
                # Check L2 cache (LRU cache for larger data)
                if cache_type in ["relationships", "patterns", "layouts"]:
                    l2_result = self.l2_cache.get(f"{cache_type}:{key}")
                    if l2_result is not None:
                        access_time = (time.time() - start_time) * 1000
                        self._update_cache_stats("l2_redis", "hit", access_time)
                        
                        # Promote to L1 cache
                        await self.set(cache_type, key, l2_result)
                        return l2_result
                
                # Cache miss
                self._update_cache_stats(cache_type, "miss", 0)
                return None
                
        except Exception as e:
            logger.error(f"Error getting from cache: {e}")
            self._update_cache_stats(cache_type, "miss", 0)
            return None
    
    async def set(self, cache_type: str, key: str, value: Any, 
                  ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.
        
        Args:
            cache_type: Type of cache to set
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        
        Returns:
            True if successful, False otherwise
        """
        try:
            start_time = time.time()
            
            with self.lock:
                # Get configuration
                config = self.cache_configs.get(cache_type, CacheConfig())
                actual_ttl = ttl or config.ttl_seconds
                
                # Calculate size
                if config.enable_serialization:
                    serialized = self._serialize_value(value, config.enable_compression)
                    size_bytes = len(serialized)
                else:
                    size_bytes = len(str(value))
                
                # Check size limits
                if size_bytes > config.max_size_mb * 1024 * 1024:
                    logger.warning(f"Cache entry too large: {size_bytes} bytes")
                    return False
                
                # Create cache entry
                entry = CacheEntry(
                    key=key,
                    value=value,
                    created_at=datetime.utcnow(),
                    last_accessed=datetime.utcnow(),
                    size_bytes=size_bytes,
                    ttl_seconds=actual_ttl,
                    metadata={"cache_type": cache_type, "original_size": len(str(value))}
                )
                
                # Check if we need to evict entries
                current_size = sum(
                    e.size_bytes for e in self.l1_cache.get(cache_type, {}).values()
                )
                max_size = config.max_size_mb * 1024 * 1024
                
                if current_size + size_bytes > max_size:
                    await self._evict_entries(cache_type, size_bytes)
                
                # Store in L1 cache
                if cache_type not in self.l1_cache:
                    self.l1_cache[cache_type] = {}
                
                self.l1_cache[cache_type][key] = entry
                
                # Also store in L2 cache for larger data types
                if cache_type in ["relationships", "patterns", "layouts"]:
                    self.l2_cache.put(f"{cache_type}:{key}", value)
                
                # Update dependencies
                await self._update_cache_dependencies(cache_type, key)
                
                access_time = (time.time() - start_time) * 1000
                self._update_cache_stats(cache_type, "set", access_time)
                
                return True
                
        except Exception as e:
            logger.error(f"Error setting in cache: {e}")
            return False
    
    async def invalidate(self, cache_type: Optional[str] = None, 
                       pattern: Optional[str] = None, 
                       cascade: bool = True) -> int:
        """
        Invalidate cache entries.
        
        Args:
            cache_type: Type of cache to invalidate (None for all)
            pattern: Pattern to match keys (None for all)
            cascade: Whether to cascade invalidation to dependent caches
        
        Returns:
            Number of entries invalidated
        """
        try:
            invalidated_count = 0
            start_time = time.time()
            
            with self.lock:
                cache_types = [cache_type] if cache_type else list(self.l1_cache.keys())
                
                for ct in cache_types:
                    if ct not in self.l1_cache:
                        continue
                    
                    keys_to_remove = []
                    
                    for key in self.l1_cache[ct]:
                        if pattern is None or pattern in key:
                            keys_to_remove.append(key)
                    
                    # Remove entries
                    for key in keys_to_remove:
                        del self.l1_cache[ct][key]
                        invalidated_count += 1
                    
                    # Also remove from L2 cache
                    if ct in ["relationships", "patterns", "layouts"]:
                        for key in keys_to_remove:
                            self.l2_cache.remove(f"{ct}:{key}")
                    
                    # Record invalidation
                    self.cache_invalidations[ct].append(datetime.utcnow())
                    
                    # Cascade to dependent caches
                    if cascade:
                        await self._cascade_invalidation(ct, keys_to_remove)
            
            # Log invalidation
            self._log_cache_operation(
                "invalidation", "invalidate", 
                (time.time() - start_time) * 1000, invalidated_count
            )
            
            return invalidated_count
            
        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
            return 0
    
    async def warm_up(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Warm up cache with frequently accessed data.
        
        Args:
            db: Database session
        
        Returns:
            Warm-up results
        """
        try:
            start_time = time.time()
            warm_up_results = {}
            
            # Warm up nodes cache
            nodes_start = time.time()
            nodes = await KnowledgeNodeCRUD.get_all(db, limit=1000)
            for node in nodes:
                await self.set("nodes", f"node:{node.id}", {
                    "id": str(node.id),
                    "name": node.name,
                    "node_type": node.node_type,
                    "platform": node.platform,
                    "properties": json.loads(node.properties or "{}")
                }, ttl=600)
            warm_up_results["nodes"] = {
                "count": len(nodes),
                "time_ms": (time.time() - nodes_start) * 1000
            }
            
            # Warm up relationships cache
            rels_start = time.time()
            relationships = await KnowledgeRelationshipCRUD.get_all(db, limit=2000)
            for rel in relationships:
                await self.set("relationships", f"rel:{rel.id}", {
                    "id": str(rel.id),
                    "source_id": rel.source_node_id,
                    "target_id": rel.target_node_id,
                    "type": rel.relationship_type,
                    "confidence_score": rel.confidence_score
                }, ttl=600)
            warm_up_results["relationships"] = {
                "count": len(relationships),
                "time_ms": (time.time() - rels_start) * 1000
            }
            
            # Warm up patterns cache
            patterns_start = time.time()
            patterns = await ConversionPatternCRUD.get_all(db, limit=500)
            for pattern in patterns:
                await self.set("patterns", f"pattern:{pattern.id}", {
                    "id": str(pattern.id),
                    "java_concept": pattern.java_concept,
                    "bedrock_concept": pattern.bedrock_concept,
                    "pattern_type": pattern.pattern_type,
                    "success_rate": pattern.success_rate
                }, ttl=900)
            warm_up_results["patterns"] = {
                "count": len(patterns),
                "time_ms": (time.time() - patterns_start) * 1000
            }
            
            total_time = (time.time() - start_time) * 1000
            warm_up_results["summary"] = {
                "total_time_ms": total_time,
                "total_items_cached": len(nodes) + len(relationships) + len(patterns),
                "cache_levels_warmed": ["l1_memory", "l2_redis"]
            }
            
            return {
                "success": True,
                "warm_up_results": warm_up_results,
                "message": "Cache warm-up completed successfully"
            }
            
        except Exception as e:
            logger.error(f"Error warming up cache: {e}")
            return {
                "success": False,
                "error": f"Cache warm-up failed: {str(e)}"
            }
    
    async def get_cache_stats(self, cache_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get cache performance statistics.
        
        Args:
            cache_type: Type of cache to get stats for (None for all)
        
        Returns:
            Cache statistics
        """
        try:
            with self.lock:
                if cache_type:
                    stats = self.cache_stats.get(cache_type, CacheStats())
                    return {
                        "cache_type": cache_type,
                        "hits": stats.hits,
                        "misses": stats.misses,
                        "sets": stats.sets,
                        "deletes": stats.deletes,
                        "evictions": stats.evictions,
                        "total_size_bytes": stats.total_size_bytes,
                        "hit_ratio": stats.hit_ratio,
                        "avg_access_time_ms": stats.avg_access_time_ms,
                        "memory_usage_mb": stats.memory_usage_mb
                    }
                else:
                    all_stats = {}
                    for ct, stats in self.cache_stats.items():
                        all_stats[ct] = {
                            "hits": stats.hits,
                            "misses": stats.misses,
                            "sets": stats.sets,
                            "deletes": stats.deletes,
                            "evictions": stats.evictions,
                            "total_size_bytes": stats.total_size_bytes,
                            "hit_ratio": stats.hit_ratio,
                            "avg_access_time_ms": stats.avg_access_time_ms,
                            "memory_usage_mb": stats.memory_usage_mb
                        }
                    
                    return {
                        "cache_types": list(self.cache_stats.keys()),
                        "stats": all_stats,
                        "overall_stats": self._calculate_overall_stats()
                    }
                    
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"error": str(e)}
    
    async def optimize_cache(self, strategy: str = "adaptive") -> Dict[str, Any]:
        """
        Optimize cache performance.
        
        Args:
            strategy: Optimization strategy
        
        Returns:
            Optimization results
        """
        try:
            start_time = time.time()
            optimization_results = {}
            
            if strategy == "adaptive":
                # Analyze performance and adjust configurations
                for cache_type, stats in self.cache_stats.items():
                    if cache_type == "overall":
                        continue
                    
                    # Get current configuration
                    config = self.cache_configs.get(cache_type, CacheConfig())
                    
                    # Optimize based on hit ratio
                    if stats.hit_ratio < 0.7:
                        # Increase cache size
                        config.max_size_mb *= 1.2
                        config.max_entries = int(config.max_entries * 1.2)
                    elif stats.hit_ratio > 0.95:
                        # Decrease cache size
                        config.max_size_mb *= 0.9
                        config.max_entries = int(config.max_entries * 0.9)
                    
                    # Optimize TTL based on access patterns
                    if stats.misses > stats.hits:
                        config.ttl_seconds = min(config.ttl_seconds * 1.5, 3600)
                    else:
                        config.ttl_seconds = max(config.ttl_seconds * 0.8, 60)
                    
                    self.cache_configs[cache_type] = config
                    optimization_results[cache_type] = {
                        "old_size_mb": config.max_size_mb / 1.2,
                        "new_size_mb": config.max_size_mb,
                        "old_ttl": config.ttl_seconds / 1.5,
                        "new_ttl": config.ttl_seconds
                    }
            
            elif strategy == "eviction":
                # Force eviction of old entries
                for cache_type in self.l1_cache.keys():
                    evicted = await self._evict_expired_entries(cache_type)
                    optimization_results[cache_type] = {
                        "evicted_entries": evicted
                    }
            
            elif strategy == "rebalance":
                # Rebalance cache distribution
                total_memory = sum(
                    sum(e.size_bytes for e in cache.values())
                    for cache in self.l1_cache.values()
                )
                optimal_memory_per_cache = 100 * 1024 * 1024 / len(self.l1_cache)  # 100MB total
                
                for cache_type, cache_data in self.l1_cache.items():
                    current_memory = sum(e.size_bytes for e in cache_data.values())
                    
                    if current_memory > optimal_memory_per_cache:
                        # Evict excess entries
                        excess_bytes = current_memory - optimal_memory_per_cache
                        evicted = await self._evict_entries(cache_type, excess_bytes)
                        optimization_results[cache_type] = {
                            "evicted_bytes": excess_bytes,
                            "evicted_entries": evicted
                        }
            
            optimization_time = (time.time() - start_time) * 1000
            optimization_results["summary"] = {
                "strategy": strategy,
                "time_ms": optimization_time,
                "cache_types_optimized": list(optimization_results.keys()) if optimization_results != {"summary": {}} else []
            }
            
            return {
                "success": True,
                "optimization_results": optimization_results,
                "message": "Cache optimization completed successfully"
            }
            
        except Exception as e:
            logger.error(f"Error optimizing cache: {e}")
            return {
                "success": False,
                "error": f"Cache optimization failed: {str(e)}"
            }
    
    # Private Helper Methods
    
    def _generate_cache_key(self, func: Any, args: Tuple, kwargs: Dict) -> str:
        """Generate cache key from function arguments."""
        try:
            # Create a deterministic string representation
            key_parts = [
                func.__name__,
                str(args),
                str(sorted(kwargs.items())),
                str(id(func))
            ]
            
            key_string = "|".join(key_parts)
            return hashlib.md5(key_string.encode()).hexdigest()
            
        except Exception:
            # Fallback to simple key
            return f"{func.__name__}_{hash(str(args) + str(kwargs))}"
    
    def _is_entry_valid(self, entry: CacheEntry) -> bool:
        """Check if cache entry is still valid."""
        try:
            # Check TTL
            if entry.ttl_seconds:
                elapsed = (datetime.utcnow() - entry.created_at).total_seconds()
                if elapsed > entry.ttl_seconds:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _serialize_value(self, value: Any, compress: bool = True) -> bytes:
        """Serialize value for caching."""
        try:
            if compress:
                # Use pickle with compression
                serialized = pickle.dumps(value)
                return serialized
            else:
                # Use pickle without compression
                serialized = pickle.dumps(value)
                return serialized
                
        except Exception:
            # Fallback to string
            return str(value).encode()
    
    def _deserialize_value(self, serialized: bytes, compressed: bool = True) -> Any:
        """Deserialize value from cache."""
        try:
            if compressed:
                return pickle.loads(serialized)
            else:
                return pickle.loads(serialized)
                
        except Exception:
            # Fallback to string
            return serialized.decode()
    
    async def _evict_entries(self, cache_type: str, size_to_free: int) -> int:
        """Evict entries to free up space."""
        try:
            if cache_type not in self.l1_cache:
                return 0
            
            cache = self.l1_cache[cache_type]
            config = self.cache_configs.get(cache_type, CacheConfig())
            
            if config.strategy == CacheStrategy.LRU:
                # Sort by last accessed time
                entries_sorted = sorted(
                    cache.items(),
                    key=lambda x: x[1].last_accessed
                )
            elif config.strategy == CacheStrategy.LFU:
                # Sort by access frequency
                entries_sorted = sorted(
                    cache.items(),
                    key=lambda x: x[1].access_count
                )
            else:
                # Default to LRU
                entries_sorted = sorted(
                    cache.items(),
                    key=lambda x: x[1].last_accessed
                )
            
            evicted_count = 0
            freed_bytes = 0
            
            for key, entry in entries_sorted:
                if freed_bytes >= size_to_free:
                    break
                
                del cache[key]
                freed_bytes += entry.size_bytes
                evicted_count += 1
                self.cache_stats[cache_type].evictions += 1
                
                # Also remove from L2 cache
                if cache_type in ["relationships", "patterns", "layouts"]:
                    self.l2_cache.remove(f"{cache_type}:{key}")
            
            return evicted_count
            
        except Exception as e:
            logger.error(f"Error evicting cache entries: {e}")
            return 0
    
    async def _evict_expired_entries(self, cache_type: str) -> int:
        """Evict expired entries from cache."""
        try:
            if cache_type not in self.l1_cache:
                return 0
            
            cache = self.l1_cache[cache_type]
            current_time = datetime.utcnow()
            evicted_count = 0
            
            expired_keys = []
            for key, entry in cache.items():
                if entry.ttl_seconds:
                    elapsed = (current_time - entry.created_at).total_seconds()
                    if elapsed > entry.ttl_seconds:
                        expired_keys.append(key)
            
            for key in expired_keys:
                del cache[key]
                evicted_count += 1
                self.cache_stats[cache_type].evictions += 1
                
                # Also remove from L2 cache
                if cache_type in ["relationships", "patterns", "layouts"]:
                    self.l2_cache.remove(f"{cache_type}:{key}")
            
            return evicted_count
            
        except Exception as e:
            logger.error(f"Error evicting expired entries: {e}")
            return 0
    
    async def _update_cache_dependencies(self, cache_type: str, key: str):
        """Update cache dependency tracking."""
        try:
            # This would track which cache entries depend on others
            # For now, implement simple dependency tracking
            pass
        except Exception as e:
            logger.error(f"Error updating cache dependencies: {e}")
    
    async def _cascade_invalidation(self, cache_type: str, keys: List[str]):
        """Cascade invalidation to dependent caches."""
        try:
            # This would invalidate dependent cache entries
            # For now, implement simple cascading
            pass
        except Exception as e:
            logger.error(f"Error in cascade invalidation: {e}")
    
    def _update_cache_stats(self, cache_type: str, operation: str, 
                           access_time: float, size: int = 0):
        """Update cache statistics."""
        try:
            stats = self.cache_stats.get(cache_type, CacheStats())
            overall_stats = self.cache_stats["overall"]
            
            if operation == "hit":
                stats.hits += 1
                overall_stats.hits += 1
            elif operation == "miss":
                stats.misses += 1
                overall_stats.misses += 1
            elif operation == "set":
                stats.sets += 1
                overall_stats.sets += 1
                stats.total_size_bytes += size
                overall_stats.total_size_bytes += size
            elif operation == "delete":
                stats.deletes += 1
                overall_stats.deletes += 1
            
            # Update average access time
            if stats.hits > 0:
                stats.avg_access_time_ms = (
                    (stats.avg_access_time_ms * (stats.hits - 1) + access_time) / stats.hits
                )
            
            if overall_stats.hits > 0:
                overall_stats.avg_access_time_ms = (
                    (overall_stats.avg_access_time_ms * (overall_stats.hits - 1) + access_time) / overall_stats.hits
                )
            
            # Calculate hit ratio
            total_requests = stats.hits + stats.misses
            stats.hit_ratio = stats.hits / total_requests if total_requests > 0 else 0
            
            overall_total = overall_stats.hits + overall_stats.misses
            overall_stats.hit_ratio = overall_stats.hits / overall_total if overall_total > 0 else 0
            
            # Update memory usage
            stats.memory_usage_mb = stats.total_size_bytes / (1024 * 1024)
            overall_stats.memory_usage_mb = overall_stats.total_size_bytes / (1024 * 1024)
            
            self.cache_stats[cache_type] = stats
            self.cache_stats["overall"] = overall_stats
            
        except Exception as e:
            logger.error(f"Error updating cache stats: {e}")
    
    def _log_cache_operation(self, cache_type: str, operation: str, 
                           access_time: float, size: int):
        """Log cache operation for performance monitoring."""
        try:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "cache_type": cache_type,
                "operation": operation,
                "access_time_ms": access_time,
                "size_bytes": size
            }
            
            self.performance_history.append(log_entry)
            
            # Keep only last 10000 entries
            if len(self.performance_history) > 10000:
                self.performance_history = self.performance_history[-5000:]
                
        except Exception as e:
            logger.error(f"Error logging cache operation: {e}")
    
    def _calculate_overall_stats(self) -> Dict[str, Any]:
        """Calculate overall cache statistics."""
        try:
            overall = self.cache_stats.get("overall", CacheStats())
            
            return {
                "total_hits": overall.hits,
                "total_misses": overall.misses,
                "total_sets": overall.sets,
                "total_deletes": overall.deletes,
                "total_evictions": overall.evictions,
                "total_size_bytes": overall.total_size_bytes,
                "hit_ratio": overall.hit_ratio,
                "avg_access_time_ms": overall.avg_access_time_ms,
                "memory_usage_mb": overall.memory_usage_mb,
                "cache_levels_active": len([ct for ct in self.cache_stats.keys() if ct != "overall"])
            }
            
        except Exception as e:
            logger.error(f"Error calculating overall stats: {e}")
            return {}
    
    def _start_cleanup_thread(self):
        """Start background cleanup thread."""
        try:
            def cleanup_task():
                while not self.stop_cleanup:
                    try:
                        # Evict expired entries
                        for cache_type in list(self.l1_cache.keys()):
                            self._evict_expired_entries(cache_type)
                        
                        # Sleep for cleanup interval
                        time.sleep(60)  # 1 minute
                        
                    except Exception as e:
                        logger.error(f"Error in cleanup task: {e}")
                        time.sleep(60)
            
            self.cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
            self.cleanup_thread.start()
            
        except Exception as e:
            logger.error(f"Error starting cleanup thread: {e}")
    
    def _estimate_memory_usage(self) -> float:
        """Estimate current memory usage in MB."""
        try:
            total_bytes = 0
            
            for cache_type, cache_data in self.l1_cache.items():
                for entry in cache_data.values():
                    total_bytes += entry.size_bytes
            
            return total_bytes / (1024 * 1024)
            
        except Exception:
            return 0.0
    
    def _calculate_cache_hit_ratio(self) -> float:
        """Calculate overall cache hit ratio."""
        try:
            overall = self.cache_stats.get("overall", CacheStats())
            if overall.hits + overall.misses == 0:
                return 0.0
            return overall.hits / (overall.hits + overall.misses)
            
        except Exception:
            return 0.0


# Singleton instance
graph_caching_service = GraphCachingService()
