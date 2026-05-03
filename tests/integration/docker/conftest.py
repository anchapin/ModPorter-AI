import os
import pytest

@pytest.fixture(scope="session")
def docker_environment():
    """
    Fixture that provides the Docker environment endpoints.
    Skips the tests if RUN_DOCKER_INTEGRATION is not set to '1'.
    """
    if os.environ.get("RUN_DOCKER_INTEGRATION") != "1":
        pytest.skip("Skipping real Docker integration tests. Set RUN_DOCKER_INTEGRATION=1 to run.")
        
    return {
        "backend_health": "http://localhost:8000/health",
        "backend_api": "http://localhost:8000/api",
        "frontend": "http://localhost:3000"
    }
