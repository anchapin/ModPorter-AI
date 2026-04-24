"""
Additional tests for core/redis.py to fill remaining coverage gaps.

Targets:
- JobQueue.enqueue with mock Redis (line 196)
- JobQueue.dequeue error paths (lines 218, 224-226)
- JobQueue.complete_job error (lines 236-238)
- JobQueue.get_queue_size error (lines 247-248)
- RateLimiter.check with mock pipeline (lines 281-307)
- RateLimiter.get_remaining with mock (lines 309-323)
- RedisClient.set not connected (line 122)
- RedisClient.delete error (line 139)
- RedisClient.exists error (line 149)
- RedisClient.expire not connected (line 154)
- RedisClient.connect unexpected error (lines 86-89)
- close_redis with actual clients (lines 359-375)
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta


class TestRedisClientEdgeCases:
    """Cover additional RedisClient paths."""

    @pytest.mark.asyncio
    async def test_connect_unexpected_error(self):
        from core.redis import RedisClient

        with patch("core.redis.aioredis.ConnectionPool") as mock_pool_class:
            mock_pool_class.from_url.side_effect = Exception("weird error")

            client = RedisClient()
            result = await client.connect()

            assert result is False
            assert client._connected is False

    @pytest.mark.asyncio
    async def test_set_not_connected(self):
        from core.redis import RedisClient

        client = RedisClient()
        client._connected = False

        result = await client.set("key", "val")
        assert result is False

    @pytest.mark.asyncio
    async def test_set_error(self):
        from core.redis import RedisClient
        from redis.exceptions import RedisError

        mock_client = AsyncMock()
        mock_client.set = AsyncMock(side_effect=RedisError("write fail"))

        client = RedisClient()
        client._client = mock_client
        client._connected = True

        result = await client.set("key", "val")
        assert result is False

    @pytest.mark.asyncio
    async def test_set_string_no_json_encode(self):
        from core.redis import RedisClient

        mock_client = AsyncMock()
        mock_client.set = AsyncMock(return_value=True)

        client = RedisClient()
        client._client = mock_client
        client._connected = True

        result = await client.set("key", "raw_string", json_encode=False)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_error(self):
        from core.redis import RedisClient
        from redis.exceptions import RedisError

        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(side_effect=RedisError("del fail"))

        client = RedisClient()
        client._client = mock_client
        client._connected = True

        result = await client.delete("key")
        assert result == 0

    @pytest.mark.asyncio
    async def test_exists_error(self):
        from core.redis import RedisClient
        from redis.exceptions import RedisError

        mock_client = AsyncMock()
        mock_client.exists = AsyncMock(side_effect=RedisError("exists fail"))

        client = RedisClient()
        client._client = mock_client
        client._connected = True

        result = await client.exists("key")
        assert result is False

    @pytest.mark.asyncio
    async def test_expire_not_connected(self):
        from core.redis import RedisClient

        client = RedisClient()
        client._connected = False

        result = await client.expire("key", 60)
        assert result is False

    @pytest.mark.asyncio
    async def test_expire_error(self):
        from core.redis import RedisClient
        from redis.exceptions import RedisError

        mock_client = AsyncMock()
        mock_client.expire = AsyncMock(side_effect=RedisError("expire fail"))

        client = RedisClient()
        client._client = mock_client
        client._connected = True

        result = await client.expire("key", 60)
        assert result is False

    @pytest.mark.asyncio
    async def test_disconnect_no_client(self):
        from core.redis import RedisClient

        client = RedisClient()
        client._connected = True

        await client.disconnect()
        assert client._connected is False


class TestJobQueueFull:
    """Cover JobQueue.enqueue, dequeue error, complete_job error, get_queue_size error."""

    @pytest.mark.asyncio
    async def test_enqueue_success(self):
        from core.redis import JobQueue

        queue = JobQueue(queue_name="test")
        queue.client._connected = True

        mock_redis = AsyncMock()
        mock_redis.zadd = AsyncMock(return_value=1)
        queue.client._client = mock_redis

        result = await queue.enqueue({"job_id": "j1", "type": "convert"}, priority=1)
        assert result is True
        mock_redis.zadd.assert_called_once()

        call_args = mock_redis.zadd.call_args
        assert call_args[0][0] == "queue:test"

    @pytest.mark.asyncio
    async def test_enqueue_generates_job_id(self):
        from core.redis import JobQueue

        queue = JobQueue(queue_name="test")
        queue.client._connected = True

        mock_redis = AsyncMock()
        mock_redis.zadd = AsyncMock(return_value=1)
        queue.client._client = mock_redis

        result = await queue.enqueue({"type": "convert"})
        assert result is True

    @pytest.mark.asyncio
    async def test_enqueue_error(self):
        from core.redis import JobQueue
        from redis.exceptions import RedisError

        queue = JobQueue(queue_name="test")
        queue.client._connected = True

        mock_redis = AsyncMock()
        mock_redis.zadd = AsyncMock(side_effect=RedisError("zadd fail"))
        queue.client._client = mock_redis

        result = await queue.enqueue({"job_id": "j1"})
        assert result is False

    @pytest.mark.asyncio
    async def test_dequeue_success_string_result(self):
        from core.redis import JobQueue

        queue = JobQueue(queue_name="test")
        queue.client._connected = True

        payload = json.dumps({"job_id": "j1", "data": "val"})
        mock_redis = AsyncMock()
        mock_redis.zpopmax = AsyncMock(return_value=[(payload, 1)])
        mock_redis.sadd = AsyncMock(return_value=1)
        queue.client._client = mock_redis

        result = await queue.dequeue()
        assert result == {"job_id": "j1", "data": "val"}

    @pytest.mark.asyncio
    async def test_dequeue_error(self):
        from core.redis import JobQueue
        from redis.exceptions import RedisError

        queue = JobQueue(queue_name="test")
        queue.client._connected = True

        mock_redis = AsyncMock()
        mock_redis.zpopmax = AsyncMock(side_effect=RedisError("zpop fail"))
        queue.client._client = mock_redis

        result = await queue.dequeue()
        assert result is None

    @pytest.mark.asyncio
    async def test_complete_job_error(self):
        from core.redis import JobQueue
        from redis.exceptions import RedisError

        queue = JobQueue(queue_name="test")
        queue.client._connected = True

        mock_redis = AsyncMock()
        mock_redis.srem = AsyncMock(side_effect=RedisError("srem fail"))
        queue.client._client = mock_redis

        result = await queue.complete_job("j1")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_queue_size_error(self):
        from core.redis import JobQueue
        from redis.exceptions import RedisError

        queue = JobQueue(queue_name="test")
        queue.client._connected = True

        mock_redis = AsyncMock()
        mock_redis.zcard = AsyncMock(side_effect=RedisError("zcard fail"))
        queue.client._client = mock_redis

        result = await queue.get_queue_size()
        assert result == 0

    @pytest.mark.asyncio
    async def test_get_queue_size_not_connected(self):
        from core.redis import JobQueue

        queue = JobQueue(queue_name="test")
        queue.client._connected = False

        result = await queue.get_queue_size()
        assert result == 0


class TestRateLimiterFull:
    """Cover RateLimiter.check and get_remaining with mock pipeline."""

    @pytest.mark.asyncio
    async def test_check_allowed(self):
        from core.redis import RateLimiter

        limiter = RateLimiter(limit=10, window=60)
        limiter.client._connected = True

        mock_pipe = MagicMock()
        mock_pipe.zremrangebyscore = MagicMock(return_value=mock_pipe)
        mock_pipe.zcard = MagicMock(return_value=mock_pipe)
        mock_pipe.zadd = MagicMock(return_value=mock_pipe)
        mock_pipe.expire = MagicMock(return_value=mock_pipe)
        mock_pipe.execute = AsyncMock(return_value=[0, 3, 1, True])

        mock_redis = MagicMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        limiter.client._client = mock_redis

        result = await limiter.check("user:1")
        assert result is True

    @pytest.mark.asyncio
    async def test_check_blocked(self):
        from core.redis import RateLimiter

        limiter = RateLimiter(limit=5, window=60)
        limiter.client._connected = True

        mock_pipe = MagicMock()
        mock_pipe.zremrangebyscore = MagicMock(return_value=mock_pipe)
        mock_pipe.zcard = MagicMock(return_value=mock_pipe)
        mock_pipe.zadd = MagicMock(return_value=mock_pipe)
        mock_pipe.expire = MagicMock(return_value=mock_pipe)
        mock_pipe.execute = AsyncMock(return_value=[0, 5, 1, True])

        mock_redis = MagicMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        limiter.client._client = mock_redis

        result = await limiter.check("user:1")
        assert result is False

    @pytest.mark.asyncio
    async def test_check_error_allows(self):
        from core.redis import RateLimiter
        from redis.exceptions import RedisError

        limiter = RateLimiter(limit=10, window=60)
        limiter.client._connected = True

        mock_redis = MagicMock()
        mock_redis.pipeline = MagicMock(side_effect=RedisError("pipe fail"))
        limiter.client._client = mock_redis

        result = await limiter.check("user:1")
        assert result is True

    @pytest.mark.asyncio
    async def test_get_remaining_success(self):
        from core.redis import RateLimiter

        limiter = RateLimiter(limit=100, window=60)
        limiter.client._connected = True

        mock_redis = AsyncMock()
        mock_redis.zremrangebyscore = AsyncMock(return_value=1)
        mock_redis.zcard = AsyncMock(return_value=30)
        limiter.client._client = mock_redis

        result = await limiter.get_remaining("user:1")
        assert result == 70

    @pytest.mark.asyncio
    async def test_get_remaining_error(self):
        from core.redis import RateLimiter
        from redis.exceptions import RedisError

        limiter = RateLimiter(limit=100, window=60)
        limiter.client._connected = True

        mock_redis = AsyncMock()
        mock_redis.zremrangebyscore = AsyncMock(side_effect=RedisError("err"))
        limiter.client._client = mock_redis

        result = await limiter.get_remaining("user:1")
        assert result == 100

    @pytest.mark.asyncio
    async def test_get_remaining_zero_floor(self):
        from core.redis import RateLimiter

        limiter = RateLimiter(limit=5, window=60)
        limiter.client._connected = True

        mock_redis = AsyncMock()
        mock_redis.zremrangebyscore = AsyncMock(return_value=1)
        mock_redis.zcard = AsyncMock(return_value=10)
        limiter.client._client = mock_redis

        result = await limiter.get_remaining("user:1")
        assert result == 0


class TestCloseRedisActual:
    """Cover close_redis with actual mock clients."""

    @pytest.mark.asyncio
    async def test_close_redis_with_clients(self):
        import core.redis as redis_mod

        mock_client = AsyncMock()
        mock_queue = AsyncMock()
        mock_limiter = AsyncMock()

        with patch.object(redis_mod, "_redis_client", mock_client):
            with patch.object(redis_mod, "_job_queue", mock_queue):
                with patch.object(redis_mod, "_rate_limiter", mock_limiter):
                    await redis_mod.close_redis()

                    mock_client.disconnect.assert_called_once()
                    mock_queue.disconnect.assert_called_once()
                    mock_limiter.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_redis_none_clients(self):
        import core.redis as redis_mod

        with patch.object(redis_mod, "_redis_client", None):
            with patch.object(redis_mod, "_job_queue", None):
                with patch.object(redis_mod, "_rate_limiter", None):
                    await redis_mod.close_redis()

    @pytest.mark.asyncio
    async def test_job_queue_connect_passthrough(self):
        from core.redis import JobQueue

        queue = JobQueue(queue_name="test")
        with patch.object(queue.client, "connect", new_callable=AsyncMock, return_value=True):
            result = await queue.connect()
            assert result is True

    @pytest.mark.asyncio
    async def test_rate_limiter_connect_passthrough(self):
        from core.redis import RateLimiter

        limiter = RateLimiter(limit=10, window=60)
        with patch.object(limiter.client, "connect", new_callable=AsyncMock, return_value=True):
            result = await limiter.connect()
            assert result is True
