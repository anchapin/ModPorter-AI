import os
import json

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

    def _perform_feature_mapping(self, java_mod_path: str, bedrock_addon_path: str, structural_diff: dict) -> list:
        mock_mappings = []

        if "file1.java" in structural_diff.get("files_removed", []) and            "bp/file1.json" in structural_diff.get("files_added", []):
            mock_mappings.append(
                FeatureMapping(
                    java_feature="Custom Block from file1.java",
                    bedrock_equivalent="Custom Block in bp/file1.json",
                    mapping_type="ASSUMED_STRUCTURAL",
                    confidence_score=0.70,
                    assumption_applied="JAVA_TO_JSON_BLOCK_CONVERSION"
                )
            )

        if "main.java" in structural_diff.get("files_removed", []) and             "scripts/main.js" in structural_diff.get("files_added", []):
            mock_mappings.append(
                FeatureMapping(
                    java_feature="Main logic from main.java",
                    bedrock_equivalent="Main logic in scripts/main.js",
                    mapping_type="ASSUMED_CODE_TRANSLATION",
                    confidence_score=0.65,
                    assumption_applied="JAVA_TO_JS_MAIN_LOGIC"
                )
            )

        if not mock_mappings:
            mock_mappings.append(
                FeatureMapping(
                    java_feature="Default Java Feature",
                    bedrock_equivalent="Default Bedrock Equivalent",
                    mapping_type="PLACEHOLDER_DEFAULT",
                    confidence_score=0.4,
                    assumption_applied="NO_SPECIFIC_STRUCTURAL_MATCH"
                )
            )
        return mock_mappings

    def compare(self, java_mod_path: str, bedrock_addon_path: str, conversion_id: str) -> ComparisonResult:
        print(f"Comparing Java mod at '{java_mod_path}' with Bedrock add-on at '{bedrock_addon_path}' for conversion '{conversion_id}'")

        structural_differences = self._compare_structures(java_mod_path, bedrock_addon_path)
        feature_mappings_list = self._perform_feature_mapping(java_mod_path, bedrock_addon_path, structural_differences)

        code_diff_summary = {"summary": "Code comparison not yet implemented."}
        asset_diff_summary = {"summary": "Asset comparison not yet implemented."}
        applied_assumptions_summary = [{"id": "GLOBAL_MOCK_ASSUMPTION", "description": "Initial placeholder global assumption."}]
        overall_confidence = {"structural_analysis": 0.65, "feature_mapping_initial": 0.55}

        result = ComparisonResult(
            conversion_id=conversion_id,
            structural_diff=structural_differences,
            code_diff=code_diff_summary,
            asset_diff=asset_diff_summary,
            feature_mappings=feature_mappings_list,
            assumptions_applied=applied_assumptions_summary,
            confidence_scores=overall_confidence
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
