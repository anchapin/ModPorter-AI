"""
Tests for status page API endpoints.

Issue #1153: Pre-beta: Uptime monitoring and public status page
"""

import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.mark.asyncio
async def test_status_endpoint_returns_components():
    """Test that status endpoint returns all expected components"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/status")

    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert "timestamp" in data
    assert "components" in data
    assert "message" in data

    component_names = [c["name"] for c in data["components"]]
    assert "Web App" in component_names
    assert "API" in component_names
    assert "Database" in component_names
    assert "Conversion Queue" in component_names


@pytest.mark.asyncio
async def test_status_endpoint_overall_status():
    """Test that overall status reflects component health"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/status")

    data = response.json()

    valid_statuses = ["operational", "degraded", "major_outage", "maintenance"]
    assert data["status"] in valid_statuses


@pytest.mark.asyncio
async def test_status_health_endpoint():
    """Test health alias endpoint"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/status/health")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "components" in data


@pytest.mark.asyncio
async def test_status_components_endpoint():
    """Test components detail endpoint"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/status/components")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 4


@pytest.mark.asyncio
async def test_status_component_structure():
    """Test that each component has required fields"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/status")

    data = response.json()
    required_fields = ["name", "status", "last_checked"]

    for component in data["components"]:
        for field in required_fields:
            assert field in component, f"Missing field {field} in component"

        valid_statuses = ["operational", "degraded", "partial_outage", "major_outage", "maintenance"]
        assert component["status"] in valid_statuses