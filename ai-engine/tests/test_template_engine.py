"""
Tests for the Template Engine and Template Library.

This test verifies the template system works correctly for Issue #436.
"""

import pytest
import json
from pathlib import Path
import sys
import tempfile

# Add ai-engine to path
ai_engine_root = Path(__file__).parent.parent
sys.path.insert(0, str(ai_engine_root))

from templates.template_engine import (
    TemplateEngine,
    TemplateSelector,
    TemplateType,
    TemplateCategory
)


class TestTemplateEngine:
    """Test template engine functionality."""
    
    @pytest.fixture
    def template_engine(self):
        """Create template engine instance."""
        templates_dir = ai_engine_root / "templates" / "bedrock"
        return TemplateEngine(templates_dir=templates_dir)
    
    @pytest.fixture
    def template_selector(self):
        """Create template selector instance."""
        return TemplateSelector()
    
    def test_template_engine_creation(self, template_engine):
        """Test template engine can be created."""
        assert template_engine is not None
        assert template_engine.templates_dir.exists()
    
    def test_discover_templates(self, template_engine):
        """Test template discovery."""
        templates = template_engine.list_available_templates()
        
        assert len(templates) > 0
        
        # Check for expected template types
        template_names = [t.value for t in templates]
        
        # Should have basic block template
        assert TemplateType.BASIC_BLOCK in templates
        
        # Should have item templates
        assert TemplateType.BASIC_ITEM in templates
        assert TemplateType.TOOL in templates
        assert TemplateType.ARMOR in templates
        assert TemplateType.CONSUMABLE in templates
        
        # Should have entity templates
        assert TemplateType.PASSIVE_MOB in templates
        assert TemplateType.HOSTILE_MOB in templates
        
        # Should have recipe templates
        assert TemplateType.CRAFTING_RECIPE in templates
        assert TemplateType.SMELTING_RECIPE in templates
    
    def test_get_template(self, template_engine):
        """Test getting a specific template."""
        template = template_engine.get_template(TemplateType.BASIC_BLOCK)
        
        assert template is not None
        assert template.template_type == TemplateType.BASIC_BLOCK
    
    def test_render_basic_block(self, template_engine):
        """Test rendering a basic block template."""
        context = {
            'namespace': 'modpack',
            'block_name': 'copper_block',
            'texture_name': 'copper_block'
        }
        
        # Render behavior pack template
        result = template_engine.render_template(
            feature_type='block',
            properties={},
            context=context,
            pack_type='bp'
        )
        
        assert result is not None
        assert 'minecraft:block' in result or 'copper_block' in result
    
    def test_render_item(self, template_engine):
        """Test rendering an item template."""
        context = {
            'namespace': 'modpack',
            'item_name': 'copper_sword'
        }
        
        result = template_engine.render_template(
            feature_type='item',
            properties={'tool': True},
            context=context
        )
        
        assert result is not None
        assert 'copper_sword' in result
    
    def test_render_recipe(self, template_engine):
        """Test rendering a recipe template."""
        context = {
            'namespace': 'modpack',
            'recipe_name': 'copper_block',
            'pattern': ['XXX', 'XXX', 'XXX'],
            'recipe_keys': {'X': 'minecraft:copper_ingot'},
            'result': 'modpack:copper_block'
        }
        
        result = template_engine.render_template(
            feature_type='recipe',
            properties={},
            context=context
        )
        
        assert result is not None
    
    def test_template_validation(self, template_engine):
        """Test template output validation."""
        # Valid block JSON
        valid_block = '{"minecraft:block": {"description": {"identifier": "test:block"}}}'
        assert template_engine.validate_template_output(valid_block, TemplateType.BASIC_BLOCK)
        
        # Valid item JSON
        valid_item = '{"minecraft:item": {"description": {"identifier": "test:item"}}}'
        assert template_engine.validate_template_output(valid_item, TemplateType.BASIC_ITEM)


class TestTemplateSelector:
    """Test smart template selection."""
    
    @pytest.fixture
    def selector(self):
        """Create template selector."""
        return TemplateSelector()
    
    def test_selector_creation(self, selector):
        """Test selector can be created."""
        assert selector is not None
    
    def test_select_basic_block(self, selector):
        """Test selecting basic block template."""
        template = selector.select_template('block', {'material': 'stone'})
        
        assert template == TemplateType.BASIC_BLOCK
    
    def test_select_container_block(self, selector):
        """Test selecting container block template."""
        template = selector.select_template('block', {'inventory': True})
        
        assert template == TemplateType.CONTAINER_BLOCK
    
    def test_select_interactive_block(self, selector):
        """Test selecting interactive block template."""
        template = selector.select_template('block', {'interact': True})
        
        assert template == TemplateType.INTERACTIVE_BLOCK
    
    def test_select_tool_item(self, selector):
        """Test selecting tool item template."""
        template = selector.select_template('item', {'pickaxe': True})
        
        assert template == TemplateType.TOOL
    
    def test_select_sword(self, selector):
        """Test selecting weapon template for sword."""
        template = selector.select_template('item', {'sword': True})
        
        assert template == TemplateType.WEAPON
    
    def test_select_armor(self, selector):
        """Test selecting armor template."""
        template = selector.select_template('item', {'helmet': True})
        
        assert template == TemplateType.ARMOR
    
    def test_select_consumable(self, selector):
        """Test selecting consumable template."""
        template = selector.select_template('item', {'food': True})
        
        assert template == TemplateType.CONSUMABLE
    
    def test_select_hostile_mob(self, selector):
        """Test selecting hostile mob template."""
        template = selector.select_template('entity', {'hostile': True})
        
        assert template == TemplateType.HOSTILE_MOB
    
    def test_select_passive_mob(self, selector):
        """Test selecting passive mob template."""
        template = selector.select_template('entity', {'passive': True})
        
        assert template == TemplateType.PASSIVE_MOB
    
    def test_select_smelting_recipe(self, selector):
        """Test selecting smelting recipe template."""
        template = selector.select_template('recipe', {'smelt': True})
        
        assert template == TemplateType.SMELTING_RECIPE


class TestTemplateCategories:
    """Test template categories and types."""
    
    def test_block_categories(self):
        """Test block template types are defined."""
        block_types = [
            TemplateType.BASIC_BLOCK,
            TemplateType.CONTAINER_BLOCK,
            TemplateType.INTERACTIVE_BLOCK,
            TemplateType.MULTI_BLOCK,
            TemplateType.MACHINE_BLOCK,
        ]
        
        for bt in block_types:
            assert bt.value.endswith('_block')
    
    def test_item_categories(self):
        """Test item template types are defined."""
        item_types = [
            TemplateType.BASIC_ITEM,
            TemplateType.TOOL,
            TemplateType.WEAPON,
            TemplateType.ARMOR,
            TemplateType.CONSUMABLE,
            TemplateType.DECORATIVE,
        ]
        
        for it in item_types:
            assert it.value.endswith('_item') or it in [TemplateType.TOOL, TemplateType.WEAPON, TemplateType.ARMOR, TemplateType.CONSUMABLE, TemplateType.DECORATIVE]
    
    def test_entity_categories(self):
        """Test entity template types are defined."""
        entity_types = [
            TemplateType.PASSIVE_MOB,
            TemplateType.HOSTILE_MOB,
            TemplateType.NPC,
            TemplateType.PROJECTILE,
        ]
        
        for et in entity_types:
            assert et.value.endswith('_mob') or et in [TemplateType.NPC, TemplateType.PROJECTILE]
    
    def test_recipe_categories(self):
        """Test recipe template types are defined."""
        recipe_types = [
            TemplateType.CRAFTING_RECIPE,
            TemplateType.SMELTING_RECIPE,
            TemplateType.BREWING_RECIPE,
            TemplateType.CUSTOM_RECIPE,
        ]
        
        for rt in recipe_types:
            assert rt.value.endswith('_recipe')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
