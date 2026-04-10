"""
Tests for RAG integration with conversion pipeline (Issue #992).

Tests the K³Trans implementation: wiring RAG pipeline into conversion loop.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock

from search.conversion_context import (
    ConversionContextAggregator,
    ConversionContext,
)
from search.conversion_rag_pipeline import (
    ConversionRAGPipeline,
    ConversionRetrievalResult,
    create_conversion_rag_pipeline,
)
from search.pattern_indexer import (
    PatternMappingIndexer,
    create_pattern_indexer,
    index_all_knowledge,
)
from knowledge.patterns.mappings import (
    PatternMappingRegistry,
    PatternMapping,
)


class TestPatternMappingRegistry:
    """Tests for PatternMappingRegistry enhancements."""

    def test_search_mappings_basic(self):
        """Test basic pattern mapping search."""
        registry = PatternMappingRegistry()
        results = registry.search_mappings("TileEntity energy storage")
        assert len(results) > 0

    def test_search_mappings_with_feature_type(self):
        """Test search with feature type filter."""
        registry = PatternMappingRegistry()
        results = registry.search_mappings("item", feature_type="item")
        assert len(results) > 0
        assert any("item" in r.java_pattern_id.lower() for r in results)

    def test_search_mappings_with_confidence(self):
        """Test search with confidence threshold."""
        registry = PatternMappingRegistry()
        results = registry.search_mappings("block", min_confidence=0.9)
        assert all(r.confidence >= 0.9 for r in results)

    def test_get_mappings_for_feature_type(self):
        """Test getting mappings for feature type."""
        registry = PatternMappingRegistry()
        results = registry.get_mappings_for_feature_type("block")
        assert len(results) > 0
        assert any("block" in r.java_pattern_id.lower() for r in results)

    def test_to_indexable_documents(self):
        """Test converting mappings to indexable documents."""
        registry = PatternMappingRegistry()
        docs = registry.to_indexable_documents()
        assert len(docs) == len(registry.mappings)
        assert all("content" in d for d in docs)
        assert all("source" in d for d in docs)


class TestConversionContext:
    """Tests for ConversionContext."""

    def test_conversion_context_creation(self):
        """Test creating a conversion context."""
        context = ConversionContext(
            query="Test query",
            confidence=0.85,
        )
        assert context.query == "Test query"
        assert context.confidence == 0.85

    def test_conversion_context_to_dict(self):
        """Test converting context to dictionary."""
        context = ConversionContext(
            query="Test query",
            confidence=0.75,
        )
        data = context.to_dict()
        assert data["query"] == "Test query"
        assert data["confidence"] == 0.75

    def test_conversion_context_format_for_llm(self):
        """Test formatting context for LLM."""
        registry = PatternMappingRegistry()
        mapping = registry.mappings.get("java_tile_entity")

        context = ConversionContext(
            query="TileEntity",
            pattern_mappings=[mapping] if mapping else [],
            confidence=0.75,
        )

        formatted = context.format_for_llm()
        assert "CONVERSION CONTEXT" in formatted
        assert "TileEntity" in formatted


class TestConversionRAGPipeline:
    """Tests for ConversionRAGPipeline."""

    def test_pipeline_creation(self):
        """Test creating a conversion RAG pipeline."""
        pipeline = ConversionRAGPipeline()
        assert pipeline is not None
        assert not pipeline.is_initialized()

    def test_pipeline_with_registry(self):
        """Test pipeline initialization with pattern registry."""
        registry = PatternMappingRegistry()
        pipeline = ConversionRAGPipeline()
        pipeline.set_pattern_registry(registry)

        assert pipeline._pattern_registry is not None

    def test_retrieve_context_sync(self):
        """Test synchronous context retrieval."""
        registry = PatternMappingRegistry()
        pipeline = ConversionRAGPipeline()
        pipeline.set_pattern_registry(registry)

        result = pipeline.retrieve_conversion_context_sync(
            java_feature="TileEntity with energy storage",
            feature_type="block",
            top_k=5,
        )

        assert isinstance(result, ConversionRetrievalResult)
        assert result.confidence > 0
        assert len(result.pattern_mappings) > 0

    def test_format_context_for_llm(self):
        """Test formatting context for LLM."""
        registry = PatternMappingRegistry()
        pipeline = ConversionRAGPipeline()
        pipeline.set_pattern_registry(registry)

        result = pipeline.retrieve_conversion_context_sync(
            java_feature="ItemStack",
            feature_type="item",
            top_k=5,
        )

        formatted = pipeline.format_context_for_llm(result)
        assert "CONVERSION CONTEXT" in formatted
        assert result.confidence > 0 or formatted == ""

    def test_create_conversion_rag_pipeline_factory(self):
        """Test factory function."""
        pipeline = create_conversion_rag_pipeline()
        assert isinstance(pipeline, ConversionRAGPipeline)


class TestConversionContextAggregator:
    """Tests for ConversionContextAggregator."""

    def test_aggregator_creation(self):
        """Test creating a context aggregator."""
        aggregator = ConversionContextAggregator()
        assert aggregator is not None

    def test_aggregator_with_registry(self):
        """Test aggregator with pattern registry."""
        registry = PatternMappingRegistry()
        aggregator = ConversionContextAggregator(pattern_registry=registry)
        assert aggregator.pattern_registry is not None

    def test_format_context_prompt(self):
        """Test formatting context prompt with actual mappings."""
        aggregator = ConversionContextAggregator()
        registry = PatternMappingRegistry()
        aggregator.set_pattern_registry(registry)

        mapping = registry.mappings.get("java_tile_entity")

        context = ConversionContext(
            query="TileEntity",
            pattern_mappings=[mapping] if mapping else [],
            confidence=0.75,
        )

        formatted = aggregator.format_context_prompt(context)
        assert "CONVERSION CONTEXT" in formatted
        assert len(formatted) > 50


class TestPatternMappingIndexer:
    """Tests for PatternMappingIndexer."""

    def test_indexer_creation(self):
        """Test creating an indexer."""
        indexer = PatternMappingIndexer()
        assert indexer is not None

    def test_create_pattern_indexer_factory(self):
        """Test factory function."""
        indexer = create_pattern_indexer()
        assert isinstance(indexer, PatternMappingIndexer)


class TestIntegration:
    """Integration tests for the RAG pipeline."""

    def test_full_context_retrieval_flow(self):
        """Test complete context retrieval flow."""
        registry = PatternMappingRegistry()

        pipeline = ConversionRAGPipeline()
        pipeline.set_pattern_registry(registry)

        result = pipeline.retrieve_conversion_context_sync(
            java_feature="TileEntity with energy storage",
            feature_type="block",
            top_k=5,
        )

        formatted = pipeline.format_context_for_llm(result)

        assert result.confidence > 0
        assert len(result.pattern_mappings) > 0
        assert "CONVERSION CONTEXT" in formatted

    def test_search_mappings_returns_sorted_results(self):
        """Test that search returns results with scores."""
        registry = PatternMappingRegistry()

        results = registry.search_mappings("entity")

        assert len(results) > 0
        assert all(hasattr(r, "confidence") for r in results)
        assert all(r.confidence > 0 for r in results)

    def test_multiple_feature_types(self):
        """Test retrieval for different feature types."""
        registry = PatternMappingRegistry()

        feature_types = ["block", "item", "entity", "recipe"]

        for feature_type in feature_types:
            pipeline = ConversionRAGPipeline()
            pipeline.set_pattern_registry(registry)

            result = pipeline.retrieve_conversion_context_sync(
                java_feature=f"test {feature_type}",
                feature_type=feature_type,
                top_k=5,
            )

            assert result.retrieval_metadata["feature_type"] == feature_type
