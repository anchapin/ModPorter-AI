import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from src.utils.vector_db_client import VectorDBClient, Document

# Define a fixture for the VectorDBClient
@pytest.fixture
def vector_db_client():
    return VectorDBClient(api_key="test_api_key")

# Define a test case for successful indexing
@pytest.mark.asyncio
async def test_index_document_success(vector_db_client):
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": "Document indexed successfully"}

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        document = Document(id="test_id", text="test_text", vector=[0.1, 0.2, 0.3])
        response = await vector_db_client.index_document(document)

        mock_post.assert_called_once_with(
            "https://vector-db-api.example.com/index",  # Assuming this is the endpoint
            json={"id": "test_id", "text": "test_text", "vector": [0.1, 0.2, 0.3]}
        )
        assert response == {"message": "Document indexed successfully"}

# Define a test case for handling API errors
@pytest.mark.asyncio
async def test_index_document_api_error(vector_db_client):
    mock_response = AsyncMock()
    mock_response.status_code = 500
    mock_response.json.return_value = {"error": "Internal Server Error"}

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        document = Document(id="test_id", text="test_text", vector=[0.1, 0.2, 0.3])

        with pytest.raises(Exception) as excinfo:  # Assuming it raises a generic Exception
            await vector_db_client.index_document(document)

        assert "API error: 500" in str(excinfo.value)
        mock_post.assert_called_once_with(
            "https://vector-db-api.example.com/index",
            json={"id": "test_id", "text": "test_text", "vector": [0.1, 0.2, 0.3]}
        )

# Define a test case for handling existing documents
@pytest.mark.asyncio
async def test_index_document_existing_document(vector_db_client):
    mock_response = AsyncMock()
    mock_response.status_code = 409  # Conflict - document already exists
    mock_response.json.return_value = {"message": "Document already exists"}

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        document = Document(id="existing_id", text="existing_text", vector=[0.4, 0.5, 0.6])
        response = await vector_db_client.index_document(document)

        mock_post.assert_called_once_with(
            "https://vector-db-api.example.com/index",
            json={"id": "existing_id", "text": "existing_text", "vector": [0.4, 0.5, 0.6]}
        )
        assert response == {"message": "Document already exists"}
