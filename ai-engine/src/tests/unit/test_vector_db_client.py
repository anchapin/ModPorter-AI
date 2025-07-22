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

# Tests for search_documents method
@pytest.mark.asyncio
async def test_search_documents_success(vector_db_client):
    """Test successful document search."""
    from unittest.mock import MagicMock
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {
                "content": "Test document 1",
                "source": "test1.txt",
                "similarity_score": 0.95
            },
            {
                "content": "Test document 2", 
                "source": "test2.txt",
                "similarity_score": 0.87
            }
        ]
    }

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        results = await vector_db_client.search_documents("test query", top_k=5)

        # Verify the post was called once
        mock_post.assert_called_once()
        
        # Get the actual call arguments
        call_args = mock_post.call_args
        assert call_args[0][0] == "/embeddings/search/"  # URL endpoint
        json_data = call_args.kwargs['json']
        
        # Verify the request structure
        assert len(json_data['query_embedding']) == 1536
        assert all(x == 0.1 for x in json_data['query_embedding'])
        assert json_data['top_k'] == 5
        assert json_data.get('document_source_filter') is None
        
        # Verify results
        assert len(results) == 2
        assert results[0]['content'] == "Test document 1"
        assert results[0]['similarity_score'] == 0.95

@pytest.mark.asyncio
async def test_search_documents_with_source_filter(vector_db_client):
    """Test document search with source filter."""
    from unittest.mock import MagicMock
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {
                "content": "Filtered document",
                "source": "filtered.txt",
                "similarity_score": 0.92
            }
        ]
    }

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        results = await vector_db_client.search_documents(
            "test query", 
            top_k=3, 
            document_source_filter="filtered.txt"
        )

        # Verify the post was called once
        mock_post.assert_called_once()
        
        # Get the actual call arguments
        call_args = mock_post.call_args
        json_data = call_args.kwargs['json']
        
        # Verify the request includes source filter
        assert json_data['document_source_filter'] == "filtered.txt"
        assert json_data['top_k'] == 3
        
        # Verify results
        assert len(results) == 1
        assert results[0]['source'] == "filtered.txt"

@pytest.mark.asyncio
async def test_search_documents_embedding_failure(vector_db_client):
    """Test search when embedding generation fails."""
    # Mock embedding generator to return None/empty
    vector_db_client.embedding_generator.generate_embeddings = AsyncMock(return_value=[None])

    results = await vector_db_client.search_documents("test query")
    
    # Should return empty list when embedding fails
    assert results == []

@pytest.mark.asyncio
async def test_search_documents_api_error(vector_db_client):
    """Test search when API returns error."""
    import httpx
    from unittest.mock import MagicMock
    
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    
    # Mock raise_for_status to raise HTTPStatusError
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="Server error", 
        request=MagicMock(),
        response=mock_response
    )

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        results = await vector_db_client.search_documents("test query")

        # Verify the post was called once
        mock_post.assert_called_once()
        
        # Should return empty list on API error
        assert results == []

@pytest.mark.asyncio
async def test_search_documents_http_exception(vector_db_client):
    """Test search when HTTP exception occurs."""
    with patch("httpx.AsyncClient.post", side_effect=Exception("Connection error")) as mock_post:
        results = await vector_db_client.search_documents("test query")

        # Verify the post was called once
        mock_post.assert_called_once()
        
        # Should return empty list on HTTP exception
        assert results == []
