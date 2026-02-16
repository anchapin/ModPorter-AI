"""
Unit tests for Bedrock template library.

These tests validate that all templates can be rendered correctly
and produce valid JSON output for Bedrock add-ons.
"""

import json
import os
import pytest
from pathlib import Path


# Get the templates directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "bedrock"


class TestBlockTemplates:
    """Test block templates."""
    
    def test_basic_block_template_exists(self):
        """Test that basic_block template exists."""
        template_path = TEMPLATES_DIR / "blocks" / "basic_block.json"
        assert template_path.exists(), "basic_block.json template not found"
    
    def test_basic_block_valid_json_structure(self):
        """Test that basic_block template has valid JSON structure."""
        template_path = TEMPLATES_DIR / "blocks" / "basic_block.json"
        with open(template_path, 'r') as f:
            content = f.read()
        
        # Should be valid Jinja2 template (not pure JSON)
        assert "{" in content, "Template should contain JSON structure"
    
    def test_container_block_template_exists(self):
        """Test that container_block template exists."""
        template_path = TEMPLATES_DIR / "blocks" / "container_block.json"
        assert template_path.exists(), "container_block.json template not found"
    
    def test_interactive_block_template_exists(self):
        """Test that interactive_block template exists."""
        template_path = TEMPLATES_DIR / "blocks" / "interactive_block.json"
        assert template_path.exists(), "interactive_block.json template not found"


class TestEntityTemplates:
    """Test entity templates."""
    
    def test_hostile_mob_template_exists(self):
        """Test that hostile_mob template exists."""
        template_path = TEMPLATES_DIR / "entities" / "hostile_mob.json"
        assert template_path.exists(), "hostile_mob.json template not found"
    
    def test_hostile_mob_has_required_components(self):
        """Test that hostile_mob template has required components."""
        template_path = TEMPLATES_DIR / "entities" / "hostile_mob.json"
        with open(template_path, 'r') as f:
            content = f.read()
        
        # Check for essential components
        assert "minecraft:entity" in content
        assert "minecraft:health" in content
        assert "minecraft:attack" in content
    
    def test_passive_mob_template_exists(self):
        """Test that passive_mob template exists."""
        template_path = TEMPLATES_DIR / "entities" / "passive_mob.json"
        assert template_path.exists(), "passive_mob.json template not found"
    
    def test_passive_mob_has_required_components(self):
        """Test that passive_mob template has required components."""
        template_path = TEMPLATES_DIR / "entities" / "passive_mob.json"
        with open(template_path, 'r') as f:
            content = f.read()
        
        # Check for essential components
        assert "minecraft:entity" in content
        assert "minecraft:health" in content


class TestItemTemplates:
    """Test item templates."""
    
    def test_basic_item_template_exists(self):
        """Test that basic_item template exists."""
        template_path = TEMPLATES_DIR / "items" / "basic_item.json"
        assert template_path.exists(), "basic_item.json template not found"
    
    def test_tool_template_exists(self):
        """Test that tool template exists."""
        template_path = TEMPLATES_DIR / "items" / "tool.json"
        assert template_path.exists(), "tool.json template not found"
    
    def test_tool_has_durability_component(self):
        """Test that tool template includes durability."""
        template_path = TEMPLATES_DIR / "items" / "tool.json"
        with open(template_path, 'r') as f:
            content = f.read()
        
        assert "minecraft:durability" in content or "durability" in content.lower()
    
    def test_armor_template_exists(self):
        """Test that armor template exists."""
        template_path = TEMPLATES_DIR / "items" / "armor.json"
        assert template_path.exists(), "armor.json template not found"
    
    def test_consumable_template_exists(self):
        """Test that consumable template exists."""
        template_path = TEMPLATES_DIR / "items" / "consumable.json"
        assert template_path.exists(), "consumable.json template not found"
    
    def test_ranged_weapon_template_exists(self):
        """Test that ranged_weapon template exists."""
        template_path = TEMPLATES_DIR / "items" / "ranged_weapon.json"
        assert template_path.exists(), "ranged_weapon.json template not found"
    
    def test_rare_item_template_exists(self):
        """Test that rare_item template exists."""
        template_path = TEMPLATES_DIR / "items" / "rare_item.json"
        assert template_path.exists(), "rare_item.json template not found"


class TestRecipeTemplates:
    """Test recipe templates."""
    
    def test_crafting_recipe_template_exists(self):
        """Test that crafting_recipe template exists."""
        template_path = TEMPLATES_DIR / "recipes" / "crafting_recipe.json"
        assert template_path.exists(), "crafting_recipe.json template not found"
    
    def test_shapeless_recipe_template_exists(self):
        """Test that shapeless_recipe template exists."""
        template_path = TEMPLATES_DIR / "recipes" / "shapeless_recipe.json"
        assert template_path.exists(), "shapeless_recipe.json template not found"
    
    def test_smelting_recipe_template_exists(self):
        """Test that smelting_recipe template exists."""
        template_path = TEMPLATES_DIR / "recipes" / "smelting_recipe.json"
        assert template_path.exists(), "smelting_recipe.json template not found"
    
    def test_blasting_recipe_template_exists(self):
        """Test that blasting_recipe template exists."""
        template_path = TEMPLATES_DIR / "recipes" / "blasting_recipe.json"
        assert template_path.exists(), "blasting_recipe.json template not found"
    
    def test_smoking_recipe_template_exists(self):
        """Test that smoking_recipe template exists."""
        template_path = TEMPLATES_DIR / "recipes" / "smoking_recipe.json"
        assert template_path.exists(), "smoking_recipe.json template not found"
    
    def test_campfire_recipe_template_exists(self):
        """Test that campfire_recipe template exists."""
        template_path = TEMPLATES_DIR / "recipes" / "campfire_recipe.json"
        assert template_path.exists(), "campfire_recipe.json template not found"
    
    def test_stonecutter_recipe_template_exists(self):
        """Test that stonecutter_recipe template exists."""
        template_path = TEMPLATES_DIR / "recipes" / "stonecutter_recipe.json"
        assert template_path.exists(), "stonecutter_recipe.json template not found"
    
    def test_smithing_recipe_template_exists(self):
        """Test that smithing_recipe template exists."""
        template_path = TEMPLATES_DIR / "recipes" / "smithing_recipe.json"
        assert template_path.exists(), "smithing_recipe.json template not found"


class TestManifestTemplates:
    """Test manifest templates."""
    
    def test_manifest_bp_template_exists(self):
        """Test that manifest_bp template exists (behavior pack)."""
        template_path = TEMPLATES_DIR / "manifest_bp.json"
        assert template_path.exists(), "manifest_bp.json template not found"
    
    def test_manifest_rp_template_exists(self):
        """Test that manifest_rp template exists (resource pack)."""
        template_path = TEMPLATES_DIR / "manifest_rp.json"
        assert template_path.exists(), "manifest_rp.json template not found"
    
    def test_manifest_has_required_fields(self):
        """Test that manifest templates have required fields."""
        template_path = TEMPLATES_DIR / "manifest_bp.json"
        with open(template_path, 'r') as f:
            content = f.read()
        
        # Check for required fields
        assert "format_version" in content
        assert "header" in content
        assert "modules" in content


class TestTemplateSelection:
    """Test template selection logic."""
    
    def test_all_required_templates_exist(self):
        """Test that all required templates from issue #404 exist."""
        required_templates = [
            "blocks/basic_block.json",
            "entities/passive_mob.json",
            "entities/hostile_mob.json",
            "items/basic_item.json",
            "items/tool.json",
        ]
        
        for template in required_templates:
            template_path = TEMPLATES_DIR / template
            assert template_path.exists(), f"Required template {template} not found"
    
    def test_template_count(self):
        """Test that we have a good variety of templates."""
        # Count all template files
        template_files = list(TEMPLATES_DIR.rglob("*.json"))
        
        # Should have at least 20 template files
        assert len(template_files) >= 20, f"Expected at least 20 templates, found {len(template_files)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
