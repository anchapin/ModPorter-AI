import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from main import app
from db.base import get_db


# Mock the database dependency
@pytest.fixture
def mock_db_session():
    """Mocks the database session."""
    db_session = AsyncMock(spec=AsyncSession)
    yield db_session


@pytest.fixture
def client(mock_db_session: AsyncMock):
    """Yield a test client with a mocked database session."""
    app.dependency_overrides[get_db] = lambda: mock_db_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@patch(
    "api.collaboration.realtime_collaboration_service.create_collaboration_session",
    new_callable=AsyncMock,
)
def test_create_collaboration_session_success(
    mock_create_session: AsyncMock, client: TestClient
):
    """Test successful creation of a collaboration session."""
    mock_create_session.return_value = {
        "success": True,
        "session_id": "test_session_id",
    }
    response = client.post(
        "/api/v1/collaboration/sessions",
        json={"graph_id": "g1", "user_id": "u1", "user_name": "testuser"},
    )
    assert response.status_code == 200
    assert response.json()["session_id"] == "test_session_id"


def test_create_collaboration_session_missing_data(client: TestClient):
    """Test error on missing data when creating a collaboration session."""
    response = client.post(
        "/api/v1/collaboration/sessions",
        json={"graph_id": "g1", "user_id": "u1"},
    )
    assert response.status_code == 400
    assert "user_name are required" in response.json()["detail"]


@patch(
    "api.collaboration.realtime_collaboration_service.create_collaboration_session",
    new_callable=AsyncMock,
)
def test_create_collaboration_session_service_error(
    mock_create_session: AsyncMock, client: TestClient
):
    """Test service error when creating a collaboration session."""
    mock_create_session.return_value = {"success": False, "error": "Service error"}
    response = client.post(
        "/api/v1/collaboration/sessions",
        json={"graph_id": "g1", "user_id": "u1", "user_name": "testuser"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Service error"


@patch(
    "api.collaboration.realtime_collaboration_service.get_session_state",
    new_callable=AsyncMock,
)
def test_get_session_state_success(mock_get_state: AsyncMock, client: TestClient):
    """Test successful retrieval of session state."""
    mock_get_state.return_value = {"success": True, "state": {"users": []}}
    response = client.get("/api/v1/collaboration/sessions/s1/state")
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "state" in response.json()


@patch(
    "api.collaboration.realtime_collaboration_service.get_session_state",
    new_callable=AsyncMock,
)
def test_get_session_state_not_found(mock_get_state: AsyncMock, client: TestClient):
    """Test session not found error when getting session state."""
    mock_get_state.return_value = {"success": False, "error": "Session not found"}
    response = client.get("/api/v1/collaboration/sessions/s1/state")
    assert response.status_code == 404
    assert "Session not found" in response.json()["detail"]


@patch(
    "api.collaboration.realtime_collaboration_service.apply_operation",
    new_callable=AsyncMock,
)
def test_apply_operation_success(mock_apply_op: AsyncMock, client: TestClient):
    """Test successful application of an operation."""
    mock_apply_op.return_value = {"success": True, "operation_id": "op1"}
    response = client.post(
        "/api/v1/collaboration/sessions/s1/operations",
        json={
            "user_id": "u1",
            "operation_type": "CREATE_NODE",
            "target_id": "n1",
            "data": {},
        },
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_apply_operation_invalid_type(client: TestClient):
    """Test error on invalid operation type."""
    response = client.post(
        "/api/v1/collaboration/sessions/s1/operations",
        json={
            "user_id": "u1",
            "operation_type": "INVALID_OP",
            "target_id": "n1",
            "data": {},
        },
    )
    assert response.status_code == 400
    assert "Invalid operation_type" in response.json()["detail"]


@patch(
    "api.collaboration.realtime_collaboration_service.resolve_conflict",
    new_callable=AsyncMock,
)
def test_resolve_conflict_success(mock_resolve: AsyncMock, client: TestClient):
    """Test successful conflict resolution."""
    mock_resolve.return_value = {"success": True, "resolved_conflict": "c1"}
    response = client.post(
        "/api/v1/collaboration/sessions/s1/conflicts/c1/resolve",
        json={
            "user_id": "u1",
            "resolution_strategy": "accept_current",
            "resolution_data": {},
        },
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_resolve_conflict_missing_data(client: TestClient):
    """Test error on missing data when resolving a conflict."""
    response = client.post(
        "/api/v1/collaboration/sessions/s1/conflicts/c1/resolve",
        json={"user_id": "u1"},
    )
    assert response.status_code == 400
    assert "resolution_strategy are required" in response.json()["detail"]


@patch(
    "api.collaboration.realtime_collaboration_service.get_user_activity",
    new_callable=AsyncMock,
)
def test_get_user_activity_success(mock_get_activity: AsyncMock, client: TestClient):
    """Test successful retrieval of user activity."""
    mock_get_activity.return_value = {"success": True, "activity": []}
    response = client.get("/api/v1/collaboration/sessions/s1/users/u1/activity")
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "activity" in response.json()


@patch(
    "api.collaboration.realtime_collaboration_service.get_user_activity",
    new_callable=AsyncMock,
)
def test_get_user_activity_not_found(mock_get_activity: AsyncMock, client: TestClient):
    """Test user not found error when getting user activity."""
    mock_get_activity.return_value = {"success": False, "error": "User not found"}
    response = client.get("/api/v1/collaboration/sessions/s1/users/u1/activity")
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


@patch("api.collaboration.realtime_collaboration_service")
def test_get_active_sessions_success(mock_service, client: TestClient):
    """Test successful retrieval of active sessions."""
    mock_service.active_sessions = {
        "s1": AsyncMock(
            graph_id="g1",
            created_at=AsyncMock(isoformat=lambda: "2023-01-01T12:00:00"),
            active_users={"u1"},
            operations=["op1"],
            pending_changes=["ch1"],
        )
    }
    response = client.get("/api/v1/collaboration/sessions/active")
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert len(response.json()["active_sessions"]) == 1


def test_get_conflict_types_success(client: TestClient):
    """Test successful retrieval of conflict types."""
    response = client.get("/api/v1/collaboration/conflicts/types")
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "conflict_types" in response.json()


def test_get_operation_types_success(client: TestClient):
    """Test successful retrieval of operation types."""
    response = client.get("/api/v1/collaboration/operations/types")
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "operation_types" in response.json()


@patch("api.collaboration.realtime_collaboration_service")
def test_get_collaboration_stats_success(mock_service, client: TestClient):
    """Test successful retrieval of collaboration stats."""
    mock_service.active_sessions = {"s1": AsyncMock()}
    mock_service.user_sessions = {"u1": "s1"}
    mock_service.websocket_connections = {"u1": AsyncMock()}
    mock_service.operation_history = ["op1"]
    mock_service.conflict_resolutions = ["cr1"]

    response = client.get("/api/v1/collaboration/stats")
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "stats" in response.json()


@patch(
    "api.collaboration.realtime_collaboration_service.leave_collaboration_session",
    new_callable=AsyncMock,
)
def test_leave_collaboration_session_success(
    mock_leave_session: AsyncMock, client: TestClient
):
    """Test successful leaving of a collaboration session."""
    mock_leave_session.return_value = {"success": True}
    response = client.post(
        "/api/v1/collaboration/sessions/s1/leave", json={"user_id": "u1"}
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_leave_collaboration_session_missing_data(client: TestClient):
    """Test error on missing data when leaving a collaboration session."""
    response = client.post("/api/v1/collaboration/sessions/s1/leave", json={})
    assert response.status_code == 400
    assert "user_id is required" in response.json()["detail"]


@patch(
    "api.collaboration.realtime_collaboration_service.leave_collaboration_session",
    new_callable=AsyncMock,
)
def test_leave_collaboration_session_service_error(
    mock_leave_session: AsyncMock, client: TestClient
):
    """Test service error when leaving a collaboration session."""
    mock_leave_session.return_value = {"success": False, "error": "Service error"}
    response = client.post(
        "/api/v1/collaboration/sessions/s1/leave", json={"user_id": "u1"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Service error"


@patch(
    "api.collaboration.realtime_collaboration_service.create_collaboration_session",
    new_callable=AsyncMock,
)
def test_create_collaboration_session_exception(
    mock_create_session: AsyncMock, client: TestClient
):
    """Test exception handling when creating a collaboration session."""
    mock_create_session.side_effect = Exception("Unexpected error")
    response = client.post(
        "/api/v1/collaboration/sessions",
        json={"graph_id": "g1", "user_id": "u1", "user_name": "testuser"},
    )
    assert response.status_code == 500
    assert "Session creation failed" in response.json()["detail"]


@patch(
    "api.collaboration.realtime_collaboration_service.join_collaboration_session",
    new_callable=AsyncMock,
)
def test_join_collaboration_session_success(
    mock_join_session: AsyncMock, client: TestClient
):
    """Test successful joining of a collaboration session."""
    mock_join_session.return_value = {
        "success": True,
        "user_info": {"id": "u1", "name": "testuser"},
    }
    response = client.post(
        "/api/v1/collaboration/sessions/s1/join",
        json={"user_id": "u1", "user_name": "testuser"},
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "Session joined" in response.json()["message"]


def test_join_collaboration_session_missing_data(client: TestClient):
    """Test error on missing data when joining a collaboration session."""
    response = client.post(
        "/api/v1/collaboration/sessions/s1/join", json={"user_id": "u1"}
    )
    assert response.status_code == 400
    assert "user_name are required" in response.json()["detail"]


@patch(
    "api.collaboration.realtime_collaboration_service.join_collaboration_session",
    new_callable=AsyncMock,
)
def test_join_collaboration_session_service_error(
    mock_join_session: AsyncMock, client: TestClient
):
    """Test service error when joining a collaboration session."""
    mock_join_session.return_value = {"success": False, "error": "Service error"}
    response = client.post(
        "/api/v1/collaboration/sessions/s1/join",
        json={"user_id": "u1", "user_name": "testuser"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Service error"
