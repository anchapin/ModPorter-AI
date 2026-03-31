"""
Unit tests for Bedrock pattern registry.
"""

import pytest
from knowledge.patterns.bedrock_patterns import BedrockPatternRegistry

class TestBedrockPatternRegistry:
    @pytest.fixture
    def registry(self):
        return BedrockPatternRegistry()

    def test_registry_initialization(self, registry):
        """Test that registry is pre-populated with patterns."""
        assert len(registry.patterns) >= 20
        assert "bedrock_simple_item" in registry.patterns
        assert "bedrock_simple_block" in registry.patterns
        assert "bedrock_simple_entity" in registry.patterns

    def test_get_pattern(self, registry):
        p = registry.get_pattern("bedrock_simple_item")
        assert p is not None
        assert p.name == "Simple Item Definition"
        
        assert registry.get_pattern("non_existent") is None

    def test_get_all_patterns(self, registry):
        all_p = registry.get_all_patterns()
        assert len(all_p) == len(registry.patterns)
        assert isinstance(all_p, list)

    def test_get_by_category(self, registry):
        items = registry.get_by_category("item")
        assert len(items) >= 4
        assert all(p.category == "item" for p in items)

    def test_get_stats(self, registry):
        stats = registry.get_stats()
        assert stats["total"] == len(registry.patterns)
        assert "by_category" in stats
        assert stats["by_category"]["item"] >= 4
