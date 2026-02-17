"""
Unit tests for embedding generation functionality.

These tests verify the embedding generation implementation for the RAG system.
"""

import numpy as np
import pytest
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.embedding_generator import (
    EmbeddingCache,
    validate_embedding_dimensions,
    get_embedding_config,
    EmbeddingResult,
    SUPPORTED_DIMENSIONS,
    DEFAULT_DIMENSION,
    CACHE_MAX_SIZE,
    CACHE_TTL_SECONDS
)


class TestEmbeddingCache:
    """Tests for the EmbeddingCache class."""
    
    def test_cache_initialization(self):
        """Test cache initializes with correct defaults."""
        cache = EmbeddingCache()
        assert cache._max_size == CACHE_MAX_SIZE
        assert cache._ttl_seconds == CACHE_TTL_SECONDS
        assert cache._hits == 0
        assert cache._misses == 0
    
    def test_cache_put_and_get(self):
        """Test storing and retrieving embeddings."""
        cache = EmbeddingCache()
        test_embedding = np.random.rand(1536).astype(np.float32)
        
        cache.put("test text", "test-model", test_embedding)
        result = cache.get("test text", "test-model")
        
        assert result is not None
        np.testing.assert_array_equal(result, test_embedding)
    
    def test_cache_miss(self):
        """Test cache returns None for non-existent entries."""
        cache = EmbeddingCache()
        result = cache.get("nonexistent text", "test-model")
        
        assert result is None
    
    def test_cache_stats(self):
        """Test cache statistics tracking."""
        cache = EmbeddingCache()
        test_embedding = np.random.rand(1536).astype(np.float32)
        
        cache.put("test text", "test-model", test_embedding)
        cache.get("test text", "test-model")  # hit
        cache.get("other text", "test-model")  # miss
        
        stats = cache.get_stats()
        
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['hit_rate'] == 0.5
    
    def test_cache_clear(self):
        """Test clearing cache resets all data."""
        cache = EmbeddingCache()
        test_embedding = np.random.rand(1536).astype(np.float32)
        
        cache.put("test text", "test-model", test_embedding)
        cache.clear()
        
        stats = cache.get_stats()
        assert stats['size'] == 0
        assert stats['hits'] == 0
        assert stats['misses'] == 0


class TestValidateEmbeddingDimensions:
    """Tests for embedding dimension validation."""
    
    def test_valid_dimensions(self):
        """Test validation passes for correct dimensions."""
        embedding = np.random.rand(1536).astype(np.float32)
        assert validate_embedding_dimensions(embedding, 1536) is True
    
    def test_invalid_dimensions(self):
        """Test validation fails for incorrect dimensions."""
        embedding = np.random.rand(1536).astype(np.float32)
        assert validate_embedding_dimensions(embedding, 384) is False
    
    def test_none_embedding(self):
        """Test validation fails for None input."""
        assert validate_embedding_dimensions(None, 1536) is False
    
    def test_non_numpy_array(self):
        """Test validation fails for non-numpy arrays."""
        assert validate_embedding_dimensions([1, 2, 3], 1536) is False
    
    def test_empty_array(self):
        """Test validation fails for empty arrays."""
        embedding = np.array([])
        assert validate_embedding_dimensions(embedding, 1536) is False


class TestGetEmbeddingConfig:
    """Tests for embedding configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = get_embedding_config()
        
        assert config['provider'] == 'auto'
        assert config['openai_model'] == 'text-embedding-ada-002'
        assert config['local_model'] == 'all-MiniLM-L6-v2'
        assert config['dimensions'] == DEFAULT_DIMENSION
        assert config['cache_enabled'] is True
        assert config['cache_size'] == CACHE_MAX_SIZE
    
    def test_custom_config_from_env(self):
        """Test configuration reads from environment variables."""
        with patch.dict(os.environ, {
            'EMBEDDING_PROVIDER': 'openai',
            'EMBEDDING_DIMENSIONS': '384'
        }):
            config = get_embedding_config()
            assert config['provider'] == 'openai'
            assert config['dimensions'] == 384


class TestEmbeddingResult:
    """Tests for EmbeddingResult dataclass."""
    
    def test_embedding_result_creation(self):
        """Test creating EmbeddingResult objects."""
        embedding = np.random.rand(1536).astype(np.float32)
        result = EmbeddingResult(
            embedding=embedding,
            model="test-model",
            dimensions=1536,
            token_count=10
        )
        
        assert result.model == "test-model"
        assert result.dimensions == 1536
        assert result.token_count == 10
    
    def test_embedding_result_without_token_count(self):
        """Test EmbeddingResult without token count."""
        embedding = np.random.rand(1536).astype(np.float32)
        result = EmbeddingResult(
            embedding=embedding,
            model="test-model",
            dimensions=1536
        )
        
        assert result.token_count is None


class TestSupportedDimensions:
    """Tests for supported dimension constants."""
    
    def test_supported_dimensions_contains_standard(self):
        """Test that standard dimensions are supported."""
        assert 1536 in SUPPORTED_DIMENSIONS  # OpenAI ada-002
        assert 384 in SUPPORTED_DIMENSIONS   # MiniLM-L6-v2
        assert 768 in SUPPORTED_DIMENSIONS   # BERT base
    
    def test_default_dimension_is_supported(self):
        """Test default dimension is in supported list."""
        assert DEFAULT_DIMENSION in SUPPORTED_DIMENSIONS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
