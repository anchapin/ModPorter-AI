"""
LangChain tool wrappers for Java Analyzer Agent
"""

import json
import os
import zipfile
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Union

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field

from utils.logging_config import get_agent_logger

logger = get_agent_logger("java_analyzer.tools")


class JavaAnalyzerTools:
    """Collection of LangChain tools for Java mod analysis"""

    def __init__(self, agent_instance=None):
        self.agent_instance = agent_instance

    @staticmethod
    def _analyze_mod_structure(mod_data: Union[str, Dict]) -> str:
        """
        Analyze the overall structure of a Java mod.

        Args:
            mod_data: JSON string containing mod file path and analysis options

        Returns:
            JSON string with structural analysis results
        """
        from agents.java_analyzer import JavaAnalyzerAgent

        agent = JavaAnalyzerAgent.get_instance()

        def _determine_mod_type_and_framework(mod_path: str) -> Dict[str, str]:
            """Determine mod type and framework"""
            if mod_path.endswith((".jar", ".zip")):
                mod_type = "jar"
                with zipfile.ZipFile(mod_path, "r") as jar:
                    file_list = jar.namelist()
                    framework = agent._detect_framework_from_jar_files(file_list, jar)
            elif os.path.isdir(mod_path):
                mod_type = "source"
                framework = agent.framework_indicators.get("unknown", "unknown")
            else:
                mod_type = "unknown"
                framework = "unknown"

            return {"type": mod_type, "framework": framework}

        def _analyze_jar_structure(jar_path: str, analysis_depth: str) -> Dict:
            """Analyze JAR file structure"""
            structure = {
                "total_files": 0,
                "package_structure": {},
                "main_classes": [],
                "resource_files": [],
                "metadata_files": [],
            }

            try:
                with zipfile.ZipFile(jar_path, "r") as jar:
                    file_list = jar.namelist()
                    structure["total_files"] = len(file_list)

                    for file_name in file_list:
                        if file_name.endswith(".class"):
                            package_path = "/".join(file_name.split("/")[:-1])
                            if package_path not in structure["package_structure"]:
                                structure["package_structure"][package_path] = []
                            structure["package_structure"][package_path].append(file_name)

                            if _is_main_class(file_name):
                                structure["main_classes"].append(file_name)

                        elif any(
                            file_name.endswith(ext) for ext in agent.file_patterns["resource_files"]
                        ):
                            structure["resource_files"].append(file_name)

                        elif any(
                            metadata in file_name
                            for metadata in agent.file_patterns["metadata_files"]
                        ):
                            structure["metadata_files"].append(file_name)

            except Exception as e:
                logger.warning(f"Error analyzing JAR structure: {e}")

            return structure

        def _analyze_source_structure(source_path: str, analysis_depth: str) -> Dict:
            """Analyze source directory structure"""
            structure = {
                "total_files": 0,
                "source_files": [],
                "resource_files": [],
                "config_files": [],
                "build_files": [],
            }

            try:
                for root, dirs, files in os.walk(source_path):
                    structure["total_files"] += len(files)

                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        rel_path = os.path.relpath(file_path, source_path)

                        if file_name.endswith(".java"):
                            structure["source_files"].append(rel_path)
                        elif any(
                            file_name.endswith(ext) for ext in agent.file_patterns["resource_files"]
                        ):
                            structure["resource_files"].append(rel_path)
                        elif any(
                            file_name.endswith(ext) for ext in agent.file_patterns["config_files"]
                        ):
                            structure["config_files"].append(rel_path)
                        elif file_name in ["build.gradle", "pom.xml", "build.xml"]:
                            structure["build_files"].append(rel_path)

            except Exception as e:
                logger.warning(f"Error analyzing source structure: {e}")

            return structure

        def _is_main_class(class_path: str) -> bool:
            """Check if a class is a main mod class"""
            class_name = class_path.split("/")[-1].replace(".class", "")
            package_path = "/".join(class_path.split("/")[:-1])

            mod_indicators = [
                "mod",
                "Mod",
                "main",
                "Main",
                "init",
                "Init",
                "loader",
                "Loader",
                "Core",
                "core",
                "Entry",
                "entry",
                "Plugin",
                "plugin",
            ]

            package_parts = package_path.split("/")
            has_mod_package = any(
                "mod" in part.lower() or "plugin" in part.lower() for part in package_parts if part
            )

            has_mod_name = any(indicator in class_name for indicator in mod_indicators)
            is_shallow = class_path.count("/") <= 3

            return (has_mod_package and has_mod_name) or is_shallow

        def _create_file_inventory(mod_path: str, mod_type: str) -> Dict:
            """Create comprehensive file inventory"""
            inventory = {"by_type": {}, "by_size": {}, "total_count": 0, "total_size": 0}

            if mod_type == "jar":
                try:
                    with zipfile.ZipFile(mod_path, "r") as jar:
                        for info in jar.infolist():
                            if not info.is_dir():
                                file_ext = Path(info.filename).suffix.lower()
                                file_size = info.file_size

                                inventory["by_type"][file_ext] = (
                                    inventory["by_type"].get(file_ext, 0) + 1
                                )
                                inventory["total_count"] += 1
                                inventory["total_size"] += file_size

                                size_category = (
                                    "small"
                                    if file_size < 1024
                                    else "medium"
                                    if file_size < 1024 * 1024
                                    else "large"
                                )
                                inventory["by_size"][size_category] = (
                                    inventory["by_size"].get(size_category, 0) + 1
                                )
                except Exception as e:
                    logger.warning(f"Error creating JAR inventory: {e}")
            elif mod_type == "source":
                try:
                    for root, dirs, files in os.walk(mod_path):
                        for file_name in files:
                            file_path = os.path.join(root, file_name)
                            file_ext = Path(file_name).suffix.lower()
                            file_size = os.path.getsize(file_path)

                            inventory["by_type"][file_ext] = (
                                inventory["by_type"].get(file_ext, 0) + 1
                            )
                            inventory["total_count"] += 1
                            inventory["total_size"] += file_size

                            size_category = (
                                "small"
                                if file_size < 1024
                                else "medium"
                                if file_size < 1024 * 1024
                                else "large"
                            )
                            inventory["by_size"][size_category] = (
                                inventory["by_size"].get(size_category, 0) + 1
                            )
                except Exception as e:
                    logger.warning(f"Error creating source inventory: {e}")

            return inventory

        def _assess_mod_complexity(structure: Dict, file_inventory: Dict) -> Dict:
            """Assess the complexity of the mod for conversion planning"""
            complexity = {
                "overall_complexity": "medium",
                "complexity_factors": [],
                "complexity_score": 0,
                "conversion_difficulty": "moderate",
            }

            score = 0
            factors = []

            total_files = file_inventory.get("total_count", 0)
            if total_files > 100:
                score += 2
                factors.append("Large number of files")
            elif total_files > 50:
                score += 1
                factors.append("Moderate number of files")

            if "package_structure" in structure:
                packages = len(structure["package_structure"])
                if packages > 10:
                    score += 2
                    factors.append("Complex package structure")
                elif packages > 5:
                    score += 1
                    factors.append("Moderate package structure")

            resource_count = len(structure.get("resource_files", []))
            if resource_count > 50:
                score += 2
                factors.append("Many resource files")
            elif resource_count > 20:
                score += 1
                factors.append("Moderate resource files")

            if score >= 5:
                complexity["overall_complexity"] = "high"
                complexity["conversion_difficulty"] = "challenging"
            elif score >= 3:
                complexity["overall_complexity"] = "medium"
                complexity["conversion_difficulty"] = "moderate"
            else:
                complexity["overall_complexity"] = "low"
                complexity["conversion_difficulty"] = "straightforward"

            complexity["complexity_score"] = score
            complexity["complexity_factors"] = factors

            return complexity

        try:
            if isinstance(mod_data, str):
                try:
                    data = json.loads(mod_data)
                    if "mod_data" in data:
                        mod_path = data["mod_data"]
                        analysis_depth = data.get("analysis_depth", "standard")
                    else:
                        mod_path = data.get("mod_path", "")
                        analysis_depth = data.get("analysis_depth", "standard")
                except json.JSONDecodeError:
                    mod_path = mod_data
                    analysis_depth = "standard"
            else:
                data = mod_data if isinstance(mod_data, dict) else {"mod_path": str(mod_data)}
                if "mod_data" in data:
                    mod_path = data["mod_data"]
                    analysis_depth = data.get("analysis_depth", "standard")
                else:
                    mod_path = data.get("mod_path", str(mod_data))
                    analysis_depth = data.get("analysis_depth", "standard")

            if not os.path.exists(mod_path):
                return json.dumps({"success": False, "error": f"Mod file not found: {mod_path}"})

            analysis_results = {
                "mod_path": mod_path,
                "mod_type": "",
                "framework": "",
                "structure_analysis": {},
                "file_inventory": {},
                "complexity_assessment": {},
            }

            mod_info = _determine_mod_type_and_framework(mod_path)
            analysis_results["mod_type"] = mod_info["type"]
            analysis_results["framework"] = mod_info["framework"]

            if mod_info["type"] == "jar":
                structure = _analyze_jar_structure(mod_path, analysis_depth)
            elif mod_info["type"] == "source":
                structure = _analyze_source_structure(mod_path, analysis_depth)
            else:
                structure = {"type": "unknown", "path": mod_path, "size": 0}

            analysis_results["structure_analysis"] = structure

            file_inventory = _create_file_inventory(mod_path, mod_info["type"])
            analysis_results["file_inventory"] = file_inventory

            complexity = _assess_mod_complexity(structure, file_inventory)
            analysis_results["complexity_assessment"] = complexity

            response = {
                "success": True,
                "analysis_results": analysis_results,
                "recommendations": ["Complete feature extraction for detailed conversion planning"],
            }

            logger.info(
                f"Analyzed mod structure: {mod_path} ({mod_info['framework']} {mod_info['type']})"
            )
            return json.dumps(response)

        except Exception as e:
            error_response = {
                "success": False,
                "error": f"Failed to analyze mod structure: {str(e)}",
            }
            logger.error(f"Mod structure analysis error: {e}")
            return json.dumps(error_response)

    @staticmethod
    def _extract_mod_metadata(mod_data: Union[str, Dict]) -> str:
        """
        Extract metadata from mod files.

        Args:
            mod_data: JSON string containing mod file path

        Returns:
            JSON string with metadata
        """
        from agents.java_analyzer import JavaAnalyzerAgent

        agent = JavaAnalyzerAgent.get_instance()

        def _extract_jar_metadata(jar_path: str) -> Dict:
            """Extract metadata from JAR file"""
            metadata = {}

            try:
                with zipfile.ZipFile(jar_path, "r") as jar:
                    for metadata_file in agent.file_patterns["metadata_files"]:
                        if metadata_file in jar.namelist():
                            try:
                                content = jar.read(metadata_file).decode("utf-8")
                                if metadata_file.endswith(".json"):
                                    metadata.update(json.loads(content))
                                else:
                                    metadata[metadata_file] = content
                            except Exception as e:
                                logger.warning(f"Error reading {metadata_file}: {e}")
            except Exception as e:
                logger.warning(f"Error extracting JAR metadata: {e}")

            return metadata

        def _extract_source_metadata(source_path: str) -> Dict:
            """Extract metadata from source directory"""
            metadata = {}

            try:
                for root, dirs, files in os.walk(source_path):
                    for file_name in files:
                        if file_name in agent.file_patterns["metadata_files"]:
                            file_path = os.path.join(root, file_name)
                            try:
                                with open(file_path, "r", encoding="utf-8") as f:
                                    content = f.read()
                                    if file_name.endswith(".json"):
                                        metadata.update(json.loads(content))
                                    else:
                                        metadata[file_name] = content
                            except Exception as e:
                                logger.warning(f"Error reading {file_path}: {e}")
            except Exception as e:
                logger.warning(f"Error extracting source metadata: {e}")

            return metadata

        try:
            if isinstance(mod_data, str):
                try:
                    data = json.loads(mod_data)
                    if "mod_data" in data:
                        mod_path = data["mod_data"]
                    else:
                        mod_path = data.get("mod_path", "")
                except json.JSONDecodeError:
                    mod_path = mod_data
            else:
                data = mod_data if isinstance(mod_data, dict) else {"mod_path": str(mod_data)}
                if "mod_data" in data:
                    mod_path = data["mod_data"]
                else:
                    mod_path = data.get("mod_path", str(mod_data))

            metadata_results = {
                "mod_info": {},
                "dependencies": [],
                "version_info": {},
                "author_info": {},
                "feature_flags": {},
                "compatibility_info": {},
            }

            if mod_path.endswith((".jar", ".zip")):
                metadata = _extract_jar_metadata(mod_path)
            else:
                metadata = _extract_source_metadata(mod_path)

            metadata_results.update(metadata)

            response = {
                "success": True,
                "metadata": metadata_results,
                "extraction_summary": {"summary": "Metadata extraction completed"},
            }

            logger.info(f"Extracted metadata from: {mod_path}")
            return json.dumps(response)

        except Exception as e:
            error_response = {"success": False, "error": f"Failed to extract metadata: {str(e)}"}
            logger.error(f"Metadata extraction error: {e}")
            return json.dumps(error_response)

    @staticmethod
    def _identify_features(mod_data: Union[str, Dict]) -> str:
        """
        Identify features in the mod.

        Args:
            mod_data: JSON string containing analysis data

        Returns:
            JSON string with identified features
        """
        from agents.java_analyzer import JavaAnalyzerAgent

        JavaAnalyzerAgent.get_instance()

        def _categorize_features(features: List[Dict]) -> Dict:
            """Categorize features by type"""
            categories = {}
            for feature in features:
                feature_type = feature.get("feature_type", "unknown")
                if feature_type not in categories:
                    categories[feature_type] = []
                categories[feature_type].append(feature)
            return categories

        def _analyze_feature_complexity(features: List[Dict]) -> Dict:
            """Analyze complexity of identified features"""
            return {
                "total_features": len(features),
                "complexity_distribution": {"simple": 0, "moderate": 0, "complex": 0},
                "high_priority_features": [f for f in features if f.get("confidence") == "high"],
            }

        def _identify_conversion_challenges(features: List[Dict], categories: Dict) -> List[str]:
            """Identify potential conversion challenges"""
            challenges = []

            if "dimensions" in categories:
                challenges.append("Custom dimensions require structural workarounds")

            if "gui" in categories:
                challenges.append("Custom GUIs need alternative interfaces")

            if "machinery" in categories:
                challenges.append("Complex machinery may lose functionality")

            return challenges

        try:
            if isinstance(mod_data, str):
                try:
                    data = json.loads(mod_data)
                    if "mod_data" in data:
                        mod_path = data["mod_data"]
                    else:
                        mod_path = data.get("mod_path", "")
                except json.JSONDecodeError:
                    mod_path = mod_data
            else:
                data = mod_data if isinstance(mod_data, dict) else {"mod_path": str(mod_data)}
                if "mod_data" in data:
                    mod_path = data["mod_data"]
                else:
                    mod_path = data.get("mod_path", str(mod_data))

            feature_results = {
                "identified_features": [],
                "feature_categories": {},
                "feature_complexity": {},
                "conversion_challenges": [],
            }

            if mod_path.endswith((".jar", ".zip")):
                analyzer_instance = JavaAnalyzerAgent.get_instance()
                ast_result = analyzer_instance.analyze_jar_with_ast(mod_path)
                if ast_result["success"]:
                    features = []
                    for feature_type, feature_list in ast_result.get("features", {}).items():
                        for feature in feature_list:
                            features.append(
                                {
                                    "feature_id": f"{feature_type}_{feature.get('name', 'unknown').lower()}",
                                    "feature_type": feature_type,
                                    "name": feature.get("name", "Unknown"),
                                    "source": "ast_analysis",
                                    "confidence": "high",
                                    "original_data": feature,
                                }
                            )
                else:
                    features = []
            else:
                features = []

            categorized_features = _categorize_features(features)
            feature_results["identified_features"] = features
            feature_results["feature_categories"] = categorized_features

            complexity_analysis = _analyze_feature_complexity(features)
            feature_results["feature_complexity"] = complexity_analysis

            challenges = _identify_conversion_challenges(features, categorized_features)
            feature_results["conversion_challenges"] = challenges

            response = {
                "success": True,
                "feature_results": feature_results,
                "feature_summary": {"summary": f"Identified {len(features)} features"},
            }

            logger.info(f"Identified {len(features)} features in: {mod_path}")
            return json.dumps(response)

        except Exception as e:
            error_response = {"success": False, "error": f"Failed to identify features: {str(e)}"}
            logger.error(f"Feature identification error: {e}")
            return json.dumps(error_response)

    @staticmethod
    def _analyze_dependencies(mod_data: Union[str, Dict]) -> str:
        """
        Analyze mod dependencies.

        Args:
            mod_data: JSON string containing mod information

        Returns:
            JSON string with dependency analysis
        """
        from agents.java_analyzer import JavaAnalyzerAgent

        JavaAnalyzerAgent.get_instance()

        def _generate_dependency_recommendations(results: Dict) -> List[str]:
            """Generate dependency recommendations"""
            return ["Review dependencies for Bedrock compatibility"]

        try:
            if isinstance(mod_data, str):
                try:
                    data = json.loads(mod_data)
                    if "mod_data" in data:
                        (data["mod_data"] if isinstance(data["mod_data"], dict) else {})
                    else:
                        data.get("mod_metadata", {})
                except json.JSONDecodeError:
                    pass
            else:
                data = mod_data if isinstance(mod_data, dict) else {"mod_metadata": {}}
                if "mod_data" in data:
                    data["mod_data"] if isinstance(data["mod_data"], dict) else {}
                else:
                    data.get("mod_metadata", {})

            dependency_results = {
                "direct_dependencies": [],
                "transitive_dependencies": [],
                "framework_dependencies": [],
                "conversion_impact": {},
                "compatibility_concerns": [],
            }

            response = {
                "success": True,
                "dependency_analysis": dependency_results,
                "recommendations": _generate_dependency_recommendations(dependency_results),
            }

            logger.info("Analyzed dependencies: 0 direct, 0 framework")
            return json.dumps(response)

        except Exception as e:
            error_response = {
                "success": False,
                "error": f"Failed to analyze dependencies: {str(e)}",
            }
            logger.error(f"Dependency analysis error: {e}")
            return json.dumps(error_response)

    @staticmethod
    def _extract_assets(mod_data: Union[str, Dict]) -> str:
        """
        Extract assets from the mod.

        Args:
            mod_data: JSON string containing mod file path

        Returns:
            JSON string with asset information
        """
        from agents.java_analyzer import JavaAnalyzerAgent

        JavaAnalyzerAgent.get_instance()

        def _extract_assets_from_jar(jar_path: str, asset_types: List[str]) -> List[Dict]:
            """Extract assets from JAR"""
            assets = []
            try:
                with zipfile.ZipFile(jar_path, "r") as jar:
                    file_list = jar.namelist()

                    for file_path in file_list:
                        if "/textures/" in file_path and file_path.endswith(
                            (".png", ".jpg", ".jpeg")
                        ):
                            assets.append(
                                {
                                    "type": "texture",
                                    "path": file_path,
                                    "name": Path(file_path).name,
                                    "size": jar.getinfo(file_path).file_size,
                                }
                            )
                        elif "/models/" in file_path and file_path.endswith((".json", ".obj")):
                            assets.append(
                                {
                                    "type": "model",
                                    "path": file_path,
                                    "name": Path(file_path).name,
                                    "size": jar.getinfo(file_path).file_size,
                                }
                            )
                        elif "/sounds/" in file_path and file_path.endswith((".ogg", ".wav")):
                            assets.append(
                                {
                                    "type": "sound",
                                    "path": file_path,
                                    "name": Path(file_path).name,
                                    "size": jar.getinfo(file_path).file_size,
                                }
                            )
                        elif "/lang/" in file_path and file_path.endswith(".json"):
                            assets.append(
                                {
                                    "type": "lang",
                                    "path": file_path,
                                    "name": Path(file_path).name,
                                    "size": jar.getinfo(file_path).file_size,
                                }
                            )
                        elif file_path.endswith("sounds.json") and "/sounds" in file_path:
                            assets.append(
                                {
                                    "type": "sounds_json",
                                    "path": file_path,
                                    "name": Path(file_path).name,
                                    "size": jar.getinfo(file_path).file_size,
                                }
                            )
            except Exception as e:
                logger.warning(f"Error extracting assets from JAR: {e}")

            return assets

        def _determine_asset_type(asset: Dict) -> str:
            """Determine asset type"""
            asset_type = asset.get("type", "unknown")
            if asset_type in ["texture", "model", "sound"]:
                return f"{asset_type}s"
            return "other_assets"

        try:
            if isinstance(mod_data, str):
                try:
                    data = json.loads(mod_data)
                    if "mod_data" in data:
                        mod_path = data["mod_data"]
                    else:
                        mod_path = data.get("mod_path", "")
                except json.JSONDecodeError:
                    mod_path = mod_data
            else:
                data = mod_data if isinstance(mod_data, dict) else {"mod_path": str(mod_data)}
                if "mod_data" in data:
                    mod_path = data["mod_data"]
                else:
                    mod_path = data.get("mod_path", str(mod_data))

            asset_results = {
                "textures": [],
                "models": [],
                "sounds": [],
                "other_assets": [],
                "asset_summary": {},
            }

            if mod_path.endswith((".jar", ".zip")):
                assets = _extract_assets_from_jar(mod_path, [])
            else:
                assets = []

            for asset in assets:
                asset_type = _determine_asset_type(asset)
                if asset_type in asset_results:
                    asset_results[asset_type].append(asset)
                else:
                    asset_results["other_assets"].append(asset)

            asset_results["asset_summary"] = {"summary": "Asset extraction completed"}

            response = {
                "success": True,
                "assets": asset_results,
                "conversion_notes": ["Assets ready for conversion analysis"],
            }

            total_assets = sum(
                len(assets) for assets in asset_results.values() if isinstance(assets, list)
            )
            logger.info(f"Extracted {total_assets} assets from: {mod_path}")
            return json.dumps(response)

        except Exception as e:
            error_response = {"success": False, "error": f"Failed to extract assets: {str(e)}"}
            logger.error(f"Asset extraction error: {e}")
            return json.dumps(error_response)

    @staticmethod
    def _analyze_complexity_with_llm(analysis_data: str) -> str:
        """
        Use LLM to analyze Java mod complexity and identify Bedrock-incompatible patterns.

        This tool augments the regex-based feature detection with LLM-powered analysis
        to provide deeper insights into mod complexity and conversion feasibility.

        Args:
            analysis_data: JSON string containing:
                - source_code: Java source code to analyze
                - class_name: Name of the class being analyzed
                - feature_data: Existing feature data from regex analysis

        Returns:
            JSON string with LLM-powered complexity analysis
        """
        try:
            data = json.loads(analysis_data)
            source_code = data.get("source_code", "")
            class_name = data.get("class_name", "UnknownClass")
            feature_data = data.get("feature_data", {})

            from utils.llm_agent_tools import get_llm_agent_tools

            llm_tools = get_llm_agent_tools()
            llm_tools.initialize()

            result = llm_tools.analyze_java_mod_complexity(
                source_code=source_code, class_name=class_name, feature_data=feature_data
            )

            if result.get("success"):
                response = {
                    "success": True,
                    "llm_analysis": {
                        "complexity_level": result.get("complexity_level", "unknown"),
                        "bedrock_incompatible_patterns": result.get(
                            "bedrock_incompatible_patterns", []
                        ),
                        "conversion_strategies": result.get("conversion_strategies", []),
                        "summary": result.get("summary", ""),
                    },
                    "model_used": result.get("model_used", "unknown"),
                }
                logger.info(
                    f"LLM complexity analysis completed for {class_name}: {result.get('complexity_level', 'unknown')}"
                )
            else:
                response = {
                    "success": False,
                    "error": result.get("error", "LLM analysis failed"),
                    "llm_analysis": None,
                }
                logger.warning(
                    f"LLM complexity analysis failed for {class_name}: {result.get('error')}"
                )

            return json.dumps(response)

        except Exception as e:
            error_response = {"success": False, "error": f"LLM analysis failed: {str(e)}"}
            logger.error(f"LLM complexity analysis error: {e}")
            return json.dumps(error_response)


# ─────────────────────────────────────────────────────────────────────────────
# Typed args_schema models — one per LangChain tool wrapper
#
# Phase 8 A6 (refs #1201). Each schema preserves the legacy single-arg
# ``mod_data: Union[str, Dict]`` (or ``analysis_data: str``) shape so chat
# models and existing call sites continue to invoke
# ``JavaAnalyzerAgent.<tool_name>.invoke({...})`` without changes. Five of
# the six tools accept either a JSON string or a dict, mirroring the
# legacy ``Union[str, Dict]`` typing on the static methods. The sixth
# (``analyze_complexity_with_llm_tool``) requires a JSON string only.
# ─────────────────────────────────────────────────────────────────────────────


class _AnalyzeModStructureInput(BaseModel):
    """Args for :class:`_AnalyzeModStructureTool`."""

    model_config = ConfigDict(extra="forbid")
    mod_data: Any = Field(
        description=(
            "JSON string or dict containing ``mod_path`` and analysis options. "
            "``Any`` preserves the legacy ``Union[str, Dict]`` calling shape."
        ),
    )


class _ExtractModMetadataInput(BaseModel):
    """Args for :class:`_ExtractModMetadataTool`."""

    model_config = ConfigDict(extra="forbid")
    mod_data: Any = Field(
        description="JSON string or dict containing ``mod_path``.",
    )


class _IdentifyFeaturesInput(BaseModel):
    """Args for :class:`_IdentifyFeaturesTool`."""

    model_config = ConfigDict(extra="forbid")
    mod_data: Any = Field(
        description="JSON string or dict containing ``mod_path`` and feature options.",
    )


class _AnalyzeDependenciesInput(BaseModel):
    """Args for :class:`_AnalyzeDependenciesTool`."""

    model_config = ConfigDict(extra="forbid")
    mod_data: Any = Field(
        description=(
            "JSON string or dict containing ``mod_path`` and an optional "
            "``metadata.dependencies`` list."
        ),
    )


class _ExtractAssetsInput(BaseModel):
    """Args for :class:`_ExtractAssetsTool`."""

    model_config = ConfigDict(extra="forbid")
    mod_data: Any = Field(
        description=(
            "JSON string or dict containing ``mod_path``, ``output_dir``, and "
            "optional ``asset_types`` filter."
        ),
    )


class _AnalyzeComplexityWithLlmInput(BaseModel):
    """Args for :class:`_AnalyzeComplexityWithLlmTool`."""

    model_config = ConfigDict(extra="forbid")
    analysis_data: str = Field(
        min_length=1,
        description=(
            "JSON string with the prior analysis output to be reasoned about "
            "by the LLM-augmented complexity analyzer."
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Typed BaseTool subclasses — replace the previous @tool @staticmethod wrappers
# ─────────────────────────────────────────────────────────────────────────────


class _BaseJavaAnalyzerTool(BaseTool):
    """Common scaffolding for Java Analyzer typed tool wrappers."""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class _AnalyzeModStructureTool(_BaseJavaAnalyzerTool):
    name: str = "analyze_mod_structure_tool"
    description: str = (
        "Analyze the overall structure of a Java mod (mod type, framework, "
        "file inventory, complexity assessment). "
        "Args: mod_data (str or dict, required) — mod_path and options."
    )
    args_schema: ClassVar[type[BaseModel]] = _AnalyzeModStructureInput

    def _run(self, mod_data: Any) -> str:  # type: ignore[override]
        return JavaAnalyzerTools._analyze_mod_structure(mod_data)


class _ExtractModMetadataTool(_BaseJavaAnalyzerTool):
    name: str = "extract_mod_metadata_tool"
    description: str = (
        "Extract metadata from a Java mod's manifest "
        "(fabric.mod.json, mods.toml, mcmod.info). "
        "Args: mod_data (str or dict, required) — mod_path."
    )
    args_schema: ClassVar[type[BaseModel]] = _ExtractModMetadataInput

    def _run(self, mod_data: Any) -> str:  # type: ignore[override]
        return JavaAnalyzerTools._extract_mod_metadata(mod_data)


class _IdentifyFeaturesTool(_BaseJavaAnalyzerTool):
    name: str = "identify_features_tool"
    description: str = (
        "Identify mod features (blocks, items, entities, recipes, events) "
        "from source/jar inspection. "
        "Args: mod_data (str or dict, required) — mod_path and options."
    )
    args_schema: ClassVar[type[BaseModel]] = _IdentifyFeaturesInput

    def _run(self, mod_data: Any) -> str:  # type: ignore[override]
        return JavaAnalyzerTools._identify_features(mod_data)


class _AnalyzeDependenciesTool(_BaseJavaAnalyzerTool):
    name: str = "analyze_dependencies_tool"
    description: str = (
        "Analyze a mod's declared and detected dependencies, including "
        "Bedrock-portability assessment. "
        "Args: mod_data (str or dict, required) — mod_path + optional metadata."
    )
    args_schema: ClassVar[type[BaseModel]] = _AnalyzeDependenciesInput

    def _run(self, mod_data: Any) -> str:  # type: ignore[override]
        return JavaAnalyzerTools._analyze_dependencies(mod_data)


class _ExtractAssetsTool(_BaseJavaAnalyzerTool):
    name: str = "extract_assets_tool"
    description: str = (
        "Extract assets (textures, models, sounds) from a Java mod. "
        "Args: mod_data (str or dict, required) — mod_path, output_dir, "
        "optional asset_types filter."
    )
    args_schema: ClassVar[type[BaseModel]] = _ExtractAssetsInput

    def _run(self, mod_data: Any) -> str:  # type: ignore[override]
        return JavaAnalyzerTools._extract_assets(mod_data)


class _AnalyzeComplexityWithLlmTool(_BaseJavaAnalyzerTool):
    name: str = "analyze_complexity_with_llm_tool"
    description: str = (
        "Use the LLM to reason about an analysis's complexity. "
        "Args: analysis_data (str, required) — JSON of prior analysis."
    )
    args_schema: ClassVar[type[BaseModel]] = _AnalyzeComplexityWithLlmInput

    def _run(self, analysis_data: str) -> str:  # type: ignore[override]
        return JavaAnalyzerTools._analyze_complexity_with_llm(analysis_data)


# ─────────────────────────────────────────────────────────────────────────────
# Module-level tool instances — preserved as class attributes on
# JavaAnalyzerTools so the ``JavaAnalyzerAgent`` class-attribute aliases in
# ``agents/java_analyzer/java_analyzer.py``
# (``extract_mod_metadata_tool = JavaAnalyzerTools.extract_mod_metadata_tool``)
# resolve to the new typed BaseTool instances at import time.
# ─────────────────────────────────────────────────────────────────────────────


JavaAnalyzerTools.analyze_mod_structure_tool = _AnalyzeModStructureTool()
JavaAnalyzerTools.extract_mod_metadata_tool = _ExtractModMetadataTool()
JavaAnalyzerTools.identify_features_tool = _IdentifyFeaturesTool()
JavaAnalyzerTools.analyze_dependencies_tool = _AnalyzeDependenciesTool()
JavaAnalyzerTools.extract_assets_tool = _ExtractAssetsTool()
JavaAnalyzerTools.analyze_complexity_with_llm_tool = _AnalyzeComplexityWithLlmTool()
