"""
Logic Translator Agent for Java to JavaScript code conversion
"""

from typing import Dict, List, Any, Optional
from crewai_tools import tool
import logging
import json
import re
from ..models.smart_assumptions import (
    SmartAssumptionEngine, FeatureContext, ConversionPlanComponent
)

logger = logging.getLogger(__name__)


class LogicTranslatorAgent:
    """
    Logic Translator Agent responsible for converting Java code to Bedrock JavaScript
    as specified in PRD Feature 2.
    """
    
    def __init__(self):
        self.smart_assumption_engine = SmartAssumptionEngine()
        
        # Java to JavaScript conversion mappings
        self.type_mappings = {
            'int': 'number',
            'double': 'number', 
            'float': 'number',
            'long': 'number',
            'boolean': 'boolean',
            'String': 'string',
            'void': 'void',
            'List': 'Array',
            'ArrayList': 'Array',
            'HashMap': 'Map',
            'Map': 'Map'
        }
        
        self.api_mappings = {
            # Common Minecraft Java to Bedrock mappings
            'player.getHealth()': 'player.getComponent("health").currentValue',
            'player.setHealth()': 'player.getComponent("health").setCurrentValue()',
            'world.getBlockAt()': 'world.getBlock()',
            'entity.getLocation()': 'entity.location',
            'ItemStack': 'ItemStack',
            'Material': 'MinecraftItemType'
        }
    
    def get_tools(self) -> List:
        """Get tools available to this agent"""
        return [
            self.translate_java_method,
            self.convert_java_class,
            self.map_java_apis,
            self.generate_event_handlers,
            self.validate_javascript_syntax
        ]
    
    @tool("Translate Java Method")
    def translate_java_method(self, method_data: str) -> str:
        """
        Translate a Java method to JavaScript for Bedrock.
        
        Args:
            method_data: JSON string containing method information:
                        method_name, return_type, parameters, body, feature_context
        
        Returns:
            JSON string with translated JavaScript method
        """
        try:
            data = json.loads(method_data)
            
            method_name = data.get('method_name', 'unknownMethod')
            return_type = data.get('return_type', 'void')
            parameters = data.get('parameters', [])
            body = data.get('body', '')
            feature_context = data.get('feature_context', {})
            
            # Convert return type
            js_return_type = self.type_mappings.get(return_type, return_type)
            
            # Convert parameters
            js_parameters = []
            for param in parameters:
                param_name = param.get('name', 'param')
                param_type = param.get('type', 'any')
                js_type = self.type_mappings.get(param_type, param_type)
                js_parameters.append(f"{param_name}: {js_type}")
            
            # Convert method body
            js_body = self._convert_java_body_to_javascript(body)
            
            # Generate JavaScript method
            if js_parameters:
                js_method = f"function {method_name}({', '.join(js_parameters)}): {js_return_type} {{\n{js_body}\n}}"
            else:
                js_method = f"function {method_name}(): {js_return_type} {{\n{js_body}\n}}"
            
            response = {
                "success": True,
                "original_method": method_name,
                "javascript_method": js_method,
                "translation_notes": [
                    f"Converted return type from {return_type} to {js_return_type}",
                    f"Converted {len(parameters)} parameters",
                    "Applied Bedrock API mappings where applicable"
                ],
                "warnings": self._get_translation_warnings(body, feature_context)
            }
            
            logger.info(f"Translated Java method {method_name} to JavaScript")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to translate method: {str(e)}"}
            logger.error(f"Method translation error: {e}")
            return json.dumps(error_response)
    
    @tool("Convert Java Class")
    def convert_java_class(self, class_data: str) -> str:
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
            
            class_name = data.get('class_name', 'UnknownClass')
            methods = data.get('methods', [])
            fields = data.get('fields', [])
            imports = data.get('imports', [])
            feature_context = data.get('feature_context', {})
            
            # Generate JavaScript class structure
            js_class_lines = [f"class {class_name} {{"]
            
            # Convert fields to properties
            for field in fields:
                field_name = field.get('name', 'unknownField')
                field_type = field.get('type', 'any')
                js_type = self.type_mappings.get(field_type, field_type)
                default_value = self._get_default_value(js_type)
                js_class_lines.append(f"    {field_name}: {js_type} = {default_value};")
            
            if fields:
                js_class_lines.append("")  # Add blank line after fields
            
            # Convert methods
            for method in methods:
                method_result = self.translate_java_method(json.dumps(method))
                method_data = json.loads(method_result)
                
                if method_data.get("success"):
                    # Extract just the method signature and body
                    js_method = method_data["javascript_method"]
                    # Indent the method for class context
                    indented_method = "    " + js_method.replace("\n", "\n    ")
                    js_class_lines.append(indented_method)
                    js_class_lines.append("")  # Add blank line after method
            
            js_class_lines.append("}")
            
            # Generate imports for Bedrock
            bedrock_imports = self._generate_bedrock_imports(imports, feature_context)
            
            js_code = "\n".join(bedrock_imports + [""] + js_class_lines)
            
            response = {
                "success": True,
                "original_class": class_name,
                "javascript_class": js_code,
                "conversion_summary": {
                    "fields_converted": len(fields),
                    "methods_converted": len(methods),
                    "imports_adapted": len(bedrock_imports)
                },
                "bedrock_compatibility_notes": self._get_compatibility_notes(feature_context)
            }
            
            logger.info(f"Converted Java class {class_name} to JavaScript")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to convert class: {str(e)}"}
            logger.error(f"Class conversion error: {e}")
            return json.dumps(error_response)
    
    @tool("Map Java APIs")
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
            
            java_apis = data.get('java_apis', [])
            context = data.get('context', {})
            
            api_mappings = []
            unsupported_apis = []
            
            for java_api in java_apis:
                bedrock_equivalent = self._find_bedrock_equivalent(java_api, context)
                
                if bedrock_equivalent:
                    api_mappings.append({
                        "java_api": java_api,
                        "bedrock_api": bedrock_equivalent["api"],
                        "confidence": bedrock_equivalent["confidence"],
                        "usage_notes": bedrock_equivalent["notes"]
                    })
                else:
                    unsupported_apis.append({
                        "java_api": java_api,
                        "reason": "No direct Bedrock equivalent available",
                        "suggested_workaround": self._suggest_workaround(java_api)
                    })
            
            response = {
                "success": True,
                "mapped_apis": api_mappings,
                "unsupported_apis": unsupported_apis,
                "mapping_summary": {
                    "total_apis": len(java_apis),
                    "successfully_mapped": len(api_mappings),
                    "unsupported": len(unsupported_apis)
                }
            }
            
            logger.info(f"Mapped {len(api_mappings)} Java APIs to Bedrock equivalents")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to map APIs: {str(e)}"}
            logger.error(f"API mapping error: {e}")
            return json.dumps(error_response)
    
    @tool("Generate Event Handlers")
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
            
            java_events = data.get('java_events', [])
            context = data.get('context', {})
            
            bedrock_handlers = []
            
            for java_event in java_events:
                event_name = java_event.get('name', 'unknownEvent')
                event_type = java_event.get('type', 'unknown')
                handler_body = java_event.get('handler_body', '')
                
                bedrock_event = self._map_java_event_to_bedrock(event_type)
                
                if bedrock_event:
                    js_handler_body = self._convert_java_body_to_javascript(handler_body)
                    
                    handler_code = f"""
world.afterEvents.{bedrock_event}.subscribe((event) => {{
    // Converted from Java {event_type} event
{js_handler_body}
}});"""
                    
                    bedrock_handlers.append({
                        "original_event": event_name,
                        "bedrock_event": bedrock_event,
                        "handler_code": handler_code.strip(),
                        "conversion_notes": f"Mapped Java {event_type} to Bedrock {bedrock_event}"
                    })
                else:
                    bedrock_handlers.append({
                        "original_event": event_name,
                        "bedrock_event": None,
                        "handler_code": f"// WARNING: No Bedrock equivalent for {event_type}",
                        "conversion_notes": f"Java event {event_type} has no direct Bedrock equivalent"
                    })
            
            response = {
                "success": True,
                "event_handlers": bedrock_handlers,
                "handler_summary": {
                    "total_events": len(java_events),
                    "converted_events": len([h for h in bedrock_handlers if h["bedrock_event"]]),
                    "unsupported_events": len([h for h in bedrock_handlers if not h["bedrock_event"]])
                }
            }
            
            logger.info(f"Generated {len(bedrock_handlers)} Bedrock event handlers")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to generate event handlers: {str(e)}"}
            logger.error(f"Event handler generation error: {e}")
            return json.dumps(error_response)
    
    @tool("Validate JavaScript Syntax")
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
            
            js_code = data.get('javascript_code', '')
            context = data.get('context', {})
            
            validation_results = {
                "syntax_valid": True,
                "syntax_errors": [],
                "bedrock_compatibility": [],
                "performance_warnings": [],
                "suggestions": []
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
                "overall_quality": "good" if validation_results["syntax_valid"] and not bedrock_issues else "needs_improvement"
            }
            
            logger.info(f"Validated JavaScript code: {response['overall_quality']}")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to validate JavaScript: {str(e)}"}
            logger.error(f"JavaScript validation error: {e}")
            return json.dumps(error_response)
    
    # Helper methods
    
    def _convert_java_body_to_javascript(self, java_body: str) -> str:
        """Convert Java method body to JavaScript"""
        js_body = java_body
        
        # Apply API mappings
        for java_api, bedrock_api in self.api_mappings.items():
            js_body = js_body.replace(java_api, bedrock_api)
        
        # Convert Java-specific syntax to JavaScript
        js_body = re.sub(r'\bSystem\.out\.println\((.*?)\)', r'console.log(\1)', js_body)
        js_body = re.sub(r'\bnew ArrayList<.*?>\(\)', r'[]', js_body)
        js_body = re.sub(r'\bnew HashMap<.*?>\(\)', r'new Map()', js_body)
        js_body = re.sub(r'\.add\(', r'.push(', js_body)
        js_body = re.sub(r'\.size\(\)', r'.length', js_body)
        
        # Add proper indentation
        lines = js_body.split('\n')
        indented_lines = ['    ' + line.strip() for line in lines if line.strip()]
        
        return '\n'.join(indented_lines)
    
    def _get_default_value(self, js_type: str) -> str:
        """Get default value for JavaScript type"""
        defaults = {
            'number': '0',
            'string': '""',
            'boolean': 'false',
            'Array': '[]',
            'Map': 'new Map()',
            'any': 'null'
        }
        return defaults.get(js_type, 'null')
    
    def _generate_bedrock_imports(self, java_imports: List[str], context: Dict) -> List[str]:
        """Generate Bedrock-specific imports from Java imports"""
        bedrock_imports = []
        
        # Common Bedrock imports
        if any('minecraft' in imp.lower() for imp in java_imports):
            bedrock_imports.extend([
                'import { world, system } from "@minecraft/server";',
                'import { MinecraftItemTypes } from "@minecraft/vanilla-data";'
            ])
        
        if any('event' in imp.lower() for imp in java_imports):
            bedrock_imports.append('import { world } from "@minecraft/server";')
        
        return bedrock_imports
    
    def _find_bedrock_equivalent(self, java_api: str, context: Dict) -> Optional[Dict]:
        """Find Bedrock equivalent for Java API"""
        if java_api in self.api_mappings:
            return {
                "api": self.api_mappings[java_api],
                "confidence": "high",
                "notes": "Direct mapping available"
            }
        
        # Pattern-based matching for common cases
        if 'player.get' in java_api.lower():
            return {
                "api": java_api.replace('.get', '.getComponent("').replace('()', '").currentValue'),
                "confidence": "medium",
                "notes": "Converted to component system"
            }
        
        return None
    
    def _suggest_workaround(self, java_api: str) -> str:
        """Suggest workaround for unsupported Java API"""
        if 'reflection' in java_api.lower():
            return "Use explicit property access instead of reflection"
        elif 'thread' in java_api.lower():
            return "Use system.run() or system.runInterval() for async operations"
        elif 'file' in java_api.lower():
            return "Store data in world dynamic properties or player storage"
        else:
            return "Consider alternative approach or request feature in Bedrock feedback"
    
    def _map_java_event_to_bedrock(self, java_event_type: str) -> Optional[str]:
        """Map Java event type to Bedrock event"""
        event_mappings = {
            'PlayerJoinEvent': 'playerSpawn',
            'PlayerQuitEvent': 'playerLeave',
            'BlockBreakEvent': 'blockBreak',
            'BlockPlaceEvent': 'blockPlace',
            'PlayerInteractEvent': 'itemUse',
            'EntityDamageEvent': 'entityHurt',
            'PlayerDeathEvent': 'entityDie'
        }
        return event_mappings.get(java_event_type)
    
    def _check_javascript_syntax(self, js_code: str) -> List[str]:
        """Check for basic JavaScript syntax issues"""
        issues = []
        
        # Basic checks
        if js_code.count('{') != js_code.count('}'):
            issues.append("Mismatched curly braces")
        
        if js_code.count('(') != js_code.count(')'):
            issues.append("Mismatched parentheses")
        
        # Check for common Java-isms that don't work in JavaScript
        if 'System.out.println' in js_code:
            issues.append("Use console.log instead of System.out.println")
        
        return issues
    
    def _check_bedrock_compatibility(self, js_code: str) -> List[str]:
        """Check for Bedrock-specific compatibility issues"""
        issues = []
        
        # Check for unsupported features
        if 'eval(' in js_code:
            issues.append("eval() is not supported in Bedrock scripting")
        
        if 'setTimeout(' in js_code:
            issues.append("Use system.runTimeout() instead of setTimeout()")
        
        if 'setInterval(' in js_code:
            issues.append("Use system.runInterval() instead of setInterval()")
        
        return issues
    
    def _check_performance_concerns(self, js_code: str) -> List[str]:
        """Check for potential performance issues"""
        warnings = []
        
        # Check for expensive operations
        if js_code.count('world.getDimension') > 5:
            warnings.append("Multiple world.getDimension() calls detected - consider caching")
        
        if 'while(true)' in js_code:
            warnings.append("Infinite loop detected - may cause server lag")
        
        return warnings
    
    def _generate_code_suggestions(self, js_code: str, context: Dict) -> List[str]:
        """Generate code improvement suggestions"""
        suggestions = []
        
        if 'console.log' in js_code:
            suggestions.append("Consider using conditional logging for production")
        
        if not any(word in js_code for word in ['try', 'catch']):
            suggestions.append("Consider adding error handling with try-catch blocks")
        
        return suggestions
    
    def _get_translation_warnings(self, java_body: str, context: Dict) -> List[str]:
        """Get warnings about translation challenges"""
        warnings = []
        
        if 'reflection' in java_body.lower():
            warnings.append("Reflection usage detected - may need manual conversion")
        
        if 'thread' in java_body.lower():
            warnings.append("Threading detected - convert to Bedrock async patterns")
        
        return warnings
    
    def _get_compatibility_notes(self, context: Dict) -> List[str]:
        """Get Bedrock compatibility notes"""
        notes = [
            "All event handlers use Bedrock's event system",
            "API calls converted to Bedrock component system where applicable",
            "Threading converted to system.run* methods"
        ]
        
        return notes
