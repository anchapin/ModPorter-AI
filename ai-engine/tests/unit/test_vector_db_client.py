import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from src.utils.vector_db_client import VectorDBClient, Document

# Define a fixture for the VectorDBClient
@pytest.fixture
def vector_db_client():
    return VectorDBClient(base_url="http://test-backend:8000/api/v1")

# Define a test case for successful indexing
@pytest.mark.asyncio
async def test_index_document_success(vector_db_client):
    mock_response = AsyncMock()
    mock_response.status_code = 201
    mock_response.text = "Document indexed successfully"

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        result = await vector_db_client.index_document("test content", "test_source.txt")

        mock_post.assert_called_once_with(
            "/embeddings/",
            json={
                "embedding": [0.1] * 1536,  # Default embedding dimension
                "document_source": "test_source.txt",
                "content_hash": "9473fdd0d880a43c21b7778d34872157"  # MD5 hash of "test content"
            }
        )
        assert result is True

# Define a test case for handling API errors
@pytest.mark.asyncio
async def test_index_document_api_error(vector_db_client):
    mock_response = AsyncMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        result = await vector_db_client.index_document("test content", "test_source.txt")

        mock_post.assert_called_once_with(
            "/embeddings/",
            json={
                "embedding": [0.1] * 1536,
                "document_source": "test_source.txt",
                "content_hash": "9473fdd0d880a43c21b7778d34872157"
            }
        )
        assert result is False

# Define a test case for handling existing documents
@pytest.mark.asyncio
async def test_index_document_existing_document(vector_db_client):
    mock_response = AsyncMock()
    mock_response.status_code = 200  # OK - document already exists
    mock_response.text = "Document already exists"

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        result = await vector_db_client.index_document("existing content", "existing_source.txt")

        mock_post.assert_called_once_with(
            "/embeddings/",
            json={
                "embedding": [0.1] * 1536,
                "document_source": "existing_source.txt",
                "content_hash": "747f41fd270fec1b82be030cc1cd4801"  # MD5 hash of "existing content"
            }
        )
        assert result is True
