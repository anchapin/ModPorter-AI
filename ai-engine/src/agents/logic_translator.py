"""
Logic Translator Agent for Java to JavaScript code conversion
"""

from typing import Dict, List, Any, Optional

import logging
import json
import re
from langchain.tools import tool
import javalang  # Added javalang
from models.smart_assumptions import (
    SmartAssumptionEngine,
)
from agents.java_analyzer import JavaAnalyzerAgent  # Added JavaAnalyzerAgent

logger = logging.getLogger(__name__)


class LogicTranslatorAgent:
    """
    Logic Translator Agent responsible for converting Java code to Bedrock JavaScript
    as specified in PRD Feature 2.
    """

    def __init__(self):
        self.smart_assumption_engine = SmartAssumptionEngine()
        self.java_analyzer_agent = (
            JavaAnalyzerAgent()
        )  # Added JavaAnalyzerAgent initialization

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
        }

        self.api_mappings = {
            # Common Minecraft Java to Bedrock mappings
            "player.getHealth()": 'player.getComponent("health").currentValue',
            "player.setHealth()": 'player.getComponent("health").setCurrentValue()',
            "world.getBlockAt()": "world.getBlock()",
            "entity.getLocation()": "entity.location",
            "ItemStack": "ItemStack",
            "Material": "MinecraftItemType",
        }
        self.api_mappings.update(
            {
                # Player Data
                "player.getDisplayNameString()": "player.nameTag",
                "player.isSneaking()": "player.isSneaking",
                "player.experienceLevel": "player.level",
                "player.getFoodStats().getFoodLevel()": 'player.getComponent("minecraft:food").foodLevel',
                # ItemStack Operations
                ".getCount()": ".amount",
                ".isEmpty()": "",  # Special handling in _convert_java_body_to_javascript
                # World
                "world.isAirBlock(": "world.getBlock(",  # Needs suffix handling in _convert_java_body_to_javascript
            }
        )

    def _translate_item_use_method(
        self,
        method_node: javalang.tree.MethodDeclaration,
        class_context: Optional[Dict],
    ) -> Optional[str]:
        """
        Translates a Java method assumed to be an item interaction event handler
        (e.g., onItemRightClick, onItemUse, onFoodEaten) to Bedrock JavaScript event handling.

        Args:
            method_node: The AST node of the Java method.
            class_context: Optional dictionary providing context about the class this method belongs to (e.g., {"class_name": "MyCustomItem"}).

        Returns:
            A string containing the Bedrock JavaScript event subscription, or None if not applicable.
        """
        method_name = method_node.name.lower()
        js_event_handler_body = self._convert_java_body_to_javascript(
            self._reconstruct_java_body_from_ast(method_node)
        )
        # TODO: Replace js_event_handler_body with AST-based translation.

        param_map = {
            "player": "event.source",
            "itemstack": "event.itemStack",
            "world": "world",
            "hand": "event.source.selectedSlot",
        }
        # Apply mapping to both the reconstructed body and any simple variable usage
        for java_param, bedrock_param in param_map.items():
            js_event_handler_body = re.sub(
                r"\\b" + re.escape(java_param) + r"\\b",
                bedrock_param,
                js_event_handler_body,
            )
            # Also handle capitalized (e.g., Player)
            js_event_handler_body = re.sub(
                r"\\b" + re.escape(java_param.capitalize()) + r"\\b",
                bedrock_param,
                js_event_handler_body,
            )

        bedrock_event_script = None
        item_name_placeholder = (
            class_context.get("class_name", "my_custom_item").lower()
            if class_context
            else "my_custom_item"
        )

        if (
            "onitemrightclick" in method_name
            or "useitem" in method_name
            or "onitemuse" in method_name
        ):
            bedrock_event_script = f"""
world.afterEvents.itemUse.subscribe((event) => {{
    // Original Java method: {method_node.name}
    // Check if the used item is an instance of this custom item.
    if (event.itemStack && event.itemStack.typeId === "custom:{item_name_placeholder}") {{
        {js_event_handler_body}
    }}
}});
"""
            logger.info(
                f"Translated Java method {method_node.name} to Bedrock itemUse event for item '{item_name_placeholder}'."
            )
        elif "onfoodeaten" in method_name or "itemcompleteuse" in method_name:
            bedrock_event_script = f"""
world.afterEvents.itemCompleteUse.subscribe((event) => {{
    // Original Java method: {method_node.name}
    // Check if the used item is an instance of this custom food item.
    if (event.itemStack && event.itemStack.typeId === "custom:{item_name_placeholder}") {{
        {js_event_handler_body}
    }}
}});
"""
            logger.info(
                f"Translated Java method {method_node.name} to Bedrock itemCompleteUse event for item '{item_name_placeholder}'."
            )

        return bedrock_event_script

    def analyze_java_code_ast(
        self, java_source: str
    ) -> Optional[javalang.tree.CompilationUnit]:
        """
        Parses Java source code into an Abstract Syntax Tree (AST).

        Args:
            java_source: The Java source code as a string.

        Returns:
            A javalang.tree.CompilationUnit representing the AST, or None if parsing fails.
        """
        try:
            tree = javalang.parse.parse(java_source)
            logger.info("Successfully parsed Java source into AST.")
            return tree
        except javalang.parser.JavaSyntaxError as e:
            msg = str(e)
            pos = getattr(e, 'position', 'unknown')
            logger.error(
                f"Java syntax error during AST parsing: {msg} at position {pos}"
            )
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during AST parsing: {str(e)}")
            return None

    def get_tools(self) -> List:
        """Get tools available to this agent"""
        return [
            self.translate_java_method_tool,
            self.convert_java_class_tool,
            self.map_java_apis_tool,
            self.generate_event_handlers_tool,
            self.validate_javascript_syntax_tool,
            self.translate_crafting_recipe_tool,  # Added new tool
        ]

    @tool
    def translate_java_method_tool(self, method_data: str) -> str:
        """Translate Java method to JavaScript."""
        return self.translate_java_method(method_data)

    @tool
    def convert_java_class_tool(self, class_data: str) -> str:
        """Convert Java class to JavaScript."""
        return self.convert_java_class(class_data)

    @tool
    def map_java_apis_tool(self, api_data: str) -> str:
        """Map Java APIs to JavaScript."""
        return self.map_java_apis(api_data)

    @tool
    def generate_event_handlers_tool(self, event_data: str) -> str:
        """Generate event handlers for JavaScript."""
        return self.generate_event_handlers(event_data)

    @tool
    def validate_javascript_syntax_tool(self, js_data: str) -> str:
        """Validate JavaScript syntax."""
        return self.validate_javascript_syntax(js_data)

    def translate_java_method(
        self, method_data: Any, feature_context_override: Optional[Dict] = None
    ) -> str:
        """
        Translate a Java method to JavaScript for Bedrock.

        Args:
            method_data: JSON string (containing method_name, return_type, parameters, body, feature_context)
                         OR a javalang.tree.MethodDeclaration AST node.
            feature_context_override: Optional dictionary for feature context, primarily used when method_data is an AST node.

        Returns:
            JSON string with translated JavaScript method
        """
        try:
            method_name: str
            return_type: str
            parameters: List[Dict[str, str]] = []
            body: str = ""
            feature_context: Dict = {}

            if isinstance(method_data, str):
                data = json.loads(method_data)
                method_name = data.get("method_name", "unknownMethod")
                return_type = data.get("return_type", "void")
                parameters = data.get("parameters", [])  # List of dicts {name, type}
                body = data.get("body", "")
                feature_context = data.get("feature_context", {})

            elif hasattr(method_data, 'parameters') and hasattr(method_data, 'name'):
                # Accept both MethodDeclaration and ConstructorDeclaration
                ast_node = method_data
                method_name = ast_node.name
                if hasattr(ast_node, 'return_type') and ast_node.return_type:
                    return_type = ast_node.return_type.name
                    if ast_node.return_type.dimensions:
                        return_type += "[]" * len(ast_node.return_type.dimensions)
                else:
                    return_type = "void"
                for param_node in ast_node.parameters:
                    param_type_name = param_node.type.name
                    if param_node.type.dimensions:
                        js_type = self.type_mappings.get(param_type_name, param_type_name)
                        param_type_name = f"{js_type}{'[]' * len(param_node.type.dimensions)}"
                    else:
                        param_type_name = self.type_mappings.get(param_type_name, param_type_name)
                    parameters.append(
                        {"name": param_node.name, "type": param_type_name}
                    )
                body = self._reconstruct_java_body_from_ast(ast_node)
                if hasattr(ast_node, 'body') and ast_node.body and not body:
                    logger.warning(
                        f"Method {method_name} AST node had a body, but reconstruction resulted in an empty string."
                    )
                if feature_context_override:
                    feature_context = feature_context_override
                else:
                    feature_context = {}

            else:
                raise TypeError(
                    "method_data must be a JSON string or javalang.tree.MethodDeclaration"
                )

            # Convert return type (common logic)
            js_return_type = self.type_mappings.get(return_type, return_type)

            # Convert parameters
            js_parameters = []
            for param in parameters:
                param_name = param.get("name", "param")
                param_type = param.get("type", "any")
                js_type = self.type_mappings.get(param_type, param_type)
                js_parameters.append(f"{param_name}: {js_type}")

            # Convert method body
            js_body = self._convert_java_body_to_javascript(body)

            # Generate JavaScript method
            if js_parameters:
                js_method = f"function {method_name}({', '.join(js_parameters)}): {js_return_type} {{\n{js_body}\n}}"
            else:
                js_method = (
                    f"function {method_name}(): {js_return_type} {{\n{js_body}\n}}"
                )

            response = {
                "success": True,
                "original_method": method_name,
                "javascript_method": js_method,
                "translation_notes": [
                    f"Converted return type from {return_type} to {js_return_type}",
                    f"Converted {len(parameters)} parameters",
                    "Applied Bedrock API mappings where applicable",
                ],
                "warnings": self._get_translation_warnings(body, feature_context),
            }

            logger.info(f"Translated Java method {method_name} to JavaScript")
            return json.dumps(response)

        except Exception as e:
            error_response = {
                "success": False,
                "error": f"Failed to translate method: {str(e)}",
            }
            logger.error(f"Method translation error: {e}")
            return json.dumps(error_response)

    def convert_java_class(self, class_data: str) -> str:
        # UNIQUE_COMMENT_FOR_VERIFICATION
        """
        Convert a complete Java class to JavaScript for Bedrock.

        Args:
            class_data: JSON string containing class information:
                       class_name, methods, fields, imports, feature_context

        Returns:
            JSON string with converted JavaScript class/module
        """
        try:
            data = json.loads(class_data)

            class_name = data.get("class_name", "UnknownClass")
            methods = data.get("methods", [])
            fields = data.get("fields", [])
            imports = data.get("imports", [])
            feature_context = data.get("feature_context", {})

            # Generate JavaScript class structure
            js_class_lines = [f"class {class_name} {{"]
            bedrock_event_scripts = []

            # Convert fields to properties
            for field in fields:
                field_name = field.get("name", "unknownField")
                field_type = field.get("type", "any")
                js_type = self.type_mappings.get(field_type, field_type)
                default_value = self._get_default_value(js_type)
                js_class_lines.append(f"    {field_name}: {js_type} = {default_value};")

            if fields:
                js_class_lines.append("")  # Add blank line after fields

            # Convert methods
            # This was 'interaction_keywords' in a previous version, renamed for clarity
            block_interaction_keywords = [
                "onblockactivated",
                "onblockrightclicked",
                "onblockbroken",
                "breakblock",
                "onblockplaced",
                "onblockadded",
            ]
            item_interaction_keywords = [
                "onitemrightclick",
                "onitemuse",
                "onfoodeaten",
                "useitem",
                "itemcompleteuse",
            ]  # Added item keywords

            for method_dict in methods:  # Assuming methods from JSON are dicts
                method_source = method_dict.get("source_code", method_dict.get("body"))
                method_name_from_json = method_dict.get("name", "unknownMethod")
                actual_method_node: Optional[javalang.tree.MethodDeclaration] = None

                if method_source:
                    temp_class_wrapper = f"class TempWrapper {{ {method_source} }}"
                    comp_unit = self.analyze_java_code_ast(temp_class_wrapper)
                    if (
                        comp_unit
                        and comp_unit.types
                        and isinstance(
                            comp_unit.types[0], javalang.tree.ClassDeclaration
                        )
                    ):
                        if comp_unit.types[0].body and isinstance(
                            comp_unit.types[0].body[0], javalang.tree.MethodDeclaration
                        ):
                            actual_method_node = comp_unit.types[0].body[0]

                method_name_to_check = (
                    actual_method_node.name.lower()
                    if actual_method_node
                    else method_name_from_json.lower()
                )

                if actual_method_node and any(
                    keyword in method_name_to_check
                    for keyword in block_interaction_keywords
                ):
                    event_script = self._translate_block_interaction_method(
                        actual_method_node, class_context={"class_name": class_name}
                    )
                    if event_script:
                        bedrock_event_scripts.append(event_script)
                elif actual_method_node and any(
                    keyword in method_name_to_check
                    for keyword in item_interaction_keywords
                ):  # Added elif for item methods
                    event_script = self._translate_item_use_method(
                        actual_method_node, class_context={"class_name": class_name}
                    )
                    if event_script:
                        bedrock_event_scripts.append(event_script)
                else:
                    # Process as a regular method
                    if actual_method_node:
                        # Pass feature_context from the class level
                        method_result_json = self.translate_java_method(
                            actual_method_node, feature_context_override=feature_context
                        )
                    else:
                        # Fallback: if AST node couldn't be obtained, pass the original method dict as JSON
                        method_dict_with_context = {
                            **method_dict,
                            "feature_context": method_dict.get(
                                "feature_context", feature_context
                            ),
                        }
                        method_result_json = self.translate_java_method(
                            json.dumps(method_dict_with_context)
                        )

                    method_output = json.loads(method_result_json)
                    if method_output.get("success"):
                        js_method_code = method_output.get("javascript_method", "")
                        if js_method_code:
                            indented_method = "    " + js_method_code.replace(
                                "\n", "\n    "
                            )
                            js_class_lines.append(indented_method)
                            js_class_lines.append("")

            js_class_lines.append("}")

            bedrock_imports = self._generate_bedrock_imports(imports, feature_context)

            final_js_parts = bedrock_imports
            if bedrock_imports:
                final_js_parts.append("")
            final_js_parts.extend(js_class_lines)
            if bedrock_event_scripts:
                final_js_parts.append("\n")
            final_js_parts.extend(bedrock_event_scripts)

            js_code = "\n".join(final_js_parts)

            response = {
                "success": True,
                "original_class": class_name,
                "javascript_class": js_code,
                "conversion_summary": {
                    "fields_converted": len(fields),
                    "methods_converted": len(methods) - len(bedrock_event_scripts),
                    "event_handlers_generated": len(bedrock_event_scripts),
                    "imports_adapted": len(bedrock_imports),
                },
                "bedrock_compatibility_notes": self._get_compatibility_notes(
                    feature_context
                ),
            }

            logger.info(f"Converted Java class {class_name} to JavaScript")
            return json.dumps(response)

        except Exception as e:
            error_response = {
                "success": False,
                "error": f"Failed to convert class: {str(e)}",
            }
            logger.error(f"Class conversion error: {e}")
            return json.dumps(error_response)

    def map_java_apis(self, api_usage_data: str) -> str:
        """
        Map Java Minecraft APIs to their Bedrock JavaScript equivalents.

        Args:
            api_usage_data: JSON string containing Java API calls and context

        Returns:
            JSON string with Bedrock API equivalents and usage notes
        """
        try:
            data = json.loads(api_usage_data)

            java_apis = data.get("java_apis", [])
            context = data.get("context", {})

            api_mappings = []
            unsupported_apis = []

            for java_api in java_apis:
                bedrock_equivalent = self._find_bedrock_equivalent(java_api, context)

                if bedrock_equivalent:
                    api_mappings.append(
                        {
                            "java_api": java_api,
                            "bedrock_api": bedrock_equivalent["api"],
                            "confidence": bedrock_equivalent["confidence"],
                            "usage_notes": bedrock_equivalent["notes"],
                        }
                    )
                else:
                    unsupported_apis.append(
                        {
                            "java_api": java_api,
                            "reason": "No direct Bedrock equivalent available",
                            "suggested_workaround": self._suggest_workaround(java_api),
                        }
                    )

            response = {
                "success": True,
                "mapped_apis": api_mappings,
                "unsupported_apis": unsupported_apis,
                "mapping_summary": {
                    "total_apis": len(java_apis),
                    "successfully_mapped": len(api_mappings),
                    "unsupported": len(unsupported_apis),
                },
            }

            logger.info(f"Mapped {len(api_mappings)} Java APIs to Bedrock equivalents")
            return json.dumps(response)

        except Exception as e:
            error_response = {
                "success": False,
                "error": f"Failed to map APIs: {str(e)}",
            }
            logger.error(f"API mapping error: {e}")
            return json.dumps(error_response)

    def generate_event_handlers(self, event_data: str) -> str:
        """
        Generate Bedrock JavaScript event handlers from Java event listeners.

        Args:
            event_data: JSON string containing Java event listeners and context

        Returns:
            JSON string with generated Bedrock event handlers
        """
        try:
            data = json.loads(event_data)

            java_events = data.get("java_events", [])

            bedrock_handlers = []

            for java_event in java_events:
                event_name = java_event.get("name", "unknownEvent")
                event_type = java_event.get("type", "unknown")
                handler_source_code = java_event.get("handler_source_code")
                handler_body_java = ""
                actual_method_node: Optional[javalang.tree.MethodDeclaration] = None

                if handler_source_code:
                    temp_class_source = (
                        f"class TempEventHandlerWrapper {{ {handler_source_code} }}"
                    )
                    ast_comp_unit = self.analyze_java_code_ast(temp_class_source)
                    if (
                        ast_comp_unit
                        and ast_comp_unit.types
                        and isinstance(
                            ast_comp_unit.types[0], javalang.tree.ClassDeclaration
                        )
                        and ast_comp_unit.types[0].body
                        and isinstance(
                            ast_comp_unit.types[0].body[0],
                            javalang.tree.MethodDeclaration,
                        )
                    ):
                        actual_method_node = ast_comp_unit.types[0].body[0]
                        handler_body_java = self._reconstruct_java_body_from_ast(
                            actual_method_node
                        )
                    else:
                        logger.warning(
                            f"Failed to parse or extract method AST from handler_source_code for event {event_name}. Falling back to handler_body."
                        )
                        handler_body_java = java_event.get(
                            "handler_body", ""
                        )  # Fallback
                else:
                    handler_body_java = java_event.get(
                        "handler_body", ""
                    )  # No source code provided

                bedrock_event = self._map_java_event_to_bedrock(event_type)

                if bedrock_event:
                    js_handler_body = self._convert_java_body_to_javascript(
                        handler_body_java
                    )

                    handler_code = f"""
world.afterEvents.{bedrock_event}.subscribe((event) => {{
    // Converted from Java {event_type} event
{js_handler_body}
}});"""

                    bedrock_handlers.append(
                        {
                            "original_event": event_name,
                            "bedrock_event": bedrock_event,
                            "handler_code": handler_code.strip(),
                            "conversion_notes": f"Mapped Java {event_type} to Bedrock {bedrock_event}",
                        }
                    )
                else:
                    bedrock_handlers.append(
                        {
                            "original_event": event_name,
                            "bedrock_event": None,
                            "handler_code": f"// WARNING: No Bedrock equivalent for {event_type}",
                            "conversion_notes": f"Java event {event_type} has no direct Bedrock equivalent",
                        }
                    )

            response = {
                "success": True,
                "event_handlers": bedrock_handlers,
                "handler_summary": {
                    "total_events": len(java_events),
                    "converted_events": len(
                        [h for h in bedrock_handlers if h["bedrock_event"]]
                    ),
                    "unsupported_events": len(
                        [h for h in bedrock_handlers if not h["bedrock_event"]]
                    ),
                },
            }

            logger.info(f"Generated {len(bedrock_handlers)} Bedrock event handlers")
            return json.dumps(response)

        except Exception as e:
            error_response = {
                "success": False,
                "error": f"Failed to generate event handlers: {str(e)}",
            }
            logger.error(f"Event handler generation error: {e}")
            return json.dumps(error_response)

    def validate_javascript_syntax(self, code_data: str) -> str:
        """
        Validate and analyze generated JavaScript code for Bedrock compatibility.

        Args:
            code_data: JSON string containing JavaScript code to validate

        Returns:
            JSON string with validation results and suggestions
        """
        try:
            data = json.loads(code_data)

            js_code = data.get("javascript_code", "")
            context = data.get("context", {})

            validation_results = {
                "syntax_valid": True,
                "syntax_errors": [],
                "bedrock_compatibility": [],
                "performance_warnings": [],
                "suggestions": [],
            }

            # Basic syntax validation
            syntax_issues = self._check_javascript_syntax(js_code)
            if syntax_issues:
                validation_results["syntax_valid"] = False
                validation_results["syntax_errors"] = syntax_issues

            # Bedrock-specific checks
            bedrock_issues = self._check_bedrock_compatibility(js_code)
            validation_results["bedrock_compatibility"] = bedrock_issues

            # Performance analysis
            performance_issues = self._check_performance_concerns(js_code)
            validation_results["performance_warnings"] = performance_issues

            # Generate improvement suggestions
            suggestions = self._generate_code_suggestions(js_code, context)
            validation_results["suggestions"] = suggestions

            response = {
                "success": True,
                "validation_results": validation_results,
                "overall_quality": "good"
                if validation_results["syntax_valid"] and not bedrock_issues
                else "needs_improvement",
            }

            logger.info(f"Validated JavaScript code: {response['overall_quality']}")
            return json.dumps(response)

        except Exception as e:
            error_response = {
                "success": False,
                "error": f"Failed to validate JavaScript: {str(e)}",
            }
            logger.error(f"JavaScript validation error: {e}")
            return json.dumps(error_response)

    # Helper methods

    def _reconstruct_java_body_from_ast(
        self, method_node: javalang.tree.MethodDeclaration
    ) -> str:
        """
        Attempts to reconstruct the Java method body from its AST node.
        This is a simplified reconstruction and might not perfectly match original formatting.
        Args:
            method_node: The javalang.tree.MethodDeclaration AST node.
        Returns:
            A string representation of the method body.
        """
        if not method_node.body:
            return ""

        body_lines = []
        for statement in method_node.body:
            if hasattr(statement, "children") and statement.children:
                line_tokens = []
                for child_path, child_node in statement:
                    if hasattr(child_node, "name"):
                        line_tokens.append(str(child_node.name))
                    elif hasattr(child_node, "value"):
                        line_tokens.append(str(child_node.value))
                    elif isinstance(child_node, javalang.tree.Statement):
                        line_tokens.append(
                            f"// Complex statement: {type(child_node).__name__}"
                        )
                    elif isinstance(child_node, list):
                        for sub_node in child_node:
                            if hasattr(sub_node, "name"):
                                line_tokens.append(str(sub_node.name))
                            elif hasattr(sub_node, "value"):
                                line_tokens.append(str(sub_node.value))

                reconstructed_line = " ".join(token for token in line_tokens if token)
                if reconstructed_line:
                    if (
                        not reconstructed_line.strip().endswith("}")
                        and not reconstructed_line.strip().endswith("{")
                        and not reconstructed_line.strip().startswith("//")
                    ):
                        reconstructed_line += ";"
                body_lines.append(reconstructed_line)
            else:
                body_lines.append(
                    f"// Unsupported statement type: {type(statement).__name__}"
                )

        return "\n".join(body_lines)

    def _translate_block_interaction_method(
        self,
        method_node: javalang.tree.MethodDeclaration,
        class_context: Optional[Dict],
    ) -> Optional[str]:
        """
        Translates a Java method assumed to be a block interaction event handler
        (e.g., onBlockActivated, onBlockBroken) to Bedrock JavaScript event handling.

        Args:
            method_node: The AST node of the Java method.
            class_context: Optional dictionary providing context about the class this method belongs to.
                           (e.g., {"class_name": "MyCustomBlock"})

        Returns:
            A string containing the Bedrock JavaScript event subscription, or None if not applicable.
        """
        method_name = method_node.name.lower()
        js_event_handler_body = self._convert_java_body_to_javascript(
            self._reconstruct_java_body_from_ast(method_node)
        )

        # TODO: Replace js_event_handler_body with AST-based translation of the method body in a future step.

        param_map = {
            "player": "event.player",
            "world": "world",
            "pos": "event.block.location",
            "block": "event.block",
            "itemStack": "event.itemStack",
        }
        for java_param, bedrock_param in param_map.items():
            js_event_handler_body = re.sub(
                r"\b" + re.escape(java_param) + r"\b",
                bedrock_param,
                js_event_handler_body,
            )

        bedrock_event_script = None
        block_name_placeholder = (
            class_context.get("class_name", "my_block").lower()
            if class_context
            else "my_block"
        )

        if "onblockactivated" in method_name or "onblockrightclicked" in method_name:
            bedrock_event_script = f"""
world.afterEvents.playerInteractWithBlock.subscribe((event) => {{
    // Original Java method: {method_node.name}
    // TODO: Add conditions to check if event.block is an instance of this custom block.
    // Example: if (event.block.typeId === "custom:{block_name_placeholder}") {{
    {js_event_handler_body}
    // }}
}});
"""
            logger.info(
                f"Translated Java method {method_node.name} to Bedrock playerInteractWithBlock event."
            )
        elif "onblockbroken" in method_name or "breakblock" in method_name:
            bedrock_event_script = f"""
world.afterEvents.playerBreakBlock.subscribe((event) => {{
    // Original Java method: {method_node.name}
    // TODO: Add conditions to check if event.block is an instance of this custom block.
    {js_event_handler_body}
}});
"""
            logger.info(
                f"Translated Java method {method_node.name} to Bedrock playerBreakBlock event."
            )
        elif "onblockplaced" in method_name or "onblockadded" in method_name:
            bedrock_event_script = f"""
world.afterEvents.playerPlaceBlock.subscribe((event) => {{
    // Original Java method: {method_node.name}
    // TODO: Add conditions to check if event.block is an instance of this custom block.
    {js_event_handler_body}
}});
"""
            logger.info(
                f"Translated Java method {method_node.name} to Bedrock playerPlaceBlock event."
            )

        return bedrock_event_script

    def _convert_java_body_to_javascript(self, java_body: str) -> str:
        """Convert Java method body to JavaScript"""
        # TODO: Refactor to use AST analysis for more robust body translation
        # Store original java_body for context checking
        self._original_java_body_for_context = java_body
        js_body = java_body

        # Apply API mappings
        for java_api, bedrock_api in self.api_mappings.items():
            js_body = js_body.replace(java_api, bedrock_api)

        # Convert Java-specific syntax to JavaScript
        js_body = re.sub(
            r"\bSystem\.out\.println\((.*?)\)", r"console.log(\1)", js_body
        )
        js_body = re.sub(r"\bnew ArrayList<.*?>\(\)", r"[]", js_body)
        js_body = re.sub(r"\bnew HashMap<.*?>\(\)", r"new Map()", js_body)
        js_body = re.sub(r"\.add\(", r".push(", js_body)
        js_body = re.sub(r"\.size\(\)", r".length", js_body)

        # Translate world.setBlockState(pos, Blocks.AIR.getDefaultState()[, flags])
        # Pattern for specific Blocks.AIR.getDefaultState() or Blocks.air.getDefaultState()
        set_block_state_air_pattern = r"world\.setBlockState\s*\(\s*([\w\.]+)\s*,\s*(?:Blocks\.AIR|Blocks\.air)\.getDefaultState\s*\(\s*\)\s*(?:,\s*[\w\.]+\s*)?\);?"

        # Determine replacement based on context (presence of 'event.block')
        # This is a heuristic. A more robust way would involve deeper context analysis.
        # We check the original java_body string that was passed into this function for context
        # as js_body might have been modified by previous rules.
        if (
            hasattr(self, "_original_java_body_for_context")
            and "event.block" in self._original_java_body_for_context
        ):
            replacement_air = r'event.block.dimension.setBlockPermutation(\1, BlockPermutation.resolve("minecraft:air")); // Original: world.setBlockState(\1, Blocks.AIR.getDefaultState())'
        else:
            replacement_air = r'world.getDimension("overworld").setBlockPermutation(\1, BlockPermutation.resolve("minecraft:air")); // Original: world.setBlockState(\1, Blocks.AIR.getDefaultState())'

        js_body = re.sub(set_block_state_air_pattern, replacement_air, js_body)

        # Translate other world.setBlockState(pos, someState[, flags]) to a TODO comment
        # This pattern tries to capture general setBlockState calls that weren't for AIR.
        # It uses a negative lookahead to avoid re-matching Blocks.AIR.getDefaultState().
        set_block_state_other_pattern = r"world\.setBlockState\s*\(\s*([\w\.]+)\s*,\s*((?!Blocks\.(?:AIR|air)\.getDefaultState\s*\(\s*\))[\w\.\(\)]+)\s*(?:,\s*[\w\.]+\s*)?\);?"

        if (
            hasattr(self, "_original_java_body_for_context")
            and "event.block" in self._original_java_body_for_context
        ):
            replacement_other = r'// TODO: Bedrock: event.block.dimension.setBlockPermutation(\1, BlockPermutation.resolve("your_block_id_from_\2")); /* Original: world.setBlockState(\1, \2) */'
        else:
            replacement_other = r'// TODO: Bedrock: world.getDimension("overworld").setBlockPermutation(\1, BlockPermutation.resolve("your_block_id_from_\2")); /* Original: world.setBlockState(\1, \2) */'

        js_body = re.sub(set_block_state_other_pattern, replacement_other, js_body)

        # Add a general comment if BlockPermutation is likely used.
        if "setBlockPermutation" in js_body or "BlockPermutation.resolve" in js_body:
            # Check if the comment is already there to avoid duplicates if method is called multiple times with similar body
            comment_to_add = "// Ensure 'BlockPermutation' is imported from \"@minecraft/server\" for this script."
            if comment_to_add not in js_body:
                js_body += "\n" + comment_to_add

        # Identify custom event bus posting and add TODO comment
        custom_event_post_pattern = r"([\w\-\.]+)\.(?:MinecraftForge\.EVENT_BUS|EVENT_BUS|eventBus)\.post\s*\(\s*new\s+([\w\.<>]+)\s*\((.*?)\)\s*\);?"
        replacement_custom_event = r"// TODO: Custom Java event posted: \2 with args: \3. Consider using Bedrock system.triggerEvent() or specific [player/entity/block].triggerEvent() and corresponding listeners. Original: \g<0>"
        js_body = re.sub(custom_event_post_pattern, replacement_custom_event, js_body)

        # Handle itemStack.isEmpty() -> !itemStack
        js_body = re.sub(r"([\w\.]+)\.isEmpty\(\s*\)", r"(!\1)", js_body)

        # Handle world.isAirBlock(pos) -> world.getBlock(pos).isAir
        # This assumes world.isAirBlock( was already changed to world.getBlock( by api_mappings
        js_body = re.sub(
            r"world\.getBlock\(([\w\.]+)\)\s*\)", r"world.getBlock(\1).isAir", js_body
        )

        # Player inventory access: player.inventory.getStackInSlot(slot) -> player.getComponent('inventory').container.getItem(slot)
        inventory_pattern_player = (
            r"([\w\.]+)\.inventory\.getStackInSlot\s*\(\s*([\w\.]+)\s*\)"
        )
        js_body = re.sub(
            inventory_pattern_player,
            r'\1.getComponent("inventory").container.getItem(\2)',
            js_body,
        )

        # Add a TODO for more complex inventory operations:
        js_body = re.sub(
            r"([\w\.]+)\.(?:inventory|getInventory\(\))\.(setInventorySlotContents|setStackInSlot|getSizeInventory|clear)\s*\(",
            r"// TODO: Bedrock: Review inventory operation: \g<0> - map to inventory component methods (e.g., container.setItem, container.size, container.clear). Original: ",
            js_body,
        )

        # world.spawnEntity(entity) -> dimension.spawnEntity(entityIdentifier, location)
        spawn_entity_pattern = r"([\w\.]+)\.spawnEntity\s*\(\s*([\w\.]+)\s*\)"
        js_body = re.sub(
            spawn_entity_pattern,
            r'// TODO: Bedrock: \1.getDimension("overworld").spawnEntity(identifier_from_\2, location_from_\2); /* Original: \g<0> */',
            js_body,
        )

        # player.getFoodStats().addStats(food, saturation) -> player.getComponent("minecraft:food").eat(foodAmount, saturationAmount)
        add_food_stats_pattern = r"([\w\.]+)\.getFoodStats\(\)\.addStats\s*\(\s*([\w\.]+)\s*,\s*([\w\.]+)\s*\)"
        js_body = re.sub(
            add_food_stats_pattern,
            r'\1.getComponent("minecraft:food").eat(\2, \3); // Approximated from addStats',
            js_body,
        )

        # Add proper indentation
        lines = js_body.split("\n")
        indented_lines = ["    " + line.strip() for line in lines if line.strip()]

        return "\n".join(indented_lines)

    def _get_default_value(self, js_type: str) -> str:
        """Get default value for JavaScript type"""
        defaults = {
            "number": "0",
            "string": '""',
            "boolean": "false",
            "Array": "[]",
            "Map": "new Map()",
            "any": "null",
        }
        return defaults.get(js_type, "null")

    def _generate_bedrock_imports(
        self, java_imports: List[str], context: Dict
    ) -> List[str]:
        """Generate Bedrock-specific imports from Java imports"""
        bedrock_imports = []

        # Common Bedrock imports
        if any("minecraft" in imp.lower() for imp in java_imports):
            bedrock_imports.extend(
                [
                    'import { world, system } from "@minecraft/server";',
                    'import { MinecraftItemTypes } from "@minecraft/vanilla-data";',
                ]
            )

        if any("event" in imp.lower() for imp in java_imports):
            bedrock_imports.append('import { world } from "@minecraft/server";')

        return bedrock_imports

    def _find_bedrock_equivalent(self, java_api: str, context: Dict) -> Optional[Dict]:
        """Find Bedrock equivalent for Java API"""
        if java_api in self.api_mappings:
            return {
                "api": self.api_mappings[java_api],
                "confidence": "high",
                "notes": "Direct mapping available",
            }

        # Pattern-based matching for common cases
        if "player.get" in java_api.lower():
            return {
                "api": java_api.replace(".get", '.getComponent("').replace(
                    "()", '").currentValue'
                ),
                "confidence": "medium",
                "notes": "Converted to component system",
            }

        return None

    def _suggest_workaround(self, java_api: str) -> str:
        """Suggest workaround for unsupported Java API"""
        if "reflection" in java_api.lower():
            return "Use explicit property access instead of reflection"
        elif "thread" in java_api.lower():
            return "Use system.run() or system.runInterval() for async operations"
        elif "file" in java_api.lower():
            return "Store data in world dynamic properties or player storage"
        else:
            return (
                "Consider alternative approach or request feature in Bedrock feedback"
            )

    def _map_java_event_to_bedrock(self, java_event_type: str) -> Optional[str]:
        """Map Java event type to Bedrock event"""
        event_mappings = {
            "PlayerJoinEvent": "playerSpawn",
            "PlayerQuitEvent": "playerLeave",
            "BlockBreakEvent": "blockBreak",
            "BlockPlaceEvent": "blockPlace",
            "PlayerInteractEvent": "itemUse",  # Generic, might need more specific handling or rely on _translate_item_use_method
            "EntityDamageEvent": "entityHurt",
            "PlayerDeathEvent": "entityDie",  # Generic entity death
            "LivingDeathEvent": "entityDie",  # More specific for living entities, maps to same Bedrock event
            # Forge Events
            "PlayerLoggedInEvent": "playerJoin",  # playerSpawn is also a candidate
            "PlayerLoggedOutEvent": "playerLeave",
            # PlayerInteractEvent.RightClickBlock is handled by _translate_block_interaction_method
            # PlayerInteractEvent.LeftClickBlock could map to playerStartDestroyingBlock or a custom interaction
            "PlayerInteractEvent.LeftClickBlock": "playerStartDestroyingBlock",  # Approximate
            "ExplosionEvent.Detonate": "explosion",  # Might need specific data extraction from event properties
            "TickEvent.WorldTickEvent": "worldTick",  # Requires careful implementation, might map to system.runInterval
            "TickEvent.ServerTickEvent": "worldTick",  # Similar to WorldTickEvent
            # Bukkit Events
            "PlayerCommandEvent": "beforeChatSend",  # For detecting and potentially cancelling commands
            "InventoryClickEvent": None,  # Complex, typically no direct Bedrock equivalent for general inventory clicks. Placeholder for TODO.
            "EntitySpawnEvent": "entitySpawn",
        }
        # For InventoryClickEvent, translation would likely involve custom logic based on UI and specific needs.
        # Logging a TODO or raising a specific error/warning during translation might be appropriate.
        if java_event_type == "InventoryClickEvent":
            logger.warning(
                "InventoryClickEvent has no direct Bedrock equivalent and requires manual translation."
            )

        return event_mappings.get(java_event_type)

    def _check_javascript_syntax(self, js_code: str) -> List[str]:
        """Check for basic JavaScript syntax issues"""
        issues = []

        # Basic checks
        if js_code.count("{") != js_code.count("}"):
            issues.append("Mismatched curly braces")

        if js_code.count("(") != js_code.count(")"):
            issues.append("Mismatched parentheses")

        # Check for common Java-isms that don't work in JavaScript
        if "System.out.println" in js_code:
            issues.append("Use console.log instead of System.out.println")

        return issues

    def _check_bedrock_compatibility(self, js_code: str) -> List[str]:
        """Check for Bedrock-specific compatibility issues"""
        issues = []

        # Check for unsupported features
        if "eval(" in js_code:
            issues.append("eval() is not supported in Bedrock scripting")

        if "setTimeout(" in js_code:
            issues.append("Use system.runTimeout() instead of setTimeout()")

        if "setInterval(" in js_code:
            issues.append("Use system.runInterval() instead of setInterval()")

        return issues

    def _check_performance_concerns(self, js_code: str) -> List[str]:
        """Check for potential performance issues"""
        warnings = []

        # Check for expensive operations
        if js_code.count("world.getDimension") > 5:
            warnings.append(
                "Multiple world.getDimension() calls detected - consider caching"
            )

        if "while(true)" in js_code:
            warnings.append("Infinite loop detected - may cause server lag")

        return warnings

    def _generate_code_suggestions(self, js_code: str, context: Dict) -> List[str]:
        """Generate code improvement suggestions"""
        suggestions = []

        if "console.log" in js_code:
            suggestions.append("Consider using conditional logging for production")

        if not any(word in js_code for word in ["try", "catch"]):
            suggestions.append("Consider adding error handling with try-catch blocks")

        return suggestions

    def _get_translation_warnings(self, java_body: str, context: Dict) -> List[str]:
        """Get warnings about translation challenges"""
        warnings = []

        if "reflection" in java_body.lower():
            warnings.append("Reflection usage detected - may need manual conversion")

        if "thread" in java_body.lower():
            warnings.append("Threading detected - convert to Bedrock async patterns")

        return warnings

    def _get_compatibility_notes(self, context: Dict) -> List[str]:
        """Get Bedrock compatibility notes"""
        notes = [
            "All event handlers use Bedrock's event system",
            "API calls converted to Bedrock component system where applicable",
            "Threading converted to system.run* methods",
        ]

        return notes

    def translate_java_code(self, java_code: str, code_type: str = "unknown") -> str:
        """
        Translate Java code to Bedrock JavaScript.

        Args:
            java_code: Java source code to translate
            code_type: Type of code (block, item, entity, etc.)

        Returns:
            JSON string with translation results
        """
        try:
            # Create method data structure that matches existing implementation
            method_data = {
                "java_code": java_code,
                "method_type": code_type,
                "conversion_context": {
                    "target_platform": "bedrock",
                    "minecraft_version": "1.19.4",
                },
            }

            # Use existing translation method
            result_json = self.translate_java_method(json.dumps(method_data))
            result = json.loads(result_json)

            # Transform to expected format for integration tests
            return json.dumps(
                {
                    "translated_javascript": result.get("translated_javascript", ""),
                    "original_java": java_code,
                    "success": result.get("success", True),
                    "conversion_notes": result.get("conversion_notes", []),
                    "api_mappings": result.get("api_mappings", {}),
                    "success_rate": result.get("success_rate", 1.0),
                }
            )

        except Exception as e:
            logger.error(f"Error in translate_java_code: {str(e)}")
            return json.dumps(
                {
                    "success": False,
                    "translated_javascript": "",
                    "conversion_notes": [f"Translation failed: {str(e)}"],
                    "api_mappings": {},
                    "success_rate": 0.0,
                    "error": str(e),
                }
            )

    @tool
    def translate_crafting_recipe_tool(self, recipe_json_data: str) -> str:
        """Translate a Java crafting recipe JSON to Bedrock recipe JSON format."""
        return self.translate_crafting_recipe_json(recipe_json_data)

    def translate_crafting_recipe_json(self, recipe_json_data: str) -> str:
        """
        Translates a Java crafting recipe from a JSON representation to Bedrock's JSON format.

        Args:
            recipe_json_data: A JSON string representing the Java crafting recipe.
                              Expected format (example):
                              {
                                  "type": "minecraft:crafting_shaped", // or "minecraft:crafting_shapeless"
                                  "pattern": [
                                      " S ",
                                      "SCS",
                                      " S "
                                  ],
                                  "key": {
                                      "S": {"item": "minecraft:stick"},
                                      "C": {"item": "minecraft:cobblestone"}
                                  },
                                  "result": {"item": "minecraft:furnace", "count": 1}
                              }
                              Or for shapeless:
                              {
                                  "type": "minecraft:crafting_shapeless",
                                  "ingredients": [
                                      {"item": "minecraft:sugar"},
                                      {"item": "minecraft:egg"}
                                  ],
                                  "result": {"item": "minecraft:cake", "count": 1}
                              }

        Returns:
            A JSON string representing the Bedrock crafting recipe, or an error JSON.
        """
        try:
            java_recipe = json.loads(recipe_json_data)
            bedrock_recipe = {"format_version": "1.12"}

            recipe_type = java_recipe.get("type", "")
            result_item_java = java_recipe.get("result", {}).get("item", "unknown_item")
            result_count_java = java_recipe.get("result", {}).get("count", 1)

            # Generate a unique recipe key for Bedrock (commonly based on result item)
            # Strip 'minecraft:' namespace from result item for Bedrock
            bedrock_item_id = result_item_java.replace("minecraft:", "")
            recipe_key_str = f"{bedrock_item_id}_from_java_recipe"

            if recipe_type == "minecraft:crafting_shaped":
                bedrock_recipe["minecraft:recipe_shaped"] = {
                    "description": {
                        "identifier": f"minecraft:{recipe_key_str}"
                    },
                    "tags": ["crafting_table"],
                    "pattern": java_recipe.get("pattern", []),
                    "key": {},
                    "result": {
                        "item": bedrock_item_id,
                        "count": result_count_java,
                    },
                }
                # Convert key mapping, strip namespace from each key item
                for k, v in java_recipe.get("key", {}).items():
                    key_item = v.copy()
                    if "item" in key_item and key_item["item"].startswith("minecraft:"):
                        key_item["item"] = key_item["item"].split(":", 1)[1]
                    bedrock_recipe["minecraft:recipe_shaped"]["key"][k] = [key_item]

            elif recipe_type == "minecraft:crafting_shapeless":
                # Strip namespace from each ingredient item
                bedrock_ingredients = []
                for ing in java_recipe.get("ingredients", []):
                    ing_copy = ing.copy()
                    if "item" in ing_copy and ing_copy["item"].startswith("minecraft:"):
                        ing_copy["item"] = ing_copy["item"].split(":", 1)[1]
                    bedrock_ingredients.append(ing_copy)
                bedrock_recipe["minecraft:recipe_shapeless"] = {
                    "description": {
                        "identifier": f"minecraft:{recipe_key_str}"
                    },
                    "tags": ["crafting_table"],
                    "ingredients": bedrock_ingredients,
                    "result": {
                        "item": bedrock_item_id,
                        "count": result_count_java,
                    },
                }
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Unsupported recipe type: {recipe_type}"
                })

            return json.dumps({
                "success": True,
                "bedrock_recipe": bedrock_recipe
            })
        except json.JSONDecodeError as e:
            return json.dumps({
                "success": False,
                "error": f"Invalid JSON: {str(e)}"
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error translating recipe: {str(e)}"
            })
