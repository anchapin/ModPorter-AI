import logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

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
from PIL import Image
import os


def create_simple_copper_block_jar():
    """
    Create a simple test JAR with a polished copper block.
    
    This fixture is designed to test the complete PortKit pipeline:
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
    
    # Create a temporary directory for building the JAR contents
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create META-INF first
        meta_dir = os.path.join(tmpdir, "META-INF")
        os.makedirs(meta_dir, exist_ok=True)
        with open(os.path.join(meta_dir, "MANIFEST.MF"), 'w') as f:
            f.write("""Manifest-Version: 1.0
Created-By: PortKit Test Suite
Specification-Title: Simple Copper Block
Specification-Version: 1.0.0
Implementation-Title: simple_copper
Implementation-Version: 1.0.0
""")
        
        # Create a valid 16x16 PNG block texture (copper color)
        textures_dir = os.path.join(tmpdir, "assets", "simple_copper", "textures", "block")
        os.makedirs(textures_dir, exist_ok=True)
        img = Image.new('RGBA', (16, 16), (184, 115, 67, 255))  # Copper color
        img.save(os.path.join(textures_dir, "polished_copper.png"), "PNG")
        
        # Add animation mcmeta file for the block texture
        mcmeta_path = os.path.join(textures_dir, "polished_copper.png.mcmeta")
        with open(mcmeta_path, 'w') as f:
            json.dump({
                "animation": {
                    "frametime": 2,
                    "frames": [0, 1, 2]
                }
            }, f, indent=2)
        
        # Create item texture (copper ingot)
        items_dir = os.path.join(tmpdir, "assets", "simple_copper", "textures", "item")
        os.makedirs(items_dir, exist_ok=True)
        img_item = Image.new('RGBA', (16, 16), (255, 165, 0, 255))  # Orange
        img_item.save(os.path.join(items_dir, "copper_ingot.png"), "PNG")
        
        # Add fabric.mod.json with complete metadata
        fabric_mod = {
            "schemaVersion": 1,
            "id": "simple_copper",
            "version": "1.0.0",
            "name": "Simple Copper Block",
            "description": "A simple mod that adds a polished copper block",
            "authors": ["PortKit"],
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
        with open(os.path.join(tmpdir, "fabric.mod.json"), 'w') as f:
            json.dump(fabric_mod, f, indent=2)
        
        # Add Java source file for more realistic testing
        java_source = '''package com.example.simple_copper;

import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.SoundType;
import net.minecraft.world.level.material.Material;
import net.minecraft.world.level.block.state.BlockBehaviour.Properties;

/**
 * Simple polished copper block for testing PortKit conversion.
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
        java_dir = os.path.join(tmpdir, "com", "example", "simple_copper")
        os.makedirs(java_dir, exist_ok=True)
        with open(os.path.join(java_dir, "PolishedCopperBlock.java"), 'w') as f:
            f.write(java_source)
        
        # Add compiled class (minimal class file structure for testing)
        class_data = (
            b'\xca\xfe\xba\xbe\x00\x00\x00:\x00\x1f\x0a\x00\x06\x00\x11\t\x00\x05\x00'
            b'\x12\x0a\x00\x13\x00\x14\x07\x00\x15\x07\x00\x16\x01\x00\x06<init>\x01'
            b'\x00\x03()V\x01\x00\x04Code'
        )
        with open(os.path.join(java_dir, "PolishedCopperBlock.class"), 'wb') as f:
            f.write(class_data)
        
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
        with open(os.path.join(java_dir, "SimpleCopperMod.java"), 'w') as f:
            f.write(main_java)
        
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
        with open(os.path.join(tmpdir, "simple_copper.mixins.json"), 'w') as f:
            json.dump(mixins_config, f, indent=2)
        
        # Add pack.mcmeta for additional metadata
        pack_mcmeta = {
            "pack": {
                "pack_format": 9,
                "description": "Simple Copper Block test fixture"
            }
        }
        with open(os.path.join(tmpdir, "pack.mcmeta"), 'w') as f:
            json.dump(pack_mcmeta, f, indent=2)
        
        # Create the JAR file
        with zipfile.ZipFile(jar_path, 'w') as zf:
            for root, dirs, files in os.walk(tmpdir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, tmpdir)
                    zf.write(file_path, arcname)
        
    logger.info(f"Created comprehensive test JAR: {jar_path}")
    logger.info(f"JAR size: {jar_path.stat().st_size} bytes")
    
    # Verify the JAR was created correctly
    with zipfile.ZipFile(jar_path, 'r') as zf:
        files = zf.namelist()
        logger.info(f"JAR contains {len(files)} files:")
        for file in sorted(files):
            logger.info(f"  - {file}")
            
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
    
    logger.info("\n" + "="*60)
    logger.info("TEST FIXTURE CREATED SUCCESSFULLY")
    logger.info("="*60)
    logger.info(f"Location: {jar_path}")
    logger.info("Use this fixture in tests to validate:")
    logger.info("1. JavaAnalyzerAgent registry name and texture extraction")
    logger.info("2. End-to-end conversion pipeline")
    logger.info("3. .mcaddon package generation")
    logger.info("\nExpected analysis result:")
    logger.info(json.dumps(get_expected_analysis_result(), indent=2))
