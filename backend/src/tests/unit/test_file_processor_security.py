import pytest
import socket
import logging
from unittest import mock
import httpx
from file_processor import FileProcessor

@pytest.fixture
def file_processor():
    return FileProcessor()

@pytest.mark.asyncio
async def test_resolve_and_validate_public_ip(file_processor):
    with mock.patch("socket.getaddrinfo") as mock_getaddrinfo:
        # Mock public IP: 93.184.216.34 (example.com)
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 80))]

        result = await file_processor._resolve_and_validate("example.com")
        assert result == "93.184.216.34"

@pytest.mark.asyncio
async def test_resolve_and_validate_private_ip(file_processor):
    with mock.patch("socket.getaddrinfo") as mock_getaddrinfo:
        # Mock private IP: 192.168.1.1
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.168.1.1', 80))]

        result = await file_processor._resolve_and_validate("internal.local")
        assert result is None

@pytest.mark.asyncio
async def test_resolve_and_validate_mixed_ips(file_processor):
    with mock.patch("socket.getaddrinfo") as mock_getaddrinfo:
        # Mock mixed IPs: one public, one private (should fail)
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 80)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.168.1.1', 80))
        ]

        result = await file_processor._resolve_and_validate("mixed.local")
        assert result is None

@pytest.mark.asyncio
async def test_download_from_url_http_rewrites_to_ip(file_processor):
    job_id = "test_job_http"
    url = "http://example.com/file.zip"

    with mock.patch.object(file_processor, "_resolve_and_validate", return_value="93.184.216.34") as mock_resolve:
        with mock.patch("httpx.AsyncClient") as MockAsyncClient:
            mock_client = MockAsyncClient.return_value.__aenter__.return_value
            mock_response = mock.AsyncMock(spec=httpx.Response)
            mock_response.status_code = 200
            mock_response.headers = {"Content-Disposition": 'attachment; filename="file.zip"'}
            mock_response.url = httpx.URL("http://93.184.216.34/file.zip")
            async def mock_aiter_bytes():
                yield b"content"
            mock_response.aiter_bytes = mock_aiter_bytes
            mock_client.get.return_value = mock_response

            # Mock file writing to avoid disk usage/errors
            with mock.patch("builtins.open", mock.mock_open()):
                 # Also mock Path.mkdir to avoid actual FS
                 with mock.patch("pathlib.Path.mkdir"):
                     # Mock Path.stat to return size > 0
                     with mock.patch("pathlib.Path.stat") as mock_stat:
                         mock_stat.return_value.st_size = 100

                         result = await file_processor.download_from_url(url, job_id)

            assert result.success is True
            # Check that client.get was called with IP URL and Host header
            expected_url = "http://93.184.216.34/file.zip"
            mock_client.get.assert_called_with(
                expected_url,
                headers={"Host": "example.com"},
                follow_redirects=False,
                timeout=30.0
            )

@pytest.mark.asyncio
async def test_download_from_url_https_uses_hostname(file_processor):
    job_id = "test_job_https"
    url = "https://example.com/file.zip"

    with mock.patch.object(file_processor, "_resolve_and_validate", return_value="93.184.216.34") as mock_resolve:
        with mock.patch("httpx.AsyncClient") as MockAsyncClient:
            mock_client = MockAsyncClient.return_value.__aenter__.return_value
            mock_response = mock.AsyncMock(spec=httpx.Response)
            mock_response.status_code = 200
            mock_response.headers = {"Content-Disposition": 'attachment; filename="file.zip"'}
            mock_response.url = httpx.URL("https://example.com/file.zip")
            async def mock_aiter_bytes():
                yield b"content"
            mock_response.aiter_bytes = mock_aiter_bytes
            mock_client.get.return_value = mock_response

            # Mock file writing
            with mock.patch("builtins.open", mock.mock_open()):
                 with mock.patch("pathlib.Path.mkdir"):
                     with mock.patch("pathlib.Path.stat") as mock_stat:
                         mock_stat.return_value.st_size = 100

                         result = await file_processor.download_from_url(url, job_id)

            assert result.success is True
            # Check that client.get was called with ORIGINAL URL (no IP rewrite for HTTPS)
            mock_client.get.assert_called_with(
                url,
                follow_redirects=False,
                timeout=30.0
            )
