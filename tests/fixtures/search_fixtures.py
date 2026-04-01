"""
Search testing fixtures for RAG and vector database tests.
Provides mock data for embedding, search, and document indexing tests.
"""

import pytest
import numpy as np
from typing import Dict, List, Any, Optional


# Mock documents for search testing
mock_documents = [
    {
        "id": "doc_1",
        "content": "The quick brown fox jumps over the lazy dog",
        "source": "test_document_1.txt",
        "metadata": {"type": "simple", "length": 44}
    },
    {
        "id": "doc_2",
        "content": "Machine learning is a subset of artificial intelligence",
        "source": "test_document_2.txt",
        "metadata": {"type": "technical", "length": 55}
    },
    {
        "id": "doc_3",
        "content": "Python is a programming language used for data science",
        "source": "test_document_3.txt",
        "metadata": {"type": "technical", "length": 55}
    },
    {
        "id": "doc_4",
        "content": "The weather today is sunny and warm",
        "source": "test_document_4.txt",
        "metadata": {"type": "weather", "length": 36}
    },
    {
        "id": "doc_5",
        "content": "Data science involves statistics and programming",
        "source": "test_document_5.txt",
        "metadata": {"type": "technical", "length": 47}
    },
]


# Mock embeddings for documents (768-dimensional vectors for testing)
mock_embeddings = {
    "doc_1": np.array([0.1, 0.2, 0.15, 0.05, 0.3] + [0.1] * 763, dtype=np.float32),
    "doc_2": np.array([0.9, 0.85, 0.8, 0.75, 0.7] + [0.8] * 763, dtype=np.float32),
    "doc_3": np.array([0.85, 0.8, 0.75, 0.7, 0.65] + [0.75] * 763, dtype=np.float32),
    "doc_4": np.array([0.2, 0.25, 0.3, 0.15, 0.2] + [0.2] * 763, dtype=np.float32),
    "doc_5": np.array([0.8, 0.75, 0.7, 0.65, 0.6] + [0.7] * 763, dtype=np.float32),
}


# Normalize embeddings
for doc_id in mock_embeddings:
    emb = mock_embeddings[doc_id]
    mock_embeddings[doc_id] = emb / (np.linalg.norm(emb) + 1e-8)


# Mock query embeddings
mock_query_embedding = np.array([0.85, 0.8, 0.75, 0.7, 0.65] + [0.75] * 763, dtype=np.float32)
mock_query_embedding = mock_query_embedding / (np.linalg.norm(mock_query_embedding) + 1e-8)


# Test queries
test_queries = [
    "machine learning and artificial intelligence",
    "Python programming for data science",
    "weather conditions today",
    "quick fox",
    "statistics and data analysis",
]


# Search results for testing
expected_search_results = {
    "machine learning and artificial intelligence": [
        {"id": "doc_2", "similarity": 0.95, "content": "Machine learning is a subset of artificial intelligence"},
        {"id": "doc_5", "similarity": 0.7, "content": "Data science involves statistics and programming"},
        {"id": "doc_3", "similarity": 0.65, "content": "Python is a programming language used for data science"},
    ],
    "Python programming for data science": [
        {"id": "doc_3", "similarity": 0.92, "content": "Python is a programming language used for data science"},
        {"id": "doc_5", "similarity": 0.8, "content": "Data science involves statistics and programming"},
        {"id": "doc_2", "similarity": 0.6, "content": "Machine learning is a subset of artificial intelligence"},
    ],
}


@pytest.fixture
def mock_document_list():
    """Fixture providing mock documents for testing."""
    return mock_documents.copy()


@pytest.fixture
def mock_embedding_vectors():
    """Fixture providing mock embeddings for testing."""
    return {k: v.copy() for k, v in mock_embeddings.items()}


@pytest.fixture
def mock_query_vec():
    """Fixture providing a mock query embedding."""
    return mock_query_embedding.copy()


@pytest.fixture
def test_query_list():
    """Fixture providing test queries."""
    return test_queries.copy()


@pytest.fixture
def mock_search_result_map():
    """Fixture providing expected search results."""
    return expected_search_results.copy()


@pytest.fixture
def sample_document_chunk():
    """Fixture providing a sample document chunk for testing."""
    return {
        "id": "chunk_1",
        "content": "This is a sample document chunk for testing embedding and search functionality",
        "source": "sample_document.txt",
        "metadata": {"chunk_index": 0, "document_id": "doc_1"}
    }


@pytest.fixture
def sample_embedding_vector():
    """Fixture providing a sample embedding vector."""
    vec = np.random.randn(768).astype(np.float32)
    return vec / (np.linalg.norm(vec) + 1e-8)


@pytest.fixture
def batch_documents():
    """Fixture providing a batch of documents for batch processing tests."""
    return [
        {
            "id": f"batch_doc_{i}",
            "content": f"This is batch document number {i}",
            "source": f"batch_document_{i}.txt",
            "metadata": {"batch_index": i}
        }
        for i in range(10)
    ]


@pytest.fixture
def embedding_config():
    """Fixture providing embedding configuration."""
    return {
        "provider": "local",
        "model": "all-MiniLM-L6-v2",
        "dimensions": 768,
        "cache_enabled": True,
        "cache_size": 1000,
        "cache_ttl": 3600,
    }


@pytest.fixture
def vector_db_config():
    """Fixture providing vector database configuration."""
    return {
        "base_url": "http://backend:8000/api/v1",
        "timeout": 30.0,
        "provider": "local",
    }


class MockVectorDBClient:
    """Mock vector database client for testing."""
    
    def __init__(self, documents=None):
        self.documents = documents or mock_documents.copy()
        self.embeddings = mock_embeddings.copy()
        self.indexed_docs = set()
    
    async def index_document(self, content: str, source: str) -> bool:
        """Mock document indexing."""
        doc_id = f"indexed_{len(self.indexed_docs)}"
        self.indexed_docs.add(doc_id)
        return True
    
    async def search_documents(
        self, query: str, top_k: int = 5, source_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Mock search functionality."""
        return [
            {
                "id": doc["id"],
                "similarity": 0.85 - (i * 0.1),
                "content": doc["content"],
                "source": doc["source"],
            }
            for i, doc in enumerate(self.documents[:top_k])
        ]
    
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Mock embedding generation."""
        if not text:
            return None
        return mock_query_embedding.tolist()
    
    async def close(self):
        """Mock client close."""
        pass


@pytest.fixture
def mock_vector_db_client():
    """Fixture providing a mock vector database client."""
    return MockVectorDBClient()


def create_mock_embeddings(num_vectors: int, dimensions: int = 768) -> np.ndarray:
    """Helper function to create random mock embeddings."""
    vectors = np.random.randn(num_vectors, dimensions).astype(np.float32)
    # Normalize each vector
    vectors = vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-8)
    return vectors


@pytest.fixture
def random_embeddings():
    """Fixture providing random embeddings for testing."""
    return create_mock_embeddings(10)


def compute_cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    if len(vec1) == 0 or len(vec2) == 0:
        return 0.0
    return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2) + 1e-8))


@pytest.fixture
def similarity_helper():
    """Fixture providing similarity computation helper."""
    return compute_cosine_similarity
