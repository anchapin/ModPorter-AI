import pytest
import os
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from services.conversion_service import (
    ConversionService,
    get_conversion_service,
    process_conversion_task,
)


class TestConversionServiceCoverage:
    @pytest.fixture
    def service(self):
        mock_ai_client = MagicMock()
        mock_cache = MagicMock()
        mock_cache.set_job_status = AsyncMock()
        mock_cache.set_progress = AsyncMock()
        return ConversionService(ai_engine_client=mock_ai_client, cache_service=mock_cache)

    @pytest.mark.asyncio
    async def test_transfer_file_to_ai_engine(self, service):
        with (
            patch("os.makedirs"),
            patch("os.path.exists", return_value=True),
            patch("shutil.copy2") as mock_copy,
        ):
            res = await service._transfer_file_to_ai_engine("/src/file.jar", "job123")
            assert "job123" in res
            mock_copy.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_conversion_success(self, service):
        service.ai_client.start_conversion = AsyncMock(return_value={"status": "started"})
        service.ai_client.get_conversion_status = AsyncMock(return_value={"status": "completed"})
        service.ai_client.poll_conversion_status = MagicMock()

        # Mock the async generator for poll_conversion_status
        async def mock_poll(*args, **kwargs):
            yield {
                "status": "in_progress",
                "progress": 50,
                "message": "Working",
                "current_stage": "test",
            }
            yield {
                "status": "completed",
                "progress": 100,
                "message": "Done",
                "current_stage": "final",
            }

        service.ai_client.poll_conversion_status.side_effect = mock_poll

        with (
            patch.object(service, "_transfer_file_to_ai_engine", return_value="/ai/path"),
            patch("services.conversion_service.ProgressHandler", new_callable=AsyncMock) as mock_ph,
            patch("os.makedirs"),
        ):
            result = await service.process_conversion(
                "job123", "/path/to/mod.jar", "mod.jar", "1.20.1", {}
            )

            assert result["status"] == "completed"
            assert "download_url" in result
            service.ai_client.start_conversion.assert_called_once()
            mock_ph.broadcast_conversion_complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_conversion_failure_on_start(self, service):
        service.ai_client.start_conversion = AsyncMock(side_effect=Exception("Failed to start"))

        with (
            patch.object(service, "_transfer_file_to_ai_engine", return_value="/ai/path"),
            patch("services.conversion_service.ProgressHandler", new_callable=AsyncMock),
            patch("os.makedirs"),
        ):
            with pytest.raises(Exception, match="Failed to start"):
                await service.process_conversion(
                    "job123", "/path/to/mod.jar", "mod.jar", "1.20.1", {}
                )

            service.cache.set_job_status.assert_called()

    @pytest.mark.asyncio
    async def test_poll_and_broadcast_error(self, service):
        service.ai_client.poll_conversion_status.side_effect = Exception("Poll error")

        with patch("services.conversion_service.ProgressHandler", new_callable=AsyncMock):
            await service._poll_and_broadcast("job123")
            service.cache.set_job_status.assert_called()

    @pytest.mark.asyncio
    async def test_handle_error(self, service):
        with patch(
            "services.conversion_service.ProgressHandler", new_callable=AsyncMock
        ) as mock_ph:
            await service._handle_error("job123", "Some error")
            service.cache.set_job_status.assert_called()
            mock_ph.broadcast_conversion_failed.assert_called_once()

    def test_get_conversion_service(self):
        s1 = get_conversion_service()
        s2 = get_conversion_service()
        assert s1 is s2

    @pytest.mark.asyncio
    async def test_process_conversion_task(self):
        mock_service = MagicMock()
        mock_service.process_conversion = AsyncMock(return_value={"status": "completed"})

        with patch("services.conversion_service.get_conversion_service", return_value=mock_service):
            payload = {
                "conversion_id": "job123",
                "file_path": "/path",
                "original_filename": "mod.jar",
            }
            res = await process_conversion_task(payload)
            assert res["status"] == "completed"

    @pytest.mark.asyncio
    async def test_process_conversion_cancelled(self, service):
        service.ai_client.start_conversion = AsyncMock(side_effect=asyncio.CancelledError())

        with (
            patch.object(service, "_transfer_file_to_ai_engine", return_value="/ai/path"),
            patch("services.conversion_service.ProgressHandler", new_callable=AsyncMock),
            patch("os.makedirs"),
        ):
            with pytest.raises(asyncio.CancelledError):
                await service.process_conversion(
                    "job123", "/path/to/mod.jar", "mod.jar", "1.20.1", {}
                )

            # Check if status was updated to cancelled
            # service.cache.set_job_status.assert_any_call("job123", ...)
            calls = service.cache.set_job_status.call_args_list
            assert any(call[0][1]["status"] == "cancelled" for call in calls)

    @pytest.mark.asyncio
    async def test_process_conversion_success_with_email(self, service):
        service.ai_client.start_conversion = AsyncMock(return_value={"status": "started"})
        service.ai_client.get_conversion_status = AsyncMock(return_value={"status": "completed"})
        service.ai_client.poll_conversion_status = MagicMock()

        # Mock the async generator for poll_conversion_status
        async def mock_poll(*args, **kwargs):
            yield {
                "status": "completed",
                "progress": 100,
                "message": "Done",
                "current_stage": "final",
            }

        service.ai_client.poll_conversion_status.side_effect = mock_poll

        with (
            patch.object(service, "_transfer_file_to_ai_engine", return_value="/ai/path"),
            patch("services.conversion_service.ProgressHandler", new_callable=AsyncMock),
            patch(
                "services.conversion_service.send_conversion_notification", new_callable=AsyncMock
            ) as mock_email,
            patch("os.makedirs"),
        ):
            mock_email.return_value = True
            result = await service.process_conversion(
                "job123",
                "/path/to/mod.jar",
                "mod.jar",
                "1.20.1",
                {},
                user_email="test@example.com",
                notify_on_completion=True,
            )

            assert result["status"] == "completed"
            assert result.get("email_verified") is True
            mock_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_conversion_success_no_email(self, service):
        service.ai_client.start_conversion = AsyncMock(return_value={"status": "started"})
        service.ai_client.get_conversion_status = AsyncMock(return_value={"status": "completed"})
        service.ai_client.poll_conversion_status = MagicMock()

        # Mock the async generator for poll_conversion_status
        async def mock_poll(*args, **kwargs):
            yield {
                "status": "completed",
                "progress": 100,
                "message": "Done",
                "current_stage": "final",
            }

        service.ai_client.poll_conversion_status.side_effect = mock_poll

        with (
            patch.object(service, "_transfer_file_to_ai_engine", return_value="/ai/path"),
            patch("services.conversion_service.ProgressHandler", new_callable=AsyncMock),
            patch(
                "services.conversion_service.send_conversion_notification", new_callable=AsyncMock
            ) as mock_email,
            patch("os.makedirs"),
        ):
            result = await service.process_conversion(
                "job123",
                "/path/to/mod.jar",
                "mod.jar",
                "1.20.1",
                {},
                user_email=None,
                notify_on_completion=False,
            )

            assert result["status"] == "completed"
            mock_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_conversion_email_fails(self, service):
        service.ai_client.start_conversion = AsyncMock(return_value={"status": "started"})
        service.ai_client.get_conversion_status = AsyncMock(return_value={"status": "completed"})
        service.ai_client.poll_conversion_status = MagicMock()

        # Mock the async generator for poll_conversion_status
        async def mock_poll(*args, **kwargs):
            yield {
                "status": "completed",
                "progress": 100,
                "message": "Done",
                "current_stage": "final",
            }

        service.ai_client.poll_conversion_status.side_effect = mock_poll

        with (
            patch.object(service, "_transfer_file_to_ai_engine", return_value="/ai/path"),
            patch("services.conversion_service.ProgressHandler", new_callable=AsyncMock),
            patch(
                "services.conversion_service.send_conversion_notification", new_callable=AsyncMock
            ) as mock_email,
            patch("os.makedirs"),
        ):
            mock_email.side_effect = Exception("Email service unavailable")
            result = await service.process_conversion(
                "job123",
                "/path/to/mod.jar",
                "mod.jar",
                "1.20.1",
                {},
                user_email="test@example.com",
                notify_on_completion=True,
            )

            assert result["status"] == "completed"
            assert result.get("email_verified") is False


if __name__ == "__main__":
    pytest.main([__file__])
