import os
import json
import re
from typing import Dict, List, Set, Tuple
from ..models.comparison import ComparisonResult, FeatureMapping

class ComparisonEngine:
    def __init__(self):
        print("ComparisonEngine initialized")

    def _list_files_recursively(self, directory_path: str) -> set:
        mock_files = {
            "path/to/java/mod": {"file1.java", "subdir/file2.java", "common.txt"},
            "path/to/bedrock/addon": {"bp/file1.json", "rp/texture.png", "common.txt", "bp/subdir/file2.js"},
            "java_mod_example_for_engine": {"main.java", "utils/helper.java", "data/config.json", "shared_scripts/script.py"},
            "bedrock_addon_example_for_engine": {"scripts/main.js", "utils/helper.js", "data/config.json", "textures/icon.png", "shared_scripts/script.py"}
        }
        normalized_path = str(directory_path).replace('\\', '/')

        if normalized_path not in mock_files:
            if "java" in normalized_path:
                return {f"generic_java_file_{normalized_path.split('/')[-1]}.java", f"common_java_resource_{normalized_path.split('/')[-1]}.txt"}
            elif "bedrock" in normalized_path or "addon" in normalized_path:
                return {f"generic_bedrock_script_{normalized_path.split('/')[-1]}.js", f"common_bedrock_resource_{normalized_path.split('/')[-1]}.txt"}
            return {f"unknown_path_file_for_{normalized_path.replace('/', '_')}.txt"}

        return mock_files.get(normalized_path, set())

    def _compare_structures(self, java_mod_path: str, bedrock_addon_path: str) -> dict:
        java_files = self._list_files_recursively(java_mod_path)
        bedrock_files = self._list_files_recursively(bedrock_addon_path)

        added_files = list(bedrock_files - java_files)
        removed_files = list(java_files - bedrock_files)
        modified_files = list(java_files.intersection(bedrock_files)) # Naive: common files are "modified"

        return {
            "files_added": sorted(added_files),
            "files_removed": sorted(removed_files),
            "files_modified": sorted(modified_files)
        }

    def _analyze_code_complexity(self, java_files: Set[str], bedrock_files: Set[str]) -> Dict[str, float]:
        """Analyze code complexity and conversion accuracy."""
        java_complexity = len([f for f in java_files if f.endswith('.java')]) * 0.8
        js_complexity = len([f for f in bedrock_files if f.endswith('.js')]) * 0.6
        
        # Logic preservation estimate based on file conversion ratio
        preservation_ratio = min(js_complexity / max(java_complexity, 1), 1.0)
        
        return {
            "logic_preserved": round(preservation_ratio, 2),
            "complexity_reduction": round(max(0, (java_complexity - js_complexity) / max(java_complexity, 1)), 2),
            "conversion_confidence": round(preservation_ratio * 0.9, 2)
        }
    
    def _analyze_assets(self, java_files: Set[str], bedrock_files: Set[str]) -> Dict[str, any]:
        """Analyze asset conversion and compatibility."""
        java_assets = [f for f in java_files if any(f.endswith(ext) for ext in ['.png', '.jpg', '.ogg', '.wav'])]
        bedrock_assets = [f for f in bedrock_files if any(f.endswith(ext) for ext in ['.png', '.jpg', '.ogg', '.wav'])]
        
        return {
            "original_assets": len(java_assets),
            "converted_assets": len(bedrock_assets),
            "conversion_rate": round(len(bedrock_assets) / max(len(java_assets), 1), 2),
            "supported_formats": ["PNG", "OGG"] if bedrock_assets else [],
            "unsupported_formats": ["WAV"] if any('.wav' in f for f in java_assets) else []
        }
    
    def _identify_smart_assumptions(self, java_files: Set[str], bedrock_files: Set[str]) -> List[Dict[str, str]]:
        """Identify smart assumptions applied during conversion."""
        assumptions = []
        
        # GUI to Sign Interface assumption
        if any('gui' in f.lower() or 'interface' in f.lower() for f in java_files):
            assumptions.append({
                "id": "GUI_TO_SIGN_INTERFACE",
                "description": "Complex Java GUIs converted to sign-based interfaces in Bedrock",
                "impact": "Medium - User interaction patterns changed",
                "confidence": "0.75"
            })
        
        # Custom Dimension assumption
        if any('dimension' in f.lower() or 'world' in f.lower() for f in java_files):
            assumptions.append({
                "id": "CUSTOM_DIMENSION_TO_STRUCTURE",
                "description": "Custom dimensions converted to large structures in existing dimensions",
                "impact": "High - Fundamental gameplay changes",
                "confidence": "0.65"
            })
        
        # Complex Machinery assumption
        if any('machine' in f.lower() or 'automation' in f.lower() for f in java_files):
            assumptions.append({
                "id": "MACHINERY_SIMPLIFICATION",
                "description": "Complex machinery simplified to preserve visual aesthetics",
                "impact": "Medium - Functionality reduced but appearance maintained",
                "confidence": "0.80"
            })
        
        return assumptions
    
    def _perform_feature_mapping(self, java_mod_path: str, bedrock_addon_path: str, structural_diff: dict) -> list:
        """Enhanced feature mapping with realistic patterns."""
        mappings = []
        java_files = set(structural_diff.get("files_removed", []))
        bedrock_files = set(structural_diff.get("files_added", []))
        
        # Java to JSON block mapping
        java_blocks = [f for f in java_files if 'block' in f.lower() and f.endswith('.java')]
        bedrock_blocks = [f for f in bedrock_files if 'block' in f.lower() and f.endswith('.json')]
        
        for java_block in java_blocks[:3]:  # Limit to avoid too many mappings
            if bedrock_blocks:
                bedrock_equivalent = bedrock_blocks[0]  # Simple 1:1 mapping for demo
                mappings.append(FeatureMapping(
                    java_feature=f"Block definition: {java_block}",
                    bedrock_equivalent=f"Block JSON: {bedrock_equivalent}",
                    mapping_type="STRUCTURAL_CONVERSION",
                    confidence_score=0.85,
                    assumption_applied="JAVA_CLASS_TO_JSON_DEFINITION"
                ))
                bedrock_blocks.pop(0)
        
        # Main logic conversion
        java_main = [f for f in java_files if 'main' in f.lower() and f.endswith('.java')]
        js_main = [f for f in bedrock_files if 'main' in f.lower() and f.endswith('.js')]
        
        if java_main and js_main:
            mappings.append(FeatureMapping(
                java_feature=f"Core logic: {java_main[0]}",
                bedrock_equivalent=f"Converted logic: {js_main[0]}",
                mapping_type="LOGIC_TRANSLATION",
                confidence_score=0.72,
                assumption_applied="JAVA_OOP_TO_JS_FUNCTIONAL"
            ))
        
        # GUI conversion
        java_gui = [f for f in java_files if any(term in f.lower() for term in ['gui', 'interface', 'screen'])]
        if java_gui:
            mappings.append(FeatureMapping(
                java_feature=f"GUI System: {java_gui[0]}",
                bedrock_equivalent="Sign-based interface system",
                mapping_type="SMART_ASSUMPTION",
                confidence_score=0.60,
                assumption_applied="GUI_TO_SIGN_INTERFACE"
            ))
        
        # Default mapping if none found
        if not mappings:
            mappings.append(FeatureMapping(
                java_feature="Generic mod functionality",
                bedrock_equivalent="Basic Bedrock add-on features",
                mapping_type="GENERIC_CONVERSION",
                confidence_score=0.45,
                assumption_applied="BEST_EFFORT_CONVERSION"
            ))
        
        return mappings

    def compare(self, java_mod_path: str, bedrock_addon_path: str, conversion_id: str) -> ComparisonResult:
        """Enhanced comparison with realistic analysis."""
        print(f"Comparing Java mod at '{java_mod_path}' with Bedrock add-on at '{bedrock_addon_path}' for conversion '{conversion_id}'")

        # Structural analysis
        structural_differences = self._compare_structures(java_mod_path, bedrock_addon_path)
        java_files = self._list_files_recursively(java_mod_path)
        bedrock_files = self._list_files_recursively(bedrock_addon_path)
        
        # Enhanced analysis
        code_analysis = self._analyze_code_complexity(java_files, bedrock_files)
        asset_analysis = self._analyze_assets(java_files, bedrock_files)
        smart_assumptions = self._identify_smart_assumptions(java_files, bedrock_files)
        feature_mappings_list = self._perform_feature_mapping(java_mod_path, bedrock_addon_path, structural_differences)
        
        # Calculate overall confidence based on various factors
        structural_confidence = min(0.9, len(structural_differences.get("files_modified", [])) / max(len(java_files), 1))
        mapping_confidence = sum(fm.confidence_score for fm in feature_mappings_list) / max(len(feature_mappings_list), 1)
        overall_confidence_score = (structural_confidence + mapping_confidence + code_analysis["conversion_confidence"]) / 3
        
        confidence_scores = {
            "overall": round(overall_confidence_score, 2),
            "structural_analysis": round(structural_confidence, 2),
            "feature_mapping": round(mapping_confidence, 2),
            "code_conversion": code_analysis["conversion_confidence"],
            "asset_conversion": asset_analysis["conversion_rate"]
        }

        result = ComparisonResult(
            conversion_id=conversion_id,
            structural_diff=structural_differences,
            code_diff=code_analysis,
            asset_diff=asset_analysis,
            feature_mappings=feature_mappings_list,
            assumptions_applied=smart_assumptions,
            confidence_scores=confidence_scores
        )
        return result

if __name__ == '__main__':
    from dataclasses import is_dataclass, asdict
    import json

    def dataclass_to_dict_for_print(obj):
        # Helper to convert dataclasses and other objects to dict for JSON printing
        if is_dataclass(obj) and not isinstance(obj, type):
            return asdict(obj)
        if isinstance(obj, list):
            return [dataclass_to_dict_for_print(e) for e in obj]
        if isinstance(obj, dict):
            return {k: dataclass_to_dict_for_print(v) for k, v in obj.items()}
        if hasattr(obj, 'isoformat'): # Handle datetime objects if they appear
            return obj.isoformat()
        if isinstance(obj, (str, int, float, bool)) or obj is None:
            return obj
        # Fallback for other types, could be expanded
        try:
            return str(obj) # Convert other types to string if not directly serializable
        except Exception:
            return "UnserializableObject"


    engine = ComparisonEngine()
    java_path_example = "java_mod_example_for_engine"
    bedrock_path_example = "bedrock_addon_example_for_engine"
    conv_id_example = "conv_test_002"

    report = engine.compare(java_path_example, bedrock_path_example, conv_id_example)

    report_dict = dataclass_to_dict_for_print(report)
    print("--- Comparison Report (JSON Output) ---")
    print(json.dumps(report_dict, indent=2))
    print("--- End of Comparison Report ---")
