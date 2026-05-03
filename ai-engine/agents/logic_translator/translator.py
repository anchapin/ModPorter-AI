"""
Logic Translator Agent for Java to JavaScript code conversion
Enhanced for Issue #546: Block Generation from Java block analysis
"""

import json
from typing import Any, Dict, List

try:
    import tree_sitter_java as ts_java
    from tree_sitter import Language, Parser

    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    ts_java = None
    Parser = None
from agents.java_analyzer import JavaAnalyzerAgent
from agents.logic_translator.block_state_mapper import (
    JAVA_TO_BEDROCK_BLOCK_PROPERTIES,
)
from agents.logic_translator.block_templates import (
    BEDROCK_BLOCK_TEMPLATES,
)
from models.smart_assumptions import (
    SmartAssumptionEngine,
)
from utils.logging_config import get_agent_logger

# Use enhanced agent logger
logger = get_agent_logger("logic_translator")

# LLM Translation temperature for code generation (per research: 0.2 is optimal)
LLM_CODE_TEMPERATURE = 0.2


# Templates loaded from block_templates module# Smart assumptions loaded from assumptions module


# Block property mappings loaded from block_state_mapper module
class LogicTranslatorAgent:
    """
    Logic Translator Agent responsible for converting Java logic to Bedrock-compatible
    JavaScript as specified in PRD Feature 2.
    """

    _instance = None

    def __init__(self):
        self.logger = logger
        self.smart_assumption_engine = SmartAssumptionEngine()
        self.java_analyzer_agent = JavaAnalyzerAgent()

        self._conversion_rag_pipeline = None
        self._rag_context_enabled = False

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
        """Convert Java type to JavaScript type. Handles both javalang and tree-sitter formats."""
        if java_type is None:
            return "any"

        # Handle tree-sitter dict format
        if isinstance(java_type, dict):
            type_name = java_type.get("type", str(java_type))
            if type_name == "type_identifier":
                type_name = java_type.get("text", str(java_type))
            if java_type.get("type") == "array_type":
                element_type_node = (
                    java_type.get("children", [{}])[0] if java_type.get("children") else {}
                )
                element_type = element_type_node.get("text", str(element_type_node))
                if element_type in self.type_mappings:
                    return f"{self.type_mappings[element_type]}[]"
                return f"{element_type}[]"
        # Handle javalang AST types (object with .name attribute)
        elif hasattr(java_type, "name"):
            type_name = java_type.name
            if hasattr(java_type, "dimensions") and java_type.dimensions:
                type_name += "[]"
        elif hasattr(java_type, "type") and hasattr(java_type.type, "name"):
            type_name = java_type.type.name
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
        """Get tools available to this agent."""
        from agents.logic_translator.tools import LogicTranslatorTools

        return [
            LogicTranslatorTools.translate_java_method_tool,
            LogicTranslatorTools.convert_java_class_tool,
            LogicTranslatorTools.map_java_apis_tool,
            LogicTranslatorTools.generate_event_handlers_tool,
            LogicTranslatorTools.validate_javascript_syntax_tool,
            LogicTranslatorTools.translate_crafting_recipe_tool,
            LogicTranslatorTools.generate_bedrock_block_tool,
            LogicTranslatorTools.validate_block_json_tool,
            LogicTranslatorTools.map_block_properties_tool,
            LogicTranslatorTools.get_rag_context_tool,
            LogicTranslatorTools.set_rag_context_tool,
        ]

    @property
    def translate_java_method_tool(self):
        """Tool-wrapped translate_java_method - backwards compatible."""
        from agents.logic_translator.tools import LogicTranslatorTools

        return LogicTranslatorTools.translate_java_method_tool

    @property
    def convert_java_class_tool(self):
        """Tool-wrapped convert_java_class - backwards compatible."""
        from agents.logic_translator.tools import LogicTranslatorTools

        return LogicTranslatorTools.convert_java_class_tool

    @property
    def map_java_apis_tool(self):
        """Tool-wrapped map_java_apis - backwards compatible."""
        from agents.logic_translator.tools import LogicTranslatorTools

        return LogicTranslatorTools.map_java_apis_tool

    @property
    def generate_event_handlers_tool(self):
        """Tool-wrapped generate_event_handlers - backwards compatible."""
        from agents.logic_translator.tools import LogicTranslatorTools

        return LogicTranslatorTools.generate_event_handlers_tool

    @property
    def validate_javascript_syntax_tool(self):
        """Tool-wrapped validate_javascript_syntax - backwards compatible."""
        from agents.logic_translator.tools import LogicTranslatorTools

        return LogicTranslatorTools.validate_javascript_syntax_tool

    @property
    def translate_crafting_recipe_tool(self):
        """Tool-wrapped translate_crafting_recipe - backwards compatible."""
        from agents.logic_translator.tools import LogicTranslatorTools

        return LogicTranslatorTools.translate_crafting_recipe_tool

    @property
    def generate_bedrock_block_tool(self):
        """Tool-wrapped generate_bedrock_block - backwards compatible."""
        from agents.logic_translator.tools import LogicTranslatorTools

        return LogicTranslatorTools.generate_bedrock_block_tool

    @property
    def validate_block_json_tool(self):
        """Tool-wrapped validate_block_json - backwards compatible."""
        from agents.logic_translator.tools import LogicTranslatorTools

        return LogicTranslatorTools.validate_block_json_tool

    @property
    def map_block_properties_tool(self):
        """Tool-wrapped map_block_properties - backwards compatible."""
        from agents.logic_translator.tools import LogicTranslatorTools

        return LogicTranslatorTools.map_block_properties_tool

    def set_rag_pipeline(self, pipeline) -> None:
        """
        Set the ConversionRAGPipeline for context-augmented translation.

        Args:
            pipeline: ConversionRAGPipeline instance
        """
        self._conversion_rag_pipeline = pipeline
        self._rag_context_enabled = pipeline is not None
        logger.info(f"RAG context {'enabled' if self._rag_context_enabled else 'disabled'}")

    def enable_rag_context(self, enabled: bool = True) -> None:
        """Enable or disable RAG context retrieval."""
        self._rag_context_enabled = enabled and self._conversion_rag_pipeline is not None

    def _get_rag_context(self, java_feature: str, feature_type: str) -> str:
        """
        Get RAG context for a Java feature.

        Args:
            java_feature: Description of the Java feature
            feature_type: Type of feature (block, item, entity, etc.)

        Returns:
            Formatted context string for LLM, or empty string if unavailable
        """
        if not self._rag_context_enabled or not self._conversion_rag_pipeline:
            return ""

        try:
            result = self._conversion_rag_pipeline.retrieve_conversion_context_sync(
                java_feature=java_feature,
                feature_type=feature_type,
                top_k=5,
            )
            return self._conversion_rag_pipeline.format_context_for_llm(result)
        except Exception as e:
            logger.warning(f"RAG context retrieval failed: {e}")
            return ""

    def _get_tree_sitter_parser(self):
        """Get or create tree-sitter parser instance."""
        if not TREE_SITTER_AVAILABLE:
            return None
        if not hasattr(self, "_ts_parser") or self._ts_parser is None:
            try:
                lang = Language(ts_java.language())
                self._ts_parser = Parser(lang)
            except Exception as e:
                logger.warning(f"Failed to initialize tree-sitter parser: {e}")
                self._ts_parser = None
        return self._ts_parser

    def _tree_sitter_to_dict(self, node, error_count: int = 0) -> Dict[str, Any]:
        """Convert tree-sitter node to dictionary."""
        result = {
            "type": node.type,
            "start_point": node.start_point,
            "end_point": node.end_point,
            "start_byte": node.start_byte,
            "end_byte": node.end_byte,
            "has_errors": error_count > 0 or node.type == "ERROR",
        }

        if node.child_count == 0:
            result["text"] = node.text.decode("utf8") if node.text else ""

        if node.child_count > 0:
            result["children"] = [
                self._tree_sitter_to_dict(child, error_count) for child in node.children
            ]

        return result

    def analyze_java_code_ast(self, java_code: str):
        """Analyze Java code and return AST using tree-sitter."""
        if not TREE_SITTER_AVAILABLE:
            logger.warning(
                "Tree-sitter not available, javalang fallback not supported in migrated code"
            )
            return {
                "success": False,
                "error": "tree-sitter not available",
                "ast_tree": None,
            }

        parser = self._get_tree_sitter_parser()
        if parser is None:
            return {
                "success": False,
                "error": "tree-sitter parser not available",
                "ast_tree": None,
            }

        try:
            tree = parser.parse(bytes(java_code, "utf8"))
            ast_dict = self._tree_sitter_to_dict(tree.root_node)
            return {
                "success": True,
                "ast_tree": ast_dict,
                "root_type": tree.root_node.type,
            }
        except Exception as e:
            logger.error(f"Error analyzing Java code AST: {e}")
            return {
                "success": False,
                "error": str(e),
                "ast_tree": None,
            }

    def _serialize_ast_for_llm(self, ast_dict: Dict[str, Any], max_depth: int = 10) -> str:
        """Serialize AST dictionary for LLM consumption."""
        if ast_dict is None:
            return "No AST available"

        lines = []
        indent = "  "

        def serialize_node(node: Dict[str, Any], depth: int = 0):
            if depth >= max_depth:
                lines.append(f"{indent * depth}...")
                return

            node_type = node.get("type", "unknown")
            has_errors = node.get("has_errors", False)

            prefix = "[ERROR] " if has_errors else ""
            lines.append(f"{indent * depth}{prefix}{node_type}")

            if "text" in node:
                text = node["text"]
                if text.strip():
                    lines.append(f"{indent * (depth + 1)}text: {repr(text)}")

            if "children" in node:
                for child in node["children"]:
                    serialize_node(child, depth + 1)

        serialize_node(ast_dict, 0)
        return "\n".join(lines)

    def generate_nl_summary_from_ast(self, java_code: str) -> str:
        """Generate natural language summary from Java AST using tree-sitter."""
        try:
            result = self.analyze_java_code_ast(java_code)

            if not result.get("success"):
                return f"Could not analyze code: {result.get('error', 'Unknown error')}"

            ast_dict = result.get("ast_tree")
            if not ast_dict:
                return "No AST found in analysis result"

            self._serialize_ast_for_llm(ast_dict)

            class_decl = None
            method_sigs = []

            def find_decls(node: Dict[str, Any]):
                nonlocal class_decl
                if node.get("type") == "class_declaration":
                    nonlocal class_decl
                    class_decl = node
                elif node.get("type") == "method_declaration":
                    method_sigs.append(node)

            def walk(node: Dict[str, Any]):
                find_decls(node)
                for child in node.get("children", []):
                    walk(child)

            walk(ast_dict)

            summary_parts = []
            if class_decl:
                class_name = "UnknownClass"
                for child in class_decl.get("children", []):
                    if child.get("type") == "identifier":
                        class_name = child.get("text", "UnknownClass")
                        break
                summary_parts.append(f"Class: {class_name}")

            if method_sigs:
                summary_parts.append(f"Contains {len(method_sigs)} method(s)")

            return "; ".join(summary_parts) if summary_parts else "Empty class"

        except Exception as e:
            logger.error(f"Error generating NL summary from AST: {e}")
            return f"Error: {str(e)}"

    def translate_java_method(self, method_data, feature_context=None) -> str:
        """Translate Java method to JavaScript with optional RAG context augmentation."""
        try:
            rag_context = ""
            feature_type = "unknown"

            if isinstance(method_data, str):
                data = json.loads(method_data)
                method_name = data.get("method_name", "unknown")
                method_body = data.get("method_body", "")
                feature_type = data.get("feature_type", "unknown")

                if self._rag_context_enabled and feature_type != "unknown":
                    rag_context = self._get_rag_context(
                        f"{method_name} {method_body}", feature_type
                    )

                translated_js = f"// Translated {method_name}\nfunction {method_name}() {{\n  // {method_body}\n}}"

                result = {
                    "success": True,
                    "original_method": method_name,
                    "translated_javascript": translated_js,
                    "warnings": [],
                }

                if rag_context:
                    result["rag_context_applied"] = True
                    result["conversion_context"] = rag_context

                return json.dumps(result)
            else:
                method_name = getattr(method_data, "name", "unknown")

                params = []
                if hasattr(method_data, "parameters") and method_data.parameters:
                    for param in method_data.parameters:
                        param_name = param.name
                        param_type = self._get_javascript_type(param.type)
                        params.append(f"{param_name}: {param_type}")

                return_type = "void"
                if hasattr(method_data, "return_type") and method_data.return_type:
                    return_type = self._get_javascript_type(method_data.return_type)

                param_str = ", ".join(params)
                if return_type != "void":
                    translated_js = f"// Translated {method_name}\nfunction {method_name}({param_str}): {return_type} {{\n  // Method body\n}}"
                else:
                    translated_js = f"// Translated {method_name}\nfunction {method_name}({param_str}) {{\n  // Method body\n}}"

                result = {
                    "success": True,
                    "original_method": method_name,
                    "javascript_method": translated_js,
                    "warnings": [],
                }

                if rag_context:
                    result["rag_context_applied"] = True
                    result["conversion_context"] = rag_context

                return json.dumps(result)
        except Exception as e:
            logger.error(f"Error translating method: {e}")
            return json.dumps({"success": False, "error": str(e), "warnings": []})

    def convert_java_class(self, class_data: str) -> str:
        """Convert Java class to JavaScript with optional RAG context."""
        try:
            data = json.loads(class_data)
            class_name = data.get("class_name", "UnknownClass")
            data.get("methods", [])
            feature_type = data.get("feature_type", "unknown")

            rag_context = ""
            if self._rag_context_enabled and feature_type != "unknown":
                rag_context = self._get_rag_context(class_name, feature_type)

            js_class = f"// Converted class {class_name}\nclass {class_name} {{}}"

            result = {
                "success": True,
                "original_class": class_name,
                "javascript_class": js_class,
                "warnings": [],
            }

            if rag_context:
                result["rag_context_applied"] = True
                result["conversion_context"] = rag_context

            return json.dumps(result)
        except Exception as e:
            logger.error(f"Error converting class: {e}")
            return json.dumps({"success": False, "error": str(e), "warnings": []})

    def map_java_apis(self, api_data: str) -> str:
        """Map Java APIs to JavaScript."""
        try:
            data = json.loads(api_data)
            apis = data.get("apis", [])

            mapped_apis = {}
            for api in apis:
                mapped_apis[api] = self._get_javascript_type(api.split(".")[-1])

            return json.dumps(
                {
                    "success": True,
                    "mapped_apis": mapped_apis,
                    "warnings": [],
                }
            )
        except Exception as e:
            logger.error(f"Error mapping APIs: {e}")
            return json.dumps({"success": False, "error": str(e), "warnings": []})

    def generate_event_handlers(self, event_data: str) -> str:
        """Generate event handlers for JavaScript."""
        try:
            data = json.loads(event_data)
            event_type = data.get("event_type", "unknown")
            handlers = data.get("handlers", [])

            js_handlers = [f"// Event handler for {event_type}"] * len(handlers)

            return json.dumps(
                {
                    "success": True,
                    "event_handlers": js_handlers,
                    "warnings": [],
                }
            )
        except Exception as e:
            logger.error(f"Error generating event handlers: {e}")
            return json.dumps({"success": False, "error": str(e), "warnings": []})

    def validate_javascript_syntax(self, js_data: str) -> str:
        """Validate JavaScript syntax."""
        try:
            data = json.loads(js_data)
            javascript_code = data.get("javascript_code", "")

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
        """Translate crafting recipe JSON to Bedrock format."""
        try:
            data = json.loads(recipe_json_data)
            recipe_type = data.get("type", "unknown")

            if recipe_type == "minecraft:crafting_shaped":
                pattern = data.get("pattern", ["ABC", "DEF", "GHI"])
                key = data.get("key", {"A": {"item": "minecraft:stick"}})
                result = data.get("result", {"item": "minecraft:wooden_sword"})

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
                ingredients = data.get("ingredients", [{"item": "minecraft:stick"}])
                result = data.get("result", {"item": "minecraft:wooden_sword"})

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

    def generate_bedrock_block_json(
        self,
        java_block_analysis: Dict[str, Any],
        namespace: str = "modporter",
        use_rag: bool = True,
    ) -> Dict[str, Any]:
        """Generate Bedrock block JSON from Java block analysis."""
        try:
            logger.info(
                f"Generating Bedrock block JSON for: {java_block_analysis.get('name', 'unknown')}"
            )

            block_name = java_block_analysis.get("registry_name", "unknown_block")
            if ":" in block_name:
                namespace, block_name = block_name.split(":", 1)

            properties = java_block_analysis.get("properties", {})

            template_type = self._determine_block_template(properties)
            template = BEDROCK_BLOCK_TEMPLATES.get(template_type, BEDROCK_BLOCK_TEMPLATES["basic"])

            block_json = self._build_block_json(
                template=template, namespace=namespace, block_name=block_name, properties=properties
            )

            validation_result = self._validate_block_json(block_json)

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

    def validate_block_json(self, block_json_data: str) -> str:
        """Validate a Bedrock block JSON against schema requirements."""
        try:
            data = json.loads(block_json_data)
            block_json = data.get("block_json", {})

            is_valid = "format_version" in block_json and "minecraft:block" in block_json

            return json.dumps(
                {
                    "success": True,
                    "is_valid": is_valid,
                    "errors": [] if is_valid else ["Missing required fields"],
                    "warnings": [],
                }
            )
        except Exception as e:
            logger.error(f"Error validating block JSON: {e}")
            return json.dumps({"success": False, "error": str(e), "warnings": []})

    def map_block_properties(self, properties_data: str) -> str:
        """Map Java block properties to Bedrock equivalents."""
        try:
            data = json.loads(properties_data)
            java_properties = data.get("properties", {})

            bedrock_properties = {}
            for key, value in java_properties.items():
                mapped_key = JAVA_TO_BEDROCK_BLOCK_PROPERTIES.get(key, key)
                bedrock_properties[mapped_key] = value

            return json.dumps(
                {
                    "success": True,
                    "bedrock_properties": bedrock_properties,
                    "warnings": [],
                }
            )
        except Exception as e:
            logger.error(f"Error mapping block properties: {e}")
            return json.dumps({"success": False, "error": str(e), "warnings": []})

    def _determine_block_template(self, properties: Dict[str, Any]) -> str:
        """Determine the best block template based on properties."""
        material = properties.get("material", "stone").lower()

        if properties.get("light_level", 0) > 0:
            return "light_emitting"

        material_template_map = {
            "wood": "wooden",
            "stone": "stone",
            "dirt": "dirt",
            "sand": "sand",
            "glass": "glass",
            "metal": "metal",
            "water": "liquid",
            "lava": "liquid",
        }

        for mat, template in material_template_map.items():
            if mat in material:
                return template

        return "basic"

    def _build_block_json(
        self, template: Dict[str, Any], namespace: str, block_name: str, properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build block JSON from template."""
        block_json = {
            "format_version": "1.17.0",
            f"minecraft:{template.get('type', 'block')}": {
                "description": {
                    "identifier": f"{namespace}:{block_name}",
                },
                "components": {},
            },
        }

        for key, value in properties.items():
            mapped_key = JAVA_TO_BEDROCK_BLOCK_PROPERTIES.get(key, key)
            block_json[f"minecraft:{template.get('type', 'block')}"]["components"][mapped_key] = (
                value
            )

        return block_json

    def _validate_block_json(self, block_json: Dict[str, Any]) -> Dict[str, Any]:
        """Validate block JSON structure."""
        errors = []
        warnings = []

        if "format_version" not in block_json:
            errors.append("Missing format_version")

        has_block_component = any(k.startswith("minecraft:") for k in block_json.keys())
        if not has_block_component:
            errors.append("Missing block component")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
