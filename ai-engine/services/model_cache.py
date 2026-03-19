"""
Model Cache Service for caching LLM and embedding models

Implements LRU caching with memory limits to avoid reloading models.
"""

import threading
import time
import logging
from typing import Dict, Any, Optional, Callable
from collections import OrderedDict
<<<<<<< HEAD
=======
import weakref
import gc

logger = logging.getLogger(__name__)


class ModelCacheStats:
    """Statistics for model cache performance tracking."""

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.loads = 0
        self.evictions = 0
        self.memory_bytes = 0

    def record_hit(self):
        self.hits += 1

    def record_miss(self):
        self.misses += 1

    def record_load(self, memory_bytes: int = 0):
        self.loads += 1
        self.memory_bytes += memory_bytes

    def record_eviction(self, memory_bytes: int = 0):
        self.evictions += 1
        self.memory_bytes -= memory_bytes

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "loads": self.loads,
            "evictions": self.evictions,
            "hit_rate": self.hit_rate,
            "memory_bytes": self.memory_bytes,
            "memory_mb": self.memory_bytes / (1024 * 1024),
        }


class ModelCache:
    """
    Thread-safe LRU cache for ML models with memory limits.

    Features:
    - LRU eviction policy
    - Memory limit enforcement
    - Thread-safe access
    - Performance statistics
    - Automatic cleanup
    """

    def __init__(
        self,
        max_models: int = 10,
        max_memory_mb: int = 4096,  # 4GB default limit
    ):
        """
        Initialize model cache.

        Args:
            max_models: Maximum number of models to cache
            max_memory_mb: Maximum memory usage in MB
        """
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._model_sizes: Dict[str, int] = {}  # model_name -> size in bytes
        self._lock = threading.RLock()
        self._max_models = max_models
        self._max_memory_bytes = max_memory_mb * 1024 * 1024
        self._stats = ModelCacheStats()

<<<<<<< HEAD
        logger.info(
            f"ModelCache initialized: max_models={max_models}, max_memory={max_memory_mb}MB"
        )
=======
        logger.info(f"ModelCache initialized: max_models={max_models}, max_memory={max_memory_mb}MB")

    def get(self, model_name: str) -> Optional[Any]:
        """
        Get model from cache.

        Args:
            model_name: Name of the model

        Returns:
            Model instance or None if not cached
        """
        with self._lock:
            if model_name in self._cache:
                # Move to end (most recently used)
                self._cache.move_to_end(model_name)
                self._stats.record_hit()
                logger.debug(f"Cache HIT for model: {model_name}")
                return self._cache[model_name]
            else:
                self._stats.record_miss()
                logger.debug(f"Cache MISS for model: {model_name}")
                return None

    def set(self, model_name: str, model: Any, memory_bytes: Optional[int] = None):
        """
        Add model to cache.

        Args:
            model_name: Name of the model
            model: Model instance to cache
            memory_bytes: Estimated memory usage (optional)
        """
        with self._lock:
            # If model already cached, update it
            if model_name in self._cache:
                old_size = self._model_sizes.get(model_name, 0)
                self._stats.record_eviction(old_size)
                del self._cache[model_name]
                del self._model_sizes[model_name]

            # Evict if necessary
            self._evict_if_needed(memory_bytes or 0)

            # Add to cache
            self._cache[model_name] = model
            self._model_sizes[model_name] = memory_bytes or 0
            self._stats.record_load(memory_bytes or 0)

<<<<<<< HEAD
            logger.info(f"Cached model: {model_name} ({(memory_bytes or 0) / (1024 * 1024):.1f}MB)")
=======
            logger.info(f"Cached model: {model_name} ({(memory_bytes or 0) / (1024*1024):.1f}MB)")

    def _evict_if_needed(self, new_model_bytes: int):
        """Evict models if cache is full or over memory limit."""
        while True:
            # Check model count limit
            if len(self._cache) >= self._max_models:
                self._evict_oldest()
                continue

            # Check memory limit
            current_memory = sum(self._model_sizes.values())
            if current_memory + new_model_bytes > self._max_memory_bytes:
                self._evict_oldest()
                continue

            break

    def _evict_oldest(self):
        """Evict the oldest (least recently used) model."""
        if not self._cache:
            return

        oldest_name = next(iter(self._cache))
        oldest_size = self._model_sizes.get(oldest_name, 0)

        logger.debug(f"Evicting oldest model: {oldest_name}")
        del self._cache[oldest_name]
        if oldest_name in self._model_sizes:
            del self._model_sizes[oldest_name]

        self._stats.record_eviction(oldest_size)

        # Force garbage collection after eviction
        gc.collect()

    def clear(self):
        """Clear all cached models."""
        with self._lock:
            self._cache.clear()
            self._model_sizes.clear()
            logger.info("Model cache cleared")
            gc.collect()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            stats = self._stats.to_dict()
            stats["cached_models"] = list(self._cache.keys())
            stats["model_count"] = len(self._cache)
            return stats

    def remove(self, model_name: str) -> bool:
        """
        Remove specific model from cache.

        Args:
            model_name: Name of model to remove

        Returns:
            True if removed, False if not found
        """
        with self._lock:
            if model_name in self._cache:
                size = self._model_sizes.get(model_name, 0)
                del self._cache[model_name]
                if model_name in self._model_sizes:
                    del self._model_sizes[model_name]
                self._stats.record_eviction(size)
                logger.info(f"Removed model from cache: {model_name}")
                return True
            return False


# Global model cache instance
_model_cache: Optional[ModelCache] = None
_cache_lock = threading.Lock()


def get_model_cache(max_models: int = 10, max_memory_mb: int = 4096) -> ModelCache:
    """
    Get or create global model cache instance.

    Args:
        max_models: Maximum models to cache
        max_memory_mb: Maximum memory in MB

    Returns:
        ModelCache instance
    """
    global _model_cache

    with _cache_lock:
        if _model_cache is None:
            _model_cache = ModelCache(max_models=max_models, max_memory_mb=max_memory_mb)
        return _model_cache


def cached_model(model_name: str, loader: Callable[[], Any], memory_bytes: Optional[int] = None):
    """
    Decorator for caching model instances.

    Usage:
        @cached_model("my-model", loader=my_loader_func)
        def get_model():
            return my_loader_func()

    Args:
        model_name: Unique name for the model
        loader: Function to load model if not cached
        memory_bytes: Estimated model size in bytes

    Returns:
        Decorated function
    """
<<<<<<< HEAD

=======
    def decorator(func: Callable[[], Any]) -> Callable[[], Any]:
        @wraps(func)
        def wrapper() -> Any:
            cache = get_model_cache()

            # Try to get from cache
            model = cache.get(model_name)
            if model is not None:
                return model

            # Load and cache
            logger.info(f"Loading model: {model_name}")
            model = loader()
            cache.set(model_name, model, memory_bytes)

            return model

        return wrapper
<<<<<<< HEAD

=======
    return decorator


class LLModelCache(ModelCache):
    """
    Specialized cache for LLM models with additional features.

    Features:
    - Model health checking
    - Automatic refresh
    - Usage tracking
    """

    def __init__(self, max_models: int = 5, max_memory_mb: int = 2048):
        super().__init__(max_models=max_models, max_memory_mb=max_memory_mb)
        self._model_health: Dict[str, float] = {}  # model_name -> last successful use
        self._model_usage: Dict[str, int] = {}  # model_name -> usage count

    def get(self, model_name: str) -> Optional[Any]:
        """Get model and update usage stats."""
        model = super().get(model_name)
        if model is not None:
            self._model_health[model_name] = time.time()
            self._model_usage[model_name] = self._model_usage.get(model_name, 0) + 1
        return model

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get detailed usage statistics."""
        stats = self.get_stats()
        stats["model_health"] = self._model_health
        stats["model_usage"] = self._model_usage
        return stats


# Singleton instances
_llm_cache: Optional[LLModelCache] = None
_embedding_cache: Optional[ModelCache] = None


def get_llm_cache() -> LLModelCache:
    """Get LLM model cache singleton."""
    global _llm_cache
    if _llm_cache is None:
        _llm_cache = LLModelCache(max_models=5, max_memory_mb=2048)
    return _llm_cache


def get_embedding_cache() -> ModelCache:
    """Get embedding model cache singleton."""
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = ModelCache(max_models=3, max_memory_mb=1024)
    return _embedding_cache
