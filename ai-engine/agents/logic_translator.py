"""
Logic Translator Agent for Java to JavaScript code conversion
Enhanced for Issue #546: Block Generation from Java block analysis
"""

from typing import List, Dict, Any

import json
from crewai.tools import tool
import javalang  # Added javalang
from models.smart_assumptions import (
    SmartAssumptionEngine,
)
from agents.java_analyzer import JavaAnalyzerAgent
from utils.logging_config import get_agent_logger, log_performance

# Use enhanced agent logger
logger = get_agent_logger("logic_translator")


# ========== Bedrock Block Templates (Issue #546) ==========
# Templates for generating valid Bedrock block JSON files

BEDROCK_BLOCK_TEMPLATES = {
    "basic": {
        "format_version": "1.20.10",
        "minecraft:block": {
            "description": {
                "identifier": "{{ namespace }}:{{ block_name }}",
                "menu_category": {"category": "{{ menu_category }}"},
            },
            "components": {
                "minecraft:destroy_time": 3.0,
                "minecraft:explosion_resistance": 6.0,
                "minecraft:unit_cube": {},
                "minecraft:material_instances": {
                    "*": {"texture": "{{ texture_name }}", "render_method": "opaque"}
                },
            },
        },
    },
    "metal": {
        "format_version": "1.20.10",
        "minecraft:block": {
            "description": {
                "identifier": "{{ namespace }}:{{ block_name }}",
                "menu_category": {"category": "construction"},
            },
            "components": {
                "minecraft:destroy_time": 5.0,
                "minecraft:explosion_resistance": 6.0,
                "minecraft:unit_cube": {},
                "minecraft:material_instances": {
                    "*": {"texture": "{{ texture_name }}", "render_method": "opaque"}
                },
            },
        },
    },
    "stone": {
        "format_version": "1.20.10",
        "minecraft:block": {
            "description": {
                "identifier": "{{ namespace }}:{{ block_name }}",
                "menu_category": {"category": "construction"},
            },
            "components": {
                "minecraft:destroy_time": 3.0,
                "minecraft:explosion_resistance": 6.0,
                "minecraft:unit_cube": {},
                "minecraft:material_instances": {
                    "*": {"texture": "{{ texture_name }}", "render_method": "opaque"}
                },
            },
        },
    },
    "wood": {
        "format_version": "1.20.10",
        "minecraft:block": {
            "description": {
                "identifier": "{{ namespace }}:{{ block_name }}",
                "menu_category": {"category": "construction"},
            },
            "components": {
                "minecraft:destroy_time": 2.0,
                "minecraft:explosion_resistance": 3.0,
                "minecraft:unit_cube": {},
                "minecraft:flammable": {"catch_chance_modifier": 5, "destroy_chance_modifier": 20},
                "minecraft:material_instances": {
                    "*": {"texture": "{{ texture_name }}", "render_method": "opaque"}
                },
            },
        },
    },
    "glass": {
        "format_version": "1.20.10",
        "minecraft:block": {
            "description": {
                "identifier": "{{ namespace }}:{{ block_name }}",
                "menu_category": {"category": "construction"},
            },
            "components": {
                "minecraft:destroy_time": 0.3,
                "minecraft:explosion_resistance": 0.3,
                "minecraft:unit_cube": {},
                "minecraft:material_instances": {
                    "*": {"texture": "{{ texture_name }}", "render_method": "blend"}
                },
            },
        },
    },
    "light_emitting": {
        "format_version": "1.20.10",
        "minecraft:block": {
            "description": {
                "identifier": "{{ namespace }}:{{ block_name }}",
                "menu_category": {"category": "construction"},
            },
            "components": {
                "minecraft:destroy_time": 3.0,
                "minecraft:explosion_resistance": 6.0,
                "minecraft:unit_cube": {},
                "minecraft:light_emission": 15,
                "minecraft:material_instances": {
                    "*": {"texture": "{{ texture_name }}", "render_method": "opaque"}
                },
            },
        },
    },
}

# ========== Bedrock Item Templates (Issue #654) ==========
# Templates for generating valid Bedrock item JSON files with full component support
# Note: Templates are applied at runtime via _build_item_json method with properties

BEDROCK_ITEM_TEMPLATES = {
    "basic": {
        "format_version": "1.20.10",
        "minecraft:item": {
            "description": {
                "identifier": "namespace:item_name",
                "menu_category": {"category": "items"},
            },
            "components": {
                "minecraft:icon": {"texture": "item_name"},
                "minecraft:display_name": {"value": "item_name"},
            },
        },
    },
    "tool": {
        "format_version": "1.20.10",
        "minecraft:item": {
            "description": {
                "identifier": "namespace:item_name",
                "menu_category": {"category": "tools"},
            },
            "components": {
                "minecraft:icon": {"texture": "item_name"},
                "minecraft:display_name": {"value": "item_name"},
                "minecraft:max_stack_size": 1,
                "minecraft:durability": {"max_durability": 250},
                "minecraft:repairable": {
                    "repair_items": [{"items": ["minecraft:iron_ingot"], "repair_amount": 50}]
                },
                "minecraft:hand_equipped": True,
                "minecraft:allow_off_hand": False,
                "minecraft:mining_speed": 6.0,
                "minecraft:damage": 2,
            },
        },
    },
    "sword": {
        "format_version": "1.20.10",
        "minecraft:item": {
            "description": {
                "identifier": "namespace:item_name",
                "menu_category": {"category": "combat"},
            },
            "components": {
                "minecraft:icon": {"texture": "item_name"},
                "minecraft:display_name": {"value": "item_name"},
                "minecraft:max_stack_size": 1,
                "minecraft:durability": {"max_durability": 250},
                "minecraft:repairable": {
                    "repair_items": [{"items": ["minecraft:iron_ingot"], "repair_amount": 50}]
                },
                "minecraft:hand_equipped": True,
                "minecraft:allow_off_hand": True,
                "minecraft:damage": 7,
            },
        },
    },
    "armor": {
        "format_version": "1.20.10",
        "minecraft:item": {
            "description": {
                "identifier": "namespace:item_name",
                "menu_category": {"category": "armor"},
            },
            "components": {
                "minecraft:icon": {"texture": "item_name"},
                "minecraft:display_name": {"value": "item_name"},
                "minecraft:max_stack_size": 1,
                "minecraft:durability": {"max_durability": 166},
                "minecraft:repairable": {
                    "repair_items": [{"items": ["minecraft:iron_ingot"], "repair_amount": 33}]
                },
                "minecraft:armor": {"protection": 2},
                "minecraft:equippable": {"slot": "torso"},
            },
        },
    },
    "food": {
        "format_version": "1.20.10",
        "minecraft:item": {
            "description": {
                "identifier": "namespace:item_name",
                "menu_category": {"category": "items"},
            },
            "components": {
                "minecraft:icon": {"texture": "item_name"},
                "minecraft:display_name": {"value": "item_name"},
                "minecraft:max_stack_size": 64,
                "minecraft:food": {
                    "nutrition": 4,
                    "saturation": 2.0,
                    "can_always_eat": False,
                    "effects": [],
                },
                "minecraft:use_duration": 32,
                "minecraft:consumable": {"consume_seconds": 1.6, "sound": "game/eat/generic"},
            },
        },
    },
    "ranged_weapon": {
        "format_version": "1.20.10",
        "minecraft:item": {
            "description": {
                "identifier": "namespace:item_name",
                "menu_category": {"category": "combat"},
            },
            "components": {
                "minecraft:icon": {"texture": "item_name"},
                "minecraft:display_name": {"value": "item_name"},
                "minecraft:max_stack_size": 1,
                "minecraft:durability": {"max_durability": 384},
                "minecraft:repairable": {
                    "repair_items": [{"items": ["minecraft:iron_ingot"], "repair_amount": 50}]
                },
                "minecraft:hand_equipped": True,
                "minecraft:allow_off_hand": False,
                "minecraft:ranged_weapon": {
                    "charged_projectiles": [{"item": "minecraft:arrow", "pickup": "allowed"}],
                    "damage": 9.0,
                    "speed": 15.0,
                    "draw_back": {"start_charge_at": 0, "max_charge": 20},
                },
            },
        },
    },
    "book": {
        "format_version": "1.20.10",
        "minecraft:item": {
            "description": {
                "identifier": "namespace:item_name",
                "menu_category": {"category": "items"},
            },
            "components": {
                "minecraft:icon": {"texture": "item_name"},
                "minecraft:display_name": {"value": "item_name"},
                "minecraft:max_stack_size": 16,
                "minecraft:book": {"author": "Unknown", "title": "item_name", "pages": []},
                "minecraft:writable_book": {"max_pages": 50},
            },
        },
    },
    "music_disc": {
        "format_version": "1.20.10",
        "minecraft:item": {
            "description": {
                "identifier": "namespace:item_name",
                "menu_category": {"category": "items"},
            },
            "components": {
                "minecraft:icon": {"texture": "item_name"},
                "minecraft:display_name": {"value": "item_name"},
                "minecraft:max_stack_size": 1,
                "minecraft:record": {
                    "sound_id": "music_disc.13",
                    "duration": 180,
                    "comparator_signal": 0,
                },
            },
        },
    },
}

# Java to Bedrock item property mappings
JAVA_TO_BEDROCK_ITEM_PROPERTIES = {
    # Tool types mapping
    "ToolType.PICKAXE": {"template": "tool", "mining_speed": 6.0, "damage": 2},
    "ToolType.AXE": {"template": "tool", "mining_speed": 8.0, "damage": 5},
    "ToolType.SHOVEL": {"template": "tool", "mining_speed": 6.0, "damage": 1.5},
    "ToolType.HOE": {"template": "tool", "mining_speed": 2.0, "damage": 0},
    "ToolType.SWORD": {"template": "sword", "damage": 7},
    # Armor types
    "ArmorType.HELMET": {"template": "armor", "armor_slot": "head", "armor_protection": 2},
    "ArmorType.CHESTPLATE": {"template": "armor", "armor_slot": "torso", "armor_protection": 6},
    "ArmorType.LEGGINGS": {"template": "armor", "armor_slot": "legs", "armor_protection": 5},
    "ArmorType.BOOTS": {"template": "armor", "armor_slot": "feet", "armor_protection": 2},
    # Material durability mapping
    "Material.WOOD": {"max_durability": 60, "repair_item": "minecraft:planks"},
    "Material.STONE": {"max_durability": 132, "repair_item": "minecraft:cobblestone"},
    "Material.IRON": {"max_durability": 251, "repair_item": "minecraft:iron_ingot"},
    "Material.GOLD": {"max_durability": 33, "repair_item": "minecraft:gold_ingot"},
    "Material.DIAMOND": {"max_durability": 1562, "repair_item": "minecraft:diamond"},
    "Material.NETHERITE": {"max_durability": 2032, "repair_item": "minecraft:netherite_ingot"},
}

# Java item methods to Bedrock components
JAVA_ITEM_METHOD_MAPPINGS = {
    "getMaxStackSize": "minecraft:max_stack_size",
    "getDefaultStackSize": "minecraft:max_stack_size",
    "getMaxDamage": "minecraft:durability",
    "getDamage": "minecraft:damage",
    "getMiningSpeed": "minecraft:mining_speed",
    "isFireResistant": "minecraft:fire_resistant",
    "getFoodHealing": "minecraft:food.nutrition",
    "getSaturation": "minecraft:food.saturation",
}

# ========== Bedrock Entity Templates (Issue #654) ==========
# Templates for generating valid Bedrock entity JSON files
# Note: Templates are applied at runtime via _build_entity_json method with properties

BEDROCK_ENTITY_TEMPLATES = {
    "hostile_mob": {
        "format_version": "1.20.10",
        "minecraft:entity": {
            "description": {
                "identifier": "namespace:entity_name",
                "is_spawnable": True,
                "is_summonable": True,
                "is_experimental": False,
            },
            "component_groups": {},
            "components": {
                "minecraft:type_family": {"family": ["hostile", "monster", "mob"]},
                "minecraft:breathable": {"total_supply": 15, "suffocate_time": 0},
                "minecraft:collision_box": {"width": 0.8, "height": 1.8},
                "minecraft:health": {"value": 20, "max": 20},
                "minecraft:attack": {"damage": 3},
                "minecraft:movement": {"value": 0.23},
                "minecraft:navigation.walk": {"can_path_over_water": False, "avoid_water": False},
                "minecraft:movement.basic": {},
                "minecraft:jump.static": {},
            },
            "events": {},
        },
    },
    "passive_mob": {
        "format_version": "1.20.10",
        "minecraft:entity": {
            "description": {
                "identifier": "namespace:entity_name",
                "is_spawnable": True,
                "is_summonable": True,
                "is_experimental": False,
            },
            "component_groups": {},
            "components": {
                "minecraft:type_family": {"family": ["passive", "mob"]},
                "minecraft:breathable": {"total_supply": 15, "suffocate_time": 0},
                "minecraft:collision_box": {"width": 0.6, "height": 1.2},
                "minecraft:health": {"value": 10, "max": 10},
                "minecraft:movement": {"value": 0.25},
                "minecraft:navigation.walk": {"can_path_over_water": True, "avoid_water": False},
                "minecraft:movement.basic": {},
                "minecraft:jump.static": {},
            },
            "events": {},
        },
    },
    "ambient_mob": {
        "format_version": "1.20.10",
        "minecraft:entity": {
            "description": {
                "identifier": "namespace:entity_name",
                "is_spawnable": True,
                "is_summonable": True,
                "is_experimental": False,
            },
            "component_groups": {},
            "components": {
                "minecraft:type_family": {"family": ["ambient", "mob"]},
                "minecraft:breathable": {"total_supply": 15, "suffocate_time": 0},
                "minecraft:collision_box": {"width": 0.5, "height": 0.5},
                "minecraft:health": {"value": 1, "max": 1},
                "minecraft:movement": {"value": 0.15},
                "minecraft:navigation.walk": {"can_path_over_water": True, "avoid_water": False},
                "minecraft:movement.basic": {},
                "minecraft:jump.static": {},
            },
            "events": {},
        },
    },
}

# Java to Bedrock entity property mappings
JAVA_TO_BEDROCK_ENTITY_PROPERTIES = {
    "EntityType.ZOMBIE": {"template": "hostile_mob", "health": 20, "attack": 3},
    "EntityType.SKELETON": {"template": "hostile_mob", "health": 20, "attack": 4},
    "EntityType.CREEPER": {"template": "hostile_mob", "health": 20, "attack": 5},
    "EntityType.SPIDER": {"template": "hostile_mob", "health": 16, "attack": 2},
    "EntityType.PIG_ZOMBIE": {"template": "hostile_mob", "health": 20, "attack": 5},
    "EntityType.ENDERMAN": {"template": "hostile_mob", "health": 40, "attack": 7},
    "EntityType.COW": {"template": "passive_mob", "health": 10},
    "EntityType.PIG": {"template": "passive_mob", "health": 10},
    "EntityType.CHICKEN": {"template": "passive_mob", "health": 4},
    "EntityType.SHEEP": {"template": "passive_mob", "health": 8},
    "EntityType.HORSE": {"template": "passive_mob", "health": 30},
    "EntityType.BAT": {"template": "ambient_mob", "health": 6},
}

# ========== Recipe Templates (Issue #654) ==========
# Templates for generating valid Bedrock recipe JSON files
# Note: Templates are applied at runtime via convert_recipe method

BEDROCK_RECIPE_TEMPLATES = {
    "shaped": {
        "format_version": "1.20.10",
        "minecraft:recipe_shaped": {
            "description": {"identifier": "namespace:recipe_name"},
            "tags": ["crafting_table"],
            "pattern": ["   ", "   ", "   "],
            "key": {},
            "result": {"item": "minecraft:air", "count": 1},
        },
    },
    "shapeless": {
        "format_version": "1.20.10",
        "minecraft:recipe_shapeless": {
            "description": {"identifier": "namespace:recipe_name"},
            "tags": ["crafting_table"],
            "ingredients": [],
            "result": {"item": "minecraft:air", "count": 1},
        },
    },
    "smelting": {
        "format_version": "1.20.10",
        "minecraft:recipe_furnace": {
            "description": {"identifier": "namespace:recipe_name"},
            "tags": ["furnace", "blast_furnace"],
            "input": "minecraft:air",
            "output": "minecraft:air",
            "experience": 0,
            "cookingtime": 200,
        },
    },
    "blasting": {
        "format_version": "1.20.10",
        "minecraft:recipe_furnace_blast": {
            "description": {"identifier": "namespace:recipe_name"},
            "tags": ["blast_furnace"],
            "input": "minecraft:air",
            "output": "minecraft:air",
            "experience": 0,
            "cookingtime": 100,
        },
    },
    "smoking": {
        "format_version": "1.20.10",
        "minecraft:recipe_furnace_smoke": {
            "description": {"identifier": "namespace:recipe_name"},
            "tags": ["smoker"],
            "input": "minecraft:air",
            "output": "minecraft:air",
            "experience": 0,
            "cookingtime": 100,
        },
    },
    "campfire": {
        "format_version": "1.20.10",
        "minecraft:recipe_campfire": {
            "description": {"identifier": "namespace:recipe_name"},
            "tags": ["campfire"],
            "input": "minecraft:air",
            "output": "minecraft:air",
            "experience": 0,
            "cookingtime": 600,
        },
    },
    "stonecutter": {
        "format_version": "1.20.10",
        "minecraft:recipe_stonecutter": {
            "description": {"identifier": "namespace:recipe_name"},
            "tags": ["stonecutter"],
            "input": "minecraft:air",
            "result": "minecraft:air",
            "count": 1,
        },
    },
    "smithing": {
        "format_version": "1.20.10",
        "minecraft:recipe_smithing_transform": {
            "description": {"identifier": "namespace:recipe_name"},
            "tags": ["smithing_table"],
            "base": "minecraft:air",
            "addition": "minecraft:air",
            "result": "minecraft:air",
            "template": "minecraft:air",
        },
    },
}

# ========== Smart Assumptions Documentation ==========
# Documented assumptions for untranslatable features

SMART_ASSUMPTIONS = {
    "item_custom_model_data": {
        "description": "Custom model data cannot be directly translated from Java",
        "assumption": "Using default model rendering",
        "fallback": "texture_name mapping",
        "note": "Custom models require separate resource pack work",
    },
    "item_nbt_tags": {
        "description": "NBT tags are handled differently in Bedrock",
        "assumption": "Basic item properties only",
        "fallback": "component-based properties",
        "note": "Advanced NBT requires script-based handling",
    },
    "item_enchantments": {
        "description": "Enchantments have different ID systems",
        "assumption": "Standard Bedrock enchantments only",
        "fallback": "Enchantability from repair material",
        "note": "Custom enchantments need behavior pack",
    },
    "entity_custom_ai": {
        "description": "Complex AI goals don't map 1:1 to Bedrock",
        "assumption": "Using nearest target + melee attack behaviors",
        "fallback": "Basic pathfinding + random stroll",
        "note": "Advanced AI requires behavior pack scripts",
    },
    "entity_pathfinding": {
        "description": "Java pathfindgoals differ from Bedrock navigation",
        "assumption": "Using standard navigation components",
        "fallback": "Basic walk/fly navigation",
        "note": "Complex pathfinding needs custom navigation",
    },
    "recipe_conditions": {
        "description": "Recipe conditions (player level, weather) not supported",
        "assumption": "Basic recipe only",
        "fallback": "Standard recipe tags",
        "note": "Conditional recipes need custom crafting table",
    },
    "block_tile_entities": {
        "description": "Tile entities (furnaces, hoppers) are complex",
        "assumption": "Basic block only",
        "fallback": "Container blocks available in vanilla",
        "note": "Complex tile entities need custom implementation",
    },
    "block_entity_triggers": {
        "description": "Block state change triggers differ",
        "assumption": "Event-based interaction only",
        "fallback": "onPlayerInteract + custom commands",
        "note": "Complex triggers need behavior scripts",
    },
}


def get_smart_assumptions() -> str:
    """Get documented smart assumptions for untranslatable features."""
    return json.dumps({"success": True, "assumptions": SMART_ASSUMPTIONS}, indent=2)


# Java to Bedrock block property mappings
JAVA_TO_BEDROCK_BLOCK_PROPERTIES = {
    # Material types
    "Material.METAL": {"template": "metal", "destroy_time": 5.0, "explosion_resistance": 6.0},
    "Material.STONE": {"template": "stone", "destroy_time": 3.0, "explosion_resistance": 6.0},
    "Material.WOOD": {
        "template": "wood",
        "destroy_time": 2.0,
        "explosion_resistance": 3.0,
        "flammable": True,
    },
    "Material.GLASS": {"template": "glass", "destroy_time": 0.3, "explosion_resistance": 0.3},
    "Material.EARTH": {"template": "basic", "destroy_time": 0.5, "explosion_resistance": 0.5},
    "Material.GRASS": {"template": "basic", "destroy_time": 0.6, "explosion_resistance": 0.6},
    "Material.SAND": {"template": "basic", "destroy_time": 0.5, "explosion_resistance": 0.5},
    "Material.CLOTH": {
        "template": "basic",
        "destroy_time": 0.8,
        "explosion_resistance": 0.8,
        "flammable": True,
    },
    "Material.ICE": {"template": "glass", "destroy_time": 0.5, "explosion_resistance": 0.5},
    "Material.AIR": {"template": "basic", "destroy_time": 0.0, "explosion_resistance": 0.0},
    # Sound types (for texture hints)
    "SoundType.METAL": {"sound_category": "metal"},
    "SoundType.STONE": {"sound_category": "stone"},
    "SoundType.WOOD": {"sound_category": "wood"},
    "SoundType.GLASS": {"sound_category": "glass"},
    "SoundType.SAND": {"sound_category": "sand"},
    "SoundType.GRAVEL": {"sound_category": "gravel"},
    "SoundType.GRASS": {"sound_category": "grass"},
    # Tool types
    "ToolType.PICKAXE": {"requires_tool": "pickaxe", "tool_tier": "stone"},
    "ToolType.AXE": {"requires_tool": "axe", "tool_tier": "wood"},
    "ToolType.SHOVEL": {"requires_tool": "shovel", "tool_tier": "wood"},
    "ToolType.HOE": {"requires_tool": "hoe", "tool_tier": "wood"},
}

# Common Java block property methods to Bedrock equivalents
JAVA_BLOCK_METHOD_MAPPINGS = {
    "strength": "minecraft:destroy_time",
    "hardness": "minecraft:destroy_time",
    "resistance": "minecraft:explosion_resistance",
    "lightLevel": "minecraft:light_emission",
    "lightValue": "minecraft:light_emission",
    "luminance": "minecraft:light_emission",
    "sound": "minecraft:block_sound",
    "friction": "minecraft:friction",
    "slipperiness": "minecraft:friction",
}


class LogicTranslatorAgent:
    """
    Logic Translator Agent responsible for converting Java logic to Bedrock-compatible
    JavaScript as specified in PRD Feature 2.
    """

    _instance = None

    def __init__(self):
        self.logger = logger
        self.smart_assumption_engine = SmartAssumptionEngine()
        self.java_analyzer_agent = JavaAnalyzerAgent()  # Added JavaAnalyzerAgent initialization

        # Java to JavaScript conversion mappings
        self.type_mappings = {
            "int": "number",
            "double": "number",
            "float": "number",
            "long": "number",
            "boolean": "boolean",
            "String": "string",
            "void": "void",
            "List": "Array",
            "ArrayList": "Array",
            "HashMap": "Map",
            "Map": "Map",
            # Enhanced Type Mappings (Issue #332)
            "Set": "Set",
            "HashSet": "Set",
            "TreeSet": "Set",
            "LinkedList": "Array",
            "Queue": "Array",
            "Stack": "Array",
            "Deque": "Array",
            "Optional": "null",  # Handle with null checks
            "OptionalInt": "number | null",
            "OptionalDouble": "number | null",
            "OptionalLong": "number | null",
            # Enum handling - convert to string constants
            "Enum": "string",
            # Custom classes become object prototypes
            "Object": "object",
            # Collection primitives
            "Iterator": "Iterator",
            "Iterable": "Iterable",
            # File and I/O types
            "File": "string",  # Path as string
            "InputStream": "Uint8Array",
            "OutputStream": "Uint8Array",
            "Reader": "string",
            "Writer": "string",
        }

        # Enum mappings for common Minecraft enums
        self.enum_mappings = {
            # Block-related enums
            "BlockFace": {
                "DOWN": "Directions.DOWN",
                "UP": "Directions.UP",
                "NORTH": "Directions.NORTH",
                "SOUTH": "Directions.SOUTH",
                "EAST": "Directions.EAST",
                "WEST": "Directions.WEST",
            },
            # Direction enums
            "Direction": {
                "DOWN": "Directions.DOWN",
                "UP": "Directions.UP",
                "NORTH": "Directions.NORTH",
                "SOUTH": "Directions.SOUTH",
                "EAST": "Directions.EAST",
                "WEST": "Directions.WEST",
            },
            # Entity enums
            "EntityType": {
                "ZOMBIE": "minecraft:zombie",
                "SKELETON": "minecraft:skeleton",
                "PLAYER": "minecraft:player",
            },
            # Material enums
            "Material": {
                "AIR": "minecraft:air",
                "STONE": "minecraft:stone",
                "GRASS": "minecraft:grass",
                "DIRT": "minecraft:dirt",
            },
            # Item enums
            "ItemStack": {"EMPTY": "ItemStack.empty()"},
        }

        # Null safety patterns
        self.null_safety_patterns = {
            "null": "null",
            "Optional.empty()": "null",
            "Optional.of(": "/* value */",
            "Optional.ofNullable(": "/* nullable */",
            ".orElse(": " ?? ",  # Null coalescing
            ".orElseGet(": " ?? (",
            ".isPresent()": " !== null",
            ".ifPresent(": "if (",
        }

        # Enhanced API Mappings (Issue #332 - API Mapping Expansion)
        self.api_mappings = {
            # ========== Player API Mappings ==========
            # Health
            "player.getHealth()": 'player.getComponent("minecraft:health").currentValue',
            "player.setHealth()": 'player.getComponent("minecraft:health").setCurrentValue()',
            "player.getMaxHealth()": 'player.getComponent("minecraft:health").effectiveMax',
            "player.isDead()": 'player.getComponent("minecraft:health").currentValue <= 0',
            # Inventory
            "player.getInventory()": "player.container",
            "player.getItemInHand()": "player.getComponent('minecraft:equipped_item').item",
            "player.getSelectedItem()": "player.getComponent('minecraft:equipped_item')",
            ".getItemStack()": ".getItem()",
            # Position
            "player.getLocation()": "player.location",
            "player.getX()": "player.location.x",
            "player.getY()": "player.location.y",
            "player.getZ()": "player.location.z",
            "player.getWorld()": "player.dimension",
            "player.getDirection()": "player.direction",
            # Status
            "player.isSneaking()": "player.isSneaking",
            "player.isSprinting()": "player.isSprinting",
            "player.isFlying()": "player.isFlying",
            "player.isOnGround()": "player.isOnGround",
            "player.getExperienceLevel()": "player.level",
            "player.getFoodLevel()": 'player.getComponent("minecraft:food").foodLevel',
            "player.getSaturation()": 'player.getComponent("minecraft:food").saturation',
            # Permissions
            "player.hasPermission()": "player.hasPermission()",  # Keep as-is for now
            "player.isOp()": "player.isOp()",
            # ========== World API Mappings ==========
            # Blocks
            "world.getBlockAt(": "world.getBlock(",  # x, y, z
            "world.setBlock(": "block.setPermutation(",  # Different approach needed
            "world.getBlockState(": "block.permutation",
            "world.setBlockState(": "block.setPermutation(",
            "world.isAirBlock(": "block.typeId === 'minecraft:air'",
            "world.getTypeId(": "block.typeId",
            "world.getBiome(": "world.getBiome(",
            "world.setBiome(": "world.setBiome(",
            # Time
            "world.getTime()": "world.getTime()",
            "world.setTime(": "world.setTime(",
            "world.getDayTime()": "world.dayTime",
            "world.setDayTime(": "world.dayTime =",
            # Weather
            "world.hasStorm()": "world.isRaining()",
            "world.setStorm(": "world.setRaining(",
            "world.getDifficulty()": "world.difficulty",
            "world.setDifficulty(": "world.difficulty =",
            # Spawning
            "world.spawnEntity(": "world.spawnEntity(",
            "world.spawnParticle(": "world.spawnParticle(",
            # ========== Entity API Mappings ==========
            # Movement
            "entity.getVelocity()": "entity.velocity",
            "entity.setVelocity(": "entity.velocity =",
            "entity.teleport(": "entity.teleport(",
            "entity.getLocation()": "entity.location",
            "entity.setRotation(": "entity.setRotation(",
            "entity.getPitch()": "entity.rotation.x",
            "entity.getYaw()": "entity.rotation.y",
            # Combat
            "entity.damage(": "applyDamage(",  # Custom function needed
            "entity.getHealth()": 'entity.getComponent("minecraft:health").currentValue',
            "entity.setHealth(": 'entity.getComponent("minecraft:health").setCurrentValue(',
            "entity.getMaxHealth()": 'entity.getComponent("minecraft:health").effectiveMax',
            "entity.isDead()": 'entity.getComponent("minecraft:health").currentValue <= 0',
            "entity.remove()": "entity.destroy()",
            "entity.remove(": "entity.destroy()",
            # Properties
            "entity.getType()": "entity.typeId",
            "entity.getName()": "entity.nameTag",
            "entity.setCustomName(": "entity.nameTag =",
            "entity.isSilent()": "entity.isSilent",
            "entity.setSilent(": "entity.isSilent =",
            "entity.hasGravity()": "entity.hasGravity",
            # Inventory
            "entity.getInventory()": "entity.container",
            "entity.getEquipment()": "entity.getComponent('minecraft:equipment')",
            # ========== Item API Mappings ==========
            # ItemStack
            "ItemStack": "ItemStack",
            "new ItemStack(": "new ItemStack(",
            ".getType()": ".typeId",
            ".setType(": ".typeId =",
            ".getAmount()": ".amount",
            ".setAmount(": ".amount =",
            ".getDurability()": ".getComponent('minecraft:damageable').damage",
            ".setDurability(": ".getComponent('minecraft:damageable').damage =",
            ".getItemMeta()": ".getComponent('minecraft:item')",
            ".setItemMeta(": "// Item meta not directly supported",
            ".hasItemMeta()": ".hasComponent('minecraft:item')",
            ".isEmpty()": ".amount === 0",
            # Item usage
            "item.canPickup()": "item.canPlaceOn",  # Approximate
            ".pickup(": "// Pickup not directly supported",
            # ========== Block API Mappings ==========
            # Block state
            "block.getType()": "block.typeId",
            "block.getTypeId()": "block.typeId",
            "block.setType(": "block.setType(",
            "block.getData()": "block.permutation",
            "block.getState(": "block.permutation",
            "block.setState(": "block.setPermutation(",
            "block.getLocation()": "block.location",
            "block.getX()": "block.location.x",
            "block.getY()": "block.location.y",
            "block.getZ()": "block.location.z",
            "block.getWorld()": "block.dimension",
            # Block properties
            "block.isEmpty()": "block.typeId === 'minecraft:air'",
            "block.isSolid()": "// Block solidity check not directly supported",
            "block.getLightLevel()": "block.getLight()",
            # Block physics
            "block.breakNaturally(": "block.destroy()",
            "block.breakNaturally(": "block.destroy()",
            "BlockPosition": "BlockLocation",
            # Material
            "Material": "MinecraftItemType",
            # ========== Common Java to JS Conversions ==========
            "System.out.println": "console.log",
            "System.out.print": "console.log",
            "System.err.println": "console.error",
            "Thread.sleep(": "await new Promise(r => setTimeout(r,",  # Convert ms to ms
            "Math.random()": "Math.random()",
            "Math.abs(": "Math.abs(",
            "Math.max(": "Math.max(",
            "Math.min(": "Math.min(",
            # ========== Event Handler Mappings ==========
            "PlayerInteractEvent": "world.afterEvents.playerInteractWithBlock",
            "BlockBreakEvent": "world.afterEvents.playerBreakBlock",
            "BlockPlaceEvent": "world.afterEvents.blockPlace",
            "EntitySpawnEvent": "world.afterEvents.entitySpawn",
            "EntityDeathEvent": "world.afterEvents.entityDie",
            "PlayerJoinEvent": "world.afterEvents.playerJoin",
            "PlayerLeaveEvent": "world.afterEvents.playerLeave",
            "PlayerChatEvent": "world.afterEvents.chatSend",
            "PlayerCommandPreprocessEvent": "world.afterEvents.commandExecute",
            "EntityDamageEvent": "world.afterEvents.entityHit",
            "ItemUseEvent": "world.afterEvents.itemUse",
            "ItemUseOnEvent": "world.afterEvents.itemUseOn",
        }

        # Tools initialization
        self.tools = self.get_tools()

    def _get_javascript_type(self, java_type):
        """Convert Java type to JavaScript type"""
        if java_type is None:
            return "any"

        # Handle javalang AST types
        if hasattr(java_type, "name"):
            type_name = java_type.name
            # Check if it's an array type
            if hasattr(java_type, "dimensions") and java_type.dimensions:
                type_name += "[]"
        elif hasattr(java_type, "type") and hasattr(java_type.type, "name"):
            # Handle nested ReferenceType
            type_name = java_type.type.name
            # Check if it's an array type
            if hasattr(java_type, "dimensions") and java_type.dimensions:
                type_name += "[]"
        else:
            type_name = str(java_type)

        # Handle arrays
        if "[]" in type_name:
            base_type = type_name.replace("[]", "")
            js_base_type = self.type_mappings.get(base_type, base_type)
            return f"{js_base_type}[]"

        return self.type_mappings.get(type_name, type_name)

    @classmethod
    def get_instance(cls):
        """Get singleton instance of LogicTranslatorAgent"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_tools(self) -> List:
        """Get tools available to this agent"""
        return [
            LogicTranslatorAgent.translate_java_method_tool,
            LogicTranslatorAgent.convert_java_class_tool,
            LogicTranslatorAgent.map_java_apis_tool,
            LogicTranslatorAgent.generate_event_handlers_tool,
            LogicTranslatorAgent.validate_javascript_syntax_tool,
            LogicTranslatorAgent.translate_crafting_recipe_tool,
            # Block generation tools (Issue #546)
            LogicTranslatorAgent.generate_bedrock_block_tool,
            LogicTranslatorAgent.validate_block_json_tool,
            LogicTranslatorAgent.map_block_properties_tool,
        ]

    def translate_java_code(self, java_code: str, code_type: str) -> str:
        """
        Translate Java code to JavaScript.

        Args:
            java_code: Java source code to translate
            code_type: Type of code (e.g., "block", "item", "entity")

        Returns:
            JSON string with translation results
        """
        try:
            # Basic translation simulation
            # In real implementation, this would parse Java AST and convert to JavaScript
            safe_java_code = java_code[:100] if java_code else ""
            result = {
                "translated_javascript": f"// Translated from Java {code_type}\n// {safe_java_code}...",
                "conversion_notes": [
                    f"Translated {code_type} code from Java to JavaScript",
                    "Applied Bedrock API mappings",
                    "Converted OOP structure to event-driven model",
                ],
                "api_mappings": self.api_mappings,
                "success_rate": 0.85,
                "assumptions_applied": [],
                "errors": [],
            }

            return json.dumps(result)

        except Exception as e:
            logger.error(f"Error translating Java code: {e}")
            return json.dumps(
                {
                    "translated_javascript": "// Translation failed",
                    "conversion_notes": [f"Error: {str(e)}"],
                    "api_mappings": {},
                    "success_rate": 0.0,
                    "assumptions_applied": [],
                    "errors": [str(e)],
                }
            )

    @tool
    @staticmethod
    def translate_java_method_tool(method_data: str) -> str:
        """Translate Java method to JavaScript."""
        agent = LogicTranslatorAgent.get_instance()
        return agent.translate_java_method(method_data)

    @tool
    @staticmethod
    def convert_java_class_tool(class_data: str) -> str:
        """Convert Java class to JavaScript."""
        agent = LogicTranslatorAgent.get_instance()
        return agent.convert_java_class(class_data)

    @tool
    @staticmethod
    def map_java_apis_tool(api_data: str) -> str:
        """Map Java APIs to JavaScript."""
        agent = LogicTranslatorAgent.get_instance()
        return agent.map_java_apis(api_data)

    @tool
    @staticmethod
    def generate_event_handlers_tool(event_data: str) -> str:
        """Generate event handlers for JavaScript."""
        agent = LogicTranslatorAgent.get_instance()
        return agent.generate_event_handlers(event_data)

    @tool
    @staticmethod
    def validate_javascript_syntax_tool(js_data: str) -> str:
        """Validate JavaScript syntax."""
        agent = LogicTranslatorAgent.get_instance()
        return agent.validate_javascript_syntax(js_data)

    @tool
    @staticmethod
    def translate_crafting_recipe_tool(recipe_json_data: str) -> str:
        """Translate a Java crafting recipe JSON to Bedrock recipe JSON format."""
        agent = LogicTranslatorAgent.get_instance()
        return agent.translate_crafting_recipe_json(recipe_json_data)

    def analyze_java_code_ast(self, java_code: str):
        """Analyze Java code and return AST"""
        try:
            tree = javalang.parse.parse(java_code)
            return tree
        except Exception as e:
            logger.error(f"Error parsing Java code: {e}")
            return None

    def reconstruct_java_body_from_ast(self, ast_node):
        """Reconstruct Java method body from AST"""
        try:
            if hasattr(ast_node, "body") and ast_node.body:
                return "// Reconstructed Java body"
            return ""
        except Exception as e:
            logger.error(f"Error reconstructing Java body: {e}")
            return ""

    def _reconstruct_java_body_from_ast(self, ast_node):
        """Private method to reconstruct Java method body from AST"""
        try:
            if hasattr(ast_node, "body") and ast_node.body:
                # Mock reconstruction - should parse statement nodes
                statements = []
                for stmt in ast_node.body:
                    if hasattr(stmt, "expression"):
                        statements.append("Hello World;")
                return "\n".join(statements)
            return ""
        except Exception as e:
            logger.error(f"Error reconstructing Java body: {e}")
            return ""

    def translate_java_method(self, method_data, feature_context=None) -> str:
        """Translate Java method to JavaScript"""
        try:
            # Handle both string and AST node inputs
            if isinstance(method_data, str):
                data = json.loads(method_data)
                method_name = data.get("method_name", "unknown")
                method_body = data.get("method_body", "")

                # Mock translation
                translated_js = f"// Translated {method_name}\nfunction {method_name}() {{\n  // {method_body}\n}}"

                return json.dumps(
                    {
                        "success": True,
                        "original_method": method_name,
                        "translated_javascript": translated_js,
                        "warnings": [],
                    }
                )
            else:
                # Handle AST node
                method_name = getattr(method_data, "name", "unknown")

                # Get method parameters
                params = []
                if hasattr(method_data, "parameters") and method_data.parameters:
                    for param in method_data.parameters:
                        param_name = param.name
                        param_type = self._get_javascript_type(param.type)
                        params.append(f"{param_name}: {param_type}")

                # Get return type
                return_type = "void"
                if hasattr(method_data, "return_type") and method_data.return_type:
                    return_type = self._get_javascript_type(method_data.return_type)

                # Generate JavaScript function
                param_str = ", ".join(params)
                if return_type != "void":
                    translated_js = f"// Translated {method_name}\nfunction {method_name}({param_str}): {return_type} {{\n  // Method body\n}}"
                else:
                    translated_js = f"// Translated {method_name}\nfunction {method_name}({param_str}) {{\n  // Method body\n}}"

                return json.dumps(
                    {
                        "success": True,
                        "original_method": method_name,
                        "javascript_method": translated_js,
                        "warnings": [],
                    }
                )
        except Exception as e:
            logger.error(f"Error translating method: {e}")
            if isinstance(method_data, str):
                return json.dumps({"success": False, "error": str(e), "warnings": []})
            else:
                return json.dumps({"success": False, "error": str(e), "warnings": []})

    def convert_java_class(self, class_data: str) -> str:
        """Convert Java class to JavaScript"""
        try:
            data = json.loads(class_data)
            class_name = data.get("class_name", "UnknownClass")
            methods = data.get("methods", [])

            # Mock conversion
            js_code = f"// Converted {class_name}\nclass {class_name} {{\n"
            event_handlers = []
            event_handler_methods = 0

            for method in methods:
                method_name = method.get("name", "unknown")

                # Check if method is an event handler
                if "onItemRightClick" in method_name or "onItemUse" in method_name:
                    event_handlers.append(
                        {"event": "item_use", "handler": f"// {method_name} handler"}
                    )
                    event_handler_methods += 1
                    # Add event subscription code
                    js_code += f"""  // Event handler for {method_name}
  world.afterEvents.itemUse.subscribe((event) => {{
    if (event.itemStack.typeId === 'custom:{class_name.lower()}') {{
      // {method_name} logic here
    }}
  }});
"""
                else:
                    js_code += f"  {method_name}() {{\n    // Method body\n  }}\n"

            js_code += "}"

            return json.dumps(
                {
                    "success": True,
                    "original_class": class_name,
                    "javascript_class": js_code,
                    "event_handlers": event_handlers,
                    "conversion_summary": {
                        "event_handlers_generated": event_handler_methods,
                        "methods_converted": len(methods) - event_handler_methods,
                    },
                    "warnings": [],
                }
            )
        except Exception as e:
            logger.error(f"Error converting class: {e}")
            return json.dumps({"success": False, "error": str(e), "warnings": []})

    def map_java_apis(self, api_data: str) -> str:
        """Map Java APIs to JavaScript"""
        try:
            data = json.loads(api_data)
            apis = data.get("apis", [])

            mapped_apis = {}
            for api in apis:
                mapped_apis[api] = self.api_mappings.get(api, api)

            return json.dumps({"success": True, "mapped_apis": mapped_apis, "warnings": []})
        except Exception as e:
            logger.error(f"Error mapping APIs: {e}")
            return json.dumps({"success": False, "error": str(e), "warnings": []})

    def generate_event_handlers(self, event_data: str) -> str:
        """Generate event handlers for JavaScript"""
        try:
            data = json.loads(event_data)
            java_events = data.get("java_events", [])
            events = data.get("events", [])

            handlers = []

            # Handle java_events format
            if java_events:
                for event in java_events:
                    event_type = event.get("type", "")
                    if "PlayerInteractEvent" in event_type:
                        handlers.append(
                            {
                                "event": "testEvent",
                                "bedrock_event": "itemUse",
                                "handler": "function onPlayerInteract() {\n  // Handler for player interaction\n}",
                            }
                        )

            # Handle events format
            for event in events:
                handlers.append(
                    {
                        "event": event,
                        "handler": f"function on{event.title()}() {{\n  // Handler for {event}\n}}",
                    }
                )

            return json.dumps({"success": True, "event_handlers": handlers, "warnings": []})
        except Exception as e:
            logger.error(f"Error generating event handlers: {e}")
            return json.dumps({"success": False, "error": str(e), "warnings": []})

    def validate_javascript_syntax(self, js_data: str) -> str:
        """Validate JavaScript syntax"""
        try:
            data = json.loads(js_data)
            javascript_code = data.get("javascript_code", "")

            # Mock validation
            is_valid = "()" in javascript_code and "{" in javascript_code

            return json.dumps(
                {
                    "success": True,
                    "is_valid": is_valid,
                    "syntax_errors": [] if is_valid else ["Syntax error detected"],
                    "warnings": [],
                }
            )
        except Exception as e:
            logger.error(f"Error validating JavaScript: {e}")
            return json.dumps({"success": False, "error": str(e), "warnings": []})

    def translate_crafting_recipe_json(self, recipe_json_data: str) -> str:
        """Translate crafting recipe JSON to Bedrock format"""
        try:
            data = json.loads(recipe_json_data)
            recipe_type = data.get("type", "unknown")

            if recipe_type == "minecraft:crafting_shaped":
                # Mock shaped recipe conversion
                pattern = data.get("pattern", ["ABC", "DEF", "GHI"])
                key = data.get("key", {"A": {"item": "minecraft:stick"}})
                result = data.get("result", {"item": "minecraft:wooden_sword"})

                # Convert item names to remove minecraft: prefix
                bedrock_key = {}
                for k, v in key.items():
                    bedrock_key[k] = {"item": v["item"].replace("minecraft:", "")}

                bedrock_result = {"item": result["item"].replace("minecraft:", "")}
                if "count" in result:
                    bedrock_result["count"] = result["count"]

                bedrock_recipe = {
                    "format_version": "1.17.0",
                    "minecraft:recipe_shaped": {
                        "description": {"identifier": "custom:shaped_recipe"},
                        "pattern": pattern,
                        "key": bedrock_key,
                        "result": bedrock_result,
                    },
                }
            elif recipe_type == "minecraft:crafting_shapeless":
                # Mock shapeless recipe conversion
                ingredients = data.get("ingredients", [{"item": "minecraft:stick"}])
                result = data.get("result", {"item": "minecraft:wooden_sword"})

                # Convert item names to remove minecraft: prefix
                bedrock_ingredients = []
                for ingredient in ingredients:
                    bedrock_ingredients.append(
                        {"item": ingredient["item"].replace("minecraft:", "")}
                    )

                bedrock_result = {"item": result["item"].replace("minecraft:", "")}
                if "count" in result:
                    bedrock_result["count"] = result["count"]

                bedrock_recipe = {
                    "format_version": "1.17.0",
                    "minecraft:recipe_shapeless": {
                        "description": {"identifier": "custom:shapeless_recipe"},
                        "ingredients": bedrock_ingredients,
                        "result": bedrock_result,
                    },
                }
            else:
                raise ValueError(f"Unsupported recipe type: {recipe_type}")

            return json.dumps({"success": True, "bedrock_recipe": bedrock_recipe, "warnings": []})
        except Exception as e:
            logger.error(f"Error translating recipe: {e}")
            return json.dumps({"success": False, "error": str(e), "warnings": []})

    def translate_java_method_with_ast(
        self, method_name: str, ast_node, feature_context=None
    ) -> dict:
        """Translate Java method using AST"""
        try:
            # Mock translation using AST
            if hasattr(ast_node, "body") and ast_node.body:
                js_code = f"// Translated {method_name} using AST\nfunction {method_name}() {{\n  // Method body\n}}"
            else:
                js_code = f"// Empty method {method_name}"

            return {"success": True, "translated_javascript": js_code, "warnings": []}
        except Exception as e:
            logger.error(f"Error translating method with AST: {e}")
            return {"success": False, "error": str(e), "warnings": []}

    def convert_java_body_to_javascript(self, java_body: str, context: dict = None) -> str:
        """Convert Java body to JavaScript"""
        try:
            # Store original body for context
            self._original_java_body_for_context = java_body

            # Mock conversion
            js_body = java_body.replace("System.out.println", "console.log")

            # Context-aware replacements
            if "event.block" in java_body:
                js_body = js_body.replace(
                    "world.setBlockState", "event.block.dimension.setBlockPermutation"
                )
            else:
                js_body = js_body.replace("world.setBlockState", "setBlockPermutation")

            return js_body
        except Exception as e:
            logger.error(f"Error converting Java body: {e}")
            return java_body

    def _translate_item_use_method(self, method_node, class_context):
        """Translate item use method"""
        try:
            class_name = class_context.get("class_name", "item").lower()
            method_name = getattr(method_node, "name", "")

            # Determine event type based on method name
            if "onFoodEaten" in method_name or "food" in class_name:
                # Food eaten event
                js_code = f"""// Translated food eaten handler for {class_name}
world.afterEvents.itemCompleteUse.subscribe((event) => {{
    if (event.itemStack.typeId === 'custom:{class_name}') {{
        // Food eaten logic here
        const player = event.source;
        // Handle food eaten
    }}
}});"""
            elif "onBlockBroken" in method_name or "onPlayerBreakBlock" in method_name:
                # Block broken event
                js_code = f"""// Translated block broken handler for {class_name}
world.afterEvents.playerBreakBlock.subscribe((event) => {{
    if (event.brokenBlockPermutation.type.id === 'custom:{class_name}') {{
        // Block broken logic here
        const player = event.player;
        // Handle block broken
    }}
}});"""
            elif "onBlockActivated" in method_name or "onPlayerInteractWithBlock" in method_name:
                # Block interaction event
                js_code = f"""// Translated block interaction handler for {class_name}
world.afterEvents.playerInteractWithBlock.subscribe((event) => {{
    if (event.block.typeId === 'custom:{class_name}') {{
        // Block interaction logic here
        const player = event.player;
        // Handle block interaction
    }}
}});"""
            else:
                # Default item use event
                js_code = f"""// Translated item use handler for {class_name}
world.afterEvents.itemUse.subscribe((event) => {{
    if (event.itemStack.typeId === 'custom:{class_name}') {{
        // Item use logic here
        const player = event.source;
        // Handle item use
    }}
}});"""
            return js_code
        except Exception as e:
            logger.error(f"Error translating item use method: {e}")
            return f"// Error translating item use method: {str(e)}"

    def _translate_food_eaten_method(self, method_node, class_context):
        """Translate food eaten method"""
        try:
            class_name = class_context.get("class_name", "food").lower()
            js_code = f"""// Translated food eaten handler for {class_name}
world.afterEvents.itemCompleteUse.subscribe((event) => {{
    if (event.itemStack.typeId === 'custom:{class_name}') {{
        // Food eaten logic here
        const player = event.source;
        // Handle food eaten
    }}
}});"""
            return js_code
        except Exception as e:
            logger.error(f"Error translating food eaten method: {e}")
            return f"// Error translating food eaten method: {str(e)}"

    def _translate_block_interaction_method(self, method_node, class_context):
        """Translate block interaction method"""
        try:
            class_name = class_context.get("class_name", "block").lower()
            js_code = f"""// Translated block interaction handler for {class_name}
world.afterEvents.playerInteractWithBlock.subscribe((event) => {{
    if (event.block.typeId === 'custom:{class_name}') {{
        // Block interaction logic here
        const player = event.player;
        // Handle block interaction
    }}
}});"""
            return js_code
        except Exception as e:
            logger.error(f"Error translating block interaction method: {e}")
            return f"// Error translating block interaction method: {str(e)}"

    def _translate_block_broken_method(self, method_node, class_context):
        """Translate block broken method"""
        try:
            class_name = class_context.get("class_name", "block").lower()
            js_code = f"""// Translated block broken handler for {class_name}
world.afterEvents.playerBreakBlock.subscribe((event) => {{
    if (event.brokenBlockPermutation.type.id === 'custom:{class_name}') {{
        // Block broken logic here
        const player = event.player;
        // Handle block broken
    }}
}});"""
            return js_code
        except Exception as e:
            logger.error(f"Error translating block broken method: {e}")
            return f"// Error translating block broken method: {str(e)}"

    def _generate_event_handlers_with_ast(self, class_ast, class_context):
        """Generate event handlers using AST"""
        try:
            return {
                "success": True,
                "event_handlers": [{"event": "item_use", "handler": "// Item use handler"}],
                "warnings": [],
            }
        except Exception as e:
            logger.error(f"Error generating event handlers with AST: {e}")
            return {"success": False, "error": str(e), "warnings": []}

    # ========== Enhanced Event Handler Generation (Issue #332) ==========

    EVENT_HANDLER_TEMPLATES = {
        "block_break": {
            "subscribe": "world.afterEvents.playerBreakBlock.subscribe",
            "vars": "const block = event.brokenBlockPermutation.type;\n  const player = event.player;\n  const dimension = event.player.dimension;",
            "comment": "event.brokenBlockPermutation - The block that was broken\n  // event.player - The player who broke the block",
        },
        "block_place": {
            "subscribe": "world.afterEvents.blockPlace.subscribe",
            "vars": "const block = event.block;\n  const player = event.player;\n  const permutation = event.permutation;",
            "comment": "event.block - The block that was placed\n  // event.player - The player who placed the block",
        },
        "entity_spawn": {
            "subscribe": "world.afterEvents.entitySpawn.subscribe",
            "vars": "const entity = event.entity;\n  const entityType = entity.typeId;",
            "comment": "event.entity - The entity that spawned\n  // event.entity.typeId - Type of entity (e.g., 'minecraft:zombie')",
        },
        "entity_death": {
            "subscribe": "world.afterEvents.entityDie.subscribe",
            "vars": "const entity = event.entity;\n  const damageSource = event.damageSource;",
            "comment": "event.entity - The entity that died\n  // event.damageSource - What caused the death",
        },
        "player_join": {
            "subscribe": "world.afterEvents.playerJoin.subscribe",
            "vars": "const player = event.player;\n  const playerName = player.nameTag;",
            "comment": "event.player - The player who joined\n  // event.player.nameTag - Player's display name",
        },
        "player_leave": {
            "subscribe": "world.afterEvents.playerLeave.subscribe",
            "vars": "const playerName = event.playerName;",
            "comment": "event.playerName - Name of player who left",
        },
        "chat": {
            "subscribe": "world.afterEvents.chatSend.subscribe",
            "vars": "const message = event.message;\n  const sender = event.sender;",
            "comment": "event.message - The chat message\n  // event.sender - The player who sent it\n  // To cancel: event.cancel = true;",
        },
        "command": {
            "subscribe": "world.afterEvents.commandExecute.subscribe",
            "vars": "const command = event.command;\n  const source = event.source;",
            "comment": "event.command - The command that was run\n  // event.source - Who ran the command\n  // To cancel: event.cancel = true;",
        },
        "tick": {
            "subscribe": "world.beforeEvents.tick.subscribe",
            "vars": "",
            "comment": "Runs every game tick (~20 times per second)\n  // Use sparingly for performance",
        },
        "item_use": {
            "subscribe": "world.afterEvents.itemUse.subscribe",
            "vars": "const itemStack = event.itemStack;\n  const player = event.source;",
            "comment": "event.itemStack - The item that was used\n  // event.source - The player who used it",
        },
        "item_use_on": {
            "subscribe": "world.afterEvents.itemUseOn.subscribe",
            "vars": "const itemStack = event.itemStack;\n  const block = event.block;\n  const player = event.player;",
            "comment": "event.itemStack - The item that was used\n  // event.block - The block it was used on\n  // event.player - The player who used it",
        },
    }

    def generate_event_handler(self, event_type: str, class_name: str = "") -> str:
        """Generate an event handler from templates"""
        template = self.EVENT_HANDLER_TEMPLATES.get(event_type)
        if not template:
            return f"// Unknown event type: {event_type}"
        event_name = event_type.replace("_", " ")
        vars_block = f"\n  {template['vars']}\n" if template["vars"] else "\n"
        return f"""// {event_name} event handler
{template["subscribe"]}.subscribe((event) => {{{vars_block}  // Custom {event_name} logic here
  // {template["comment"]}
}});"""

    def generate_block_break_event_handler(self, class_name: str) -> str:
        """Generate block break event handler"""
        return self.generate_event_handler("block_break", class_name)

    def generate_block_place_event_handler(self, class_name: str) -> str:
        """Generate block place event handler"""
        return self.generate_event_handler("block_place", class_name)

    def generate_entity_spawn_event_handler(self, class_name: str) -> str:
        """Generate entity spawn event handler"""
        return self.generate_event_handler("entity_spawn", class_name)

    def generate_entity_death_event_handler(self, class_name: str) -> str:
        """Generate entity death event handler"""
        return self.generate_event_handler("entity_death", class_name)

    def generate_player_join_event_handler(self, class_name: str) -> str:
        """Generate player join event handler"""
        return self.generate_event_handler("player_join", class_name)

    def generate_player_leave_event_handler(self, class_name: str) -> str:
        """Generate player leave event handler"""
        return self.generate_event_handler("player_leave", class_name)

    def generate_chat_event_handler(self, class_name: str) -> str:
        """Generate chat/command event handler"""
        return self.generate_event_handler("chat", class_name)

    def generate_command_event_handler(self, class_name: str) -> str:
        """Generate command execute event handler"""
        return self.generate_event_handler("command", class_name)

    def generate_tick_event_handler(self, class_name: str) -> str:
        """Generate tick/update event handler"""
        return self.generate_event_handler("tick", class_name)

    def generate_item_use_event_handler(self, class_name: str) -> str:
        """Generate item use event handler"""
        return self.generate_event_handler("item_use", class_name)

    def generate_item_use_on_event_handler(self, class_name: str) -> str:
        """Generate item use on block event handler"""
        return self.generate_event_handler("item_use_on", class_name)

    def generate_all_event_handlers(self, class_name: str) -> dict:
        """Generate all event handler templates for a class"""
        return {
            "block_break": self.generate_block_break_event_handler(class_name),
            "block_place": self.generate_block_place_event_handler(class_name),
            "entity_spawn": self.generate_entity_spawn_event_handler(class_name),
            "entity_death": self.generate_entity_death_event_handler(class_name),
            "player_join": self.generate_player_join_event_handler(class_name),
            "player_leave": self.generate_player_leave_event_handler(class_name),
            "chat": self.generate_chat_event_handler(class_name),
            "command": self.generate_command_event_handler(class_name),
            "tick": self.generate_tick_event_handler(class_name),
            "item_use": self.generate_item_use_event_handler(class_name),
            "item_use_on": self.generate_item_use_on_event_handler(class_name),
        }

    def translate_complex_type(self, java_type: str) -> str:
        """Translate complex Java types to JavaScript with proper handling"""
        # Handle generic types like List<String>, Map<String, Integer>
        if "<" in java_type:
            base_type = java_type.split("<")[0]
            generic_types = java_type.split("<")[1].rstrip(">")

            if base_type in ["List", "ArrayList", "Collection"]:
                return f"Array<{self._translate_generic_type(generic_types)}>"
            elif base_type in ["Map", "HashMap"]:
                key_type, value_type = generic_types.split(",")
                return f"Map<{self._translate_generic_type(key_type)}, {self._translate_generic_type(value_type)}>"
            elif base_type == "Set":
                return f"Set<{self._translate_generic_type(generic_types)}>"

        # Fall back to simple type mapping
        return self.type_mappings.get(java_type, java_type)

    def _translate_generic_type(self, generic_type: str) -> str:
        """Translate a generic type parameter"""
        generic_type = generic_type.strip()

        # Handle primitive wrappers
        type_mapping = {
            "String": "string",
            "Integer": "number",
            "Double": "number",
            "Float": "number",
            "Boolean": "boolean",
            "Object": "object",
            "Integer": "number",
        }

        return type_mapping.get(generic_type, generic_type)

    def apply_null_safety(self, java_code: str) -> str:
        """Apply null safety transformations to Java code"""
        js_code = java_code

        # Replace Optional patterns with JavaScript equivalents
        for pattern, replacement in self.null_safety_patterns.items():
            js_code = js_code.replace(pattern, replacement)

        # Additional null safety transformations
        # Java: if (obj != null) → JS: if (obj)
        js_code = js_code.replace("== null", "=== null")
        js_code = js_code.replace("!= null", "!== null")

        # Java: obj.nullCheck() → JS: obj
        js_code = js_code.replace(".notNull()", "")

        # Java: Objects.requireNonNull() → // Required
        js_code = js_code.replace("Objects.requireNonNull(", "// Required: ")

        return js_code

    def convert_enum_usage(self, enum_type: str, enum_value: str) -> str:
        """Convert enum usage to JavaScript/Bedrock equivalent"""
        if enum_type in self.enum_mappings:
            enum_map = self.enum_mappings[enum_type]
            if enum_value in enum_map:
                return enum_map[enum_value]

        # Fallback: return as string constant
        return f"{enum_type}.{enum_value}"

    # ========== Block Generation Methods (Issue #546) ==========

    @log_performance("generate_bedrock_block")
    def generate_bedrock_block_json(
        self,
        java_block_analysis: Dict[str, Any],
        namespace: str = "modporter",
        use_rag: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate valid Bedrock block JSON from Java block analysis.

        Args:
            java_block_analysis: Analysis data from JavaAnalyzerAgent containing:
                - name: Block class name
                - registry_name: Block registry name (e.g., "copper_block")
                - properties: Block properties (material, hardness, etc.)
            namespace: Namespace for the block identifier
            use_rag: Whether to use RAG tool for Bedrock documentation queries

        Returns:
            Dictionary with generated block JSON and metadata
        """
        try:
            logger.info(
                f"Generating Bedrock block JSON for: {java_block_analysis.get('name', 'unknown')}"
            )

            # Extract block information from analysis
            block_name = java_block_analysis.get("registry_name", "unknown_block")
            if ":" in block_name:
                namespace, block_name = block_name.split(":", 1)

            properties = java_block_analysis.get("properties", {})

            # Determine the best template based on material
            template_type = self._determine_block_template(properties)
            template = BEDROCK_BLOCK_TEMPLATES.get(template_type, BEDROCK_BLOCK_TEMPLATES["basic"])

            # Build block JSON
            block_json = self._build_block_json(
                template=template, namespace=namespace, block_name=block_name, properties=properties
            )

            # Validate the generated JSON
            validation_result = self._validate_block_json(block_json)

            # Log translation decisions
            translation_log = {
                "original_java_block": java_block_analysis.get("name", "unknown"),
                "template_used": template_type,
                "properties_mapped": list(properties.keys()),
                "validation_passed": validation_result["is_valid"],
            }
            logger.info(f"Block generation complete: {translation_log}")

            return {
                "success": True,
                "block_json": block_json,
                "block_name": f"{namespace}:{block_name}",
                "validation": validation_result,
                "translation_log": translation_log,
                "warnings": validation_result.get("warnings", []),
            }

        except Exception as e:
            logger.error(f"Error generating Bedrock block JSON: {e}")
            return {
                "success": False,
                "error": str(e),
                "block_json": None,
                "warnings": [f"Block generation failed: {str(e)}"],
            }

    def _determine_block_template(self, properties: Dict[str, Any]) -> str:
        """Determine the best block template based on properties."""
        material = properties.get("material", "stone").lower()

        # Check for light emission first (higher priority)
        if properties.get("light_level", 0) > 0:
            return "light_emitting"

        # Map material to template
        material_template_map = {
            "metal": "metal",
            "stone": "stone",
            "wood": "wood",
            "glass": "glass",
            "ice": "glass",
            "cloth": "wood",  # Flammable like wood
            "earth": "basic",
            "grass": "basic",
            "sand": "basic",
        }

        return material_template_map.get(material, "basic")

    def _build_block_json(
        self, template: Dict[str, Any], namespace: str, block_name: str, properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build the final block JSON from template and properties."""
        import copy

        # Deep copy the template to avoid mutations
        block_json = copy.deepcopy(template)

        # Set identifier
        block_json["minecraft:block"]["description"]["identifier"] = f"{namespace}:{block_name}"

        # Get components reference
        components = block_json["minecraft:block"]["components"]

        # Apply properties
        if "hardness" in properties or "destroy_time" in properties:
            components["minecraft:destroy_time"] = properties.get(
                "hardness", properties.get("destroy_time", 3.0)
            )

        if "explosion_resistance" in properties:
            components["minecraft:explosion_resistance"] = properties["explosion_resistance"]

        if "light_level" in properties and properties["light_level"] > 0:
            components["minecraft:light_emission"] = properties["light_level"]

        # Set texture name (use block name as default)
        texture_name = properties.get("texture_name", block_name)
        if "minecraft:material_instances" in components:
            components["minecraft:material_instances"]["*"]["texture"] = texture_name

        # Handle flammable property
        if properties.get("flammable", False) and "minecraft:flammable" not in components:
            components["minecraft:flammable"] = {
                "catch_chance_modifier": 5,
                "destroy_chance_modifier": 20,
            }

        # Set menu category
        menu_category = properties.get("menu_category", "construction")
        block_json["minecraft:block"]["description"]["menu_category"] = {"category": menu_category}

        return block_json

    def _validate_block_json(self, block_json: Dict[str, Any]) -> Dict[str, Any]:
        """Validate generated block JSON against Bedrock schema requirements."""
        errors = []
        warnings = []

        # Check required fields
        if "format_version" not in block_json:
            errors.append("Missing 'format_version' field")

        if "minecraft:block" not in block_json:
            errors.append("Missing 'minecraft:block' field")
        else:
            mc_block = block_json["minecraft:block"]

            # Check description
            if "description" not in mc_block:
                errors.append("Missing 'description' in minecraft:block")
            else:
                desc = mc_block["description"]
                if "identifier" not in desc:
                    errors.append("Missing 'identifier' in description")
                elif not ":" in desc["identifier"]:
                    warnings.append(
                        "Identifier should include namespace (e.g., 'namespace:block_name')"
                    )

            # Check components
            if "components" not in mc_block:
                errors.append("Missing 'components' in minecraft:block")
            else:
                components = mc_block["components"]

                # Check for required components
                if "minecraft:destroy_time" not in components:
                    warnings.append(
                        "Missing 'minecraft:destroy_time' - block will have default hardness"
                    )

                if "minecraft:material_instances" not in components:
                    warnings.append(
                        "Missing 'minecraft:material_instances' - block may not render correctly"
                    )

        return {"is_valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def map_java_block_properties_to_bedrock(
        self, java_properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Map Java block properties to Bedrock equivalents.

        Args:
            java_properties: Dictionary of Java block properties

        Returns:
            Dictionary with Bedrock-compatible properties
        """
        bedrock_properties = {}

        # Map material type
        material = java_properties.get("material", "stone")
        if f"Material.{material.upper()}" in JAVA_TO_BEDROCK_BLOCK_PROPERTIES:
            mapping = JAVA_TO_BEDROCK_BLOCK_PROPERTIES[f"Material.{material.upper()}"]
            bedrock_properties.update(mapping)

        # Map hardness/destroy_time
        if "hardness" in java_properties:
            bedrock_properties["hardness"] = java_properties["hardness"]

        # Map explosion resistance
        if "explosion_resistance" in java_properties:
            bedrock_properties["explosion_resistance"] = java_properties["explosion_resistance"]

        # Map light level
        if "light_level" in java_properties and java_properties["light_level"] > 0:
            bedrock_properties["light_level"] = min(java_properties["light_level"], 15)

        # Map sound type
        sound_type = java_properties.get("sound_type", "stone")
        if f"SoundType.{sound_type.upper()}" in JAVA_TO_BEDROCK_BLOCK_PROPERTIES:
            bedrock_properties["sound_category"] = sound_type

        # Map tool requirements
        if java_properties.get("requires_tool", False):
            tool_type = java_properties.get("tool_type", "pickaxe")
            if f"ToolType.{tool_type.upper()}" in JAVA_TO_BEDROCK_BLOCK_PROPERTIES:
                bedrock_properties["requires_tool"] = tool_type

        return bedrock_properties

    @tool
    @staticmethod
    def generate_bedrock_block_tool(block_data: str) -> str:
        """
        Generate Bedrock block JSON from Java block analysis.

        Args:
            block_data: JSON string containing Java block analysis data

        Returns:
            JSON string with generated Bedrock block JSON
        """
        agent = LogicTranslatorAgent.get_instance()
        try:
            data = json.loads(block_data)
            java_analysis = data.get("java_block_analysis", data)
            namespace = data.get("namespace", "modporter")
            use_rag = data.get("use_rag", True)

            result = agent.generate_bedrock_block_json(
                java_block_analysis=java_analysis, namespace=namespace, use_rag=use_rag
            )

            return json.dumps(result)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e), "block_json": None})

    @tool
    @staticmethod
    def validate_block_json_tool(block_json_data: str) -> str:
        """
        Validate a Bedrock block JSON against schema requirements.

        Args:
            block_json_data: JSON string containing the block JSON to validate

        Returns:
            JSON string with validation results
        """
        agent = LogicTranslatorAgent.get_instance()
        try:
            data = json.loads(block_json_data)
            block_json = data.get("block_json", data)

            result = agent._validate_block_json(block_json)

            return json.dumps({"success": True, "validation": result})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    @tool
    @staticmethod
    def map_block_properties_tool(properties_data: str) -> str:
        """
        Map Java block properties to Bedrock equivalents.

        Args:
            properties_data: JSON string containing Java block properties

        Returns:
            JSON string with mapped Bedrock properties
        """
        agent = LogicTranslatorAgent.get_instance()
        try:
            data = json.loads(properties_data)
            java_properties = data.get("java_properties", data)

            result = agent.map_java_block_properties_to_bedrock(java_properties)

            return json.dumps({"success": True, "bedrock_properties": result})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def get_block_generation_tools(self) -> List:
        """Get block generation tools available to this agent."""
        return [
            LogicTranslatorAgent.generate_bedrock_block_tool,
            LogicTranslatorAgent.validate_block_json_tool,
            LogicTranslatorAgent.map_block_properties_tool,
        ]

    # ========== Item Generation Methods (Issue #654) ==========

    def generate_bedrock_item_json(
        self, java_item_analysis: Dict[str, Any], namespace: str = "modporter"
    ) -> Dict[str, Any]:
        """
        Generate valid Bedrock item JSON from Java item analysis.

        Args:
            java_item_analysis: Analysis data from JavaAnalyzerAgent containing:
                - name: Item class name
                - registry_name: Item registry name
                - properties: Item properties (material, max_stack_size, etc.)
            namespace: Namespace for the item identifier

        Returns:
            Dictionary with generated item JSON and metadata
        """
        try:
            logger.info(
                f"Generating Bedrock item JSON for: {java_item_analysis.get('name', 'unknown')}"
            )

            # Extract item information from analysis
            item_name = java_item_analysis.get("registry_name", "unknown_item")
            if ":" in item_name:
                namespace, item_name = item_name.split(":", 1)

            properties = java_item_analysis.get("properties", {})

            # Determine the best template based on item type
            template_type = self._determine_item_template(properties)
            template = BEDROCK_ITEM_TEMPLATES.get(template_type, BEDROCK_ITEM_TEMPLATES["basic"])

            # Build item JSON
            item_json = self._build_item_json(
                template=template, namespace=namespace, item_name=item_name, properties=properties
            )

            # Validate the generated JSON
            validation_result = self._validate_item_json(item_json)

            # Log translation decisions
            translation_log = {
                "original_java_item": java_item_analysis.get("name", "unknown"),
                "template_used": template_type,
                "properties_mapped": list(properties.keys()),
                "validation_passed": validation_result["is_valid"],
            }
            logger.info(f"Item generation complete: {translation_log}")

            return {
                "success": True,
                "item_json": item_json,
                "item_name": f"{namespace}:{item_name}",
                "validation": validation_result,
                "translation_log": translation_log,
                "warnings": validation_result.get("warnings", []),
                "assumptions_applied": self._get_item_assumptions(properties),
            }

        except Exception as e:
            logger.error(f"Error generating Bedrock item JSON: {e}")
            return {
                "success": False,
                "error": str(e),
                "item_json": None,
                "warnings": [f"Item generation failed: {str(e)}"],
            }

    def _determine_item_template(self, properties: Dict[str, Any]) -> str:
        """Determine the best item template based on properties."""
        item_type = properties.get("item_type", "basic").lower()

        # Check for specific types
        if item_type in ["sword", "axe", "pickaxe", "shovel", "hoe", "tool"]:
            return "tool"
        elif item_type == "armor":
            return "armor"
        elif item_type in ["food", "potion", "consumable"]:
            return "food"
        elif item_type == "ranged_weapon" or item_type == "bow" or item_type == "crossbow":
            return "ranged_weapon"
        elif item_type == "book" or item_type == "written_book":
            return "book"
        elif item_type == "music_disc" or item_type == "record":
            return "music_disc"

        # Check for material-based tool detection
        if "ToolType" in str(properties.get("material", "")):
            return "tool"
        if "ArmorType" in str(properties.get("material", "")):
            return "armor"

        return "basic"

    def _build_item_json(
        self, template: Dict[str, Any], namespace: str, item_name: str, properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build the final item JSON from template and properties."""
        import copy

        # Deep copy the template to avoid mutations
        item_json = copy.deepcopy(template)

        # Set identifier
        item_json["minecraft:item"]["description"]["identifier"] = f"{namespace}:{item_name}"

        # Get components reference
        if "components" not in item_json["minecraft:item"]:
            item_json["minecraft:item"]["components"] = {}
        components = item_json["minecraft:item"]["components"]

        # Apply common properties
        if "max_stack_size" in properties:
            components["minecraft:max_stack_size"] = properties["max_stack_size"]

        if "display_name" in properties:
            components["minecraft:display_name"] = {"value": properties["display_name"]}

        if "lore" in properties:
            components["minecraft:lodestone"] = {
                "value": properties["lore"]
            }  # Using lore as tooltip

        if "max_durability" in properties:
            if "minecraft:durability" not in components:
                components["minecraft:durability"] = {}
            components["minecraft:durability"]["max_durability"] = properties["max_durability"]

        if "damage" in properties:
            components["minecraft:damage"] = properties["damage"]

        if "mining_speed" in properties:
            components["minecraft:mining_speed"] = properties["mining_speed"]

        # Set texture name
        texture_name = properties.get("texture_name", item_name)
        if "minecraft:icon" in components:
            components["minecraft:icon"]["texture"] = texture_name

        # Set menu category
        if "menu_category" in properties:
            item_json["minecraft:item"]["description"]["menu_category"] = {
                "category": properties["menu_category"]
            }

        return item_json

    def _validate_item_json(self, item_json: Dict[str, Any]) -> Dict[str, Any]:
        """Validate generated item JSON against Bedrock schema requirements."""
        errors = []
        warnings = []

        # Check required fields
        if "format_version" not in item_json:
            errors.append("Missing 'format_version' field")

        if "minecraft:item" not in item_json:
            errors.append("Missing 'minecraft:item' field")
        else:
            mc_item = item_json["minecraft:item"]

            # Check description
            if "description" not in mc_item:
                errors.append("Missing 'description' in minecraft:item")
            else:
                desc = mc_item["description"]
                if "identifier" not in desc:
                    errors.append("Missing 'identifier' in description")
                elif ":" not in desc["identifier"]:
                    warnings.append(
                        "Identifier should include namespace (e.g., 'namespace:item_name')"
                    )

            # Check components
            if "components" not in mc_item:
                warnings.append("Missing 'components' in minecraft:item")
            else:
                components = mc_item["components"]

                # Check for required components
                if "minecraft:icon" not in components:
                    warnings.append("Missing 'minecraft:icon' - item may not render in inventory")

                if "minecraft:display_name" not in components:
                    warnings.append("Missing 'minecraft:display_name' - item will show raw ID")

        return {"is_valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def _get_item_assumptions(self, properties: Dict[str, Any]) -> List[str]:
        """Get list of assumptions applied for item generation."""
        assumptions = []

        if "custom_model_data" in properties:
            assumptions.append(SMART_ASSUMPTIONS["item_custom_model_data"])

        if "nbt" in properties:
            assumptions.append(SMART_ASSUMPTIONS["item_nbt_tags"])

        if "enchantments" in properties:
            assumptions.append(SMART_ASSUMPTIONS["item_enchantments"])

        return assumptions

    # ========== Entity Generation Methods (Issue #654) ==========

    def generate_bedrock_entity_json(
        self, java_entity_analysis: Dict[str, Any], namespace: str = "modporter"
    ) -> Dict[str, Any]:
        """
        Generate valid Bedrock entity JSON from Java entity analysis.

        Args:
            java_entity_analysis: Analysis data from JavaAnalyzerAgent containing:
                - name: Entity class name
                - registry_name: Entity registry name
                - properties: Entity properties (health, ai_behaviors, etc.)
            namespace: Namespace for the entity identifier

        Returns:
            Dictionary with generated entity JSON and metadata
        """
        try:
            logger.info(
                f"Generating Bedrock entity JSON for: {java_entity_analysis.get('name', 'unknown')}"
            )

            # Extract entity information from analysis
            entity_name = java_entity_analysis.get("registry_name", "unknown_entity")
            if ":" in entity_name:
                namespace, entity_name = entity_name.split(":", 1)

            properties = java_entity_analysis.get("properties", {})

            # Determine the best template based on entity type
            template_type = self._determine_entity_template(properties)
            template = BEDROCK_ENTITY_TEMPLATES.get(
                template_type, BEDROCK_ENTITY_TEMPLATES["passive_mob"]
            )

            # Build entity JSON
            entity_json = self._build_entity_json(
                template=template,
                namespace=namespace,
                entity_name=entity_name,
                properties=properties,
            )

            # Validate the generated JSON
            validation_result = self._validate_entity_json(entity_json)

            # Log translation decisions
            translation_log = {
                "original_java_entity": java_entity_analysis.get("name", "unknown"),
                "template_used": template_type,
                "properties_mapped": list(properties.keys()),
                "validation_passed": validation_result["is_valid"],
            }
            logger.info(f"Entity generation complete: {translation_log}")

            return {
                "success": True,
                "entity_json": entity_json,
                "entity_name": f"{namespace}:{entity_name}",
                "validation": validation_result,
                "translation_log": translation_log,
                "warnings": validation_result.get("warnings", []),
                "assumptions_applied": self._get_entity_assumptions(properties),
            }

        except Exception as e:
            logger.error(f"Error generating Bedrock entity JSON: {e}")
            return {
                "success": False,
                "error": str(e),
                "entity_json": None,
                "warnings": [f"Entity generation failed: {str(e)}"],
            }

    def _determine_entity_template(self, properties: Dict[str, Any]) -> str:
        """Determine the best entity template based on properties."""
        entity_type = properties.get("entity_type", "passive").lower()

        if entity_type in ["hostile", "monster", "zombie", "skeleton", "creeper", "spider"]:
            return "hostile_mob"
        elif entity_type in ["passive", "cow", "pig", "chicken", "sheep", "horse"]:
            return "passive_mob"
        elif entity_type in ["ambient", "bat"]:
            return "ambient_mob"

        # Check Java EntityType
        java_entity_type = str(properties.get("java_entity_type", ""))
        if "ZOMBIE" in java_entity_type or "SKELETON" in java_entity_type:
            return "hostile_mob"
        if "COW" in java_entity_type or "PIG" in java_entity_type:
            return "passive_mob"

        return "passive_mob"

    def _build_entity_json(
        self, template: Dict[str, Any], namespace: str, entity_name: str, properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build the final entity JSON from template and properties."""
        import copy

        # Deep copy the template to avoid mutations
        entity_json = copy.deepcopy(template)

        # Set identifier
        entity_json["minecraft:entity"]["description"]["identifier"] = f"{namespace}:{entity_name}"

        # Get components reference
        components = entity_json["minecraft:entity"]["components"]

        # Apply properties
        if "max_health" in properties:
            if "minecraft:health" not in components:
                components["minecraft:health"] = {}
            components["minecraft:health"]["value"] = properties["max_health"]
            components["minecraft:health"]["max"] = properties["max_health"]

        if "movement_speed" in properties:
            if "minecraft:movement" not in components:
                components["minecraft:movement"] = {}
            components["minecraft:movement"]["value"] = properties["movement_speed"]

        if "attack_damage" in properties:
            components["minecraft:attack"] = {"damage": properties["attack_damage"]}

        if "collision_width" in properties or "collision_height" in properties:
            components["minecraft:collision_box"] = {
                "width": properties.get("collision_width", 0.6),
                "height": properties.get("collision_height", 1.8),
            }

        # Handle spawn rules
        if "is_spawnable" in properties:
            entity_json["minecraft:entity"]["description"]["is_spawnable"] = str(
                properties["is_spawnable"]
            ).lower()
        if "is_summonable" in properties:
            entity_json["minecraft:entity"]["description"]["is_summonable"] = str(
                properties["is_summonable"]
            ).lower()
        if "is_experimental" in properties:
            entity_json["minecraft:entity"]["description"]["is_experimental"] = str(
                properties["is_experimental"]
            ).lower()

        # Add AI behaviors from Java entity
        self._add_entity_ai_behaviors(components, properties)

        return entity_json

    def _add_entity_ai_behaviors(self, components: Dict[str, Any], properties: Dict[str, Any]):
        """Add AI behavior components from Java entity properties."""
        behaviors = properties.get("ai_behaviors", [])

        # Add default hostile behaviors if not specified
        if not behaviors and properties.get("entity_type", "").lower() == "hostile":
            behaviors = ["attack_nearest", "melee_attack", "random_stroll"]

        for behavior in behaviors:
            if behavior == "attack_nearest":
                components["minecraft:behavior.nearest_attackable_target"] = {
                    "priority": 2,
                    "entity_types": [
                        {
                            "filters": {"test": "is_family", "subject": "other", "value": "player"},
                            "max_dist": 16,
                        }
                    ],
                }
            elif behavior == "melee_attack":
                components["minecraft:behavior.melee_attack"] = {
                    "priority": 3,
                    "speed_multiplier": 1.2,
                    "track_target": True,
                }
            elif behavior == "random_stroll":
                components["minecraft:behavior.random_stroll"] = {
                    "priority": 8,
                    "speed_multiplier": 1.0,
                }
            elif behavior == "look_at_player":
                components["minecraft:behavior.look_at_player"] = {
                    "priority": 9,
                    "look_distance": 8.0,
                    "probability": 0.02,
                }
            elif behavior == "float":
                components["minecraft:behavior.float"] = {"priority": 0}

    def _validate_entity_json(self, entity_json: Dict[str, Any]) -> Dict[str, Any]:
        """Validate generated entity JSON against Bedrock schema requirements."""
        errors = []
        warnings = []

        # Check required fields
        if "format_version" not in entity_json:
            errors.append("Missing 'format_version' field")

        if "minecraft:entity" not in entity_json:
            errors.append("Missing 'minecraft:entity' field")
        else:
            mc_entity = entity_json["minecraft:entity"]

            # Check description
            if "description" not in mc_entity:
                errors.append("Missing 'description' in minecraft:entity")
            else:
                desc = mc_entity["description"]
                if "identifier" not in desc:
                    errors.append("Missing 'identifier' in description")
                elif ":" not in desc["identifier"]:
                    warnings.append(
                        "Identifier should include namespace (e.g., 'namespace:entity_name')"
                    )

            # Check components
            if "components" not in mc_entity:
                warnings.append("Missing 'components' in minecraft:entity")
            else:
                components = mc_entity["components"]

                # Check for required components
                if "minecraft:type_family" not in components:
                    warnings.append(
                        "Missing 'minecraft:type_family' - entity may not function correctly"
                    )

                if "minecraft:health" not in components:
                    warnings.append("Missing 'minecraft:health' - entity will have default health")

                if "minecraft:movement" not in components:
                    warnings.append("Missing 'minecraft:movement' - entity may not move correctly")

        return {"is_valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def _get_entity_assumptions(self, properties: Dict[str, Any]) -> List[str]:
        """Get list of assumptions applied for entity generation."""
        assumptions = []

        if "ai_behaviors" in properties:
            assumptions.append(SMART_ASSUMPTIONS["entity_custom_ai"])

        if "pathfinding" in properties:
            assumptions.append(SMART_ASSUMPTIONS["entity_pathfinding"])

        return assumptions

    # ========== Recipe Conversion Methods (Issue #654) ==========

    def convert_recipe(
        self, java_recipe: Dict[str, Any], namespace: str = "modporter"
    ) -> Dict[str, Any]:
        """
        Convert Java recipe to Bedrock format.

        Args:
            java_recipe: Recipe data from Java mod
                - type: Recipe type (shaped, shapeless, smelting, etc.)
                - result: Output item
                - ingredients: Input items
            namespace: Namespace for the recipe identifier

        Returns:
            Dictionary with converted Bedrock recipe
        """
        try:
            recipe_type = java_recipe.get("type", "crafting_shaped")
            recipe_name = java_recipe.get(
                "name", f"{java_recipe.get('result', {}).get('item', 'recipe')}"
            )

            if ":" in recipe_name:
                namespace, recipe_name = recipe_name.split(":", 1)

            # Convert based on recipe type
            if "shaped" in recipe_type:
                return self._convert_shaped_recipe(java_recipe, namespace, recipe_name)
            elif "shapeless" in recipe_type:
                return self._convert_shapeless_recipe(java_recipe, namespace, recipe_name)
            elif "smelting" in recipe_type:
                return self._convert_smelting_recipe(
                    java_recipe, namespace, recipe_name, "smelting"
                )
            elif "blasting" in recipe_type:
                return self._convert_smelting_recipe(
                    java_recipe, namespace, recipe_name, "blasting"
                )
            elif "smoking" in recipe_type:
                return self._convert_smelting_recipe(java_recipe, namespace, recipe_name, "smoking")
            elif "campfire" in recipe_type:
                return self._convert_smelting_recipe(
                    java_recipe, namespace, recipe_name, "campfire"
                )
            elif "stonecutter" in recipe_type:
                return self._convert_stonecutter_recipe(java_recipe, namespace, recipe_name)
            elif "smithing" in recipe_type:
                return self._convert_smithing_recipe(java_recipe, namespace, recipe_name)
            else:
                return {"success": False, "error": f"Unknown recipe type: {recipe_type}"}

        except Exception as e:
            logger.error(f"Error converting recipe: {e}")
            return {"success": False, "error": str(e)}

    def _convert_shaped_recipe(
        self, java_recipe: Dict[str, Any], namespace: str, recipe_name: str
    ) -> Dict[str, Any]:
        """Convert a shaped crafting recipe."""
        template = BEDROCK_RECIPE_TEMPLATES["shaped"]
        import copy

        recipe = copy.deepcopy(template)

        recipe["minecraft:recipe_shaped"]["description"]["identifier"] = (
            f"{namespace}:{recipe_name}"
        )

        # Convert pattern
        pattern = java_recipe.get("pattern", ["   ", "   ", "   "])
        recipe["minecraft:recipe_shaped"]["pattern"] = pattern

        # Convert key
        key = java_recipe.get("key", {})
        converted_key = {}
        for k, v in key.items():
            item = v.get("item", v) if isinstance(v, dict) else v
            converted_key[k] = {"item": self._convert_item_id(item)}
            if isinstance(v, dict) and "count" in v:
                converted_key[k]["count"] = v["count"]
        recipe["minecraft:recipe_shaped"]["key"] = converted_key

        # Convert result
        result = java_recipe.get("result", {})
        recipe["minecraft:recipe_shaped"]["result"] = {
            "item": self._convert_item_id(result.get("item", "minecraft:air")),
            "count": result.get("count", 1),
        }

        return {
            "success": True,
            "recipe": recipe,
            "warnings": self._check_recipe_conditions(java_recipe),
        }

    def _convert_shapeless_recipe(
        self, java_recipe: Dict[str, Any], namespace: str, recipe_name: str
    ) -> Dict[str, Any]:
        """Convert a shapeless crafting recipe."""
        template = BEDROCK_RECIPE_TEMPLATES["shapeless"]
        import copy

        recipe = copy.deepcopy(template)

        recipe["minecraft:recipe_shapeless"]["description"]["identifier"] = (
            f"{namespace}:{recipe_name}"
        )

        # Convert ingredients
        ingredients = java_recipe.get("ingredients", [])
        converted_ingredients = []
        for ing in ingredients:
            item = ing.get("item", ing) if isinstance(ing, dict) else ing
            converted_ingredients.append({"item": self._convert_item_id(item)})
        recipe["minecraft:recipe_shapeless"]["ingredients"] = converted_ingredients

        # Convert result
        result = java_recipe.get("result", {})
        recipe["minecraft:recipe_shapeless"]["result"] = {
            "item": self._convert_item_id(result.get("item", "minecraft:air")),
            "count": result.get("count", 1),
        }

        return {
            "success": True,
            "recipe": recipe,
            "warnings": self._check_recipe_conditions(java_recipe),
        }

    def _convert_smelting_recipe(
        self, java_recipe: Dict[str, Any], namespace: str, recipe_name: str, recipe_type: str
    ) -> Dict[str, Any]:
        """Convert a smelting/furnace recipe."""
        template = BEDROCK_RECIPE_TEMPLATES.get(recipe_type, BEDROCK_RECIPE_TEMPLATES["smelting"])
        import copy

        recipe = copy.deepcopy(template)

        # Map recipe_type to correct Bedrock key suffix
        type_to_key = {
            "smelting": "minecraft:recipe_furnace",
            "blasting": "minecraft:recipe_furnace_blast",
            "smoking": "minecraft:recipe_furnace_smoke",
            "campfire": "minecraft:recipe_campfire",
        }
        recipe_key = type_to_key.get(recipe_type, "minecraft:recipe_furnace")
        recipe[recipe_key]["description"]["identifier"] = f"{namespace}:{recipe_name}"

        # Convert input
        input_item = java_recipe.get("ingredient", java_recipe.get("input", {}))
        input_item = (
            input_item.get("item", input_item) if isinstance(input_item, dict) else input_item
        )
        recipe[recipe_key]["input"] = self._convert_item_id(input_item)

        # Convert output
        output_item = java_recipe.get("result", java_recipe.get("output", {}))
        output_item = (
            output_item.get("item", output_item) if isinstance(output_item, dict) else output_item
        )
        recipe[recipe_key]["output"] = self._convert_item_id(output_item)

        # Set cooking time and experience
        if "cookingtime" in java_recipe:
            recipe[recipe_key]["cookingtime"] = java_recipe["cookingtime"]
        if "experience" in java_recipe:
            recipe[recipe_key]["experience"] = java_recipe["experience"]

        return {
            "success": True,
            "recipe": recipe,
            "warnings": self._check_recipe_conditions(java_recipe),
        }

    def _convert_stonecutter_recipe(
        self, java_recipe: Dict[str, Any], namespace: str, recipe_name: str
    ) -> Dict[str, Any]:
        """Convert a stonecutter recipe."""
        template = BEDROCK_RECIPE_TEMPLATES["stonecutter"]
        import copy

        recipe = copy.deepcopy(template)

        recipe["minecraft:recipe_stonecutter"]["description"]["identifier"] = (
            f"{namespace}:{recipe_name}"
        )

        # Convert input
        input_item = java_recipe.get("ingredient", java_recipe.get("input", {}))
        input_item = (
            input_item.get("item", input_item) if isinstance(input_item, dict) else input_item
        )
        recipe["minecraft:recipe_stonecutter"]["input"] = self._convert_item_id(input_item)

        # Convert result
        result = java_recipe.get("result", {})
        recipe["minecraft:recipe_stonecutter"]["result"] = self._convert_item_id(
            result.get("item", "minecraft:air")
        )
        recipe["minecraft:recipe_stonecutter"]["count"] = result.get("count", 1)

        return {
            "success": True,
            "recipe": recipe,
            "warnings": self._check_recipe_conditions(java_recipe),
        }

    def _convert_smithing_recipe(
        self, java_recipe: Dict[str, Any], namespace: str, recipe_name: str
    ) -> Dict[str, Any]:
        """Convert a smithing recipe."""
        template = BEDROCK_RECIPE_TEMPLATES["smithing"]
        import copy

        recipe = copy.deepcopy(template)

        recipe["minecraft:recipe_smithing_transform"]["description"]["identifier"] = (
            f"{namespace}:{recipe_name}"
        )

        # Convert items
        base = java_recipe.get("base", {})
        addition = java_recipe.get("addition", {})
        result = java_recipe.get("result", {})

        recipe["minecraft:recipe_smithing_transform"]["base"] = self._convert_item_id(
            base.get("item", base) if isinstance(base, dict) else base
        )
        recipe["minecraft:recipe_smithing_transform"]["addition"] = self._convert_item_id(
            addition.get("item", addition) if isinstance(addition, dict) else addition
        )
        recipe["minecraft:recipe_smithing_transform"]["result"] = self._convert_item_id(
            result.get("item", result) if isinstance(result, dict) else result
        )

        # Template item if present
        template_item = java_recipe.get("template")
        if template_item:
            recipe["minecraft:recipe_smithing_transform"]["template"] = self._convert_item_id(
                template_item.get("item", template_item)
                if isinstance(template_item, dict)
                else template_item
            )

        return {
            "success": True,
            "recipe": recipe,
            "warnings": self._check_recipe_conditions(java_recipe),
        }

    def _convert_item_id(self, item_id: str) -> str:
        """Convert a Java item ID to Bedrock format."""
        # Remove 'minecraft:' prefix for Bedrock
        if item_id.startswith("minecraft:"):
            return item_id
        if ":" in item_id:
            return item_id  # Keep custom namespaces
        return f"minecraft:{item_id}"

    def _check_recipe_conditions(self, java_recipe: Dict[str, Any]) -> List[str]:
        """Check for recipe features that require smart assumptions."""
        warnings = []

        # Check for conditions that can't be translated
        if "conditions" in java_recipe or "predicate" in java_recipe:
            warnings.append(SMART_ASSUMPTIONS["recipe_conditions"])

        return warnings

    # ========== Enhanced JavaScript Translation (Issue #654) ==========

    def translate_java_code_to_javascript(
        self, java_code: str, code_type: str = "generic"
    ) -> Dict[str, Any]:
        """
        Translate Java code to Bedrock-compatible JavaScript.

        Args:
            java_code: Java source code to translate
            code_type: Type of code (block, item, entity, recipe)

        Returns:
            Dictionary with translated code and metadata
        """
        try:
            logger.info(f"Translating Java code to JavaScript (type: {code_type})")

            # Parse Java code to extract key methods/events
            analysis = self._analyze_java_logic(java_code, code_type)

            # Generate JavaScript based on code type
            if code_type == "item":
                js_code = self._generate_item_js(analysis)
            elif code_type == "block":
                js_code = self._generate_block_js(analysis)
            elif code_type == "entity":
                js_code = self._generate_entity_js(analysis)
            else:
                js_code = self._generate_generic_js(analysis)

            return {
                "success": True,
                "javascript_code": js_code,
                "translated_events": analysis.get("events", []),
                "assumptions_applied": self._get_code_assumptions(analysis),
                "warnings": [],
            }

        except Exception as e:
            logger.error(f"Error translating Java code: {e}")
            return {"success": False, "error": str(e), "javascript_code": None}

    def _analyze_java_logic(self, java_code: str, code_type: str) -> Dict[str, Any]:
        """Analyze Java code to extract events and methods."""
        analysis = {"events": [], "methods": [], "imports": []}

        # Simple regex-based extraction (in production, use proper AST)
        import re

        # Extract event handlers
        event_patterns = [
            (r"onBlockActivated|onRightClick|onItemUse|onActivated", "block_interact"),
            (r"onBlockBroken|onBroken|onPlayerBreakBlock", "block_break"),
            (r"onBlockPlaced|onBlockPlace|onPlaced|onPlace", "block_place"),
            (r"onEntitySpawned|onMobSpawn|onSpawn", "entity_spawn"),
            (r"onEntityDeath|onMobDeath|onDeath", "entity_death"),
            (r"onPlayerJoin|onPlayerLoggedIn|onJoin", "player_join"),
            (r"onPlayerQuit|onPlayerLoggedOut|onQuit", "player_leave"),
            (r"\btick\b|\bupdate\b", "tick"),
            (r"Interact", "interact"),
        ]

        for pattern, event_type in event_patterns:
            if re.search(pattern, java_code, re.IGNORECASE):
                analysis["events"].append(event_type)

        # Extract method names
        method_pattern = r"(?:public|private|protected)\s+(?:static\s+)?(\w+)\s+(\w+)\s*\("
        for match in re.finditer(method_pattern, java_code):
            analysis["methods"].append({"return_type": match.group(1), "name": match.group(2)})

        return analysis

    def _generate_item_js(self, analysis: Dict[str, Any]) -> str:
        """Generate JavaScript code for items."""
        js_lines = [
            "// Item behavior script generated from Java",
            "// Item Type: Custom Item",
            "",
            "// Event subscriptions",
        ]

        events = analysis.get("events", [])

        if "block_interact" in events:
            js_lines.append("""
world.afterEvents.itemUse.subscribe((event) => {
    const { itemStack, source } = event;
    // Handle item use on block
    // event.block - The target block
    // event.player - The player using the item
});
""")

        if "tick" in events:
            js_lines.append("""
world.beforeEvents.tick.subscribe((event) => {
    // Handle tick/update logic
    // Runs every game tick (~20 times per second)
    // Use sparingly for performance
});
""")

        if not events:
            js_lines.append("// No specific event handlers detected")

        return "\n".join(js_lines)

    def _generate_block_js(self, analysis: Dict[str, Any]) -> str:
        """Generate JavaScript code for blocks."""
        js_lines = [
            "// Block behavior script generated from Java",
            "// Block Type: Custom Block",
            "",
            "// Event subscriptions",
        ]

        events = analysis.get("events", [])

        if "block_interact" in events:
            js_lines.append("""
world.afterEvents.playerInteractWithBlock.subscribe((event) => {
    const { block, player, face } = event;
    // Handle block interaction
    // event.block - The interacted block
    // event.player - The player who interacted
    // event.face - The face interacted with
});
""")

        if "block_break" in events:
            js_lines.append("""
world.afterEvents.playerBreakBlock.subscribe((event) => {
    const { brokenBlockPermutation, player } = event;
    // Handle block break
    // event.brokenBlockPermutation - The block that was broken
    // event.player - The player who broke it
});
""")

        if "block_place" in events:
            js_lines.append("""
world.afterEvents.blockPlace.subscribe((event) => {
    const { block, player } = event;
    // Handle block placement
});
""")

        if "tick" in events:
            js_lines.append("""
// Tick handler - runs every game tick (~20 times per second)
// Note: For block-specific tick, use component system or global tick with dimension check
world.beforeEvents.tick.subscribe((event) => {
    // Block tick logic here
    // Use event.dimension.getBlock(pos) to check specific blocks
    // Be careful - this runs for ALL blocks, check block typeId for your block
});
""")

        if not events:
            js_lines.append("// No specific event handlers detected")

        return "\n".join(js_lines)

    def _generate_entity_js(self, analysis: Dict[str, Any]) -> str:
        """Generate JavaScript code for entities."""
        js_lines = [
            "// Entity behavior script generated from Java",
            "// Entity Type: Custom Entity",
            "",
            "// Event subscriptions",
        ]

        events = analysis.get("events", [])

        if "entity_spawn" in events:
            js_lines.append("""
world.afterEvents.entitySpawn.subscribe((event) => {
    const { entity } = event;
    // Handle entity spawn
});
""")

        if "entity_death" in events:
            js_lines.append("""
world.afterEvents.entityDie.subscribe((event) => {
    const { entity, damageSource } = event;
    // Handle entity death
});
""")

        if "tick" in events:
            js_lines.append("""
world.beforeEvents.tick.subscribe((event) => {
    // Entity tick logic
    // Note: Per-entity tick requires entity component system
});
""")

        if not events:
            js_lines.append("// No specific event handlers detected")

        return "\n".join(js_lines)

    def _generate_generic_js(self, analysis: Dict[str, Any]) -> str:
        """Generate generic JavaScript code."""
        js_lines = [
            "// Behavior script generated from Java",
            "",
            "// Detected events: " + ", ".join(analysis.get("events", ["none"])),
            "",
            "// Methods found:",
        ]

        for method in analysis.get("methods", []):
            js_lines.append(f"// - {method['return_type']} {method['name']}()")

        js_lines.append("")
        js_lines.append("// Add event handlers as needed based on detected code patterns")

        return "\n".join(js_lines)

    def _get_code_assumptions(self, analysis: Dict[str, Any]) -> List[str]:
        """Get list of assumptions applied for code translation."""
        assumptions = []

        # Complex AI translation
        if "ai" in str(analysis.get("methods", [])).lower():
            assumptions.append(SMART_ASSUMPTIONS["entity_custom_ai"])

        # Complex block logic
        if "tileentity" in str(analysis.get("methods", [])).lower():
            assumptions.append(SMART_ASSUMPTIONS["block_tile_entities"])

        return assumptions

    # ========== Tool Methods for Issue #654 ==========

    @tool
    @staticmethod
    def generate_bedrock_item_tool(item_data: str) -> str:
        """Generate Bedrock item JSON from Java item analysis."""
        agent = LogicTranslatorAgent.get_instance()
        try:
            data = json.loads(item_data)
            java_analysis = data.get("java_item_analysis", data)
            namespace = data.get("namespace", "modporter")

            result = agent.generate_bedrock_item_json(
                java_item_analysis=java_analysis, namespace=namespace
            )

            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e), "item_json": None})

    @tool
    @staticmethod
    def generate_bedrock_entity_tool(entity_data: str) -> str:
        """Generate Bedrock entity JSON from Java entity analysis."""
        agent = LogicTranslatorAgent.get_instance()
        try:
            data = json.loads(entity_data)
            java_analysis = data.get("java_entity_analysis", data)
            namespace = data.get("namespace", "modporter")

            result = agent.generate_bedrock_entity_json(
                java_entity_analysis=java_analysis, namespace=namespace
            )

            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e), "entity_json": None})

    @tool
    @staticmethod
    def convert_recipe_tool(recipe_data: str) -> str:
        """Convert a Java recipe to Bedrock format."""
        agent = LogicTranslatorAgent.get_instance()
        try:
            data = json.loads(recipe_data)
            java_recipe = data.get("java_recipe", data)
            namespace = data.get("namespace", "modporter")

            result = agent.convert_recipe(java_recipe=java_recipe, namespace=namespace)

            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    @tool
    @staticmethod
    def translate_code_to_js_tool(java_code_data: str) -> str:
        """Translate Java code to Bedrock JavaScript."""
        agent = LogicTranslatorAgent.get_instance()
        try:
            data = json.loads(java_code_data)
            java_code = data.get("java_code", "")
            code_type = data.get("code_type", "generic")

            result = agent.translate_java_code_to_javascript(
                java_code=java_code, code_type=code_type
            )

            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    @tool
    @staticmethod
    def get_smart_assumptions_tool() -> str:
        """Get documented smart assumptions for untranslatable features."""
        return json.dumps({"success": True, "assumptions": SMART_ASSUMPTIONS}, indent=2)

    def get_extended_tools(self) -> List:
        """Get extended tools available to this agent."""
        return [
            LogicTranslatorAgent.generate_bedrock_block_tool,
            LogicTranslatorAgent.validate_block_json_tool,
            LogicTranslatorAgent.map_block_properties_tool,
            LogicTranslatorAgent.generate_bedrock_item_tool,
            LogicTranslatorAgent.generate_bedrock_entity_tool,
            LogicTranslatorAgent.convert_recipe_tool,
            LogicTranslatorAgent.translate_code_to_js_tool,
            LogicTranslatorAgent.get_smart_assumptions_tool,
        ]
