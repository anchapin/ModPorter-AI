"""
Logic Translator Agent - Converts Java code to Bedrock JavaScript
"""

import json
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class JavaToJavaScriptTranslator:
    """Tool for translating Java code to Bedrock JavaScript"""
    
    name: str = "Java to JavaScript Translator"
    description: str = "Translates Java code patterns to equivalent Bedrock JavaScript with proper API mappings"
    
    def _run(self, java_code: str, feature_type: str = "general") -> str:
        """
        Translate Java code to JavaScript
        
        Args:
            java_code: Java source code to translate
            feature_type: Type of feature (block, item, entity, etc.)
            
        Returns:
            JSON string with translated JavaScript code
        """
        try:
            translation_result = {
                "original_java": java_code,
                "translated_javascript": "",
                "conversion_notes": [],
                "untranslatable_sections": [],
                "api_mappings": [],
                "success_rate": 0.0
            }
            
            # Basic Java to JavaScript translations
            js_code = self._translate_basic_syntax(java_code)
            
            # Apply feature-specific translations
            if feature_type == "block":
                js_code, notes = self._translate_block_code(js_code)
                translation_result["conversion_notes"].extend(notes)
            elif feature_type == "item":
                js_code, notes = self._translate_item_code(js_code)
                translation_result["conversion_notes"].extend(notes)
            elif feature_type == "entity":
                js_code, notes = self._translate_entity_code(js_code)
                translation_result["conversion_notes"].extend(notes)
            
            # Identify untranslatable sections
            untranslatable = self._identify_untranslatable_code(java_code)
            translation_result["untranslatable_sections"] = untranslatable
            
            # Add API mappings
            translation_result["api_mappings"] = self._generate_api_mappings(java_code)
            
            # Calculate success rate
            translation_result["success_rate"] = self._calculate_translation_success_rate(
                java_code, len(untranslatable)
            )
            
            translation_result["translated_javascript"] = js_code
            
            return json.dumps(translation_result, indent=2)
            
        except Exception as e:
            logger.error(f"Error translating Java code: {e}")
            return json.dumps({"error": f"Failed to translate Java code: {str(e)}"})
    
    def _translate_basic_syntax(self, java_code: str) -> str:
        """Translate basic Java syntax to JavaScript"""
        js_code = java_code
        
        # Basic syntax replacements
        replacements = {
            "public class": "// Original: public class",
            "private static": "// Original: private static",
            "public static": "// Original: public static", 
            "protected": "// Original: protected",
            "import": "// Original import:",
            "package": "// Original package:",
            "extends": "// Original extends:",
            "implements": "// Original implements:",
            "String": "string",
            "int": "number",
            "float": "number",
            "double": "number",
            "boolean": "boolean",
            "void": "// returns void",
            "null": "undefined",
            "true": "true",
            "false": "false",
            "new ArrayList": "[]",
            "new HashMap": "{}",
            "System.out.println": "console.log"
        }
        
        for java_pattern, js_replacement in replacements.items():
            js_code = js_code.replace(java_pattern, js_replacement)
        
        return js_code
    
    def _translate_block_code(self, java_code: str) -> tuple[str, List[str]]:
        """Translate block-specific Java code to Bedrock JavaScript"""
        js_code = java_code
        notes = []
        
        # Block registration patterns
        if "registerBlock" in java_code:
            js_code = js_code.replace(
                "registerBlock", 
                "// Bedrock: Register block in behavior pack manifest"
            )
            notes.append("Block registration moved to behavior pack manifest")
        
        # Block state patterns
        if "BlockState" in java_code:
            js_code = js_code.replace(
                "BlockState", 
                "// Bedrock: Use block permutations in behavior pack"
            )
            notes.append("Block states converted to permutations")
        
        # Block properties
        if "setHardness" in java_code:
            js_code = js_code.replace(
                "setHardness", 
                "// Bedrock: Set destroy_time in block behavior"
            )
            notes.append("Block hardness mapped to destroy_time")
        
        return js_code, notes
    
    def _translate_item_code(self, java_code: str) -> tuple[str, List[str]]:
        """Translate item-specific Java code to Bedrock JavaScript"""
        js_code = java_code
        notes = []
        
        # Item registration
        if "registerItem" in java_code:
            js_code = js_code.replace(
                "registerItem", 
                "// Bedrock: Register item in behavior pack manifest"
            )
            notes.append("Item registration moved to behavior pack manifest")
        
        # Item properties
        if "setMaxStackSize" in java_code:
            js_code = js_code.replace(
                "setMaxStackSize", 
                "// Bedrock: Set max_stack_size in item behavior"
            )
            notes.append("Stack size mapped to max_stack_size property")
        
        return js_code, notes
    
    def _translate_entity_code(self, java_code: str) -> tuple[str, List[str]]:
        """Translate entity-specific Java code to Bedrock JavaScript"""
        js_code = java_code
        notes = []
        
        # Entity registration
        if "registerEntity" in java_code:
            js_code = js_code.replace(
                "registerEntity", 
                "// Bedrock: Register entity in behavior pack manifest"
            )
            notes.append("Entity registration moved to behavior pack manifest")
        
        # Entity AI
        if "EntityAI" in java_code:
            js_code = js_code.replace(
                "EntityAI", 
                "// Bedrock: Use entity behavior components"
            )
            notes.append("Entity AI converted to behavior components")
        
        return js_code, notes
    
    def _identify_untranslatable_code(self, java_code: str) -> List[Dict[str, str]]:
        """Identify sections of code that cannot be translated"""
        untranslatable = []
        
        # Complex patterns that can't be directly translated
        untranslatable_patterns = [
            ("@Override", "Method overriding not directly supported"),
            ("instanceof", "Type checking pattern needs manual conversion"),
            ("reflection", "Java reflection not available in Bedrock"),
            ("ClassLoader", "Class loading not available in Bedrock"),
            ("Thread", "Threading not available in Bedrock scripting"),
            ("synchronized", "Synchronization not available in Bedrock"),
            ("try-catch", "Error handling needs to be adapted"),
            ("Annotation", "Annotations not supported in Bedrock")
        ]
        
        for pattern, reason in untranslatable_patterns:
            if pattern in java_code:
                untranslatable.append({
                    "pattern": pattern,
                    "reason": reason,
                    "suggestion": "Manual conversion required"
                })
        
        return untranslatable
    
    def _generate_api_mappings(self, java_code: str) -> List[Dict[str, str]]:
        """Generate API mappings from Java to Bedrock"""
        mappings = []
        
        # Common API mappings
        api_mappings = {
            "Block.setHardness": "minecraft:destructible_by_mining component",
            "Item.setMaxStackSize": "minecraft:max_stack_size component", 
            "Entity.setHealth": "minecraft:health component",
            "World.setBlock": "dimension.setBlockType()",
            "Player.addItem": "player.getComponent('inventory').container.addItem()",
            "Block.onRightClick": "minecraft:on_interact component",
            "Entity.tick": "minecraft:tick component"
        }
        
        for java_api, bedrock_api in api_mappings.items():
            if java_api.split('.')[0] in java_code or java_api.split('.')[1] in java_code:
                mappings.append({
                    "java_api": java_api,
                    "bedrock_api": bedrock_api,
                    "notes": "Direct API mapping available"
                })
        
        return mappings
    
    def _calculate_translation_success_rate(self, java_code: str, untranslatable_count: int) -> float:
        """Calculate the success rate of translation"""
        total_lines = len(java_code.split('\n'))
        if total_lines == 0:
            return 0.0
        
        # Base success rate
        base_rate = 0.7  # Assume 70% base success for basic syntax
        
        # Penalty for untranslatable sections
        penalty = min(untranslatable_count * 0.1, 0.5)  # Max 50% penalty
        
        # Bonus for simple code
        if total_lines < 50:
            bonus = 0.1
        else:
            bonus = 0.0
        
        return max(0.0, min(1.0, base_rate - penalty + bonus))


class LogicTranslatorAgent:
    """Agent for translating Java logic to Bedrock JavaScript"""
    
    def __init__(self):
        self.translator = JavaToJavaScriptTranslator()
        logger.info("LogicTranslatorAgent initialized")
    
    def translate_java_code(self, java_code: str, feature_type: str = "general") -> str:
        """
        Translate Java code to Bedrock JavaScript equivalent.
        
        Args:
            java_code: Java source code to translate
            feature_type: Type of feature (block, item, entity, etc.)
            
        Returns:
            JSON string with translation results
        """
        return self.translator._run(java_code, feature_type)
    
    def generate_api_mappings(self, java_apis: str) -> str:
        """
        Generate mappings from Java APIs to Bedrock equivalents.
        
        Args:
            java_apis: JSON string with list of Java APIs used
            
        Returns:
            JSON string with API mappings
        """
        try:
            apis = json.loads(java_apis)
            
            # Comprehensive API mapping table
            api_mapping_table = {
                # Block APIs
                "Block.setHardness": {
                    "bedrock_equivalent": "minecraft:destructible_by_mining",
                    "type": "component",
                    "notes": "Set in block behavior file"
                },
                "Block.setResistance": {
                    "bedrock_equivalent": "minecraft:destructible_by_explosion", 
                    "type": "component",
                    "notes": "Set explosion resistance"
                },
                "Block.setLightLevel": {
                    "bedrock_equivalent": "minecraft:light_emission",
                    "type": "component", 
                    "notes": "Set light emission level"
                },
                
                # Item APIs
                "Item.setMaxStackSize": {
                    "bedrock_equivalent": "minecraft:max_stack_size",
                    "type": "component",
                    "notes": "Set in item behavior file"
                },
                "Item.setDurability": {
                    "bedrock_equivalent": "minecraft:durability",
                    "type": "component",
                    "notes": "Set item durability"
                },
                
                # Entity APIs
                "Entity.setHealth": {
                    "bedrock_equivalent": "minecraft:health",
                    "type": "component",
                    "notes": "Set entity health"
                },
                "Entity.setMovementSpeed": {
                    "bedrock_equivalent": "minecraft:movement",
                    "type": "component",
                    "notes": "Set movement speed"
                },
                
                # World APIs
                "World.setBlock": {
                    "bedrock_equivalent": "dimension.setBlockType()",
                    "type": "script_api",
                    "notes": "Use scripting API"
                },
                "World.getBlock": {
                    "bedrock_equivalent": "dimension.getBlock()",
                    "type": "script_api",
                    "notes": "Use scripting API"
                },
                
                # Player APIs
                "Player.addItem": {
                    "bedrock_equivalent": "player.getComponent('inventory').container.addItem()",
                    "type": "script_api",
                    "notes": "Use inventory component"
                },
                "Player.sendMessage": {
                    "bedrock_equivalent": "player.sendMessage()",
                    "type": "script_api",
                    "notes": "Send message to player"
                }
            }
            
            mappings = []
            for api in apis:
                if api in api_mapping_table:
                    mappings.append({
                        "java_api": api,
                        **api_mapping_table[api]
                    })
                else:
                    mappings.append({
                        "java_api": api,
                        "bedrock_equivalent": "No direct equivalent",
                        "type": "manual",
                        "notes": "Requires manual implementation or smart assumption"
                    })
            
            return json.dumps({"api_mappings": mappings}, indent=2)
            
        except Exception as e:
            logger.error(f"Error generating API mappings: {e}")
            return json.dumps({"error": f"Failed to generate API mappings: {str(e)}"})
    
    def analyze_code_complexity(self, java_code: str) -> str:
        """
        Analyze complexity of Java code for translation difficulty assessment.
        
        Args:
            java_code: Java source code to analyze
            
        Returns:
            JSON string with complexity analysis
        """
        try:
            complexity_analysis = {
                "total_lines": len(java_code.split('\n')),
                "complexity_factors": [],
                "difficulty_score": 0.0,
                "translation_challenges": []
            }
            
            # Analyze complexity factors
            complexity_factors = [
                ("class", "Class definitions", 1),
                ("interface", "Interface definitions", 2),
                ("extends", "Inheritance", 2),
                ("implements", "Interface implementation", 2),
                ("@Override", "Method overriding", 3),
                ("synchronized", "Thread synchronization", 5),
                ("reflection", "Java reflection", 5),
                ("ClassLoader", "Dynamic class loading", 5),
                ("Thread", "Threading", 4),
                ("try-catch", "Exception handling", 2),
                ("switch", "Switch statements", 1),
                ("for", "Loops", 1),
                ("while", "Loops", 1),
                ("if", "Conditional statements", 1)
            ]
            
            difficulty_score = 0
            for pattern, description, weight in complexity_factors:
                count = java_code.count(pattern)
                if count > 0:
                    factor_score = count * weight
                    difficulty_score += factor_score
                    complexity_analysis["complexity_factors"].append({
                        "pattern": pattern,
                        "description": description,
                        "occurrences": count,
                        "weight": weight,
                        "contribution": factor_score
                    })
            
            complexity_analysis["difficulty_score"] = difficulty_score
            
            # Determine overall difficulty
            if difficulty_score < 10:
                difficulty = "Low"
                challenges = ["Basic syntax translation", "Simple API mapping"]
            elif difficulty_score < 25:
                difficulty = "Medium"
                challenges = ["API mapping required", "Some manual conversion needed"]
            elif difficulty_score < 50:
                difficulty = "High"
                challenges = ["Complex API mapping", "Significant manual work", "Smart assumptions likely needed"]
            else:
                difficulty = "Very High"
                challenges = ["Extensive manual conversion", "Multiple smart assumptions", "Some features may be impossible"]
            
            complexity_analysis["overall_difficulty"] = difficulty
            complexity_analysis["translation_challenges"] = challenges
            
            return json.dumps(complexity_analysis, indent=2)
            
        except Exception as e:
            logger.error(f"Error analyzing code complexity: {e}")
            return json.dumps({"error": f"Failed to analyze complexity: {str(e)}"})
    
    def get_tools(self) -> List:
        """Return available tools for this agent"""
        return [self.translate_java_code, self.generate_api_mappings, self.analyze_code_complexity]
