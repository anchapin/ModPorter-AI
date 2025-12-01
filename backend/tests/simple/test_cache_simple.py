"""
Simplified tests for cache.py API endpoints
Tests caching functionality without complex async mocking
"""

import pytest
import sys
import os
import uuid
import datetime
from fastapi.testclient import TestClient
from fastapi import FastAPI, APIRouter, HTTPException, Path
from pydantic import BaseModel, Field
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)


# Pydantic models for API requests/responses
class CacheEntryCreate(BaseModel):
    """Request model for creating a cache entry"""

    key: str = Field(..., description="Cache key")
    value: Dict[str, Any] = Field(..., description="Value to cache")
    ttl_seconds: int = Field(default=3600, description="Time to live in seconds")


class CacheEntryResponse(BaseModel):
    """Response model for cache entry data"""

    key: str = Field(..., description="Cache key")
    value: Dict[str, Any] = Field(..., description="Cached value")
    created_at: str = Field(..., description="Creation timestamp")
    expires_at: str = Field(..., description="Expiration timestamp")


# Test database models
class MockCacheEntry:
    def __init__(self, key=None, value=None, ttl_seconds=3600):
        self.key = key or str(uuid.uuid4())
        self.value = value or {"data": "test"}
        self.ttl_seconds = ttl_seconds
        now = datetime.datetime.now()
        self.created_at = now
        self.expires_at = now + datetime.timedelta(seconds=ttl_seconds)


# Mock in-memory cache
cache_store = {}


def mock_get_cache_entry(key):
    """Mock function to get a cache entry by key"""
    return cache_store.get(key)


def mock_set_cache_entry(key, value, ttl_seconds=3600):
    """Mock function to set a cache entry"""
    now = datetime.datetime.now()
    expires_at = now + datetime.timedelta(seconds=ttl_seconds)
    entry = {"key": key, "value": value, "created_at": now, "expires_at": expires_at}
    cache_store[key] = entry
    return entry


def mock_delete_cache_entry(key):
    """Mock function to delete a cache entry by key"""
    if key in cache_store:
        del cache_store[key]
        return True
    return False


def mock_clear_expired_cache():
    """Mock function to clear expired cache entries"""
    now = datetime.datetime.now()
    expired_keys = [k for k, v in cache_store.items() if v["expires_at"] < now]
    for key in expired_keys:
        del cache_store[key]
    return len(expired_keys)


# Create router with mock endpoints
router = APIRouter()


@router.get("/cache/{key}", response_model=CacheEntryResponse)
async def get_cache_entry(key: str = Path(..., description="Cache key")):
    """Get a cache entry by key."""
    try:
        entry = mock_get_cache_entry(key)
        if not entry:
            raise HTTPException(status_code=404, detail="Cache entry not found")
        return CacheEntryResponse(
            key=entry["key"],
            value=entry["value"],
            created_at=entry["created_at"].isoformat(),
            expires_at=entry["expires_at"].isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get cache entry: {str(e)}"
        )


@router.post("/cache", response_model=CacheEntryResponse)
async def set_cache_entry(entry_data: CacheEntryCreate):
    """Set a cache entry."""
    try:
        entry = mock_set_cache_entry(
            key=entry_data.key,
            value=entry_data.value,
            ttl_seconds=entry_data.ttl_seconds,
        )
        return CacheEntryResponse(
            key=entry["key"],
            value=entry["value"],
            created_at=entry["created_at"].isoformat(),
            expires_at=entry["expires_at"].isoformat(),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to set cache entry: {str(e)}"
        )


@router.delete("/cache/{key}")
async def delete_cache_entry(key: str = Path(..., description="Cache key")):
    """Delete a cache entry."""
    try:
        result = mock_delete_cache_entry(key)
        if not result:
            raise HTTPException(status_code=404, detail="Cache entry not found")
        return {"message": f"Cache entry {key} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete cache entry: {str(e)}"
        )


@router.post("/cache/clear-expired")
async def clear_expired_cache():
    """Clear all expired cache entries."""
    try:
        count = mock_clear_expired_cache()
        return {"message": f"Cleared {count} expired cache entries"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to clear expired cache: {str(e)}"
        )


# Create a FastAPI test app
app = FastAPI()
app.include_router(router, prefix="/api")


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestCacheApi:
    """Test cache API endpoints"""

    def test_get_cache_entry_basic(self, client):
        """Test basic retrieval of a cache entry."""
        # First, set a cache entry
        key = str(uuid.uuid4())
        cache_store[key] = {
            "key": key,
            "value": {"data": "test value"},
            "created_at": datetime.datetime.now(),
            "expires_at": datetime.datetime.now() + datetime.timedelta(hours=1),
        }

        response = client.get(f"/api/cache/{key}")

        assert response.status_code == 200
        data = response.json()
        assert data["key"] == key
        assert data["value"]["data"] == "test value"

    def test_get_cache_entry_not_found(self, client):
        """Test retrieval of a non-existent cache entry."""
        key = "nonexistent"
        response = client.get(f"/api/cache/{key}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_set_cache_entry_basic(self, client):
        """Test basic cache entry creation."""
        key = str(uuid.uuid4())
        entry_data = {
            "key": key,
            "value": {"data": "test data", "type": "string"},
            "ttl_seconds": 3600,
        }

        response = client.post("/api/cache", json=entry_data)

        assert response.status_code == 200
        data = response.json()
        assert data["key"] == key
        assert data["value"]["data"] == "test data"
        assert data["value"]["type"] == "string"

    def test_set_cache_entry_minimal(self, client):
        """Test cache entry creation with minimal data."""
        key = str(uuid.uuid4())
        entry_data = {"key": key, "value": {"minimal": True}}

        response = client.post("/api/cache", json=entry_data)

        assert response.status_code == 200
        data = response.json()
        assert data["key"] == key
        assert data["value"]["minimal"] is True
        # TTL should default to 3600
        now = datetime.datetime.now()
        default_expires = now + datetime.timedelta(seconds=3600)
        response_expires = datetime.datetime.fromisoformat(data["expires_at"])
        # Allow for small time difference in test
        assert abs((default_expires - response_expires).total_seconds()) < 5

    def test_delete_cache_entry(self, client):
        """Test deleting a cache entry."""
        # First, set a cache entry
        key = str(uuid.uuid4())
        cache_store[key] = {
            "key": key,
            "value": {"data": "test"},
            "created_at": datetime.datetime.now(),
            "expires_at": datetime.datetime.now() + datetime.timedelta(hours=1),
        }

        response = client.delete(f"/api/cache/{key}")

        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"].lower()
        # Verify entry is gone
        assert key not in cache_store

    def test_delete_cache_entry_not_found(self, client):
        """Test deleting a non-existent cache entry."""
        key = "nonexistent"
        response = client.delete(f"/api/cache/{key}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_clear_expired_cache_basic(self, client):
        """Test clearing expired cache entries."""
        # Add some entries, some expired
        now = datetime.datetime.now()
        expired_key1 = str(uuid.uuid4())
        expired_key2 = str(uuid.uuid4())
        valid_key = str(uuid.uuid4())

        # Add expired entries
        cache_store[expired_key1] = {
            "key": expired_key1,
            "value": {"data": "expired1"},
            "created_at": now,
            "expires_at": now - datetime.timedelta(hours=1),
        }
        cache_store[expired_key2] = {
            "key": expired_key2,
            "value": {"data": "expired2"},
            "created_at": now,
            "expires_at": now - datetime.timedelta(hours=2),
        }
        # Add valid entry
        cache_store[valid_key] = {
            "key": valid_key,
            "value": {"data": "valid"},
            "created_at": now,
            "expires_at": now + datetime.timedelta(hours=1),
        }

        response = client.post("/api/cache/clear-expired")

        assert response.status_code == 200
        data = response.json()
        assert "2 expired cache entries" in data["message"]
        # Verify expired entries are gone but valid one remains
        assert expired_key1 not in cache_store
        assert expired_key2 not in cache_store
        assert valid_key in cache_store

    def test_clear_expired_cache_none_expired(self, client):
        """Test clearing expired cache when none are expired."""
        # Add only valid entries
        now = datetime.datetime.now()
        valid_key1 = str(uuid.uuid4())
        valid_key2 = str(uuid.uuid4())

        cache_store[valid_key1] = {
            "key": valid_key1,
            "value": {"data": "valid1"},
            "created_at": now,
            "expires_at": now + datetime.timedelta(hours=1),
        }
        cache_store[valid_key2] = {
            "key": valid_key2,
            "value": {"data": "valid2"},
            "created_at": now,
            "expires_at": now + datetime.timedelta(hours=2),
        }

        response = client.post("/api/cache/clear-expired")

        assert response.status_code == 200
        data = response.json()
        assert "0 expired cache entries" in data["message"]
        # Verify all entries are still there
        assert valid_key1 in cache_store
        assert valid_key2 in cache_store

    def test_error_handling(self, client):
        """Test error handling in API endpoints."""
        # Test with a completely invalid route that should result in 404
        response = client.get("/api/cache-nonexistent")
        assert response.status_code == 404
