"""
Unit tests for Hybrid Search Engine with BM25 support.

This module tests the hybrid search engine functionality including
keyword search, BM25 search, and vector similarity search.
"""

import pytest
import hashlib
from datetime import datetime
from typing import Dict, List

import sys
from pathlib import Path

# Add ai-engine to path
ai_engine_root = Path(__file__).parent.parent
sys.path.insert(0, str(ai_engine_root))

from search.hybrid_search_engine import (
    KeywordSearchEngine,
    HybridSearchEngine,
    SearchMode,
    RankingStrategy,
    BM25_AVAILABLE,
)
from schemas.multimodal_schema import (
    SearchQuery,
    MultiModalDocument,
    ContentType,
)


class TestKeywordSearchEngine:
    """Tests for the KeywordSearchEngine class."""

    @pytest.fixture
    def keyword_engine(self):
        """Create a KeywordSearchEngine instance for testing."""
        return KeywordSearchEngine()

    def test_initialization(self, keyword_engine):
        """Test that KeywordSearchEngine initializes correctly."""
        assert keyword_engine is not None
        assert keyword_engine.stop_words is not None
        assert len(keyword_engine.stop_words) > 0
        assert "the" in keyword_engine.stop_words
        assert "and" in keyword_engine.stop_words

    def test_extract_keywords_basic(self, keyword_engine):
        """Test basic keyword extraction."""
        text = "How to create a custom block in Minecraft"
        keywords = keyword_engine.extract_keywords(text, include_synonyms=False)

        assert isinstance(keywords, list)
        assert "how" in keywords or "create" in keywords
        # Stop words should be filtered
        assert "to" not in keywords
        assert "a" not in keywords
        assert "in" not in keywords

    def test_extract_keywords_with_synonyms(self, keyword_engine):
        """Test keyword extraction with domain synonyms."""
        text = "How to create a custom block in Minecraft"
        keywords = keyword_engine.extract_keywords(text, include_synonyms=True)

        # Should include synonyms for domain terms
        assert "block" in keywords
        # Minecraft synonyms should be added
        assert "blocks" in keywords or "cube" in keywords or "tile" in keywords

    def test_extract_keywords_empty_text(self, keyword_engine):
        """Test keyword extraction with empty text."""
        keywords = keyword_engine.extract_keywords("")
        assert keywords == []

    def test_extract_keywords_short_words(self, keyword_engine):
        """Test that very short words are filtered."""
        text = "I am a custom block"  # "I" and "am" are too short
        keywords = keyword_engine.extract_keywords(text, include_synonyms=False)

        # Short words should be filtered
        assert "i" not in keywords
        assert "am" not in keywords
        # But "custom" and "block" should be there
        assert "custom" in keywords or "block" in keywords

    def test_calculate_keyword_similarity(self, keyword_engine):
        """Test keyword similarity calculation."""
        query_keywords = ["create", "custom", "block"]
        document_text = "How to create a custom block in Minecraft"

        score, explanation = keyword_engine.calculate_keyword_similarity(
            query_keywords, document_text
        )

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert isinstance(explanation, dict)
        assert "matched_terms" in explanation

    def test_calculate_keyword_similarity_empty(self, keyword_engine):
        """Test keyword similarity with empty inputs."""
        score, explanation = keyword_engine.calculate_keyword_similarity([], "some text")
        assert score == 0.0

        score, explanation = keyword_engine.calculate_keyword_similarity(["test"], "")
        assert score == 0.0


class TestBM25Integration:
    """Tests for BM25 integration in KeywordSearchEngine."""

    @pytest.fixture
    def keyword_engine(self):
        """Create a KeywordSearchEngine instance for testing."""
        return KeywordSearchEngine()

    @pytest.fixture
    def sample_documents(self) -> Dict[str, MultiModalDocument]:
        """Create sample documents for BM25 testing."""
        docs = {}
        texts = [
            "How to create a custom block in Minecraft using Forge",
            "Creating items and recipes for Minecraft mods",
            "Entity AI behavior and pathfinding in Minecraft",
            "Texture pack creation and resource pack management",
            "Redstone circuit design and automation techniques",
        ]

        for i, text in enumerate(texts):
            doc_id = f"doc_{i}"
            docs[doc_id] = MultiModalDocument(
                id=doc_id,
                content_hash=hashlib.md5(text.encode()).hexdigest(),
                source_path=f"/test/{doc_id}.txt",
                content_type=ContentType.DOCUMENTATION,
                content_text=text,
                tags=["minecraft", "modding"],
            )
        return docs

    @pytest.mark.skipif(not BM25_AVAILABLE, reason="rank_bm25 not installed")
    def test_build_bm25_index(self, keyword_engine, sample_documents):
        """Test building BM25 index from documents."""
        result = keyword_engine.build_bm25_index(sample_documents)

        assert result is True
        assert keyword_engine._bm25_index is not None
        assert len(keyword_engine._bm25_documents) > 0

    @pytest.mark.skipif(not BM25_AVAILABLE, reason="rank_bm25 not installed")
    def test_search_bm25(self, keyword_engine, sample_documents):
        """Test BM25 search returns relevant results."""
        # Build index first
        keyword_engine.build_bm25_index(sample_documents)

        # Search for "block creation"
        results = keyword_engine.search_bm25(
            "block creation", sample_documents, top_k=3
        )

        assert isinstance(results, list)
        assert len(results) > 0
        assert len(results) <= 3
        # First result should have highest score
        if len(results) > 1:
            assert results[0][1] >= results[1][1]

    @pytest.mark.skipif(not BM25_AVAILABLE, reason="rank_bm25 not installed")
    def test_bm25_fallback(self, keyword_engine, sample_documents):
        """Test BM25 fallback when index not built."""
        # Don't build index - should fall back to basic keyword search
        results = keyword_engine.search_bm25(
            "block creation", sample_documents, top_k=3
        )

        # Should still return results via fallback
        assert isinstance(results, list)


class TestHybridSearchEngine:
    """Tests for the HybridSearchEngine class."""

    @pytest.fixture
    def hybrid_engine(self):
        """Create a HybridSearchEngine instance for testing."""
        return HybridSearchEngine()

    @pytest.fixture
    def sample_documents(self) -> Dict[str, MultiModalDocument]:
        """Create sample documents for testing."""
        docs = {}
        texts = [
            "How to create a custom block in Minecraft using Forge",
            "Creating items and recipes for Minecraft mods",
            "Entity AI behavior and pathfinding in Minecraft",
            "Texture pack creation and resource pack management",
            "Redstone circuit design and automation techniques",
        ]

        for i, text in enumerate(texts):
            doc_id = f"doc_{i}"
            docs[doc_id] = MultiModalDocument(
                id=doc_id,
                content_hash=hashlib.md5(text.encode()).hexdigest(),
                source_path=f"/test/{doc_id}.txt",
                content_type=ContentType.DOCUMENTATION,
                content_text=text,
                tags=["minecraft", "modding"],
            )
        return docs

    @pytest.fixture
    def sample_embeddings(self) -> Dict[str, List]:
        """Create sample embeddings for testing."""
        # Generate random embeddings for each document
        embeddings = {}
        for i in range(5):
            import random
            embeddings[f"doc_{i}"] = [random.random() for _ in range(384)]
        return embeddings

    def test_initialization(self, hybrid_engine):
        """Test that HybridSearchEngine initializes correctly."""
        assert hybrid_engine is not None
        assert hybrid_engine.keyword_engine is not None
        assert hybrid_engine.ranking_strategies is not None
        assert RankingStrategy.WEIGHTED_SUM in hybrid_engine.ranking_strategies
        assert RankingStrategy.RECIPROCAL_RANK_FUSION in hybrid_engine.ranking_strategies

    def test_build_index(self, hybrid_engine, sample_documents):
        """Test building search indexes."""
        result = hybrid_engine.build_index(sample_documents)

        assert result is True

    @pytest.mark.asyncio
    async def test_search_keyword_only(self, hybrid_engine, sample_documents):
        """Test search with keyword-only mode."""
        query = SearchQuery(
            query_text="custom block creation",
            top_k=3,
        )

        results = await hybrid_engine.search(
            query=query,
            documents=sample_documents,
            embeddings={},
            query_embedding=[],
            search_mode=SearchMode.KEYWORD_ONLY,
        )

        assert isinstance(results, list)
        # Should return up to top_k results
        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_search_with_filters(self, hybrid_engine, sample_documents):
        """Test search with content type filters."""
        query = SearchQuery(
            query_text="Minecraft mod",
            top_k=5,
            content_types=[ContentType.DOCUMENTATION],
        )

        results = await hybrid_engine.search(
            query=query,
            documents=sample_documents,
            embeddings={},
            query_embedding=[],
            search_mode=SearchMode.KEYWORD_ONLY,
        )

        # All results should match the content type filter
        for result in results:
            if hasattr(result, 'document'):
                assert result.document.content_type == ContentType.DOCUMENTATION

    @pytest.mark.asyncio
    async def test_search_empty_documents(self, hybrid_engine):
        """Test search with empty documents."""
        query = SearchQuery(
            query_text="test query",
            top_k=10,
        )

        results = await hybrid_engine.search(
            query=query,
            documents={},
            embeddings={},
            query_embedding=[],
            search_mode=SearchMode.KEYWORD_ONLY,
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_search_hybrid_mode(self, hybrid_engine, sample_documents, sample_embeddings):
        """Test search with hybrid mode (vector + keyword)."""
        query = SearchQuery(
            query_text="custom block",
            top_k=3,
        )

        results = await hybrid_engine.search(
            query=query,
            documents=sample_documents,
            embeddings=sample_embeddings,
            query_embedding=sample_embeddings["doc_0"],
            search_mode=SearchMode.HYBRID,
        )

        assert isinstance(results, list)
        assert len(results) <= 3


class TestSearchModes:
    """Tests for different search modes."""

    @pytest.fixture
    def hybrid_engine(self):
        """Create a HybridSearchEngine instance for testing."""
        return HybridSearchEngine()

    @pytest.fixture
    def sample_documents(self) -> Dict[str, MultiModalDocument]:
        """Create sample documents for testing."""
        docs = {}
        texts = [
            "How to create a custom block in Minecraft",
            "Creating items and recipes for Minecraft mods",
            "Entity AI behavior in Minecraft",
        ]

        for i, text in enumerate(texts):
            doc_id = f"doc_{i}"
            docs[doc_id] = MultiModalDocument(
                id=doc_id,
                content_hash=hashlib.md5(text.encode()).hexdigest(),
                source_path=f"/test/{doc_id}.txt",
                content_type=ContentType.DOCUMENTATION,
                content_text=text,
            )
        return docs

    def test_search_mode_enum(self):
        """Test SearchMode enum values."""
        assert SearchMode.VECTOR_ONLY.value == "vector_only"
        assert SearchMode.KEYWORD_ONLY.value == "keyword_only"
        assert SearchMode.HYBRID.value == "hybrid"
        assert SearchMode.ADAPTIVE.value == "adaptive"

    def test_ranking_strategy_enum(self):
        """Test RankingStrategy enum values."""
        assert RankingStrategy.WEIGHTED_SUM.value == "weighted_sum"
        assert RankingStrategy.RECIPROCAL_RANK_FUSION.value == "reciprocal_rank_fusion"
        assert RankingStrategy.BAYESIAN_COMBINATION.value == "bayesian_combination"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])