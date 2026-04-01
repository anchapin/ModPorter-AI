"""
Unit tests for experiments API endpoints.

Issue: Test coverage for src/api/experiments.py
"""

import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import status
from fastapi.testclient import TestClient
from fastapi import FastAPI

from api.experiments import router


app = FastAPI()
app.include_router(router)


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    mock = AsyncMock()
    return mock


@pytest.fixture
def client(mock_db):
    """Create test client with mocked dependencies."""
    from db.base import get_db

    app.dependency_overrides[get_db] = lambda: mock_db

    yield TestClient(app)

    app.dependency_overrides.clear()


class TestCreateExperiment:
    """Tests for POST /experiments endpoint."""

    def test_create_experiment_invalid_traffic_allocation(self, client, mock_db):
        """Test creating experiment with invalid traffic allocation."""
        request_data = {
            "name": "Test Experiment",
            "traffic_allocation": 150,  # Invalid: > 100
        }

        response = client.post("/experiments", json=request_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_experiment_success(self, client, mock_db):
        """Test successful experiment creation."""
        from db import crud

        mock_experiment = MagicMock()
        mock_experiment.id = uuid.uuid4()
        mock_experiment.name = "Test Experiment"
        mock_experiment.description = "A test"
        mock_experiment.start_date = None
        mock_experiment.end_date = None
        mock_experiment.status = "draft"
        mock_experiment.traffic_allocation = 100
        mock_experiment.created_at = MagicMock()
        mock_experiment.updated_at = MagicMock()

        with patch.object(
            crud, "create_experiment", new_callable=AsyncMock, return_value=mock_experiment
        ):
            request_data = {
                "name": "Test Experiment",
            }

            response = client.post("/experiments", json=request_data)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["name"] == "Test Experiment"


class TestListExperiments:
    """Tests for GET /experiments endpoint."""

    def test_list_experiments_invalid_skip(self, client, mock_db):
        """Test listing experiments with negative skip."""
        response = client.get("/experiments?skip=-1")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_experiments_invalid_limit(self, client, mock_db):
        """Test listing experiments with invalid limit."""
        response = client.get("/experiments?limit=0")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_experiments_limit_too_high(self, client, mock_db):
        """Test listing experiments with limit exceeding max."""
        response = client.get("/experiments?limit=2000")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_experiments_success(self, client, mock_db):
        """Test successful experiment listing."""
        from db import crud

        mock_experiment = MagicMock()
        mock_experiment.id = uuid.uuid4()
        mock_experiment.name = "Test Experiment"
        mock_experiment.description = None
        mock_experiment.start_date = None
        mock_experiment.end_date = None
        mock_experiment.status = "draft"
        mock_experiment.traffic_allocation = 100
        mock_experiment.created_at = MagicMock()
        mock_experiment.updated_at = MagicMock()

        with patch.object(
            crud, "list_experiments", new_callable=AsyncMock, return_value=[mock_experiment]
        ):
            response = client.get("/experiments")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1


class TestGetExperiment:
    """Tests for GET /experiments/{experiment_id} endpoint."""

    def test_get_experiment_invalid_id(self, client, mock_db):
        """Test getting experiment with invalid ID format."""
        response = client.get("/experiments/invalid-uuid")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_experiment_not_found(self, client, mock_db):
        """Test getting non-existent experiment."""
        from db import crud

        with patch.object(crud, "get_experiment", new_callable=AsyncMock, return_value=None):
            exp_id = str(uuid.uuid4())
            response = client.get(f"/experiments/{exp_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_experiment_success(self, client, mock_db):
        """Test successfully getting an experiment."""
        from db import crud

        mock_experiment = MagicMock()
        mock_experiment.id = uuid.uuid4()
        mock_experiment.name = "Test Experiment"
        mock_experiment.description = "A test"
        mock_experiment.start_date = None
        mock_experiment.end_date = None
        mock_experiment.status = "active"
        mock_experiment.traffic_allocation = 100
        mock_experiment.created_at = MagicMock()
        mock_experiment.updated_at = MagicMock()

        with patch.object(
            crud, "get_experiment", new_callable=AsyncMock, return_value=mock_experiment
        ):
            exp_id = str(uuid.uuid4())
            response = client.get(f"/experiments/{exp_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Test Experiment"


class TestUpdateExperiment:
    """Tests for PUT /experiments/{experiment_id} endpoint."""

    def test_update_experiment_invalid_id(self, client, mock_db):
        """Test updating with invalid ID format."""
        request_data = {"name": "Updated Name"}

        response = client.put("/experiments/invalid-uuid", json=request_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_experiment_invalid_status(self, client, mock_db):
        """Test updating with invalid status."""
        from db import crud

        mock_experiment = MagicMock()
        mock_experiment.id = uuid.uuid4()

        with patch.object(
            crud, "get_experiment", new_callable=AsyncMock, return_value=mock_experiment
        ):
            exp_id = str(uuid.uuid4())
            request_data = {"status": "invalid_status"}
            response = client.put(f"/experiments/{exp_id}", json=request_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_experiment_invalid_traffic(self, client, mock_db):
        """Test updating with invalid traffic allocation."""
        from db import crud

        mock_experiment = MagicMock()
        mock_experiment.id = uuid.uuid4()

        with patch.object(
            crud, "get_experiment", new_callable=AsyncMock, return_value=mock_experiment
        ):
            exp_id = str(uuid.uuid4())
            request_data = {"traffic_allocation": 150}
            response = client.put(f"/experiments/{exp_id}", json=request_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_experiment_not_found(self, client, mock_db):
        """Test updating non-existent experiment."""
        from db import crud

        with patch.object(crud, "get_experiment", new_callable=AsyncMock, return_value=None):
            exp_id = str(uuid.uuid4())
            request_data = {"name": "Updated"}
            response = client.put(f"/experiments/{exp_id}", json=request_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_experiment_success(self, client, mock_db):
        """Test successful experiment update."""
        from db import crud

        mock_experiment = MagicMock()
        mock_experiment.id = uuid.uuid4()

        mock_updated = MagicMock()
        mock_updated.id = mock_experiment.id
        mock_updated.name = "Updated Experiment"
        mock_updated.description = None
        mock_updated.start_date = None
        mock_updated.end_date = None
        mock_updated.status = "active"
        mock_updated.traffic_allocation = 100
        mock_updated.created_at = MagicMock()
        mock_updated.updated_at = MagicMock()

        with (
            patch.object(
                crud, "get_experiment", new_callable=AsyncMock, return_value=mock_experiment
            ),
            patch.object(
                crud, "update_experiment", new_callable=AsyncMock, return_value=mock_updated
            ),
        ):
            exp_id = str(uuid.uuid4())
            request_data = {"name": "Updated Experiment"}
            response = client.put(f"/experiments/{exp_id}", json=request_data)

        assert response.status_code == status.HTTP_200_OK


class TestDeleteExperiment:
    """Tests for DELETE /experiments/{experiment_id} endpoint."""

    def test_delete_experiment_invalid_id(self, client, mock_db):
        """Test deleting with invalid ID format."""
        response = client.delete("/experiments/invalid-uuid")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_experiment_not_found(self, client, mock_db):
        """Test deleting non-existent experiment."""
        from db import crud

        with patch.object(crud, "get_experiment", new_callable=AsyncMock, return_value=None):
            exp_id = str(uuid.uuid4())
            response = client.delete(f"/experiments/{exp_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_experiment_success(self, client, mock_db):
        """Test successful experiment deletion."""
        from db import crud

        mock_experiment = MagicMock()
        mock_experiment.id = uuid.uuid4()

        with (
            patch.object(
                crud, "get_experiment", new_callable=AsyncMock, return_value=mock_experiment
            ),
            patch.object(crud, "delete_experiment", new_callable=AsyncMock, return_value=True),
        ):
            exp_id = str(uuid.uuid4())
            response = client.delete(f"/experiments/{exp_id}")

        assert response.status_code == status.HTTP_200_OK


class TestCreateExperimentVariant:
    """Tests for POST /experiments/{experiment_id}/variants endpoint."""

    def test_create_variant_invalid_experiment_id(self, client, mock_db):
        """Test creating variant with invalid experiment ID."""
        request_data = {"name": "Control"}

        response = client.post("/experiments/invalid-uuid/variants", json=request_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_variant_experiment_not_found(self, client, mock_db):
        """Test creating variant for non-existent experiment."""
        from db import crud

        with patch.object(crud, "get_experiment", new_callable=AsyncMock, return_value=None):
            exp_id = str(uuid.uuid4())
            request_data = {"name": "Control"}
            response = client.post(f"/experiments/{exp_id}/variants", json=request_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_variant_success(self, client, mock_db):
        """Test successful variant creation."""
        from db import crud

        mock_experiment = MagicMock()
        mock_experiment.id = uuid.uuid4()

        mock_variant = MagicMock()
        mock_variant.id = uuid.uuid4()
        mock_variant.experiment_id = mock_experiment.id
        mock_variant.name = "Control"
        mock_variant.description = None
        mock_variant.is_control = True
        mock_variant.strategy_config = None
        mock_variant.created_at = MagicMock()
        mock_variant.updated_at = MagicMock()

        with (
            patch.object(
                crud, "get_experiment", new_callable=AsyncMock, return_value=mock_experiment
            ),
            patch.object(
                crud, "create_experiment_variant", new_callable=AsyncMock, return_value=mock_variant
            ),
        ):
            exp_id = str(uuid.uuid4())
            request_data = {"name": "Control", "is_control": True}
            response = client.post(f"/experiments/{exp_id}/variants", json=request_data)

        assert response.status_code == status.HTTP_200_OK


class TestListExperimentVariants:
    """Tests for GET /experiments/{experiment_id}/variants endpoint."""

    def test_list_variants_invalid_experiment_id(self, client, mock_db):
        """Test listing variants with invalid experiment ID."""
        response = client.get("/experiments/invalid-uuid/variants")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_variants_experiment_not_found(self, client, mock_db):
        """Test listing variants for non-existent experiment."""
        from db import crud

        with patch.object(crud, "get_experiment", new_callable=AsyncMock, return_value=None):
            exp_id = str(uuid.uuid4())
            response = client.get(f"/experiments/{exp_id}/variants")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_variants_success(self, client, mock_db):
        """Test successful variant listing."""
        from db import crud

        mock_experiment = MagicMock()
        mock_experiment.id = uuid.uuid4()

        mock_variant = MagicMock()
        mock_variant.id = uuid.uuid4()
        mock_variant.experiment_id = mock_experiment.id
        mock_variant.name = "Control"
        mock_variant.description = None
        mock_variant.is_control = True
        mock_variant.strategy_config = None
        mock_variant.created_at = MagicMock()
        mock_variant.updated_at = MagicMock()

        with (
            patch.object(
                crud, "get_experiment", new_callable=AsyncMock, return_value=mock_experiment
            ),
            patch.object(
                crud,
                "list_experiment_variants",
                new_callable=AsyncMock,
                return_value=[mock_variant],
            ),
        ):
            exp_id = str(uuid.uuid4())
            response = client.get(f"/experiments/{exp_id}/variants")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1


class TestGetExperimentVariant:
    """Tests for GET /experiments/{experiment_id}/variants/{variant_id} endpoint."""

    def test_get_variant_invalid_ids(self, client, mock_db):
        """Test getting variant with invalid ID formats."""
        response = client.get("/experiments/invalid/variants/invalid")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_variant_not_found(self, client, mock_db):
        """Test getting non-existent variant."""
        from db import crud

        mock_experiment = MagicMock()
        mock_experiment.id = uuid.uuid4()

        with (
            patch.object(
                crud, "get_experiment", new_callable=AsyncMock, return_value=mock_experiment
            ),
            patch.object(crud, "get_experiment_variant", new_callable=AsyncMock, return_value=None),
        ):
            exp_id = str(uuid.uuid4())
            var_id = str(uuid.uuid4())
            response = client.get(f"/experiments/{exp_id}/variants/{var_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUpdateExperimentVariant:
    """Tests for PUT /experiments/{experiment_id}/variants/{variant_id} endpoint."""

    def test_update_variant_success(self, client, mock_db):
        """Test successful variant update."""
        from db import crud

        mock_experiment = MagicMock()
        mock_experiment.id = uuid.uuid4()

        mock_variant = MagicMock()
        mock_variant.id = uuid.uuid4()
        mock_variant.experiment_id = mock_experiment.id

        mock_updated = MagicMock()
        mock_updated.id = mock_variant.id
        mock_updated.experiment_id = mock_experiment.id
        mock_updated.name = "Updated Variant"
        mock_updated.description = None
        mock_updated.is_control = False
        mock_updated.strategy_config = None
        mock_updated.created_at = MagicMock()
        mock_updated.updated_at = MagicMock()

        with (
            patch.object(
                crud, "get_experiment", new_callable=AsyncMock, return_value=mock_experiment
            ),
            patch.object(
                crud, "get_experiment_variant", new_callable=AsyncMock, return_value=mock_variant
            ),
            patch.object(
                crud, "update_experiment_variant", new_callable=AsyncMock, return_value=mock_updated
            ),
        ):
            exp_id = str(mock_experiment.id)
            var_id = str(mock_variant.id)
            request_data = {"name": "Updated Variant"}
            response = client.put(f"/experiments/{exp_id}/variants/{var_id}", json=request_data)

        assert response.status_code == status.HTTP_200_OK


class TestDeleteExperimentVariant:
    """Tests for DELETE /experiments/{experiment_id}/variants/{variant_id} endpoint."""

    def test_delete_variant_success(self, client, mock_db):
        """Test successful variant deletion."""
        from db import crud

        mock_experiment = MagicMock()
        mock_experiment.id = uuid.uuid4()

        mock_variant = MagicMock()
        mock_variant.id = uuid.uuid4()
        mock_variant.experiment_id = mock_experiment.id

        with (
            patch.object(
                crud, "get_experiment", new_callable=AsyncMock, return_value=mock_experiment
            ),
            patch.object(
                crud, "get_experiment_variant", new_callable=AsyncMock, return_value=mock_variant
            ),
            patch.object(
                crud, "delete_experiment_variant", new_callable=AsyncMock, return_value=True
            ),
        ):
            exp_id = str(mock_experiment.id)
            var_id = str(mock_variant.id)
            response = client.delete(f"/experiments/{exp_id}/variants/{var_id}")

        assert response.status_code == status.HTTP_200_OK


class TestCreateExperimentResult:
    """Tests for POST /experiment_results endpoint."""

    def test_create_result_invalid_ids(self, client, mock_db):
        """Test creating result with invalid ID formats."""
        request_data = {
            "variant_id": "invalid",
            "session_id": "invalid",
        }

        response = client.post("/experiment_results", json=request_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_result_invalid_quality(self, client, mock_db):
        """Test creating result with out-of-range quality."""
        request_data = {
            "variant_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "kpi_quality": 150,  # Invalid: > 100
        }

        response = client.post("/experiment_results", json=request_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_result_invalid_feedback_score(self, client, mock_db):
        """Test creating result with out-of-range feedback score."""
        request_data = {
            "variant_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "user_feedback_score": 10,  # Invalid: > 5
        }

        response = client.post("/experiment_results", json=request_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_result_variant_not_found(self, client, mock_db):
        """Test creating result for non-existent variant."""
        from db import crud

        with patch.object(
            crud, "get_experiment_variant", new_callable=AsyncMock, return_value=None
        ):
            request_data = {
                "variant_id": str(uuid.uuid4()),
                "session_id": str(uuid.uuid4()),
            }
            response = client.post("/experiment_results", json=request_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestListExperimentResults:
    """Tests for GET /experiment_results endpoint."""

    def test_list_results_invalid_skip(self, client, mock_db):
        """Test listing results with negative skip."""
        response = client.get("/experiment_results?skip=-1")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_results_invalid_limit(self, client, mock_db):
        """Test listing results with invalid limit."""
        response = client.get("/experiment_results?limit=0")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_results_invalid_uuid(self, client, mock_db):
        """Test listing results with invalid UUID."""
        response = client.get("/experiment_results?variant_id=invalid")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestExperimentModels:
    """Tests for experiment model validation."""

    def test_experiment_create(self):
        """Test ExperimentCreate model."""
        from api.experiments import ExperimentCreate

        exp = ExperimentCreate(
            name="Test Experiment",
            description="A test",
            traffic_allocation=50,
        )

        assert exp.name == "Test Experiment"
        assert exp.traffic_allocation == 50

    def test_experiment_update(self):
        """Test ExperimentUpdate model."""
        from api.experiments import ExperimentUpdate

        update = ExperimentUpdate(
            name="Updated Name",
            status="active",
        )

        assert update.name == "Updated Name"
        assert update.status == "active"

    def test_variant_create(self):
        """Test ExperimentVariantCreate model."""
        from api.experiments import ExperimentVariantCreate

        variant = ExperimentVariantCreate(
            name="Control",
            is_control=True,
            strategy_config={"key": "value"},
        )

        assert variant.name == "Control"
        assert variant.is_control is True

    def test_result_create(self):
        """Test ExperimentResultCreate model."""
        from api.experiments import ExperimentResultCreate

        result = ExperimentResultCreate(
            variant_id=str(uuid.uuid4()),
            session_id=str(uuid.uuid4()),
            kpi_quality=85.5,
            kpi_speed=1500,
            user_feedback_score=4.5,
        )

        assert result.kpi_quality == 85.5
        assert result.kpi_speed == 1500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
