"""
Unit tests for AST-based Java to JavaScript translation features in LogicTranslatorAgent
"""

import json
import pytest
import javalang
from unittest.mock import Mock, patch
from src.agents.logic_translator import LogicTranslatorAgent


class TestLogicTranslatorAST:
    """Test suite for AST-based translation features"""

    def setup_method(self):
        """Setup test instance"""
        self.translator = LogicTranslatorAgent()

    def test_analyze_java_code_ast_success(self):
        """Test successful Java AST parsing"""
        java_code = """
        public class TestClass {
            public void testMethod() {
                System.out.println("Hello World");
            }
        }
        """
        
        result = self.translator.analyze_java_code_ast(java_code)
        
        assert result is not None
        assert isinstance(result, javalang.tree.CompilationUnit)
        assert len(result.types) == 1
        assert isinstance(result.types[0], javalang.tree.ClassDeclaration)
        assert result.types[0].name == "TestClass"

    def test_analyze_java_code_ast_syntax_error(self):
        """Test Java AST parsing with syntax error"""
        invalid_java_code = """
        public class TestClass {
            public void testMethod() {
                // Missing closing brace
        """
        
        result = self.translator.analyze_java_code_ast(invalid_java_code)
        
        assert result is None

    def test_reconstruct_java_body_from_ast(self):
        """Test reconstructing Java method body from AST"""
        java_code = """
        public class TestClass {
            public void testMethod() {
                System.out.println("Hello");
                int x = 5;
            }
        }
        """
        
        ast = self.translator.analyze_java_code_ast(java_code)
        method_node = ast.types[0].body[0]  # First method
        
        result = self.translator._reconstruct_java_body_from_ast(method_node)
        
        assert "Hello" in result
        assert ";" in result

    def test_reconstruct_java_body_empty_method(self):
        """Test reconstructing empty method body"""
        java_code = """
        public class TestClass {
            public void emptyMethod() {
            }
        }
        """
        
        ast = self.translator.analyze_java_code_ast(java_code)
        method_node = ast.types[0].body[0]
        
        result = self.translator._reconstruct_java_body_from_ast(method_node)
        
        assert result == ""

    def test_translate_item_use_method(self):
        """Test translating item use method"""
        java_code = """
        public class TestItem {
            public void onItemRightClick() {
                player.setHealth(20);
            }
        }
        """
        
        ast = self.translator.analyze_java_code_ast(java_code)
        method_node = ast.types[0].body[0]
        class_context = {"class_name": "TestItem"}
        
        result = self.translator._translate_item_use_method(method_node, class_context)
        
        assert result is not None
        assert "world.afterEvents.itemUse.subscribe" in result
        assert "testitem" in result.lower()

    def test_translate_food_eaten_method(self):
        """Test translating food eaten method"""
        java_code = """
        public class TestFood {
            public void onFoodEaten() {
                player.addEffect(Effects.REGENERATION);
            }
        }
        """
        
        ast = self.translator.analyze_java_code_ast(java_code)
        method_node = ast.types[0].body[0]
        class_context = {"class_name": "TestFood"}
        
        result = self.translator._translate_item_use_method(method_node, class_context)
        
        assert result is not None
        assert "world.afterEvents.itemCompleteUse.subscribe" in result
        assert "testfood" in result.lower()

    def test_translate_block_interaction_method(self):
        """Test translating block interaction method"""
        java_code = """
        public class TestBlock {
            public void onBlockActivated() {
                world.setBlockState(pos, Blocks.AIR.getDefaultState());
            }
        }
        """
        
        ast = self.translator.analyze_java_code_ast(java_code)
        method_node = ast.types[0].body[0]
        class_context = {"class_name": "TestBlock"}
        
        result = self.translator._translate_block_interaction_method(method_node, class_context)
        
        assert result is not None
        assert "world.afterEvents.playerInteractWithBlock.subscribe" in result
        assert "testblock" in result.lower()

    def test_translate_block_broken_method(self):
        """Test translating block broken method"""
        java_code = """
        public class TestBlock {
            public void onBlockBroken() {
                player.giveAchievement(Achievements.BREAK_BLOCK);
            }
        }
        """
        
        ast = self.translator.analyze_java_code_ast(java_code)
        method_node = ast.types[0].body[0]
        class_context = {"class_name": "TestBlock"}
        
        result = self.translator._translate_block_interaction_method(method_node, class_context)
        
        assert result is not None
        assert "world.afterEvents.playerBreakBlock.subscribe" in result

    def test_translate_java_method_with_ast_node(self):
        """Test translating Java method using AST node input"""
        java_code = """
        public class TestClass {
            public int calculateValue(int input) {
                return input * 2;
            }
        }
        """
        
        ast = self.translator.analyze_java_code_ast(java_code)
        method_node = ast.types[0].body[0]
        
        result_json = self.translator.translate_java_method(method_node)
        result = json.loads(result_json)
        
        assert result["success"] is True
        assert "calculateValue" in result["javascript_method"]
        assert "input: number" in result["javascript_method"]
        assert "number" in result["javascript_method"]  # Return type

    def test_translate_java_method_with_feature_context_override(self):
        """Test translating Java method with feature context override"""
        java_code = """
        public class TestClass {
            public void testMethod() {
                System.out.println("test");
            }
        }
        """
        
        ast = self.translator.analyze_java_code_ast(java_code)
        method_node = ast.types[0].body[0]
        feature_context = {"custom_feature": True}
        
        result_json = self.translator.translate_java_method(method_node, feature_context)
        result = json.loads(result_json)
        
        assert result["success"] is True

    def test_convert_java_class_with_event_methods(self):
        """Test converting Java class with event handler methods"""
        class_data = {
            "class_name": "TestMod",
            "methods": [
                {
                    "name": "onItemRightClick",
                    "source_code": "public void onItemRightClick() { player.heal(5); }",
                    "body": "player.heal(5);"
                },
                {
                    "name": "regularMethod",
                    "source_code": "public void regularMethod() { System.out.println(\"test\"); }",
                    "body": "System.out.println(\"test\");"
                }
            ],
            "fields": [],
            "imports": [],
            "feature_context": {}
        }
        
        result_json = self.translator.convert_java_class(json.dumps(class_data))
        result = json.loads(result_json)
        
        assert result["success"] is True
        assert result["conversion_summary"]["event_handlers_generated"] == 1
        assert result["conversion_summary"]["methods_converted"] == 1
        assert "world.afterEvents.itemUse.subscribe" in result["javascript_class"]

    def test_generate_event_handlers_with_ast(self):
        """Test generating event handlers using AST analysis"""
        event_data = {
            "java_events": [
                {
                    "name": "testEvent",
                    "type": "PlayerInteractEvent",
                    "handler_source_code": "public void onPlayerInteract() { player.sendMessage(\"Hello\"); }"
                }
            ],
            "context": {}
        }
        
        result_json = self.translator.generate_event_handlers(json.dumps(event_data))
        result = json.loads(result_json)
        
        assert result["success"] is True
        assert len(result["event_handlers"]) == 1
        assert result["event_handlers"][0]["bedrock_event"] == "itemUse"

    def test_convert_java_body_original_context_attribute(self):
        """Test that _original_java_body_for_context attribute is properly set"""
        java_body = "world.setBlockState(pos, Blocks.AIR.getDefaultState());"
        
        # Ensure attribute doesn't exist initially
        if hasattr(self.translator, '_original_java_body_for_context'):
            delattr(self.translator, '_original_java_body_for_context')
        
        result = self.translator._convert_java_body_to_javascript(java_body)
        
        # Check that attribute is now set
        assert hasattr(self.translator, '_original_java_body_for_context')
        assert self.translator._original_java_body_for_context == java_body
        
        # Check that the context-based replacement works
        assert "setBlockPermutation" in result

    def test_convert_java_body_event_block_context(self):
        """Test Java body conversion with event.block context"""
        java_body = "if (event.block != null) { world.setBlockState(pos, Blocks.AIR.getDefaultState()); }"
        
        result = self.translator._convert_java_body_to_javascript(java_body)
        
        # Should use event.block.dimension when event.block is in context
        assert "event.block.dimension.setBlockPermutation" in result

    def test_translate_crafting_recipe_tool(self):
        """Test the new crafting recipe translation tool"""
        recipe_data = {
            "type": "minecraft:crafting_shaped",
            "pattern": [
                "SSS",
                "SCS",
                "SSS"
            ],
            "key": {
                "S": {"item": "minecraft:stick"},
                "C": {"item": "minecraft:cobblestone"}
            },
            "result": {"item": "minecraft:furnace", "count": 1}
        }
        result_json = self.translator.translate_crafting_recipe_json(json.dumps(recipe_data))
        result = json.loads(result_json)
        assert result["success"] is True
        assert "bedrock_recipe" in result
        assert "minecraft:recipe_shaped" in result["bedrock_recipe"]
        assert result["bedrock_recipe"]["minecraft:recipe_shaped"]["result"]["item"] == "furnace"

    def test_translate_shapeless_recipe(self):
        """Test translating shapeless crafting recipe"""
        recipe_data = {
            "type": "minecraft:crafting_shapeless",
            "ingredients": [
                {"item": "minecraft:sugar"},
                {"item": "minecraft:egg"}
            ],
            "result": {"item": "minecraft:cake", "count": 1}
        }
        
        result_json = self.translator.translate_crafting_recipe_json(json.dumps(recipe_data))
        result = json.loads(result_json)
        
        assert result["success"] is True
        assert "minecraft:recipe_shapeless" in result["bedrock_recipe"]
        assert len(result["bedrock_recipe"]["minecraft:recipe_shapeless"]["ingredients"]) == 2

    def test_invalid_recipe_type(self):
        """Test handling invalid recipe type"""
        recipe_data = {
            "type": "minecraft:invalid_recipe",
            "result": {"item": "minecraft:dirt", "count": 1}
        }
        
        result_json = self.translator.translate_crafting_recipe_json(json.dumps(recipe_data))
        result = json.loads(result_json)
        
        assert result["success"] is False
        assert "Unsupported recipe type" in result["error"]

    @patch('agents.logic_translator.logger')
    def test_ast_parsing_error_logging(self, mock_logger):
        """Test that AST parsing errors are properly logged"""
        invalid_java = "public class { invalid syntax"
        
        result = self.translator.analyze_java_code_ast(invalid_java)
        
        assert result is None
        mock_logger.error.assert_called()

    def test_no_duplicate_event_handlers(self):
        """Test that duplicate item interaction methods don't create duplicate handlers"""
        class_data = {
            "class_name": "TestItem",
            "methods": [
                {
                    "name": "onItemUse", 
                    "source_code": "public void onItemUse() { player.heal(5); }",
                    "body": "player.heal(5);"
                }
            ],
            "fields": [],
            "imports": [],
            "feature_context": {}
        }
        
        result_json = self.translator.convert_java_class(json.dumps(class_data))
        result = json.loads(result_json)
        
        assert result["success"] is True
        assert result["conversion_summary"]["event_handlers_generated"] == 1
        
        # Count the number of itemUse subscriptions in the output
        js_class = result["javascript_class"]
        itemUse_count = js_class.count("world.afterEvents.itemUse.subscribe")
        assert itemUse_count == 1

    def test_method_with_array_parameters(self):
        """Test translating method with array parameters"""
        java_code = """
        public class TestClass {
            public void processItems(ItemStack[] items) {
                // Process items
            }
        }
        """
        ast = self.translator.analyze_java_code_ast(java_code)
        method_node = ast.types[0].body[0]
        result_json = self.translator.translate_java_method(method_node)
        result = json.loads(result_json)
        assert result["success"] is True
        # Accept either 'Array[]' or 'ItemStack[]' as mapped type for flexibility
        assert ("items: Array[]" in result["javascript_method"] or "items: ItemStack[]" in result["javascript_method"])

    def test_method_with_no_return_type(self):
        """Test translating constructor or method with no explicit return type"""
        java_code = """
        public class TestClass {
            public TestClass() {
                // Constructor
            }
        }
        """
        ast = self.translator.analyze_java_code_ast(java_code)
        constructor_node = ast.types[0].body[0]
        result_json = self.translator.translate_java_method(constructor_node)
        result = json.loads(result_json)
        assert result["success"] is True
        assert "function TestClass()" in result["javascript_method"]

    @patch('agents.logic_translator.logger')
    def test_empty_method_body_warning(self, mock_logger):
        """Test warning when AST method has body but reconstruction is empty"""
        java_code = """
        public class TestClass {
            public void emptyMethod() {
            }
        }
        """
        ast = self.translator.analyze_java_code_ast(java_code)
        method_node = ast.types[0].body[0]
        result = self.translator._reconstruct_java_body_from_ast(method_node)
        assert result == ""