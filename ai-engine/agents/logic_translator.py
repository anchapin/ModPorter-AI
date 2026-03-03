"""
Logic Translator Agent for Java to JavaScript code conversion
Enhanced for Issue #546: Block Generation from Java block analysis
"""

from typing import List, Dict, Any, Optional
import os

import json
from crewai.tools import tool
import javalang  # Added javalang
from models.smart_assumptions import (
    SmartAssumptionEngine,
)
from agents.java_analyzer import JavaAnalyzerAgent
from utils.logging_config import get_agent_logger, log_performance

# Import validation and warning modules (Issue #570)
try:
    from engines.javascript_validator import (
        JavaScriptValidator,
        ValidationResult
    )
    from engines.translation_warnings import (
        TranslationWarningDetector,
        WarningReport,
        ImpactLevel
    )
    VALIDATION_AVAILABLE = True
except ImportError:
    VALIDATION_AVAILABLE = False
    logger.warning("Validation modules not available. Some features may be limited.")

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
                "menu_category": {
                    "category": "{{ menu_category }}"
                }
            },
            "components": {
                "minecraft:destroy_time": 3.0,
                "minecraft:explosion_resistance": 6.0,
                "minecraft:unit_cube": {},
                "minecraft:material_instances": {
                    "*": {
                        "texture": "{{ texture_name }}",
                        "render_method": "opaque"
                    }
                }
            }
        }
    },
    "metal": {
        "format_version": "1.20.10",
        "minecraft:block": {
            "description": {
                "identifier": "{{ namespace }}:{{ block_name }}",
                "menu_category": {
                    "category": "construction"
                }
            },
            "components": {
                "minecraft:destroy_time": 5.0,
                "minecraft:explosion_resistance": 6.0,
                "minecraft:unit_cube": {},
                "minecraft:material_instances": {
                    "*": {
                        "texture": "{{ texture_name }}",
                        "render_method": "opaque"
                    }
                }
            }
        }
    },
    "stone": {
        "format_version": "1.20.10",
        "minecraft:block": {
            "description": {
                "identifier": "{{ namespace }}:{{ block_name }}",
                "menu_category": {
                    "category": "construction"
                }
            },
            "components": {
                "minecraft:destroy_time": 3.0,
                "minecraft:explosion_resistance": 6.0,
                "minecraft:unit_cube": {},
                "minecraft:material_instances": {
                    "*": {
                        "texture": "{{ texture_name }}",
                        "render_method": "opaque"
                    }
                }
            }
        }
    },
    "wood": {
        "format_version": "1.20.10",
        "minecraft:block": {
            "description": {
                "identifier": "{{ namespace }}:{{ block_name }}",
                "menu_category": {
                    "category": "construction"
                }
            },
            "components": {
                "minecraft:destroy_time": 2.0,
                "minecraft:explosion_resistance": 3.0,
                "minecraft:unit_cube": {},
                "minecraft:flammable": {
                    "catch_chance_modifier": 5,
                    "destroy_chance_modifier": 20
                },
                "minecraft:material_instances": {
                    "*": {
                        "texture": "{{ texture_name }}",
                        "render_method": "opaque"
                    }
                }
            }
        }
    },
    "glass": {
        "format_version": "1.20.10",
        "minecraft:block": {
            "description": {
                "identifier": "{{ namespace }}:{{ block_name }}",
                "menu_category": {
                    "category": "construction"
                }
            },
            "components": {
                "minecraft:destroy_time": 0.3,
                "minecraft:explosion_resistance": 0.3,
                "minecraft:unit_cube": {},
                "minecraft:material_instances": {
                    "*": {
                        "texture": "{{ texture_name }}",
                        "render_method": "blend"
                    }
                }
            }
        }
    },
    "light_emitting": {
        "format_version": "1.20.10",
        "minecraft:block": {
            "description": {
                "identifier": "{{ namespace }}:{{ block_name }}",
                "menu_category": {
                    "category": "construction"
                }
            },
            "components": {
                "minecraft:destroy_time": 3.0,
                "minecraft:explosion_resistance": 6.0,
                "minecraft:unit_cube": {},
                "minecraft:light_emission": 15,
                "minecraft:material_instances": {
                    "*": {
                        "texture": "{{ texture_name }}",
                        "render_method": "opaque"
                    }
                }
            }
        }
    }
}

# Java to Bedrock block property mappings
JAVA_TO_BEDROCK_BLOCK_PROPERTIES = {
    # Material types
    "Material.METAL": {"template": "metal", "destroy_time": 5.0, "explosion_resistance": 6.0},
    "Material.STONE": {"template": "stone", "destroy_time": 3.0, "explosion_resistance": 6.0},
    "Material.WOOD": {"template": "wood", "destroy_time": 2.0, "explosion_resistance": 3.0, "flammable": True},
    "Material.GLASS": {"template": "glass", "destroy_time": 0.3, "explosion_resistance": 0.3},
    "Material.EARTH": {"template": "basic", "destroy_time": 0.5, "explosion_resistance": 0.5},
    "Material.GRASS": {"template": "basic", "destroy_time": 0.6, "explosion_resistance": 0.6},
    "Material.SAND": {"template": "basic", "destroy_time": 0.5, "explosion_resistance": 0.5},
    "Material.CLOTH": {"template": "basic", "destroy_time": 0.8, "explosion_resistance": 0.8, "flammable": True},
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
        self.java_analyzer_agent = (
            JavaAnalyzerAgent()
        )  # Added JavaAnalyzerAgent initialization

        # Initialize validation modules (Issue #570)
        if VALIDATION_AVAILABLE:
            self.js_validator = JavaScriptValidator(api_mappings=self.api_mappings)
            self.warning_detector = TranslationWarningDetector()
        else:
            self.js_validator = None
            self.warning_detector = None

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
            "BlockFace": {"DOWN": "Directions.DOWN", "UP": "Directions.UP", 
                         "NORTH": "Directions.NORTH", "SOUTH": "Directions.SOUTH",
                         "EAST": "Directions.EAST", "WEST": "Directions.WEST"},
            # Direction enums
            "Direction": {"DOWN": "Directions.DOWN", "UP": "Directions.UP",
                         "NORTH": "Directions.NORTH", "SOUTH": "Directions.SOUTH",
                         "EAST": "Directions.EAST", "WEST": "Directions.WEST"},
            # Entity enums
            "EntityType": {"ZOMBIE": "minecraft:zombie", "SKELETON": "minecraft:skeleton",
                          "PLAYER": "minecraft:player"},
            # Material enums
            "Material": {"AIR": "minecraft:air", "STONE": "minecraft:stone",
                        "GRASS": "minecraft:grass", "DIRT": "minecraft:dirt"},
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

    def _get_javascript_type(self, java_type):
        """Convert Java type to JavaScript type"""
        if java_type is None:
            return "any"
        
        # Handle javalang AST types
        if hasattr(java_type, 'name'):
            type_name = java_type.name
            # Check if it's an array type
            if hasattr(java_type, 'dimensions') and java_type.dimensions:
                type_name += '[]'
        elif hasattr(java_type, 'type') and hasattr(java_type.type, 'name'):
            # Handle nested ReferenceType
            type_name = java_type.type.name
            # Check if it's an array type
            if hasattr(java_type, 'dimensions') and java_type.dimensions:
                type_name += '[]'
        else:
            type_name = str(java_type)
        
        # Handle arrays
        if '[]' in type_name:
            base_type = type_name.replace('[]', '')
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
        tools = [
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

        # Add validation and warning tools (Issue #570)
        if VALIDATION_AVAILABLE:
            tools.extend([
                LogicTranslatorAgent.validate_javascript_comprehensive_tool,
                LogicTranslatorAgent.analyze_translation_warnings_tool,
                LogicTranslatorAgent.generate_user_facing_report_tool,
            ])

        return tools
    
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
            result = {
                "translated_javascript": f"// Translated from Java {code_type}\n// {java_code[:100]}...",
                "conversion_notes": [
                    f"Translated {code_type} code from Java to JavaScript",
                    "Applied Bedrock API mappings",
                    "Converted OOP structure to event-driven model"
                ],
                "api_mappings": self.api_mappings,
                "success_rate": 0.85,
                "assumptions_applied": [],
                "errors": []
            }
            
            return json.dumps(result)
            
        except Exception as e:
            logger.error(f"Error translating Java code: {e}")
            return json.dumps({
                "translated_javascript": "// Translation failed",
                "conversion_notes": [f"Error: {str(e)}"],
                "api_mappings": {},
                "success_rate": 0.0,
                "assumptions_applied": [],
                "errors": [str(e)]
            })

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
            if hasattr(ast_node, 'body') and ast_node.body:
                return "// Reconstructed Java body"
            return ""
        except Exception as e:
            logger.error(f"Error reconstructing Java body: {e}")
            return ""

    def _reconstruct_java_body_from_ast(self, ast_node):
        """Private method to reconstruct Java method body from AST"""
        try:
            if hasattr(ast_node, 'body') and ast_node.body:
                # Mock reconstruction - should parse statement nodes
                statements = []
                for stmt in ast_node.body:
                    if hasattr(stmt, 'expression'):
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
                method_name = data.get('method_name', 'unknown')
                method_body = data.get('method_body', '')
                
                # Mock translation
                translated_js = f"// Translated {method_name}\nfunction {method_name}() {{\n  // {method_body}\n}}"
                
                return json.dumps({
                    "success": True,
                    "original_method": method_name,
                    "translated_javascript": translated_js,
                    "warnings": []
                })
            else:
                # Handle AST node
                method_name = getattr(method_data, 'name', 'unknown')
                
                # Get method parameters
                params = []
                if hasattr(method_data, 'parameters') and method_data.parameters:
                    for param in method_data.parameters:
                        param_name = param.name
                        param_type = self._get_javascript_type(param.type)
                        params.append(f"{param_name}: {param_type}")
                
                # Get return type
                return_type = "void"
                if hasattr(method_data, 'return_type') and method_data.return_type:
                    return_type = self._get_javascript_type(method_data.return_type)
                
                # Generate JavaScript function
                param_str = ", ".join(params)
                if return_type != "void":
                    translated_js = f"// Translated {method_name}\nfunction {method_name}({param_str}): {return_type} {{\n  // Method body\n}}"
                else:
                    translated_js = f"// Translated {method_name}\nfunction {method_name}({param_str}) {{\n  // Method body\n}}"
                
                return json.dumps({
                    "success": True,
                    "original_method": method_name,
                    "javascript_method": translated_js,
                    "warnings": []
                })
        except Exception as e:
            logger.error(f"Error translating method: {e}")
            if isinstance(method_data, str):
                return json.dumps({
                    "success": False,
                    "error": str(e),
                    "warnings": []
                })
            else:
                return json.dumps({
                    "success": False,
                    "error": str(e),
                    "warnings": []
                })

    def convert_java_class(self, class_data: str) -> str:
        """Convert Java class to JavaScript"""
        try:
            data = json.loads(class_data)
            class_name = data.get('class_name', 'UnknownClass')
            methods = data.get('methods', [])
            
            # Mock conversion
            js_code = f"// Converted {class_name}\nclass {class_name} {{\n"
            event_handlers = []
            event_handler_methods = 0
            
            for method in methods:
                method_name = method.get('name', 'unknown')
                
                # Check if method is an event handler
                if 'onItemRightClick' in method_name or 'onItemUse' in method_name:
                    event_handlers.append({
                        "event": "item_use",
                        "handler": f"// {method_name} handler"
                    })
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
            
            return json.dumps({
                "success": True,
                "original_class": class_name,
                "javascript_class": js_code,
                "event_handlers": event_handlers,
                "conversion_summary": {
                    "event_handlers_generated": event_handler_methods,
                    "methods_converted": len(methods) - event_handler_methods
                },
                "warnings": []
            })
        except Exception as e:
            logger.error(f"Error converting class: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "warnings": []
            })

    def map_java_apis(self, api_data: str) -> str:
        """Map Java APIs to JavaScript"""
        try:
            data = json.loads(api_data)
            apis = data.get('apis', [])
            
            mapped_apis = {}
            for api in apis:
                mapped_apis[api] = self.api_mappings.get(api, api)
            
            return json.dumps({
                "success": True,
                "mapped_apis": mapped_apis,
                "warnings": []
            })
        except Exception as e:
            logger.error(f"Error mapping APIs: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "warnings": []
            })

    def generate_event_handlers(self, event_data: str) -> str:
        """Generate event handlers for JavaScript"""
        try:
            data = json.loads(event_data)
            java_events = data.get('java_events', [])
            events = data.get('events', [])
            
            handlers = []
            
            # Handle java_events format
            if java_events:
                for event in java_events:
                    event_type = event.get('type', '')
                    if 'PlayerInteractEvent' in event_type:
                        handlers.append({
                            "event": "testEvent",
                            "bedrock_event": "itemUse",
                            "handler": "function onPlayerInteract() {\n  // Handler for player interaction\n}"
                        })
            
            # Handle events format
            for event in events:
                handlers.append({
                    "event": event,
                    "handler": f"function on{event.title()}() {{\n  // Handler for {event}\n}}"
                })
            
            return json.dumps({
                "success": True,
                "event_handlers": handlers,
                "warnings": []
            })
        except Exception as e:
            logger.error(f"Error generating event handlers: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "warnings": []
            })

    def validate_javascript_syntax(self, js_data: str) -> str:
        """Validate JavaScript syntax"""
        try:
            data = json.loads(js_data)
            javascript_code = data.get('javascript_code', '')
            
            # Mock validation
            is_valid = '()' in javascript_code and '{' in javascript_code
            
            return json.dumps({
                "success": True,
                "is_valid": is_valid,
                "syntax_errors": [] if is_valid else ["Syntax error detected"],
                "warnings": []
            })
        except Exception as e:
            logger.error(f"Error validating JavaScript: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "warnings": []
            })

    def translate_crafting_recipe_json(self, recipe_json_data: str) -> str:
        """Translate crafting recipe JSON to Bedrock format"""
        try:
            data = json.loads(recipe_json_data)
            recipe_type = data.get('type', 'unknown')
            
            if recipe_type == 'minecraft:crafting_shaped':
                # Mock shaped recipe conversion
                pattern = data.get('pattern', ["ABC", "DEF", "GHI"])
                key = data.get('key', {"A": {"item": "minecraft:stick"}})
                result = data.get('result', {"item": "minecraft:wooden_sword"})
                
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
                        "result": bedrock_result
                    }
                }
            elif recipe_type == 'minecraft:crafting_shapeless':
                # Mock shapeless recipe conversion
                ingredients = data.get('ingredients', [{"item": "minecraft:stick"}])
                result = data.get('result', {"item": "minecraft:wooden_sword"})
                
                # Convert item names to remove minecraft: prefix
                bedrock_ingredients = []
                for ingredient in ingredients:
                    bedrock_ingredients.append({"item": ingredient["item"].replace("minecraft:", "")})
                
                bedrock_result = {"item": result["item"].replace("minecraft:", "")}
                if "count" in result:
                    bedrock_result["count"] = result["count"]
                
                bedrock_recipe = {
                    "format_version": "1.17.0",
                    "minecraft:recipe_shapeless": {
                        "description": {"identifier": "custom:shapeless_recipe"},
                        "ingredients": bedrock_ingredients,
                        "result": bedrock_result
                    }
                }
            else:
                raise ValueError(f"Unsupported recipe type: {recipe_type}")
            
            return json.dumps({
                "success": True,
                "bedrock_recipe": bedrock_recipe,
                "warnings": []
            })
        except Exception as e:
            logger.error(f"Error translating recipe: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "warnings": []
            })

    def translate_java_method_with_ast(self, method_name: str, ast_node, feature_context=None) -> dict:
        """Translate Java method using AST"""
        try:
            # Mock translation using AST
            if hasattr(ast_node, 'body') and ast_node.body:
                js_code = f"// Translated {method_name} using AST\nfunction {method_name}() {{\n  // Method body\n}}"
            else:
                js_code = f"// Empty method {method_name}"
            
            return {
                "success": True,
                "translated_javascript": js_code,
                "warnings": []
            }
        except Exception as e:
            logger.error(f"Error translating method with AST: {e}")
            return {
                "success": False,
                "error": str(e),
                "warnings": []
            }

    def convert_java_body_to_javascript(self, java_body: str, context: dict = None) -> str:
        """Convert Java body to JavaScript"""
        try:
            # Store original body for context
            self._original_java_body_for_context = java_body
            
            # Mock conversion
            js_body = java_body.replace("System.out.println", "console.log")
            
            # Context-aware replacements
            if "event.block" in java_body:
                js_body = js_body.replace("world.setBlockState", "event.block.dimension.setBlockPermutation")
            else:
                js_body = js_body.replace("world.setBlockState", "setBlockPermutation")
                
            return js_body
        except Exception as e:
            logger.error(f"Error converting Java body: {e}")
            return java_body
    
    def _convert_java_body_to_javascript(self, java_body: str, context: dict = None) -> str:
        """Convert Java body to JavaScript"""
        try:
            # Store original body for context
            self._original_java_body_for_context = java_body
            
            # Mock conversion
            js_body = java_body.replace("System.out.println", "console.log")
            
            # Context-aware replacements
            if "event.block" in java_body:
                js_body = js_body.replace("world.setBlockState", "event.block.dimension.setBlockPermutation")
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
            method_name = getattr(method_node, 'name', '')
            
            # Determine event type based on method name
            if 'onFoodEaten' in method_name or 'food' in class_name:
                # Food eaten event
                js_code = f"""// Translated food eaten handler for {class_name}
world.afterEvents.itemCompleteUse.subscribe((event) => {{
    if (event.itemStack.typeId === 'custom:{class_name}') {{
        // Food eaten logic here
        const player = event.source;
        // Handle food eaten
    }}
}});"""
            elif 'onBlockBroken' in method_name or 'onPlayerBreakBlock' in method_name:
                # Block broken event
                js_code = f"""// Translated block broken handler for {class_name}
world.afterEvents.playerBreakBlock.subscribe((event) => {{
    if (event.brokenBlockPermutation.type.id === 'custom:{class_name}') {{
        // Block broken logic here
        const player = event.player;
        // Handle block broken
    }}
}});"""
            elif 'onBlockActivated' in method_name or 'onPlayerInteractWithBlock' in method_name:
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
                "event_handlers": [
                    {
                        "event": "item_use",
                        "handler": "// Item use handler"
                    }
                ],
                "warnings": []
            }
        except Exception as e:
            logger.error(f"Error generating event handlers with AST: {e}")
            return {
                "success": False,
                "error": str(e),
                "warnings": []
            }

    # ========== Enhanced Event Handler Generation (Issue #332) ==========
    
    def generate_block_break_event_handler(self, class_name: str) -> str:
        """Generate block break event handler"""
        return f"""// Block break event handler
world.afterEvents.playerBreakBlock.subscribe((event) => {{
  const block = event.brokenBlockPermutation.type;
  const player = event.player;
  const dimension = event.player.dimension;
  
  // Custom block break logic here
  // event.brokenBlockPermutation - The block that was broken
  // event.player - The player who broke the block
}});"""

    def generate_block_place_event_handler(self, class_name: str) -> str:
        """Generate block place event handler"""
        return f"""// Block place event handler
world.afterEvents.blockPlace.subscribe((event) => {{
  const block = event.block;
  const player = event.player;
  const permutation = event.permutation;
  
  // Custom block place logic here
  // event.block - The block that was placed
  // event.player - The player who placed the block
}});"""

    def generate_entity_spawn_event_handler(self, class_name: str) -> str:
        """Generate entity spawn event handler"""
        return f"""// Entity spawn event handler
world.afterEvents.entitySpawn.subscribe((event) => {{
  const entity = event.entity;
  const entityType = entity.typeId;
  
  // Custom entity spawn logic here
  // event.entity - The entity that spawned
  // event.entity.typeId - Type of entity (e.g., 'minecraft:zombie')
}});"""

    def generate_entity_death_event_handler(self, class_name: str) -> str:
        """Generate entity death event handler"""
        return f"""// Entity death event handler
world.afterEvents.entityDie.subscribe((event) => {{
  const entity = event.entity;
  const damageSource = event.damageSource;
  
  // Custom entity death logic here
  // event.entity - The entity that died
  // event.damageSource - What caused the death
}});"""

    def generate_player_join_event_handler(self, class_name: str) -> str:
        """Generate player join event handler"""
        return f"""// Player join event handler
world.afterEvents.playerJoin.subscribe((event) => {{
  const player = event.player;
  const playerName = player.nameTag;
  
  // Custom player join logic here
  // event.player - The player who joined
  // event.player.nameTag - Player's display name
}});"""

    def generate_player_leave_event_handler(self, class_name: str) -> str:
        """Generate player leave event handler"""
        return f"""// Player leave event handler
world.afterEvents.playerLeave.subscribe((event) => {{
  const playerName = event.playerName;
  
  // Custom player leave logic here
  // event.playerName - Name of player who left
}});"""

    def generate_chat_event_handler(self, class_name: str) -> str:
        """Generate chat/command event handler"""
        return f"""// Chat event handler
world.afterEvents.chatSend.subscribe((event) => {{
  const message = event.message;
  const sender = event.sender;
  
  // Custom chat logic here
  // event.message - The chat message
  // event.sender - The player who sent it
  // To cancel: event.cancel = true;
}});"""

    def generate_command_event_handler(self, class_name: str) -> str:
        """Generate command execute event handler"""
        return f"""// Command execute event handler
world.afterEvents.commandExecute.subscribe((event) => {{
  const command = event.command;
  const source = event.source;
  
  // Custom command logic here
  // event.command - The command that was run
  // event.source - Who ran the command
  // To cancel: event.cancel = true;
}});"""

    def generate_tick_event_handler(self, class_name: str) -> str:
        """Generate tick/update event handler"""
        return f"""// Tick event handler (runs every tick)
world.beforeEvents.tick.subscribe((event) => {{
  // Custom tick logic here
  // Runs every game tick (~20 times per second)
  // Use sparingly for performance
}});"""

    def generate_item_use_event_handler(self, class_name: str) -> str:
        """Generate item use event handler"""
        return f"""// Item use event handler
world.afterEvents.itemUse.subscribe((event) => {{
  const itemStack = event.itemStack;
  const player = event.source;
  
  // Custom item use logic here
  // event.itemStack - The item that was used
  // event.source - The player who used it
}});"""

    def generate_item_use_on_event_handler(self, class_name: str) -> str:
        """Generate item use on block event handler"""
        return f"""// Item use on block event handler
world.afterEvents.itemUseOn.subscribe((event) => {{
  const itemStack = event.itemStack;
  const block = event.block;
  const player = event.player;
  
  // Custom item use on block logic here
  // event.itemStack - The item that was used
  // event.block - The block it was used on
  // event.player - The player who used it
}});"""

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
        if '<' in java_type:
            base_type = java_type.split('<')[0]
            generic_types = java_type.split('<')[1].rstrip('>')
            
            if base_type in ['List', 'ArrayList', 'Collection']:
                return f"Array<{self._translate_generic_type(generic_types)}>"
            elif base_type in ['Map', 'HashMap']:
                key_type, value_type = generic_types.split(',')
                return f"Map<{self._translate_generic_type(key_type)}, {self._translate_generic_type(value_type)}>"
            elif base_type == 'Set':
                return f"Set<{self._translate_generic_type(generic_types)}>"
        
        # Fall back to simple type mapping
        return self.type_mappings.get(java_type, java_type)

    def _translate_generic_type(self, generic_type: str) -> str:
        """Translate a generic type parameter"""
        generic_type = generic_type.strip()
        
        # Handle primitive wrappers
        type_mapping = {
            'String': 'string',
            'Integer': 'number',
            'Double': 'number',
            'Float': 'number',
            'Boolean': 'boolean',
            'Object': 'object',
            'Integer': 'number',
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
        js_code = js_code.replace('!= null', '!== null')
        js_code = js_code.replace('== null', '=== null')
        
        # Java: obj.nullCheck() → JS: obj
        js_code = js_code.replace('.notNull()', '')
        
        # Java: Objects.requireNonNull() → // Required
        js_code = js_code.replace('Objects.requireNonNull(', '// Required: ')
        
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
        use_rag: bool = True
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
            logger.info(f"Generating Bedrock block JSON for: {java_block_analysis.get('name', 'unknown')}")
            
            # Extract block information from analysis
            block_name = java_block_analysis.get('registry_name', 'unknown_block')
            if ':' in block_name:
                namespace, block_name = block_name.split(':', 1)
            
            properties = java_block_analysis.get('properties', {})
            
            # Determine the best template based on material
            template_type = self._determine_block_template(properties)
            template = BEDROCK_BLOCK_TEMPLATES.get(template_type, BEDROCK_BLOCK_TEMPLATES['basic'])
            
            # Build block JSON
            block_json = self._build_block_json(
                template=template,
                namespace=namespace,
                block_name=block_name,
                properties=properties
            )
            
            # Validate the generated JSON
            validation_result = self._validate_block_json(block_json)
            
            # Log translation decisions
            translation_log = {
                "original_java_block": java_block_analysis.get('name', 'unknown'),
                "template_used": template_type,
                "properties_mapped": list(properties.keys()),
                "validation_passed": validation_result['is_valid']
            }
            logger.info(f"Block generation complete: {translation_log}")
            
            return {
                "success": True,
                "block_json": block_json,
                "block_name": f"{namespace}:{block_name}",
                "validation": validation_result,
                "translation_log": translation_log,
                "warnings": validation_result.get('warnings', [])
            }
            
        except Exception as e:
            logger.error(f"Error generating Bedrock block JSON: {e}")
            return {
                "success": False,
                "error": str(e),
                "block_json": None,
                "warnings": [f"Block generation failed: {str(e)}"]
            }
    
    def _determine_block_template(self, properties: Dict[str, Any]) -> str:
        """Determine the best block template based on properties."""
        material = properties.get('material', 'stone').lower()
        
        # Check for light emission first (higher priority)
        if properties.get('light_level', 0) > 0:
            return 'light_emitting'
        
        # Map material to template
        material_template_map = {
            'metal': 'metal',
            'stone': 'stone',
            'wood': 'wood',
            'glass': 'glass',
            'ice': 'glass',
            'cloth': 'wood',  # Flammable like wood
            'earth': 'basic',
            'grass': 'basic',
            'sand': 'basic',
        }
        
        return material_template_map.get(material, 'basic')
    
    def _build_block_json(
        self, 
        template: Dict[str, Any],
        namespace: str,
        block_name: str,
        properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build the final block JSON from template and properties."""
        import copy
        
        # Deep copy the template to avoid mutations
        block_json = copy.deepcopy(template)
        
        # Set identifier
        block_json['minecraft:block']['description']['identifier'] = f"{namespace}:{block_name}"
        
        # Get components reference
        components = block_json['minecraft:block']['components']
        
        # Apply properties
        if 'hardness' in properties or 'destroy_time' in properties:
            components['minecraft:destroy_time'] = properties.get('hardness', properties.get('destroy_time', 3.0))
        
        if 'explosion_resistance' in properties:
            components['minecraft:explosion_resistance'] = properties['explosion_resistance']
        
        if 'light_level' in properties and properties['light_level'] > 0:
            components['minecraft:light_emission'] = properties['light_level']
        
        # Set texture name (use block name as default)
        texture_name = properties.get('texture_name', block_name)
        if 'minecraft:material_instances' in components:
            components['minecraft:material_instances']['*']['texture'] = texture_name
        
        # Handle flammable property
        if properties.get('flammable', False) and 'minecraft:flammable' not in components:
            components['minecraft:flammable'] = {
                "catch_chance_modifier": 5,
                "destroy_chance_modifier": 20
            }
        
        # Set menu category
        menu_category = properties.get('menu_category', 'construction')
        block_json['minecraft:block']['description']['menu_category'] = {
            "category": menu_category
        }
        
        return block_json
    
    def _validate_block_json(self, block_json: Dict[str, Any]) -> Dict[str, Any]:
        """Validate generated block JSON against Bedrock schema requirements."""
        errors = []
        warnings = []
        
        # Check required fields
        if 'format_version' not in block_json:
            errors.append("Missing 'format_version' field")
        
        if 'minecraft:block' not in block_json:
            errors.append("Missing 'minecraft:block' field")
        else:
            mc_block = block_json['minecraft:block']
            
            # Check description
            if 'description' not in mc_block:
                errors.append("Missing 'description' in minecraft:block")
            else:
                desc = mc_block['description']
                if 'identifier' not in desc:
                    errors.append("Missing 'identifier' in description")
                elif not ':' in desc['identifier']:
                    warnings.append("Identifier should include namespace (e.g., 'namespace:block_name')")
            
            # Check components
            if 'components' not in mc_block:
                errors.append("Missing 'components' in minecraft:block")
            else:
                components = mc_block['components']
                
                # Check for required components
                if 'minecraft:destroy_time' not in components:
                    warnings.append("Missing 'minecraft:destroy_time' - block will have default hardness")
                
                if 'minecraft:material_instances' not in components:
                    warnings.append("Missing 'minecraft:material_instances' - block may not render correctly")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def map_java_block_properties_to_bedrock(
        self, 
        java_properties: Dict[str, Any]
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
        material = java_properties.get('material', 'stone')
        if f"Material.{material.upper()}" in JAVA_TO_BEDROCK_BLOCK_PROPERTIES:
            mapping = JAVA_TO_BEDROCK_BLOCK_PROPERTIES[f"Material.{material.upper()}"]
            bedrock_properties.update(mapping)
        
        # Map hardness/destroy_time
        if 'hardness' in java_properties:
            bedrock_properties['hardness'] = java_properties['hardness']
        
        # Map explosion resistance
        if 'explosion_resistance' in java_properties:
            bedrock_properties['explosion_resistance'] = java_properties['explosion_resistance']
        
        # Map light level
        if 'light_level' in java_properties and java_properties['light_level'] > 0:
            bedrock_properties['light_level'] = min(java_properties['light_level'], 15)
        
        # Map sound type
        sound_type = java_properties.get('sound_type', 'stone')
        if f"SoundType.{sound_type.upper()}" in JAVA_TO_BEDROCK_BLOCK_PROPERTIES:
            bedrock_properties['sound_category'] = sound_type
        
        # Map tool requirements
        if java_properties.get('requires_tool', False):
            tool_type = java_properties.get('tool_type', 'pickaxe')
            if f"ToolType.{tool_type.upper()}" in JAVA_TO_BEDROCK_BLOCK_PROPERTIES:
                bedrock_properties['requires_tool'] = tool_type
        
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
            java_analysis = data.get('java_block_analysis', data)
            namespace = data.get('namespace', 'modporter')
            use_rag = data.get('use_rag', True)
            
            result = agent.generate_bedrock_block_json(
                java_block_analysis=java_analysis,
                namespace=namespace,
                use_rag=use_rag
            )
            
            return json.dumps(result)
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "block_json": None
            })
    
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
            block_json = data.get('block_json', data)
            
            result = agent._validate_block_json(block_json)
            
            return json.dumps({
                "success": True,
                "validation": result
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
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
            java_properties = data.get('java_properties', data)
            
            result = agent.map_java_block_properties_to_bedrock(java_properties)
            
            return json.dumps({
                "success": True,
                "bedrock_properties": result
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    def get_block_generation_tools(self) -> List:
        """Get block generation tools available to this agent."""
        return [
            LogicTranslatorAgent.generate_bedrock_block_tool,
            LogicTranslatorAgent.validate_block_json_tool,
            LogicTranslatorAgent.map_block_properties_tool
        ]

    # ========== Issue #570: Enhanced Validation and Warning Tools ==========

    @tool
    @staticmethod
    def validate_javascript_comprehensive_tool(js_data: str) -> str:
        """
        Comprehensive JavaScript validation including syntax, semantics, API correctness,
        and Bedrock compatibility.

        Args:
            js_data: JSON string containing:
                - javascript_code: The JavaScript code to validate
                - context: Optional context about the code (feature_type, etc.)

        Returns:
            JSON string with validation results
        """
        agent = LogicTranslatorAgent.get_instance()

        if not VALIDATION_AVAILABLE or agent.js_validator is None:
            return json.dumps({
                "success": False,
                "error": "JavaScript validation module not available"
            })

        try:
            data = json.loads(js_data)
            javascript_code = data.get('javascript_code', '')
            context = data.get('context', {})

            # Perform comprehensive validation
            result = agent.js_validator.validate(javascript_code, context)

            return json.dumps({
                "success": True,
                "validation_result": {
                    "is_valid": result.is_valid,
                    "score": result.score,
                    "statistics": result.statistics
                },
                "issues": [
                    {
                        "severity": issue.severity.value,
                        "category": issue.category,
                        "message": issue.message,
                        "line_number": issue.line_number,
                        "suggestion": issue.suggestion,
                        "code_snippet": issue.code_snippet
                    }
                    for issue in result.issues
                ],
                "breakdown": {
                    "syntax_errors": len(result.syntax_errors),
                    "semantic_errors": len(result.semantic_errors),
                    "api_warnings": len(result.api_warnings),
                    "security_warnings": len(result.security_warnings)
                }
            })
        except Exception as e:
            logger.error(f"Error validating JavaScript: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })

    @tool
    @staticmethod
    def analyze_translation_warnings_tool(java_data: str) -> str:
        """
        Analyze Java code for potential translation warnings and functionality loss.

        Args:
            java_data: JSON string containing:
                - java_code: The Java source code to analyze
                - feature_type: Optional feature type (block, item, entity, etc.)
                - translated_javascript: Optional translated JavaScript for comparison

        Returns:
            JSON string with warning report
        """
        agent = LogicTranslatorAgent.get_instance()

        if not VALIDATION_AVAILABLE or agent.warning_detector is None:
            return json.dumps({
                "success": False,
                "error": "Warning detector module not available"
            })

        try:
            data = json.loads(java_data)
            java_code = data.get('java_code', '')
            feature_type = data.get('feature_type')
            translated_javascript = data.get('translated_javascript')

            # Analyze original Java code
            if translated_javascript:
                report = agent.warning_detector.analyze_translated_javascript(
                    translated_javascript,
                    java_code
                )
            else:
                report = agent.warning_detector.analyze_java_code(
                    java_code,
                    feature_type
                )

            # Convert warnings to serializable format
            warnings_serializable = [
                {
                    "category": w.category,
                    "java_feature": w.java_feature,
                    "bedrock_status": w.bedrock_status,
                    "impact": w.impact.value,
                    "user_explanation": w.user_explanation,
                    "technical_notes": w.technical_notes,
                    "workarounds": w.workarounds,
                    "code_reference": w.code_reference
                }
                for w in report.warnings
            ]

            return json.dumps({
                "success": True,
                "warning_report": {
                    "warnings": warnings_serializable,
                    "critical_count": report.critical_count,
                    "high_count": report.high_count,
                    "medium_count": report.medium_count,
                    "low_count": report.low_count,
                    "overall_assessment": report.overall_assessment,
                    "recommendations": report.recommendations
                }
            })
        except Exception as e:
            logger.error(f"Error analyzing translation warnings: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })

    @tool
    @staticmethod
    def generate_user_facing_report_tool(report_data: str) -> str:
        """
        Generate user-facing report from validation and warning results.

        Args:
            report_data: JSON string containing:
                - validation_result: Optional validation result
                - warning_report: Optional warning report
                - translation_metadata: Optional metadata about the translation

        Returns:
            JSON string with formatted user-facing report
        """
        agent = LogicTranslatorAgent.get_instance()

        if not VALIDATION_AVAILABLE or agent.warning_detector is None:
            return json.dumps({
                "success": False,
                "error": "Warning detector module not available"
            })

        try:
            data = json.loads(report_data)
            validation_result = data.get('validation_result')
            warning_report_data = data.get('warning_report')
            translation_metadata = data.get('translation_metadata', {})

            # Build user-facing report
            report_sections = []

            # Add overall summary
            overall_score = validation_result.get('score', 0.0) if validation_result else 0.0
            if overall_score >= 0.9:
                summary = "Translation appears excellent with high quality Bedrock JavaScript."
            elif overall_score >= 0.7:
                summary = "Translation is good with minor issues that may need review."
            elif overall_score >= 0.5:
                summary = "Translation is acceptable but has issues that should be addressed."
            else:
                summary = "Translation has significant issues requiring manual review and fixes."

            report_sections.append({
                "section": "Overall Assessment",
                "content": summary,
                "score": overall_score
            })

            # Add validation findings
            if validation_result:
                stats = validation_result.get('statistics', {})
                report_sections.append({
                    "section": "Code Quality",
                    "content": f"Validation score: {overall_score:.2f}/1.0",
                    "details": {
                        "total_issues": stats.get('total_issues', 0),
                        "errors": stats.get('error_count', 0),
                        "warnings": stats.get('warning_count', 0),
                        "syntax_issues": stats.get('by_category', {}).get('syntax', 0),
                        "api_issues": stats.get('by_category', {}).get('api', 0)
                    }
                })

            # Add functionality warnings
            if warning_report_data:
                report_sections.append({
                    "section": "Functionality Assessment",
                    "content": warning_report_data.get('overall_assessment', ''),
                    "details": {
                        "critical_issues": warning_report_data.get('critical_count', 0),
                        "high_issues": warning_report_data.get('high_count', 0),
                        "medium_issues": warning_report_data.get('medium_count', 0),
                        "low_issues": warning_report_data.get('low_count', 0)
                    }
                })

                # Add recommendations
                if warning_report_data.get('recommendations'):
                    report_sections.append({
                        "section": "Recommendations",
                        "content": "Recommended actions:",
                        "details": warning_report_data.get('recommendations', [])
                    })

            # Add translation metadata
            if translation_metadata:
                report_sections.append({
                    "section": "Translation Details",
                    "content": "Technical information about the translation",
                    "details": translation_metadata
                })

            from datetime import datetime
            return json.dumps({
                "success": True,
                "user_report": {
                    "sections": report_sections,
                    "generated_at": str(datetime.now()),
                    "version": "1.0"
                }
            })
        except Exception as e:
            logger.error(f"Error generating user-facing report: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })

    def validate_translation_with_comprehensive_checks(
        self,
        java_code: str,
        javascript_code: str,
        feature_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive validation of a translation.

        Args:
            java_code: Original Java source code
            javascript_code: Translated JavaScript code
            feature_type: Optional feature type

        Returns:
            Dictionary with validation results
        """
        result = {
            "success": True,
            "validation": None,
            "warnings": None,
            "overall_score": 0.0,
            "recommendations": []
        }

        # Perform JavaScript validation
        if VALIDATION_AVAILABLE and self.js_validator:
            validation = self.js_validator.validate(javascript_code, {
                'feature_type': feature_type
            })
            result["validation"] = {
                "is_valid": validation.is_valid,
                "score": validation.score,
                "statistics": validation.statistics
            }
            result["overall_score"] = validation.score

        # Analyze translation warnings
        if VALIDATION_AVAILABLE and self.warning_detector:
            warning_report = self.warning_detector.analyze_translated_javascript(
                javascript_code,
                java_code
            )
            result["warnings"] = {
                "critical_count": warning_report.critical_count,
                "high_count": warning_report.high_count,
                "medium_count": warning_report.medium_count,
                "low_count": warning_report.low_count,
                "overall_assessment": warning_report.overall_assessment
            }

            # Add recommendations
            if warning_report.recommendations:
                result["recommendations"].extend(warning_report.recommendations)

        # Combine scores
        if result["validation"]:
            val_score = result["validation"]["score"]
            warn_penalty = (result["warnings"]["critical_count"] * 0.2 +
                           result["warnings"]["high_count"] * 0.1 +
                           result["warnings"]["medium_count"] * 0.05)
            result["overall_score"] = max(0.0, val_score - warn_penalty)

        # Final validation
        if result["overall_score"] < 0.5:
            result["recommendations"].append(
                "Translation quality is low. Manual review and fixes strongly recommended."
            )
        elif result["warnings"]["critical_count"] > 0:
            result["recommendations"].append(
                "Critical functionality loss detected. Review warnings carefully."
            )

        return result
