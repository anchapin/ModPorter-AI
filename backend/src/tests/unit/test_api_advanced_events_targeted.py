
import pytest
import uuid
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

# Import the router to test
from api.advanced_events import router, EventType, EventTriggerType, EventActionType

# Create a test FastAPI app
app = FastAPI()
app.include_router(router)

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

class TestAdvancedEventsAPITargeted:
    
    def test_get_event_types(self, client):
        response = client.get("/events/types")
        assert response.status_code == 200
        assert any(item["type"] == "entity_spawn" for item in response.json())

    def test_get_trigger_types(self, client):
        response = client.get("/events/triggers")
        assert response.status_code == 200
        assert any(item["type"] == "once" for item in response.json())

    def test_get_action_types(self, client):
        response = client.get("/events/actions")
        assert response.status_code == 200
        assert any(item["type"] == "command" for item in response.json())

    def test_get_event_templates(self, client):
        response = client.get("/events/templates")
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert response.json()[0]["name"] == "Entity Drops System"

    @patch("api.advanced_events.get_db")
    @patch("api.advanced_events.crud")
    async def test_create_event_system_success(self, mock_crud, mock_get_db, client):
        mock_get_db.return_value = AsyncMock()
        
        conversion_id = str(uuid.uuid4())
        mock_job = MagicMock()
        mock_job.id = conversion_id
        mock_crud.get_job = AsyncMock(return_value=mock_job)
        mock_crud.create_behavior_file = AsyncMock()
        
        payload = {
            "name": "Test System",
            "description": "Test Description",
            "config": {
                "event_type": "entity_spawn",
                "namespace": "test",
                "priority": 0,
                "enabled": True,
                "debug": False
            },
            "triggers": [],
            "actions": [],
            "variables": {},
            "version": "1.0.0"
        }
        
        response = client.post(f"/events/systems?conversion_id={conversion_id}", json=payload)
        
        assert response.status_code == 201
        assert response.json()["name"] == "Test System"
        mock_crud.create_behavior_file.assert_called_once()

    def test_create_event_system_invalid_uuid(self, client):
        payload = {
            "name": "Test", "description": "Test", "config": {"event_type": "custom"},
            "triggers": [], "actions": [], "variables": {}, "version": "1.0.0"
        }
        response = client.post("/events/systems?conversion_id=invalid-uuid", json=payload)
        assert response.status_code == 400
        assert "Invalid conversion ID format" in response.json()["detail"]

    @patch("api.advanced_events.get_db")
    @patch("api.advanced_events.crud")
    async def test_create_event_system_not_found(self, mock_crud, mock_get_db, client):
        mock_get_db.return_value = AsyncMock()
        mock_crud.get_job = AsyncMock(return_value=None)
        
        conversion_id = str(uuid.uuid4())
        response = client.post(f"/events/systems?conversion_id={conversion_id}", json={
            "name": "Test", "description": "Test", "config": {"event_type": "custom"},
            "triggers": [], "actions": [], "variables": {}, "version": "1.0.0"
        })
        assert response.status_code == 404

    def test_get_event_system_not_implemented(self, client):
        response = client.get("/events/systems/some-id")
        assert response.status_code == 501

    def test_test_event_system(self, client):
        payload = {
            "test_data": {"mock_actions": [{}, {}]},
            "expected_results": [],
            "dry_run": True
        }
        response = client.post("/events/systems/some-id/test", json=payload)
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["executed_actions"] == 2

    @patch("api.advanced_events.get_db")
    def test_generate_event_system_functions(self, mock_get_db, client):
        mock_get_db.return_value = AsyncMock()
        with patch("api.advanced_events.generate_event_functions_background") as mock_bg:
            response = client.post("/events/systems/some-id/generate")
            assert response.status_code == 201
            assert "started" in response.json()["message"]

    def test_get_event_system_debug(self, client):
        response = client.get("/events/systems/some-id/debug")
        assert response.status_code == 200
        assert response.json()["system_id"] == "some-id"
