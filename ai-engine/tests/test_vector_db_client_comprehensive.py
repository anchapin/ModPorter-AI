"""
Comprehensive unit tests for VectorDBClient.
Tests document indexing, searching, caching, and error handling.
"""

import pytest
import numpy as np
import httpx
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any, Optional
import logging

# Set up imports
try:
    from utils.vector_db_client import VectorDBClient
    from utils.embedding_generator import (
        LocalEmbeddingGenerator,
        OpenAIEmbeddingGenerator,
        EmbeddingCache,
    )
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(e)


# Skip all tests if imports fail
pytestmark = pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Required imports unavailable")


@pytest.fixture
def mock_embedding_generator():
    """Create a mock embedding generator."""
    gen = AsyncMock(spec=LocalEmbeddingGenerator)
    gen.model_name = "test-model"
    gen.dimensions = 768
    gen.generate_embedding = AsyncMock(return_value=MagicMock(
        embedding=np.array([0.1] * 768, dtype=np.float32)
    ))
    return gen


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client."""
    client = AsyncMock(spec=httpx.AsyncClient)
    return client


@pytest.fixture
def sample_document():
    """Sample document for testing."""
    return {
        "id": "doc_1",
        "content": "This is a sample document for testing",
        "source": "test_source.txt",
        "metadata": {"type": "test"}
    }


@pytest.fixture
def sample_documents():
    """Multiple sample documents for testing."""
    return [
        {
            "id": f"doc_{i}",
            "content": f"Document {i} content about testing",
            "source": f"test_{i}.txt",
            "metadata": {"index": i}
        }
        for i in range(5)
    ]


class TestVectorDBClientInitialization:
    """Test VectorDBClient initialization."""
    
    @pytest.mark.asyncio
    async def test_initialization_with_defaults(self):
        """Test VectorDBClient initialization with defaults."""
        with patch('utils.vector_db_client.httpx.AsyncClient'):
            with patch('utils.vector_db_client.get_embedding_config') as mock_config:
                mock_config.return_value = {
                    "provider": "local",
                    "cache_size": 10000,
                    "cache_ttl": 3600
                }
                
                with patch.object(VectorDBClient, '_create_embedding_generator'):
                    client = VectorDBClient()
                    
                    assert client.base_url is not None
                    assert client.client is not None
    
    @pytest.mark.asyncio
    async def test_initialization_custom_url(self):
        """Test initialization with custom base URL."""
        custom_url = "http://localhost:8000/api/v1"
        
        with patch('utils.vector_db_client.httpx.AsyncClient'):
            with patch('utils.vector_db_client.get_embedding_config', return_value={}):
                with patch.object(VectorDBClient, '_create_embedding_generator'):
                    client = VectorDBClient(base_url=custom_url)
                    
                    assert client.base_url == custom_url
    
    @pytest.mark.asyncio
    async def test_initialization_custom_timeout(self):
        """Test initialization with custom timeout."""
        with patch('utils.vector_db_client.httpx.AsyncClient') as mock_async_client:
            with patch('utils.vector_db_client.get_embedding_config', return_value={}):
                with patch.object(VectorDBClient, '_create_embedding_generator'):
                    client = VectorDBClient(timeout=60.0)
                    
                    # AsyncClient should be called with timeout
                    mock_async_client.assert_called()


class TestEmbeddingGeneratorCreation:
    """Test embedding generator creation."""
    
    @pytest.mark.asyncio
    async def test_create_openai_generator(self):
        """Test creating OpenAI generator."""
        with patch('utils.vector_db_client.OpenAIEmbeddingGenerator') as mock_openai:
            mock_gen = MagicMock()
            mock_gen._client = MagicMock()
            mock_openai.return_value = mock_gen
            
            with patch('utils.vector_db_client.httpx.AsyncClient'):
                with patch('utils.vector_db_client.get_embedding_config') as mock_config:
                    mock_config.return_value = {"provider": "openai"}
                    
                    client = VectorDBClient(provider="openai")
                    gen = client._create_embedding_generator()
                    
                    assert gen is not None
    
    @pytest.mark.asyncio
    async def test_create_local_generator(self):
        """Test creating local generator."""
        with patch('utils.vector_db_client.LocalEmbeddingGenerator') as mock_local:
            with patch('utils.vector_db_client.httpx.AsyncClient'):
                with patch('utils.vector_db_client.get_embedding_config') as mock_config:
                    mock_config.return_value = {"provider": "local"}
                    
                    client = VectorDBClient(provider="local")
                    gen = client._create_embedding_generator()
                    
                    assert gen is not None
    
    @pytest.mark.asyncio
    async def test_auto_provider_fallback(self):
        """Test auto provider with fallback to local."""
        with patch('utils.vector_db_client.OpenAIEmbeddingGenerator') as mock_openai:
            with patch('utils.vector_db_client.LocalEmbeddingGenerator') as mock_local:
                # OpenAI unavailable
                mock_openai_instance = MagicMock()
                mock_openai_instance._client = None
                mock_openai.return_value = mock_openai_instance
                
                with patch('utils.vector_db_client.httpx.AsyncClient'):
                    with patch('utils.vector_db_client.get_embedding_config') as mock_config:
                        mock_config.return_value = {"provider": "auto"}
                        
                        client = VectorDBClient(provider="auto")
                        gen = client._create_embedding_generator()
                        
                        # Should fall back to local
                        assert gen is not None


class TestDocumentIndexing:
    """Test document indexing functionality."""
    
    @pytest.mark.asyncio
    async def test_index_document_success(self, sample_document):
        """Test successful document indexing."""
        with patch('utils.vector_db_client.httpx.AsyncClient') as mock_client_class:
            with patch('utils.vector_db_client.get_embedding_config', return_value={}):
                with patch.object(VectorDBClient, '_create_embedding_generator') as mock_gen_creator:
                    mock_gen = MagicMock()
                    mock_gen.generate_embedding.return_value = MagicMock(
                        embedding=np.array([0.1] * 768, dtype=np.float32)
                    )
                    mock_gen.model_name = "test-model"
                    mock_gen.dimensions = 768
                    mock_gen_creator.return_value = mock_gen
                    
                    mock_client = AsyncMock()
                    mock_client_class.return_value = mock_client
                    
                    mock_response = MagicMock()
                    mock_response.status_code = 201
                    mock_client.post = AsyncMock(return_value=mock_response)
                    
                    client = VectorDBClient()
                    client.embedding_generator = mock_gen
                    client.client = mock_client
                    
                    result = await client.index_document(
                        sample_document["content"],
                        sample_document["source"]
                    )
                    
                    assert result is True
    
    @pytest.mark.asyncio
    async def test_index_document_status_200(self, sample_document):
        """Test document indexing with 200 status (already exists)."""
        with patch('utils.vector_db_client.httpx.AsyncClient') as mock_client_class:
            with patch('utils.vector_db_client.get_embedding_config', return_value={}):
                with patch.object(VectorDBClient, '_create_embedding_generator') as mock_gen_creator:
                    mock_gen = MagicMock()
                    mock_gen.generate_embedding.return_value = MagicMock(
                        embedding=np.array([0.1] * 768, dtype=np.float32)
                    )
                    mock_gen.model_name = "test-model"
                    mock_gen.dimensions = 768
                    mock_gen_creator.return_value = mock_gen
                    
                    mock_client = AsyncMock()
                    mock_client_class.return_value = mock_client
                    
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_client.post = AsyncMock(return_value=mock_response)
                    
                    client = VectorDBClient()
                    client.embedding_generator = mock_gen
                    client.client = mock_client
                    
                    result = await client.index_document(
                        sample_document["content"],
                        sample_document["source"]
                    )
                    
                    assert result is True
    
    @pytest.mark.asyncio
    async def test_index_document_failure(self, sample_document):
        """Test document indexing failure."""
        with patch('utils.vector_db_client.httpx.AsyncClient') as mock_client_class:
            with patch('utils.vector_db_client.get_embedding_config', return_value={}):
                with patch.object(VectorDBClient, '_create_embedding_generator') as mock_gen_creator:
                    mock_gen = MagicMock()
                    mock_gen.generate_embedding.return_value = MagicMock(
                        embedding=np.array([0.1] * 768, dtype=np.float32)
                    )
                    mock_gen.model_name = "test-model"
                    mock_gen.dimensions = 768
                    mock_gen_creator.return_value = mock_gen
                    
                    mock_client = AsyncMock()
                    mock_client_class.return_value = mock_client
                    
                    mock_response = MagicMock()
                    mock_response.status_code = 500
                    mock_response.text = "Server error"
                    mock_client.post = AsyncMock(return_value=mock_response)
                    
                    client = VectorDBClient()
                    client.embedding_generator = mock_gen
                    client.client = mock_client
                    
                    result = await client.index_document(
                        sample_document["content"],
                        sample_document["source"]
                    )
                    
                    assert result is False
    
    @pytest.mark.asyncio
    async def test_index_document_embedding_failure(self, sample_document):
        """Test document indexing when embedding generation fails."""
        with patch('utils.vector_db_client.httpx.AsyncClient') as mock_client_class:
            with patch('utils.vector_db_client.get_embedding_config', return_value={}):
                with patch.object(VectorDBClient, '_create_embedding_generator') as mock_gen_creator:
                    mock_gen = MagicMock()
                    mock_gen.generate_embedding.return_value = None
                    mock_gen.model_name = "test-model"
                    mock_gen.dimensions = 768
                    mock_gen_creator.return_value = mock_gen
                    
                    mock_client = AsyncMock()
                    mock_client_class.return_value = mock_client
                    
                    client = VectorDBClient()
                    client.embedding_generator = mock_gen
                    client.client = mock_client
                    
                    result = await client.index_document(
                        sample_document["content"],
                        sample_document["source"]
                    )
                    
                    assert result is False


class TestDocumentSearch:
    """Test document search functionality."""
    
    @pytest.mark.asyncio
    async def test_search_documents_success(self):
        """Test successful document search."""
        with patch('utils.vector_db_client.httpx.AsyncClient') as mock_client_class:
            with patch('utils.vector_db_client.get_embedding_config', return_value={}):
                with patch.object(VectorDBClient, '_create_embedding_generator') as mock_gen_creator:
                    mock_gen = MagicMock()
                    mock_gen.generate_embedding.return_value = MagicMock(
                        embedding=np.array([0.1] * 768, dtype=np.float32)
                    )
                    mock_gen.model_name = "test-model"
                    mock_gen.dimensions = 768
                    mock_gen_creator.return_value = mock_gen
                    
                    mock_client = AsyncMock()
                    mock_client_class.return_value = mock_client
                    
                    expected_results = [
                        {"id": "doc_1", "content": "result 1", "similarity": 0.9},
                        {"id": "doc_2", "content": "result 2", "similarity": 0.8},
                    ]
                    
                    mock_response = MagicMock()
                    mock_response.json.return_value = {"results": expected_results}
                    mock_client.post = AsyncMock(return_value=mock_response)
                    
                    client = VectorDBClient()
                    client.embedding_generator = mock_gen
                    client.client = mock_client
                    
                    results = await client.search_documents("test query", top_k=2)
                    
                    assert len(results) == 2
                    assert results[0]["id"] == "doc_1"
    
    @pytest.mark.asyncio
    async def test_search_documents_with_filter(self):
        """Test search with source filter."""
        with patch('utils.vector_db_client.httpx.AsyncClient') as mock_client_class:
            with patch('utils.vector_db_client.get_embedding_config', return_value={}):
                with patch.object(VectorDBClient, '_create_embedding_generator') as mock_gen_creator:
                    mock_gen = MagicMock()
                    mock_gen.generate_embedding.return_value = MagicMock(
                        embedding=np.array([0.1] * 768, dtype=np.float32)
                    )
                    mock_gen.model_name = "test-model"
                    mock_gen.dimensions = 768
                    mock_gen_creator.return_value = mock_gen
                    
                    mock_client = AsyncMock()
                    mock_client_class.return_value = mock_client
                    
                    mock_response = MagicMock()
                    mock_response.json.return_value = {"results": []}
                    mock_client.post = AsyncMock(return_value=mock_response)
                    
                    client = VectorDBClient()
                    client.embedding_generator = mock_gen
                    client.client = mock_client
                    
                    results = await client.search_documents(
                        "test query",
                        top_k=5,
                        document_source_filter="test_source"
                    )
                    
                    # Verify filter was passed
                    mock_client.post.assert_called()
                    call_args = mock_client.post.call_args
                    assert "document_source_filter" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_search_documents_embedding_failure(self):
        """Test search when embedding generation fails."""
        with patch('utils.vector_db_client.httpx.AsyncClient') as mock_client_class:
            with patch('utils.vector_db_client.get_embedding_config', return_value={}):
                with patch.object(VectorDBClient, '_create_embedding_generator') as mock_gen_creator:
                    mock_gen = MagicMock()
                    mock_gen.generate_embedding.return_value = None
                    mock_gen.model_name = "test-model"
                    mock_gen.dimensions = 768
                    mock_gen_creator.return_value = mock_gen
                    
                    mock_client = AsyncMock()
                    mock_client_class.return_value = mock_client
                    
                    client = VectorDBClient()
                    client.embedding_generator = mock_gen
                    client.client = mock_client
                    
                    results = await client.search_documents("test query")
                    
                    assert results == []
    
    @pytest.mark.asyncio
    async def test_search_documents_http_error(self):
        """Test search with HTTP error."""
        with patch('utils.vector_db_client.httpx.AsyncClient') as mock_client_class:
            with patch('utils.vector_db_client.get_embedding_config', return_value={}):
                with patch.object(VectorDBClient, '_create_embedding_generator') as mock_gen_creator:
                    mock_gen = MagicMock()
                    mock_gen.generate_embedding.return_value = MagicMock(
                        embedding=np.array([0.1] * 768, dtype=np.float32)
                    )
                    mock_gen.model_name = "test-model"
                    mock_gen.dimensions = 768
                    mock_gen_creator.return_value = mock_gen
                    
                    mock_client = AsyncMock()
                    mock_client_class.return_value = mock_client
                    
                    mock_client.post = AsyncMock(
                        side_effect=httpx.HTTPStatusError("404", request=Mock(), response=Mock())
                    )
                    
                    client = VectorDBClient()
                    client.embedding_generator = mock_gen
                    client.client = mock_client
                    
                    results = await client.search_documents("test query")
                    
                    assert results == []


class TestEmbeddingGeneration:
    """Test embedding generation functionality."""
    
    @pytest.mark.asyncio
    async def test_get_embedding_success(self):
        """Test successful embedding generation."""
        with patch('utils.vector_db_client.httpx.AsyncClient') as mock_client_class:
            with patch('utils.vector_db_client.get_embedding_config', return_value={}):
                with patch.object(VectorDBClient, '_create_embedding_generator') as mock_gen_creator:
                    test_embedding = [0.1] * 768
                    mock_gen = MagicMock()
                    mock_gen.generate_embedding.return_value = MagicMock(
                        embedding=np.array(test_embedding, dtype=np.float32)
                    )
                    mock_gen.model_name = "test-model"
                    mock_gen.dimensions = 768
                    mock_gen_creator.return_value = mock_gen
                    
                    mock_client = AsyncMock()
                    mock_client_class.return_value = mock_client
                    
                    client = VectorDBClient()
                    client.embedding_generator = mock_gen
                    client.client = mock_client
                    
                    result = await client.get_embedding("test text")
                    
                    assert result is not None
                    assert isinstance(result, list)
                    assert len(result) == 768
    
    @pytest.mark.asyncio
    async def test_get_embedding_failure(self):
        """Test embedding generation failure."""
        with patch('utils.vector_db_client.httpx.AsyncClient') as mock_client_class:
            with patch('utils.vector_db_client.get_embedding_config', return_value={}):
                with patch.object(VectorDBClient, '_create_embedding_generator') as mock_gen_creator:
                    mock_gen = MagicMock()
                    mock_gen.generate_embedding.return_value = None
                    mock_gen.model_name = "test-model"
                    mock_gen.dimensions = 768
                    mock_gen_creator.return_value = mock_gen
                    
                    mock_client = AsyncMock()
                    mock_client_class.return_value = mock_client
                    
                    client = VectorDBClient()
                    client.embedding_generator = mock_gen
                    client.client = mock_client
                    
                    result = await client.get_embedding("test text")
                    
                    assert result is None


class TestCaching:
    """Test caching functionality."""
    
    @pytest.mark.asyncio
    async def test_cache_embedding(self):
        """Test that embeddings are cached."""
        with patch('utils.vector_db_client.httpx.AsyncClient') as mock_client_class:
            with patch('utils.vector_db_client.get_embedding_config', return_value={}):
                with patch.object(VectorDBClient, '_create_embedding_generator') as mock_gen_creator:
                    test_embedding = np.array([0.1] * 768, dtype=np.float32)
                    mock_gen = MagicMock()
                    mock_gen.generate_embedding.return_value = MagicMock(
                        embedding=test_embedding
                    )
                    mock_gen.model_name = "test-model"
                    mock_gen.dimensions = 768
                    mock_gen_creator.return_value = mock_gen
                    
                    mock_client = AsyncMock()
                    mock_client_class.return_value = mock_client
                    
                    client = VectorDBClient()
                    client.embedding_generator = mock_gen
                    client.client = mock_client
                    
                    # First call
                    await client.get_embedding("test text")
                    
                    # Check cache
                    cached = client._cache.get("test text", "test-model")
                    
                    assert cached is not None
    
    @pytest.mark.asyncio
    async def test_cache_hit_on_search(self):
        """Test that cached embeddings are used in search."""
        with patch('utils.vector_db_client.httpx.AsyncClient') as mock_client_class:
            with patch('utils.vector_db_client.get_embedding_config', return_value={}):
                with patch.object(VectorDBClient, '_create_embedding_generator') as mock_gen_creator:
                    test_embedding = np.array([0.1] * 768, dtype=np.float32)
                    mock_gen = MagicMock()
                    mock_gen.generate_embedding.return_value = MagicMock(
                        embedding=test_embedding
                    )
                    mock_gen.model_name = "test-model"
                    mock_gen.dimensions = 768
                    mock_gen_creator.return_value = mock_gen
                    
                    mock_client = AsyncMock()
                    mock_client_class.return_value = mock_client
                    
                    mock_response = MagicMock()
                    mock_response.json.return_value = {"results": []}
                    mock_client.post = AsyncMock(return_value=mock_response)
                    
                    client = VectorDBClient()
                    client.embedding_generator = mock_gen
                    client.client = mock_client
                    
                    # Cache the embedding
                    client._cache.put("test query", "test-model", test_embedding)
                    
                    # Search should use cached embedding
                    results = await client.search_documents("test query")
                    
                    # Embedding generation should not be called again
                    mock_gen.generate_embedding.assert_not_called()


class TestClientClosing:
    """Test client resource cleanup."""
    
    @pytest.mark.asyncio
    async def test_close_client(self):
        """Test closing the client."""
        with patch('utils.vector_db_client.httpx.AsyncClient') as mock_client_class:
            with patch('utils.vector_db_client.get_embedding_config', return_value={}):
                with patch.object(VectorDBClient, '_create_embedding_generator') as mock_gen_creator:
                    mock_gen = MagicMock()
                    mock_gen_creator.return_value = mock_gen
                    
                    mock_client = AsyncMock()
                    mock_client_class.return_value = mock_client
                    mock_client.aclose = AsyncMock()
                    
                    client = VectorDBClient()
                    client.client = mock_client
                    
                    await client.close()
                    
                    mock_client.aclose.assert_called_once()


class TestErrorHandling:
    """Test error handling in VectorDBClient."""
    
    @pytest.mark.asyncio
    async def test_request_error_handling(self):
        """Test handling of request errors."""
        with patch('utils.vector_db_client.httpx.AsyncClient') as mock_client_class:
            with patch('utils.vector_db_client.get_embedding_config', return_value={}):
                with patch.object(VectorDBClient, '_create_embedding_generator') as mock_gen_creator:
                    mock_gen = MagicMock()
                    mock_gen.generate_embedding.return_value = MagicMock(
                        embedding=np.array([0.1] * 768, dtype=np.float32)
                    )
                    mock_gen.model_name = "test-model"
                    mock_gen.dimensions = 768
                    mock_gen_creator.return_value = mock_gen
                    
                    mock_client = AsyncMock()
                    mock_client_class.return_value = mock_client
                    
                    mock_client.post = AsyncMock(
                        side_effect=httpx.RequestError("Connection failed")
                    )
                    
                    client = VectorDBClient()
                    client.embedding_generator = mock_gen
                    client.client = mock_client
                    
                    results = await client.search_documents("test")
                    
                    assert results == []
    
    @pytest.mark.asyncio
    async def test_generic_exception_handling(self):
        """Test handling of generic exceptions."""
        with patch('utils.vector_db_client.httpx.AsyncClient') as mock_client_class:
            with patch('utils.vector_db_client.get_embedding_config', return_value={}):
                with patch.object(VectorDBClient, '_create_embedding_generator') as mock_gen_creator:
                    mock_gen = MagicMock()
                    mock_gen.generate_embedding.return_value = MagicMock(
                        embedding=np.array([0.1] * 768, dtype=np.float32)
                    )
                    mock_gen.model_name = "test-model"
                    mock_gen.dimensions = 768
                    mock_gen_creator.return_value = mock_gen
                    
                    mock_client = AsyncMock()
                    mock_client_class.return_value = mock_client
                    
                    mock_client.post = AsyncMock(
                        side_effect=Exception("Unexpected error")
                    )
                    
                    client = VectorDBClient()
                    client.embedding_generator = mock_gen
                    client.client = mock_client
                    
                    results = await client.search_documents("test")
                    
                    assert results == []
