"""
Integration tests for WebSocket and Conversion API endpoints.

These tests verify:
- WebSocket connection management
- Progress message broadcasting
- Conversion REST endpoints
- Integration with background tasks
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

# Import the main app
from main import app


# Fixtures
@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def test_file_path() -> str:
    """Path to a test JAR file."""
    return os.path.join(os.path.dirname(__file__), "fixtures", "test_mod.jar")


@pytest.fixture
def mock_upload_file(tmp_path):
    """Create a mock uploaded file."""
    file_path = tmp_path / "test_mod.jar"
    file_path.write_bytes(b"fake jar content")
    return file_path


# WebSocket Tests
@pytest.mark.asyncio
async def test_websocket_connection():
    """Test WebSocket connection acceptance."""
    from websocket.manager import manager

    # Create a mock WebSocket
    mock_ws = MagicMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_json = AsyncMock()

    conversion_id = "test-conversion-123"

    # Connect
    await manager.connect(mock_ws, conversion_id)

    # Verify
    mock_ws.accept.assert_called_once()
    assert conversion_id in manager.active_connections
    assert mock_ws in manager.active_connections[conversion_id]
    assert manager.get_connection_count(conversion_id) == 1

    # Cleanup
    manager.disconnect(mock_ws, conversion_id)


@pytest.mark.asyncio
async def test_websocket_broadcast():
    """Test WebSocket message broadcasting."""
    from websocket.manager import manager

    # Create mock WebSockets
    mock_ws1 = MagicMock()
    mock_ws2 = MagicMock()
    mock_ws1.accept = AsyncMock()
    mock_ws2.accept = AsyncMock()
    mock_ws1.send_json = AsyncMock()
    mock_ws2.send_json = AsyncMock()

    conversion_id = "test-conversion-456"

    # Connect both clients
    await manager.connect(mock_ws1, conversion_id)
    await manager.connect(mock_ws2, conversion_id)

    # Broadcast a message
    test_message = {"type": "test", "data": {"progress": 50}}
    await manager.broadcast(test_message, conversion_id)

    # Verify both clients received the message
    mock_ws1.send_json.assert_called_once_with(test_message)
    mock_ws2.send_json.assert_called_once_with(test_message)

    # Cleanup
    manager.disconnect(mock_ws1, conversion_id)
    manager.disconnect(mock_ws2, conversion_id)


@pytest.mark.asyncio
async def test_websocket_disconnect_cleanup():
    """Test WebSocket disconnect cleanup."""
    from websocket.manager import manager

    mock_ws = MagicMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_json = AsyncMock()

    conversion_id = "test-conversion-789"

    # Connect
    await manager.connect(mock_ws, conversion_id)
    assert manager.get_connection_count(conversion_id) == 1

    # Disconnect
    manager.disconnect(mock_ws, conversion_id)

    # Verify cleanup
    assert conversion_id not in manager.active_connections
    assert manager.get_connection_count(conversion_id) == 0


@pytest.mark.asyncio
async def test_multiple_clients_same_conversion():
    """Test multiple clients connecting to the same conversion."""
    from websocket.manager import manager

    clients = []
    conversion_id = "test-conversion-multi"

    # Connect multiple clients
    for i in range(5):
        mock_ws = MagicMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()
        await manager.connect(mock_ws, conversion_id)
        clients.append(mock_ws)

    # Verify all connected
    assert manager.get_connection_count(conversion_id) == 5

    # Broadcast to all
    test_message = {"type": "broadcast_test", "data": {"value": 123}}
    await manager.broadcast(test_message, conversion_id)

    # Verify all received
    for client in clients:
        client.send_json.assert_called_once_with(test_message)

    # Cleanup
    for client in clients:
        manager.disconnect(client, conversion_id)

    assert conversion_id not in manager.active_connections


# Progress Handler Tests
@pytest.mark.asyncio
async def test_progress_message_creation():
    """Test progress message structure."""
    from websocket.progress_handler import progress_message, AgentStatus

    msg = progress_message(
        agent="JavaAnalyzerAgent",
        status=AgentStatus.IN_PROGRESS,
        progress=45,
        message="Analyzing Java files...",
    )

    assert msg.data.agent == "JavaAnalyzerAgent"
    assert msg.data.status == AgentStatus.IN_PROGRESS
    assert msg.data.progress == 45
    assert msg.data.message == "Analyzing Java files..."
    assert msg.data.timestamp is not None
    assert msg.type == "agent_progress"

    # Verify can be serialized to JSON
    json_str = msg.model_dump_json()
    assert "JavaAnalyzerAgent" in json_str


@pytest.mark.asyncio
async def test_progress_handler_broadcast():
    """Test ProgressHandler broadcasting."""
    from websocket.progress_handler import ProgressHandler
    from websocket.manager import manager

    # Setup mock WebSocket
    mock_ws = MagicMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_json = AsyncMock()

    conversion_id = "test-progress-handler"

    await manager.connect(mock_ws, conversion_id)

    # Broadcast agent start
    await ProgressHandler.broadcast_agent_start(
        conversion_id, "TestAgent", "Starting test task"
    )

    # Verify message sent
    assert mock_ws.send_json.call_count == 1
    sent_data = mock_ws.send_json.call_args[0][0]
    assert sent_data["data"]["agent"] == "TestAgent"
    assert sent_data["data"]["status"] == "in_progress"
    assert sent_data["data"]["progress"] == 0

    # Broadcast agent update
    await ProgressHandler.broadcast_agent_update(
        conversion_id, "TestAgent", 50, "Halfway through"
    )

    assert mock_ws.send_json.call_count == 2
    sent_data = mock_ws.send_json.call_args[0][0]
    assert sent_data["data"]["progress"] == 50

    # Broadcast agent complete
    await ProgressHandler.broadcast_agent_complete(conversion_id, "TestAgent")

    assert mock_ws.send_json.call_count == 3
    sent_data = mock_ws.send_json.call_args[0][0]
    assert sent_data["data"]["status"] == "completed"
    assert sent_data["data"]["progress"] == 100

    # Cleanup
    manager.disconnect(mock_ws, conversion_id)


@pytest.mark.asyncio
async def test_conversion_complete_broadcast():
    """Test conversion completion broadcast."""
    from websocket.progress_handler import ProgressHandler
    from websocket.manager import manager

    mock_ws = MagicMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_json = AsyncMock()

    conversion_id = "test-complete"
    download_url = f"/api/v1/conversions/{conversion_id}/download"

    await manager.connect(mock_ws, conversion_id)

    await ProgressHandler.broadcast_conversion_complete(conversion_id, download_url)

    assert mock_ws.send_json.call_count == 2  # Connection confirm + complete message
    sent_data = mock_ws.send_json.call_args[0][0]
    assert sent_data["type"] == "conversion_complete"
    assert sent_data["data"]["agent"] == "ConversionWorkflow"
    assert sent_data["data"]["status"] == "completed"
    assert sent_data["data"]["details"]["download_url"] == download_url

    manager.disconnect(mock_ws, conversion_id)


@pytest.mark.asyncio
async def test_conversion_failed_broadcast():
    """Test conversion failure broadcast."""
    from websocket.progress_handler import ProgressHandler
    from websocket.manager import manager

    mock_ws = MagicMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_json = AsyncMock()

    conversion_id = "test-failed"
    error_msg = "Failed to parse Java file"

    await manager.connect(mock_ws, conversion_id)

    await ProgressHandler.broadcast_conversion_failed(conversion_id, error_msg)

    sent_data = mock_ws.send_json.call_args[0][0]
    assert sent_data["type"] == "conversion_failed"
    assert sent_data["data"]["status"] == "failed"
    assert error_msg in sent_data["data"]["message"]
    assert sent_data["data"]["details"]["error"] == error_msg

    manager.disconnect(mock_ws, conversion_id)


# Conversion API Tests
@pytest.mark.asyncio
async def test_create_conversion_with_file(async_client, mock_upload_file):
    """Test creating a conversion with file upload."""
    # Skip if file doesn't exist
    if not os.path.exists(mock_upload_file):
        pytest.skip("Mock file not created")

    with open(mock_upload_file, "rb") as f:
        response = await async_client.post(
            "/api/v1/conversions",
            files={"file": ("test_mod.jar", f, "application/java-archive")},
            data={"options": '{"assumptions": "conservative", "target_version": "1.20.0"}'},
        )

    assert response.status_code == 202
    data = response.json()
    assert "conversion_id" in data
    assert data["status"] == "queued"
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_conversion_invalid_file_type(async_client):
    """Test that invalid file types are rejected."""
    # Create a temporary file with wrong extension
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as tmp:
        tmp.write(b"fake exe content")
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            response = await async_client.post(
                "/api/v1/conversions",
                files={"file": ("malicious.exe", f, "application/x-msdownload")},
            )

        assert response.status_code == 400
        assert "not supported" in response.json()["detail"].lower()
    finally:
        os.unlink(tmp_path)


@pytest.mark.asyncio
async def test_get_conversion_status(async_client):
    """Test getting conversion status."""
    # This test would require creating a conversion first
    # For now, test that the endpoint returns 404 for non-existent conversion
    response = await async_client.get("/api/v1/conversions/nonexistent-id-12345")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_conversions(async_client):
    """Test listing conversions."""
    response = await async_client.get("/api/v1/conversions")

    assert response.status_code == 200
    data = response.json()
    assert "conversions" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert isinstance(data["conversions"], list)


@pytest.mark.asyncio
async def test_list_conversions_pagination(async_client):
    """Test conversion listing pagination."""
    response = await async_client.get("/api/v1/conversions?page=1&page_size=10")

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 10


@pytest.mark.asyncio
async def test_delete_conversion(async_client):
    """Test deleting/cancelling a conversion."""
    # Test with non-existent conversion
    response = await async_client.delete("/api/v1/conversions/nonexistent-id-12345")

    # Should return 404 or 204 depending on implementation
    assert response.status_code in [204, 404]


@pytest.mark.asyncio
async def test_download_conversion_not_found(async_client):
    """Test downloading a non-existent conversion."""
    response = await async_client.get("/api/v1/conversions/nonexistent-id-12345/download")

    assert response.status_code == 404


# Integration Tests
@pytest.mark.asyncio
async def test_websocket_with_conversion_progress():
    """Test WebSocket receives progress updates during conversion."""
    from websocket.manager import manager
    from websocket.progress_handler import ProgressHandler

    # Setup mock client
    mock_ws = MagicMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_json = AsyncMock()
    mock_ws.receive_text = AsyncMock(side_effect=["ping", "ping", Exception("Disconnect")])

    conversion_id = "test-integration-123"

    # Simulate connection
    await manager.connect(mock_ws, conversion_id)

    # Simulate progress updates
    await ProgressHandler.broadcast_agent_start(conversion_id, "JavaAnalyzerAgent")
    await ProgressHandler.broadcast_agent_update(conversion_id, "JavaAnalyzerAgent", 50, "Halfway")
    await ProgressHandler.broadcast_agent_complete(conversion_id, "JavaAnalyzerAgent")

    # Verify messages
    assert mock_ws.send_json.call_count >= 3  # Connection confirm + 3 updates

    # Check message types
    messages = [call[0][0] for call in mock_ws.send_json.call_args_list]
    message_types = [msg.get("type") for msg in messages]

    assert "connection_established" in message_types
    assert "agent_progress" in message_types

    # Cleanup
    manager.disconnect(mock_ws, conversion_id)


@pytest.mark.asyncio
async def test_progress_message_serialization():
    """Test that progress messages serialize correctly to JSON."""
    from websocket.progress_handler import progress_message, AgentStatus

    msg = progress_message(
        agent="TestAgent",
        status=AgentStatus.IN_PROGRESS,
        progress=75,
        message="Test message",
        details={"file_count": 42, "files_processed": 30},
    )

    # Test JSON serialization
    json_str = msg.model_dump_json()
    parsed = json.loads(json_str)

    assert parsed["data"]["agent"] == "TestAgent"
    assert parsed["data"]["progress"] == 75
    assert parsed["data"]["details"]["file_count"] == 42

    # Test dict serialization for WebSocket
    msg_dict = msg.model_dump()
    assert isinstance(msg_dict, dict)
    assert msg_dict["data"]["timestamp"] is not None
