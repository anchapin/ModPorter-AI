"""
Mock Redis implementation for testing purposes.

This module provides a mock implementation of Redis functionality
to enable testing without requiring a real Redis instance.
"""

import asyncio
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock
import logging

logger = logging.getLogger(__name__)


class MockRedis:
    """Mock Redis client for testing."""

    def __init__(self, decode_responses=True):
        """Initialize the mock Redis client."""
        self.decode_responses = decode_responses
        self.data: Dict[str, Any] = {}
        self.expiry: Dict[str, float] = {}
        self._closed = False

    async def from_url(self, url: str, **kwargs) -> "MockRedis":
        """Create a new Redis instance from a URL."""
        return MockRedis()

    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set a key-value pair in the mock Redis."""
        if self._closed:
            raise ConnectionError("Redis connection is closed")

        # Handle binary data for decode_responses=False
        if not self.decode_responses and isinstance(value, str):
            value = value.encode("utf-8")

        self.data[key] = value

        # Set expiry if provided
        if ex:
            self.expiry[key] = asyncio.get_event_loop().time() + ex

        return True

    async def setex(self, key: str, seconds: int, value: Any) -> bool:
        """Set a key-value pair with expiration in seconds."""
        return await self.set(key, value, ex=seconds)

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from the mock Redis."""
        if self._closed:
            raise ConnectionError("Redis connection is closed")

        # Check if key exists and hasn't expired
        if key not in self.data:
            return None

        # Check expiry
        if key in self.expiry and asyncio.get_event_loop().time() > self.expiry[key]:
            del self.data[key]
            del self.expiry[key]
            return None

        value = self.data[key]

        # Handle binary data for decode_responses=False
        if not self.decode_responses and isinstance(value, bytes):
            value = value.decode("utf-8")

        return value

    async def delete(self, key: str) -> int:
        """Delete a key from the mock Redis."""
        if self._closed:
            raise ConnectionError("Redis connection is closed")

        result = 1 if key in self.data else 0
        if key in self.data:
            del self.data[key]
        if key in self.expiry:
            del self.expiry[key]
        return result

    async def sadd(self, key: str, *values: Any) -> int:
        """Add values to a set."""
        if self._closed:
            raise ConnectionError("Redis connection is closed")

        if key not in self.data:
            self.data[key] = set()

        count = 0
        for value in values:
            if value not in self.data[key]:
                self.data[key].add(value)
                count += 1

        return count

    async def keys(self, pattern: str) -> List[str]:
        """Get all keys matching a pattern."""
        if self._closed:
            raise ConnectionError("Redis connection is closed")

        # Simple pattern matching - only support * at the end
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return [key for key in self.data.keys() if key.startswith(prefix)]
        else:
            return [key for key in self.data.keys() if key == pattern]

    async def info(self, section: Optional[str] = None) -> Dict[str, Any]:
        """Get mock Redis info."""
        if self._closed:
            raise ConnectionError("Redis connection is closed")

        return {
            "used_memory": 1234567,
            "used_memory_human": "1.23M",
            "connected_clients": 1,
            "uptime_in_seconds": 1000,
        }

    async def ping(self) -> bool:
        """Ping the mock Redis."""
        if self._closed:
            raise ConnectionError("Redis connection is closed")
        return True

    async def close(self) -> None:
        """Close the mock Redis connection."""
        self._closed = True
        self.data.clear()
        self.expiry.clear()

    def __del__(self):
        """Cleanup when object is destroyed."""
        if not self._closed:
            self._closed = True


class MockRedisAsyncio:
    """Mock for redis.asyncio module."""

    def __init__(self):
        """Initialize the mock redis.asyncio module."""
        self._instances = []

    def from_url(self, url: str, **kwargs) -> MockRedis:
        """Create a new Redis instance from a URL."""
        instance = MockRedis()
        self._instances.append(instance)
        return instance

    def __getattr__(self, name: str):
        """Pass through any other attributes to the original module if available."""
        try:
            # Avoid recursion by checking if we're already in the mock
            import sys

            if "redis" in sys.modules and isinstance(sys.modules["redis"], MagicMock):
                # We're already mocked, return a MagicMock
                return MagicMock()
            import redis.asyncio

            return getattr(redis.asyncio, name)
        except (ImportError, AttributeError):
            # Return a MagicMock for any attributes we don't explicitly mock
            return MagicMock()


# Create the mock module
mock_redis_asyncio = MockRedisAsyncio()


# Monkey patch the redis module for testing
def apply_redis_mock():
    """Apply the Redis mock to prevent connection errors."""
    import sys
    from unittest.mock import MagicMock

    # Create a mock redis module
    mock_redis = MagicMock()
    mock_redis.asyncio = mock_redis_asyncio

    # Replace the redis module in sys.modules
    sys.modules["redis"] = mock_redis
    sys.modules["redis.asyncio"] = mock_redis_asyncio


# Utility function for tests
def create_mock_redis_client(decode_responses=True) -> MockRedis:
    """Create a mock Redis client for testing."""
    return MockRedis(decode_responses=decode_responses)
