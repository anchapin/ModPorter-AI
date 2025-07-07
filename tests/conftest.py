import pytest
import requests
import time
import os
from requests.exceptions import ConnectionError
from docker.models.services import Service as DockerService # To prevent pydantic clash if any
from docker.errors import NotFound

# Define service names and their health check endpoints/ports if applicable
SERVICE_HEALTH_CHECKS = {
    "frontend": {"url": "http://localhost:3000", "type": "http"}, # Basic check, real health might be via API
    "backend": {"url": "http://localhost:8000/api/v1/health", "type": "http"},
    "redis": {"type": "docker_health"}, # Relies on Docker's health check
    "postgres": {"type": "docker_health"}, # Relies on Docker's health check
    "ai-engine": {"type": "docker_health_optional"}, # ai-engine might not have an explicit health check endpoint, rely on container being up
}

# Timeout for waiting for services to become healthy (seconds)
SERVICE_WAIT_TIMEOUT = 180
# Interval for polling health checks (seconds)
POLL_INTERVAL = 5

@pytest.fixture(scope="class")
def docker_environment(docker_compose_file, docker_compose_project_name, docker_services):
    """
    Manages the full application stack using docker-compose.
    - Starts all services defined in tests/docker-compose.test.yml.
    - Waits for services to be healthy.
    - Provides service URLs/info to tests.
    - Tears down the stack after tests.
    """
    # docker_compose_file and docker_compose_project_name are provided by pytest-docker
    # docker_services is also a pytest-docker fixture to interact with services

    # Ensure docker-compose path is correct (relative to project root)
    # This fixture assumes tests/docker-compose.test.yml exists
    # pytest-docker should handle the `up` command implicitly if configured via pytest.ini or command line.
    # If not, we might need: `docker_compose.up(detach=True, build=True)`
    # For now, assume pytest-docker handles 'up' based on docker_compose_file.

    service_urls = {
        "frontend": "http://localhost:3000",
        "backend_api": "http://localhost:8000/api/v1", # Base API URL
        "backend_health": SERVICE_HEALTH_CHECKS["backend"]["url"]
    }

    # Wait for services to be healthy
    start_time = time.time()
    services_to_check = set(SERVICE_HEALTH_CHECKS.keys())

    print(f"Waiting for services to become healthy: {', '.join(services_to_check)}")

    while services_to_check and (time.time() - start_time) < SERVICE_WAIT_TIMEOUT:
        still_waiting_for = set()
        for service_name in list(services_to_check):
            try:
                service_config = SERVICE_HEALTH_CHECKS[service_name]
                is_healthy = False

                if service_config["type"] == "http":
                    response = requests.get(service_config["url"], timeout=POLL_INTERVAL / 2)
                    if response.status_code >= 200 and response.status_code < 300:
                        # For backend, check specific health status if possible
                        if service_name == "backend":
                            if response.json().get("status") == "healthy":
                                is_healthy = True
                        else: # For frontend, any 2xx is good enough for now
                            is_healthy = True
                    if is_healthy:
                        print(f"Service '{service_name}' is healthy via HTTP check.")
                    else:
                        print(f"Service '{service_name}' HTTP check failed: Status {response.status_code}, Content: {response.text[:100]}")
                        still_waiting_for.add(service_name)

                elif service_config["type"] == "docker_health" or service_config["type"] == "docker_health_optional":
                    # Use docker_services fixture to check health
                    # The service name in docker-compose might be different from our key
                    # (e.g., projectname_service_1)
                    # We need to find the actual Docker service object.
                    # Note: pytest-docker's `docker_services.is_healthy(service_name)` might be simpler
                    # if service names align perfectly or are managed by pytest-docker.
                    # Let's try a more direct approach if `is_healthy` is available.

                    # Construct the full service name as Docker Compose does
                    # Example: modporterai_backend_1 (if project name is modporterai)
                    # However, pytest-docker's `docker_services.is_healthy()` expects the logical service name.

                    if docker_services.is_healthy(service_name):
                        is_healthy = True
                        print(f"Service '{service_name}' is healthy via Docker health check.")
                    elif service_config["type"] == "docker_health_optional":
                        # For optional health check, if container is running, consider it "sufficiently" healthy for now
                        # This is a fallback if explicit Docker health check isn't configured or passing yet for ai-engine
                        try:
                            # Get the Docker SDK client from pytest-docker
                            client = docker_services._docker_compose.client # Access underlying client

                            # Find the container for the service. This is a bit complex.
                            # We need to list containers for the project and find the one for this service.
                            # For now, let's assume `is_healthy` or direct check is enough.
                            # A simpler check: if `is_healthy` returned False, but it's optional,
                            # we might just log it and proceed, or check if the container exists.

                            # Let's assume for ai-engine, if not explicitly healthy by Docker's check,
                            # we'll just wait and hope it starts, or rely on other services failing
                            # if it's a hard dependency. The current `is_healthy` should suffice.
                            print(f"Service '{service_name}' (optional health check) Docker health check not (yet) passing.")
                            still_waiting_for.add(service_name) # Keep waiting
                        except Exception as e:
                            print(f"Could not check Docker container status for '{service_name}': {e}")
                            still_waiting_for.add(service_name)
                    else: # Mandatory Docker health check failed
                        print(f"Service '{service_name}' Docker health check not (yet) passing.")
                        still_waiting_for.add(service_name)

                if is_healthy:
                    services_to_check.remove(service_name)

            except ConnectionError:
                print(f"Service '{service_name}' not yet responding (ConnectionError).")
                still_waiting_for.add(service_name)
            except requests.RequestException as e:
                print(f"Error checking health for service '{service_name}': {e}")
                still_waiting_for.add(service_name)
            except Exception as e: # Catch other errors like Docker API issues
                print(f"Generic error checking health for service '{service_name}': {e}")
                still_waiting_for.add(service_name)

        services_to_check = still_waiting_for
        if services_to_check:
            print(f"Still waiting for services: {', '.join(services_to_check)}. Polling again in {POLL_INTERVAL}s.")
            time.sleep(POLL_INTERVAL)

    if services_to_check: # Timeout reached
        failed_services = ", ".join(services_to_check)
        # Capture logs from failed services
        for service_name in services_to_check:
            try:
                # Service name in docker-compose might be <project>_<service_name>_1
                # However, `docker_services.get_logs` expects the logical service name.
                logs = docker_services.get_logs(service_name)
                if logs:
                    print(f"Logs for service '{service_name}':")
                    for line in logs:
                        print(line.decode('utf-8').strip())
            except Exception as e:
                print(f"Could not retrieve logs for service '{service_name}': {e}")
        pytest.fail(f"Timeout: Services not healthy after {SERVICE_WAIT_TIMEOUT}s: {failed_services}")

    print("All services are healthy.")
    yield service_urls

    # Teardown is implicitly handled by pytest-docker when the fixture scope ends.
    # It will run `docker-compose down`.
    # If specific cleanup is needed (e.g., `docker_compose.down(volumes=True)`),
    # it can be added here or configured in pytest.ini.
    print("Docker environment teardown will be handled by pytest-docker.")

# It's good practice to configure pytest-docker via pytest.ini,
# but we can also provide default paths here if needed.
@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    # Ensure the path is relative to the root of the project
    return os.path.join(pytestconfig.rootdir, "tests", "docker-compose.test.yml")

# Note: docker_compose_project_name can also be set in pytest.ini to avoid collisions
# For example:
# [pytest]
# docker_compose_project_name = modportertest
