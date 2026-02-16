"""
Tests for the enhanced template engine.
"""

import pytest
import json
from pathlib import Path
from templates.template_engine import TemplateEngine, TemplateType


class TestTemplateEngine:
    """Test the enhanced template engine functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.templates_dir = Path(__file__).parent.parent / 'templates' / 'bedrock'
        self.engine = TemplateEngine(self.templates_dir)
    
    def test_engine_initialization(self):
        """Test template engine initializes correctly."""
        assert self.engine is not None
        assert self.engine.templates_dir == self.templates_dir
        assert self.engine.jinja_env is not None
        assert self.engine.selector is not None
    
    def test_basic_block_template_rendering(self):
        """Test basic block template renders correctly."""
        context = {
            "namespace": "test_mod",
            "block_name": "test_block",
            "texture_name": "test_block"
        }
        
        result = self.engine.render_template(
            feature_type="block",
            properties={},
            context=context
        )
        
        # Verify it's valid JSON
        data = json.loads(result)
        assert "minecraft:block" in data
        assert data["minecraft:block"]["description"]["identifier"] == "test_mod:test_block"
    
    def test_resource_pack_template_rendering(self):
        """Test resource pack template rendering."""
        context = {
            "namespace": "test_mod", 
            "block_name": "test_block",
            "texture_name": "test_block"
        }
        
        result = self.engine.render_template(
            feature_type="block",
            properties={},
            context=context,
            pack_type="rp"
        )
        
        # Verify it's valid JSON and has RP structure
        data = json.loads(result)
        assert "minecraft:block" in data
        assert "minecraft:unit_cube" in data["minecraft:block"]["components"]
    
    def test_template_selection_logic(self):
        """Test template selection based on properties."""
        # Test container block selection
        container_properties = {"inventory": True, "container": "chest"}
        template_type = self.engine.selector.select_template("block", container_properties)
        assert template_type == TemplateType.CONTAINER_BLOCK
        
        # Test interactive block selection
        interactive_properties = {"interact": True, "gui": "custom"}
        template_type = self.engine.selector.select_template("block", interactive_properties)
        assert template_type == TemplateType.INTERACTIVE_BLOCK
        
        # Test basic block fallback
        basic_properties = {}
        template_type = self.engine.selector.select_template("block", basic_properties)
        assert template_type == TemplateType.BASIC_BLOCK
    
    def test_item_template_selection(self):
        """Test item template selection."""
        # Test tool selection
        tool_properties = {"tool": True, "pickaxe": True}
        template_type = self.engine.selector.select_template("item", tool_properties)
        assert template_type == TemplateType.TOOL
        
        # Test consumable selection
        food_properties = {"food": True, "consumable": True}
        template_type = self.engine.selector.select_template("item", food_properties)
        assert template_type == TemplateType.CONSUMABLE
    
    def test_template_validation(self):
        """Test template output validation."""
        # Test valid block template
        valid_block = '{"minecraft:block": {"description": {"identifier": "test:block"}}}'
        assert self.engine.validate_template_output(valid_block, TemplateType.BASIC_BLOCK)
        
        # Test invalid JSON
        invalid_json = '{"minecraft:block": malformed json}'
        assert not self.engine.validate_template_output(invalid_json, TemplateType.BASIC_BLOCK)
        
        # Test wrong structure
        wrong_structure = '{"minecraft:item": {"description": {"identifier": "test:item"}}}'
        assert not self.engine.validate_template_output(wrong_structure, TemplateType.BASIC_BLOCK)
    
    def test_available_templates_discovery(self):
        """Test that templates are discovered correctly."""
        available = self.engine.list_available_templates()
        assert len(available) > 0
        assert TemplateType.BASIC_BLOCK in available
    
    def test_template_metadata_loading(self):
        """Test template metadata is loaded correctly."""
        template = self.engine.get_template(TemplateType.BASIC_BLOCK)
        assert template.metadata is not None
        
        # Check if metadata has expected fields
        if template.metadata:
            assert isinstance(template.metadata, dict)
    
    def test_context_validation(self):
        """Test template context validation."""
        template = self.engine.get_template(TemplateType.BASIC_BLOCK)
        
        # Test valid context
        valid_context = {
            "namespace": "test",
            "block_name": "test_block", 
            "texture_name": "test_texture"
        }
        assert template.validate_context(valid_context)
        
        # Test invalid context (missing required params)
        invalid_context = {"namespace": "test"}
        # With metadata loaded, this should fail
        assert not template.validate_context(invalid_context)
    
    def test_entity_template_selection(self):
        """Test entity template selection based on properties."""
        # Test hostile mob selection
        hostile_properties = {"hostile": True, "aggressive": True}
        template_type = self.engine.selector.select_template("entity", hostile_properties)
        assert template_type == TemplateType.HOSTILE_MOB
        
        # Test passive mob selection
        passive_properties = {"passive": True, "peaceful": True}
        template_type = self.engine.selector.select_template("entity", passive_properties)
        assert template_type == TemplateType.PASSIVE_MOB
        
        # Test NPC selection
        npc_properties = {"npc": True, "villager": True}
        template_type = self.engine.selector.select_template("entity", npc_properties)
        assert template_type == TemplateType.NPC
        
        # Test projectile selection
        projectile_properties = {"projectile": True, "arrow": True}
        template_type = self.engine.selector.select_template("entity", projectile_properties)
        assert template_type == TemplateType.PROJECTILE
    
    def test_hostile_mob_template_rendering(self):
        """Test hostile mob template renders correctly."""
        context = {
            "namespace": "test_mod",
            "entity_name": "evil_zombie",
            "max_health": 30,
            "attack_damage": 5,
            "movement_speed": 0.25
        }
        
        result = self.engine.render_template(
            feature_type="entity",
            properties={"hostile": True},
            context=context
        )
        
        # Verify it's valid JSON
        data = json.loads(result)
        assert "minecraft:entity" in data
        assert data["minecraft:entity"]["description"]["identifier"] == "test_mod:evil_zombie"
        # Verify hostile characteristics
        assert "minecraft:attack" in data["minecraft:entity"]["components"]
        assert data["minecraft:entity"]["components"]["minecraft:attack"]["damage"] == 5
    
    def test_passive_mob_template_rendering(self):
        """Test passive mob template renders correctly."""
        context = {
            "namespace": "test_mod",
            "entity_name": "friendly_cow",
            "can_be_bred": True,
            "drops_items": True
        }
        
        result = self.engine.render_template(
            feature_type="entity",
            properties={"passive": True},
            context=context
        )
        
        # Verify it's valid JSON
        data = json.loads(result)
        assert "minecraft:entity" in data
        assert data["minecraft:entity"]["description"]["identifier"] == "test_mod:friendly_cow"
        # Verify passive characteristics
        assert "minecraft:behavior.panic" in data["minecraft:entity"]["components"]
    
    def test_tool_template_rendering(self):
        """Test tool item template renders correctly."""
        context = {
            "namespace": "test_mod",
            "item_name": "diamond_pickaxe",
            "max_durability": 500
        }
        
        result = self.engine.render_template(
            feature_type="item",
            properties={"tool": True, "pickaxe": True},
            context=context
        )
        
        # Verify it's valid JSON
        data = json.loads(result)
        assert "minecraft:item" in data
        assert data["minecraft:item"]["description"]["identifier"] == "test_mod:diamond_pickaxe"
        # Verify tool characteristics
        assert "minecraft:durability" in data["minecraft:item"]["components"]
        assert data["minecraft:item"]["components"]["minecraft:durability"]["max_durability"] == 500
    
    def test_armor_template_rendering(self):
        """Test armor item template renders correctly."""
        context = {
            "namespace": "test_mod",
            "item_name": "diamond_helmet",
            "armor_slot": "head",
            "defense": 6
        }
        
        result = self.engine.render_template(
            feature_type="item",
            properties={"armor": True, "helmet": True},
            context=context
        )
        
        # Verify it's valid JSON
        data = json.loads(result)
        assert "minecraft:item" in data
        assert data["minecraft:item"]["description"]["identifier"] == "test_mod:diamond_helmet"
    
    def test_consumable_template_rendering(self):
        """Test consumable item template renders correctly."""
        context = {
            "namespace": "test_mod",
            "item_name": "golden_apple",
            "max_stack_size": 64,
            "use_duration": 32
        }
        
        result = self.engine.render_template(
            feature_type="item",
            properties={"food": True, "consumable": True},
            context=context
        )
        
        # Verify it's valid JSON
        data = json.loads(result)
        assert "minecraft:item" in data
        assert data["minecraft:item"]["description"]["identifier"] == "test_mod:golden_apple"
        # Verify consumable characteristics
        assert "minecraft:use_duration" in data["minecraft:item"]["components"]
    
    def test_tool_metadata_loaded(self):
        """Test tool template has metadata with defaults."""
        template = self.engine.get_template(TemplateType.TOOL)
        assert template.metadata is not None
        assert "defaults" in template.metadata
        # Verify defaults are applied
        defaults = template.metadata["defaults"]
        assert defaults["max_stack_size"] == 1
        assert defaults["max_durability"] == 250
    
    def test_entity_metadata_loaded(self):
        """Test entity templates have metadata."""
        hostile_template = self.engine.get_template(TemplateType.HOSTILE_MOB)
        assert hostile_template.metadata is not None
        
        passive_template = self.engine.get_template(TemplateType.PASSIVE_MOB)
        assert passive_template.metadata is not None

    def test_entity_template_rendering(self):
        """Test entity template rendering."""
        # Test passive mob template
        template = self.engine.get_template(TemplateType.PASSIVE_MOB)
        context = {
            "namespace": "test_mod",
            "entity_name": "cow",
            "max_health": 10,
            "entity_family": "passive"
        }
        
        result = template.render(context)
        data = json.loads(result)
        assert "minecraft:entity" in data
        assert data["minecraft:entity"]["description"]["identifier"] == "test_mod:cow"
        
        # Test hostile mob template
        template = self.engine.get_template(TemplateType.HOSTILE_MOB)
        context = {
            "namespace": "test_mod",
            "entity_name": "zombie",
            "max_health": 20,
            "entity_family": "hostile"
        }
        
        result = template.render(context)
        data = json.loads(result)
        assert "minecraft:entity" in data
        assert data["minecraft:entity"]["description"]["identifier"] == "test_mod:zombie"

    def test_entity_template_selection(self):
        """Test entity template selection logic."""
        # Test hostile mob selection
        hostile_properties = {"hostile": True, "attack": True}
        template_type = self.engine.selector.select_template("entity", hostile_properties)
        assert template_type == TemplateType.HOSTILE_MOB
        
        # Test passive mob fallback
        passive_properties = {"passive": True, "friendly": True}
        template_type = self.engine.selector.select_template("entity", passive_properties)
        assert template_type == TemplateType.PASSIVE_MOB

    def test_recipe_template_rendering(self):
        """Test recipe template rendering."""
        # Test crafting recipe template
        template = self.engine.get_template(TemplateType.CRAFTING_RECIPE)
        context = {
            "namespace": "test_mod",
            "recipe_name": "diamond_pickaxe",
            "pattern": ["XXX", " X ", " X "],
            "recipe_keys": {
                "X": {"item": "minecraft:diamond", "count": 3}
            },
            "result": {"item": "minecraft:diamond_pickaxe", "count": 1}
        }
        
        result = template.render(context)
        data = json.loads(result)
        assert "minecraft:recipe_shaped" in data
        assert data["minecraft:recipe_shaped"]["description"]["identifier"] == "test_mod:diamond_pickaxe"
        
        # Test smelting recipe template
        template = self.engine.get_template(TemplateType.SMELTING_RECIPE)
        context = {
            "namespace": "test_mod",
            "recipe_name": "iron_ingot",
            "tags": ["furnace"],
            "input": {"item": "minecraft:iron_ore"},
            "output": {"item": "minecraft:iron_ingot", "count": 1}
        }
        
        result = template.render(context)
        data = json.loads(result)
        assert "minecraft:recipe_furnace" in data

    def test_recipe_template_selection(self):
        """Test recipe template selection logic."""
        # Test smelting recipe selection
        smelt_properties = {"smelt": True, "furnace": True}
        template_type = self.engine.selector.select_template("recipe", smelt_properties)
        assert template_type == TemplateType.SMELTING_RECIPE
        
        # Test crafting recipe fallback
        craft_properties = {"craft": True, "shaped": True}
        template_type = self.engine.selector.select_template("recipe", craft_properties)
        assert template_type == TemplateType.CRAFTING_RECIPE


if __name__ == "__main__":
    pytest.main([__file__])
