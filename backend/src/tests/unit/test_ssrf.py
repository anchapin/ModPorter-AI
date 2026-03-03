import pytest
import socket
from unittest import mock
import httpx
from file_processor import FileProcessor

@pytest.fixture
def file_processor():
    return FileProcessor()

@pytest.fixture
def mock_job_id():
    return "test_job_ssrf"

@pytest.mark.asyncio
@mock.patch("file_processor.httpx.AsyncClient")
@mock.patch("file_processor.socket.getaddrinfo")
async def test_download_http_dns_pinning(mock_getaddrinfo, MockAsyncClient, file_processor, mock_job_id):
    """
    Verifies that for HTTP URLs, the FileProcessor resolves the IP and uses it for the request
    (DNS pinning), while adding a Host header.
    """
    # Mock DNS resolution to a safe public IP
    safe_ip = "93.184.216.34"
    mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (safe_ip, 80))]

    # Mock HTTP response
    mock_response = mock.AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.headers = {"Content-Disposition": 'attachment; filename="safe.zip"'}
    mock_response.url = httpx.URL(f"http://{safe_ip}/safe.zip")

    async def mock_aiter_bytes():
        yield b"safe content"
    mock_response.aiter_bytes = mock_aiter_bytes

    mock_get = mock.AsyncMock(return_value=mock_response)
    MockAsyncClient.return_value.__aenter__.return_value.get = mock_get

    url = "http://example.com/safe.zip"

    # We need to mock _sanitize_filename or ensure it works (it does)
    # We need to mock open/write to avoid file system operations or use temp dir
    # But for this test, we care about the call arguments to client.get

    # Use a real temporary directory for download destination to avoid errors
    with mock.patch("builtins.open", mock.mock_open()), \
         mock.patch("pathlib.Path.mkdir"), \
         mock.patch("pathlib.Path.stat", return_value=mock.Mock(st_size=12)):

        await file_processor.download_from_url(url, mock_job_id)

    # ASSERTION: Check that client.get was called with the IP address in the URL
    # and the original hostname in the Host header.

    # Expected URL: http://93.184.216.34/safe.zip
    # Expected Headers: Host: example.com

    # Get the actual call arguments
    args, kwargs = mock_get.call_args
    actual_url = args[0]
    actual_headers = kwargs.get("headers", {})

    assert actual_url == f"http://{safe_ip}/safe.zip", f"Expected URL to use IP {safe_ip}, but got {actual_url}"
    assert actual_headers.get("Host") == "example.com", f"Expected Host header to be example.com, but got {actual_headers.get('Host')}"


@pytest.mark.asyncio
@mock.patch("file_processor.httpx.AsyncClient")
@mock.patch("file_processor.socket.getaddrinfo")
async def test_download_https_no_dns_pinning(mock_getaddrinfo, MockAsyncClient, file_processor, mock_job_id):
    """
    Verifies that for HTTPS URLs, the FileProcessor uses the hostname in the URL (relying on TLS),
    but still performs the safety check.
    """
    # Mock DNS resolution to a safe public IP
    safe_ip = "93.184.216.34"
    mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (safe_ip, 443))]

    # Mock HTTP response
    mock_response = mock.AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.headers = {"Content-Disposition": 'attachment; filename="safe.zip"'}
    mock_response.url = httpx.URL("https://example.com/safe.zip")

    async def mock_aiter_bytes():
        yield b"safe content"
    mock_response.aiter_bytes = mock_aiter_bytes

    mock_get = mock.AsyncMock(return_value=mock_response)
    MockAsyncClient.return_value.__aenter__.return_value.get = mock_get

    url = "https://example.com/safe.zip"

    with mock.patch("builtins.open", mock.mock_open()), \
         mock.patch("pathlib.Path.mkdir"), \
         mock.patch("pathlib.Path.stat", return_value=mock.Mock(st_size=12)):

        await file_processor.download_from_url(url, mock_job_id)

    # ASSERTION: Check that client.get was called with the HOSTNAME in the URL

    args, kwargs = mock_get.call_args
    actual_url = args[0]

    assert actual_url == url, f"Expected URL to remain {url} for HTTPS, but got {actual_url}"
    # Verify DNS check was still performed (mock_getaddrinfo called)
    mock_getaddrinfo.assert_called()
