"""Test JAR generator utilities for creating test fixtures."""

import os
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Union


class TestJarGenerator:
    """Utility class for generating test JAR files for mod conversion testing."""
    
    def __init__(self, temp_dir: Optional[str] = None):
        """Initialize the test JAR generator.
        
        Args:
            temp_dir: Optional temporary directory for JAR creation
        """
        if temp_dir:
            self.temp_dir = temp_dir
            # Ensure the directory exists
            Path(self.temp_dir).mkdir(parents=True, exist_ok=True)
        else:
            self.temp_dir = tempfile.mkdtemp()
        
        self.created_jars = []
    
    def create_simple_jar(self, name: str, java_files: Dict[str, str]) -> str:
        """Create a simple JAR file with the provided Java files.
        
        Args:
            name: Name of the JAR file (without extension)
            java_files: Dict mapping file paths to Java source code
            
        Returns:
            Path to the created JAR file
        """
        jar_path = os.path.join(self.temp_dir, f"{name}.jar")
        
        with zipfile.ZipFile(jar_path, 'w', zipfile.ZIP_DEFLATED) as jar:
            for file_path, content in java_files.items():
                jar.writestr(file_path, content)
        
        self.created_jars.append(jar_path)
        return jar_path
    
    def create_mod_jar(self, mod_name: str, blocks: List[str] = None, items: List[str] = None) -> str:
        """Create a test mod JAR with basic structure.
        
        Args:
            mod_name: Name of the mod
            blocks: List of block names to include
            items: List of item names to include
            
        Returns:
            Path to the created JAR file
        """
        blocks = blocks or ["stone_block"]
        items = items or ["copper_ingot"]
        
        java_files = {}
        
        # Create main mod class
        main_class = f"""
package com.example.{mod_name.lower()};

import net.minecraft.block.Block;
import net.minecraft.item.Item;
import net.minecraftforge.fml.common.Mod;

@Mod("{mod_name.lower()}")
public class {mod_name.title()}Mod {{
    public static final String MODID = "{mod_name.lower()}";
    
    // Mod initialization
}}
"""
        java_files[f"com/example/{mod_name.lower()}/{mod_name.title()}Mod.java"] = main_class
        
        # Create block classes
        for block in blocks:
            block_class = f"""
package com.example.{mod_name.lower()}.blocks;

import net.minecraft.block.Block;
import net.minecraft.block.material.Material;

public class {block.title().replace('_', '')} extends Block {{
    public {block.title().replace('_', '')}() {{
        super(Material.STONE);
        setUnlocalizedName("{block}");
        setRegistryName("{block}");
    }}
}}
"""
            java_files[f"com/example/{mod_name.lower()}/blocks/{block.title().replace('_', '')}.java"] = block_class
        
        # Create item classes
        for item in items:
            item_class = f"""
package com.example.{mod_name.lower()}.items;

import net.minecraft.item.Item;

public class {item.title().replace('_', '')} extends Item {{
    public {item.title().replace('_', '')}() {{
        setUnlocalizedName("{item}");
        setRegistryName("{item}");
    }}
}}
"""
            java_files[f"com/example/{mod_name.lower()}/items/{item.title().replace('_', '')}.java"] = item_class
        
        return self.create_simple_jar(mod_name, java_files)
    
    def cleanup(self):
        """Clean up created JAR files."""
        for jar_path in self.created_jars:
            if os.path.exists(jar_path):
                os.remove(jar_path)
        self.created_jars.clear()


def create_test_mod_suite(output_dir = None) -> Dict[str, str]:
    """Create a suite of test mods for comprehensive testing.
    
    Args:
        output_dir: Directory to create JAR files in (Path or str)
        
    Returns:
        Dict mapping mod names to JAR file paths
    """
    # Ensure output directory exists and convert to string
    if output_dir is not None:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        output_dir_str = str(output_path)
    else:
        output_dir_str = None
    
    generator = TestJarGenerator(output_dir_str)
    
    mod_suite = {}
    
    # Simple mod with basic blocks
    mod_suite["simple_blocks"] = generator.create_mod_jar(
        "simple_blocks", 
        blocks=["stone_block", "wood_block"],
        items=["stone_ingot"]
    )
    
    # Complex mod with multiple components
    mod_suite["complex_mod"] = generator.create_mod_jar(
        "complex_mod",
        blocks=["custom_ore", "custom_stone", "magic_block"],
        items=["magic_wand", "ore_fragment", "enchanted_gem"]
    )
    
    # Minimal mod for edge case testing
    mod_suite["minimal_mod"] = generator.create_mod_jar(
        "minimal_mod",
        blocks=["basic_block"],
        items=["basic_item"]
    )
    
    return mod_suite


# Convenience functions for backward compatibility
def create_test_jar(name: str = "test_mod") -> str:
    """Create a basic test JAR file.
    
    Args:
        name: Name of the JAR file
        
    Returns:
        Path to the created JAR file
    """
    generator = TestJarGenerator()
    return generator.create_mod_jar(name)


def get_test_fixtures_dir() -> str:
    """Get the path to the test fixtures directory.
    
    Returns:
        Path to test fixtures directory
    """
    return str(Path(__file__).parent)