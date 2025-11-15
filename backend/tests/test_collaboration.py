
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from backend.src.api.collaboration import router

client = TestClient(router)

@pytest.fixture
def mock_db_session():
    with patch('backend.src.api.collaboration.get_db') as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        yield mock_db

@patch('backend.src.api.collaboration.realtime_collaboration_service.create_collaboration_session', new_callable=AsyncMock)
def test_create_collaboration_session_success(mock_create_session, mock_db_session):
    session_data = {
        "graph_id": "test_graph",
        "user_id": "test_user",
        "user_name": "Test User"
    }
    mock_create_session.return_value = {"success": True, "session_id": "test_session"}

    response = client.post("/sessions", json=session_data)

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "session_id" in response.json()
    mock_create_session.assert_called_once()

def test_create_collaboration_session_missing_data(mock_db_session):
    session_data = {
        "graph_id": "test_graph",
        "user_id": "test_user"
    }

    response = client.post("/sessions", json=session_data)

    assert response.status_code == 400
    assert "user_name are required" in response.json()["detail"]
