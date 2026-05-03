"""
Unit tests for base pattern classes.
Tests ConversionPattern and PatternLibrary.
"""

import pytest
from knowledge.patterns.base import ConversionPattern, PatternLibrary, ComplexityLevel

class TestConversionPattern:
    def test_creation_success(self):
        p = ConversionPattern(
            id="test1",
            name="Test",
            description="Desc",
            java_example="java",
            bedrock_example="bedrock",
            category="item",
            tags=["tag1"],
            complexity="simple",
            success_rate=0.5
        )
        assert p.id == "test1"
        assert p.tags == ["tag1"]

    def test_creation_validation_errors(self):
        with pytest.raises(ValueError, match="Pattern ID"):
            ConversionPattern("", "N", "D", "J", "B", "C")
        with pytest.raises(ValueError, match="Java example"):
            ConversionPattern("I", "N", "D", "", "B", "C")
        with pytest.raises(ValueError, match="Bedrock example"):
            ConversionPattern("I", "N", "D", "J", "", "C")
        with pytest.raises(ValueError, match="Invalid complexity"):
            ConversionPattern("I", "N", "D", "J", "B", "C", complexity="invalid")
        with pytest.raises(ValueError, match="Success rate"):
            ConversionPattern("I", "N", "D", "J", "B", "C", success_rate=1.5)

    def test_to_dict(self):
        p = ConversionPattern("id", "name", "desc", "j", "b", "cat")
        d = p.to_dict()
        assert d["id"] == "id"
        assert d["java_example"] == "j"

    def test_from_dict(self):
        d = {
            "id": "id2", "name": "name2", "description": "desc2",
            "java_example": "j2", "bedrock_example": "b2", "category": "cat2",
            "tags": ["t"], "complexity": "medium", "success_rate": 0.8
        }
        p = ConversionPattern.from_dict(d)
        assert p.id == "id2"
        assert p.complexity == "medium"


class TestPatternLibrary:
    @pytest.fixture
    def library(self):
        lib = PatternLibrary()
        p1 = ConversionPattern("p1", "Name One", "Description One", "java code here", "bedrock code", "item", ["tag1"])
        p2 = ConversionPattern("p2", "Name Two", "Other Desc", "other java", "other bedrock", "block", ["tag2"])
        lib.add_pattern(p1)
        lib.add_pattern(p2)
        return lib

    def test_add_pattern_duplicate_error(self, library):
        p = ConversionPattern("p1", "N", "D", "J", "B", "C")
        with pytest.raises(ValueError, match="already exists"):
            library.add_pattern(p)

    def test_get_pattern(self, library):
        assert library.get_pattern("p1").name == "Name One"
        assert library.get_pattern("missing") is None

    def test_search_by_name(self, library):
        res = library.search("Name One")
        assert len(res) == 1
        assert res[0].id == "p1"

    def test_search_by_code(self, library):
        res = library.search("java code")
        assert len(res) == 1
        assert res[0].id == "p1"

    def test_search_with_category_filter(self, library):
        res = library.search("Name", category="block")
        assert len(res) == 1
        assert res[0].id == "p2"

    def test_search_with_tags_filter(self, library):
        res = library.search("Name", tags=["tag1"])
        assert len(res) == 1
        assert res[0].id == "p1"
        
        # Multiple tags (all must match)
        res = library.search("Name", tags=["tag1", "tag2"])
        assert len(res) == 0

    def test_get_by_category(self, library):
        res = library.get_by_category("item")
        assert len(res) == 1
        assert res[0].id == "p1"

    def test_get_stats(self, library):
        stats = library.get_stats()
        assert stats["total"] == 2
        assert stats["by_category"]["item"] == 1
        assert stats["by_complexity"]["simple"] == 2

    def test_update_success_rate(self, library):
        library.update_success_rate("p1", True)
        assert library.get_pattern("p1").success_rate > 0.0
        
        library.update_success_rate("p1", False)
        # Success rate should decrease
        
        with pytest.raises(ValueError, match="not found"):
            library.update_success_rate("missing", True)
