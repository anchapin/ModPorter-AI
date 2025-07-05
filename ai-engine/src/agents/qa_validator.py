"""
QA Validator Agent - Validates conversion quality and generates comprehensive reports
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from crewai_tools import BaseTool, tool
from datetime import datetime

logger = logging.getLogger(__name__)


class ConversionQualityChecker(BaseTool):
    """Tool for checking overall conversion quality"""
    
    name: str = "Conversion Quality Checker"
    description: str = "Evaluates the quality and completeness of mod conversion"
    
    def _run(self, conversion_data: str) -> str:
        """
        Check conversion quality
        
        Args:
            conversion_data: JSON string with complete conversion results
            
        Returns:
            JSON string with quality assessment
        """
        try:
            data = json.loads(conversion_data)
            
            quality_assessment = {
                "overall_score": 0.0,
                "quality_metrics": {},
                "feature_completeness": {},
                "asset_quality": {},
                "code_translation_quality": {},
                "smart_assumption_impact": {},
                "issues_found": [],
                "recommendations": []
            }
            
            # Assess feature completeness
            self._assess_feature_completeness(data, quality_assessment)
            
            # Assess asset quality
            self._assess_asset_quality(data, quality_assessment)
            
            # Assess code translation quality
            self._assess_code_translation_quality(data, quality_assessment)
            
            # Assess smart assumption impact
            self._assess_smart_assumption_impact(data, quality_assessment)
            
            # Calculate overall score
            quality_assessment["overall_score"] = self._calculate_overall_score(quality_assessment)
            
            # Generate recommendations
            self._generate_recommendations(quality_assessment)
            
            return json.dumps(quality_assessment, indent=2)
            
        except Exception as e:
            logger.error(f"Error checking conversion quality: {e}")
            return json.dumps({"error": f"Failed to check conversion quality: {str(e)}"})
    
    def _assess_feature_completeness(self, data: Dict, assessment: Dict):
        """Assess completeness of feature conversion"""
        original_features = data.get("analysis", {}).get("features", {})
        converted_features = data.get("feature_conversions", {})
        
        completeness_metrics = {
            "total_features": 0,
            "successfully_converted": 0,
            "partially_converted": 0,
            "failed_conversions": 0,
            "excluded_features": 0
        }
        
        for feature_type, feature_list in original_features.items():
            if isinstance(feature_list, list):
                completeness_metrics["total_features"] += len(feature_list)
                
                # Check if features were converted
                if feature_type in converted_features:
                    converted_list = converted_features[feature_type]
                    if isinstance(converted_list, list):
                        for feature in converted_list:
                            if isinstance(feature, dict):
                                status = feature.get("status", "unknown")
                                if status == "success":
                                    completeness_metrics["successfully_converted"] += 1
                                elif status == "partial":
                                    completeness_metrics["partially_converted"] += 1
                                elif status == "failed":
                                    completeness_metrics["failed_conversions"] += 1
                                elif status == "excluded":
                                    completeness_metrics["excluded_features"] += 1
                else:
                    completeness_metrics["failed_conversions"] += len(feature_list)
        
        # Calculate completeness percentage
        if completeness_metrics["total_features"] > 0:
            success_rate = (completeness_metrics["successfully_converted"] + 
                          completeness_metrics["partially_converted"] * 0.5) / completeness_metrics["total_features"]
        else:
            success_rate = 0.0
        
        assessment["feature_completeness"] = {
            **completeness_metrics,
            "success_rate": success_rate
        }
    
    def _assess_asset_quality(self, data: Dict, assessment: Dict):
        """Assess quality of asset conversion"""
        asset_conversions = data.get("asset_conversions", {})
        
        asset_metrics = {
            "total_assets": 0,
            "successful_conversions": 0,
            "failed_conversions": 0,
            "format_issues": 0,
            "resolution_issues": 0
        }
        
        for asset_type, asset_list in asset_conversions.items():
            if isinstance(asset_list, list):
                asset_metrics["total_assets"] += len(asset_list)
                
                for asset in asset_list:
                    if isinstance(asset, dict):
                        if asset.get("success", False):
                            asset_metrics["successful_conversions"] += 1
                        else:
                            asset_metrics["failed_conversions"] += 1
                        
                        # Check for format issues
                        if asset.get("format") not in ["PNG", "OGG", "Bedrock Geometry"]:
                            asset_metrics["format_issues"] += 1
                        
                        # Check for resolution issues
                        if asset_type == "textures":
                            size = asset.get("target_size", "")
                            if size not in ["16x16", "32x32", "64x64"]:
                                asset_metrics["resolution_issues"] += 1
        
        # Calculate asset quality score
        if asset_metrics["total_assets"] > 0:
            quality_score = asset_metrics["successful_conversions"] / asset_metrics["total_assets"]
        else:
            quality_score = 0.0
        
        assessment["asset_quality"] = {
            **asset_metrics,
            "quality_score": quality_score
        }
    
    def _assess_code_translation_quality(self, data: Dict, assessment: Dict):
        """Assess quality of code translation"""
        code_translations = data.get("code_translations", {})
        
        translation_metrics = {
            "total_files": 0,
            "successful_translations": 0,
            "partial_translations": 0,
            "failed_translations": 0,
            "untranslatable_sections": 0,
            "api_mappings_found": 0
        }
        
        for file_path, translation in code_translations.items():
            if isinstance(translation, dict):
                translation_metrics["total_files"] += 1
                
                success_rate = translation.get("success_rate", 0.0)
                if success_rate >= 0.8:
                    translation_metrics["successful_translations"] += 1
                elif success_rate >= 0.4:
                    translation_metrics["partial_translations"] += 1
                else:
                    translation_metrics["failed_translations"] += 1
                
                # Count untranslatable sections
                untranslatable = translation.get("untranslatable_sections", [])
                translation_metrics["untranslatable_sections"] += len(untranslatable)
                
                # Count API mappings
                api_mappings = translation.get("api_mappings", [])
                translation_metrics["api_mappings_found"] += len(api_mappings)
        
        # Calculate translation quality score
        if translation_metrics["total_files"] > 0:
            quality_score = (translation_metrics["successful_translations"] + 
                           translation_metrics["partial_translations"] * 0.5) / translation_metrics["total_files"]
        else:
            quality_score = 0.0
        
        assessment["code_translation_quality"] = {
            **translation_metrics,
            "quality_score": quality_score
        }
    
    def _assess_smart_assumption_impact(self, data: Dict, assessment: Dict):
        """Assess impact of smart assumptions on conversion quality"""
        smart_assumptions = data.get("smart_assumptions_applied", [])
        
        impact_metrics = {
            "total_assumptions": len(smart_assumptions),
            "high_impact_assumptions": 0,
            "medium_impact_assumptions": 0,
            "low_impact_assumptions": 0,
            "assumption_categories": {}
        }
        
        for assumption in smart_assumptions:
            if isinstance(assumption, dict):
                impact_level = assumption.get("assumption", {}).get("impact", "medium")
                
                if impact_level == "high":
                    impact_metrics["high_impact_assumptions"] += 1
                elif impact_level == "medium":
                    impact_metrics["medium_impact_assumptions"] += 1
                else:
                    impact_metrics["low_impact_assumptions"] += 1
                
                # Categorize assumptions
                feature_type = assumption.get("feature_type", "unknown")
                if feature_type not in impact_metrics["assumption_categories"]:
                    impact_metrics["assumption_categories"][feature_type] = 0
                impact_metrics["assumption_categories"][feature_type] += 1
        
        # Calculate impact score (lower is better)
        if impact_metrics["total_assumptions"] > 0:
            impact_score = (impact_metrics["high_impact_assumptions"] * 0.3 + 
                          impact_metrics["medium_impact_assumptions"] * 0.2 + 
                          impact_metrics["low_impact_assumptions"] * 0.1) / impact_metrics["total_assumptions"]
        else:
            impact_score = 0.0
        
        assessment["smart_assumption_impact"] = {
            **impact_metrics,
            "impact_score": impact_score
        }
    
    def _calculate_overall_score(self, assessment: Dict) -> float:
        """Calculate overall conversion quality score"""
        feature_score = assessment.get("feature_completeness", {}).get("success_rate", 0.0)
        asset_score = assessment.get("asset_quality", {}).get("quality_score", 0.0)
        code_score = assessment.get("code_translation_quality", {}).get("quality_score", 0.0)
        assumption_penalty = assessment.get("smart_assumption_impact", {}).get("impact_score", 0.0)
        
        # Weighted average with assumption penalty
        weights = {"features": 0.4, "assets": 0.3, "code": 0.3}
        weighted_score = (feature_score * weights["features"] + 
                         asset_score * weights["assets"] + 
                         code_score * weights["code"])
        
        # Apply assumption penalty
        final_score = max(0.0, weighted_score - assumption_penalty)
        
        return round(final_score, 2)
    
    def _generate_recommendations(self, assessment: Dict):
        """Generate recommendations based on quality assessment"""
        recommendations = []
        
        # Feature completeness recommendations
        feature_completeness = assessment.get("feature_completeness", {})
        if feature_completeness.get("success_rate", 0.0) < 0.7:
            recommendations.append("Consider reviewing failed feature conversions for potential improvements")
        
        # Asset quality recommendations
        asset_quality = assessment.get("asset_quality", {})
        if asset_quality.get("format_issues", 0) > 0:
            recommendations.append("Fix asset format issues to ensure Bedrock compatibility")
        
        # Code translation recommendations
        code_quality = assessment.get("code_translation_quality", {})
        if code_quality.get("untranslatable_sections", 0) > 0:
            recommendations.append("Review untranslatable code sections for manual conversion opportunities")
        
        # Smart assumption recommendations
        assumption_impact = assessment.get("smart_assumption_impact", {})
        if assumption_impact.get("high_impact_assumptions", 0) > 0:
            recommendations.append("High-impact assumptions were applied - verify converted functionality meets expectations")
        
        assessment["recommendations"] = recommendations


class ConversionReportGenerator(BaseTool):
    """Tool for generating comprehensive conversion reports"""
    
    name: str = "Conversion Report Generator"
    description: str = "Generates detailed reports on conversion results"
    
    def _run(self, conversion_data: str, quality_assessment: str) -> str:
        """
        Generate comprehensive conversion report
        
        Args:
            conversion_data: JSON string with conversion results
            quality_assessment: JSON string with quality assessment
            
        Returns:
            JSON string with comprehensive report
        """
        try:
            data = json.loads(conversion_data)
            quality = json.loads(quality_assessment)
            
            report = {
                "report_metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "report_version": "1.0",
                    "generator": "ModPorter AI QA Validator"
                },
                "conversion_summary": {},
                "quality_assessment": quality,
                "detailed_results": {},
                "smart_assumptions_report": {},
                "recommendations": [],
                "next_steps": []
            }
            
            # Generate conversion summary
            self._generate_conversion_summary(data, report)
            
            # Generate detailed results
            self._generate_detailed_results(data, report)
            
            # Generate smart assumptions report
            self._generate_smart_assumptions_report(data, report)
            
            # Generate recommendations and next steps
            self._generate_recommendations_and_next_steps(data, quality, report)
            
            return json.dumps(report, indent=2)
            
        except Exception as e:
            logger.error(f"Error generating conversion report: {e}")
            return json.dumps({"error": f"Failed to generate conversion report: {str(e)}"})
    
    def _generate_conversion_summary(self, data: Dict, report: Dict):
        """Generate high-level conversion summary"""
        mod_info = data.get("mod_info", {})
        
        summary = {
            "original_mod": {
                "name": mod_info.get("name", "Unknown"),
                "version": mod_info.get("version", "Unknown"),
                "framework": mod_info.get("framework", "Unknown"),
                "minecraft_version": mod_info.get("minecraft_version", "Unknown")
            },
            "conversion_statistics": {
                "total_features": 0,
                "converted_features": 0,
                "total_assets": 0,
                "converted_assets": 0,
                "smart_assumptions_applied": 0
            },
            "conversion_status": "Unknown",
            "estimated_functionality": "Unknown"
        }
        
        # Calculate statistics
        features = data.get("analysis", {}).get("features", {})
        for feature_list in features.values():
            if isinstance(feature_list, list):
                summary["conversion_statistics"]["total_features"] += len(feature_list)
        
        assets = data.get("analysis", {}).get("assets", {})
        for asset_list in assets.values():
            if isinstance(asset_list, list):
                summary["conversion_statistics"]["total_assets"] += len(asset_list)
        
        smart_assumptions = data.get("smart_assumptions_applied", [])
        summary["conversion_statistics"]["smart_assumptions_applied"] = len(smart_assumptions)
        
        # Determine conversion status
        overall_score = report.get("quality_assessment", {}).get("overall_score", 0.0)
        if overall_score >= 0.8:
            summary["conversion_status"] = "Excellent"
            summary["estimated_functionality"] = "High (80-100%)"
        elif overall_score >= 0.6:
            summary["conversion_status"] = "Good"
            summary["estimated_functionality"] = "Moderate (60-79%)"
        elif overall_score >= 0.4:
            summary["conversion_status"] = "Fair"
            summary["estimated_functionality"] = "Limited (40-59%)"
        else:
            summary["conversion_status"] = "Poor"
            summary["estimated_functionality"] = "Low (0-39%)"
        
        report["conversion_summary"] = summary
    
    def _generate_detailed_results(self, data: Dict, report: Dict):
        """Generate detailed conversion results"""
        detailed_results = {
            "feature_conversions": {},
            "asset_conversions": {},
            "code_translations": {},
            "package_structure": {}
        }
        
        # Feature conversion details
        feature_conversions = data.get("feature_conversions", {})
        for feature_type, features in feature_conversions.items():
            if isinstance(features, list):
                detailed_results["feature_conversions"][feature_type] = {
                    "count": len(features),
                    "successful": len([f for f in features if f.get("status") == "success"]),
                    "failed": len([f for f in features if f.get("status") == "failed"]),
                    "details": features
                }
        
        # Asset conversion details
        asset_conversions = data.get("asset_conversions", {})
        for asset_type, assets in asset_conversions.items():
            if isinstance(assets, list):
                detailed_results["asset_conversions"][asset_type] = {
                    "count": len(assets),
                    "successful": len([a for a in assets if a.get("success")]),
                    "failed": len([a for a in assets if not a.get("success")]),
                    "details": assets
                }
        
        # Code translation details
        code_translations = data.get("code_translations", {})
        detailed_results["code_translations"] = code_translations
        
        # Package structure details
        package_data = data.get("package_data", {})
        detailed_results["package_structure"] = package_data
        
        report["detailed_results"] = detailed_results
    
    def _generate_smart_assumptions_report(self, data: Dict, report: Dict):
        """Generate smart assumptions report"""
        smart_assumptions = data.get("smart_assumptions_applied", [])
        
        assumptions_report = {
            "total_assumptions": len(smart_assumptions),
            "assumptions_by_category": {},
            "assumptions_by_impact": {"high": 0, "medium": 0, "low": 0},
            "detailed_assumptions": []
        }
        
        for assumption in smart_assumptions:
            if isinstance(assumption, dict):
                # Categorize by type
                feature_type = assumption.get("feature_type", "unknown")
                if feature_type not in assumptions_report["assumptions_by_category"]:
                    assumptions_report["assumptions_by_category"][feature_type] = 0
                assumptions_report["assumptions_by_category"][feature_type] += 1
                
                # Categorize by impact
                impact = assumption.get("assumption", {}).get("impact", "medium")
                if impact in assumptions_report["assumptions_by_impact"]:
                    assumptions_report["assumptions_by_impact"][impact] += 1
                
                # Add detailed assumption
                assumptions_report["detailed_assumptions"].append({
                    "feature_type": feature_type,
                    "original_feature": assumption.get("assumption", {}).get("java_feature", "Unknown"),
                    "bedrock_equivalent": assumption.get("assumption", {}).get("bedrock_workaround", "Unknown"),
                    "impact": impact,
                    "affected_features": assumption.get("affected_features", []),
                    "user_explanation": assumption.get("assumption", {}).get("description", "")
                })
        
        report["smart_assumptions_report"] = assumptions_report
    
    def _generate_recommendations_and_next_steps(self, data: Dict, quality: Dict, report: Dict):
        """Generate recommendations and next steps"""
        recommendations = quality.get("recommendations", [])
        
        # Add specific recommendations based on data
        if data.get("smart_assumptions_applied"):
            recommendations.append("Test converted features thoroughly to ensure they work as expected")
        
        if data.get("package_data", {}).get("errors"):
            recommendations.append("Review and fix package assembly errors before distribution")
        
        next_steps = [
            "Review the conversion report and quality assessment",
            "Test the converted add-on in a Minecraft Bedrock world",
            "Verify that smart assumptions produce acceptable results",
            "Make any necessary manual adjustments to the converted code",
            "Package the final add-on for distribution"
        ]
        
        report["recommendations"] = recommendations
        report["next_steps"] = next_steps


class QAValidatorAgent:
    """Agent for quality assurance and validation of conversions"""
    
    def __init__(self):
        self.quality_checker = ConversionQualityChecker()
        self.report_generator = ConversionReportGenerator()
        logger.info("QAValidatorAgent initialized")
    
    @tool("Conversion Quality Assessment Tool")
    def assess_conversion_quality(self, conversion_data: str) -> str:
        """
        Assess the overall quality of the mod conversion.
        
        Args:
            conversion_data: JSON string with complete conversion results
            
        Returns:
            JSON string with quality assessment
        """
        return self.quality_checker._run(conversion_data)
    
    @tool("Conversion Report Generator")
    def generate_conversion_report(self, conversion_data: str, quality_assessment: str) -> str:
        """
        Generate comprehensive conversion report.
        
        Args:
            conversion_data: JSON string with conversion results
            quality_assessment: JSON string with quality assessment
            
        Returns:
            JSON string with comprehensive report
        """
        return self.report_generator._run(conversion_data, quality_assessment)
    
    @tool("Feature Validation Tool")
    def validate_converted_features(self, feature_data: str) -> str:
        """
        Validate individual converted features for correctness.
        
        Args:
            feature_data: JSON string with converted feature data
            
        Returns:
            JSON string with validation results
        """
        try:
            features = json.loads(feature_data)
            
            validation_results = {
                "total_features": 0,
                "valid_features": 0,
                "invalid_features": 0,
                "validation_details": [],
                "critical_issues": [],
                "warnings": []
            }
            
            for feature_type, feature_list in features.items():
                if isinstance(feature_list, list):
                    validation_results["total_features"] += len(feature_list)
                    
                    for feature in feature_list:
                        if isinstance(feature, dict):
                            is_valid = self._validate_single_feature(feature, feature_type)
                            
                            if is_valid:
                                validation_results["valid_features"] += 1
                            else:
                                validation_results["invalid_features"] += 1
                            
                            validation_results["validation_details"].append({
                                "feature_type": feature_type,
                                "feature_name": feature.get("name", "Unknown"),
                                "valid": is_valid,
                                "issues": feature.get("validation_issues", [])
                            })
            
            return json.dumps(validation_results, indent=2)
            
        except Exception as e:
            logger.error(f"Error validating features: {e}")
            return json.dumps({"error": f"Failed to validate features: {str(e)}"})
    
    def _validate_single_feature(self, feature: Dict, feature_type: str) -> bool:
        """Validate a single converted feature"""
        # Basic validation checks
        required_fields = ["name", "status"]
        
        for field in required_fields:
            if field not in feature:
                if "validation_issues" not in feature:
                    feature["validation_issues"] = []
                feature["validation_issues"].append(f"Missing required field: {field}")
                return False
        
        # Type-specific validation
        if feature_type == "blocks":
            return self._validate_block_feature(feature)
        elif feature_type == "items":
            return self._validate_item_feature(feature)
        elif feature_type == "entities":
            return self._validate_entity_feature(feature)
        
        return True
    
    def _validate_block_feature(self, feature: Dict) -> bool:
        """Validate a converted block feature"""
        # Check for required block properties
        required_properties = ["material", "hardness"]
        
        for prop in required_properties:
            if prop not in feature.get("properties", {}):
                if "validation_issues" not in feature:
                    feature["validation_issues"] = []
                feature["validation_issues"].append(f"Missing block property: {prop}")
                return False
        
        return True
    
    def _validate_item_feature(self, feature: Dict) -> bool:
        """Validate a converted item feature"""
        # Check for required item properties
        required_properties = ["max_stack_size", "durability"]
        
        properties = feature.get("properties", {})
        if not properties:
            if "validation_issues" not in feature:
                feature["validation_issues"] = []
            feature["validation_issues"].append("No item properties defined")
            return False
        
        return True
    
    def _validate_entity_feature(self, feature: Dict) -> bool:
        """Validate a converted entity feature"""
        # Check for required entity components
        required_components = ["health", "movement"]
        
        components = feature.get("components", {})
        if not components:
            if "validation_issues" not in feature:
                feature["validation_issues"] = []
            feature["validation_issues"].append("No entity components defined")
            return False
        
        return True
    
    def get_tools(self) -> List:
        """Return available tools for this agent"""
        return [
            self.assess_conversion_quality,
            self.generate_conversion_report,
            self.validate_converted_features
        ]