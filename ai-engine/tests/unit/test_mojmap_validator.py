import pytest
from ai_engine.mmsd.validators.mojmap_validator import MojmapMappingValidator


class TestMojmapMappingValidator:
    """Tests for MojmapMappingValidator."""

    @pytest.fixture
    def validator(self):
        return MojmapMappingValidator()

    def test_mojmap_valid_java_source(self, validator):
        """Mojmap naming (readable) should pass validation."""
        java_source = """
        package com.example.mod;

        public class MyBlock extends Block {
            public void registerBlock() {
                // Mojmap style method names
            }

            public BlockState getDefaultState() {
                return defaultState;
            }
        }
        """
        is_valid, msg = validator.validate(java_source)
        assert is_valid is True
        assert msg == "Mojmap"

    def test_detects_func_pattern(self, validator):
        """SRG func_N pattern should fail validation."""
        java_source = """
        public void func_123456_a() {
            // SRG method name
        }
        """
        is_valid, msg = validator.validate(java_source)
        assert is_valid is False
        assert "func_" in msg

    def test_detects_field_pattern(self, validator):
        """SRG field_N pattern should fail validation."""
        java_source = """
        public int field_789012;
        """
        is_valid, msg = validator.validate(java_source)
        assert is_valid is False
        assert "field_" in msg

    def test_detects_class_pattern(self, validator):
        """SRG class_N pattern should fail validation."""
        java_source = """
        private class class_345678 {
        }
        """
        is_valid, msg = validator.validate(java_source)
        assert is_valid is False
        assert "class_" in msg

    def test_detects_net_minecraft_underscore(self, validator):
        """SRG net_minecraft_ package style should fail."""
        java_source = """
        import net_minecraft_world.entity.Entity;
        """
        is_valid, msg = validator.validate(java_source)
        assert is_valid is False
        assert "net_minecraft_" in msg

    def test_empty_source_returns_valid(self, validator):
        """Empty source should be treated as valid (skip)."""
        is_valid, msg = validator.validate("")
        assert is_valid is True
        assert msg == "Empty source (skip)"

    def test_none_source_returns_valid(self, validator):
        """None source should be treated as valid."""
        is_valid, msg = validator.validate(None)
        assert is_valid is True

    def test_filter_pairs_separates_valid_invalid(self, validator):
        """filter_pairs should separate valid and invalid pairs."""
        pairs = [
            {"java_source": "public void registerBlock() {}", "id": "valid1"},
            {"java_source": "public void func_123() {}", "id": "invalid1"},
            {"java_source": "public int getValue() {}", "id": "valid2"},
            {"java_source": "private int field_456;", "id": "invalid2"},
        ]
        valid, invalid = validator.filter_pairs(pairs)
        assert len(valid) == 2
        assert len(invalid) == 2
        assert valid[0]["id"] == "valid1"
        assert valid[1]["id"] == "valid2"
        assert invalid[0]["id"] == "invalid1"
        assert invalid[1]["id"] == "invalid2"

    def test_filter_pairs_handles_missing_key(self, validator):
        """filter_pairs should treat missing java_source as valid."""
        pairs = [
            {"id": "no_java_source"},
            {"java_source": "func_123", "id": "has_srg"},
        ]
        valid, invalid = validator.filter_pairs(pairs)
        assert len(valid) == 1
        assert len(invalid) == 1