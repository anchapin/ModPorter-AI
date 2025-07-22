"""
Unit tests for Redis Job Manager in AI Engine.

These tests verify the thread-safe Redis-based job state management
that replaced the global dictionary.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock
from fastapi import HTTPException

# Import the modules we need to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.main import RedisJobManager, ConversionStatus


class TestRedisJobManager:
    """Test cases for RedisJobManager class."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        mock_redis = AsyncMock()
        return mock_redis

    @pytest.fixture
    def job_manager(self, mock_redis):
        """Create a RedisJobManager instance with mock Redis."""
        return RedisJobManager(mock_redis)

    @pytest.fixture
    def sample_job_status(self):
        """Create a sample ConversionStatus for testing."""
        return ConversionStatus(
            job_id="test-job-123",
            status="processing",
            progress=50,
            current_stage="translation",
            message="Converting Java code to Bedrock",
            started_at=datetime.utcnow()
        )

    @pytest.mark.asyncio
    async def test_set_job_status_success(self, job_manager, mock_redis, sample_job_status):
        """Test successful job status storage."""
        mock_redis.set.return_value = True
        
        await job_manager.set_job_status("test-job-123", sample_job_status)
        
        # Verify Redis set was called with correct parameters
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        
        # Check key format
        assert call_args[0][0] == "ai_engine:jobs:test-job-123"
        
        # Check JSON data structure
        stored_data = json.loads(call_args[0][1])
        assert stored_data["job_id"] == "test-job-123"
        assert stored_data["status"] == "processing"
        assert stored_data["progress"] == 50
        assert stored_data["current_stage"] == "translation"
        
        # Check expiration was set
        assert call_args[1]["ex"] == 3600

    @pytest.mark.asyncio
    async def test_set_job_status_redis_failure(self, job_manager, mock_redis, sample_job_status):
        """Test job status storage when Redis fails."""
        mock_redis.set.side_effect = Exception("Redis connection failed")
        
        with pytest.raises(HTTPException) as exc_info:
            await job_manager.set_job_status("test-job-123", sample_job_status)
        
        assert exc_info.value.status_code == 503
        assert "Job state storage failed" in str(exc_info.value.detail)
        assert job_manager.available is False

    @pytest.mark.asyncio
    async def test_get_job_status_success(self, job_manager, mock_redis):
        """Test successful job status retrieval."""
        # Mock Redis response
        stored_data = {
            "job_id": "test-job-123",
            "status": "completed",
            "progress": 100,
            "current_stage": "finished",
            "message": "Conversion completed",
            "started_at": "2024-01-01T12:00:00",
            "completed_at": "2024-01-01T12:05:00"
        }
        mock_redis.get.return_value = json.dumps(stored_data)
        
        result = await job_manager.get_job_status("test-job-123")
        
        # Verify Redis get was called
        mock_redis.get.assert_called_once_with("ai_engine:jobs:test-job-123")
        
        # Verify returned ConversionStatus object
        assert isinstance(result, ConversionStatus)
        assert result.job_id == "test-job-123"
        assert result.status == "completed"
        assert result.progress == 100
        assert result.current_stage == "finished"
        assert isinstance(result.started_at, datetime)
        assert isinstance(result.completed_at, datetime)

    @pytest.mark.asyncio
    async def test_get_job_status_not_found(self, job_manager, mock_redis):
        """Test job status retrieval when job doesn't exist."""
        mock_redis.get.return_value = None
        
        result = await job_manager.get_job_status("nonexistent-job")
        
        assert result is None
        mock_redis.get.assert_called_once_with("ai_engine:jobs:nonexistent-job")

    @pytest.mark.asyncio
    async def test_get_job_status_redis_failure(self, job_manager, mock_redis):
        """Test job status retrieval when Redis fails."""
        mock_redis.get.side_effect = Exception("Redis connection failed")
        
        result = await job_manager.get_job_status("test-job-123")
        
        assert result is None
        assert job_manager.available is False

    @pytest.mark.asyncio
    async def test_get_job_status_invalid_json(self, job_manager, mock_redis):
        """Test job status retrieval with corrupted JSON data."""
        mock_redis.get.return_value = "invalid json data"
        
        result = await job_manager.get_job_status("test-job-123")
        
        assert result is None
        assert job_manager.available is False

    @pytest.mark.asyncio
    async def test_delete_job_success(self, job_manager, mock_redis):
        """Test successful job deletion."""
        mock_redis.delete.return_value = 1
        
        await job_manager.delete_job("test-job-123")
        
        mock_redis.delete.assert_called_once_with("ai_engine:jobs:test-job-123")

    @pytest.mark.asyncio
    async def test_delete_job_redis_failure(self, job_manager, mock_redis):
        """Test job deletion when Redis fails."""
        mock_redis.delete.side_effect = Exception("Redis connection failed")
        
        # Should not raise exception, just log error
        await job_manager.delete_job("test-job-123")
        
        mock_redis.delete.assert_called_once_with("ai_engine:jobs:test-job-123")

    @pytest.mark.asyncio
    async def test_manager_unavailable_state(self, mock_redis):
        """Test behavior when manager is in unavailable state."""
        job_manager = RedisJobManager(mock_redis)
        job_manager.available = False
        
        sample_status = ConversionStatus(
            job_id="test",
            status="queued",
            progress=0,
            current_stage="init",
            message="test"
        )
        
        # Should raise exception when trying to set status
        with pytest.raises(HTTPException) as exc_info:
            await job_manager.set_job_status("test", sample_status)
        
        assert exc_info.value.status_code == 503
        assert "Job state storage failed" in str(exc_info.value.detail)
        
        # Should return None when trying to get status
        result = await job_manager.get_job_status("test")
        assert result is None

    def test_datetime_serialization(self, job_manager, sample_job_status):
        """Test that datetime objects are properly serialized."""
        # This would be tested as part of set_job_status, but we can also test the logic directly
        status_dict = sample_job_status.model_dump()
        
        # Simulate the datetime conversion logic
        if status_dict.get('started_at'):
            status_dict['started_at'] = status_dict['started_at'].isoformat()
        if status_dict.get('completed_at'):
            status_dict['completed_at'] = status_dict['completed_at'].isoformat() if status_dict['completed_at'] else None
        
        # Should be JSON serializable
        json_str = json.dumps(status_dict)
        assert isinstance(json_str, str)
        
        # Should be deserializable
        parsed = json.loads(json_str)
        assert parsed['job_id'] == sample_job_status.job_id


class TestThreadSafety:
    """Test thread safety aspects of Redis job management."""

    @pytest.mark.asyncio
    async def test_concurrent_job_operations(self):
        """Test that concurrent operations don't interfere with each other."""
        import asyncio
        
        mock_redis = AsyncMock()
        mock_redis.set.return_value = True
        mock_redis.get.return_value = None
        mock_redis.delete.return_value = 1
        
        job_manager = RedisJobManager(mock_redis)
        
        # Create multiple concurrent operations
        async def set_job(job_id, status):
            job_status = ConversionStatus(
                job_id=job_id,
                status=status,
                progress=0,
                current_stage="test",
                message="test message"
            )
            await job_manager.set_job_status(job_id, job_status)
        
        async def get_job(job_id):
            return await job_manager.get_job_status(job_id)
        
        async def delete_job(job_id):
            await job_manager.delete_job(job_id)
        
        # Run concurrent operations
        tasks = []
        for i in range(10):
            tasks.append(set_job(f"job-{i}", "processing"))
            tasks.append(get_job(f"job-{i}"))
            tasks.append(delete_job(f"job-{i}"))
        
        # All operations should complete without errors
        await asyncio.gather(*tasks)
        
        # Verify Redis was called the expected number of times
        assert mock_redis.set.call_count == 10
        assert mock_redis.get.call_count == 10
        assert mock_redis.delete.call_count == 10