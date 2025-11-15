"""
Mocks for RAG system components to avoid complex dependencies in tests.

This module provides mocks for:
- search.hybrid_search_engine
- search.reranking_engine
- search.query_expansion
- utils.multimodal_embedding_generator
- utils.advanced_chunker
- schemas.multimodal_schema
- utils.vector_db_client
"""

import sys
from unittest.mock import MagicMock, Mock
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass

# Mock schemas.multimodal_schema
def mock_multimodal_schema():
    """Create a comprehensive mock for multimodal_schema module."""
    multimodal_schema_mock = MagicMock()

    # Create ContentType enum
    ContentType = Mock()
    ContentType.DOCUMENTATION = "documentation"
    ContentType.CODE = "code"
    ContentType.CONFIGURATION = "configuration"
    ContentType.IMAGE = "image"
    multimodal_schema_mock.ContentType = ContentType

    # Create SearchQuery
    @dataclass
    class MockSearchQuery:
        text: str
        content_types: List = None
        filters: Dict = None
        limit: int = 10

    multimodal_schema_mock.SearchQuery = MockSearchQuery

    # Create SearchResult
    @dataclass
    class MockSearchResult:
        document: Any
        matched_content: str
        relevance_score: float
        final_score: float
        rank: int
        similarity_score: float = 0.0
        keyword_score: float = 0.0

    multimodal_schema_mock.SearchResult = MockSearchResult

    # Create MultiModalDocument
    @dataclass
    class MockMultiModalDocument:
        id: str
        content: str
        content_type: str
        source_path: str
        metadata: Dict = None
        embedding: List = None

    multimodal_schema_mock.MultiModalDocument = MockMultiModalDocument

    return multimodal_schema_mock

# Mock search.hybrid_search_engine
def mock_hybrid_search_engine():
    """Create a comprehensive mock for hybrid_search_engine module."""
    hybrid_search_mock = MagicMock()

    # Create SearchMode enum
    SearchMode = Mock()
    SearchMode.SEMANTIC = "semantic"
    SearchMode.KEYWORD = "keyword"
    SearchMode.HYBRID = "hybrid"
    hybrid_search_mock.SearchMode = SearchMode

    # Create RankingStrategy enum
    RankingStrategy = Mock()
    RankingStrategy.RECIPROCAL_RANK = "reciprocal_rank"
    RankingStrategy.WEIGHTED_SUM = "weighted_sum"
    hybrid_search_mock.RankingStrategy = RankingStrategy

    # Create HybridSearchEngine class
    class MockHybridSearchEngine:
        def __init__(self, vector_db_client=None, **kwargs):
            self.vector_db_client = vector_db_client
            self.search_mode = "hybrid"
            self.ranking_strategy = "reciprocal_rank"

        async def search(self, query_text, content_types=None, limit=10, **kwargs):
            # Create mock results
            from schemas.multimodal_schema import SearchResult, MultiModalDocument

            mock_documents = [
                MultiModalDocument(
                    id=f"doc_{i}",
                    content=f"Mock content {i} about {query_text}",
                    content_type="documentation",
                    source_path=f"/mock/path/doc_{i}.md",
                    metadata={"source": "mock"}
                )
                for i in range(min(limit, 5))  # Return at most 5 results
            ]

            return [
                SearchResult(
                    document=doc,
                    matched_content=doc.content,
                    relevance_score=0.9 - (i * 0.1),
                    final_score=0.9 - (i * 0.1),
                    rank=i+1,
                    similarity_score=0.8 - (i * 0.1),
                    keyword_score=0.7 - (i * 0.05)
                )
                for i, doc in enumerate(mock_documents)
            ]

    hybrid_search_mock.HybridSearchEngine = MockHybridSearchEngine

    return hybrid_search_mock

# Mock search.reranking_engine
def mock_reranking_engine():
    """Create a comprehensive mock for reranking_engine module."""
    reranking_mock = MagicMock()

    class MockEnsembleReRanker:
        def __init__(self, **kwargs):
            self.reranking_enabled = True

        async def rerank(self, results, query, **kwargs):
            # Just reorder results slightly to simulate reranking
            if len(results) > 1:
                # Swap first two results
                results[0], results[1] = results[1], results[0]
                # Update scores
                results[0].final_score = 0.95
                results[1].final_score = 0.85
            return results

    reranking_mock.EnsembleReRanker = MockEnsembleReRanker

    return reranking_mock

# Mock search.query_expansion
def mock_query_expansion():
    """Create a comprehensive mock for query_expansion module."""
    query_expansion_mock = MagicMock()

    # Create ExpansionStrategy enum
    ExpansionStrategy = Mock()
    ExpansionStrategy.SYNONYM = "synonym"
    ExpansionStrategy.HYPERNYM = "hypernym"
    ExpansionStrategy.SEMANTIC = "semantic"
    query_expansion_mock.ExpansionStrategy = ExpansionStrategy

    class MockQueryExpansionEngine:
        def __init__(self, **kwargs):
            self.expansion_enabled = True

        async def expand_query(self, query_text, **kwargs):
            # Return expanded query with some synonyms
            expanded_terms = []
            if "block" in query_text.lower():
                expanded_terms.append("cube")
                expanded_terms.append("brick")
            if "create" in query_text.lower():
                expanded_terms.append("make")
                expanded_terms.append("build")

            if expanded_terms:
                return f"{query_text} {' '.join(expanded_terms)}"
            return query_text

    query_expansion_mock.QueryExpansionEngine = MockQueryExpansionEngine

    return query_expansion_mock

# Mock utils.multimodal_embedding_generator
def mock_multimodal_embedding_generator():
    """Create a comprehensive mock for multimodal_embedding_generator module."""
    embedding_mock = MagicMock()

    # Create EmbeddingStrategy enum
    EmbeddingStrategy = Mock()
    EmbeddingStrategy.OPENAI = "openai"
    EmbeddingStrategy.SENTENCE_TRANSFORMER = "sentence_transformer"
    EmbeddingStrategy.MULTIMODAL = "multimodal"
    embedding_mock.EmbeddingStrategy = EmbeddingStrategy

    class MockMultiModalEmbeddingGenerator:
        def __init__(self, strategy="sentence_transformer", **kwargs):
            self.strategy = strategy

        async def generate_embedding(self, content, content_type="text", **kwargs):
            # Return a fixed mock embedding
            return [0.1, 0.2, 0.3, 0.4, 0.5]

    embedding_mock.MultiModalEmbeddingGenerator = MockMultiModalEmbeddingGenerator

    return embedding_mock

# Mock utils.advanced_chunker
def mock_advanced_chunker():
    """Create a comprehensive mock for advanced_chunker module."""
    chunker_mock = MagicMock()

    class MockAdvancedChunker:
        def __init__(self, **kwargs):
            self.chunk_size = 1000
            self.chunk_overlap = 200

        async def chunk_document(self, document, **kwargs):
            # Return fixed mock chunks
            return [
                {
                    "content": f"Chunk {i} of document {document.id if hasattr(document, 'id') else 'unknown'}",
                    "metadata": {"chunk_id": i, "source": document.id if hasattr(document, 'id') else 'unknown'}
                }
                for i in range(3)  # Return 3 chunks
            ]

    chunker_mock.AdvancedChunker = MockAdvancedChunker

    return chunker_mock

# Mock utils.vector_db_client
def mock_vector_db_client():
    """Create a comprehensive mock for vector_db_client module."""
    vector_db_mock = MagicMock()

    class MockVectorDBClient:
        def __init__(self, **kwargs):
            self.client_type = "chromadb"

        async def add_document(self, document, embedding=None, **kwargs):
            return f"doc_id_{datetime.now().timestamp()}"

        async def query_documents(self, query_embedding, content_types=None, limit=10, **kwargs):
            # Return mock results
            return [
                {
                    "id": f"result_{i}",
                    "content": f"Result {i} content",
                    "metadata": {"type": "documentation"},
                    "score": 0.9 - (i * 0.1)
                }
                for i in range(min(limit, 5))  # Return at most 5 results
            ]

        async def delete_document(self, document_id, **kwargs):
            return True

        async def update_document(self, document_id, document, **kwargs):
            return True

    vector_db_mock.VectorDBClient = MockVectorDBClient

    return vector_db_mock

# Apply all RAG component mocks
def apply_rag_mocks():
    """Apply all RAG component mocks to sys.modules."""
    # Apply all mocks
    sys.modules['schemas.multimodal_schema'] = mock_multimodal_schema()
    sys.modules['search.hybrid_search_engine'] = mock_hybrid_search_engine()
    sys.modules['search.reranking_engine'] = mock_reranking_engine()
    sys.modules['search.query_expansion'] = mock_query_expansion()
    sys.modules['utils.multimodal_embedding_generator'] = mock_multimodal_embedding_generator()
    sys.modules['utils.advanced_chunker'] = mock_advanced_chunker()
    sys.modules['utils.vector_db_client'] = mock_vector_db_client()

    # Also need to mock the parent modules
    sys.modules['search'] = MagicMock()
    sys.modules['utils'] = MagicMock()
    sys.modules['schemas'] = MagicMock()
