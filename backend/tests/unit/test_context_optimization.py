"""
Unit tests for context window optimization components.

Tests:
- QueryComplexityAnalyzer: Classification of queries into SIMPLE/STANDARD/COMPLEX
- DynamicContextSizer: Context window sizing based on complexity
- ContextManager: Multi-turn conversation management
- ChunkPrioritizer: Relevance-based chunk ranking
"""

import sys
import os

# Add ai-engine to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "ai-engine"))

import pytest
from search.query_complexity_analyzer import (
    QueryComplexityAnalyzer,
    ComplexityLevel,
    analyze_query_complexity,
)
from search.context_manager import (
    DynamicContextSizer,
    ContextManager,
    ContextConfig,
    ContextStrategy,
)
from indexing.chunk_prioritizer import ChunkPrioritizer, RelevanceScore
from indexing.chunking_strategies import Chunk


class TestQueryComplexityAnalyzer:
    """Tests for QueryComplexityAnalyzer."""

    def test_simple_query_single_word(self):
        """Single word queries should be classified as SIMPLE."""
        analyzer = QueryComplexityAnalyzer()
        level, confidence = analyzer.analyze("item")
        assert level == ComplexityLevel.SIMPLE
        assert 0.7 <= confidence <= 1.0

    def test_standard_query_multiple_words(self):
        """Multiple word queries with basic technical terms should be STANDARD."""
        analyzer = QueryComplexityAnalyzer()
        level, confidence = analyzer.analyze("how to create custom block")
        assert level == ComplexityLevel.STANDARD
        assert 0.7 <= confidence <= 1.0

    def test_complex_query_long_with_terms(self):
        """Long queries with technical terms should be COMPLEX."""
        analyzer = QueryComplexityAnalyzer()
        level, confidence = analyzer.analyze(
            "convert entity with AI behavior from java to bedrock edition"
        )
        assert level == ComplexityLevel.COMPLEX
        assert 0.7 <= confidence <= 1.0

    def test_convenience_function(self):
        """Test convenience function for quick analysis."""
        level, confidence = analyze_query_complexity("block definition")
        assert isinstance(level, ComplexityLevel)
        assert isinstance(confidence, float)


class TestDynamicContextSizer:
    """Tests for DynamicContextSizer."""

    def test_simple_config(self):
        """SIMPLE queries should get smaller context window."""
        sizer = DynamicContextSizer()
        config = sizer.get_config(ComplexityLevel.SIMPLE)

        assert config.max_chunks == 5
        assert config.max_tokens == 1000
        assert config.min_chunks == 2

    def test_standard_config(self):
        """STANDARD queries should get medium context window."""
        sizer = DynamicContextSizer()
        config = sizer.get_config(ComplexityLevel.STANDARD)

        assert config.max_chunks == 10
        assert config.max_tokens == 2000
        assert config.min_chunks == 3

    def test_complex_config(self):
        """COMPLEX queries should get larger context window."""
        sizer = DynamicContextSizer()
        config = sizer.get_config(ComplexityLevel.COMPLEX)

        assert config.max_chunks == 20
        assert config.max_tokens == 4000
        assert config.min_chunks == 5

    def test_custom_configs(self):
        """Test custom configuration override."""
        custom = {ComplexityLevel.SIMPLE: ContextConfig(500, 25, 1, 3)}
        sizer = DynamicContextSizer(custom_configs=custom)

        config = sizer.get_config(ComplexityLevel.SIMPLE)
        assert config.max_tokens == 500
        assert config.max_chunks == 3


class TestContextManager:
    """Tests for ContextManager."""

    def test_add_turn(self):
        """Test adding conversation turns."""
        cm = ContextManager(max_turns=5)
        cm.add_turn("What is a block?", "A block is a cube.", ComplexityLevel.SIMPLE)

        assert len(cm) == 1
        turns = cm.get_context_window()
        assert len(turns) == 1
        assert turns[0].user_query == "What is a block?"

    def test_max_turns_limit(self):
        """Test that max turns limit is respected."""
        cm = ContextManager(max_turns=3)

        for i in range(5):
            cm.add_turn(f"Query {i}", f"Response {i}", ComplexityLevel.SIMPLE)

        assert len(cm) == 3

    def test_token_budget(self):
        """Test that token budget is respected."""
        cm = ContextManager(token_budget=200)

        cm.add_turn("A" * 500, "B" * 500)  # ~250 tokens each
        assert len(cm) == 1  # First turn fits

        cm.add_turn("C" * 500, "D" * 500)  # Another ~250 tokens
        assert len(cm) <= 2  # Should trim

    def test_get_context_text(self):
        """Test context text formatting."""
        cm = ContextManager()
        cm.add_turn("What is x?", "x is a variable.")

        text = cm.get_context_text()
        assert "What is x?" in text
        assert "x is a variable." in text

    def test_clear(self):
        """Test clearing conversation history."""
        cm = ContextManager()
        cm.add_turn("Query", "Response")

        cm.clear()
        assert len(cm) == 0


class TestChunkPrioritizer:
    """Tests for ChunkPrioritizer."""

    def test_prioritize_returns_sorted_results(self):
        """Test that prioritize returns chunks sorted by relevance."""
        chunks = [
            Chunk(content="First chunk about blocks", index=0, total_chunks=3),
            Chunk(content="Second chunk about items", index=1, total_chunks=3),
            Chunk(content="Third chunk about entities", index=2, total_chunks=3),
        ]

        prioritizer = ChunkPrioritizer()
        results = prioritizer.prioritize("block definition", chunks)

        # First chunk should have highest relevance for "block"
        assert results[0][0].index == 0
        assert results[0][1].score >= results[1][1].score

    def test_relevance_scores_have_reasons(self):
        """Test that relevance scores include explanations."""
        chunks = [
            Chunk(content="Block is a cube", index=0, total_chunks=1),
        ]

        prioritizer = ChunkPrioritizer()
        results = prioritizer.prioritize("block", chunks)

        score = results[0][1]
        assert isinstance(score, RelevanceScore)
        assert len(score.reasons) > 0

    def test_keyword_matching(self):
        """Test that keyword matching is applied."""
        chunks = [
            Chunk(content="Minecraft block definition", index=0, total_chunks=2),
            Chunk(content="Item recipe crafting", index=1, total_chunks=2),
        ]

        prioritizer = ChunkPrioritizer()
        results = prioritizer.prioritize("block", chunks)

        # First chunk should rank higher for "block" query
        assert results[0][0].index == 0

    def test_heading_context_boost(self):
        """Test that heading context boosts relevance."""
        chunks = [
            Chunk(content="Content here", index=0, total_chunks=1, original_heading="Block"),
            Chunk(content="Content here", index=1, total_chunks=1),
        ]

        prioritizer = ChunkPrioritizer()
        results = prioritizer.prioritize("block", chunks)

        # Chunk with heading should rank higher
        assert results[0][0].original_heading == "Block"

    def test_get_top_chunks(self):
        """Test getting top K chunks."""
        chunks = [Chunk(content=f"Chunk {i}", index=i, total_chunks=10) for i in range(10)]

        prioritizer = ChunkPrioritizer()
        top = prioritizer.get_top_chunks("test", chunks, top_k=3)

        assert len(top) == 3


class TestIntegration:
    """Integration tests for the complete context optimization pipeline."""

    def test_query_to_context_pipeline(self):
        """Test complete pipeline: query -> complexity -> context size."""
        # 1. Analyze query complexity
        analyzer = QueryComplexityAnalyzer()
        level, _ = analyzer.analyze("how to create custom block with properties")

        # 2. Get context config based on complexity
        sizer = DynamicContextSizer()
        config = sizer.get_config(level)

        # 3. Select chunks based on config
        chunks = [Chunk(content=f"Chunk {i}", index=i, total_chunks=20) for i in range(20)]
        selected = sizer.calculate_chunks(chunks, config)

        # Verify limits
        assert len(selected) <= config.max_chunks
        assert len(selected) >= config.min_chunks

    def test_full_rag_pipeline(self):
        """Test full RAG context optimization pipeline."""
        # Query complexity analysis
        analyzer = QueryComplexityAnalyzer()
        query = "convert entity AI behavior from java to bedrock"
        level, _ = analyzer.analyze(query)

        # Dynamic context sizing
        sizer = DynamicContextSizer()
        config = sizer.get_config(level)

        # Create sample chunks
        chunks = [
            Chunk(
                content=f"Content about {topic}", index=i, total_chunks=10, heading_context=[topic]
            )
            for i, topic in enumerate(["block", "item", "entity", "recipe", "biome"])
        ]

        # Chunk prioritization
        prioritizer = ChunkPrioritizer()
        prioritized = prioritizer.prioritize(query, chunks)

        # Verify prioritization worked
        assert len(prioritized) == len(chunks)
        assert all(isinstance(p[1], RelevanceScore) for p in prioritized)

        # Context manager for multi-turn
        cm = ContextManager()
        cm.add_turn(query, "Converted response", level)

        assert len(cm) == 1
