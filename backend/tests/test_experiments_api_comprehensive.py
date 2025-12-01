"""
Comprehensive Test Suite for Experiments API

This module provides extensive test coverage for the A/B testing experiments API,
including experiment management, variant handling, and results tracking.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Import the router
from src.api.experiments import router

# Create FastAPI app with the router
app = FastAPI()
app.include_router(router, prefix="/api")


class TestExperimentsAPI:
    """Comprehensive test suite for experiments API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def sample_experiment_data(self):
        """Sample experiment data for testing."""
        return {
            "name": "UI Conversion Test",
            "description": "Testing new checkout flow",
            "start_date": datetime.utcnow().isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "traffic_allocation": 50,
        }

    @pytest.fixture
    def sample_variant_data(self):
        """Sample variant data for testing."""
        return {
            "name": "New Checkout Flow",
            "description": "Simplified checkout process",
            "is_control": False,
            "strategy_config": {
                "new_button_color": "#FF5722",
                "simplified_steps": True,
                "trust_badges": True,
            },
        }

    @pytest.fixture
    def sample_result_data(self):
        """Sample result data for testing."""
        return {
            "variant_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "kpi_quality": 85.5,
            "kpi_speed": 1200,
            "kpi_cost": 0.15,
            "user_feedback_score": 4.2,
            "user_feedback_text": "Much easier to use",
            "metadata": {
                "browser": "Chrome",
                "device": "Desktop",
                "user_type": "returning",
            },
        }

    # Experiment Management Tests

    def test_create_experiment_success(self, client, sample_experiment_data):
        """Test successful creation of an experiment."""
        response = client.post("/api/experiments", json=sample_experiment_data)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "id" in data
        assert "name" in data
        assert "description" in data
        assert "status" in data
        assert "traffic_allocation" in data
        assert "created_at" in data
        assert "updated_at" in data

        # Verify data mapping
        assert data["name"] == sample_experiment_data["name"]
        assert data["description"] == sample_experiment_data["description"]
        assert (
            data["traffic_allocation"] == sample_experiment_data["traffic_allocation"]
        )

    def test_create_experiment_invalid_traffic_allocation_negative(self, client):
        """Test creation with negative traffic allocation."""
        experiment_data = {"name": "Test Experiment", "traffic_allocation": -10}

        response = client.post("/api/experiments", json=experiment_data)
        assert response.status_code == 400

    def test_create_experiment_invalid_traffic_allocation_over_100(self, client):
        """Test creation with traffic allocation over 100."""
        experiment_data = {"name": "Test Experiment", "traffic_allocation": 150}

        response = client.post("/api/experiments", json=experiment_data)
        assert response.status_code == 400

    def test_create_experiment_default_traffic_allocation(self, client):
        """Test creation with default traffic allocation."""
        experiment_data = {"name": "Test Experiment", "description": "Test description"}

        response = client.post("/api/experiments", json=experiment_data)
        assert response.status_code == 200

        data = response.json()
        # Should default to 100
        assert data["traffic_allocation"] == 100

    def test_list_experiments_default(self, client):
        """Test listing experiments with default parameters."""
        response = client.get("/api/experiments")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        # Should return experiment objects with proper structure
        if data:
            experiment = data[0]
            assert "id" in experiment
            assert "name" in experiment
            assert "status" in experiment

    def test_list_experiments_with_status_filter(self, client):
        """Test listing experiments with status filter."""
        response = client.get("/api/experiments?status=active")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_experiments_pagination_skip_zero(self, client):
        """Test listing experiments with skip=0."""
        response = client.get("/api/experiments?skip=0&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_experiments_pagination_valid_range(self, client):
        """Test listing experiments with valid pagination range."""
        response = client.get("/api/experiments?skip=20&limit=50")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_experiments_invalid_skip_negative(self, client):
        """Test listing experiments with negative skip."""
        response = client.get("/api/experiments?skip=-5")

        assert response.status_code == 400
        assert "skip must be non-negative" in response.json()["detail"]

    def test_list_experiments_invalid_limit_zero(self, client):
        """Test listing experiments with limit=0."""
        response = client.get("/api/experiments?limit=0")

        assert response.status_code == 400
        assert "limit must be between 1 and 1000" in response.json()["detail"]

    def test_list_experiments_invalid_limit_over_max(self, client):
        """Test listing experiments with limit over 1000."""
        response = client.get("/api/experiments?limit=1500")

        assert response.status_code == 400
        assert "limit must be between 1 and 1000" in response.json()["detail"]

    def test_get_experiment_success(self, client):
        """Test getting a specific experiment by ID."""
        experiment_id = str(uuid.uuid4())

        response = client.get(f"/api/experiments/{experiment_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == experiment_id
        assert "name" in data
        assert "status" in data
        assert "traffic_allocation" in data

    def test_get_experiment_invalid_uuid_format(self, client):
        """Test getting experiment with invalid UUID format."""
        experiment_id = "invalid-uuid-format"

        response = client.get(f"/api/experiments/{experiment_id}")

        assert response.status_code == 400
        assert "Invalid experiment ID format" in response.json()["detail"]

    def test_update_experiment_success(self, client, sample_experiment_data):
        """Test successful update of an experiment."""
        experiment_id = str(uuid.uuid4())
        update_data = {
            "name": "Updated Experiment Name",
            "description": "Updated description",
            "status": "active",
        }

        response = client.put(f"/api/experiments/{experiment_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == experiment_id
        # Should reflect updated values
        assert data["name"] == update_data["name"]

    def test_update_experiment_invalid_uuid_format(self, client):
        """Test updating experiment with invalid UUID format."""
        experiment_id = "invalid-uuid-format"
        update_data = {"name": "Updated Name"}

        response = client.put(f"/api/experiments/{experiment_id}", json=update_data)

        assert response.status_code == 400
        assert "Invalid experiment ID format" in response.json()["detail"]

    def test_update_experiment_invalid_status(self, client):
        """Test updating experiment with invalid status."""
        experiment_id = str(uuid.uuid4())
        update_data = {"status": "invalid_status"}

        response = client.put(f"/api/experiments/{experiment_id}", json=update_data)

        assert response.status_code == 400
        assert "Invalid status" in response.json()["detail"]

    def test_update_experiment_valid_statuses(self, client):
        """Test updating experiment with each valid status."""
        valid_statuses = ["draft", "active", "paused", "completed"]
        experiment_id = str(uuid.uuid4())

        for status in valid_statuses:
            update_data = {"status": status}
            response = client.put(f"/api/experiments/{experiment_id}", json=update_data)
            assert response.status_code == 200

    def test_update_experiment_invalid_traffic_allocation(self, client):
        """Test updating experiment with invalid traffic allocation."""
        experiment_id = str(uuid.uuid4())
        update_data = {"traffic_allocation": 150}

        response = client.put(f"/api/experiments/{experiment_id}", json=update_data)

        assert response.status_code == 400
        assert (
            "Traffic allocation must be between 0 and 100" in response.json()["detail"]
        )

    def test_delete_experiment_success(self, client):
        """Test successful deletion of an experiment."""
        experiment_id = str(uuid.uuid4())

        response = client.delete(f"/api/experiments/{experiment_id}")

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "deleted successfully" in data["message"]

    def test_delete_experiment_invalid_uuid_format(self, client):
        """Test deleting experiment with invalid UUID format."""
        experiment_id = "invalid-uuid-format"

        response = client.delete(f"/api/experiments/{experiment_id}")

        assert response.status_code == 400
        assert "Invalid experiment ID format" in response.json()["detail"]

    # Variant Management Tests

    def test_create_experiment_variant_success(self, client, sample_variant_data):
        """Test successful creation of an experiment variant."""
        experiment_id = str(uuid.uuid4())

        response = client.post(
            f"/api/experiments/{experiment_id}/variants", json=sample_variant_data
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "id" in data
        assert "experiment_id" in data
        assert "name" in data
        assert "is_control" in data
        assert "strategy_config" in data
        assert "created_at" in data
        assert "updated_at" in data

        # Verify data mapping
        assert data["experiment_id"] == experiment_id
        assert data["name"] == sample_variant_data["name"]
        assert data["is_control"] == sample_variant_data["is_control"]

    def test_create_experiment_variant_invalid_experiment_uuid(self, client):
        """Test creating variant with invalid experiment UUID format."""
        experiment_id = "invalid-uuid-format"
        variant_data = {"name": "Test Variant"}

        response = client.post(
            f"/api/experiments/{experiment_id}/variants", json=variant_data
        )

        assert response.status_code == 400
        assert "Invalid experiment ID format" in response.json()["detail"]

    def test_create_experiment_variant_default_is_control(self, client):
        """Test creating variant with default is_control value."""
        experiment_id = str(uuid.uuid4())
        variant_data = {"name": "Test Variant"}

        response = client.post(
            f"/api/experiments/{experiment_id}/variants", json=variant_data
        )

        assert response.status_code == 200

        data = response.json()
        assert not data["is_control"]  # Should default to False

    def test_list_experiment_variants_success(self, client):
        """Test listing variants for an experiment."""
        experiment_id = str(uuid.uuid4())

        response = client.get(f"/api/experiments/{experiment_id}/variants")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        # Should return variant objects with proper structure
        if data:
            variant = data[0]
            assert "id" in variant
            assert "experiment_id" in variant
            assert "name" in variant
            assert "is_control" in variant

    def test_list_experiment_variants_invalid_experiment_uuid(self, client):
        """Test listing variants with invalid experiment UUID format."""
        experiment_id = "invalid-uuid-format"

        response = client.get(f"/api/experiments/{experiment_id}/variants")

        assert response.status_code == 400
        assert "Invalid experiment ID format" in response.json()["detail"]

    def test_get_experiment_variant_success(self, client):
        """Test getting a specific variant."""
        experiment_id = str(uuid.uuid4())
        variant_id = str(uuid.uuid4())

        response = client.get(f"/api/experiments/{experiment_id}/variants/{variant_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == variant_id
        assert data["experiment_id"] == experiment_id
        assert "name" in data
        assert "is_control" in data

    def test_get_experiment_variant_invalid_experiment_uuid(self, client):
        """Test getting variant with invalid experiment UUID."""
        experiment_id = "invalid-uuid-format"
        variant_id = str(uuid.uuid4())

        response = client.get(f"/api/experiments/{experiment_id}/variants/{variant_id}")

        assert response.status_code == 400
        assert "Invalid ID format" in response.json()["detail"]

    def test_get_experiment_variant_invalid_variant_uuid(self, client):
        """Test getting variant with invalid variant UUID."""
        experiment_id = str(uuid.uuid4())
        variant_id = "invalid-uuid-format"

        response = client.get(f"/api/experiments/{experiment_id}/variants/{variant_id}")

        assert response.status_code == 400
        assert "Invalid ID format" in response.json()["detail"]

    def test_update_experiment_variant_success(self, client):
        """Test successful update of an experiment variant."""
        experiment_id = str(uuid.uuid4())
        variant_id = str(uuid.uuid4())
        update_data = {
            "name": "Updated Variant Name",
            "description": "Updated description",
            "is_control": True,
        }

        response = client.put(
            f"/api/experiments/{experiment_id}/variants/{variant_id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == variant_id
        assert data["experiment_id"] == experiment_id
        assert data["name"] == update_data["name"]

    def test_update_experiment_variant_invalid_uuids(self, client):
        """Test updating variant with invalid UUIDs."""
        experiment_id = "invalid-experiment-uuid"
        variant_id = "invalid-variant-uuid"
        update_data = {"name": "Updated Name"}

        response = client.put(
            f"/api/experiments/{experiment_id}/variants/{variant_id}", json=update_data
        )

        assert response.status_code == 400
        assert "Invalid ID format" in response.json()["detail"]

    def test_delete_experiment_variant_success(self, client):
        """Test successful deletion of an experiment variant."""
        experiment_id = str(uuid.uuid4())
        variant_id = str(uuid.uuid4())

        response = client.delete(
            f"/api/experiments/{experiment_id}/variants/{variant_id}"
        )

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "deleted successfully" in data["message"]

    def test_delete_experiment_variant_invalid_uuids(self, client):
        """Test deleting variant with invalid UUIDs."""
        experiment_id = "invalid-experiment-uuid"
        variant_id = "invalid-variant-uuid"

        response = client.delete(
            f"/api/experiments/{experiment_id}/variants/{variant_id}"
        )

        assert response.status_code == 400
        assert "Invalid ID format" in response.json()["detail"]

    # Results Management Tests

    def test_create_experiment_result_success(self, client, sample_result_data):
        """Test successful recording of an experiment result."""
        response = client.post("/api/experiment_results", json=sample_result_data)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "id" in data
        assert "variant_id" in data
        assert "session_id" in data
        assert "kpi_quality" in data
        assert "kpi_speed" in data
        assert "kpi_cost" in data
        assert "user_feedback_score" in data
        assert "user_feedback_text" in data
        assert "metadata" in data
        assert "created_at" in data

        # Verify data mapping
        assert data["variant_id"] == sample_result_data["variant_id"]
        assert data["session_id"] == sample_result_data["session_id"]
        assert data["kpi_quality"] == sample_result_data["kpi_quality"]
        assert data["user_feedback_score"] == sample_result_data["user_feedback_score"]

    def test_create_experiment_result_invalid_variant_uuid(self, client):
        """Test creating result with invalid variant UUID."""
        result_data = {"variant_id": "invalid-uuid", "session_id": str(uuid.uuid4())}

        response = client.post("/api/experiment_results", json=result_data)

        assert response.status_code == 400
        assert "Invalid ID format" in response.json()["detail"]

    def test_create_experiment_result_invalid_session_uuid(self, client):
        """Test creating result with invalid session UUID."""
        result_data = {"variant_id": str(uuid.uuid4()), "session_id": "invalid-uuid"}

        response = client.post("/api/experiment_results", json=result_data)

        assert response.status_code == 400
        assert "Invalid ID format" in response.json()["detail"]

    def test_create_experiment_result_invalid_kpi_quality_negative(self, client):
        """Test creating result with negative KPI quality."""
        result_data = {
            "variant_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "kpi_quality": -10,
        }

        response = client.post("/api/experiment_results", json=result_data)

        assert response.status_code == 400
        assert "kpi_quality must be between 0 and 100" in response.json()["detail"]

    def test_create_experiment_result_invalid_kpi_quality_over_100(self, client):
        """Test creating result with KPI quality over 100."""
        result_data = {
            "variant_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "kpi_quality": 150,
        }

        response = client.post("/api/experiment_results", json=result_data)

        assert response.status_code == 400
        assert "kpi_quality must be between 0 and 100" in response.json()["detail"]

    def test_create_experiment_result_invalid_user_feedback_score_low(self, client):
        """Test creating result with user feedback score below minimum."""
        result_data = {
            "variant_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "user_feedback_score": 0,
        }

        response = client.post("/api/experiment_results", json=result_data)

        assert response.status_code == 400
        assert (
            "user_feedback_score must be between 1 and 5" in response.json()["detail"]
        )

    def test_create_experiment_result_invalid_user_feedback_score_high(self, client):
        """Test creating result with user feedback score above maximum."""
        result_data = {
            "variant_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "user_feedback_score": 6,
        }

        response = client.post("/api/experiment_results", json=result_data)

        assert response.status_code == 400
        assert (
            "user_feedback_score must be between 1 and 5" in response.json()["detail"]
        )

    def test_create_experiment_result_optional_fields_none(self, client):
        """Test creating result with all optional fields as None."""
        result_data = {
            "variant_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            # All other fields omitted (should default to None)
        }

        response = client.post("/api/experiment_results", json=result_data)

        assert response.status_code == 200
        data = response.json()

        # Optional fields should be None or default values
        assert data["variant_id"] == result_data["variant_id"]
        assert data["session_id"] == result_data["session_id"]

    def test_list_experiment_results_default(self, client):
        """Test listing experiment results with default parameters."""
        response = client.get("/api/experiment_results")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        # Should return result objects with proper structure
        if data:
            result = data[0]
            assert "id" in result
            assert "variant_id" in result
            assert "session_id" in result
            assert "kpi_quality" in result
            assert "created_at" in result

    def test_list_experiment_results_with_variant_filter(self, client):
        """Test listing results filtered by variant ID."""
        variant_id = str(uuid.uuid4())

        response = client.get(f"/api/experiment_results?variant_id={variant_id}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_experiment_results_with_session_filter(self, client):
        """Test listing results filtered by session ID."""
        session_id = str(uuid.uuid4())

        response = client.get(f"/api/experiment_results?session_id={session_id}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_experiment_results_pagination_valid(self, client):
        """Test listing results with valid pagination."""
        response = client.get("/api/experiment_results?skip=10&limit=25")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_experiment_results_invalid_skip_negative(self, client):
        """Test listing results with negative skip."""
        response = client.get("/api/experiment_results?skip=-5")

        assert response.status_code == 400
        assert "skip must be non-negative" in response.json()["detail"]

    def test_list_experiment_results_invalid_limit_zero(self, client):
        """Test listing results with limit=0."""
        response = client.get("/api/experiment_results?limit=0")

        assert response.status_code == 400
        assert "limit must be between 1 and 1000" in response.json()["detail"]

    def test_list_experiment_results_invalid_limit_over_max(self, client):
        """Test listing results with limit over 1000."""
        response = client.get("/api/experiment_results?limit=1500")

        assert response.status_code == 400
        assert "limit must be between 1 and 1000" in response.json()["detail"]

    def test_list_experiment_results_invalid_variant_uuid(self, client):
        """Test listing results with invalid variant UUID filter."""
        response = client.get("/api/experiment_results?variant_id=invalid-uuid")

        assert response.status_code == 400
        assert "Invalid ID format" in response.json()["detail"]

    def test_list_experiment_results_invalid_session_uuid(self, client):
        """Test listing results with invalid session UUID filter."""
        response = client.get("/api/experiment_results?session_id=invalid-uuid")

        assert response.status_code == 400
        assert "Invalid ID format" in response.json()["detail"]

    # Edge Case and Integration Tests

    def test_experiment_lifecycle(
        self, client, sample_experiment_data, sample_variant_data
    ):
        """Test complete experiment lifecycle from creation to completion."""
        # 1. Create experiment
        experiment_response = client.post(
            "/api/experiments", json=sample_experiment_data
        )
        assert experiment_response.status_code == 200
        experiment_data = experiment_response.json()
        experiment_id = experiment_data["id"]

        # 2. Create variant
        variant_response = client.post(
            f"/api/experiments/{experiment_id}/variants", json=sample_variant_data
        )
        assert variant_response.status_code == 200
        variant_data = variant_response.json()
        variant_id = variant_data["id"]

        # 3. Update experiment status
        status_update = {"status": "active"}
        update_response = client.put(
            f"/api/experiments/{experiment_id}", json=status_update
        )
        assert update_response.status_code == 200

        # 4. Record results
        result_data = {
            "variant_id": variant_id,
            "session_id": str(uuid.uuid4()),
            "kpi_quality": 85.0,
            "kpi_speed": 1000,
            "user_feedback_score": 4.0,
        }
        result_response = client.post("/api/experiment_results", json=result_data)
        assert result_response.status_code == 200

        # 5. List results for the variant
        results_response = client.get(
            f"/api/experiment_results?variant_id={variant_id}"
        )
        assert results_response.status_code == 200
        results = results_response.json()
        assert len(results) > 0

        # 6. List variants for the experiment
        variants_response = client.get(f"/api/experiments/{experiment_id}/variants")
        assert variants_response.status_code == 200
        variants = variants_response.json()
        assert len(variants) > 0

    def test_multiple_variants_same_experiment(self, client):
        """Test creating multiple variants for the same experiment."""
        experiment_id = str(uuid.uuid4())

        # Create control variant
        control_data = {
            "name": "Control",
            "description": "Original version",
            "is_control": True,
        }
        control_response = client.post(
            f"/api/experiments/{experiment_id}/variants", json=control_data
        )
        assert control_response.status_code == 200

        # Create test variant
        test_data = {
            "name": "Test Variant",
            "description": "New version",
            "is_control": False,
        }
        test_response = client.post(
            f"/api/experiments/{experiment_id}/variants", json=test_data
        )
        assert test_response.status_code == 200

        # List all variants
        variants_response = client.get(f"/api/experiments/{experiment_id}/variants")
        assert variants_response.status_code == 200
        variants = variants_response.json()
        assert len(variants) >= 2

    def test_experiment_results_with_metadata(self, client):
        """Test recording results with complex metadata."""
        result_data = {
            "variant_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "kpi_quality": 92.5,
            "kpi_speed": 800,
            "kpi_cost": 0.12,
            "user_feedback_score": 4.8,
            "user_feedback_text": "Excellent experience",
            "metadata": {
                "browser": "Chrome",
                "version": "120.0",
                "device": {
                    "type": "desktop",
                    "os": "Windows",
                    "resolution": "1920x1080",
                },
                "user_segment": "power_user",
                "timestamp": datetime.utcnow().isoformat(),
                "conversion_funnel": {
                    "step1": True,
                    "step2": True,
                    "step3": True,
                    "completed": True,
                },
            },
        }

        response = client.post("/api/experiment_results", json=result_data)
        assert response.status_code == 200

        data = response.json()
        assert "metadata" in data
        assert data["metadata"]["browser"] == "Chrome"
        assert data["metadata"]["device"]["type"] == "desktop"

    def test_experiment_with_boundary_traffic_allocation(self, client):
        """Test experiment creation with boundary traffic allocation values."""
        boundary_values = [0, 50, 100]

        for allocation in boundary_values:
            experiment_data = {
                "name": f"Test Experiment {allocation}",
                "traffic_allocation": allocation,
            }

            response = client.post("/api/experiments", json=experiment_data)
            assert response.status_code == 200

    def test_user_feedback_score_boundary_values(self, client):
        """Test result recording with boundary user feedback scores."""
        boundary_scores = [1, 3, 5]

        for score in boundary_scores:
            result_data = {
                "variant_id": str(uuid.uuid4()),
                "session_id": str(uuid.uuid4()),
                "user_feedback_score": score,
            }

            response = client.post("/api/experiment_results", json=result_data)
            assert response.status_code == 200

    def test_kpi_quality_boundary_values(self, client):
        """Test result recording with boundary KPI quality values."""
        boundary_qualities = [0, 50, 100]

        for quality in boundary_qualities:
            result_data = {
                "variant_id": str(uuid.uuid4()),
                "session_id": str(uuid.uuid4()),
                "kpi_quality": quality,
            }

            response = client.post("/api/experiment_results", json=result_data)
            assert response.status_code == 200

    def test_experiment_status_transitions(self, client):
        """Test valid experiment status transitions."""
        experiment_id = str(uuid.uuid4())
        valid_statuses = ["draft", "active", "paused", "completed"]

        # Create experiment in draft status
        experiment_data = {"name": "Status Test", "status": "draft"}
        create_response = client.post("/api/experiments", json=experiment_data)
        assert create_response.status_code == 200

        # Test transitions to each valid status
        for status in valid_statuses:
            update_data = {"status": status}
            response = client.put(f"/api/experiments/{experiment_id}", json=update_data)
            assert response.status_code == 200

            # Verify status was updated
            get_response = client.get(f"/api/experiments/{experiment_id}")
            assert get_response.status_code == 200
            experiment_data = get_response.json()
            assert experiment_data["status"] == status

    def test_variant_with_complex_strategy_config(self, client):
        """Test creating variant with complex strategy configuration."""
        experiment_id = str(uuid.uuid4())
        complex_config = {
            "name": "Complex Strategy Variant",
            "strategy_config": {
                "ui_changes": {
                    "button_color": "#FF5722",
                    "font_size": "16px",
                    "layout": "grid",
                    "animations": {
                        "enabled": True,
                        "duration": "300ms",
                        "easing": "ease-in-out",
                    },
                },
                "backend_changes": {
                    "api_version": "v2",
                    "cache_enabled": True,
                    "optimization_level": "aggressive",
                },
                "feature_flags": {
                    "new_checkout": True,
                    "guest_checkout": False,
                    "express_payment": True,
                },
                "targeting": {
                    "user_segments": ["new_users", "returning_users"],
                    "geographic_regions": ["US", "CA", "UK"],
                    "device_types": ["desktop", "mobile"],
                },
            },
        }

        response = client.post(
            f"/api/experiments/{experiment_id}/variants", json=complex_config
        )
        assert response.status_code == 200

        data = response.json()
        assert "strategy_config" in data
        assert data["strategy_config"]["ui_changes"]["button_color"] == "#FF5722"
        assert data["strategy_config"]["feature_flags"]["new_checkout"]

    def test_experiment_deletion_cascade_behavior(self, client):
        """Test that deleting an experiment handles related variants appropriately."""
        experiment_id = str(uuid.uuid4())

        # First create an experiment and variant
        experiment_data = {"name": "Cascade Test"}
        experiment_response = client.post("/api/experiments", json=experiment_data)
        assert experiment_response.status_code == 200

        variant_data = {"name": "Test Variant"}
        variant_response = client.post(
            f"/api/experiments/{experiment_id}/variants", json=variant_data
        )
        assert variant_response.status_code == 200

        # Delete the experiment
        delete_response = client.delete(f"/api/experiments/{experiment_id}")
        assert delete_response.status_code == 200

        # Verify experiment is gone
        get_experiment_response = client.get(f"/api/experiments/{experiment_id}")
        # This might return 404 or error depending on implementation
        assert get_experiment_response.status_code in [
            404,
            500,
        ]  # Depends on implementation

    def test_pagination_edge_cases(self, client):
        """Test pagination with edge case values."""
        # Test with limit at maximum boundary
        response = client.get("/api/experiments?limit=1000")
        assert response.status_code == 200

        # Test with skip at large value
        response = client.get("/api/experiments?skip=10000&limit=10")
        assert response.status_code == 200

        # Test with both skip and limit at boundaries
        response = client.get("/api/experiments?skip=999999&limit=1")
        assert response.status_code == 200


# Run tests if this file is executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
