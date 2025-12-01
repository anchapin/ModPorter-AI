"""
Production Redis Configuration and Management
Optimized Redis setup with clustering, persistence, and monitoring
"""

import redis
from redis import Redis as SyncRedis
import redis.asyncio as redis_async
from redis.asyncio import Redis as AsyncRedis
from typing import Dict, Any, Optional, List
import json
import logging
from datetime import datetime
import asyncio
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RedisConfig:
    """Production Redis configuration"""

    host: str = "redis"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0
    ssl: bool = False
    connection_pool_size: int = 50
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    retry_on_timeout: bool = True
    decode_responses: bool = True
    max_connections: int = 100


class ProductionRedisManager:
    """Production Redis manager with clustering and optimization"""

    def __init__(self, config: RedisConfig):
        self.config = config
        self.redis_client = None
        self.async_redis = None
        self.connection_pool = None
        self.async_pool = None

    async def initialize(self):
        """Initialize Redis connections with production settings"""
        # Connection pool for sync operations
        self.connection_pool = redis.ConnectionPool(
            host=self.config.host,
            port=self.config.port,
            password=self.config.password,
            db=self.config.db,
            ssl=self.config.ssl,
            max_connections=self.config.max_connections,
            socket_timeout=self.config.socket_timeout,
            socket_connect_timeout=self.config.socket_connect_timeout,
            retry_on_timeout=self.config.retry_on_timeout,
            decode_responses=self.config.decode_responses,
        )

        self.redis_client = SyncRedis(connection_pool=self.connection_pool)

        # Async connection pool
        self.async_pool = redis_async.ConnectionPool(
            host=self.config.host,
            port=self.config.port,
            password=self.config.password,
            db=self.config.db,
            ssl=self.config.ssl,
            max_connections=self.config.max_connections,
            socket_timeout=self.config.socket_timeout,
            socket_connect_timeout=self.config.socket_connect_timeout,
            retry_on_timeout=self.config.retry_on_timeout,
            decode_responses=self.config.decode_responses,
        )

        self.async_redis = AsyncRedis(connection_pool=self.async_pool)

        # Test connections
        await self._test_connections()

    async def _test_connections(self):
        """Test Redis connections"""
        try:
            # Sync test
            self.redis_client.ping()
            # Async test
            await self.async_redis.ping()
            logger.info("Redis connections established successfully")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise

    async def configure_production_settings(self):
        """Configure Redis for production use"""
        settings = {
            # Memory management
            "maxmemory": "1gb",
            "maxmemory-policy": "allkeys-lru",
            "maxmemory-samples": 5,
            # Persistence settings
            "save": "900 1 300 10 60 10000",  # RDB snapshots
            "appendonly": "yes",  # AOF enabled
            "appendfsync": "everysec",  # AOF fsync policy
            "no-appendfsync-on-rewrite": "no",
            "auto-aof-rewrite-percentage": 100,
            "auto-aof-rewrite-min-size": "64mb",
            # Network settings
            "timeout": 300,
            "tcp-keepalive": 60,
            "tcp-backlog": 511,
            # Client settings
            "maxclients": 10000,
            # Performance settings
            "hash-max-ziplist-entries": 512,
            "hash-max-ziplist-value": 64,
            "list-max-ziplist-size": -2,
            "list-compress-depth": 0,
            "set-max-intset-entries": 512,
            "zset-max-ziplist-entries": 128,
            "zset-max-ziplist-value": 64,
            # Slow log
            "slowlog-log-slower-than": 10000,
            "slowlog-max-len": 128,
            # Security
            "protected-mode": "no",
        }

        for setting, value in settings.items():
            try:
                await self.async_redis.config_set(setting, value)
                logger.debug(f"Set Redis config: {setting} = {value}")
            except Exception as e:
                logger.warning(f"Failed to set Redis config {setting}: {e}")


class CacheManager:
    """Production cache management with intelligent eviction"""

    def __init__(self, redis_manager: ProductionRedisManager):
        self.redis = redis_manager.async_redis
        self.cache_stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}

    def _generate_cache_key(self, prefix: str, identifier: str) -> str:
        """Generate cache key with namespace"""
        return f"modporter:{prefix}:{identifier}"

    async def get(self, prefix: str, identifier: str) -> Any:
        """Get value from cache"""
        key = self._generate_cache_key(prefix, identifier)
        try:
            value = await self.redis.get(key)
            if value:
                self.cache_stats["hits"] += 1
                return (
                    json.loads(value)
                    if value.startswith("{") or value.startswith("[")
                    else value
                )
            else:
                self.cache_stats["misses"] += 1
                return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            self.cache_stats["misses"] += 1
            return None

    async def set(self, prefix: str, identifier: str, value: Any, ttl: int = 3600):
        """Set value in cache with TTL"""
        key = self._generate_cache_key(prefix, identifier)
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            await self.redis.setex(key, ttl, value)
            self.cache_stats["sets"] += 1
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")

    async def delete(self, prefix: str, identifier: str):
        """Delete value from cache"""
        key = self._generate_cache_key(prefix, identifier)
        try:
            result = await self.redis.delete(key)
            if result:
                self.cache_stats["deletes"] += 1
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")

    async def invalidate_pattern(self, pattern: str):
        """Invalidate cache keys by pattern"""
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
                logger.info(
                    f"Invalidated {len(keys)} cache keys matching pattern: {pattern}"
                )
        except Exception as e:
            logger.error(f"Cache pattern invalidation error: {e}")

    async def get_cache_stats(self) -> Dict:
        """Get cache performance statistics"""
        try:
            redis_info = await self.redis.info()
            return {
                **self.cache_stats,
                "redis_memory_used": redis_info.get("used_memory_human"),
                "redis_memory_peak": redis_info.get("used_memory_peak_human"),
                "redis_connected_clients": redis_info.get("connected_clients"),
                "redis_keyspace_hits": redis_info.get("keyspace_hits"),
                "redis_keyspace_misses": redis_info.get("keyspace_misses"),
                "hit_ratio": self.cache_stats["hits"]
                / max(1, self.cache_stats["hits"] + self.cache_stats["misses"]),
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return self.cache_stats


class SessionManager:
    """Production session management for real-time features"""

    def __init__(self, redis_manager: ProductionRedisManager):
        self.redis = redis_manager.async_redis
        self.session_ttl = 3600  # 1 hour default

    async def create_session(
        self, session_id: str, user_id: str, data: Dict = None
    ) -> Dict:
        """Create new session"""
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "data": data or {},
        }

        key = f"session:{session_id}"
        await self.redis.hset(
            key,
            mapping={
                k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                for k, v in session_data.items()
            },
        )
        await self.redis.expire(key, self.session_ttl)

        return session_data

    async def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data"""
        key = f"session:{session_id}"
        try:
            data = await self.redis.hgetall(key)
            if data:
                session = {}
                for k, v in data.items():
                    try:
                        session[k] = (
                            json.loads(v)
                            if v.startswith("{") or v.startswith("[")
                            else v
                        )
                    except:
                        session[k] = v

                # Update last activity
                await self.redis.hset(
                    key, "last_activity", datetime.utcnow().isoformat()
                )
                await self.redis.expire(key, self.session_ttl)

                return session
            return None
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            return None

    async def update_session(self, session_id: str, data: Dict):
        """Update session data"""
        key = f"session:{session_id}"
        try:
            await self.redis.hset(key, "data", json.dumps(data))
            await self.redis.hset(key, "last_activity", datetime.utcnow().isoformat())
            await self.redis.expire(key, self.session_ttl)
        except Exception as e:
            logger.error(f"Error updating session {session_id}: {e}")

    async def delete_session(self, session_id: str):
        """Delete session"""
        key = f"session:{session_id}"
        await self.redis.delete(key)

    async def get_active_sessions(self, user_id: str) -> List[str]:
        """Get active sessions for user"""
        pattern = "session:*"
        sessions = []
        try:
            async for key in self.redis.scan_iter(match=pattern):
                session_data = await self.redis.hgetall(key)
                if session_data.get("user_id") == user_id:
                    session_id = key.decode().replace("session:", "")
                    sessions.append(session_id)
        except Exception as e:
            logger.error(f"Error getting active sessions for user {user_id}: {e}")

        return sessions


class DistributedLock:
    """Distributed lock implementation using Redis"""

    def __init__(self, redis_manager: ProductionRedisManager):
        self.redis = redis_manager.async_redis

    async def acquire(self, lock_name: str, ttl: int = 30, timeout: int = 10) -> bool:
        """Acquire distributed lock"""
        lock_key = f"lock:{lock_name}"
        identifier = f"{datetime.utcnow().timestamp()}-{hash(lock_name)}"

        end_time = asyncio.get_event_loop().time() + timeout

        while asyncio.get_event_loop().time() < end_time:
            if await self.redis.set(lock_key, identifier, nx=True, ex=ttl):
                return identifier

            await asyncio.sleep(0.01)

        return False

    async def release(self, lock_name: str, identifier: str) -> bool:
        """Release distributed lock"""
        lock_key = f"lock:{lock_name}"

        # Lua script for atomic release
        lua_script = """
        if redis.call("GET", KEYS[1]) == ARGV[1] then
            return redis.call("DEL", KEYS[1])
        else
            return 0
        end
        """

        try:
            result = await self.redis.eval(lua_script, 1, lock_key, identifier)
            return bool(result)
        except Exception as e:
            logger.error(f"Error releasing lock {lock_name}: {e}")
            return False


class RedisHealthMonitor:
    """Redis health monitoring for production"""

    def __init__(self, redis_manager: ProductionRedisManager):
        self.redis = redis_manager.async_redis

    async def health_check(self) -> Dict:
        """Perform comprehensive Redis health check"""
        health_status = {
            "status": "healthy",
            "checks": {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            # Basic connectivity
            await self.redis.ping()
            health_status["checks"]["connectivity"] = "pass"

            # Memory usage
            info = await self.redis.info()
            health_status["checks"]["memory_used"] = info.get("used_memory_human")
            health_status["checks"]["memory_peak"] = info.get("used_memory_peak_human")
            health_status["checks"]["memory_fragmentation"] = round(
                info.get("mem_fragmentation_ratio", 0), 2
            )

            # Connection stats
            health_status["checks"]["connected_clients"] = info.get("connected_clients")
            health_status["checks"]["blocked_clients"] = info.get("blocked_clients")

            # Performance metrics
            health_status["checks"]["total_commands_processed"] = info.get(
                "total_commands_processed"
            )
            health_status["checks"]["instantaneous_ops_per_sec"] = info.get(
                "instantaneous_ops_per_sec"
            )
            health_status["checks"]["keyspace_hits"] = info.get("keyspace_hits")
            health_status["checks"]["keyspace_misses"] = info.get("keyspace_misses")

            # Persistence
            health_status["checks"]["last_save_time"] = (
                datetime.fromtimestamp(info.get("rdb_last_save_time", 0)).isoformat()
                if info.get("rdb_last_save_time")
                else None
            )

            health_status["checks"]["aof_enabled"] = info.get("aof_enabled", False)
            health_status["checks"]["aof_rewrite_in_progress"] = info.get(
                "aof_rewrite_in_progress", False
            )

            # Slow log
            slowlog = await self.redis.slowlog_get(5)
            health_status["checks"]["slowlog_count"] = len(slowlog)
            health_status["checks"]["recent_slow_commands"] = [
                {
                    "id": entry[0],
                    "timestamp": datetime.fromtimestamp(entry[1]).isoformat(),
                    "duration": entry[2],
                    "command": entry[3],
                }
                for entry in slowlog[:3]  # Show last 3 slow commands
            ]

        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["checks"]["error"] = str(e)
            logger.error(f"Redis health check failed: {e}")

        return health_status


# Utility functions
async def get_redis_manager(config: RedisConfig) -> ProductionRedisManager:
    """Factory function to create Redis manager"""
    manager = ProductionRedisManager(config)
    await manager.initialize()
    await manager.configure_production_settings()
    return manager
