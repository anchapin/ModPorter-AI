"""
Unit tests for Java pattern registry.
"""

import pytest
from knowledge.patterns.java_patterns import JavaPatternRegistry

class TestJavaPatternRegistry:
    @pytest.fixture
    def registry(self):
        return JavaPatternRegistry()

    def test_registry_initialization(self, registry):
        """Test that registry is pre-populated with patterns."""
        assert len(registry.patterns) >= 20
        assert "java_simple_item" in registry.patterns
        assert "java_simple_block" in registry.patterns
        assert "java_simple_entity" in registry.patterns

    def test_get_pattern(self, registry):
        p = registry.get_pattern("java_simple_item")
        assert p is not None
        assert p.name == "Simple Item Registration"
        
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
