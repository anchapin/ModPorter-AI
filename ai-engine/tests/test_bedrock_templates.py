"""
Unit tests for Bedrock template library.

These tests verify that all entity, item, and recipe templates generate valid Bedrock JSON.
"""

import json
import pytest
from pathlib import Path

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from templates.template_engine import TemplateEngine, TemplateType, TemplateCategory


class TestBedrockTemplates:
    """Test Bedrock template generation."""
    
    @pytest.fixture
    def template_engine(self):
        """Create template engine instance."""
        return TemplateEngine()
    
    @pytest.fixture
    def basic_context(self):
        """Basic context for template rendering."""
        return {
            'namespace': 'mod',
            'entity_name': 'test_entity'
        }
    
    def test_template_engine_initialization(self, template_engine):
        """Test template engine initializes correctly."""
        assert template_engine is not None
        assert template_engine.templates_dir.exists()
    
    def test_list_available_templates(self, template_engine):
        """Test listing available templates."""
        templates = template_engine.list_available_templates()
        assert len(templates) > 0
    
    def test_hostile_mob_template(self, template_engine, basic_context):
        """Test hostile mob template generates valid JSON."""
        result = template_engine.render_template(
            'entity',
            {'behavior': 'hostile'},
            basic_context
        )
        data = json.loads(result)
        assert 'minecraft:entity' in data
        assert data['minecraft:entity']['description']['identifier'] == 'mod:test_entity'
    
    def test_passive_mob_template(self, template_engine, basic_context):
        """Test passive mob template generates valid JSON."""
        context = {
            'namespace': 'mod',
            'entity_name': 'sheep',
            'entity_family': 'passive'
        }
        result = template_engine.render_template(
            'entity',
            {'behavior': 'passive'},
            context
        )
        data = json.loads(result)
        assert 'minecraft:entity' in data
    
    def test_tool_template(self, template_engine):
        """Test tool item template generates valid JSON."""
        context = {
            'namespace': 'mod',
            'item_name': 'diamond_pickaxe',
            'max_damage': 1561,
            'enchantable': True
        }
        result = template_engine.render_template(
            'item',
            {'type': 'tool'},
            context
        )
        data = json.loads(result)
        assert 'minecraft:item' in data
    
    def test_armor_template(self, template_engine):
        """Test armor item template generates valid JSON."""
        context = {
            'namespace': 'mod',
            'item_name': 'diamond_helmet',
            'armor': 6,
            'toughness': 2
        }
        result = template_engine.render_template(
            'item',
            {'type': 'armor'},
            context
        )
        data = json.loads(result)
        assert 'minecraft:item' in data
    
    def test_consumable_template(self, template_engine):
        """Test consumable item template generates valid JSON."""
        context = {
            'namespace': 'mod',
            'item_name': 'apple',
            'food': 4
        }
        result = template_engine.render_template(
            'item',
            {'type': 'consumable'},
            context
        )
        data = json.loads(result)
        assert 'minecraft:item' in data
    
    def test_shaped_crafting_recipe(self, template_engine):
        """Test shaped crafting recipe generates valid JSON."""
        context = {
            'namespace': 'mod',
            'recipe_name': 'diamond_sword',
            'pattern': ['X', 'X', '|'],
            'recipe_keys': {
                'X': {'item': 'minecraft:diamond'},
                '|': {'item': 'minecraft:stick'}
            },
            'result': {'item': 'minecraft:diamond_sword', 'count': 1}
        }
        result = template_engine.render_template(
            'recipe',
            {'type': 'shaped'},
            context
        )
        data = json.loads(result)
        assert 'minecraft:recipe_shaped' in data or 'type' in data
    
    def test_shapeless_recipe(self, template_engine):
        """Test shapeless recipe generates valid JSON."""
        context = {
            'namespace': 'mod',
            'recipe_name': 'torch',
            'tags': ['crafting_table'],
            'ingredients': [
                {'item': 'minecraft:coal'},
                {'item': 'minecraft:stick'}
            ],
            'result': {'item': 'minecraft:torch', 'count': 4}
        }
        result = template_engine.render_template(
            'recipe',
            {'type': 'shapeless'},
            context
        )
        data = json.loads(result)
        assert 'minecraft:recipe_shapeless' in data or 'type' in data
    
    def test_smelting_recipe(self, template_engine):
        """Test smelting recipe generates valid JSON."""
        context = {
            'namespace': 'mod',
            'recipe_name': 'iron_ingot',
            'input': {'item': 'minecraft:iron_ore'},
            'output': {'item': 'minecraft:iron_ingot'},
            'tags': ['furnace'],
            'cooking_time': 200,
            'experience': 0.7
        }
        result = template_engine.render_template(
            'recipe',
            {'type': 'smelting'},
            context
        )
        data = json.loads(result)
        assert 'minecraft:recipe_furnace' in data or 'type' in data
    
    def test_container_block_template(self, template_engine):
        """Test container block template generates valid JSON."""
        context = {
            'namespace': 'mod',
            'block_name': 'chest',
            'container_type': 'chest'
        }
        result = template_engine.render_template(
            'block',
            {'container': True},
            context
        )
        data = json.loads(result)
        assert 'minecraft:block' in data
    
    def test_interactive_block_template(self, template_engine):
        """Test interactive block template generates valid JSON."""
        context = {
            'namespace': 'mod',
            'block_name': 'button',
            'interactive_type': 'click'
        }
        result = template_engine.render_template(
            'block',
            {'interactive': True},
            context
        )
        data = json.loads(result)
        assert 'minecraft:block' in data
    
    def test_validate_template_output(self, template_engine):
        """Test template output validation."""
        valid_block = '{"minecraft:block": {"description": {}}}'
        assert template_engine.validate_template_output(valid_block, TemplateType.BASIC_BLOCK) is True
    
    def test_template_type_enum(self):
        """Test TemplateType enum contains expected values."""
        assert TemplateType.HOSTILE_MOB.value == 'hostile_mob'
        assert TemplateType.PASSIVE_MOB.value == 'passive_mob'
        assert TemplateType.TOOL.value == 'tool'
        assert TemplateType.ARMOR.value == 'armor'
        assert TemplateType.CONSUMABLE.value == 'consumable'
        assert TemplateType.CRAFTING_RECIPE.value == 'crafting_recipe'
        assert TemplateType.SHAPELESS_RECIPE.value == 'shapeless_recipe'
        assert TemplateType.SMELTING_RECIPE.value == 'smelting_recipe'
    
    def test_template_category_enum(self):
        """Test TemplateCategory enum contains expected values."""
        assert TemplateCategory.BLOCKS.value == 'blocks'
        assert TemplateCategory.ITEMS.value == 'items'
        assert TemplateCategory.ENTITIES.value == 'entities'
        assert TemplateCategory.RECIPES.value == 'recipes'


class TestTemplateSelector:
    """Test template selector logic."""
    
    @pytest.fixture
    def selector(self):
        from templates.template_engine import TemplateSelector
        return TemplateSelector()
    
    def test_select_hostile_entity(self, selector):
        """Test selecting hostile entity template."""
        template = selector.select_template('entity', {'behavior': 'hostile', 'attack': True})
        assert template == TemplateType.HOSTILE_MOB
    
    def test_select_passive_entity(self, selector):
        """Test selecting passive entity template."""
        template = selector.select_template('entity', {'behavior': 'passive'})
        assert template == TemplateType.PASSIVE_MOB
    
    def test_select_tool_item(self, selector):
        """Test selecting tool item template."""
        template = selector.select_template('item', {'type': 'tool', 'pickaxe': True})
        assert template == TemplateType.TOOL
    
    def test_select_armor_item(self, selector):
        """Test selecting armor item template."""
        template = selector.select_template('item', {'armor': True, 'helmet': True})
        assert template == TemplateType.ARMOR
    
    def test_select_container_block(self, selector):
        """Test selecting container block template."""
        template = selector.select_template('block', {'container': True, 'inventory': True})
        assert template == TemplateType.CONTAINER_BLOCK
    
    def test_select_interactive_block(self, selector):
        """Test selecting interactive block template."""
        template = selector.select_template('block', {'interactive': True, 'click': True})
        assert template == TemplateType.INTERACTIVE_BLOCK
    
    def test_select_shapeless_recipe(self, selector):
        """Test selecting shapeless recipe template."""
        template = selector.select_template('recipe', {'type': 'shapeless'})
        assert template == TemplateType.SHAPELESS_RECIPE
    
    def test_select_smelting_recipe(self, selector):
        """Test selecting smelting recipe template."""
        template = selector.select_template('recipe', {'type': 'smelting'})
        assert template == TemplateType.SMELTING_RECIPE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
