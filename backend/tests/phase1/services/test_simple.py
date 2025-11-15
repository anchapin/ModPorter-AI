"""
Simple test file for Phase 1 tests.
This is a basic test to verify our test infrastructure is working.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio
import uuid


class TestSimple:
    """Simple test cases to verify test infrastructure."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session for testing."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        return session

    def test_simple_assertion(self):
        """A simple test that should always pass."""
        assert True
        assert 1 + 1 == 2
        assert "hello" + " world" == "hello world"

    def test_simple_fixture(self, mock_db_session):
        """Test that our fixture is working."""
        # Verify the mock is of the right type
        assert mock_db_session is not None
        assert hasattr(mock_db_session, 'execute')
        assert hasattr(mock_db_session, 'commit')
        assert hasattr(mock_db_session, 'rollback')

    @pytest.mark.asyncio
    async def test_async_function(self, mock_db_session):
        """Test an async function."""
        # Mock an async operation
        mock_db_session.execute.return_value = MagicMock()
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None

        # Call the async function
        await mock_db_session.execute("SELECT * FROM table")

        # Verify it was called
        mock_db_session.execute.assert_called_once_with("SELECT * FROM table")



    def test_uuid_generation(self):
        """Test UUID generation."""
        # Generate a UUID
        test_uuid = uuid.uuid4()

        # Verify it's a valid UUID
        assert isinstance(test_uuid, uuid.UUID)
        assert test_uuid.version == 4  # UUID v4 is random

    def test_with_fixtures(self):
        """Test using multiple fixtures."""
        # Test data
        test_dict = {"key1": "value1", "key2": "value2"}

        # Verify structure
        assert isinstance(test_dict, dict)
        assert "key1" in test_dict
        assert test_dict["key1"] == "value1"

    @pytest.mark.parametrize("input_val,expected", [
        (1, 2),
        (2, 4),
        (3, 6),
        (0, 0)
    ])
    def test_parameterized(self, input_val, expected):
        """Test with parameterized values."""
        result = input_val * 2
        assert result == expected

    @pytest.mark.slow
    def test_marked_slow(self):
        """A test marked as slow."""
        # Simulate a slow operation
        import time
        time.sleep(0.1)
        assert True

    def test_with_raises(self):
        """Test that verifies an exception is raised."""
        with pytest.raises(ValueError):
            raise ValueError("Expected error")

    def test_dict_operations(self):
        """Test dictionary operations."""
        test_dict = {}

        # Add items
        test_dict["a"] = 1
        test_dict["b"] = 2

        # Verify
        assert "a" in test_dict
        assert test_dict["b"] == 2
        assert len(test_dict) == 2

        # Remove item
        del test_dict["a"]
        assert "a" not in test_dict
        assert len(test_dict) == 1

    def test_list_operations(self):
        """Test list operations."""
        test_list = [1, 2, 3]

        # Add item
        test_list.append(4)
        assert 4 in test_list
        assert len(test_list) == 4

        # Remove item
        test_list.remove(1)
        assert 1 not in test_list
        assert len(test_list) == 3

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test using an async context manager."""
        # Create a simple async context manager
        class SimpleAsyncContext:
            async def __aenter__(self):
                self.value = "entered"
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                self.value = "exited"

        # Use the context manager
        async with SimpleAsyncContext() as ctx:
            assert ctx.value == "entered"

        # Verify it was exited
        assert ctx.value == "exited"
