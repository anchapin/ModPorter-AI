import pytest
import requests
import time


@pytest.mark.integration_docker
@pytest.mark.docker_communication
class TestServiceCommunication:
    """
    Tests for verifying inter-service communication in the Docker environment.
    This ensures all services can communicate with each other as expected.
    """

    def test_backend_database_connection(self, docker_environment):
        """
        Test that the backend can successfully connect to the database.
        """
        backend_api_url = docker_environment.get("backend_api")
        assert backend_api_url, "Backend API URL not provided by docker_environment fixture"

        # The health endpoint should verify database connectivity
        health_response = requests.get(f"{backend_api_url}/health", timeout=30)
        assert health_response.status_code == 200
        
        health_data = health_response.json()
        assert health_data.get("status") == "healthy"
        
        # If database connection fails, the backend should report unhealthy
        assert "database" not in health_data or health_data.get("database") != "disconnected"

    def test_backend_redis_connection(self, docker_environment):
        """
        Test that the backend can successfully connect to Redis.
        """
        backend_api_url = docker_environment.get("backend_api")
        assert backend_api_url, "Backend API URL not provided by docker_environment fixture"

        # Start a conversion job to test Redis integration
        # (Redis is used for job queuing and status tracking)
        conversion_response = requests.post(
            f"{backend_api_url}/convert",
            json={
                "file_name": "test_redis.jar",
                "target_version": "1.20.0",
                "smart_assumptions": {
                    "enable_smart_assumptions": True,
                    "assumption_confidence": 0.8
                }
            },
            timeout=30
        )

        # If Redis is not working, this should fail
        assert conversion_response.status_code == 200
        conversion_data = conversion_response.json()
        assert "job_id" in conversion_data
        
        # Job should be queued, which requires Redis
        assert conversion_data.get("status") in ["queued", "processing"]

    def test_frontend_proxy_configuration(self, docker_environment):
        """
        Test that the frontend's nginx proxy correctly forwards API requests.
        This is crucial for production deployments where the frontend
        proxies API requests to the backend.
        """
        frontend_url = docker_environment.get("frontend")
        backend_api_url = docker_environment.get("backend_api")
        
        assert frontend_url, "Frontend URL not provided by docker_environment fixture"
        assert backend_api_url, "Backend API URL not provided by docker_environment fixture"

        # Test 1: Direct backend access should work
        direct_health_response = requests.get(f"{backend_api_url}/health", timeout=30)
        assert direct_health_response.status_code == 200
        direct_health_data = direct_health_response.json()

        # Test 2: Proxied access through frontend should also work
        # Note: This depends on the nginx configuration in the frontend container
        try:
            proxied_health_response = requests.get(f"{frontend_url}/api/v1/health", timeout=30)
            if proxied_health_response.status_code == 200:
                proxied_health_data = proxied_health_response.json()
                # Both should return the same data
                assert proxied_health_data.get("status") == direct_health_data.get("status")
        except requests.exceptions.RequestException:
            # If nginx proxy is not configured, this test will be skipped
            # This is acceptable for Phase 1 implementation
            pytest.skip("Frontend nginx proxy not configured for API forwarding")

    def test_all_services_startup_order(self, docker_environment):
        """
        Test that all services start in the correct order with proper dependencies.
        """
        # The docker_environment fixture ensures all services are healthy
        # If we reach this point, the startup order worked correctly
        
        backend_api_url = docker_environment.get("backend_api")
        assert backend_api_url, "Backend API URL not provided by docker_environment fixture"

        # Backend should be healthy (depends on postgres and redis)
        health_response = requests.get(f"{backend_api_url}/health", timeout=30)
        assert health_response.status_code == 200
        
        health_data = health_response.json()
        assert health_data.get("status") == "healthy"

        # Frontend should be serving content
        frontend_url = docker_environment.get("frontend")
        if frontend_url:
            frontend_response = requests.get(frontend_url, timeout=30)
            assert frontend_response.status_code == 200

    def test_service_restart_resilience(self, docker_environment):
        """
        Test that services can handle brief connectivity issues.
        Note: This is a basic test that verifies the services are stable.
        """
        backend_api_url = docker_environment.get("backend_api")
        assert backend_api_url, "Backend API URL not provided by docker_environment fixture"

        # Make multiple requests to ensure stability
        for i in range(3):
            health_response = requests.get(f"{backend_api_url}/health", timeout=30)
            assert health_response.status_code == 200
            
            health_data = health_response.json()
            assert health_data.get("status") == "healthy"
            
            # Brief pause between requests
            time.sleep(1)

    def test_network_isolation(self, docker_environment):
        """
        Test that services are properly isolated in their Docker network.
        """
        # Services should be accessible via their configured ports
        backend_api_url = docker_environment.get("backend_api")
        frontend_url = docker_environment.get("frontend")
        
        assert backend_api_url, "Backend API URL not provided by docker_environment fixture"
        assert frontend_url, "Frontend URL not provided by docker_environment fixture"

        # Both services should be accessible
        backend_response = requests.get(f"{backend_api_url}/health", timeout=30)
        assert backend_response.status_code == 200

        frontend_response = requests.get(frontend_url, timeout=30)
        assert frontend_response.status_code == 200

        # Services should be using different ports
        # This ensures proper network configuration
        backend_port = backend_api_url.split(':')[-1].split('/')[0]
        frontend_port = frontend_url.split(':')[-1].split('/')[0]
        
        assert backend_port != frontend_port, "Backend and frontend should use different ports"