"""
Unit tests for RAG Pipeline and Multi-Stage Reranker.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass

from search.rag_pipeline import (
    RAGPipeline,
    PipelineConfig,
    PipelineResult,
    QueryAnalysis,
    QueryAnalysisStage,
    QueryExpansionStage,
    SearchStage,
    RerankingStage,
    FusionStage,
    QueryType,
    ComplexityLevel,
)

from search.multi_stage_reranker import (
    MultiStageReranker,
    RerankStageConfig,
    ReRankingStrategy,
    STANDARD,
    LIGHTWEIGHT,
    COMPREHENSIVE,
)


@pytest.fixture
def mock_search_result():
    """Create a mock search result."""
    doc = Mock()
    doc.id = "doc_1"
    doc.content_text = "Test content about Minecraft blocks"
    doc.source_path = "/test/block.java"
    doc.content_type = "code"

    result = Mock()
    result.document = doc
    result.similarity_score = 0.8
    result.keyword_score = 0.6
    result.final_score = 0.7
    result.rank = 1
    result.matched_content = "Test content"

    return result


@pytest.fixture
def mock_search_results(mock_search_result):
    """Create a list of mock search results."""
    results = []
    for i in range(5):
        doc = Mock()
        doc.id = f"doc_{i}"
        doc.content_text = f"Test content {i}"
        doc.source_path = f"/test/file{i}.java"
        doc.content_type = "code"

        result = Mock()
        result.document = doc
        result.similarity_score = 0.8 - (i * 0.1)
        result.keyword_score = 0.6 - (i * 0.1)
        result.final_score = 0.7 - (i * 0.1)
        result.rank = i + 1
        result.matched_content = f"Test content {i}"

        results.append(result)

    return results


class TestQueryAnalysisStage:
    """Tests for QueryAnalysisStage."""

    def test_simple_query(self):
        """Test analysis of simple query."""
        stage = QueryAnalysisStage()
        analysis = stage.process("how to create a block")

        assert analysis.original_query == "how to create a block"
        assert analysis.query_type == QueryType.INFORMATIONAL

    def test_navigational_query(self):
        """Test analysis of navigational query."""
        stage = QueryAnalysisStage()
        analysis = stage.process("docs page link")

        assert analysis.query_type == QueryType.NAVIGATIONAL

    def test_complexity_simple(self):
        """Test complexity detection for simple query."""
        stage = QueryAnalysisStage()
        analysis = stage.process("block")

        assert analysis.complexity == ComplexityLevel.SIMPLE

    def test_complexity_standard(self):
        """Test complexity detection for standard query."""
        stage = QueryAnalysisStage()
        analysis = stage.process("how to create block item entity")

        assert analysis.complexity in [ComplexityLevel.STANDARD, ComplexityLevel.COMPLEX]

    def test_technical_terms(self):
        """Test technical term counting."""
        stage = QueryAnalysisStage()
        count = stage._count_technical_terms("convert class method api")

        assert count >= 2


class TestQueryExpansionStage:
    """Tests for QueryExpansionStage."""

    def test_expansion_basic(self):
        """Test basic query expansion."""
        stage = QueryExpansionStage()
        analysis = QueryAnalysis(
            original_query="minecraft block",
            query_type=QueryType.SIMPLE,
            complexity=ComplexityLevel.SIMPLE,
        )

        expanded = stage.process(analysis)

        assert len(expanded.expanded_terms) > 0
        assert "block" in expanded.expanded_terms

    def test_expansion_with_synonyms(self):
        """Test expansion with synonyms."""
        stage = QueryExpansionStage()
        analysis = QueryAnalysis(
            original_query="convert mod",
            query_type=QueryType.SIMPLE,
            complexity=ComplexityLevel.SIMPLE,
        )

        expanded = stage.process(analysis)

        assert "mod" in expanded.expanded_terms


class TestPipelineConfig:
    """Tests for PipelineConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = PipelineConfig()

        assert config.enable_query_expansion is True
        assert config.enable_reranking is True
        assert config.max_results == 20
        assert config.cache_enabled is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = PipelineConfig(
            enable_query_expansion=False, reranking_stages=["feature"], max_results=10
        )

        assert config.enable_query_expansion is False
        assert config.reranking_stages == ["feature"]
        assert config.max_results == 10


class TestRAGPipeline:
    """Tests for RAGPipeline."""

    def test_pipeline_initialization(self):
        """Test pipeline initialization."""
        pipeline = RAGPipeline()

        assert pipeline.config is not None
        assert pipeline.query_analysis_stage is not None
        assert pipeline.query_expansion_stage is not None

    def test_pipeline_with_custom_config(self):
        """Test pipeline with custom config."""
        config = PipelineConfig(enable_query_expansion=False, max_results=5)
        pipeline = RAGPipeline(config)

        assert pipeline.config.max_results == 5
        assert pipeline.config.enable_query_expansion is False

    def test_pipeline_search_no_engine(self):
        """Test pipeline search without search engine."""
        config = PipelineConfig(cache_enabled=False)
        pipeline = RAGPipeline(config)

        result = pipeline.search("test query")

        assert isinstance(result, PipelineResult)
        assert isinstance(result.query_analysis, QueryAnalysis)
        assert result.results == []

    def test_cache_key_generation(self):
        """Test cache key generation."""
        config = PipelineConfig(cache_enabled=False)
        pipeline = RAGPipeline(config)

        key1 = pipeline._generate_cache_key("test query", 10)
        key2 = pipeline._generate_cache_key("test query", 10)
        key3 = pipeline._generate_cache_key("different query", 10)

        assert key1 == key2
        assert key1 != key3

    def test_get_stats(self):
        """Test pipeline stats retrieval."""
        pipeline = RAGPipeline()
        stats = pipeline.get_stats()

        assert "config" in stats
        assert stats["config"]["enable_query_expansion"] is True


class TestMultiStageReranker:
    """Tests for MultiStageReranker."""

    def test_reranker_initialization(self):
        """Test reranker initialization."""
        reranker = MultiStageReranker()

        assert reranker.stages is not None
        assert len(reranker.stages) > 0

    def test_reranker_with_standard_config(self):
        """Test reranker with standard config."""
        reranker = MultiStageReranker(STANDARD)

        assert len(reranker.stages) == 2
        assert reranker.stages[0].name == "feature"
        assert reranker.stages[1].name == "cross_encoder"

    def test_reranker_with_lightweight_config(self):
        """Test reranker with lightweight config."""
        reranker = MultiStageReranker(LIGHTWEIGHT)

        assert len(reranker.stages) == 1
        assert reranker.stages[0].strategy == ReRankingStrategy.FEATURE_BASED

    def test_reranker_with_comprehensive_config(self):
        """Test reranker with comprehensive config."""
        reranker = MultiStageReranker(COMPREHENSIVE)

        assert len(reranker.stages) == 4

    def test_rerank_empty_results(self):
        """Test reranking with empty results."""
        reranker = MultiStageReranker()

        results = reranker.rerank("test query", [])

        assert results == []

    def test_rerank_with_results(self, mock_search_results):
        """Test reranking with results."""
        reranker = MultiStageReranker(LIGHTWEIGHT)

        results = reranker.rerank("test query", mock_search_results)

        assert len(results) > 0
        assert results[0].rank == 1

    def test_stage_history(self, mock_search_results):
        """Test stage history tracking."""
        reranker = MultiStageReranker(LIGHTWEIGHT)

        reranker.rerank("test query", mock_search_results)

        history = reranker.get_stage_history()

        assert len(history) > 0
        assert history[0].stage_name == "feature"

    def test_add_stage(self):
        """Test adding a new stage."""
        reranker = MultiStageReranker(LIGHTWEIGHT)

        reranker.add_stage(
            name="new_stage",
            strategy=ReRankingStrategy.CROSS_ENCODER,
            config={"top_k": 10, "weight": 0.5},
        )

        assert len(reranker.stages) == 2
        assert reranker.stages[-1].name == "new_stage"

    def test_get_stats(self, mock_search_results):
        """Test reranker stats."""
        reranker = MultiStageReranker(LIGHTWEIGHT)

        reranker.rerank("test query", mock_search_results)
        stats = reranker.get_stats()

        assert "stages_count" in stats
        assert "total_time_ms" in stats

    def test_should_continue(self, mock_search_results):
        """Test convergence check."""
        reranker = MultiStageReranker(LIGHTWEIGHT)

        result = reranker.should_continue(mock_search_results)

        assert isinstance(result, bool)


class TestRerankStageConfig:
    """Tests for RerankStageConfig."""

    def test_stage_config_creation(self):
        """Test creating a stage config."""
        config = RerankStageConfig(
            name="test_stage", strategy=ReRankingStrategy.FEATURE_BASED, top_k=50, weight=0.8
        )

        assert config.name == "test_stage"
        assert config.strategy == ReRankingStrategy.FEATURE_BASED
        assert config.top_k == 50
        assert config.weight == 0.8

    def test_stage_config_defaults(self):
        """Test default stage config values."""
        config = RerankStageConfig(name="test", strategy=ReRankingStrategy.CROSS_ENCODER)

        assert config.top_k is None
        assert config.weight == 1.0
        assert config.model_name is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
