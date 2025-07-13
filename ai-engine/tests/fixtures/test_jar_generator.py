"""
Test JAR Generator - Creates realistic test JAR files for different mod types
"""

import zipfile
import json
from pathlib import Path
from typing import Dict, List, Any


class TestJarGenerator:
    """Generator for creating realistic test JAR files for different mod scenarios."""
    
    @staticmethod
    def create_fabric_mod(mod_id: str, output_path: Path, blocks: List[str] = None, items: List[str] = None) -> Path:
        """Create a Fabric mod JAR file."""
        if blocks is None:
            blocks = ["copper_block"]
        if items is None:
            items = ["copper_ingot"]
        
        with zipfile.ZipFile(output_path, 'w') as jar:
            # Create fabric.mod.json
            fabric_manifest = {
                "schemaVersion": 1,
                "id": mod_id,
                "version": "1.0.0",
                "name": mod_id.replace('_', ' ').title(),
                "description": f"Test mod: {mod_id}",
                "authors": ["Test Author"],
                "environment": "*",
                "depends": {
                    "minecraft": "1.19.4",
                    "fabricloader": ">=0.14.0"
                }
            }
            jar.writestr("fabric.mod.json", json.dumps(fabric_manifest, indent=2))
            
            # Create main mod class
            main_class = f"""
package net.{mod_id};

import net.fabricmc.api.ModInitializer;
import net.minecraft.block.Block;
import net.minecraft.item.Item;
import net.minecraft.util.Identifier;
import net.minecraft.util.registry.Registry;

public class {mod_id.title().replace('_', '')}Mod implements ModInitializer {{
    public static final String MOD_ID = "{mod_id}";
    
    @Override
    public void onInitialize() {{
        // Register blocks
        {chr(10).join(f'        Registry.register(Registry.BLOCK, new Identifier(MOD_ID, "{block}"), new {block.title().replace("_", "")}Block());' for block in blocks)}
        
        // Register items
        {chr(10).join(f'        Registry.register(Registry.ITEM, new Identifier(MOD_ID, "{item}"), new {item.title().replace("_", "")}Item());' for item in items)}
    }}
}}
"""
            jar.writestr(f"net/{mod_id}/{mod_id.title().replace('_', '')}Mod.java", main_class)
            
            # Create block classes and assets
            for block in blocks:
                # Block Java class
                block_class = f"""
package net.{mod_id}.blocks;

import net.minecraft.block.Block;
import net.minecraft.block.Material;

public class {block.title().replace('_', '')}Block extends Block {{
    public {block.title().replace('_', '')}Block() {{
        super(Settings.of(Material.METAL).strength(3.0f, 6.0f));
    }}
}}
"""
                jar.writestr(f"net/{mod_id}/blocks/{block.title().replace('_', '')}Block.java", block_class)
                
                # Block texture (minimal PNG)
                png_data = b'\\x89PNG\\r\\n\\x1a\\n\\x00\\x00\\x00\\rIHDR\\x00\\x00\\x00\\x10\\x00\\x00\\x00\\x10\\x08\\x02\\x00\\x00\\x00\\x90\\x91h6\\x00\\x00\\x00\\x0bIDATx\\x9cc\\xf8\\x0f\\x00\\x00\\x01\\x00\\x01\\x00\\x18\\xdd\\x8d\\xb4\\x00\\x00\\x00\\x00IEND\\xaeB`\\x82'
                jar.writestr(f"assets/{mod_id}/textures/block/{block}.png", png_data)
                
                # Block model
                block_model = {
                    "parent": "minecraft:block/cube_all",
                    "textures": {
                        "all": f"{mod_id}:block/{block}"
                    }
                }
                jar.writestr(f"assets/{mod_id}/models/block/{block}.json", json.dumps(block_model, indent=2))
                
                # Block state
                block_state = {
                    "variants": {
                        "": {
                            "model": f"{mod_id}:block/{block}"
                        }
                    }
                }
                jar.writestr(f"assets/{mod_id}/blockstates/{block}.json", json.dumps(block_state, indent=2))
            
            # Create item classes and assets
            for item in items:
                # Item Java class
                item_class = f"""
package net.{mod_id}.items;

import net.minecraft.item.Item;

public class {item.title().replace('_', '')}Item extends Item {{
    public {item.title().replace('_', '')}Item() {{
        super(new Settings().maxCount(64));
    }}
}}
"""
                jar.writestr(f"net/{mod_id}/items/{item.title().replace('_', '')}Item.java", item_class)
                
                # Item texture
                jar.writestr(f"assets/{mod_id}/textures/item/{item}.png", png_data)
                
                # Item model
                item_model = {
                    "parent": "minecraft:item/generated",
                    "textures": {
                        "layer0": f"{mod_id}:item/{item}"
                    }
                }
                jar.writestr(f"assets/{mod_id}/models/item/{item}.json", json.dumps(item_model, indent=2))
        
        return output_path
    
    @staticmethod
    def create_forge_mod(mod_id: str, output_path: Path, blocks: List[str] = None) -> Path:
        """Create a Forge mod JAR file."""
        if blocks is None:
            blocks = ["copper_block"]
        
        with zipfile.ZipFile(output_path, 'w') as jar:
            # Create mods.toml
            mods_toml = f"""
modLoader="javafml"
loaderVersion="[40,)"
license="MIT"
[[mods]]
modId="{mod_id}"
version="1.0.0"
displayName="{mod_id.replace('_', ' ').title()}"
description="Test Forge mod: {mod_id}"
authors="Test Author"
"""
            jar.writestr("META-INF/mods.toml", mods_toml)
            
            # Create main mod class (Forge style)
            main_class = f"""
package net.{mod_id};

import net.minecraft.world.level.block.Block;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;

@Mod("{mod_id}")
public class {mod_id.title().replace('_', '')}Mod {{
    public static final String MOD_ID = "{mod_id}";
    
    public static final DeferredRegister<Block> BLOCKS = DeferredRegister.create(ForgeRegistries.BLOCKS, MOD_ID);
    
    public {mod_id.title().replace('_', '')}Mod() {{
        IEventBus modEventBus = FMLJavaModLoadingContext.get().getModEventBus();
        BLOCKS.register(modEventBus);
    }}
}}
"""
            jar.writestr(f"net/{mod_id}/{mod_id.title().replace('_', '')}Mod.java", main_class)
            
            # Create blocks
            for block in blocks:
                # Block texture
                png_data = b'\\x89PNG\\r\\n\\x1a\\n\\x00\\x00\\x00\\rIHDR\\x00\\x00\\x00\\x10\\x00\\x00\\x00\\x10\\x08\\x02\\x00\\x00\\x00\\x90\\x91h6\\x00\\x00\\x00\\x0bIDATx\\x9cc\\xf8\\x0f\\x00\\x00\\x01\\x00\\x01\\x00\\x18\\xdd\\x8d\\xb4\\x00\\x00\\x00\\x00IEND\\xaeB`\\x82'
                jar.writestr(f"assets/{mod_id}/textures/block/{block}.png", png_data)
        
        return output_path
    
    @staticmethod
    def create_bukkit_plugin(plugin_id: str, output_path: Path) -> Path:
        """Create a Bukkit plugin JAR file."""
        with zipfile.ZipFile(output_path, 'w') as jar:
            # Create plugin.yml
            plugin_yml = f"""
name: {plugin_id.title().replace('_', '')}
version: 1.0.0
main: net.{plugin_id}.{plugin_id.title().replace('_', '')}Plugin
api-version: 1.19
description: Test Bukkit plugin: {plugin_id}
author: Test Author
"""
            jar.writestr("plugin.yml", plugin_yml)
            
            # Create main plugin class
            main_class = f"""
package net.{plugin_id};

import org.bukkit.plugin.java.JavaPlugin;

public class {plugin_id.title().replace('_', '')}Plugin extends JavaPlugin {{
    @Override
    public void onEnable() {{
        getLogger().info("{plugin_id} has been enabled!");
    }}
    
    @Override
    public void onDisable() {{
        getLogger().info("{plugin_id} has been disabled!");
    }}
}}
"""
            jar.writestr(f"net/{plugin_id}/{plugin_id.title().replace('_', '')}Plugin.java", main_class)
        
        return output_path
    
    @staticmethod
    def create_complex_mod(mod_id: str, output_path: Path, complexity_level: str = "medium") -> Path:
        """Create a complex mod with multiple features."""
        features = {
            "simple": {
                "blocks": ["copper_block"],
                "items": ["copper_ingot"],
                "entities": [],
                "dimensions": []
            },
            "medium": {
                "blocks": ["copper_block", "bronze_block", "steel_block"],
                "items": ["copper_ingot", "bronze_ingot", "steel_ingot", "hammer"],
                "entities": ["copper_golem"],
                "dimensions": []
            },
            "complex": {
                "blocks": ["copper_block", "bronze_block", "steel_block", "furnace_block", "crusher_block"],
                "items": ["copper_ingot", "bronze_ingot", "steel_ingot", "hammer", "wrench", "gear"],
                "entities": ["copper_golem", "mining_robot"],
                "dimensions": ["copper_dimension"]
            }
        }
        
        config = features.get(complexity_level, features["medium"])
        
        with zipfile.ZipFile(output_path, 'w') as jar:
            # Create fabric.mod.json
            fabric_manifest = {
                "schemaVersion": 1,
                "id": mod_id,
                "version": "1.0.0",
                "name": f"Complex {mod_id.replace('_', ' ').title()}",
                "description": f"Complex test mod with {complexity_level} features",
                "environment": "*",
                "depends": {"minecraft": "1.19.4", "fabricloader": ">=0.14.0"}
            }
            jar.writestr("fabric.mod.json", json.dumps(fabric_manifest, indent=2))
            
            # Add blocks
            for block in config["blocks"]:
                png_data = b'\\x89PNG\\r\\n\\x1a\\n\\x00\\x00\\x00\\rIHDR\\x00\\x00\\x00\\x10\\x00\\x00\\x00\\x10\\x08\\x02\\x00\\x00\\x00\\x90\\x91h6\\x00\\x00\\x00\\x0bIDATx\\x9cc\\xf8\\x0f\\x00\\x00\\x01\\x00\\x01\\x00\\x18\\xdd\\x8d\\xb4\\x00\\x00\\x00\\x00IEND\\xaeB`\\x82'
                jar.writestr(f"assets/{mod_id}/textures/block/{block}.png", png_data)
            
            # Add items
            for item in config["items"]:
                jar.writestr(f"assets/{mod_id}/textures/item/{item}.png", png_data)
            
            # Add entities (textures only for MVP)
            for entity in config["entities"]:
                jar.writestr(f"assets/{mod_id}/textures/entity/{entity}.png", png_data)
            
            # Add dimensions (structure files)
            for dimension in config["dimensions"]:
                dimension_json = {
                    "type": f"{mod_id}:{dimension}",
                    "generator": {
                        "type": "minecraft:noise",
                        "biome_source": {
                            "type": "minecraft:fixed",
                            "biome": f"{mod_id}:copper_biome"
                        }
                    }
                }
                jar.writestr(f"data/{mod_id}/dimension/{dimension}.json", json.dumps(dimension_json, indent=2))
        
        return output_path


# Helper functions for integration tests
def create_test_mod_suite(output_dir: Path) -> Dict[str, Path]:
    """Create a suite of test mods for comprehensive testing."""
    output_dir.mkdir(parents=True, exist_ok=True)
    generator = TestJarGenerator()
    
    test_mods = {}
    
    # Fabric mods
    test_mods["simple_fabric"] = generator.create_fabric_mod(
        "simple_fabric", output_dir / "simple_fabric.jar", 
        blocks=["copper_block"], items=["copper_ingot"]
    )
    
    test_mods["complex_fabric"] = generator.create_fabric_mod(
        "complex_fabric", output_dir / "complex_fabric.jar",
        blocks=["copper_block", "bronze_block", "steel_block"],
        items=["copper_ingot", "bronze_ingot", "steel_ingot", "hammer"]
    )
    
    # Forge mod
    test_mods["forge_mod"] = generator.create_forge_mod(
        "forge_mod", output_dir / "forge_mod.jar",
        blocks=["copper_block", "tin_block"]
    )
    
    # Bukkit plugin
    test_mods["bukkit_plugin"] = generator.create_bukkit_plugin(
        "bukkit_plugin", output_dir / "bukkit_plugin.jar"
    )
    
    # Complex mods of different sizes
    for complexity in ["simple", "medium", "complex"]:
        test_mods[f"{complexity}_mod"] = generator.create_complex_mod(
            f"{complexity}_mod", output_dir / f"{complexity}_mod.jar", complexity
        )
    
    return test_mods


if __name__ == "__main__":
    # Generate test suite
    import tempfile
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        test_mods = create_test_mod_suite(temp_path / "test_mods")
        
        print("🎮 Generated Test Mod Suite:")
        for mod_name, mod_path in test_mods.items():
            size = mod_path.stat().st_size
            print(f"  ✅ {mod_name}: {size:,} bytes")
        
        print(f"\\n📁 Total mods created: {len(test_mods)}")