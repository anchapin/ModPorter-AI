"""
Bedrock Architect Agent - Designs conversion strategies using Smart Assumptions
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from crewai_tools import BaseTool, tool

logger = logging.getLogger(__name__)


class ConversionPlannerTool(BaseTool):
    """Tool for creating conversion plans with smart assumptions"""
    
    name: str = "Conversion Planner Tool"
    description: str = "Creates detailed conversion plans mapping Java features to Bedrock equivalents using smart assumptions"
    
    def _run(self, analysis_data: str, smart_assumptions_table: str) -> str:
        """
        Create conversion plan based on analysis data
        
        Args:
            analysis_data: JSON string of mod analysis
            smart_assumptions_table: JSON string of available smart assumptions
            
        Returns:
            JSON string with conversion plan
        """
        try:
            analysis = json.loads(analysis_data)
            assumptions = json.loads(smart_assumptions_table)
            
            conversion_plan = {
                "mod_info": analysis.get("mod_info", {}),
                "conversion_strategy": {},
                "smart_assumptions_applied": [],
                "feature_mappings": {},
                "excluded_features": [],
                "complexity_assessment": {},
                "estimated_success_rate": 0.0
            }
            
            # Plan asset conversions
            assets = analysis.get("assets", {})
            conversion_plan["conversion_strategy"]["assets"] = self._plan_asset_conversions(assets)
            
            # Plan feature conversions
            features = analysis.get("features", {})
            conversion_plan["conversion_strategy"]["features"] = self._plan_feature_conversions(features)
            
            # Apply smart assumptions for incompatible features
            conversion_plan["smart_assumptions_applied"] = self._apply_smart_assumptions(analysis, assumptions)
            
            # Calculate estimated success rate
            conversion_plan["estimated_success_rate"] = self._calculate_success_rate(conversion_plan)
            
            return json.dumps(conversion_plan, indent=2)
            
        except Exception as e:
            logger.error(f"Error creating conversion plan: {e}")
            return json.dumps({"error": f"Failed to create conversion plan: {str(e)}"})
    
    def _plan_asset_conversions(self, assets: Dict[str, List[str]]) -> Dict[str, Any]:
        """Plan asset conversion strategies"""
        asset_plan = {
            "textures": {"strategy": "direct_convert", "format": "png", "notes": "Convert to 16x16 or 32x32 for Bedrock compatibility"},
            "models": {"strategy": "geometry_convert", "format": "bedrock_geometry", "notes": "Convert to Bedrock geometry format"},
            "sounds": {"strategy": "direct_convert", "format": "ogg", "notes": "Convert to OGG format for Bedrock"},
            "lang": {"strategy": "direct_convert", "format": "json", "notes": "Convert to Bedrock language format"},
            "data": {"strategy": "manual_review", "format": "behavior_pack", "notes": "Recipes and data require manual conversion"},
            "shaders": {"strategy": "exclude", "format": "none", "notes": "Shaders not supported in Bedrock"},
            "blockstates": {"strategy": "convert_to_components", "format": "behavior_pack", "notes": "Convert to Bedrock block components"}
        }
        
        planned_conversions = {}
        for asset_type, files in assets.items():
            if asset_type in asset_plan and files:
                planned_conversions[asset_type] = {
                    "file_count": len(files),
                    "files": files,
                    **asset_plan[asset_type]
                }
        
        return planned_conversions
    
    def _plan_feature_conversions(self, features: Dict[str, List[str]]) -> Dict[str, Any]:
        """Plan feature conversion strategies"""
        feature_plan = {
            "blocks": {"strategy": "direct_convert", "complexity": "medium", "notes": "Convert to Bedrock block format"},
            "items": {"strategy": "direct_convert", "complexity": "low", "notes": "Convert to Bedrock item format"},
            "entities": {"strategy": "behavior_mapping", "complexity": "high", "notes": "Map to closest Bedrock entity"},
            "dimensions": {"strategy": "smart_assumption", "complexity": "very_high", "notes": "Requires dimension-to-structure conversion"},
            "guis": {"strategy": "smart_assumption", "complexity": "high", "notes": "Convert to book-based interface"},
            "recipes_in_code": {"strategy": "data_pack", "complexity": "medium", "notes": "Convert to Bedrock recipe format"}
        }
        
        planned_features = {}
        for feature_type, feature_list in features.items():
            if feature_type in feature_plan and feature_list:
                planned_features[feature_type] = {
                    "count": len(feature_list),
                    "features": feature_list,
                    **feature_plan[feature_type]
                }
        
        return planned_features
    
    def _apply_smart_assumptions(self, analysis: Dict[str, Any], assumptions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply smart assumptions to incompatible features"""
        applied_assumptions = []
        
        # Check for custom dimensions
        if analysis.get("features", {}).get("dimensions"):
            dimension_assumption = next(
                (a for a in assumptions if "dimension" in a.get("java_feature", "").lower()), None
            )
            if dimension_assumption:
                applied_assumptions.append({
                    "feature_type": "custom_dimensions",
                    "assumption": dimension_assumption,
                    "affected_features": analysis["features"]["dimensions"],
                    "conversion_strategy": "Convert to large structure in Overworld"
                })
        
        # Check for custom GUIs
        if analysis.get("features", {}).get("guis"):
            gui_assumption = next(
                (a for a in assumptions if "gui" in a.get("java_feature", "").lower()), None
            )
            if gui_assumption:
                applied_assumptions.append({
                    "feature_type": "custom_guis",
                    "assumption": gui_assumption,
                    "affected_features": analysis["features"]["guis"],
                    "conversion_strategy": "Convert to book-based interface"
                })
        
        # Check for complex machinery (heuristic based on Java files)
        java_files = analysis.get("raw_analysis_data", {}).get("java_code_scan", {}).get("java_files_found", [])
        machinery_indicators = ["machine", "generator", "processor", "automation"]
        
        if any(indicator in " ".join(java_files).lower() for indicator in machinery_indicators):
            machinery_assumption = next(
                (a for a in assumptions if "machinery" in a.get("java_feature", "").lower()), None
            )
            if machinery_assumption:
                applied_assumptions.append({
                    "feature_type": "complex_machinery",
                    "assumption": machinery_assumption,
                    "affected_features": [f for f in java_files if any(ind in f.lower() for ind in machinery_indicators)],
                    "conversion_strategy": "Simplify to decorative blocks or containers"
                })
        
        # Check for client-side rendering
        if analysis.get("assets", {}).get("shaders"):
            rendering_assumption = next(
                (a for a in assumptions if "rendering" in a.get("java_feature", "").lower()), None
            )
            if rendering_assumption:
                applied_assumptions.append({
                    "feature_type": "client_rendering",
                    "assumption": rendering_assumption,
                    "affected_features": analysis["assets"]["shaders"],
                    "conversion_strategy": "Exclude from conversion with notification"
                })
        
        # Check for mod dependencies
        if analysis.get("dependencies"):
            dependency_assumption = next(
                (a for a in assumptions if "dependency" in a.get("java_feature", "").lower()), None
            )
            if dependency_assumption:
                applied_assumptions.append({
                    "feature_type": "mod_dependencies",
                    "assumption": dependency_assumption,
                    "affected_features": analysis["dependencies"],
                    "conversion_strategy": "Attempt bundling for simple dependencies"
                })
        
        return applied_assumptions
    
    def _calculate_success_rate(self, conversion_plan: Dict[str, Any]) -> float:
        """Calculate estimated conversion success rate"""
        total_score = 0.0
        total_weight = 0.0
        
        # Asset conversion scores
        assets = conversion_plan.get("conversion_strategy", {}).get("assets", {})
        for asset_type, asset_info in assets.items():
            weight = asset_info.get("file_count", 1)
            if asset_info.get("strategy") == "direct_convert":
                score = 0.9
            elif asset_info.get("strategy") == "geometry_convert":
                score = 0.7
            elif asset_info.get("strategy") == "manual_review":
                score = 0.5
            else:  # exclude
                score = 0.0
            
            total_score += score * weight
            total_weight += weight
        
        # Feature conversion scores
        features = conversion_plan.get("conversion_strategy", {}).get("features", {})
        for feature_type, feature_info in features.items():
            weight = feature_info.get("count", 1)
            complexity = feature_info.get("complexity", "medium")
            
            if complexity == "low":
                score = 0.9
            elif complexity == "medium":
                score = 0.7
            elif complexity == "high":
                score = 0.5
            else:  # very_high
                score = 0.3
            
            total_score += score * weight
            total_weight += weight
        
        # Smart assumption penalty
        assumptions_applied = len(conversion_plan.get("smart_assumptions_applied", []))
        assumption_penalty = min(assumptions_applied * 0.05, 0.3)  # Max 30% penalty
        
        if total_weight > 0:
            base_rate = total_score / total_weight
            return max(0.0, base_rate - assumption_penalty)
        
        return 0.5  # Default moderate success rate


class BedrockArchitectAgent:
    """Agent for designing Bedrock conversion strategies"""
    
    def __init__(self):
        self.conversion_planner = ConversionPlannerTool()
        logger.info("BedrockArchitectAgent initialized")
    
    @tool("Bedrock Conversion Planning Tool")
    def create_conversion_plan(self, analysis_data: str, smart_assumptions_table: str) -> str:
        """
        Create a detailed conversion plan based on mod analysis data.
        Uses smart assumptions to handle incompatible features.
        
        Args:
            analysis_data: JSON string containing mod analysis results
            smart_assumptions_table: JSON string containing available smart assumptions
            
        Returns:
            JSON string with comprehensive conversion plan
        """
        return self.conversion_planner._run(analysis_data, smart_assumptions_table)
    
    @tool("Feature Compatibility Checker")
    def check_feature_compatibility(self, feature_list: str) -> str:
        """
        Check compatibility of Java features with Bedrock platform.
        
        Args:
            feature_list: JSON string with list of features to check
            
        Returns:
            JSON string with compatibility assessment
        """
        try:
            features = json.loads(feature_list)
            
            compatibility_map = {
                "blocks": {"compatible": True, "effort": "low", "notes": "Direct conversion possible"},
                "items": {"compatible": True, "effort": "low", "notes": "Direct conversion possible"},
                "entities": {"compatible": True, "effort": "medium", "notes": "Behavior mapping required"},
                "dimensions": {"compatible": False, "effort": "high", "notes": "Requires smart assumption"},
                "guis": {"compatible": False, "effort": "high", "notes": "Requires smart assumption"},
                "recipes": {"compatible": True, "effort": "medium", "notes": "Data pack conversion"},
                "shaders": {"compatible": False, "effort": "impossible", "notes": "Not supported in Bedrock"},
                "client_rendering": {"compatible": False, "effort": "impossible", "notes": "Not supported in Bedrock"}
            }
            
            results = {}
            for feature_type, feature_items in features.items():
                if feature_type in compatibility_map:
                    results[feature_type] = {
                        "feature_count": len(feature_items) if isinstance(feature_items, list) else 1,
                        **compatibility_map[feature_type]
                    }
            
            return json.dumps(results, indent=2)
            
        except Exception as e:
            logger.error(f"Error checking feature compatibility: {e}")
            return json.dumps({"error": f"Failed to check compatibility: {str(e)}"})
    
    def get_tools(self) -> List:
        """Return available tools for this agent"""
        return [self.create_conversion_plan, self.check_feature_compatibility]