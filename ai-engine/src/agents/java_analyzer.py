import logging
import zipfile
from pathlib import Path
import json
import shutil # For cleaning up temp directory

logger = logging.getLogger(__name__)

# Common asset extensions and paths
ASSET_CONFIG = {
    "textures": {"extensions": [".png", ".jpg", ".jpeg", ".tga", ".bmp"], "paths": ["assets/**/textures"]},
    "models": {"extensions": [".json", ".obj", ".gltf", ".fbx"], "paths": ["assets/**/models"]},
    "sounds": {"extensions": [".ogg", ".wav", ".mp3"], "paths": ["assets/**/sounds", "assets/**/sound"]},
    "lang": {"extensions": [".json", ".lang"], "paths": ["assets/**/lang"]},
    "data": {"extensions": [".json"], "paths": ["data/**/recipes", "data/**/loot_tables", "data/**/advancements", "data/**/tags"]},
    "shaders": {"extensions": [".fsh", ".vsh", ".glsl"], "paths": ["assets/**/shaders"]},
    "blockstates": {"extensions": [".json"], "paths": ["assets/**/blockstates"]},
    "font": {"extensions": [".ttf", ".otf", ".png"], "paths": ["assets/**/font"]}
}

class ExtractModFileToolInternal: # Renamed to avoid conflict if used elsewhere
    name: str = "Internal Extract Mod File Tool"
    description: str = "Extracts the contents of a .jar or .zip mod file to a temporary directory and returns the path to this directory."

    def _run(self, mod_file_path: str, temp_base_path: Path = Path("temp_extraction")) -> str:
        try:
            mod_path = Path(mod_file_path)
            if not mod_path.exists() or not mod_path.is_file():
                return json.dumps({"error": f"Mod file not found or is not a file: {mod_file_path}"})
            if not (mod_file_path.endswith('.jar') or mod_file_path.endswith('.zip')):
                return json.dumps({"error": f"File is not a .jar or .zip file: {mod_file_path}"})

            extraction_dir = temp_base_path / mod_path.name.replace('.jar', '').replace('.zip', '')

            if extraction_dir.exists():
                shutil.rmtree(extraction_dir)
            extraction_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(mod_file_path, 'r') as zip_ref:
                zip_ref.extractall(extraction_dir)
            logger.info(f"Successfully extracted {mod_file_path} to {extraction_dir}")
            return json.dumps({"extraction_path": str(extraction_dir)})
        except zipfile.BadZipFile:
            logger.error(f"Error: Bad zip file {mod_file_path}")
            return json.dumps({"error": f"Bad zip file {mod_file_path}."})
        except Exception as e:
            logger.error(f"Error extracting mod file {mod_file_path}: {e}")
            return json.dumps({"error": f"Error extracting mod file {mod_file_path}: {str(e)}"})

class IdentifyModFrameworkToolInternal: # Renamed
    name: str = "Internal Identify Mod Framework Tool"
    description: str = "Identifies the mod framework."

    def _run(self, extracted_mod_path: str) -> str:
        try:
            base_path = Path(extracted_mod_path)
            if not base_path.exists() or not base_path.is_dir():
                return json.dumps({"error": f"Extraction path not found: {extracted_mod_path}"})

            fabric_manifest_path = base_path / "fabric.mod.json"
            if fabric_manifest_path.exists():
                try:
                    with open(fabric_manifest_path, 'r') as f:
                        data = json.load(f)
                    return json.dumps({"framework": "fabric", "id": data.get("id"), "version": data.get("version"), "minecraft_version": data.get("depends", {}).get("minecraft"), "dependencies": data.get("depends")})
                except Exception as e:
                    return json.dumps({"framework": "fabric", "error": f"Error parsing fabric.mod.json: {str(e)}"})

            quilt_manifest_path = base_path / "quilt.mod.json"
            if quilt_manifest_path.exists():
                try:
                    with open(quilt_manifest_path, 'r') as f:
                        data = json.load(f)
                    return json.dumps({"framework": "quilt", "id": data.get("quilt_loader", {}).get("id"), "version": data.get("quilt_loader", {}).get("version"), "minecraft_version": data.get("quilt_loader",{}).get("depends", {}).get("minecraft")})
                except Exception as e:
                    return json.dumps({"framework": "quilt", "error": f"Error parsing quilt.mod.json: {str(e)}"})

            forge_manifest_path_toml = base_path / "META-INF" / "mods.toml"
            if forge_manifest_path_toml.exists():
                return json.dumps({"framework": "forge", "manifest_type": "mods.toml", "id": "unknown_toml", "version": "unknown_toml", "minecraft_version": "unknown_toml"})

            forge_manifest_path_mcmod = base_path / "mcmod.info"
            if forge_manifest_path_mcmod.exists():
                try:
                    with open(forge_manifest_path_mcmod, 'r') as f:
                        content = f.read()
                    data = json.loads(content)
                    mod_info = data[0] if isinstance(data, list) and data else data
                    return json.dumps({"framework": "forge", "manifest_type": "mcmod.info", "id": mod_info.get("modid"), "version": mod_info.get("version"), "minecraft_version": mod_info.get("mcversion")})
                except Exception as e:
                    return json.dumps({"framework": "forge", "manifest_type": "mcmod.info", "error": f"Error parsing mcmod.info: {str(e)}"})
            return json.dumps({"framework": "unknown", "message": "No known manifest file found."})
        except Exception as e:
            return json.dumps({"error": f"Error identifying mod framework: {str(e)}"})

class CatalogAssetsToolInternal: # Renamed
    name: str = "Internal Catalog Mod Assets Tool"
    description: str = "Catalogs assets."
    def _run(self, extracted_mod_path: str) -> str:
        try:
            base_path = Path(extracted_mod_path)
            if not base_path.exists() or not base_path.is_dir():
                return json.dumps({"error": f"Extraction path not found: {extracted_mod_path}"})
            found_assets = {category: [] for category in ASSET_CONFIG.keys()}
            found_assets["other"] = []
            for file_path in base_path.rglob("*"):
                if file_path.is_file():
                    relative_path_str = str(file_path.relative_to(base_path)).replace("\\", "/")
                    categorized = False
                    for category, config in ASSET_CONFIG.items():
                        if file_path.suffix.lower() in config["extensions"]:
                            if any(Path(relative_path_str).match(pattern) for pattern in config["paths"]):
                                found_assets[category].append(relative_path_str)
                                categorized = True
                                break
                    if not categorized:
                        if "assets/" in relative_path_str.lower() and file_path.suffix.lower() in ASSET_CONFIG["textures"]["extensions"] and "/textures/" in relative_path_str.lower():
                            found_assets["textures"].append(relative_path_str)
                            categorized = True
                        elif not categorized:
                            found_assets["other"].append(relative_path_str)
            final_catalog = {k: v for k,v in found_assets.items() if v}
            return json.dumps(final_catalog)
        except Exception as e:
            return json.dumps({"error": f"Error cataloging assets: {str(e)}"})

class ParseJavaCodeToolInternal: # Renamed
    name: str = "Internal Parse Java Code Tool"
    description: str = "Identifies Java source files."
    def _run(self, extracted_mod_path: str) -> str:
        try:
            base_path = Path(extracted_mod_path)
            if not base_path.exists() or not base_path.is_dir():
                return json.dumps({"error": f"Extraction path not found: {extracted_mod_path}"})
            java_files = [str(fp.relative_to(base_path)).replace("\\", "/") for fp in base_path.rglob("*.java") if fp.is_file()]
            identified_features = {"blocks": [], "items": [], "entities": [], "dimensions": [], "guis": [], "recipes_in_code": [], "dependencies_in_code": []}
            return json.dumps({"java_files_found": java_files, "identified_features_placeholder": identified_features, "analysis_status": "Initial scan for .java files completed."})
        except Exception as e:
            return json.dumps({"error": f"Error during initial Java code scan: {str(e)}"})


class JavaAnalyzerAgent:
    def __init__(self, temp_base_path_str: str = "temp_extraction_agent"):
        logger.info(f"JavaAnalyzerAgent initialized with temp base: {temp_base_path_str}")
        self.temp_base_path = Path(temp_base_path_str)
        self.temp_base_path.mkdir(parents=True, exist_ok=True)

        self._extraction_tool_internal = ExtractModFileToolInternal()
        self._framework_identification_tool_internal = IdentifyModFrameworkToolInternal()
        self._asset_catalog_tool_internal = CatalogAssetsToolInternal()
        self._java_parser_tool_internal = ParseJavaCodeToolInternal()

    def analyze_mod_file(self, mod_file_path: str) -> str:
        """
        Analyzes a Java mod file (.jar or .zip) and returns a comprehensive JSON report.
        Orchestrates extraction, framework identification, asset cataloging, and Java file scanning.
        Manages cleanup of temporary files.
        """
        final_report = {
            "mod_info": {"name": "Unknown", "version": "Unknown", "framework": "unknown", "minecraft_version": "Unknown"},
            "assets": {}, "features": {"blocks": [], "items": [], "entities": [], "dimensions": [], "guis": []},
            "dependencies": [], "complexity_score": 0.0, "raw_analysis_data": {}, "errors": []
        }
        mod_path_obj = Path(mod_file_path)
        final_report["mod_info"]["name"] = mod_path_obj.name.replace('.jar','').replace('.zip','')
        extracted_path_str = None # Initialize to ensure it's defined for finally block

        extraction_result_str = self._extraction_tool_internal._run(mod_file_path, temp_base_path=self.temp_base_path)
        extraction_result = json.loads(extraction_result_str)

        if "error" in extraction_result:
            final_report["errors"].append(f"Extraction failed: {extraction_result['error']}")
            if "extraction_path" in extraction_result and extraction_result["extraction_path"]: # if path was somehow returned
                 extracted_path_str = extraction_result["extraction_path"] # so finally can try to clean it
            # No early return here if we want `finally` to always run for cleanup attempt
        else:
            extracted_path_str = extraction_result["extraction_path"]
            final_report["raw_analysis_data"]["extraction_path"] = extracted_path_str

        if extracted_path_str: # Proceed only if extraction path is available
            try:
                framework_result_str = self._framework_identification_tool_internal._run(extracted_path_str)
                framework_result = json.loads(framework_result_str)
                final_report["raw_analysis_data"]["framework_identification"] = framework_result
                if "error" not in framework_result:
                    final_report["mod_info"]["framework"] = framework_result.get("framework", "unknown")
                    final_report["mod_info"]["version"] = framework_result.get("version", final_report["mod_info"]["version"])
                    final_report["mod_info"]["name"] = framework_result.get("id", final_report["mod_info"]["name"])
                    final_report["mod_info"]["minecraft_version"] = framework_result.get("minecraft_version", "Unknown")
                    if framework_result.get("framework") == "fabric" and isinstance(framework_result.get("dependencies"), dict):
                        final_report["dependencies"] = [f"{k}:{v}" for k,v in framework_result["dependencies"].items()]
                else:
                    final_report["errors"].append(f"Framework ID error: {framework_result['error']}")

                assets_result_str = self._asset_catalog_tool_internal._run(extracted_path_str)
                assets_result = json.loads(assets_result_str)
                final_report["raw_analysis_data"]["asset_catalog"] = assets_result
                if "error" not in assets_result:
                    final_report["assets"] = assets_result
                else:
                    final_report["errors"].append(f"Asset catalog error: {assets_result['error']}")

                java_scan_result_str = self._java_parser_tool_internal._run(extracted_path_str)
                java_scan_result = json.loads(java_scan_result_str)
                final_report["raw_analysis_data"]["java_code_scan"] = java_scan_result
                if "error" not in java_scan_result:
                    final_report["features"].update(java_scan_result.get("identified_features_placeholder", {}))
                else:
                    final_report["errors"].append(f"Java scan error: {java_scan_result['error']}")

                final_report["complexity_score"] = 5.0
            except Exception as e_main_analysis:  # Catch errors during the main analysis phase
                logger.error(f"Error during main analysis of {extracted_path_str}: {e_main_analysis}")
                final_report["errors"].append(f"Main analysis phase error: {str(e_main_analysis)}")
            finally:
                extracted_path_obj = Path(extracted_path_str)
                if extracted_path_obj.exists() and self.temp_base_path.resolve() in extracted_path_obj.resolve().parents:
                    try:
                        shutil.rmtree(extracted_path_obj)
                        logger.info(f"Cleaned up temp directory: {extracted_path_obj}")
                    except Exception as e:
                        logger.error(f"Error cleaning up temp directory {extracted_path_obj}: {e}")
                        final_report["errors"].append(f"Cleanup error: {str(e)}")
                elif extracted_path_obj.exists():
                    logger.warning(f"Skipping cleanup of {extracted_path_obj} as it is not in the designated temp area {self.temp_base_path.resolve()}.")

        return json.dumps(final_report, indent=2)

    def get_tools(self) -> list:
        return [self.analyze_mod_file]


# if __name__ == '__main__':
#    agent_instance = JavaAnalyzerAgent(temp_base_path_str="temp_agent_main_test")
#
#    dummy_mod_name = "MyAwesomeMod"
#    dummy_version = "0.5.0"
#    dummy_mc_version = "1.19.4"
#    dummy_jar_path = Path(f"{dummy_mod_name}.jar")
#
#    if dummy_jar_path.exists(): dummy_jar_path.unlink()
#
#    with zipfile.ZipFile(dummy_jar_path, 'w') as zf:
#        fabric_mod_json = {
#            "schemaVersion": 1, "id": dummy_mod_name.lower(), "version": dummy_version,
#            "name": dummy_mod_name, "environment": "*",
#            "depends": {"minecraft": dummy_mc_version, "fabricloader": ">=0.14.0", "another_mod": ">=1.0.0"}
#        }
#        zf.writestr("fabric.mod.json", json.dumps(fabric_mod_json))
#        zf.writestr(f"assets/{dummy_mod_name.lower()}/textures/block/magic_block.png", "png_data")
#        zf.writestr(f"assets/{dummy_mod_name.lower()}/models/item/magic_sword.json", "{}")
#        zf.writestr(f"data/{dummy_mod_name.lower()}/recipes/magic_recipe.json", "{}")
#        zf.writestr(f"com/example/{dummy_mod_name.lower()}/Main.java", "public class Main {}")
#        zf.writestr(f"com/example/{dummy_mod_name.lower()}/block/MagicBlock.java", "public class MagicBlock {}")
#
#    print(f"Created dummy mod: {dummy_jar_path}")
#    analysis_json_output = agent_instance.analyze_mod_file(str(dummy_jar_path))
#
#    print("\n--- Generated Analysis Report ---")
#    print(analysis_json_output)
#    print("--- End of Report ---")
#
#    report = {}
#    try:
#        report = json.loads(analysis_json_output)
#        assert report["mod_info"]["name"] == dummy_mod_name.lower()
#        assert report["mod_info"]["version"] == dummy_version
#        assert report["mod_info"]["framework"] == "fabric"
#        assert report["mod_info"]["minecraft_version"] == dummy_mc_version
#        assert f"another_mod:>=1.0.0" in report["dependencies"]
#        assert "textures" in report["assets"] and len(report["assets"]["textures"]) == 1
#        assert "java_files_found" in report["raw_analysis_data"]["java_code_scan"] and \
#               len(report["raw_analysis_data"]["java_code_scan"]["java_files_found"]) == 2
#        assert not report["errors"]
#        print("\nReport basic validation PASSED.")
#    except (AssertionError, KeyError, json.JSONDecodeError) as e:
#        print(f"\nReport basic validation FAILED: {e}")
#        if report:
#             print(f"Report content was: {json.dumps(report, indent=2)}")
#
#    if dummy_jar_path.exists(): dummy_jar_path.unlink()
#
#    extraction_dir_name = dummy_jar_path.name.replace('.jar', '').replace('.zip', '')
#    specific_extraction_path = agent_instance.temp_base_path / extraction_dir_name
#
#    if specific_extraction_path.exists():
#        print(f"Warning: Specific extraction path {specific_extraction_path} was NOT cleaned up.")
#    else:
#        print(f"Confirmed: Specific extraction path {specific_extraction_path} was cleaned up as expected.")
#
#    print("\n--- Testing with non-existent file ---")
#    non_existent_jar = "non_existent_mod.jar"
#    error_report_json = agent_instance.analyze_mod_file(non_existent_jar)
#    print(error_report_json)
#    try:
#        error_report = json.loads(error_report_json)
#        assert len(error_report["errors"]) > 0
#        assert "Extraction failed" in error_report["errors"][0]
#        assert non_existent_jar in error_report["errors"][0]
#        print("Non-existent file test PASSED.")
#    except (AssertionError, KeyError, json.JSONDecodeError) as e:
#        print(f"Non-existent file test FAILED: {e}")
#
#    print("\n--- Testing with a bad zip file ---")
#    bad_zip_path = Path("bad_mod.jar")
#    with open(bad_zip_path, "w") as f:
#        f.write("This is not a zip file")
#
#    error_report_json_bad_zip = agent_instance.analyze_mod_file(str(bad_zip_path))
#    print(error_report_json_bad_zip)
#    try:
#        error_report_bad_zip = json.loads(error_report_json_bad_zip)
#        assert len(error_report_bad_zip["errors"]) > 0
#        assert "Extraction failed" in error_report_bad_zip["errors"][0]
#        assert "Bad zip file" in error_report_bad_zip["errors"][0]
#        print("Bad zip file test PASSED.")
#    except (AssertionError, KeyError, json.JSONDecodeError) as e:
#        print(f"Bad zip file test FAILED: {e}")
#    finally:
#        if bad_zip_path.exists(): bad_zip_path.unlink()
#        if agent_instance.temp_base_path.exists():
#             shutil.rmtree(agent_instance.temp_base_path)
#             print(f"Cleaned up agent's base temp directory: {agent_instance.temp_base_path} after all tests.")
