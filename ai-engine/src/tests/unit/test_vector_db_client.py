import pytest
import numpy as np
from unittest.mock import AsyncMock, patch

from src.utils.vector_db_client import VectorDBClient

# Define a fixture for the VectorDBClient
@pytest.fixture
def vector_db_client():
    with patch('src.utils.vector_db_client.EmbeddingGenerator') as mock_embedding_gen_class:
        # Create a mock embedding generator instance
        mock_embedding_gen = AsyncMock()
        mock_embedding_gen_class.return_value = mock_embedding_gen
        
        # Setup the embedding generator to return predictable embeddings
        async def mock_generate_embeddings(texts):
            return [np.array([0.1] * 1536)] * len(texts)
            
        mock_embedding_gen.generate_embeddings = AsyncMock(side_effect=mock_generate_embeddings)
        mock_embedding_gen.get_embedding_dimension.return_value = 1536
        
        return VectorDBClient(base_url="http://test-backend:8000/api/v1")

# Define a test case for successful indexing
@pytest.mark.asyncio
async def test_index_document_success(vector_db_client):
    mock_response = AsyncMock()
    mock_response.status_code = 201
    mock_response.text = "Document indexed successfully"

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        result = await vector_db_client.index_document("test content", "test_source.txt")

        # Verify the post was called once
        mock_post.assert_called_once()
        
        # Get the actual call arguments
        call_args = mock_post.call_args
        json_data = call_args.kwargs['json']
        
        # Verify the structure and key values
        assert json_data['document_source'] == "test_source.txt"
        assert json_data['content_hash'] == "9473fdd0d880a43c21b7778d34872157"  # MD5 hash of "test content"
        assert len(json_data['embedding']) == 1536
        assert all(x == 0.1 for x in json_data['embedding'])  # All values should be 0.1
        
        assert result is True

# Define a test case for handling API errors
@pytest.mark.asyncio
async def test_index_document_api_error(vector_db_client):
    mock_response = AsyncMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        result = await vector_db_client.index_document("test content", "test_source.txt")

        # Verify the post was called once
        mock_post.assert_called_once()
        
        # Get the actual call arguments
        call_args = mock_post.call_args
        json_data = call_args.kwargs['json']
        
        # Verify the structure and key values
        assert json_data['document_source'] == "test_source.txt"
        assert json_data['content_hash'] == "9473fdd0d880a43c21b7778d34872157"  # MD5 hash of "test content"
        assert len(json_data['embedding']) == 1536
        assert all(x == 0.1 for x in json_data['embedding'])  # All values should be 0.1
        
        assert result is False

# Define a test case for handling existing documents
@pytest.mark.asyncio
async def test_index_document_existing_document(vector_db_client):
    mock_response = AsyncMock()
    mock_response.status_code = 200  # OK - document already exists
    mock_response.text = "Document already exists"

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        result = await vector_db_client.index_document("existing content", "existing_source.txt")

        # Verify the post was called once
        mock_post.assert_called_once()
        
        # Get the actual call arguments
        call_args = mock_post.call_args
        json_data = call_args.kwargs['json']
        
        # Verify the structure and key values
        assert json_data['document_source'] == "existing_source.txt"
        assert json_data['content_hash'] == "747f41fd270fec1b82be030cc1cd4801"  # MD5 hash of "existing content"
        assert len(json_data['embedding']) == 1536
        assert all(x == 0.1 for x in json_data['embedding'])  # All values should be 0.1
        
        assert result is True
