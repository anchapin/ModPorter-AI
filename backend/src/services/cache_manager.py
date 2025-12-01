"""
Cache Manager Service

This module provides a high-level interface for cache operations,
wrapping the low-level CacheService and adding management capabilities.
"""

import logging
from typing import Dict, Any, Optional
from .cache import CacheService

logger = logging.getLogger(__name__)


class CacheManager:
    """
    High-level cache management service.
    Wraps CacheService and provides additional management methods.
    """

    def __init__(self):
        self.cache_service = CacheService()
        self.emergency_mode = False

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            stats = await self.cache_service.get_cache_stats()
            return {
                "hits": stats.hits,
                "misses": stats.misses,
                "current_items": stats.current_items,
                "total_size_bytes": stats.total_size_bytes,
                "hit_rate": stats.hits / (stats.hits + stats.misses)
                if (stats.hits + stats.misses) > 0
                else 0.0,
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}

    async def emergency_increase_cache_size(self) -> None:
        """
        Emergency action to increase cache size/capacity.
        In a real implementation, this might adjust Redis maxmemory or eviction policies.
        For now, it's a placeholder for the optimization integration.
        """
        logger.warning("Emergency cache size increase triggered")
        self.emergency_mode = True
        # Logic to dynamically adjust cache configuration would go here
        pass

    async def emergency_cleanup(self) -> None:
        """
        Emergency action to clean up cache.
        """
        logger.warning("Emergency cache cleanup triggered")
        # Logic to aggressively evict keys would go here
        # For example, clearing volatile keys or specific prefixes
        pass

    # Delegate common methods to the underlying service
    async def get(self, key: str) -> Optional[Any]:
        # This is a simplification, actual delegation would depend on CacheService methods
        # CacheService uses specific methods like get_mod_analysis, not generic get
        pass


# Global cache manager instance
cache_manager = CacheManager()
