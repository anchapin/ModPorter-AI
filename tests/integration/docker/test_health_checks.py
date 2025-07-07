import pytest
import requests

@pytest.mark.integration_docker
class TestServiceHealth:
    """
    Tests for verifying the health of all services in the Docker environment.
    """

    def test_all_services_are_healthy(self, docker_environment):
        """
        This test relies on the docker_environment fixture to ensure all services
        have started and passed their initial health checks.
        It then performs an additional explicit check on the backend's health endpoint
        and a basic check on the frontend.
        """
        # The docker_environment fixture has already performed health checks.
        # If we are here, it means all services were deemed healthy by the fixture.

        backend_health_url = docker_environment.get("backend_health")
        assert backend_health_url, "Backend health URL not provided by docker_environment fixture"

        try:
            response = requests.get(backend_health_url, timeout=10)
            response.raise_for_status() # Raises an exception for 4XX/5XX status codes

            health_data = response.json()
            assert health_data.get("status") == "healthy", f"Backend service reported unhealthy: {health_data}"
            # Backend health endpoint check passed

        except requests.RequestException as e:
            pytest.fail(f"Failed to connect to backend health endpoint {backend_health_url}: {e}")

        frontend_url = docker_environment.get("frontend")
        assert frontend_url, "Frontend URL not provided by docker_environment fixture"
        try:
            response = requests.get(frontend_url, timeout=10)
            response.raise_for_status()
            # Basic check for frontend content (e.g., HTML doctype or Vite-specific script)
            # This confirms the frontend server is up and serving something.
            assert "<!doctype html>" in response.text.lower() or "vite" in response.text.lower(), \
                f"Frontend content at {frontend_url} did not seem like a valid HTML page."
            # Frontend URL check passed, content validation successful

        except requests.RequestException as e:
            pytest.fail(f"Failed to connect to frontend URL {frontend_url}: {e}")

        # If the test reaches here, it means the fixture worked and explicit checks passed.
        # Test passes implicitly without redundant assertion
