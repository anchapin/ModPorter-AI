"""
Unit tests for Token Optimizer module.

Tests ContextTrimmer, PromptCache, and token estimation functionality.
"""

import pytest
import time
from datetime import datetime, timedelta
from utils.token_optimizer import (
    ContextTrimmer,
    PromptCache,
    TokenUsage,
    MODEL_TOKEN_LIMITS,
    TOKEN_PRICING,
    CachedPrompt,
)


class TestContextTrimmer:
    """Tests for the ContextTrimmer class."""

    @pytest.fixture
    def trimmer(self):
        """Create a ContextTrimmer for testing."""
        return ContextTrimmer(model="default")

    @pytest.fixture
    def gpt4_trimmer(self):
        """Create a ContextTrimmer with GPT-4 model."""
        return ContextTrimmer(model="gpt-4")

    def test_initialization_default(self):
        """Test default initialization."""
        trimmer = ContextTrimmer()
        assert trimmer.model == "default"
        assert trimmer.max_tokens == MODEL_TOKEN_LIMITS["default"]

    def test_initialization_custom_model(self):
        """Test initialization with custom model."""
        trimmer = ContextTrimmer(model="gpt-4-turbo")
        assert trimmer.model == "gpt-4-turbo"
        assert trimmer.max_tokens == MODEL_TOKEN_LIMITS["gpt-4-turbo"]

    def test_initialization_unknown_model(self):
        """Test initialization with unknown model falls back to default."""
        trimmer = ContextTrimmer(model="unknown-model")
        assert trimmer.model == "unknown-model"
        assert trimmer.max_tokens == MODEL_TOKEN_LIMITS["default"]

    def test_estimate_tokens_empty_string(self, trimmer):
        """Test token estimation with empty string."""
        tokens = trimmer.estimate_tokens("")
        assert tokens == 0

    def test_estimate_tokens_short_text(self, trimmer):
        """Test token estimation with short text."""
        text = "Hello world"
        tokens = trimmer.estimate_tokens(text)
        # 4 chars ≈ 1 token, "Hello world" = 11 chars, should be ~3 tokens
        assert tokens >= 2
        assert tokens <= 4

    def test_estimate_tokens_longer_text(self, trimmer):
        """Test token estimation with longer text."""
        text = "word " * 100  # 500 chars, ~125 tokens
        tokens = trimmer.estimate_tokens(text)
        assert 100 <= tokens <= 150

    def test_estimate_tokens_very_long_text(self, trimmer):
        """Test token estimation with very long text."""
        # Create ~12500 character text (25 chars * 500)
        text = "Lorem ipsum dolor sit amet. " * 500
        tokens = trimmer.estimate_tokens(text)
        # Should be approximately 3125 tokens (12500/4), allow range 2500-4000
        assert 2500 <= tokens <= 4000

    def test_model_token_limits_gpt4(self, gpt4_trimmer):
        """Test GPT-4 model has correct token limit."""
        assert gpt4_trimmer.max_tokens == MODEL_TOKEN_LIMITS["gpt-4"]
        assert gpt4_trimmer.max_tokens == 8192

    def test_model_token_limits_claude(self):
        """Test Claude models have correct token limits."""
        claude_trimmer = ContextTrimmer(model="claude-3-opus")
        assert claude_trimmer.max_tokens == 200000


class TestPromptCache:
    """Tests for the PromptCache class."""

    @pytest.fixture
    def cache(self):
        """Create a PromptCache for testing."""
        return PromptCache(max_size=3, ttl_hours=1)

    def test_initialization(self):
        """Test PromptCache initialization."""
        cache = PromptCache(max_size=10, ttl_hours=2)
        assert cache._max_size == 10
        assert cache._ttl == timedelta(hours=2)
        assert len(cache._cache) == 0
        assert cache._hits == 0
        assert cache._misses == 0

    def test_put_and_get(self, cache):
        """Test putting and getting items from cache."""
        content = "test prompt content"
        tokens = 100

        cache.put(content, tokens)
        cached = cache.get(content)

        assert cached is not None
        assert cached.content == content
        assert cached.tokens == tokens
        # hit_count starts at 1, then increments on get() = 2
        assert cached.hit_count == 2

    def test_cache_miss(self, cache):
        """Test cache miss returns None."""
        cached = cache.get("nonexistent content")
        assert cached is None

    def test_cache_hit_increments_counter(self, cache):
        """Test that cache hits increment the hit counter."""
        content = "test prompt"
        cache.put(content, 50)

        cache.get(content)  # hit_count = 1+1 = 2
        cache.get(content)  # hit_count = 2+1 = 3
        cache.get(content)  # hit_count = 3+1 = 4

        cached = cache.get(content)  # hit_count = 4+1 = 5, returns cached

        # hit_count starts at 1, increments on each get() - 4 get calls = 5
        assert cached.hit_count == 5
        assert cache._hits == 4

    def test_cache_miss_increments_miss_counter(self, cache):
        """Test that cache misses increment the miss counter."""
        cache.get("missing1")
        cache.get("missing2")

        assert cache._misses == 2

    def test_cache_eviction_lru(self, cache):
        """Test that cache evicts oldest item when full."""
        cache.put("content1", 10)
        cache.put("content2", 20)
        cache.put("content3", 30)

        # Cache is full now (max_size=3)
        # Access content1 to make it recently used
        cache.get("content1")

        # Add new item, should evict content2 (least recently used)
        cache.put("content4", 40)

        assert cache.get("content1") is not None  # Was accessed
        assert cache.get("content2") is None      # Was evicted
        assert cache.get("content3") is not None  # Still in cache
        assert cache.get("content4") is not None  # Just added

    def test_cache_expiry(self):
        """Test that cache items expire after TTL."""
        cache = PromptCache(max_size=10, ttl_hours=0)  # 0 hours TTL

        cache.put("expiring content", 50)

        # Item should be expired immediately
        cached = cache.get("expiring content")
        assert cached is None

    def test_get_stats(self, cache):
        """Test cache statistics."""
        cache.put("content1", 10)
        cache.get("content1")  # hit
        cache.get("content2")  # miss
        cache.get("content3")  # miss

        stats = cache.get_stats()

        assert stats["size"] == 1
        assert stats["max_size"] == 3
        assert stats["hits"] == 1
        assert stats["misses"] == 2
        assert stats["total_requests"] == 3
        assert stats["hit_rate_percent"] == pytest.approx(33.33, rel=0.1)

    def test_clear(self, cache):
        """Test clearing the cache."""
        cache.put("content1", 10)
        cache.put("content2", 20)
        cache.get("content1")

        cache.clear()

        assert len(cache._cache) == 0
        assert cache._hits == 0
        assert cache._misses == 0


class TestTokenUsage:
    """Tests for the TokenUsage dataclass."""

    def test_initialization(self):
        """Test TokenUsage initialization."""
        usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost=0.003,
            model="gpt-4"
        )

        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150
        assert usage.cost == 0.003
        assert usage.model == "gpt-4"

    def test_to_dict(self):
        """Test TokenUsage serialization."""
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50)
        result = usage.to_dict()

        assert isinstance(result, dict)
        assert result["prompt_tokens"] == 100
        assert result["completion_tokens"] == 50
        assert "timestamp" in result


class TestModelTokenLimits:
    """Tests for MODEL_TOKEN_LIMITS constant."""

    def test_known_models_have_limits(self):
        """Test that known models have token limits defined."""
        assert "gpt-4" in MODEL_TOKEN_LIMITS
        assert "gpt-4-turbo" in MODEL_TOKEN_LIMITS
        assert "gpt-3.5-turbo" in MODEL_TOKEN_LIMITS
        assert "claude-3-opus" in MODEL_TOKEN_LIMITS
        assert "default" in MODEL_TOKEN_LIMITS

    def test_gpt4_limit(self):
        """Test GPT-4 has correct limit."""
        assert MODEL_TOKEN_LIMITS["gpt-4"] == 8192

    def test_gpt4_turbo_limit(self):
        """Test GPT-4 Turbo has correct limit."""
        assert MODEL_TOKEN_LIMITS["gpt-4-turbo"] == 128000

    def test_claude_opus_limit(self):
        """Test Claude 3 Opus has correct limit."""
        assert MODEL_TOKEN_LIMITS["claude-3-opus"] == 200000


class TestTokenPricing:
    """Tests for TOKEN_PRICING constant."""

    def test_known_models_have_pricing(self):
        """Test that known models have pricing defined."""
        assert "gpt-4" in TOKEN_PRICING
        assert "gpt-3.5-turbo" in TOKEN_PRICING
        assert "default" in TOKEN_PRICING

    def test_pricing_structure(self):
        """Test that pricing has prompt and completion prices."""
        pricing = TOKEN_PRICING["gpt-4"]
        assert "prompt" in pricing
        assert "completion" in pricing

    def test_gpt35_cheaper_than_gpt4(self):
        """Test that GPT-3.5 is cheaper than GPT-4."""
        gpt35_pricing = TOKEN_PRICING["gpt-3.5-turbo"]
        gpt4_pricing = TOKEN_PRICING["gpt-4"]

        assert gpt35_pricing["prompt"] < gpt4_pricing["prompt"]
        assert gpt35_pricing["completion"] < gpt4_pricing["completion"]