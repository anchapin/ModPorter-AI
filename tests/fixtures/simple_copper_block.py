"""
Script to create a simple test JAR file for MVP testing.
This creates the fixture mentioned in Issue #174.

Creates a comprehensive test fixture with:
- Proper mod metadata (fabric.mod.json)
- Block texture asset
- Java class structure
- Expected conversion outputs

For Issue #174: Add sample .jar fixture for testing
"""

import zipfile
import json
from pathlib import Path


def create_simple_copper_block_jar():
    """
    Create a simple test JAR with a polished copper block.
    
    This fixture is designed to test the complete ModPorter AI pipeline:
    1. JavaAnalyzerAgent can extract registry name and texture path
    2. Conversion pipeline can generate Bedrock blocks
    3. Packager can create .mcaddon files
    
    Returns:
        Path: Path to the created JAR file
    """
    
    # Ensure fixtures directory exists
    fixtures_dir = Path(__file__).parent
    fixtures_dir.mkdir(exist_ok=True)
    
    jar_path = fixtures_dir / "simple_copper_block.jar"
    
    with zipfile.ZipFile(jar_path, 'w') as zf:
        # Add fabric.mod.json with complete metadata
        fabric_mod = {
            "schemaVersion": 1,
            "id": "simple_copper",
            "version": "1.0.0",
            "name": "Simple Copper Block",
            "description": "A simple mod that adds a polished copper block",
            "authors": ["ModPorter AI"],
            "license": "MIT",
            "environment": "*",
            "entrypoints": {
                "main": ["com.example.simple_copper.SimpleCopperMod"]
            },
            "depends": {
                "fabricloader": ">=0.14.0",
                "minecraft": "~1.19.2"
            }
        }
        zf.writestr('fabric.mod.json', json.dumps(fabric_mod, indent=2))
        
        # Add block texture (16x16 PNG header for more realistic testing)
        png_header = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10'
            b'\x08\x06\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x04gAMA\x00\x00\xb1\x8f'
            b'\x0b\xfca\x05\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00 cHRM'
            b'z%\x00\x00\x80\x83\x00\x00\xf9\x7f\x00\x00\x80\xe9\x00\x00u0\x00\x00'
            b'\xea`\x00\x00:\x98\x00\x00\x17o\x92_\xc5F\x00\x00\x00\tpHYs\x00\x00\x0b'
            b'\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00IEND\xaeB`\x82'
        )
        zf.writestr('assets/simple_copper/textures/block/polished_copper.png', png_header)
        
        # Add Java source file for more realistic testing
        java_source = '''package com.example.simple_copper;

import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.SoundType;
import net.minecraft.world.level.material.Material;
import net.minecraft.world.level.block.state.BlockBehaviour.Properties;

/**
 * Simple polished copper block for testing ModPorter AI conversion.
 * Registry name should be extracted as "polished_copper"
 */
public class PolishedCopperBlock extends Block {
    
    public PolishedCopperBlock() {
        super(Properties.of(Material.METAL)
            .strength(3.0F, 6.0F)
            .sound(SoundType.COPPER)
            .requiresCorrectToolForDrops());
    }
}
'''
        zf.writestr('com/example/simple_copper/PolishedCopperBlock.java', java_source)
        
        # Add compiled class (minimal class file structure for testing)
        class_data = (
            b'\xca\xfe\xba\xbe\x00\x00\x00:\x00\x1f\x0a\x00\x06\x00\x11\t\x00\x05\x00'
            b'\x12\x0a\x00\x13\x00\x14\x07\x00\x15\x07\x00\x16\x01\x00\x06<init>\x01'
            b'\x00\x03()V\x01\x00\x04Code'
        )
        zf.writestr('com/example/simple_copper/PolishedCopperBlock.class', class_data)
        
        # Add mod main class
        main_java = '''package com.example.simple_copper;

import net.fabricmc.api.ModInitializer;
import net.minecraft.core.Registry;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.level.block.Block;

public class SimpleCopperMod implements ModInitializer {
    
    public static final Block POLISHED_COPPER_BLOCK = new PolishedCopperBlock();
    
    @Override
    public void onInitialize() {
        Registry.register(Registry.BLOCK, 
                         new ResourceLocation("simple_copper", "polished_copper"), 
                         POLISHED_COPPER_BLOCK);
    }
}
'''
        zf.writestr('com/example/simple_copper/SimpleCopperMod.java', main_java)
        
        # Add manifest
        manifest = '''Manifest-Version: 1.0
Created-By: ModPorter AI Test Suite
Specification-Title: Simple Copper Block
Specification-Version: 1.0.0
Implementation-Title: simple_copper
Implementation-Version: 1.0.0
'''
        zf.writestr('META-INF/MANIFEST.MF', manifest)
        
        # Add mixins.json for completeness
        mixins_config = {
            "required": True,
            "package": "com.example.simple_copper.mixins",
            "compatibilityLevel": "JAVA_17",
            "refmap": "simple_copper.refmap.json",
            "mixins": [],
            "client": [],
            "server": [],
            "minVersion": "0.8"
        }
        zf.writestr('simple_copper.mixins.json', json.dumps(mixins_config, indent=2))
        
        # Add pack.mcmeta for additional metadata
        pack_mcmeta = {
            "pack": {
                "pack_format": 9,
                "description": "Simple Copper Block test fixture"
            }
        }
        zf.writestr('pack.mcmeta', json.dumps(pack_mcmeta, indent=2))
        
    print(f"Created comprehensive test JAR: {jar_path}")
    print(f"JAR size: {jar_path.stat().st_size} bytes")
    
    # Verify the JAR was created correctly
    with zipfile.ZipFile(jar_path, 'r') as zf:
        files = zf.namelist()
        print(f"JAR contains {len(files)} files:")
        for file in sorted(files):
            print(f"  - {file}")
            
    return jar_path


def get_expected_analysis_result():
    """
    Return the expected JavaAnalyzerAgent analysis result for this fixture.
    
    This serves as the test oracle for automated testing.
    """
    return {
        "success": True,
        "registry_name": "simple_copper:polished_copper",
        "texture_path": "assets/simple_copper/textures/block/polished_copper.png",
        "errors": []
    }


def get_expected_bedrock_block():
    """
    Return the expected Bedrock block definition for this fixture.
    """
    return {
        "format_version": "1.16.100",
        "minecraft:block": {
            "description": {
                "identifier": "simple_copper:polished_copper"
            },
            "components": {
                "minecraft:destroy_time": 3.0,
                "minecraft:explosion_resistance": 6.0,
                "minecraft:material_instances": {
                    "*": {
                        "texture": "polished_copper"
                    }
                }
            }
        }
    }


if __name__ == "__main__":
    jar_path = create_simple_copper_block_jar()
    
    print("\n" + "="*60)
    print("TEST FIXTURE CREATED SUCCESSFULLY")
    print("="*60)
    print(f"Location: {jar_path}")
    print("Use this fixture in tests to validate:")
    print("1. JavaAnalyzerAgent registry name and texture extraction")
    print("2. End-to-end conversion pipeline")
    print("3. .mcaddon package generation")
    print("\nExpected analysis result:")
    print(json.dumps(get_expected_analysis_result(), indent=2))
