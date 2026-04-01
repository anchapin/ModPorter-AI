"""
Unit tests for pattern mappings.
Tests PatternMapping and PatternMappingRegistry.
"""

import pytest
from knowledge.patterns.mappings import PatternMapping, PatternMappingRegistry, MappingConfidence

class TestPatternMapping:
    def test_creation_success(self):
        m = PatternMapping(
            java_pattern_id="j1",
            bedrock_pattern_id="b1",
            confidence=0.9,
            notes="Notes",
            limitations=["lim1"],
            requires_manual_review=False
        )
        assert m.java_pattern_id == "j1"
        assert m.confidence == 0.9

    def test_creation_validation_errors(self):
        with pytest.raises(ValueError, match="Java pattern ID"):
            PatternMapping("", "b1", 0.5)
        with pytest.raises(ValueError, match="Bedrock pattern ID"):
            PatternMapping("j1", "", 0.5)
        with pytest.raises(ValueError, match="Confidence"):
            PatternMapping("j1", "b1", 1.5)

    def test_to_dict(self):
        m = PatternMapping("j1", "b1", 0.8)
        d = m.to_dict()
        assert d["java_pattern_id"] == "j1"
        assert d["confidence"] == 0.8

    def test_from_dict(self):
        d = {
            "java_pattern_id": "j2", "bedrock_pattern_id": "b2", 
            "confidence": 0.7, "notes": "n", "limitations": ["l"],
            "requires_manual_review": True
        }
        m = PatternMapping.from_dict(d)
        assert m.java_pattern_id == "j2"
        assert m.requires_manual_review is True


class TestPatternMappingRegistry:
    @pytest.fixture
    def registry(self):
        return PatternMappingRegistry()

    def test_registry_initialization(self, registry):
        """Test that registry is pre-populated with mappings."""
        assert len(registry.mappings) >= 20
        assert "java_simple_item" in registry.mappings
        assert "java_tile_entity" in registry.mappings

    def test_add_mapping(self, registry):
        m = PatternMapping("new_j", "new_b", 0.5)
        registry.add_mapping(m)
        assert registry.get_bedrock_equivalent("new_j") == m

    def test_add_mapping_duplicate_error(self, registry):
        m = PatternMapping("java_simple_item", "b", 0.5)
        with pytest.raises(ValueError, match="already exists"):
            registry.add_mapping(m)

    def test_get_bedrock_equivalent(self, registry):
        m = registry.get_bedrock_equivalent("java_simple_item")
        assert m is not None
        assert m.bedrock_pattern_id == "bedrock_simple_item"
        
        assert registry.get_bedrock_equivalent("non_existent") is None

    def test_get_all_mappings(self, registry):
        all_maps = registry.get_all_mappings()
        assert len(all_maps) == len(registry.mappings)
        assert isinstance(all_maps, list)

    def test_get_by_confidence(self, registry):
        # High confidence mappings
        high = registry.get_by_confidence(0.9)
        assert len(high) > 0
        assert all(m.confidence >= 0.9 for m in high)

    def test_get_manual_review_required(self, registry):
        required = registry.get_manual_review_required()
        assert len(required) > 0
        assert all(m.requires_manual_review for m in required)

    def test_get_stats(self, registry):
        stats = registry.get_stats()
        assert stats["total"] == len(registry.mappings)
        assert "by_confidence" in stats
        assert "requires_manual_review" in stats
        assert stats["by_confidence"]["high"] > 0
