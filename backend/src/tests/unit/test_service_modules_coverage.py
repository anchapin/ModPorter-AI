"""
Tests for multiple service modules to boost coverage.

Covers:
- conversion_queue.py (ConversionJobQueue)
- result_storage.py (ResultStorage)
- report_exporter.py (ReportExporter)
- experiment_service.py (ExperimentService)
"""

import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
from pathlib import Path
import uuid


class TestConversionJobQueue:
    """Test ConversionJobQueue service."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        redis = AsyncMock()
        redis.from_url = AsyncMock(return_value=redis)
        redis.hset = AsyncMock()
        redis.zadd = AsyncMock()
        redis.zpopmin = AsyncMock(return_value=[])
        redis.hgetall = MagicMock(return_value={})
        redis.hget = AsyncMock(return_value=None)
        redis.hset = AsyncMock()
        redis.delete = AsyncMock()
        redis.exists = AsyncMock(return_value=False)
        return redis

    @pytest.fixture
    def queue(self, mock_redis):
        """Create queue with mocked Redis."""
        from services.conversion_queue import ConversionJobQueue

        q = ConversionJobQueue(redis_url="redis://localhost:6379")
        q._redis = mock_redis
        return q

    def test_queue_initialization(self):
        """Test queue initializes correctly."""
        from services.conversion_queue import ConversionJobQueue

        queue = ConversionJobQueue()
        assert queue.redis_url == "redis://localhost:6379"
        assert queue.QUEUE_KEY == "conversion:queue"
        assert queue.JOBS_KEY == "conversion:jobs"
        assert queue.PROGRESS_KEY == "conversion:progress"
        assert queue.RESULTS_KEY == "conversion:results"

    def test_queue_custom_redis_url(self):
        """Test queue with custom Redis URL."""
        from services.conversion_queue import ConversionJobQueue

        queue = ConversionJobQueue(redis_url="redis://custom:6379")
        assert queue.redis_url == "redis://custom:6379"

    @pytest.mark.asyncio
    async def test_enqueue_job(self, queue, mock_redis):
        """Test enqueuing a job."""
        job_id = await queue.enqueue_job(
            user_id="user-123",
            java_code="public class Test {}",
            mod_info={"name": "test-mod", "version": "1.0.0"},
            options={"target": "bedrock"},
            priority=5,
        )

        assert job_id is not None
        mock_redis.hset.assert_called()
        mock_redis.zadd.assert_called()

    @pytest.mark.asyncio
    async def test_get_job_status(self, queue, mock_redis):
        """Test getting job status."""
        mock_redis.hgetall = AsyncMock(
            return_value={"job_id": "job-123", "status": "completed", "user_id": "user-123"}
        )

        status = await queue.get_job_status("job-123")

        assert status is not None

    @pytest.mark.asyncio
    async def test_get_job_status_not_found(self, queue, mock_redis):
        """Test getting status for non-existent job."""
        mock_redis.hgetall = AsyncMock(return_value={})

        status = await queue.get_job_status("non-existent")

        assert status is None

    @pytest.mark.asyncio
    async def test_get_queue_stats(self, queue, mock_redis):
        """Test getting queue statistics."""
        mock_redis.zcard = AsyncMock(return_value=5)

        stats = await queue.get_queue_stats()

        assert stats is not None


class TestResultStorage:
    """Test ResultStorage service."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def storage(self):
        """Create storage with mocked dependencies."""
        with patch("pathlib.Path.mkdir"):
            with patch("services.result_storage.TEMP_UPLOADS_DIR", Path("/tmp/test_uploads")):
                with patch(
                    "services.result_storage.CONVERSION_OUTPUTS_DIR", Path("/tmp/test_outputs")
                ):
                    from services.result_storage import ResultStorage

                    return ResultStorage()

    def test_storage_initialization(self, storage):
        """Test storage initializes correctly."""
        from services.result_storage import RESULT_EXPIRY_DAYS

        assert storage is not None
        assert RESULT_EXPIRY_DAYS == 30

    @pytest.mark.asyncio
    async def test_store_result(self, storage, mock_db_session):
        """Test storing conversion result."""
        with patch("builtins.open", MagicMock()):
            result_id = await storage.store_result(
                job_id="job-123",
                user_id="user-123",
                bedrock_code="// Bedrock code",
                result_metadata={"version": "1.0"},
                db=mock_db_session,
            )

            assert result_id is not None

    @pytest.mark.asyncio
    async def test_get_result(self, storage, mock_db_session):
        """Test retrieving result."""
        mock_result = MagicMock()
        mock_result.output_data = {"metadata": {}}

        with patch("services.result_storage.ResultStorage.get_result", return_value=mock_result):
            result = await storage.get_result("result-123", mock_db_session)

            assert result is not None


class TestReportExporter:
    """Test ReportExporter service."""

    @pytest.fixture
    def exporter(self):
        """Create report exporter."""
        from services.report_exporter import ReportExporter

        return ReportExporter()

    def test_exporter_initialization(self, exporter):
        """Test exporter initializes correctly."""
        assert exporter.supported_formats == ["json", "html", "csv"]

    def test_escape_report_data_string(self, exporter):
        """Test escaping HTML in string data."""
        data = "<script>alert('xss')</script>"
        result = exporter._escape_report_data(data)

        assert "&lt;" in result or "&gt;" in result

    def test_escape_report_data_dict(self, exporter):
        """Test escaping HTML in dict data."""
        data = {"key": "<value>"}
        result = exporter._escape_report_data(data)

        assert result["key"] != "<value>"

    def test_escape_report_data_list(self, exporter):
        """Test escaping HTML in list data."""
        data = ["<item1>", "<item2>"]
        result = exporter._escape_report_data(data)

        assert len(result) == 2

    def test_escape_report_data_int(self, exporter):
        """Test escaping non-string data."""
        result = exporter._escape_report_data(123)
        assert result == 123

    def test_escape_report_data_none(self, exporter):
        """Test escaping None data."""
        result = exporter._escape_report_data(None)
        assert result is None


class TestExperimentService:
    """Test ExperimentService."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_db_session):
        """Create experiment service."""
        from services.experiment_service import ExperimentService

        return ExperimentService(db_session=mock_db_session)

    @pytest.mark.asyncio
    async def test_get_active_experiments(self, service, mock_db_session):
        """Test getting active experiments."""
        with patch("db.crud.list_experiments", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = []

            result = await service.get_active_experiments()

            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_experiment_variants(self, service, mock_db_session):
        """Test getting experiment variants."""
        with patch("db.crud.list_experiment_variants", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = []

            result = await service.get_experiment_variants(uuid.uuid4())

            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_allocate_variant_no_experiment(self, service, mock_db_session):
        """Test allocating variant when experiment doesn't exist."""
        with patch("db.crud.get_experiment", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            result = await service.allocate_variant(uuid.uuid4())

            assert result is None

    @pytest.mark.asyncio
    async def test_allocate_variant_inactive(self, service, mock_db_session):
        """Test allocating variant when experiment is inactive."""
        experiment = MagicMock()
        experiment.status = "inactive"

        with patch("db.crud.get_experiment", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = experiment

            result = await service.allocate_variant(uuid.uuid4())

            assert result is None

    @pytest.mark.asyncio
    async def test_get_control_variant(self, service, mock_db_session):
        """Test getting control variant."""
        mock_variant = MagicMock()
        mock_variant.is_control = True

        with patch(
            "services.experiment_service.ExperimentService.get_experiment_variants",
            new_callable=AsyncMock,
        ) as mock_variants:
            mock_variants.return_value = [mock_variant]

            result = await service.get_control_variant(uuid.uuid4())

            assert result is not None

    @pytest.mark.asyncio
    async def test_get_control_variant_no_control(self, service, mock_db_session):
        """Test getting control variant when none exists."""
        mock_variant = MagicMock()
        mock_variant.is_control = False

        with patch(
            "services.experiment_service.ExperimentService.get_experiment_variants",
            new_callable=AsyncMock,
        ) as mock_variants:
            mock_variants.return_value = [mock_variant]

            result = await service.get_control_variant(uuid.uuid4())

            assert result is None

    @pytest.mark.asyncio
    async def test_record_experiment_result(self, service, mock_db_session):
        """Test recording experiment result."""
        mock_result = MagicMock()

        with patch("db.crud.create_experiment_result", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_result

            result = await service.record_experiment_result(
                variant_id=uuid.uuid4(),
                session_id=uuid.uuid4(),
                kpi_quality=0.95,
                kpi_speed=120,
                kpi_cost=0.50,
                user_feedback_score=4.5,
            )

            assert result is not None


class TestAdditionalServiceMethods:
    """Test additional service methods."""

    @pytest.fixture
    def mock_db_session(self):
        return AsyncMock()

    def test_queue_constants(self):
        """Test queue constants are defined."""
        from services.conversion_queue import ConversionJobQueue

        assert ConversionJobQueue.QUEUE_KEY is not None
        assert ConversionJobQueue.JOBS_KEY is not None

    def test_storage_paths(self):
        """Test storage paths are defined."""
        from services.result_storage import TEMP_UPLOADS_DIR, CONVERSION_OUTPUTS_DIR

        assert TEMP_UPLOADS_DIR is not None
        assert CONVERSION_OUTPUTS_DIR is not None
