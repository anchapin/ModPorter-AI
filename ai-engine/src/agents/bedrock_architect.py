"""
Bedrock Architect Agent for conversion planning and smart assumption application
"""

from typing import Dict, List, Any, Optional

import logging
import json
from ..models.smart_assumptions import (
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
            self.analyze_java_feature,
            self.apply_smart_assumption,
            self.create_conversion_plan,
            self.get_assumption_conflicts,
            self.validate_bedrock_compatibility
        ]
    
    
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
