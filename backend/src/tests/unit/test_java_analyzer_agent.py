"""Tests for java_analyzer_agent.py module."""

import pytest
import zipfile
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.java_analyzer_agent import JavaAnalyzerAgent


class TestJavaAnalyzerAgent:
    """Test cases for JavaAnalyzerAgent class."""

    @pytest.fixture
    def agent(self):
        """Create a JavaAnalyzerAgent instance."""
        return JavaAnalyzerAgent()

    @pytest.fixture
    def temp_jar_path(self):
        """Create a temporary JAR file for testing."""
        with tempfile.NamedTemporaryFile(suffix='.jar', delete=False) as tmp:
            jar_path = tmp.name
        
        yield jar_path
        
        # Cleanup
        if os.path.exists(jar_path):
            os.remove(jar_path)

    def test_agent_initialization(self, agent):
        """Test that JavaAnalyzerAgent initializes correctly."""
        assert agent is not None
        assert isinstance(agent, JavaAnalyzerAgent)

    def test_analyze_jar_for_mvp_success(self, agent, temp_jar_path):
        """Test successful MVP analysis of a JAR file."""
        # Create a mock JAR with Java class and texture
        with zipfile.ZipFile(temp_jar_path, 'w') as jar:
            # Add a Java class file
            java_code = """
package com.example.mod;

import net.minecraft.block.Block;
import net.minecraft.block.material.Material;
import net.minecraft.item.Item;
import net.minecraft.item.ItemBlock;
import net.minecraftforge.event.RegistryEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.common.eventhandler.SubscribeEvent;

@Mod(modid = "testmod", name = "Test Mod", version = "1.0")
public class TestMod {
    
    public static final Block COPPER_BLOCK = new Block(Material.IRON).setUnlocalizedName("copperBlock");
    
    @SubscribeEvent
    public static void registerBlocks(RegistryEvent.Register<Block> event) {
        event.getRegistry().register(COPPER_BLOCK.setRegistryName("copper_block"));
    }
    
    @SubscribeEvent
    public static void registerItems(RegistryEvent.Register<Item> event) {
        event.getRegistry().register(new ItemBlock(COPPER_BLOCK).setRegistryName("copper_block"));
    }
}
"""
            jar.writestr("com/example/mod/TestMod.class", java_code.encode())
            
            # Add a texture file
            jar.writestr("assets/testmod/textures/block/copper_block.png", b"fake_png_data")

        with patch('javalang.parse.parse') as mock_parse:
            # Mock the Java AST parser
            mock_tree = MagicMock()
            mock_parse.return_value = mock_tree
            
            result = agent.analyze_jar_for_mvp(temp_jar_path)
            
            assert result['success'] is True
            assert 'registry_name' in result
            assert 'texture_path' in result
            assert result['texture_path'] == 'assets/testmod/textures/block/copper_block.png'

    def test_analyze_jar_for_mvp_empty_jar(self, agent, temp_jar_path):
        """Test analysis of an empty JAR file."""
        # Create an empty JAR
        with zipfile.ZipFile(temp_jar_path, 'w') as jar:
            pass  # Create empty JAR

        result = agent.analyze_jar_for_mvp(temp_jar_path)
        
        assert result['success'] is True
        assert result['registry_name'] == 'unknown:copper_block'
        assert result['texture_path'] is None
        assert len(result['errors']) > 0

    def test_find_block_texture_success(self, agent):
        """Test finding block texture in file list."""
        file_list = [
            'com/example/Mod.class',
            'assets/testmod/textures/block/copper_block.png',
            'assets/testmod/models/block/copper_block.json'
        ]
        
        texture_path = agent._find_block_texture(file_list)
        assert texture_path == 'assets/testmod/textures/block/copper_block.png'

    def test_find_block_texture_none_found(self, agent):
        """Test when no block texture is found."""
        file_list = [
            'com/example/Mod.class',
            'assets/testmod/models/block/copper_block.json',
            'assets/testmod/textures/item/copper_ingot.png'
        ]
        
        texture_path = agent._find_block_texture(file_list)
        assert texture_path is None

    def test_find_block_texture_multiple_options(self, agent):
        """Test finding the first block texture when multiple exist."""
        file_list = [
            'com/example/Mod.class',
            'assets/testmod/textures/block/copper_block.png',
            'assets/testmod/textures/block/tin_block.png',
            'assets/testmod/textures/block/iron_block.png'
        ]
        
        texture_path = agent._find_block_texture(file_list)
        # Should return the first one found
        assert texture_path in [
            'assets/testmod/textures/block/copper_block.png',
            'assets/testmod/textures/block/tin_block.png',
            'assets/testmod/textures/block/iron_block.png'
        ]

    def test_extract_registry_name_from_metadata_fabric(self, agent, temp_jar_path):
        """Test extracting registry name from Fabric mod metadata."""
        with zipfile.ZipFile(temp_jar_path, 'w') as jar:
            # Add Fabric mod file
            fabric_mod_json = """
{
    "schemaVersion": 1,
    "id": "testmod",
    "version": "1.0.0",
    "name": "Test Mod",
    "environment": "*"
}
"""
            jar.writestr("fabric.mod.json", fabric_mod_json.encode())

        file_list = jar.namelist()
        with zipfile.ZipFile(temp_jar_path, 'r') as jar:
            registry_name = agent._extract_registry_name_from_jar(jar, file_list)
        
        # Should extract mod ID from fabric.mod.json
        assert registry_name == 'testmod:unknown_block'

    def test_extract_registry_name_from_metadata_forge(self, agent, temp_jar_path):
        """Test extracting registry name from Forge mods.toml metadata."""
        with zipfile.ZipFile(temp_jar_path, 'w') as jar:
            # Add Forge mods.toml file
            forge_mods = """
[[mods]]
modId="testmod"
version="1.0.0"
displayName="Test Mod"
"""
            jar.writestr("META-INF/mods.toml", forge_mods.encode())

        file_list = jar.namelist()
        with zipfile.ZipFile(temp_jar_path, 'r') as jar:
            registry_name = agent._extract_registry_name_from_jar(jar, file_list)
        
        # Should extract mod ID from mods.toml
        assert registry_name == 'testmod:unknown_block'

    def test_class_name_to_registry_name(self, agent):
        """Test converting class names to registry names."""
        # Test basic conversion
        result = agent._class_name_to_registry_name("CopperBlock")
        assert result == "copper_block"
        
        # Test with multiple words
        result = agent._class_name_to_registry_name("AdvancedRedstoneBlock")
        assert result == "advanced_redstone_block"
        
        # Test with numbers
        result = agent._class_name_to_registry_name("Block3D")
        assert result == "block_3d"

    def test_find_block_class_name(self, agent):
        """Test finding block class name from Java source."""
        java_code = """
package com.example.mod;

import net.minecraft.block.Block;

public class CopperBlock extends Block {
    public CopperBlock() {
        super(Material.IRON);
    }
}
"""
        
        with patch('javalang.parse.parse') as mock_parse:
            # Mock the Java AST parser
            mock_tree = MagicMock()
            mock_class = MagicMock()
            mock_class.name = "CopperBlock"
            mock_tree.types = [mock_class]
            mock_parse.return_value = mock_tree
            
            result = agent._find_block_class_name(java_code)
            assert result == "CopperBlock"

    def test_invalid_jar_file(self, agent):
        """Test handling of invalid JAR file."""
        result = agent.analyze_jar_for_mvp("nonexistent_file.jar")
        
        assert result['success'] is False
        assert result['registry_name'] == 'unknown:block'
        assert result['texture_path'] is None
        assert len(result['errors']) > 0

    def test_nonexistent_file(self, agent):
        """Test handling of nonexistent file."""
        result = agent.analyze_jar_for_mvp("path/to/nonexistent/file.jar")
        
        assert result['success'] is False
        assert result['errors'][0].startswith("JAR analysis failed:")

    def test_jar_with_java_source_file(self, agent, temp_jar_path):
        """Test analyzing JAR with Java source file."""
        with zipfile.ZipFile(temp_jar_path, 'w') as jar:
            # Add Java source file
            java_source = """
package com.example.mod;

import net.minecraft.block.Block;

public class TinBlock extends Block {
    public TinBlock() {
        super(Material.IRON);
    }
}
"""
            jar.writestr("com/example/mod/TinBlock.java", java_source.encode())
            
            # Add texture
            jar.writestr("assets/testmod/textures/block/tin_block.png", b"fake_png_data")

        with patch('javalang.parse.parse') as mock_parse:
            # Mock the Java AST parser for source file
            mock_tree = MagicMock()
            mock_class = MagicMock()
            mock_class.name = "TinBlock"
            mock_tree.types = [mock_class]
            mock_parse.return_value = mock_tree
            
            result = agent.analyze_jar_for_mvp(temp_jar_path)
            
            assert result['success'] is True
            assert 'tin_block' in result['registry_name'].lower()
            assert result['texture_path'] == 'assets/testmod/textures/block/tin_block.png'

    def test_jar_missing_texture(self, agent, temp_jar_path):
        """Test JAR with Java class but missing texture."""
        with zipfile.ZipFile(temp_jar_path, 'w') as jar:
            # Add only Java class, no texture
            java_code = """
package com.example.mod;

public class CopperBlock {
    // Block implementation
}
"""
            jar.writestr("com/example/mod/CopperBlock.class", java_code.encode())

        with patch('javalang.parse.parse') as mock_parse:
            mock_tree = MagicMock()
            mock_parse.return_value = mock_tree
            
            result = agent.analyze_jar_for_mvp(temp_jar_path)
            
            assert result['success'] is False
            assert result['texture_path'] is None
            assert "Could not find block texture" in result['errors']

    def test_jar_missing_registry_name(self, agent, temp_jar_path):
        """Test JAR with texture but no identifiable registry name."""
        with zipfile.ZipFile(temp_jar_path, 'w') as jar:
            # Add texture but no meaningful Java classes
            jar.writestr("assets/testmod/textures/block/random_block.png", b"fake_png_data")
            jar.writestr("META-INF/MANIFEST.MF", b"Manifest-Version: 1.0")

        result = agent.analyze_jar_for_mvp(temp_jar_path)
        
        assert result['success'] is False
        assert result['registry_name'] == 'unknown:block'
        assert "Could not determine block registry name" in result['errors']
