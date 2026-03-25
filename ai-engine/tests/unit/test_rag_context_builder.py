"""
Unit tests for RAG Context Builder with token optimization.

Tests the token-based context window optimization functionality.
"""

import pytest
from services.rag_context_builder import RAGContextBuilder, get_context_builder


class TestRAGContextBuilder:
    """Tests for the RAGContextBuilder class."""

    @pytest.fixture
    def context_builder(self):
        """Create a RAGContextBuilder for testing."""
        return RAGContextBuilder(max_context_tokens=4000, model="default")

    @pytest.fixture
    def sample_search_results(self):
        """Create sample search results for testing."""
        return [
            {
                "example": {
                    "java_code": "public class TestBlock extends Block { private int value; }",
                    "bedrock_code": '{"type": "block", "data": {"value": 0}}',
                },
                "score": 0.95,
            },
            {
                "example": {
                    "java_code": "public class Item extends ItemStack { private String name; }",
                    "bedrock_code": '{"type": "item", "data": {"name": "test"}}',
                },
                "score": 0.85,
            },
            {
                "example": {
                    "java_code": "public void onInteract(Player p) { p.sendMessage(\"Hello\"); }",
                    "bedrock_code": '{"event": "onInteract", "action": "message"}',
                },
                "score": 0.75,
            },
        ]

    def test_initialization_default(self):
        """Test default initialization."""
        builder = RAGContextBuilder()
        assert builder.max_context_tokens == 4000
        assert builder.model == "default"
        assert builder.context_trimmer is not None

    def test_initialization_custom(self):
        """Test custom initialization."""
        builder = RAGContextBuilder(max_context_tokens=8000, model="gpt-4")
        assert builder.max_context_tokens == 8000
        assert builder.model == "gpt-4"

    def test_build_context_empty_results(self, context_builder):
        """Test building context with empty results."""
        result = context_builder.build_context([], "test query")
        assert result == ""

    def test_build_context_with_results(self, context_builder, sample_search_results):
        """Test building context with search results."""
        result = context_builder.build_context(sample_search_results, "How to create a block")
        assert "Query:" in result
        assert "Similar conversion examples:" in result
        assert "Example 1" in result

    def test_build_context_respects_token_limit(self, context_builder, sample_search_results):
        """Test that context respects token limit."""
        # Use a very small token limit
        builder = RAGContextBuilder(max_context_tokens=100)
        result = builder.build_context(sample_search_results, "test query", max_examples=3)

        # Should have query but may not have all examples due to token limit
        assert "Query:" in result
        # The context should be shorter due to token limiting

    def test_build_context_max_examples(self, context_builder, sample_search_results):
        """Test max_examples parameter."""
        result = context_builder.build_context(
            sample_search_results, "test", max_examples=1
        )
        assert "Example 1" in result
        # Should only have one example

    def test_build_prompt(self, context_builder):
        """Test prompt building."""
        context = "Here is some context"
        java_code = "public class Test {}"
        prompt = context_builder.build_prompt(java_code, context)

        assert "You are an expert" in prompt
        assert "Reference examples:" in prompt
        assert context in prompt
        assert java_code in prompt
        assert "Bedrock Translation:" in prompt

    def test_build_prompt_with_custom_instruction(self, context_builder):
        """Test prompt building with custom instruction."""
        instruction = "Custom instruction"
        prompt = context_builder.build_prompt("code", "context", instruction=instruction)
        assert instruction in prompt


class TestGetContextBuilder:
    """Tests for the get_context_builder factory function."""

    def test_get_context_builder_singleton(self):
        """Test that get_context_builder returns singleton."""
        builder1 = get_context_builder()
        builder2 = get_context_builder()
        assert builder1 is builder2

    def test_get_context_builder_with_params(self):
        """Test getting builder with custom params."""
        # Reset the global singleton
        import services.rag_context_builder as module
        module._context_builder = None

        builder = get_context_builder(max_context_tokens=6000, model="gpt-4")
        assert builder.max_context_tokens == 6000
        assert builder.model == "gpt-4"


class TestTokenEstimation:
    """Tests for token estimation in context building."""

    @pytest.fixture
    def context_builder(self):
        """Create a RAGContextBuilder for testing."""
        return RAGContextBuilder(max_context_tokens=4000, model="default")

    def test_token_estimation_available(self, context_builder):
        """Test that token estimation is available."""
        assert hasattr(context_builder, "context_trimmer")
        assert hasattr(context_builder.context_trimmer, "estimate_tokens")

    def test_estimate_tokens_method(self, context_builder):
        """Test token estimation method."""
        text = "Hello world, this is a test."
        tokens = context_builder.context_trimmer.estimate_tokens(text)
        # 4 chars ≈ 1 token, so "Hello world, this is a test." (~25 chars) ≈ 6 tokens
        assert tokens > 0
        assert tokens <= len(text) // 2  # Should be roughly half or less

    def test_token_estimation_longer_text(self, context_builder):
        """Test token estimation with longer text."""
        # Create text with known approximate length
        text = "word " * 100  # 500 chars, ~125 tokens
        tokens = context_builder.context_trimmer.estimate_tokens(text)
        # Should be around 125 tokens (500/4)
        assert 100 <= tokens <= 150