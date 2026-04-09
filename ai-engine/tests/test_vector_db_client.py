"""
Unit tests for VectorDBClient.
"""

import unittest
import httpx
from unittest.mock import patch, MagicMock, AsyncMock
from utils.vector_db_client import VectorDBClient

class TestVectorDBClient(unittest.IsolatedAsyncioTestCase):
    """Tests for VectorDBClient."""

    async def asyncSetUp(self):
        """Set up test fixtures."""
        self.base_url = "http://test-backend:8000/api/v1"
        self.client = VectorDBClient(base_url=self.base_url)

    async def asyncTearDown(self):
        """Tear down test fixtures."""
        await self.client.close()

    @patch("utils.vector_db_client.get_embedding_config")
    def test_initialization(self, mock_config):
        """Test that client initializes correctly."""
        mock_config.return_value = {"provider": "local"}
        client = VectorDBClient(base_url="http://another-backend:8000")
        self.assertEqual(client.base_url, "http://another-backend:8000")
        self.assertEqual(client._provider, "local")

    @patch("utils.embedding_generator.LocalEmbeddingGenerator.generate_embedding")
    async def test_get_embedding(self, mock_generate):
        """Test generating an embedding."""
        # Mock embedding result
        mock_result = MagicMock()
        import numpy as np
        mock_result.embedding = np.array([0.1, 0.2, 0.3])
        mock_generate.return_value = mock_result
        
        embedding = await self.client.get_embedding("test text")
        
        self.assertIsNotNone(embedding)
        self.assertEqual(embedding, [0.1, 0.2, 0.3])
        mock_generate.assert_called_once_with("test text")
        
        # Test caching
        mock_generate.reset_mock()
        embedding2 = await self.client.get_embedding("test text")
        self.assertEqual(embedding2, [0.1, 0.2, 0.3])
        mock_generate.assert_not_called()

    @patch("utils.embedding_generator.LocalEmbeddingGenerator.generate_embedding")
    async def test_index_document(self, mock_generate):
        """Test indexing a document."""
        # Mock embedding result
        mock_result = MagicMock()
        import numpy as np
        mock_result.embedding = np.array([0.1, 0.2, 0.3])
        mock_generate.return_value = mock_result
        
        # Mock HTTP response
        with patch.object(self.client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(status_code=201)
            
            success = await self.client.index_document("test content", "test_source.txt")
            
            self.assertTrue(success)
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            self.assertEqual(args[0], "/embeddings/")
            payload = kwargs["json"]
            self.assertEqual(payload["document_source"], "test_source.txt")
            self.assertEqual(payload["embedding"], [0.1, 0.2, 0.3])

    @patch("utils.embedding_generator.LocalEmbeddingGenerator.generate_embedding")
    async def test_search_documents(self, mock_generate):
        """Test searching for documents."""
        # Mock embedding result
        mock_result = MagicMock()
        import numpy as np
        mock_result.embedding = np.array([0.1, 0.2, 0.3])
        mock_generate.return_value = mock_result
        
        # Mock HTTP response
        with patch.object(self.client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [
                    {"document_source": "doc1.txt", "similarity_score": 0.9, "content": "found content"}
                ]
            }
            mock_post.return_value = mock_response
            
            results = await self.client.search_documents("search query", top_k=5)
            
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["document_source"], "doc1.txt")
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            payload = kwargs["json"]
            self.assertEqual(payload["query_embedding"], [0.1, 0.2, 0.3])
            self.assertEqual(payload["top_k"], 5)

    async def test_error_handling(self):
        """Test error handling in indexing and search."""
        # Test HTTP error in search
        with patch.object(self.client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.RequestError("Connection failed")
            
            # Indexing failure
            success = await self.client.index_document("content", "source")
            self.assertFalse(success)
            
            # Search failure
            results = await self.client.search_documents("query")
            self.assertEqual(results, [])

if __name__ == "__main__":
    unittest.main()
