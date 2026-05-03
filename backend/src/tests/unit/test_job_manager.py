import pytest
import json
import uuid
from unittest.mock import MagicMock, patch, AsyncMock
from services.job_manager import (
    JobManager,
    Job,
    JobStatus,
    JobOptions,
    ConversionMode,
    TargetVersion,
    OutputFormat,
)


class TestJobManager:
    @pytest.fixture
    def manager(self):
        with patch("services.job_manager.StorageManager"):
            return JobManager()

    def test_target_version_enum(self):
        assert TargetVersion.V1_19 == "1.19"
        assert TargetVersion.V1_20 == "1.20"
        assert TargetVersion.V1_21 == "1.21"

    def test_output_format_enum(self):
        assert OutputFormat.MCADDON == "mcaddon"
        assert OutputFormat.ZIP == "zip"

    def test_job_options_defaults(self):
        options = JobOptions()
        assert options.target_version == TargetVersion.V1_20
        assert options.output_format == OutputFormat.MCADDON

    @pytest.mark.asyncio
    async def test_create_job(self, manager):
        mock_redis = MagicMock()
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis._client = MagicMock()
        mock_redis._client.zadd = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock(return_value=True)

        mock_queue = MagicMock()
        mock_queue.enqueue = AsyncMock(return_value=True)

        with (
            patch.object(manager, "_get_redis", return_value=mock_redis),
            patch.object(manager, "_get_queue", return_value=mock_queue),
        ):
            job_id = await manager.create_job(
                user_id="user123",
                file_path="/path/to/mod.jar",
                original_filename="mod.jar",
                options=JobOptions(conversion_mode=ConversionMode.STANDARD),
            )

            assert job_id is not None
            assert isinstance(job_id, str)
            mock_redis.set.assert_called_once()
            mock_queue.enqueue.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_job_success(self, manager):
        job_id = str(uuid.uuid4())
        job_data = {
            "job_id": job_id,
            "user_id": "user123",
            "file_path": "/path",
            "original_filename": "mod.jar",
            "status": "pending",
            "options": {},
        }

        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=job_data)

        with patch.object(manager, "_get_redis", return_value=mock_redis):
            job = await manager.get_job(job_id)
            assert job is not None
            assert job.job_id == job_id
            assert job.status == JobStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, manager):
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)

        with patch.object(manager, "_get_redis", return_value=mock_redis):
            job = await manager.get_job("non-existent")
            assert job is None

    @pytest.mark.asyncio
    async def test_update_progress(self, manager):
        job_id = "job123"
        job = Job(job_id=job_id, user_id="u", file_path="p", original_filename="f")

        mock_redis = MagicMock()
        mock_redis.set = AsyncMock(return_value=True)

        with (
            patch.object(manager, "get_job", return_value=job),
            patch.object(manager, "_get_redis", return_value=mock_redis),
        ):
            success = await manager.update_progress(job_id, 50, "Step 1")
            assert success is True
            assert job.progress == 50
            assert job.status == JobStatus.PROCESSING

    @pytest.mark.asyncio
    async def test_complete_job(self, manager):
        job_id = "job123"
        job = Job(job_id=job_id, user_id="u", file_path="p", original_filename="f")

        mock_redis = MagicMock()
        mock_redis.set = AsyncMock(return_value=True)

        with (
            patch.object(manager, "get_job", return_value=job),
            patch.object(manager, "_get_redis", return_value=mock_redis),
            patch.object(manager, "_send_webhook", new_callable=AsyncMock) as mock_webhook,
        ):
            success = await manager.complete_job(job_id, "http://result")
            assert success is True
            assert job.status == JobStatus.COMPLETED
            assert job.result_url == "http://result"

    @pytest.mark.asyncio
    async def test_fail_job(self, manager):
        job_id = "job123"
        job = Job(job_id=job_id, user_id="u", file_path="p", original_filename="f")

        mock_redis = MagicMock()
        mock_redis.set = AsyncMock(return_value=True)

        with (
            patch.object(manager, "get_job", return_value=job),
            patch.object(manager, "_get_redis", return_value=mock_redis),
        ):
            success = await manager.fail_job(job_id, "Error message")
            assert success is True
            assert job.status == JobStatus.FAILED
            assert job.error_message == "Error message"

    @pytest.mark.asyncio
    async def test_cancel_job(self, manager):
        job_id = "job123"
        job = Job(
            job_id=job_id,
            user_id="u",
            file_path="p",
            original_filename="f",
            status=JobStatus.PENDING,
        )

        mock_redis = MagicMock()
        mock_redis.set = AsyncMock(return_value=True)

        with (
            patch.object(manager, "get_job", return_value=job),
            patch.object(manager, "_get_redis", return_value=mock_redis),
        ):
            success = await manager.cancel_job(job_id)
            assert success is True
            assert job.status == JobStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_list_jobs(self, manager):
        user_id = "user123"
        job_ids = [b"job1", b"job2"]

        mock_redis = MagicMock()
        mock_redis._client.zrevrange = AsyncMock(return_value=job_ids)

        job1 = Job(job_id="job1", user_id=user_id, file_path="p", original_filename="f")
        job2 = Job(job_id="job2", user_id=user_id, file_path="p", original_filename="f")

        with (
            patch.object(manager, "_get_redis", return_value=mock_redis),
            patch.object(manager, "get_job", side_effect=[job1, job2]),
        ):
            jobs = await manager.list_jobs(user_id)
            assert len(jobs) == 2
            assert jobs[0].job_id == "job1"


if __name__ == "__main__":
    pytest.main([__file__])
