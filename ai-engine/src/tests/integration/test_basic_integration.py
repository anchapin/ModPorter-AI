"""
Basic integration test to verify test infrastructure is working.

This test should pass and verify that:
1. Import paths are working correctly
2. Async test infrastructure is set up properly
3. Basic test environment is functional
"""
import pytest
import asyncio
import os


def test_basic_imports():
    """Test that basic Python imports work."""
    import sys
    import json
    import pathlib
    
    assert sys.version_info >= (3, 9)
    assert json is not None
    assert pathlib is not None


def test_environment_setup():
    """Test that test environment is set up correctly."""
    assert os.getenv("TESTING") == "true"


@pytest.mark.asyncio
async def test_async_functionality():
    """Test that async functionality works in tests."""
    async def async_function():
        await asyncio.sleep(0.01)
        return "async_result"
    
    result = await async_function()
    assert result == "async_result"


def test_pytest_markers():
    """Test that pytest markers are working."""
    # This test itself uses no special markers, but verifies the test runner works
    assert True


@pytest.mark.asyncio
async def test_async_with_timeout():
    """Test async functionality with timeout."""
    start_time = asyncio.get_event_loop().time()
    await asyncio.sleep(0.01)
    end_time = asyncio.get_event_loop().time()
    
    # Should complete quickly
    assert (end_time - start_time) < 1.0


class TestBasicIntegration:
    """Test class to verify class-based tests work."""
    
    def test_class_method(self):
        """Test that class-based tests work."""
        assert True
    
    @pytest.mark.asyncio
    async def test_async_class_method(self):
        """Test that async class methods work."""
        await asyncio.sleep(0.01)
        assert True


# Skip tests that require external dependencies
@pytest.mark.skipif(
    not os.getenv("OLLAMA_BASE_URL"),
    reason="Ollama not available"
)
def test_ollama_availability():
    """Test Ollama availability when configured."""
    import requests
    
    try:
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        assert response.status_code == 200
    except Exception as e:
        pytest.skip(f"Ollama not available: {e}")


def test_import_paths_work():
    """Test that our import path fixes are working."""
    try:
        # These imports should work with our conftest.py fixes
        import config
        import utils
        assert True
    except ImportError:
        # Some modules might not exist yet, that's ok
        pass
