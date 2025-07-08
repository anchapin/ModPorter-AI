"""
Bedrock Architect Agent for conversion planning and smart assumption application
"""

from typing import Dict, List, Any, Optional

import logging
import json
from langchain.tools import tool
from src.models.smart_assumptions import (
    SmartAssumptionEngine, FeatureContext, AssumptionResult, 
    ConversionPlanComponent, AssumptionReport
)

logger = logging.getLogger(__name__)


class BedrockArchitectAgent:
    """
    Bedrock Architect Agent responsible for designing optimal conversion strategies
    using smart assumptions as specified in PRD Feature 2.
    """
    
    def __init__(self):
        self.smart_assumption_engine = SmartAssumptionEngine()
        
    def get_tools(self) -> List:
        """Get tools available to this agent"""
        return [
            self.analyze_java_feature_tool,
            self.apply_smart_assumption_tool,
            self.create_conversion_plan_tool,
            self.get_assumption_conflicts_tool,
            self.validate_bedrock_compatibility_tool,
            self.generate_block_definitions_tool,
            self.generate_item_definitions_tool,
            self.generate_recipe_definitions_tool,
            self.generate_entity_definitions_tool
        ]
    
    @tool
    def analyze_java_feature_tool(self, feature_data: str) -> str:
        """Analyze a Java mod feature to determine applicable smart assumptions."""
        return self.analyze_java_feature(feature_data)
    
    @tool
    def apply_smart_assumption_tool(self, assumption_data: str) -> str:
        """Apply smart assumption to a feature."""
        return self.apply_smart_assumption(assumption_data)
    
    @tool
    def create_conversion_plan_tool(self, plan_data: str) -> str:
        """Create a conversion plan for features."""
        return self.create_conversion_plan(plan_data)
    
    @tool
    def get_assumption_conflicts_tool(self, conflict_data: str) -> str:
        """Get assumption conflicts for features."""
        return self.get_assumption_conflicts(conflict_data)
    
    @tool
    def validate_bedrock_compatibility_tool(self, compatibility_data: str) -> str:
        """Validate Bedrock compatibility of features."""
        return self.validate_bedrock_compatibility(compatibility_data)
    
    
    def analyze_java_feature(self, feature_data: str) -> str:
        """
        Analyze a Java mod feature to determine applicable smart assumptions.
        
        Args:
            feature_data: JSON string containing feature information with keys:
                         feature_id, feature_type, name, original_data
        
        Returns:
            JSON string with analysis results including applicable assumptions
        """
        try:
            data = json.loads(feature_data)
            
            # Create FeatureContext from input data
            feature_context = FeatureContext(
                feature_id=data.get('feature_id', 'unknown'),
                feature_type=data.get('feature_type', 'unknown'),
                name=data.get('name'),
                original_data=data.get('original_data', {})
            )
            
            # Analyze using Smart Assumptions Engine
            result = self.smart_assumption_engine.analyze_feature(feature_context)
            
            response = {
                "feature_id": feature_context.feature_id,
                "feature_type": feature_context.feature_type,
                "has_applicable_assumption": result.applied_assumption is not None,
                "applicable_assumption": result.applied_assumption.java_feature if result.applied_assumption else None,
                "has_conflicts": len(result.conflicting_assumptions) > 0,
                "conflicting_assumptions": [a.java_feature for a in result.conflicting_assumptions],
                "conflict_resolution": result.conflict_resolution_reason,
                "recommendation": self._get_conversion_recommendation(result)
            }
            
            logger.info(f"Analyzed feature {feature_context.feature_id}: {response}")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"error": f"Failed to analyze feature: {str(e)}"}
            logger.error(f"Feature analysis error: {e}")
            return json.dumps(error_response)
    
    
    def apply_smart_assumption(self, analysis_result_data: str) -> str:
        """
        Apply a smart assumption to a feature and generate conversion plan component.
        
        Args:
            analysis_result_data: JSON string containing analysis result and feature context
        
        Returns:
            JSON string with conversion plan component details
        """
        try:
            data = json.loads(analysis_result_data)
            
            # Reconstruct feature context and assumption result
            feature_context = FeatureContext(
                feature_id=data['feature_context']['feature_id'],
                feature_type=data['feature_context']['feature_type'],
                name=data['feature_context'].get('name'),
                original_data=data['feature_context'].get('original_data', {})
            )
            
            # Re-analyze to get current assumption
            analysis_result = self.smart_assumption_engine.analyze_feature(feature_context)
            
            if not analysis_result.applied_assumption:
                return json.dumps({"error": "No applicable assumption found for feature"})
            
            # Apply the assumption
            plan_component = self.smart_assumption_engine.apply_assumption(analysis_result)
            
            if plan_component:
                response = {
                    "success": True,
                    "conversion_plan_component": {
                        "original_feature_id": plan_component.original_feature_id,
                        "original_feature_type": plan_component.original_feature_type,
                        "assumption_type": plan_component.assumption_type,
                        "bedrock_equivalent": plan_component.bedrock_equivalent,
                        "impact_level": plan_component.impact_level,
                        "user_explanation": plan_component.user_explanation,
                        "technical_notes": plan_component.technical_notes
                    }
                }
                logger.info(f"Applied assumption for {feature_context.feature_id}: {plan_component.assumption_type}")
            else:
                response = {"success": False, "error": "Failed to generate conversion plan component"}
            
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to apply assumption: {str(e)}"}
            logger.error(f"Assumption application error: {e}")
            return json.dumps(error_response)
    
    
    def create_conversion_plan(self, features_data: str) -> str:
        """
        Create a comprehensive conversion plan for multiple features.
        
        Args:
            features_data: JSON string containing list of features to convert
        
        Returns:
            JSON string with complete conversion plan and assumption report
        """
        try:
            features = json.loads(features_data)
            plan_components = []
            
            for feature_data in features:
                # Create feature context
                feature_context = FeatureContext(
                    feature_id=feature_data.get('feature_id', 'unknown'),
                    feature_type=feature_data.get('feature_type', 'unknown'),
                    name=feature_data.get('name'),
                    original_data=feature_data.get('original_data', {})
                )
                
                # Analyze and apply assumptions
                analysis_result = self.smart_assumption_engine.analyze_feature(feature_context)
                
                if analysis_result.applied_assumption:
                    plan_component = self.smart_assumption_engine.apply_assumption(analysis_result)
                    if plan_component:
                        plan_components.append(plan_component)
                        logger.info(f"Added conversion plan for {feature_context.feature_id}")
                else:
                    logger.info(f"No assumption applicable for {feature_context.feature_id}, skipping")
            
            # Generate assumption report
            assumption_report = self.smart_assumption_engine.generate_assumption_report(plan_components)
            
            response = {
                "success": True,
                "conversion_plan_components": len(plan_components),
                "features_requiring_assumptions": len([c for c in plan_components]),
                "assumption_report": {
                    "assumptions_applied": [
                        {
                            "original_feature": item.original_feature,
                            "assumption_type": item.assumption_type,
                            "bedrock_equivalent": item.bedrock_equivalent,
                            "impact_level": item.impact_level,
                            "user_explanation": item.user_explanation
                        }
                        for item in assumption_report.assumptions_applied
                    ]
                },
                "detailed_components": [
                    {
                        "original_feature_id": comp.original_feature_id,
                        "original_feature_type": comp.original_feature_type,
                        "assumption_type": comp.assumption_type,
                        "bedrock_equivalent": comp.bedrock_equivalent,
                        "impact_level": comp.impact_level,
                        "user_explanation": comp.user_explanation,
                        "technical_notes": comp.technical_notes
                    }
                    for comp in plan_components
                ]
            }
            
            logger.info(f"Created conversion plan with {len(plan_components)} components")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to create conversion plan: {str(e)}"}
            logger.error(f"Conversion plan creation error: {e}")
            return json.dumps(error_response)
    
    
    def get_assumption_conflicts(self, feature_type: str) -> str:
        """
        Get detailed information about assumption conflicts for a feature type.
        
        Args:
            feature_type: The type of feature to analyze for conflicts
        
        Returns:
            JSON string with conflict analysis details
        """
        try:
            conflict_analysis = self.smart_assumption_engine.get_conflict_analysis(feature_type)
            logger.info(f"Conflict analysis for {feature_type}: {conflict_analysis}")
            return json.dumps(conflict_analysis)
            
        except Exception as e:
            error_response = {"error": f"Failed to analyze conflicts: {str(e)}"}
            logger.error(f"Conflict analysis error: {e}")
            return json.dumps(error_response)
    
    
    def validate_bedrock_compatibility(self, conversion_plan_data: str) -> str:
        """
        Validate that a conversion plan is compatible with Bedrock limitations.
        
        Args:
            conversion_plan_data: JSON string containing conversion plan components
        
        Returns:
            JSON string with compatibility validation results
        """
        try:
            plan_data = json.loads(conversion_plan_data)
            components = plan_data.get('components', [])
            
            validation_results = {
                "is_compatible": True,
                "warnings": [],
                "recommendations": [],
                "component_validations": []
            }
            
            for component in components:
                component_validation = self._validate_component_compatibility(component)
                validation_results["component_validations"].append(component_validation)
                
                if not component_validation["is_compatible"]:
                    validation_results["is_compatible"] = False
                
                validation_results["warnings"].extend(component_validation.get("warnings", []))
                validation_results["recommendations"].extend(component_validation.get("recommendations", []))
            
            logger.info(f"Validated {len(components)} conversion components")
            return json.dumps(validation_results)
            
        except Exception as e:
            error_response = {"error": f"Failed to validate compatibility: {str(e)}"}
            logger.error(f"Compatibility validation error: {e}")
            return json.dumps(error_response)
    
    def _get_conversion_recommendation(self, analysis_result: AssumptionResult) -> str:
        """Get conversion recommendation based on analysis result"""
        if not analysis_result.applied_assumption:
            return "Feature appears to be directly convertible without assumptions"
        
        assumption = analysis_result.applied_assumption
        if assumption.impact.value == "high":
            return f"High-impact conversion required using {assumption.java_feature} assumption. Significant functionality changes expected."
        elif assumption.impact.value == "medium":
            return f"Moderate conversion using {assumption.java_feature} assumption. Some functionality changes expected."
        else:
            return f"Low-impact conversion using {assumption.java_feature} assumption. Minimal functionality changes expected."
    
    def _validate_component_compatibility(self, component: Dict[str, Any]) -> Dict[str, Any]:
        """Validate individual component compatibility with Bedrock"""
        validation = {
            "component_id": component.get("original_feature_id", "unknown"),
            "is_compatible": True,
            "warnings": [],
            "recommendations": []
        }
        
        assumption_type = component.get("assumption_type", "")
        impact_level = component.get("impact_level", "")
        
        # Check for high-impact conversions
        if impact_level == "high":
            validation["warnings"].append(f"High-impact conversion may result in significant functionality loss")
            validation["recommendations"].append("Review user expectations and provide clear documentation about changes")
        
        # Check for specific assumption types
        if "dimension" in assumption_type:
            validation["warnings"].append("Custom dimension converted to static structure - dynamic generation lost")
            validation["recommendations"].append("Consider creating multiple structure variants for variety")
        
        elif "machinery" in assumption_type:
            validation["warnings"].append("Complex machinery logic will be simplified or removed")
            validation["recommendations"].append("Preserve visual aesthetics and consider alternative interaction methods")
        
        elif "gui" in assumption_type:
            validation["warnings"].append("Interactive GUI elements will become static text")
            validation["recommendations"].append("Reorganize information for optimal book presentation")
        
        return validation

    # --- Placeholder methods for Bedrock Definition Generation ---

    @tool
    def generate_block_definitions_tool(self, block_data: str) -> str:
        """Generate Bedrock block definition files (placeholder).
        Args:
            block_data: JSON string containing block information (e.g., id, name, properties).
        Returns:
            JSON string with success status and placeholder block definition.
        """
        return self._generate_placeholder_definition(block_data, "block")

    @tool
    def generate_item_definitions_tool(self, item_data: str) -> str:
        """Generate Bedrock item definition files (placeholder).
        Args:
            item_data: JSON string containing item information (e.g., id, name, components).
        Returns:
            JSON string with success status and placeholder item definition.
        """
        return self._generate_placeholder_definition(item_data, "item")

    @tool
    def generate_recipe_definitions_tool(self, recipe_data: str) -> str:
        """Generate Bedrock recipe JSON files (placeholder).
        Args:
            recipe_data: JSON string containing recipe information (e.g., id, ingredients, result).
        Returns:
            JSON string with success status and placeholder recipe definition.
        """
        return self._generate_placeholder_definition(recipe_data, "recipe")

    @tool
    def generate_entity_definitions_tool(self, entity_data: str) -> str:
        """Generate Bedrock entity definition files (placeholder).
        Args:
            entity_data: JSON string containing entity information (e.g., id, name, components, behaviors).
        Returns:
            JSON string with success status and placeholder entity definition.
        """
        return self._generate_placeholder_definition(entity_data, "entity")

    def _generate_placeholder_definition(self, component_data_str: str, component_type: str) -> str:
        """
        Generic placeholder for generating Bedrock component definitions.
        """
        try:
            component_data = json.loads(component_data_str)
            identifier = component_data.get("identifier", f"custom:{component_data.get('id', f'{component_type}_placeholder')}")
            name = component_data.get("name", f"Custom {component_type.capitalize()}")

            # Basic placeholder structure common to many Bedrock definitions
            placeholder_definition = {
                "format_version": "1.20.0", # Using a recent common version
                f"minecraft:{component_type}": {
                    "description": {
                        "identifier": identifier
                    },
                    "components": {
                        "minecraft:display_name": { # Common component for user-visible name
                            "value": name
                        },
                        # Specific components would vary greatly depending on component_type
                        # Example: A block might have "minecraft:material_instances"
                        # An item might have "minecraft:icon"
                        # An entity might have "minecraft:collision_box"
                    },
                    "metadata_generated": { # Custom section for our tool's info
                        "source_java_id": component_data.get('id', 'unknown_java_id'),
                        "conversion_tool": "ModPorterAI_BedrockArchitect",
                        "conversion_notes": f"This is an AI-generated placeholder {component_type} definition. Review and refine."
                    }
                }
            }

            # Add type-specific components if needed for a basic valid structure
            if component_type == "block":
                placeholder_definition[f"minecraft:{component_type}"]["components"]["minecraft:loot"] = f"loot_tables/blocks/{component_data.get('id', 'placeholder_block')}.json"
                placeholder_definition[f"minecraft:{component_type}"]["components"]["minecraft:destructible_by_mining"] = {"seconds_to_destroy": 1.0}
            elif component_type == "item":
                placeholder_definition[f"minecraft:{component_type}"]["components"]["minecraft:icon"] = {"texture": component_data.get('id', 'placeholder_item_icon')}
                placeholder_definition[f"minecraft:{component_type}"]["components"]["minecraft:max_stack_size"] = 64
            elif component_type == "entity":
                placeholder_definition[f"minecraft:{component_type}"]["components"]["minecraft:type_family"] = {"family": [component_type, "mob"]}
                placeholder_definition[f"minecraft:{component_type}"]["components"]["minecraft:health"] = {"value": 20, "max": 20}


            logger.info(f"Generated placeholder {component_type} definition for identifier: {identifier}")
            return json.dumps({
                "success": True,
                "component_type": component_type,
                "identifier": identifier,
                "definition_json": placeholder_definition, # Return the definition as a JSON object, not a string
                "message": f"Placeholder {component_type} definition generated successfully for {identifier}."
            }, indent=2)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON input for placeholder {component_type} definition: {str(e)} - Input: {component_data_str[:500]}...", exc_info=True) # Log part of the input
            return json.dumps({
                "success": False,
                "error": f"Invalid JSON input for {component_type} definition: {str(e)}"
            }, indent=2)
        except Exception as e:
            logger.error(f"Error generating placeholder {component_type} definition: {e}", exc_info=True)
            return json.dumps({
                "success": False,
                "error": f"Failed to generate placeholder {component_type} definition: {str(e)}"
            }, indent=2)
