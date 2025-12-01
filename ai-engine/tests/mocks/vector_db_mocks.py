"""
Mocks for vector database dependencies to avoid installing heavy packages in tests.

This module provides mocks for:
- chromadb
- sentence-transformers
- pgvector
"""

import sys
from unittest.mock import MagicMock

# Mock chromadb
def mock_chromadb():
    """Create a comprehensive mock for chromadb module."""
    chromadb_mock = MagicMock()

    # Mock Client
    client_mock = MagicMock()
    chromadb_mock.Client = MagicMock(return_value=client_mock)

    # Mock Collection
    collection_mock = MagicMock()
    collection_mock.name = "test_collection"
    collection_mock.count = MagicMock(return_value=10)
    client_mock.get_or_create_collection = MagicMock(return_value=collection_mock)

    # Mock query results
    query_result = {
        "ids": [["doc1", "doc2", "doc3"]],
        "documents": [["Document 1 content", "Document 2 content", "Document 3 content"]],
        "metadatas": [[{"source": "test1"}, {"source": "test2"}, {"source": "test3"}]],
        "distances": [[0.1, 0.2, 0.3]]
    }
    collection_mock.query = MagicMock(return_value=query_result)

    # Mock add results
    collection_mock.add = MagicMock(return_value=["id1", "id2", "id3"])

    return chromadb_mock

# Mock sentence-transformers
def mock_sentence_transformers():
    """Create a comprehensive mock for sentence-transformers module."""
    sentence_transformers_mock = MagicMock()

    # Mock SentenceTransformer
    transformer_mock = MagicMock()

    # Mock encode method
    def mock_encode(texts, **kwargs):
        # Return different embeddings based on input
        if isinstance(texts, str):
            return [0.1, 0.2, 0.3]
        elif isinstance(texts, list):
            return [[0.1, 0.2, 0.3] for _ in texts]
        return [[0.1, 0.2, 0.3]]

    transformer_mock.encode = MagicMock(side_effect=mock_encode)
    sentence_transformers_mock.SentenceTransformer = MagicMock(return_value=transformer_mock)

    # Mock util module
    util_mock = MagicMock()
    util_mock.cos_sim = MagicMock(return_value=0.8)
    sentence_transformers_mock.util = util_mock

    return sentence_transformers_mock

# Apply mocks
def apply_vector_db_mocks():
    """Apply all vector database mocks to sys.modules."""
    sys.modules['chromadb'] = mock_chromadb()
    sys.modules['sentence_transformers'] = mock_sentence_transformers()
    sys.modules['sentence_transformers.util'] = sys.modules['sentence_transformers'].util

    # Mock pgvector if needed
    pgvector_mock = MagicMock()
    sys.modules['pgvector'] = pgvector_mock
    sys.modules['pgvector.sqlalchemy'] = MagicMock()
    sys.modules['pgvector.sqlalchemy.VECTOR'] = MagicMock()
