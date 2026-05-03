import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from api.advanced_events import router, EventType, EventTriggerType, EventActionType
from unittest.mock import AsyncMock, patch, MagicMock
import uuid


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.mark.asyncio
async def test_get_event_types(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/events/types")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert any(item["type"] == EventType.BLOCK_BREAK.value for item in data)


@pytest.mark.asyncio
async def test_get_trigger_types(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/events/triggers")
    assert response.status_code == 200
    assert len(response.json()) > 0


@pytest.mark.asyncio
async def test_get_action_types(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/events/actions")
    assert response.status_code == 200
    assert len(response.json()) > 0


@pytest.mark.asyncio
async def test_get_event_templates(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/events/templates")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["name"] == "Entity Drops System"


@pytest.mark.asyncio
async def test_create_event_system_invalid_uuid(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/events/systems",
            params={"conversion_id": "invalid-uuid"},
            json={
                "name": "Test System",
                "description": "Test Desc",
                "config": {"event_type": "block_break"},
                "triggers": [],
                "actions": [],
                "variables": {},
            },
        )
    assert response.status_code == 400
    assert "Invalid conversion ID format" in response.json()["detail"]


@pytest.mark.asyncio
@patch("db.crud.get_job", new_callable=AsyncMock)
async def test_create_event_system_not_found(mock_get_job, app):
    mock_get_job.return_value = None
    conv_id = str(uuid.uuid4())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/events/systems",
            params={"conversion_id": conv_id},
            json={
                "name": "Test System",
                "description": "Test Desc",
                "config": {"event_type": "block_break"},
                "triggers": [],
                "actions": [],
                "variables": {},
            },
        )
    assert response.status_code == 404
    assert "Conversion not found" in response.json()["detail"]


@pytest.mark.asyncio
@patch("db.crud.get_job", new_callable=AsyncMock)
@patch("db.crud.create_behavior_file", new_callable=AsyncMock)
async def test_create_event_system_success(mock_create_file, mock_get_job, app):
    mock_get_job.return_value = MagicMock()
    mock_create_file.return_value = MagicMock()
    conv_id = str(uuid.uuid4())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/events/systems",
            params={"conversion_id": conv_id},
            json={
                "name": "Test System",
                "description": "Test Desc",
                "config": {"event_type": "block_break"},
                "triggers": [],
                "actions": [],
                "variables": {},
            },
        )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test System"
    assert "event_system_" in data["id"]


@pytest.mark.asyncio
async def test_get_event_system_501(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/events/systems/some-id")
    assert response.status_code == 501


@pytest.mark.asyncio
async def test_test_event_system(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/events/systems/some-id/test",
            json={"test_data": {"mock_actions": [1, 2]}, "dry_run": True},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["executed_actions"] == 2


@pytest.mark.asyncio
async def test_generate_functions(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/events/systems/some-id/generate")
    assert response.status_code == 201
    assert "generation started" in response.json()["message"]


@pytest.mark.asyncio
async def test_get_debug_info(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/events/systems/some-id/debug")
    assert response.status_code == 200
    data = response.json()
    assert data["system_id"] == "some-id"
    assert "performance_stats" in data
