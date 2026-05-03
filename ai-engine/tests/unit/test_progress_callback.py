"""
Unit tests for ProgressCallback system.
"""

import pytest
import json
import os
from unittest.mock import MagicMock, patch, AsyncMock
from utils.progress_callback import ProgressCallback, ProgressCallbackManager, create_progress_callback, cleanup_progress_callback, get_progress_manager

class TestProgressCallback:
    @pytest.fixture
    def mock_redis(self):
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = AsyncMock()
            mock_from_url.return_value = mock_client
            yield mock_client

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_redis):
        cb = ProgressCallback("job1")
        success = await cb.connect()
        assert success is True
        assert cb._connected is True
        mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self, mock_redis):
        mock_redis.ping.side_effect = Exception("Redis down")
        cb = ProgressCallback("job1")
        success = await cb.connect()
        assert success is False
        assert cb._connected is False

    @pytest.mark.asyncio
    async def test_send_progress_not_connected(self):
        cb = ProgressCallback("job1")
        # Should return early without calling redis
        await cb.send_progress("agent", "status", 50, "msg")
        assert cb.redis_client is None

    @pytest.mark.asyncio
    async def test_send_progress_success(self, mock_redis):
        cb = ProgressCallback("job1")
        await cb.connect()
        await cb.send_progress("agent", "status", 50, "msg", {"foo": "bar"})
        
        assert mock_redis.set.called
        assert mock_redis.publish.called
        
        # Verify call arguments
        args, _ = mock_redis.set.call_args
        key = args[0]
        data = json.loads(args[1])
        assert key == "ai_engine:progress:job1"
        assert data["agent"] == "agent"
        assert data["details"]["foo"] == "bar"

    @pytest.mark.asyncio
    async def test_send_progress_exception(self, mock_redis):
        cb = ProgressCallback("job1")
        await cb.connect()
        mock_redis.set.side_effect = Exception("Set failed")
        # Should catch exception and log it
        await cb.send_progress("agent", "status", 50, "msg")

    @pytest.mark.asyncio
    async def test_broadcast_helpers(self, mock_redis):
        cb = ProgressCallback("job1")
        await cb.connect()
        
        with patch.object(cb, 'send_progress', new_callable=AsyncMock) as mock_send:
            await cb.broadcast_agent_start("A1")
            mock_send.assert_called_with(agent="A1", status="in_progress", progress=0, message="A1 started processing")
            
            await cb.broadcast_agent_update("A1", 50, "Updated")
            mock_send.assert_called_with(agent="A1", status="in_progress", progress=50, message="Updated", details=None)
            
            await cb.broadcast_agent_complete("A1")
            mock_send.assert_called_with(agent="A1", status="completed", progress=100, message="A1 completed successfully")
            
            await cb.broadcast_agent_failed("A1", "Error")
            mock_send.assert_called_with(agent="A1", status="failed", progress=0, message="A1 failed: Error", details={"error": "Error"})
            
            await cb.broadcast_conversion_complete("http://down")
            mock_send.assert_called_with(agent="ConversionWorkflow", status="completed", progress=100, message="Conversion completed successfully", details={"download_url": "http://down"})
            
            await cb.broadcast_conversion_failed("Global error")
            mock_send.assert_called_with(agent="ConversionWorkflow", status="failed", progress=0, message="Conversion failed: Global error", details={"error": "Global error"})

    @pytest.mark.asyncio
    async def test_disconnect(self, mock_redis):
        cb = ProgressCallback("job1")
        await cb.connect()
        await cb.disconnect()
        assert cb._connected is False
        mock_redis.close.assert_called_once()


class TestProgressCallbackManager:
    @pytest.mark.asyncio
    async def test_manager_lifecycle(self):
        with patch('utils.progress_callback.ProgressCallback.connect', new_callable=AsyncMock) as mock_connect, \
             patch('utils.progress_callback.ProgressCallback.disconnect', new_callable=AsyncMock) as mock_disconnect:
            
            manager = ProgressCallbackManager()
            
            cb1 = await manager.get_callback("job1")
            assert "job1" in manager._callbacks
            mock_connect.assert_called_once()
            
            # Same job ID should return same callback
            cb1_again = await manager.get_callback("job1")
            assert cb1 is cb1_again
            assert mock_connect.call_count == 1
            
            await manager.remove_callback("job1")
            assert "job1" not in manager._callbacks
            mock_disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_all(self):
        with patch('utils.progress_callback.ProgressCallback.connect', new_callable=AsyncMock), \
             patch('utils.progress_callback.ProgressCallback.disconnect', new_callable=AsyncMock) as mock_disconnect:
            
            manager = ProgressCallbackManager()
            await manager.get_callback("j1")
            await manager.get_callback("j2")
            
            await manager.cleanup_all()
            assert len(manager._callbacks) == 0
            assert mock_disconnect.call_count == 2


class TestModuleFunctions:
    @pytest.mark.asyncio
    async def test_create_and_cleanup(self):
        with patch('utils.progress_callback.ProgressCallback.connect', new_callable=AsyncMock), \
             patch('utils.progress_callback.ProgressCallback.disconnect', new_callable=AsyncMock):
            
            cb = await create_progress_callback("jobX")
            assert cb.job_id == "jobX"
            
            # Verify it's in the global manager
            manager = get_progress_manager()
            assert "jobX" in manager._callbacks
            
            await cleanup_progress_callback("jobX")
            assert "jobX" not in manager._callbacks

def test_redis_not_available():
    """Test behavior when Redis is not available."""
    with patch('utils.progress_callback.REDIS_AVAILABLE', False):
        cb = ProgressCallback("job")
        # Should return False on connect
        import asyncio
        loop = asyncio.new_event_loop()
        res = loop.run_until_complete(cb.connect())
        assert res is False
        loop.close()
