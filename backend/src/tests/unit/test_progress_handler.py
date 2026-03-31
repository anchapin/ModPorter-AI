"""
Unit tests for WebSocket progress handler module.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from src.websocket.progress_handler import (
    AgentStatus,
    ProgressMessageData,
    ProgressMessage,
    progress_message,
    ProgressHandler,
)


class TestAgentStatus:
    """Test cases for AgentStatus enum."""

    def test_all_statuses(self):
        """Test all agent statuses are defined."""
        assert AgentStatus.QUEUED.value == "queued"
        assert AgentStatus.IN_PROGRESS.value == "in_progress"
        assert AgentStatus.COMPLETED.value == "completed"
        assert AgentStatus.FAILED.value == "failed"
        assert AgentStatus.SKIPPED.value == "skipped"


class TestProgressMessageData:
    """Test cases for ProgressMessageData model."""

    def test_valid_data(self):
        """Test creating valid progress message data."""
        data = ProgressMessageData(
            agent="JavaAnalyzerAgent",
            status=AgentStatus.IN_PROGRESS,
            progress=50,
            message="Analyzing Java code",
        )
        
        assert data.agent == "JavaAnalyzerAgent"
        assert data.status == AgentStatus.IN_PROGRESS
        assert data.progress == 50
        assert data.message == "Analyzing Java code"
        assert data.timestamp is not None

    def test_default_timestamp(self):
        """Test default timestamp is set."""
        data = ProgressMessageData(
            agent="Test",
            status=AgentStatus.COMPLETED,
            progress=100,
            message="Done",
        )
        
        assert isinstance(data.timestamp, datetime)
        assert data.timestamp.tzinfo is not None  # Should be timezone-aware

    def test_custom_timestamp(self):
        """Test custom timestamp can be set."""
        custom_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        data = ProgressMessageData(
            agent="Test",
            status=AgentStatus.COMPLETED,
            progress=100,
            message="Done",
            timestamp=custom_time,
        )
        
        assert data.timestamp == custom_time

    def test_details_optional(self):
        """Test details field is optional."""
        data = ProgressMessageData(
            agent="Test",
            status=AgentStatus.QUEUED,
            progress=0,
            message="Queued",
        )
        
        assert data.details is None

    def test_details_with_data(self):
        """Test details field can contain data."""
        details = {"file": "test.java", "lines": 150}
        
        data = ProgressMessageData(
            agent="Test",
            status=AgentStatus.IN_PROGRESS,
            progress=75,
            message="Processing",
            details=details,
        )
        
        assert data.details == details


class TestProgressMessage:
    """Test cases for ProgressMessage model."""

    def test_default_type(self):
        """Test default message type."""
        msg = ProgressMessage(
            data=ProgressMessageData(
                agent="Test",
                status=AgentStatus.COMPLETED,
                progress=100,
                message="Done",
            )
        )
        
        assert msg.type == "agent_progress"

    def test_custom_type(self):
        """Test custom message type."""
        msg = ProgressMessage(
            type="conversion_complete",
            data=ProgressMessageData(
                agent="Test",
                status=AgentStatus.COMPLETED,
                progress=100,
                message="Done",
            )
        )
        
        assert msg.type == "conversion_complete"


class TestProgressMessageFunction:
    """Test cases for progress_message helper function."""

    def test_create_message(self):
        """Test creating progress message."""
        msg = progress_message(
            agent="JavaAnalyzerAgent",
            status=AgentStatus.IN_PROGRESS,
            progress=50,
            message="Analyzing code",
        )
        
        assert isinstance(msg, ProgressMessage)
        assert msg.data.agent == "JavaAnalyzerAgent"
        assert msg.data.status == AgentStatus.IN_PROGRESS
        assert msg.data.progress == 50
        assert msg.data.message == "Analyzing code"

    def test_create_with_details(self):
        """Test creating message with details."""
        msg = progress_message(
            agent="Test",
            status=AgentStatus.COMPLETED,
            progress=100,
            message="Done",
            details={"key": "value"},
        )
        
        assert msg.data.details == {"key": "value"}


class TestProgressHandler:
    """Test cases for ProgressHandler class."""

    @pytest.mark.asyncio
    async def test_broadcast_progress(self):
        """Test broadcasting progress."""
        with patch("src.websocket.progress_handler.manager") as mock_manager:
            mock_manager.broadcast = AsyncMock()
            
            await ProgressHandler.broadcast_progress(
                conversion_id="test-123",
                agent="JavaAnalyzerAgent",
                status=AgentStatus.IN_PROGRESS,
                progress=50,
                message="Analyzing code",
            )
            
            mock_manager.broadcast.assert_called_once()
            call_args = mock_manager.broadcast.call_args
            assert call_args[0][1] == "test-123"

    @pytest.mark.asyncio
    async def test_broadcast_agent_start(self):
        """Test broadcasting agent start."""
        with patch("src.websocket.progress_handler.manager") as mock_manager:
            mock_manager.broadcast = AsyncMock()
            
            await ProgressHandler.broadcast_agent_start(
                conversion_id="test-123",
                agent="JavaAnalyzerAgent",
            )
            
            mock_manager.broadcast.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_agent_start_custom_message(self):
        """Test broadcasting agent start with custom message."""
        with patch("src.websocket.progress_handler.manager") as mock_manager:
            mock_manager.broadcast = AsyncMock()
            
            await ProgressHandler.broadcast_agent_start(
                conversion_id="test-123",
                agent="JavaAnalyzerAgent",
                message="Custom start message",
            )
            
            mock_manager.broadcast.assert_called_once()
            call_args = mock_manager.broadcast.call_args
            msg_data = call_args[0][0]["data"]
            assert msg_data["message"] == "Custom start message"

    @pytest.mark.asyncio
    async def test_broadcast_agent_update(self):
        """Test broadcasting agent update."""
        with patch("src.websocket.progress_handler.manager") as mock_manager:
            mock_manager.broadcast = AsyncMock()
            
            await ProgressHandler.broadcast_agent_update(
                conversion_id="test-123",
                agent="JavaAnalyzerAgent",
                progress=75,
                message="Processing files",
            )
            
            mock_manager.broadcast.assert_called_once()
            call_args = mock_manager.broadcast.call_args
            msg_data = call_args[0][0]["data"]
            assert msg_data["progress"] == 75
            assert msg_data["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_broadcast_agent_complete(self):
        """Test broadcasting agent completion."""
        with patch("src.websocket.progress_handler.manager") as mock_manager:
            mock_manager.broadcast = AsyncMock()
            
            await ProgressHandler.broadcast_agent_complete(
                conversion_id="test-123",
                agent="JavaAnalyzerAgent",
            )
            
            mock_manager.broadcast.assert_called_once()
            call_args = mock_manager.broadcast.call_args
            msg_data = call_args[0][0]["data"]
            assert msg_data["status"] == "completed"
            assert msg_data["progress"] == 100

    @pytest.mark.asyncio
    async def test_broadcast_agent_failed(self):
        """Test broadcasting agent failure."""
        with patch("src.websocket.progress_handler.manager") as mock_manager:
            mock_manager.broadcast = AsyncMock()
            
            await ProgressHandler.broadcast_agent_failed(
                conversion_id="test-123",
                agent="JavaAnalyzerAgent",
                error_message="Analysis failed",
            )
            
            mock_manager.broadcast.assert_called_once()
            call_args = mock_manager.broadcast.call_args
            msg_data = call_args[0][0]["data"]
            assert msg_data["status"] == "failed"
            assert msg_data["details"]["error"] == "Analysis failed"

    @pytest.mark.asyncio
    async def test_broadcast_conversion_complete(self):
        """Test broadcasting conversion complete."""
        with patch("src.websocket.progress_handler.manager") as mock_manager:
            mock_manager.broadcast = AsyncMock()
            
            await ProgressHandler.broadcast_conversion_complete(
                conversion_id="test-123",
                download_url="https://example.com/download",
            )
            
            mock_manager.broadcast.assert_called_once()
            call_args = mock_manager.broadcast.call_args
            msg_data = call_args[0][0]["data"]
            assert msg_data["details"]["download_url"] == "https://example.com/download"

    @pytest.mark.asyncio
    async def test_broadcast_conversion_failed(self):
        """Test broadcasting conversion failure."""
        with patch("src.websocket.progress_handler.manager") as mock_manager:
            mock_manager.broadcast = AsyncMock()
            
            await ProgressHandler.broadcast_conversion_failed(
                conversion_id="test-123",
                error_message="Conversion failed",
            )
            
            mock_manager.broadcast.assert_called_once()
            call_args = mock_manager.broadcast.call_args
            msg_data = call_args[0][0]["data"]
            assert msg_data["status"] == "failed"
            assert "Conversion failed" in msg_data["message"]

    @pytest.mark.asyncio
    async def test_broadcast_error_handling(self):
        """Test error handling in broadcast."""
        with patch("src.websocket.progress_handler.manager") as mock_manager:
            mock_manager.broadcast = AsyncMock(side_effect=Exception("Connection error"))
            
            # Should not raise exception, just log error
            await ProgressHandler.broadcast_progress(
                conversion_id="test-123",
                agent="Test",
                status=AgentStatus.COMPLETED,
                progress=100,
                message="Done",
            )
            
            mock_manager.broadcast.assert_called_once()


class TestProgressMessageSerialization:
    """Test cases for message serialization."""

    def test_model_dump(self):
        """Test model dump for JSON serialization."""
        msg = progress_message(
            agent="Test",
            status=AgentStatus.COMPLETED,
            progress=100,
            message="Done",
        )
        
        dumped = msg.model_dump()
        
        assert "type" in dumped
        assert "data" in dumped
        assert dumped["data"]["agent"] == "Test"
        assert dumped["data"]["status"] == "completed"

    def test_json_serialization(self):
        """Test JSON serialization."""
        import json
        
        msg = progress_message(
            agent="Test",
            status=AgentStatus.COMPLETED,
            progress=100,
            message="Done",
        )
        
        json_str = msg.model_dump_json()
        
        assert "agent" in json_str
        assert "Test" in json_str