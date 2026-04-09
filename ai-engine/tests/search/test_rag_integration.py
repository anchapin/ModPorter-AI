"""
Integration tests for RAG Pipeline.

These tests verify end-to-end pipeline functionality including
caching, performance, and edge cases.
"""

import pytest
import time
from unittest.mock import Mock, patch

from search.rag_pipeline import (
    RAGPipeline,
    PipelineConfig,
    PipelineResult,
    QueryAnalysis,
)


from search.pipeline_cache import (
    PipelineCache,
    MemoryCache,
    CachedResult,
)

from search.query_rewriter import (
    QueryRewriter,
    RewriteType,
)

from search.adaptive_fusion import (
    AdaptiveFusion,
    QueryType,
    ComplexityLevel,
)


@pytest.fixture
def mock_document():
    """Create a mock document."""
    doc = Mock()
    doc.id = "doc_1"
    doc.content_text = "Minecraft block tutorial content"
    doc.source_path = "/tutorials/block.java"
    doc.content_type = "documentation"
    return doc


@pytest.fixture
def mock_search_result(mock_document):
    """Create a mock search result."""
    result = Mock()
    result.document = mock_document
    result.similarity_score = 0.85
    result.keyword_score = 0.75
    result.final_score = 0.80
    result.rank = 1
    result.matched_content = "Test content"
    return result


@pytest.fixture
def mock_search_results(mock_search_result):
    """Create multiple mock search results."""
    results = []
    for i in range(10):
        doc = Mock()
        doc.id = f"doc_{i}"
        doc.content_text = f"Content about Minecraft {i}"
        doc.source_path = f"/test/file{i}.java"
        doc.content_type = "code"

        result = Mock()
        result.document = doc
        result.similarity_score = 0.9 - (i * 0.05)
        result.keyword_score = 0.8 - (i * 0.05)
        result.final_score = 0.85 - (i * 0.05)
        result.rank = i + 1
        result.matched_content = f"Content {i}"

        results.append(result)

    return results


class TestPipelineCache:
    """Tests for PipelineCache."""

    def test_memory_cache_initialization(self):
        """Test memory cache initialization."""
        cache = PipelineCache(backend="memory", ttl=3600)

        assert cache.ttl == 3600

    def test_cache_set_and_get(self):
        """Test basic cache set and get."""
        cache = MemoryCache(ttl=3600)

        result = PipelineResult(
            results=[],
            query_analysis=QueryAnalysis(
                original_query="test", query_type="simple", complexity="simple"
            ),
        )

        cached = CachedResult(
            results=result.results, query_analysis=result.query_analysis, ttl=3600
        )

        cache.set("test_key", cached)
        retrieved = cache.get("test_key")

        assert retrieved is not None

    def test_cache_miss(self):
        """Test cache miss."""
        cache = MemoryCache(ttl=3600)

        result = cache.get("nonexistent_key")

        assert result is None

    def test_cache_invalidation(self):
        """Test cache invalidation."""
        cache = MemoryCache(ttl=3600)

        cached = CachedResult(
            results=[], query_analysis=QueryAnalysis(original_query="test"), ttl=3600
        )

        cache.set("key1", cached)
        cache.set("key2", cached)

        cache.invalidate()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = MemoryCache(ttl=3600)

        cached = CachedResult(
            results=[], query_analysis=QueryAnalysis(original_query="test"), ttl=3600
        )

        cache.set("key1", cached)
        cache.get("key1")
        cache.get("nonexistent")

        stats = cache.get_stats()

        assert "hits" in stats
        assert "misses" in stats
        assert stats["hits"] == 1
        assert stats["misses"] == 1

    def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = MemoryCache(max_size=3, ttl=3600)

        for i in range(5):
            cached = CachedResult(
                results=[], query_analysis=QueryAnalysis(original_query=f"query_{i}"), ttl=3600
            )
            cache.set(f"key_{i}", cached)

        assert cache.get("key_0") is None
        assert cache.get("key_4") is not None


class TestQueryRewriter:
    """Tests for QueryRewriter."""

    def test_rewriter_disabled(self):
        """Test rewriter when disabled."""
        rewriter = QueryRewriter(enabled=False)

        result = rewriter.rewrite("test query")

        assert result.rewritten_query == "test query"
        assert result.rewrite_type == RewriteType.NONE

    def test_abbreviation_expansion(self):
        """Test abbreviation expansion."""
        rewriter = QueryRewriter(enabled=True)

        result = rewriter.rewrite("convert mc mod")

        assert "Minecraft" in result.rewritten_query

    def test_should_rewrite(self):
        """Test should_rewrite logic."""
        rewriter = QueryRewriter(enabled=True)

        assert rewriter.should_rewrite("what's a block") is True
        assert rewriter.should_rewrite("mc mod") is True
        assert rewriter.should_rewrite("simple query") is False

    def test_disabled_should_rewrite(self):
        """Test should_rewrite when disabled."""
        rewriter = QueryRewriter(enabled=False)

        assert rewriter.should_rewrite("any query") is False


class TestAdaptiveFusion:
    """Tests for AdaptiveFusion."""

    def test_fusion_initialization(self):
        """Test fusion initialization."""
        fusion = AdaptiveFusion()

        assert fusion.default_strategy is not None

    def test_select_strategy_by_query_type(self):
        """Test strategy selection by query type."""
        fusion = AdaptiveFusion()

        strategy = fusion.select_strategy(
            query_type=QueryType.NAVIGATIONAL, complexity=ComplexityLevel.STANDARD
        )

        assert strategy.value is not None

    def test_select_strategy_by_complexity(self):
        """Test strategy selection by complexity."""
        fusion = AdaptiveFusion()

        simple_strategy = fusion.select_strategy(complexity=ComplexityLevel.SIMPLE)
        complex_strategy = fusion.select_strategy(complexity=ComplexityLevel.COMPLEX)

        assert simple_strategy is not None
        assert complex_strategy is not None

    def test_fusion_with_empty_results(self):
        """Test fusion with empty results."""
        fusion = AdaptiveFusion()

        results = fusion.fuse({})

        assert results == []

    def test_fusion_with_single_source(self):
        """Test fusion with single source."""
        fusion = AdaptiveFusion()

        mock_results = []
        for i in range(5):
            doc = Mock()
            doc.id = f"doc_{i}"

            result = Mock()
            result.document = doc
            result.final_score = 0.9 - (i * 0.1)
            result.similarity_score = 0.8
            result.keyword_score = 0.7

            mock_results.append(result)

        results = fusion.fuse({"semantic": mock_results})

        assert len(results) > 0

    def test_get_stats(self):
        """Test getting fusion stats."""
        fusion = AdaptiveFusion()

        stats = fusion.get_stats()

        assert "default_strategy" in stats
        assert "query_type_weights" in stats


@pytest.mark.integration
class TestRAGPipelineIntegration:
    """Integration tests for RAG Pipeline."""

    def test_pipeline_with_cache_disabled(self):
        """Test pipeline with caching disabled."""
        config = PipelineConfig(
            cache_enabled=False, enable_query_expansion=True, enable_reranking=True
        )

        pipeline = RAGPipeline(config)

        assert pipeline.cache is None

    @patch("search.rag_pipeline.SearchStage")
    def test_pipeline_search_performance(self, mock_stage, mock_search_results):
        """Test pipeline search performance."""
        config = PipelineConfig(cache_enabled=False, enable_reranking=False, reranking_stages=[])
        pipeline = RAGPipeline(config)

        start = time.time()
        pipeline.search("test query")
        elapsed = (time.time() - start) * 1000

        assert elapsed < 1000

    def test_pipeline_cache_key_different_queries(self):
        """Test cache keys are different for different queries."""
        config = PipelineConfig(cache_enabled=False)
        pipeline = RAGPipeline(config)

        key1 = pipeline._generate_cache_key("query 1", 10)
        key2 = pipeline._generate_cache_key("query 2", 10)

        assert key1 != key2

    def test_pipeline_cache_key_different_topk(self):
        """Test cache keys are different for different top_k."""
        config = PipelineConfig(cache_enabled=False)
        pipeline = RAGPipeline(config)

        key1 = pipeline._generate_cache_key("same query", 10)
        key2 = pipeline._generate_cache_key("same query", 20)

        assert key1 != key2


@pytest.mark.performance
class TestPipelinePerformance:
    """Performance tests for RAG Pipeline."""

    def test_simple_query_timing(self):
        """Test simple query meets timing target."""
        config = PipelineConfig(
            cache_enabled=False, enable_query_expansion=False, enable_reranking=False
        )

        pipeline = RAGPipeline(config)

        start = time.time()
        pipeline.search("block")
        elapsed = (time.time() - start) * 1000

        assert elapsed < 100, f"Simple query took {elapsed}ms, expected <100ms"

    def test_cache_hit_performance(self):
        """Test cache hit performance."""
        config = PipelineConfig(
            cache_enabled=True, enable_query_expansion=True, enable_reranking=False
        )

        pipeline = RAGPipeline(config)

        pipeline.search("test query")

        start = time.time()
        pipeline.search("test query")
        elapsed = (time.time() - start) * 1000

        assert elapsed < 50, f"Cache hit took {elapsed}ms, expected <50ms"


class TestEdgeCases:
    """Edge case tests."""

    def test_empty_query(self):
        """Test handling of empty query."""
        config = PipelineConfig(cache_enabled=False)
        pipeline = RAGPipeline(config)

        result = pipeline.search("")

        assert isinstance(result, PipelineResult)

    def test_very_long_query(self):
        """Test handling of very long query."""
        config = PipelineConfig(cache_enabled=False)
        pipeline = RAGPipeline(config)

        long_query = " ".join(["word"] * 100)
        result = pipeline.search(long_query)

        assert isinstance(result, PipelineResult)

    def test_special_characters_query(self):
        """Test handling of special characters in query."""
        config = PipelineConfig(cache_enabled=False)
        pipeline = RAGPipeline(config)

        result = pipeline.search("test <script>alert(1)</script>")

        assert isinstance(result, PipelineResult)

    def test_clear_cache(self):
        """Test clearing the cache."""
        config = PipelineConfig(cache_enabled=True)
        pipeline = RAGPipeline(config)

        pipeline.search("test query")
        pipeline.clear_cache()

        assert pipeline.cache is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
