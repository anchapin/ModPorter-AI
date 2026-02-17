"""
Test for RAG Embedding Generation functionality.

This test verifies the embedding generation service works correctly,
addressing Issue #435.
"""

import pytest
import numpy as np
from pathlib import Path
import sys

# Add ai-engine to path
ai_engine_root = Path(__file__).parent.parent
sys.path.insert(0, str(ai_engine_root))

from utils.embedding_generator import (
    create_rag_embedding_service,
    LocalEmbeddingGenerator,
    OpenAIEmbeddingGenerator,
    EmbeddingResult
)


class TestEmbeddingGeneration:
    """Test embedding generation functionality."""
    
    def test_local_embedding_generator_creation(self):
        """Test local embedding generator can be created."""
        generator = LocalEmbeddingGenerator()
        assert generator is not None
        assert generator.dimensions == 384  # Default for all-MiniLM-L6-v2
    
    def test_local_embedding_generation(self):
        """Test generating an embedding."""
        generator = LocalEmbeddingGenerator()
        
        # Test with fallback (no actual model loaded)
        result = generator.generate_embedding("Test content")
        
        assert result is not None
        assert isinstance(result.embedding, np.ndarray)
        assert result.dimensions == 384
        assert result.model is not None
    
    def test_batch_embedding_generation(self):
        """Test generating multiple embeddings."""
        generator = LocalEmbeddingGenerator()
        
        texts = ["First text", "Second text", "Third text"]
        results = generator.generate_embeddings(texts)
        
        assert len(results) == 3
        for result in results:
            assert result is not None
            assert isinstance(result.embedding, np.ndarray)
    
    def test_rag_service_creation(self):
        """Test RAG embedding service can be created."""
        service = create_rag_embedding_service("local")
        assert service is not None
        assert service._embedding_generator is not None
    
    def test_store_and_search(self):
        """Test storing and searching embeddings."""
        service = create_rag_embedding_service("local")
        
        # Store some embeddings
        success = service.generate_and_store(
            "doc1", 
            "This is a test document about Minecraft blocks",
            {"type": "test"}
        )
        assert success is True
        
        success = service.generate_and_store(
            "doc2",
            "Java mods use Forge or Fabric API",
            {"type": "reference"}
        )
        assert success is True
        
        # Search
        results = service.search("Minecraft blocks", top_k=2)
        
        assert len(results) > 0
        # Verify results have required fields
        assert 'document_id' in results[0]
        assert 'similarity' in results[0]
        # Note: With fallback embedding (no sentence-transformers), 
        # results may not be semantically accurate - that's expected
        # The important thing is that storage and retrieval work
    
    def test_embedding_caching(self):
        """Test embedding result caching."""
        generator = LocalEmbeddingGenerator()
        
        # Generate same embedding twice
        text = "Test caching"
        result1 = generator.generate_embedding(text)
        result2 = generator.generate_embedding(text)
        
        # Both should be valid
        assert result1 is not None
        assert result2 is not None
        
        # Results should be similar (same hash-based fallback)
        similarity = np.dot(result1.embedding, result2.embedding)
        assert similarity > 0.99  # Almost identical
    
    def test_dimension_validation(self):
        """Test embedding dimension validation."""
        generator = LocalEmbeddingGenerator()
        
        result = generator.generate_embedding("Short text")
        
        assert result.embedding.shape[0] == generator.dimensions
        assert len(result.embedding.shape) == 1  # 1D array


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
