"""
Unit tests for JavaAnalyzerAgent AST functionality.
Tests for the enhanced AST-based Java mod analysis.
"""

import pytest
import tempfile
import zipfile
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

from agents.java_analyzer import JavaAnalyzerAgent


class TestJavaAnalyzerAST:
    """Test JavaAnalyzerAgent AST-specific functionality."""
    
    @pytest.fixture
    def analyzer(self):
        """Create JavaAnalyzerAgent instance for testing."""
        return JavaAnalyzerAgent()
    
    @pytest.fixture
    def jar_with_java_sources(self):
        """Create a JAR with Java source files for AST testing."""
        with tempfile.NamedTemporaryFile(suffix='.jar', delete=False) as jar_file:
            with zipfile.ZipFile(jar_file.name, 'w') as zf:
                # Add fabric.mod.json
                fabric_mod = {
                    "schemaVersion": 1,
                    "id": "test_mod",
                    "version": "1.0.0",
                    "name": "Test Mod"
                }
                zf.writestr('fabric.mod.json', json.dumps(fabric_mod))
                
                # Add a block texture
                zf.writestr('assets/test_mod/textures/block/test_block.png', b'fake_png_data')
                
                # Add Java source files
                block_source = """
package com.example.testmod.block;

import net.minecraft.block.Block;
import net.minecraft.block.Material;
import net.minecraft.item.Item;

public class TestBlock extends Block {
    public TestBlock() {
        super(Material.STONE);
    }
    
    public void onUse() {
        // Block interaction logic
    }
}
"""
                zf.writestr('src/main/java/com/example/testmod/block/TestBlock.java', block_source)
                
                item_source = """
package com.example.testmod.item;

import net.minecraft.item.Item;

public class TestItem extends Item {
    public TestItem() {
        super(new Item.Settings());
    }
    
    public void onUse() {
        // Item use logic
    }
}
"""
                zf.writestr('src/main/java/com/example/testmod/item/TestItem.java', item_source)
                
                # Add a class file for fallback testing
                zf.writestr('com/example/testmod/block/TestBlock.class', b'fake_class_data')
                
            yield jar_file.name
            
        # Cleanup
        os.unlink(jar_file.name)
    
    def test_analyze_jar_with_ast_success(self, analyzer, jar_with_java_sources):
        """Test successful AST-based analysis."""
        result = analyzer.analyze_jar_with_ast(jar_with_java_sources)
        
        assert result["success"] is True
        assert result["mod_info"]["name"] == "test_mod"
        assert result["framework"] == "fabric"
        assert len(result["features"]["blocks"]) > 0
        assert len(result["features"]["items"]) > 0
        assert result["processing_time"] > 0
    
    def test_parse_java_source(self, analyzer):
        """Test Java source parsing."""
        java_code = """
public class TestClass {
    public void testMethod() {
        System.out.println("Hello World");
    }
}
"""
        tree = analyzer._parse_java_source(java_code)
        assert tree is not None
    
    def test_extract_features_from_ast(self, analyzer):
        """Test feature extraction from AST."""
        java_code = """
public class TestBlock {
    public void onUse() {
        // Block interaction logic
    }
    
    public void onBreak() {
        // Block break logic
    }
}
"""
        tree = analyzer._parse_java_source(java_code)
        features = analyzer._extract_features_from_ast(tree)
        
        assert len(features["blocks"]) > 0
        assert features["blocks"][0]["name"] == "TestBlock"
        assert "onUse" in features["blocks"][0]["methods"]
        assert "onBreak" in features["blocks"][0]["methods"]
    
    def test_class_name_to_registry_name(self, analyzer):
        """Test class name to registry name conversion."""
        test_cases = [
            ("TestBlock", "test"),
            ("CopperIngotBlock", "copper_ingot"),
            ("BlockOfDiamond", "of_diamond"),
            ("SimpleItem", "simple_item")
        ]
        
        for class_name, expected in test_cases:
            result = analyzer._class_name_to_registry_name(class_name)
            assert result == expected, f"Expected {expected}, got {result} for {class_name}"
    
    def test_analyze_features_from_sources(self, analyzer, jar_with_java_sources):
        """Test feature analysis from Java sources."""
        with zipfile.ZipFile(jar_with_java_sources, 'r') as jar:
            java_sources = ['src/main/java/com/example/testmod/block/TestBlock.java', 
                           'src/main/java/com/example/testmod/item/TestItem.java']
            features = analyzer._analyze_features_from_sources(jar, java_sources)
            
            assert len(features["blocks"]) > 0
            assert len(features["items"]) > 0
            assert features["blocks"][0]["name"] == "TestBlock"
            assert features["items"][0]["name"] == "TestItem"
    
    def test_extract_features_from_classes(self, analyzer):
        """Test feature extraction from class files."""
        file_list = [
            'com/example/TestBlock.class',
            'com/example/TestItem.class',
            'com/example/SomeEntity.class'
        ]
        
        features = analyzer._extract_features_from_classes(file_list)
        
        assert len(features["blocks"]) > 0
        assert len(features["items"]) > 0
        assert len(features["entities"]) > 0
        assert features["blocks"][0]["name"] == "TestBlock"
    
    def test_analyze_dependencies_from_ast(self, analyzer):
        """Test dependency analysis from AST."""
        java_code = """
import net.minecraft.block.Block;
import net.minecraft.item.Item;

public class TestClass {
    public void testMethod() {
        Block block = new Block();
        Item item = new Item();
    }
}
"""
        tree = analyzer._parse_java_source(java_code)
        dependencies = analyzer._analyze_dependencies_from_ast(tree)
        
        # Should find at least the explicit imports
        assert len([d for d in dependencies if d['type'] == 'explicit']) >= 2
    
    def test_extract_mod_metadata_from_ast(self, analyzer):
        """Test metadata extraction from AST."""
        java_code = """
@Mod("testmod")
public class TestMod {
    @Instance
    public static TestMod instance;
}
"""
        tree = analyzer._parse_java_source(java_code)
        metadata = analyzer._extract_mod_metadata_from_ast(tree)
        
        # This is a simplified test - real annotations would be more complex
        # We're just verifying the method doesn't crash
        assert isinstance(metadata, dict)


if __name__ == '__main__':
    pytest.main([__file__])