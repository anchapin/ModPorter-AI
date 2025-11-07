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


if __name__ == "__main__":
    pytest.main([__file__])