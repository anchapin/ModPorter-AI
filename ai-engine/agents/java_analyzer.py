"""
Java Analyzer Agent for analyzing Java mod structure and extracting features
"""

import json
import re
from typing import List, Dict, Union, Optional, Any
from crewai.tools import tool
from models.smart_assumptions import (
    SmartAssumptionEngine,
)
from utils.embedding_generator import LocalEmbeddingGenerator
from utils.logging_config import get_agent_logger, log_performance
import os
import zipfile
from pathlib import Path
import time
import javalang

# Make javassist optional - will be used for bytecode analysis if available
try:
    import javassist

    JAVASSIST_AVAILABLE = True
except ImportError:
    javassist = None
    JAVASSIST_AVAILABLE = False

# Make javassist optional - will be used for bytecode analysis if available
try:
    import javassist

    JAVASSIST_AVAILABLE = True
except ImportError:
    javassist = None
    JAVASSIST_AVAILABLE = False


# Constants for file analysis limits
FEATURE_ANALYSIS_FILE_LIMIT = 10
METADATA_AST_FILE_LIMIT = 5
DEPENDENCY_ANALYSIS_FILE_LIMIT = 10

# Use enhanced agent logger
logger = get_agent_logger("java_analyzer")


class JavaAnalyzerAgent:
    """
    Java Analyzer Agent responsible for analyzing Java mod structure,
    dependencies, and features as specified in PRD Feature 2.
    """

    _instance = None

    def __init__(self):
        self.logger = logger
        self.smart_assumption_engine = SmartAssumptionEngine()
        self.embedding_generator = (
            LocalEmbeddingGenerator()
        )  # Added EmbeddingGenerator instantiation

        # File patterns for different types of mod files
        self.file_patterns = {
            "mod_files": [".jar", ".zip"],
            "source_files": [".java"],
            "config_files": [".json", ".toml", ".cfg"],
            "resource_files": [".png", ".jpg", ".ogg", ".wav", ".obj", ".mtl"],
            "metadata_files": ["mcmod.info", "fabric.mod.json", "quilt.mod.json", "mods.toml"],
        }

        # Common modding framework indicators
        self.framework_indicators = {
            "forge": ["net.minecraftforge", "cpw.mods", "@Mod", "ForgeModContainer"],
            "fabric": ["net.fabricmc", "FabricLoader", "fabric.mod.json"],
            "quilt": ["org.quiltmc", "QuiltLoader", "quilt.mod.json"],
            "bukkit": ["org.bukkit", "plugin.yml", "JavaPlugin"],
            "spigot": ["org.spigotmc", "SpigotAPI"],
            "paper": ["io.papermc", "PaperAPI"],
        }

        # Feature extraction patterns
        self.feature_patterns = {
            "blocks": ["Block", "BlockState", "registerBlock", "ModBlocks"],
            "items": ["Item", "ItemStack", "registerItem", "ModItems"],
            "entities": ["Entity", "EntityType", "registerEntity", "ModEntities"],
            "dimensions": ["Dimension", "World", "DimensionType", "createDimension"],
            "gui": ["GuiScreen", "ContainerScreen", "IGuiHandler", "MenuType"],
            "machinery": ["TileEntity", "BlockEntity", "IEnergyStorage", "IFluidHandler"],
            "recipes": ["IRecipe", "ShapedRecipe", "ShapelessRecipe", "registerRecipe"],
            "commands": ["Command", "ICommand", "CommandBase", "registerCommand"],
            "events": ["Event", "SubscribeEvent", "EventHandler", "Listener"],
        }

    @classmethod
    def get_instance(cls):
        """Get singleton instance of JavaAnalyzerAgent"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_tools(self) -> List:
        """Get tools available to this agent"""
        # Return the actual decorated tool instances created by @tool decorator
        return [
            JavaAnalyzerAgent.analyze_mod_structure_tool,
            JavaAnalyzerAgent.extract_mod_metadata_tool,
            JavaAnalyzerAgent.identify_features_tool,
            JavaAnalyzerAgent.analyze_dependencies_tool,
            JavaAnalyzerAgent.extract_assets_tool,
        ]

    @log_performance("mod_file_analysis")
    def analyze_mod_file(self, mod_path: str) -> str:
        """
        Analyze a mod file and return comprehensive results.

        Args:
            mod_path: Path to the mod file

        Returns:
            JSON string with analysis results
        """
        try:
            self.logger.log_operation_start(
                "mod_file_analysis", mod_path=mod_path, file_size=self._get_file_size(mod_path)
            )

            # Initialize result structure
            result = {
                "mod_info": {"name": "unknown", "framework": "unknown", "version": "1.0.0"},
                "assets": {},
                "features": {},
                "structure": {},
                "metadata": {},
                "errors": [],
                "embeddings_data": [],
            }

            self.logger.debug("Initialized analysis result structure")

            # Analyze the mod file based on type
            if mod_path.endswith((".jar", ".zip")):
                self.logger.info("Analyzing JAR/ZIP file", file_type="archive")
                # Use AST-based analysis for better feature extraction
                ast_result = self.analyze_jar_with_ast(mod_path)
                if ast_result["success"]:
                    # Merge AST results with existing structure
                    result["mod_info"].update(ast_result["mod_info"])
                    result["assets"] = ast_result["assets"]
                    result["features"] = ast_result["features"]
                    result["structure"] = {"files": ast_result.get("file_count", 0), "type": "jar"}
                    if ast_result.get("dependencies"):
                        result["dependencies"] = ast_result["dependencies"]
                    if ast_result.get("framework"):
                        result["mod_info"]["framework"] = ast_result["framework"]
                    result["errors"].extend(ast_result.get("errors", []))
                else:
                    # Fallback to original analysis if AST analysis fails
                    self.logger.warning("AST analysis failed, falling back to original analysis")
                    result = self._analyze_jar_file(mod_path, result)
            elif os.path.isdir(mod_path):
                self.logger.info("Analyzing source directory", file_type="directory")
                result = self._analyze_source_directory(mod_path, result)
            else:
                error_msg = f"Unsupported mod file format: {mod_path}"
                self.logger.error(error_msg)
                result["errors"].append(error_msg)

            # Log analysis results summary
            self.logger.info(
                "Analysis completed",
                mod_name=result["mod_info"]["name"],
                framework=result["mod_info"]["framework"],
                assets_count=len(result["assets"]),
                features_count=len(result["features"]),
                errors_count=len(result["errors"]),
            )

            # Generate embeddings for the analyzed content
            self.logger.debug("Generating embeddings for analyzed content")
            embedding_start = time.time()
            self._generate_embeddings(result)
            embedding_duration = time.time() - embedding_start
            self.logger.log_tool_usage(
                "embedding_generator",
                result=f"Generated {len(result['embeddings_data'])} embeddings",
                duration=embedding_duration,
            )

            result_json = json.dumps(result)
            self.logger.debug("Analysis result serialized", result_size=len(result_json))
            return result_json

        except Exception as e:
            self.logger.error(
                f"Error analyzing mod file {mod_path}: {e}", error_type=type(e).__name__
            )
            error_result = {
                "mod_info": {"name": "error", "framework": "unknown", "version": "1.0.0"},
                "assets": {},
                "features": {},
                "structure": {},
                "metadata": {},
                "errors": [f"Analysis failed: {str(e)}"],
                "embeddings_data": [],
            }
            return json.dumps(error_result)

    def _get_file_size(self, file_path: str) -> int:
        """Get file size in bytes, return 0 if file doesn't exist or is directory"""
        try:
            if os.path.isfile(file_path):
                return os.path.getsize(file_path)
            elif os.path.isdir(file_path):
                # Calculate directory size
                total_size = 0
                for dirpath, dirnames, filenames in os.walk(file_path):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        try:
                            total_size += os.path.getsize(filepath)
                        except (OSError, IOError):
                            continue
                return total_size
            return 0
        except (OSError, IOError):
            return 0

    def _analyze_sources_batch(self, jar: zipfile.ZipFile, java_sources: List[str]) -> Dict:
        """
        Analyze Java sources in a single pass to extract features, dependencies, and metadata.
        Optimized to parse each file only once and skip files without relevant keywords.

        Args:
            jar: Opened JAR file
            java_sources: List of Java source file paths in the JAR

        Returns:
            Dictionary with keys 'features', 'dependencies', 'metadata'
        """
        batch_result = {
            "features": {
                "blocks": [],
                "items": [],
                "entities": [],
                "recipes": [],
                "dimensions": [],
                "gui": [],
                "machinery": [],
                "commands": [],
                "events": [],
            },
            "dependencies": [],
            "metadata": {},
        }

        max_files = max(
            FEATURE_ANALYSIS_FILE_LIMIT, DEPENDENCY_ANALYSIS_FILE_LIMIT, METADATA_AST_FILE_LIMIT
        )

        # Collect keywords for pre-check
        feature_keywords = set()
        for patterns in self.feature_patterns.values():
            feature_keywords.update(patterns)

        metadata_keywords = {"Mod", "ModInstance", "Instance", "@Mod"}
        dependency_keywords = {"import", "package"}

        for i, source_path in enumerate(java_sources[:max_files]):
            # Determine needs before try block to avoid UnboundLocalError in except
            need_features = i < FEATURE_ANALYSIS_FILE_LIMIT
            need_deps = i < DEPENDENCY_ANALYSIS_FILE_LIMIT
            need_metadata = i < METADATA_AST_FILE_LIMIT

            try:
                # Read source file
                source_code = jar.read(source_path).decode("utf-8")

                # Optimization: Keyword Pre-check
                should_parse = False

                # Check keywords based on needs
                if need_deps:
                    if any(k in source_code for k in dependency_keywords):
                        should_parse = True

                if not should_parse and need_metadata:
                    if any(k in source_code for k in metadata_keywords):
                        should_parse = True

                if not should_parse and need_features:
                    if any(k in source_code for k in feature_keywords):
                        should_parse = True

                if not should_parse:
                    # Skip parsing if no relevant keywords found
                    continue

                # Parse AST
                tree = self._parse_java_source(source_code)
                if not tree:
                    continue

                # Extract Features
                if need_features:
                    source_features = self._extract_features_from_ast(tree)
                    for feature_type, feature_list in source_features.items():
                        if feature_type in batch_result["features"]:
                            batch_result["features"][feature_type].extend(feature_list)

                # Extract Dependencies
                if need_deps:
                    dependencies = self._analyze_dependencies_from_ast(tree)
                    batch_result["dependencies"].extend(dependencies)

                # Extract Metadata
                if need_metadata:
                    source_metadata = self._extract_mod_metadata_from_ast(tree)
                    batch_result["metadata"].update(source_metadata)

            except Exception as e:
                logger.warning(f"Error analyzing source file {source_path}: {e}")
                # Try to extract features from class names as fallback
                if need_features:
                    class_name = source_path.split("/")[-1].replace(".java", "")
                    fallback_features = self._extract_features_from_class_name(class_name)
                    for feature_type, feature_list in fallback_features.items():
                        if feature_type in batch_result["features"]:
                            batch_result["features"][feature_type].extend(feature_list)
                continue

        # Deduplicate features
        for feature_type in batch_result["features"]:
            seen = set()
            unique_features = []
            for feature in batch_result["features"][feature_type]:
                feature_key = f"{feature.get('name', '')}_{feature.get('registry_name', '')}"
                if feature_key not in seen:
                    seen.add(feature_key)
                    unique_features.append(feature)
            batch_result["features"][feature_type] = unique_features

        # Deduplicate dependencies
        seen_imports = set()
        unique_dependencies = []
        for dep in batch_result["dependencies"]:
            import_path = dep.get("import", "")
            if import_path not in seen_imports:
                seen_imports.add(import_path)
                unique_dependencies.append(dep)
        batch_result["dependencies"] = unique_dependencies

        return batch_result

    def analyze_jar_with_ast(self, jar_path: str) -> dict:
        """
        AST-focused analysis: Extract comprehensive mod information using Java AST parsing.

        Args:
            jar_path: Path to the JAR file

        Returns:
            Dict with analysis results including features, dependencies, and metadata
        """
        try:
            logger.info(f"AST analysis of JAR: {jar_path}")
            result = {
                "success": False,
                "mod_info": {},
                "assets": {},
                "features": {},
                "dependencies": [],
                "framework": "unknown",
                "errors": [],
                "processing_time": 0,
            }

            start_time = time.time()

            with zipfile.ZipFile(jar_path, "r") as jar:
                file_list = jar.namelist()

                # Handle empty JARs gracefully
                if not file_list:
                    logger.warning(f"Empty JAR file: {jar_path}")
                    result["success"] = True  # Consider empty JAR as successfully analyzed
                    result["mod_info"] = {
                        "name": "unknown",
                        "framework": "unknown",
                        "version": "1.0.0",
                    }
                    result["errors"].append("JAR file is empty but analysis completed")
                    result["processing_time"] = time.time() - start_time
                    result["file_count"] = 0
                    return result

                # Detect framework
                framework = self._detect_framework_from_jar_files(file_list, jar)
                result["framework"] = framework
                result["mod_info"]["framework"] = framework

                # Extract mod info from metadata files
                mod_info = self._extract_mod_info_from_jar(jar, file_list)
                result["mod_info"].update(mod_info)

                # Analyze assets
                result["assets"] = self._analyze_assets_from_jar(file_list)

                # Extract Java source files and analyze with AST
                java_sources = [f for f in file_list if f.endswith(".java")]
                if java_sources:
                    logger.info(f"Found {len(java_sources)} Java source files, analyzing with AST")

                    # Optimized single-pass analysis
                    batch_results = self._analyze_sources_batch(jar, java_sources)

                    result["features"] = batch_results["features"]
                    result["dependencies"] = batch_results["dependencies"]
                    result["mod_info"].update(batch_results["metadata"])
                else:
                    logger.info("No Java source files found in JAR, attempting bytecode analysis")

                    # First try bytecode analysis if javassist is available
                    if JAVASSIST_AVAILABLE:
                        bytecode_features = self._analyze_classes_with_bytecode(jar, file_list)
                        if bytecode_features and (
                            bytecode_features.get("blocks")
                            or bytecode_features.get("items")
                            or bytecode_features.get("entities")
                        ):
                            logger.info(
                                f"Bytecode analysis found {len(bytecode_features['blocks'])} blocks, {len(bytecode_features['items'])} items"
                            )
                            result["features"] = bytecode_features
                        else:
                            logger.info(
                                "Bytecode analysis yielded no results, falling back to class name analysis"
                            )
                            result["features"] = self._extract_features_from_classes(file_list)
                    else:
                        logger.info("Javassist not available, using class name-based analysis")
                        # Extract features from class names (existing approach)
                        result["features"] = self._extract_features_from_classes(file_list)

                    result["dependencies"] = []  # No dependency analysis without sources

                # Mark as successful
                result["success"] = True
                result["file_count"] = len(file_list)

            result["processing_time"] = time.time() - start_time
            logger.info(
                f"AST analysis completed successfully for {jar_path} in {result['processing_time']:.2f}s"
            )
            return result

        except Exception as e:
            logger.error(f"AST analysis error: {e}")
            return {
                "success": False,
                "mod_info": {},
                "assets": {},
                "features": {},
                "dependencies": [],
                "framework": "unknown",
                "errors": [f"JAR analysis failed: {str(e)}"],
                "processing_time": 0,
            }

    def analyze_jar_for_mvp(self, jar_path: str) -> dict:
        """
        MVP-focused analysis: Extract registry name and texture path from simple block JAR.

        This method implements the specific requirements for Issue #167:
        - Parse registry name from Java classes
        - Find texture path in assets/*/textures/block/*.png

        Args:
            jar_path: Path to the JAR file

        Returns:
            Dict with registry_name, texture_path, and success status
        """
        try:
            logger.info(f"MVP analysis of JAR: {jar_path}")
            result = {
                "success": False,
                "registry_name": "unknown:block",
                "texture_path": None,
                "errors": [],
            }

            with zipfile.ZipFile(jar_path, "r") as jar:
                file_list = jar.namelist()

                # Handle empty JARs gracefully
                if not file_list:
                    logger.warning(f"Empty JAR file: {jar_path}")
                    result["success"] = True  # Consider empty JAR as successfully analyzed
                    result["registry_name"] = (
                        "unknown:copper_block"  # Default fallback for empty JARs
                    )
                    result["errors"].append("JAR file is empty but analysis completed")
                    return result

                # Find block texture
                texture_path = self._find_block_texture(file_list)
                if texture_path:
                    result["texture_path"] = texture_path
                    logger.info(f"Found texture: {texture_path}")

                # Extract registry name
                registry_name = self._extract_registry_name_from_jar(jar, file_list)
                if registry_name:
                    result["registry_name"] = registry_name
                    logger.info(f"Found registry name: {registry_name}")

                # For MVP, we need at least a registry name for success
                if registry_name and registry_name != "unknown:block":
                    result["success"] = True
                    logger.info(f"MVP analysis completed successfully for {jar_path}")
                    if not texture_path:
                        logger.warning("No texture found, will use default texture")
                        if "warnings" not in result:
                            result["warnings"] = []
                        result["warnings"].append(
                            "Could not find block texture in JAR, using default"
                        )
                else:
                    result["errors"].append("Could not determine block registry name")
                    # Explicitly set success to False if not already set
                    if "success" not in result or not result["success"]:
                        result["success"] = False

                return result

        except Exception as e:
            logger.error(f"MVP analysis error: {e}")
            return {
                "success": False,
                "registry_name": "unknown:block",
                "texture_path": None,
                "errors": [f"JAR analysis failed: {str(e)}"],
            }

    def _find_block_texture(self, file_list: list) -> str:
        """Find a block texture in the JAR file list."""
        for file_path in file_list:
            if (
                file_path.startswith("assets/")
                and "/textures/block/" in file_path
                and file_path.endswith(".png")
            ):
                return file_path
        return None

    def _extract_registry_name_from_jar_simple(self, jar, file_list: list) -> str:
        """Extract block registry name from JAR metadata (simple version)."""
        # Look for mod metadata files
        for metadata_file in ["mcmod.info", "fabric.mod.json", "mods.toml"]:
            if metadata_file in file_list:
                try:
                    content = jar.read(metadata_file).decode("utf-8")
                    if metadata_file == "mcmod.info":
                        import json

                        data = json.loads(content)
                        if isinstance(data, list) and len(data) > 0:
                            mod_id = data[0].get("modid", "unknown")
                            return f"{mod_id}:copper_block"  # Default block name for MVP
                    elif metadata_file == "fabric.mod.json":
                        import json

                        data = json.loads(content)
                        mod_id = data.get("id", "unknown")
                        return f"{mod_id}:copper_block"
                except (json.JSONDecodeError, UnicodeDecodeError, KeyError) as e:
                    logger.debug(f"Could not parse {metadata_file}: {e}")
                    continue

        # Default fallback
        return "unknown:copper_block"

    def _find_block_texture_extended(self, file_list: list) -> str:
        """
        Find the first block texture in the JAR.
        Looks for: assets/*/textures/block/*.png
        """
        for file_name in file_list:
            if (
                file_name.startswith("assets/")
                and "/textures/block/" in file_name
                and file_name.endswith(".png")
            ):
                return file_name
        return None

    def _extract_registry_name_from_jar(self, jar: zipfile.ZipFile, file_list: list) -> str:
        """
        Extract registry name from Java source files or class names.
        Uses multiple strategies:
        1. Parse fabric.mod.json or mcmod.info for mod ID
        2. Look for Block class names
        3. Try to parse Java source if available
        """
        # Strategy 1: Get mod ID from metadata (most reliable)
        mod_id = self._extract_mod_id_from_metadata(jar, file_list)
        if mod_id:
            # Try to find a block class and construct registry name
            block_class = self._find_block_class_name(file_list)
            if block_class:
                # Convert BlockName to snake_case
                block_name = self._class_name_to_registry_name(block_class)
                return f"{mod_id}:{block_name}"
            return f"{mod_id}:unknown_block"

        # Strategy 2: Extract from main block class name
        block_class = self._find_block_class_name(file_list)
        if block_class:
            block_name = self._class_name_to_registry_name(block_class)
            return f"modporter:{block_name}"

        # Strategy 3: Use JAR filename as fallback
        return "modporter:unknown_block"

    def _extract_mod_id_from_metadata(self, jar: zipfile.ZipFile, file_list: list) -> str:
        """Extract mod ID from metadata files."""
        # Try fabric.mod.json first
        if "fabric.mod.json" in file_list:
            try:
                content = jar.read("fabric.mod.json").decode("utf-8")
                data = json.loads(content)
                return data.get("id", "").lower()
            except Exception as e:
                logger.warning(f"Error reading fabric.mod.json: {e}")

        # Try mcmod.info
        if "mcmod.info" in file_list:
            try:
                content = jar.read("mcmod.info").decode("utf-8")
                data = json.loads(content)
                if isinstance(data, list) and len(data) > 0:
                    return data[0].get("modid", "").lower()
            except Exception as e:
                logger.warning(f"Error reading mcmod.info: {e}")

        # Try mods.toml
        for file_name in file_list:
            if file_name.endswith("mods.toml"):
                try:
                    content = jar.read(file_name).decode("utf-8")
                    for line in content.split("\n"):
                        if "modId" in line and "=" in line:
                            mod_id = line.split("=")[1].strip().strip("\"'")
                            return mod_id.lower()
                except Exception as e:
                    logger.warning(f"Error reading {file_name}: {e}")

        return None

    def _find_block_class_name(self, file_list: list) -> str:
        """Find the main block class name from file paths."""
        block_candidates = []

        for file_name in file_list:
            if file_name.endswith(".class") or file_name.endswith(".java"):
                # Extract class name from path
                class_name = Path(file_name).stem

                # Look for Block in class name
                if "Block" in class_name and not class_name.startswith("Abstract"):
                    block_candidates.append(class_name)

        # Return the first/shortest block class name
        if block_candidates:
            # Prefer simpler names (shorter, fewer underscores)
            block_candidates.sort(key=lambda x: (len(x), x.count("_")))
            return block_candidates[0]

        return None

    def _class_name_to_registry_name(self, class_name: str) -> str:
        """Convert Java class name to registry name format."""
        # Remove 'Block' suffix if present, but only if it's not the entire name
        name = class_name
        if name.endswith("Block") and len(name) > 5:
            name = name[:-5]  # Remove 'Block' from the end
        elif name.startswith("Block") and len(name) > 5 and name[5].isupper():
            name = name[5:]  # Remove 'Block' from the start if it's a prefix like BlockOfCopper

        # Convert CamelCase to snake_case
        name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name).lower()

        # Clean up any double underscores or leading/trailing underscores
        name = re.sub(r"_+", "_", name).strip("_")

        # Ensure it's not empty after processing
        return name if name else "unknown"

    def _parse_java_source(self, source_code: str) -> javalang.ast.Node:
        """
        Parse Java source code into an AST using javalang.

        Improved to handle more Java syntax with better error handling.

        Args:
            source_code: Java source code as string

        Returns:
            Parsed AST or None if parsing fails
        """
        try:
            tree = javalang.parse.parse(source_code)
            return tree
        except javalang.parser.ParserError as e:
            # Handle specific parser errors with more context
            logger.warning(f"Parser error while parsing Java source: {e}")
            # Try to extract partial information even from malformed code
            return self._parse_java_source_fallback(source_code)
        except javalang.parser.JavaSyntaxError as e:
            logger.warning(f"Java syntax error: {e}")
            return self._parse_java_source_fallback(source_code)
        except Exception as e:
            logger.warning(f"Failed to parse Java source: {e}")
            return None

    def _parse_java_source_fallback(self, source_code: str) -> Optional[javalang.ast.Node]:
        """
        Fallback parsing that tries to handle partial/incomplete Java source code.

        Attempts to extract useful information even from code that fails full parsing.

        Args:
            source_code: Java source code as string

        Returns:
            Partial AST or None if parsing fails completely
        """
        try:
            # Try to extract imports using regex as fallback
            import re

            import_statements = re.findall(r"^import\s+([^;]+);", source_code, re.MULTILINE)

            # Try to extract class declarations using regex
            class_pattern = (
                r"(?:public\s+|private\s+|protected\s+)?(?:static\s+)?(?:abstract\s+)?class\s+(\w+)"
            )
            class_matches = re.findall(class_pattern, source_code)

            # Create a minimal AST-like structure
            class FakeAST:
                def __init__(self):
                    self.imports = []
                    for imp in import_statements:

                        class FakeImport:
                            def __init__(self, path):
                                self.path = path

                        self.imports.append(FakeImport(imp))
                    self.classes = class_matches

                def __iter__(self):
                    """Support tree walking"""
                    # Yield fake class declarations for compatibility
                    for class_name in self.classes:

                        class FakeClassNode:
                            def __init__(self, name):
                                self.name = name
                                self.methods = []
                                self.qualifier = ""
                                self.annotations = []

                        yield [], FakeClassNode(class_name)

            logger.debug(
                f"Fallback parsing extracted {len(import_statements)} imports and {len(class_matches)} classes"
            )
            return FakeAST()
        except Exception as e:
            logger.warning(f"Fallback parsing also failed: {e}")
            return None

    def _analyze_bytecode_class(self, class_data: bytes, class_name: str) -> Dict:
        """
        Analyze a Java class file using Javassist to extract class information.

        This provides fallback analysis when Java source files are not available.

        Args:
            class_data: Raw bytecode data from .class file
            class_name: Full class name (e.g., 'com/example/MyBlock')

        Returns:
            Dictionary with extracted class information
        """
        if not JAVASSIST_AVAILABLE or javassist is None:
            return {"error": "javassist not available"}

        class_info = {
            "name": class_name,
            "superclass": None,
            "interfaces": [],
            "fields": [],
            "methods": [],
            "annotations": [],
            "source": "bytecode",
        }

        try:
            # Create a class pool and read the class
            cp = javassist.ClassPool()
            # Add the current directory to the class path
            cp.appendSystemPath()

            # Read the class from bytecode
            ct_class = cp.make_class(javassist.bytecode.ConstPool(bytearray(class_data)))

            # Extract class name (without package)
            simple_name = class_name.split(".")[-1]
            class_info["simple_name"] = simple_name

            # Get superclass
            if ct_class.getSuperclass():
                class_info["superclass"] = ct_class.getSuperclass().getName()

            # Get interfaces
            for interface in ct_class.getInterfaces():
                class_info["interfaces"].append(interface.getName())

            # Get fields
            for field in ct_class.getFields():
                field_info = {
                    "name": field.getName(),
                    "type": field.getType().getName() if field.getType() else "unknown",
                }
                class_info["fields"].append(field_info)

            # Get methods
            for method in ct_class.getMethods():
                method_info = {"name": method.getName(), "signature": method.getSignature()}
                class_info["methods"].append(method_info)

            # Get annotations (if available)
            try:
                RuntimeVisibleAnnotations = ct_class.getAnnotation("Ljava/lang/Deprecated;")
                if RuntimeVisibleAnnotations:
                    class_info["annotations"] = [str(a) for a in RuntimeVisibleAnnotations]
            except Exception:
                pass  # Annotations may not be present

            logger.debug(
                f"Bytecode analysis of {class_name}: found {len(class_info['methods'])} methods, {len(class_info['fields'])} fields"
            )

            return class_info

        except Exception as e:
            logger.warning(f"Failed to analyze bytecode for {class_name}: {e}")
            return {"error": str(e), "name": class_name}

    def _extract_features_from_bytecode(self, class_info: Dict) -> Dict:
        """
        Extract mod features from bytecode-analyzed class information.

        Args:
            class_info: Dictionary from _analyze_bytecode_class

        Returns:
            Dictionary with extracted features
        """
        features = {
            "type": "unknown",
            "name": class_info.get("simple_name", class_info.get("name", "Unknown")),
            "registry_name": self._class_name_to_registry_name(
                class_info.get("simple_name", class_info.get("name", "Unknown"))
            ),
            "methods": [],
            "properties": {},
        }

        try:
            name = class_info.get("simple_name", class_info.get("name", ""))
            superclass = class_info.get("superclass", "")
            interfaces = class_info.get("interfaces", [])

            # Determine type based on class name and superclass
            if "Block" in name or "Block" in superclass:
                features["type"] = "block"
                features["properties"] = self._extract_block_properties_from_bytecode(class_info)
            elif "Item" in name or "Item" in superclass:
                features["type"] = "item"
            elif "Entity" in name or "Entity" in superclass or "Entity" in interfaces:
                features["type"] = "entity"
            elif "TileEntity" in name or "BlockEntity" in superclass:
                features["type"] = "tile_entity"

            # Extract method names
            methods = class_info.get("methods", [])
            features["methods"] = [m.get("name", "") for m in methods]

            return features

        except Exception as e:
            logger.warning(f"Error extracting features from bytecode: {e}")
            return features

    def _extract_block_properties_from_bytecode(self, class_info: Dict) -> Dict:
        """
        Extract block properties from bytecode-analyzed class.

        Args:
            class_info: Dictionary from _analyze_bytecode_class

        Returns:
            Dictionary with extracted block properties
        """
        properties = {
            "material": "stone",
            "hardness": 1.0,
            "explosion_resistance": 0.0,
            "sound_type": "stone",
            "light_level": 0,
            "requires_tool": False,
            "source": "bytecode_estimate",
        }

        try:
            name = class_info.get("simple_name", "").lower()
            methods = class_info.get("methods", [])
            fields = class_info.get("fields", [])

            # Estimate properties based on naming conventions
            if "wood" in name or "plank" in name:
                properties["material"] = "wood"
                properties["sound_type"] = "wood"
                properties["hardness"] = 2.0
            elif "stone" in name or "cobbl" in name:
                properties["material"] = "stone"
                properties["sound_type"] = "stone"
                properties["hardness"] = 1.5
            elif "metal" in name or "iron" in name or "gold" in name or "copper" in name:
                properties["material"] = "metal"
                properties["sound_type"] = "metal"
                properties["hardness"] = 5.0
                properties["explosion_resistance"] = 6.0
            elif "glass" in name:
                properties["material"] = "glass"
                properties["sound_type"] = "glass"
                properties["hardness"] = 0.3
            elif "dirt" in name or "grass" in name or "sand" in name:
                properties["material"] = "dirt"
                properties["sound_type"] = "gravel"
                properties["hardness"] = 0.5

            # Check methods for property hints
            method_names = " ".join([m.get("name", "").lower() for m in methods])

            if "requiresCorrectTool" in method_names or "requires_tool" in method_names:
                properties["requires_tool"] = True

            if "emitsLight" in method_names or "luminance" in method_names:
                properties["light_level"] = 0  # Would need deeper analysis for actual value

            # Check field values (constant hardness/resistance values)
            for field in fields:
                field_name = field.get("name", "").lower()
                if "hardness" in field_name:
                    properties["hardness"] = (
                        1.0  # Estimate, actual would require const pool analysis
                    )
                if "resistance" in field_name:
                    properties["explosion_resistance"] = 3.0  # Estimate

            return properties

        except Exception as e:
            logger.warning(f"Error extracting block properties from bytecode: {e}")
            return properties

    def _analyze_classes_with_bytecode(self, jar, file_list: List[str]) -> Dict:
        """
        Analyze .class files in a JAR using bytecode analysis.

        Args:
            jar: zipfile.ZipFile object
            file_list: List of file paths in the JAR

        Returns:
            Dictionary with extracted features from all analyzed classes
        """
        features = {
            "blocks": [],
            "items": [],
            "entities": [],
            "recipes": [],
            "tile_entities": [],
            "other": [],
        }

        # Filter to only .class files
        class_files = [f for f in file_list if f.endswith(".class")]

        if not class_files:
            logger.info("No .class files found for bytecode analysis")
            return features

        logger.info(f"Starting bytecode analysis of {len(class_files)} class files")

        # Limit to prevent excessive processing time
        max_classes = 50
        analyzed_count = 0

        for class_file in class_files[:max_classes]:
            try:
                # Read class bytecode
                class_data = jar.read(class_file)

                # Convert file path to class name
                # com/example/mymod/TestBlock.class -> com.example.mymod.TestBlock
                class_name = class_file.replace("/", ".").replace(".class", "")

                # Analyze bytecode
                class_info = self._analyze_bytecode_class(class_data, class_name)

                if "error" not in class_info:
                    # Extract features from the analyzed class
                    class_features = self._extract_features_from_bytecode(class_info)

                    # Categorize by type
                    if class_features["type"] == "block":
                        features["blocks"].append(class_features)
                    elif class_features["type"] == "item":
                        features["items"].append(class_features)
                    elif class_features["type"] == "entity":
                        features["entities"].append(class_features)
                    elif class_features["type"] == "tile_entity":
                        features["tile_entities"].append(class_features)
                    else:
                        features["other"].append(class_features)

                    analyzed_count += 1

            except Exception as e:
                logger.debug(f"Could not analyze class {class_file}: {e}")
                continue

        logger.info(
            f"Bytecode analysis complete: analyzed {analyzed_count} classes, found {len(features['blocks'])} blocks, {len(features['items'])} items"
        )

        return features

    def _extract_features_from_ast(self, tree: javalang.ast.Node) -> Dict:
        """
        Extract features from parsed Java AST.

        Args:
            tree: Parsed Java AST

        Returns:
            Dictionary with extracted features
        """
        features = {
            "blocks": [],
            "items": [],
            "entities": [],
            "recipes": [],
            "dimensions": [],
            "gui": [],
            "machinery": [],
            "commands": [],
            "events": [],
        }

        try:
            # Extract class declarations
            for path, node in tree:
                if isinstance(node, javalang.tree.ClassDeclaration):
                    # Check if it's a block class
                    if "Block" in node.name and not node.name.startswith("Abstract"):
                        block_info = {
                            "name": node.name,
                            "registry_name": self._class_name_to_registry_name(node.name),
                            "methods": [method.name for method in node.methods],
                            "properties": self._extract_block_properties_from_ast(node),
                        }
                        features["blocks"].append(block_info)
                        logger.debug(
                            f"Extracted block: {node.name} with properties: {block_info['properties']}"
                        )

                    # Check if it's an item class
                    elif "Item" in node.name and not node.name.startswith("Abstract"):
                        features["items"].append(
                            {
                                "name": node.name,
                                "registry_name": self._class_name_to_registry_name(node.name),
                                "methods": [method.name for method in node.methods],
                            }
                        )

                    # Check if it's an entity class
                    elif "Entity" in node.name and not node.name.startswith("Abstract"):
                        features["entities"].append(
                            {
                                "name": node.name,
                                "registry_name": self._class_name_to_registry_name(node.name),
                                "methods": [method.name for method in node.methods],
                            }
                        )

                # Extract method declarations for recipes, commands, events
                elif isinstance(node, javalang.tree.MethodDeclaration):
                    method_name = node.name

                    # Check for recipe-related methods
                    if any(
                        keyword in method_name.lower() for keyword in ["recipe", "craft", "smelt"]
                    ):
                        features["recipes"].append(
                            {
                                "name": method_name,
                                "parameters": [param.type.name for param in node.parameters]
                                if node.parameters
                                else [],
                            }
                        )

                    # Check for command-related methods
                    if any(keyword in method_name.lower() for keyword in ["command", "execute"]):
                        features["commands"].append(
                            {
                                "name": method_name,
                                "parameters": [param.type.name for param in node.parameters]
                                if node.parameters
                                else [],
                            }
                        )

                    # Check for event-related methods
                    if any(
                        keyword in method_name.lower() for keyword in ["event", "trigger", "handle"]
                    ):
                        features["events"].append(
                            {
                                "name": method_name,
                                "parameters": [param.type.name for param in node.parameters]
                                if node.parameters
                                else [],
                            }
                        )

            return features
        except Exception as e:
            logger.warning(f"Error extracting features from AST: {e}")
            return features

    def _extract_block_properties_from_ast(
        self, class_node: javalang.tree.ClassDeclaration
    ) -> Dict:
        """
        Extract block properties from a Block class AST node.

        Analyzes constructor and method calls to extract:
        - Material type (METAL, STONE, WOOD, etc.)
        - Hardness value
        - Explosion resistance
        - Sound type
        - Light emission
        - Tool requirements

        Args:
            class_node: ClassDeclaration node for a Block class

        Returns:
            Dictionary with extracted block properties
        """
        properties = {
            "material": "stone",  # Default
            "hardness": 1.0,
            "explosion_resistance": 0.0,
            "sound_type": "stone",
            "light_level": 0,
            "requires_tool": False,
        }

        try:
            # Look for constructor calls and method chains
            for path, node in javalang.ast.walk_tree(class_node):
                # Look for method invocations like .strength(), .sound(), etc.
                if isinstance(node, javalang.tree.MethodInvocation):
                    method_name = node.member.lower()

                    # Extract hardness and resistance from .strength(hardness, resistance)
                    if method_name == "strength":
                        if node.arguments and len(node.arguments) >= 1:
                            # Try to extract hardness value
                            hardness_arg = node.arguments[0]
                            if hasattr(hardness_arg, "value"):
                                try:
                                    properties["hardness"] = float(hardness_arg.value.rstrip("Ff"))
                                except (ValueError, AttributeError):
                                    pass
                            if len(node.arguments) >= 2:
                                resistance_arg = node.arguments[1]
                                if hasattr(resistance_arg, "value"):
                                    try:
                                        properties["explosion_resistance"] = float(
                                            resistance_arg.value.rstrip("Ff")
                                        )
                                    except (ValueError, AttributeError):
                                        pass

                    # Extract sound type from .sound(SoundType.XXX)
                    elif method_name == "sound":
                        if node.arguments and len(node.arguments) >= 1:
                            sound_arg = node.arguments[0]
                            if hasattr(sound_arg, "qualifier") and hasattr(sound_arg, "member"):
                                # SoundType.COPPER -> 'copper'
                                sound_name = (
                                    sound_arg.member.lower() if sound_arg.member else "stone"
                                )
                                properties["sound_type"] = sound_name

                    # Check for tool requirements
                    elif "requirescorrecttool" in method_name or "requires_tool" in method_name:
                        properties["requires_tool"] = True

                    # Extract light level from .lightLevel() or .luminance()
                    elif method_name in ["lightlevel", "luminance", "emitslight"]:
                        if node.arguments and len(node.arguments) >= 1:
                            light_arg = node.arguments[0]
                            if hasattr(light_arg, "value"):
                                try:
                                    properties["light_level"] = int(
                                        float(light_arg.value.rstrip("Ff"))
                                    )
                                except (ValueError, AttributeError):
                                    pass

                # Look for Material.XXX in method calls like Properties.of(Material.METAL)
                elif isinstance(node, javalang.tree.MemberReference):
                    # Check for Material.XXX pattern
                    if hasattr(node, "qualifier") and node.qualifier == "Material":
                        material_name = node.member.lower() if node.member else "stone"
                        properties["material"] = material_name

            logger.debug(f"Extracted block properties: {properties}")
            return properties

        except Exception as e:
            logger.warning(f"Error extracting block properties from AST: {e}")
            return properties

    def _extract_mod_metadata_from_ast(self, tree: javalang.ast.Node) -> Dict:
        """
        Extract mod metadata from parsed Java AST.

        Improved to handle more annotation types and complex annotation structures.

        Args:
            tree: Parsed Java AST

        Returns:
            Dictionary with extracted metadata
        """
        metadata = {}
        annotations_found = []

        try:
            # Look for annotations that might indicate mod information
            for path, node in tree:
                if isinstance(node, javalang.tree.Annotation):
                    annotation_data = self._extract_annotation_data(node)
                    annotations_found.append(annotation_data)

                    # Check for common mod annotations
                    if node.name in ["Mod", "ModInstance", "Instance", "ModEventBusSubscriber"]:
                        # Extract the annotation element
                        if hasattr(node, "element") and node.element is not None:
                            element = node.element
                            # Handle Literal values correctly by extracting the actual value
                            if hasattr(element, "value"):
                                # For string literals, also strip quotes
                                if isinstance(element.value, str):
                                    metadata["value"] = element.value.strip('"')
                                else:
                                    metadata["value"] = element.value
                            else:
                                # Handle complex annotation elements (key-value pairs)
                                metadata["value"] = str(element)

                    # Handle other common Minecraft/Forge annotations
                    elif node.name in ["SubscribeEvent", "Mod.EventBusSubscriber"]:
                        metadata["event_subscriber"] = True

                    elif node.name == "ObjectHolder":
                        # Extract ObjectHolder annotation for registry entries
                        if hasattr(node, "element") and node.element:
                            obj_holder = self._extract_annotation_element(node.element)
                            if obj_holder:
                                metadata["object_holder"] = obj_holder

            # Store all annotations found for comprehensive analysis
            if annotations_found:
                metadata["all_annotations"] = annotations_found

            return metadata
        except Exception as e:
            logger.warning(f"Error extracting metadata from AST: {e}")
            return metadata

    def _extract_annotation_data(self, node: javalang.tree.Annotation) -> Dict:
        """
        Extract comprehensive data from an annotation node.

        Args:
            node: Annotation AST node

        Returns:
            Dictionary with annotation data
        """
        annotation_info = {
            "name": node.name if hasattr(node, "name") else "unknown",
            "type": "unknown",
        }

        try:
            # Determine annotation type
            if node.name:
                name_lower = node.name.lower()
                if name_lower in ["mod", "modinstance", "modid"]:
                    annotation_info["type"] = "mod_id"
                elif "eventbus" in name_lower or "subscribe" in name_lower:
                    annotation_info["type"] = "event_subscriber"
                elif "objectholder" in name_lower:
                    annotation_info["type"] = "object_holder"
                elif name_lower.startswith("inject") or name_lower.startswith("redirect"):
                    annotation_info["type"] = "mixin"

            # Extract annotation element value(s)
            if hasattr(node, "element") and node.element:
                element_value = self._extract_annotation_element(node.element)
                if element_value:
                    annotation_info["value"] = element_value

            return annotation_info

        except Exception as e:
            logger.debug(f"Error extracting annotation data: {e}")
            return annotation_info

    def _extract_annotation_element(self, element) -> Optional[Any]:
        """
        Extract value from an annotation element, handling various formats.

        Handles:
        - Simple literal values
        - Key-value pairs (element-value pairs)
        - Nested annotations
        - Arrays

        Args:
            element: Annotation element node

        Returns:
            Extracted value or None
        """
        if element is None:
            return None

        try:
            # Direct value attribute
            if hasattr(element, "value"):
                value = element.value
                if isinstance(value, str):
                    return value.strip('"')
                return value

            # Element value pair (for key="value" annotations)
            if hasattr(element, "element") and hasattr(element, "value"):
                # This is an ElementValuePair
                key = element.element if hasattr(element, "element") else "unknown"
                val = element.value

                if isinstance(val, str):
                    return {key: val.strip('"')}
                elif hasattr(val, "value"):
                    val_str = val.value
                    if isinstance(val_str, str):
                        return {key: val_str.strip('"')}
                    return {key: val_str}
                return {key: str(val)}

            # Literal node
            if hasattr(element, "literal"):
                return str(element.literal).strip('"')

            # For arrays, collect all values
            if hasattr(element, "values"):
                values = []
                for val in element.values:
                    if hasattr(val, "value"):
                        val_str = val.value
                        if isinstance(val_str, str):
                            values.append(val_str.strip('"'))
                        else:
                            values.append(val_str)
                    elif hasattr(val, "literal"):
                        values.append(str(val.literal).strip('"'))
                return values if values else None

            return str(element)

        except Exception as e:
            logger.debug(f"Error extracting annotation element: {e}")
            return None

    def _analyze_dependencies_from_ast(self, tree: javalang.ast.Node) -> List[Dict]:
        """
        Analyze dependencies from parsed Java AST.

        Improved to also detect reflection usage and API patterns.

        Args:
            tree: Parsed Java AST

        Returns:
            List of dependency information
        """
        dependencies = []
        reflection_uses = []

        try:
            # Extract import statements
            if hasattr(tree, "imports"):
                for imp in tree.imports:
                    if hasattr(imp, "path"):
                        dependencies.append({"import": imp.path, "type": "explicit"})

            # Extract method calls that might indicate dependencies
            for path, node in tree:
                if isinstance(node, javalang.tree.MethodInvocation):
                    if hasattr(node, "qualifier") and node.qualifier:
                        # Check if this is a call to a library
                        qualifier_parts = node.qualifier.split(".")
                        if len(qualifier_parts) > 1:
                            dependencies.append(
                                {
                                    "import": node.qualifier,
                                    "type": "implicit",
                                    "method": node.member,
                                }
                            )

                    # Detect reflection usage patterns
                    method_name = node.member.lower() if hasattr(node, "member") else ""
                    if method_name in [
                        "class_forname",
                        "class",
                        "getmethod",
                        "getfield",
                        "getdeclaredmethod",
                        "getdeclaredfield",
                        "newinstance",
                        "invoke",
                        "setaccessible",
                        "getclass",
                    ]:
                        reflection_uses.append(
                            {
                                "type": "reflection",
                                "method": method_name,
                                "qualifier": node.qualifier if hasattr(node, "qualifier") else None,
                                "static_analysis": "Note: Reflection usage detected. Static analysis has limited visibility into dynamically accessed members.",
                            }
                        )

            # Detect reflection patterns in string literals (Class.forName("..."))
            if hasattr(tree, "children"):
                for child in tree.children:
                    if isinstance(child, str):
                        # Check for class name patterns in string literals
                        if "net." in child or "com." in child or "org." in child:
                            reflection_uses.append(
                                {
                                    "type": "string_reflection",
                                    "pattern": "Potential class name in string",
                                    "static_analysis": "Dynamic class loading detected in string. Full analysis requires runtime information.",
                                }
                            )

            # Combine dependencies with reflection analysis
            if reflection_uses:
                dependencies.extend(reflection_uses)

            return dependencies
        except Exception as e:
            logger.warning(f"Error analyzing dependencies from AST: {e}")
            return dependencies

    def _detect_reflection_in_mods(self, tree: javalang.ast.Node) -> Dict:
        """
        Detect reflection usage in mods through static analysis.

        This helps identify dynamically accessed classes and methods that
        cannot be fully analyzed statically.

        Args:
            tree: Parsed Java AST

        Returns:
            Dictionary with reflection detection results
        """
        reflection_info = {
            "detected": False,
            "class_forname": [],
            "method_reflection": [],
            "field_reflection": [],
            "warnings": [],
        }

        try:
            for path, node in tree:
                # Check for Class.forName calls
                if isinstance(node, javalang.tree.MethodInvocation):
                    member = node.member.lower() if hasattr(node, "member") else ""
                    qualifier = node.qualifier.lower() if hasattr(node, "qualifier") and node.qualifier else ""

                    if member == "forname" and qualifier == "class":
                        reflection_info["detected"] = True
                        # Try to extract the class name argument
                        if node.arguments and len(node.arguments) > 0:
                            arg = node.arguments[0]
                            class_name = self._extract_string_value(arg)
                            if class_name:
                                reflection_info["class_forname"].append(class_name)

                    # Check for getMethod, getDeclaredMethod
                    elif member in ["getmethod", "getdeclaredmethod"]:
                        reflection_info["detected"] = True
                        reflection_info["method_reflection"].append(
                            {
                                "method": member,
                                "qualifier": node.qualifier if hasattr(node, "qualifier") else None,
                            }
                        )

                    # Check for getField, getDeclaredField
                    elif member in ["getfield", "getdeclaredfield"]:
                        reflection_info["detected"] = True
                        reflection_info["field_reflection"].append(
                            {
                                "method": member,
                                "qualifier": node.qualifier if hasattr(node, "qualifier") else None,
                            }
                        )

                    # Check for setAccessible
                    elif member == "setaccessible":
                        reflection_info["detected"] = True

                # Check for .class literal (ClassName.class)
                elif isinstance(node, javalang.tree.ClassReference):
                    # This is normal usage, not reflection
                    pass

                # Check for type cast to Class<?>
                elif isinstance(node, javalang.tree.Cast):
                    if hasattr(node, "type") and hasattr(node.type, "name"):
                        if node.type.name == "Class":
                            reflection_info["warnings"].append(
                                "Type cast to Class detected - may indicate reflection usage"
                            )

            if reflection_info["detected"]:
                logger.debug(
                    f"Reflection detected in mod: {len(reflection_info['class_forname'])} Class.forName, "
                    f"{len(reflection_info['method_reflection'])} method reflections"
                )

            return reflection_info

        except Exception as e:
            logger.warning(f"Error detecting reflection: {e}")
            return reflection_info

    def _extract_string_value(self, node) -> Optional[str]:
        """
        Extract string value from an AST node.

        Args:
            node: AST node that may contain a string literal

        Returns:
            String value or None
        """
        if node is None:
            return None

        # Direct string value
        if hasattr(node, "value") and isinstance(node.value, str):
            return node.value.strip("\"'")

        # Literal node
        if hasattr(node, "literal"):
            return str(node.literal).strip("\"'")

        return None

    def _analyze_jar_file(self, jar_path: str, result: dict) -> dict:
        """Analyze a JAR file for mod information"""
        try:
            with zipfile.ZipFile(jar_path, "r") as jar:
                file_list = jar.namelist()

                # Detect framework
                framework = self._detect_framework_from_jar_files(file_list, jar)
                result["mod_info"]["framework"] = framework

                # Extract mod info from metadata files
                mod_info = self._extract_mod_info_from_jar(jar, file_list)
                result["mod_info"].update(mod_info)

                # Analyze assets
                result["assets"] = self._analyze_assets_from_jar(file_list)

                # Analyze structure
                result["structure"] = {"files": len(file_list), "type": "jar"}

                # Extract Java source files and analyze with AST
                java_sources = [f for f in file_list if f.endswith(".java")]
                if java_sources:
                    logger.info(f"Found {len(java_sources)} Java source files, analyzing with AST")

                    # Optimized single-pass analysis
                    batch_results = self._analyze_sources_batch(jar, java_sources)
                    result["features"] = batch_results["features"]
                    result["dependencies"] = batch_results["dependencies"]
                else:
                    logger.info("No Java source files found in JAR, attempting bytecode analysis")

                    # First try bytecode analysis if javassist is available
                    if JAVASSIST_AVAILABLE:
                        bytecode_features = self._analyze_classes_with_bytecode(jar, file_list)
                        if bytecode_features and (
                            bytecode_features.get("blocks")
                            or bytecode_features.get("items")
                            or bytecode_features.get("entities")
                        ):
                            logger.info(
                                f"Bytecode analysis found {len(bytecode_features['blocks'])} blocks, {len(bytecode_features['items'])} items"
                            )
                            result["features"] = bytecode_features
                        else:
                            logger.info(
                                "Bytecode analysis yielded no results, falling back to class name analysis"
                            )
                            result["features"] = self._extract_features_from_classes(file_list)
                    else:
                        logger.info("Javassist not available, using class name-based analysis")
                        # Extract features from class names (existing approach)
                        result["features"] = self._extract_features_from_classes(file_list)

        except Exception as e:
            result["errors"].append(f"Error analyzing JAR file: {str(e)}")

        return result

    def _extract_features_from_class_name(self, class_name: str) -> Dict:
        """
        Extract features from a single class name (fallback for parse failures).

        Args:
            class_name: Name of the Java class (without .java extension)

        Returns:
            Dictionary with extracted features
        """
        features = {
            "blocks": [],
            "items": [],
            "entities": [],
            "recipes": [],
            "dimensions": [],
            "gui": [],
            "machinery": [],
            "commands": [],
            "events": [],
        }

        try:
            # Use existing pattern matching for feature detection
            for feature_type, patterns in self.feature_patterns.items():
                for pattern in patterns:
                    if pattern.lower() in class_name.lower():
                        feature_entry = {
                            "name": class_name,
                            "registry_name": self._class_name_to_registry_name(class_name),
                        }
                        features[feature_type].append(feature_entry)
                        break  # Only add to first matching category

            return features
        except Exception as e:
            logger.warning(f"Error extracting features from class name {class_name}: {e}")
            return features

    def _extract_features_from_classes(self, file_list: List[str]) -> Dict:
        """
        Extract features from class file names (fallback method).

        Args:
            file_list: List of files in the JAR

        Returns:
            Dictionary with extracted features
        """
        features = {
            "blocks": [],
            "items": [],
            "entities": [],
            "recipes": [],
            "dimensions": [],
            "gui": [],
            "machinery": [],
            "commands": [],
            "events": [],
        }

        try:
            for file_path in file_list:
                if file_path.endswith(".class"):
                    class_name = Path(file_path).stem

                    # Use existing pattern matching for feature detection
                    for feature_type, patterns in self.feature_patterns.items():
                        for pattern in patterns:
                            if pattern.lower() in class_name.lower():
                                feature_entry = {
                                    "name": class_name,
                                    "registry_name": self._class_name_to_registry_name(class_name),
                                }
                                features[feature_type].append(feature_entry)
                                break  # Only add to first matching category

            return features
        except Exception as e:
            logger.warning(f"Error extracting features from classes: {e}")
            return features

    def _detect_framework_from_jar_files(self, file_list: list, jar: zipfile.ZipFile) -> str:
        """Detect modding framework from JAR file contents"""
        try:
            # Check for framework-specific files and patterns
            for framework, indicators in self.framework_indicators.items():
                for indicator in indicators:
                    if any(indicator in file_name for file_name in file_list):
                        return framework

            # Check file contents if available
            for file_name in file_list:
                if file_name.endswith(".json") and "mod" in file_name.lower():
                    try:
                        content = jar.read(file_name).decode("utf-8")
                        for framework, indicators in self.framework_indicators.items():
                            for indicator in indicators:
                                if indicator in content:
                                    return framework
                    except (UnicodeDecodeError, KeyError) as e:
                        logger.debug(f"Could not read {file_name}: {e}")
                        continue

            return "unknown"
        except Exception as e:
            logger.warning(f"Error detecting framework: {e}")
            return "unknown"

    def _extract_mod_info_from_jar(self, jar: zipfile.ZipFile, file_list: list) -> dict:
        """Extract mod information from metadata files"""
        mod_info = {}

        # Look for Fabric mod.json
        if "fabric.mod.json" in file_list:
            try:
                content = jar.read("fabric.mod.json").decode("utf-8")
                fabric_data = json.loads(content)
                mod_info["name"] = fabric_data.get("id", fabric_data.get("name", "unknown")).lower()
                mod_info["version"] = fabric_data.get("version", "1.0.0")
                return mod_info
            except (json.JSONDecodeError, UnicodeDecodeError, KeyError) as e:
                logger.debug(f"Could not parse fabric.mod.json: {e}")
                pass

        # Look for Quilt mod.json
        if "quilt.mod.json" in file_list:
            try:
                content = jar.read("quilt.mod.json").decode("utf-8")
                quilt_data = json.loads(content)
                mod_info["name"] = quilt_data.get("quilt_loader", {}).get("id", "unknown").lower()
                mod_info["version"] = quilt_data.get("quilt_loader", {}).get("version", "1.0.0")
                return mod_info
            except (json.JSONDecodeError, UnicodeDecodeError, KeyError) as e:
                logger.debug(f"Could not parse quilt.mod.json: {e}")
                pass

        # Look for Forge mcmod.info
        if "mcmod.info" in file_list:
            try:
                content = jar.read("mcmod.info").decode("utf-8")
                mcmod_data = json.loads(content)
                if isinstance(mcmod_data, list) and len(mcmod_data) > 0:
                    mod_data = mcmod_data[0]
                    mod_info["name"] = mod_data.get("modid", "unknown").lower()
                    mod_info["version"] = mod_data.get("version", "1.0.0")
                    return mod_info
            except (json.JSONDecodeError, UnicodeDecodeError, KeyError) as e:
                logger.debug(f"Could not parse mcmod.info: {e}")
                pass

        # Look for mods.toml
        for file_name in file_list:
            if file_name.endswith("mods.toml"):
                try:
                    content = jar.read(file_name).decode("utf-8")
                    # Simple TOML parsing for modId
                    for line in content.split("\n"):
                        if "modId" in line and "=" in line:
                            mod_id = line.split("=")[1].strip().strip("\"'")
                            mod_info["name"] = mod_id.lower()
                            break
                    return mod_info
                except Exception as e:
                    logger.debug(f"Could not parse mods.toml: {e}")
                    pass

        return mod_info

    def _analyze_assets_from_jar(self, file_list: list) -> dict:
        """Analyze assets in the JAR file"""
        assets = {"textures": [], "models": [], "sounds": [], "other": []}

        for file_name in file_list:
            if "/textures/" in file_name and file_name.endswith((".png", ".jpg", ".jpeg")):
                assets["textures"].append(file_name)
            elif "/models/" in file_name and file_name.endswith((".json", ".obj")):
                assets["models"].append(file_name)
            elif "/sounds/" in file_name and file_name.endswith((".ogg", ".wav")):
                assets["sounds"].append(file_name)
            elif any(
                file_name.endswith(ext) for ext in [".png", ".jpg", ".ogg", ".wav", ".obj", ".mtl"]
            ):
                assets["other"].append(file_name)

        return assets

    def _analyze_source_directory(self, source_path: str, result: dict) -> dict:
        """Analyze a source directory for mod information"""
        try:
            # This would be implemented for source analysis
            result["mod_info"]["framework"] = "source"
            result["structure"] = {"type": "source", "path": source_path}
        except Exception as e:
            result["errors"].append(f"Error analyzing source directory: {str(e)}")

        return result

    @tool
    @staticmethod
    def analyze_mod_structure_tool(mod_data: Union[str, Dict]) -> str:
        """
        Analyze the overall structure of a Java mod.

        Args:
            mod_data: JSON string containing mod file path and analysis options

        Returns:
            JSON string with structural analysis results
        """
        agent = JavaAnalyzerAgent.get_instance()

        def _determine_mod_type_and_framework(mod_path: str) -> Dict[str, str]:
            """Determine mod type (jar, source, etc.) and framework (forge, fabric, etc.)"""
            if mod_path.endswith((".jar", ".zip")):
                mod_type = "jar"
                framework = _detect_framework_from_jar(mod_path)
            elif os.path.isdir(mod_path):
                mod_type = "source"
                framework = _detect_framework_from_source(mod_path)
            else:
                mod_type = "unknown"
                framework = "unknown"

            return {"type": mod_type, "framework": framework}

        def _detect_framework_from_jar(jar_path: str) -> str:
            """Detect modding framework from JAR file contents"""
            try:
                with zipfile.ZipFile(jar_path, "r") as jar:
                    file_list = jar.namelist()

                    # Check for framework-specific files and patterns
                    for framework, indicators in agent.framework_indicators.items():
                        for indicator in indicators:
                            if any(indicator in file_name for file_name in file_list):
                                return framework

                    # Check file contents if available
                    for file_name in file_list:
                        if file_name.endswith(".json") and "mod" in file_name.lower():
                            try:
                                content = jar.read(file_name).decode("utf-8")
                                for framework, indicators in agent.framework_indicators.items():
                                    for indicator in indicators:
                                        if indicator in content:
                                            return framework
                            except (UnicodeDecodeError, KeyError) as e:
                                logger.debug(f"Could not read {file_name}: {e}")
                                continue

                    return "unknown"
            except Exception as e:
                logger.warning(f"Error in framework detection tool: {e}")
                return "unknown"

        def _detect_framework_from_source(source_path: str) -> str:
            """Detect modding framework from source directory"""
            try:
                # Check for framework-specific files
                for root, dirs, files in os.walk(source_path):
                    for file_name in files:
                        for framework, indicators in agent.framework_indicators.items():
                            if file_name in indicators:
                                return framework

                    # Check file contents
                    for file_name in files:
                        if file_name.endswith(".java"):
                            try:
                                file_path = os.path.join(root, file_name)
                                with open(file_path, "r", encoding="utf-8") as f:
                                    content = f.read()
                                    for framework, indicators in agent.framework_indicators.items():
                                        for indicator in indicators:
                                            if indicator in content:
                                                return framework
                            except (UnicodeDecodeError, FileNotFoundError, PermissionError) as e:
                                logger.debug(f"Could not read {file_path}: {e}")
                                continue

                return "unknown"
            except Exception as e:
                logger.warning(f"Error in source framework detection: {e}")
                return "unknown"

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
                            # Java class file
                            package_path = "/".join(file_name.split("/")[:-1])
                            if package_path not in structure["package_structure"]:
                                structure["package_structure"][package_path] = []
                            structure["package_structure"][package_path].append(file_name)

                            # Check if it's a main class
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

        def _analyze_unknown_structure(mod_path: str, analysis_depth: str) -> Dict:
            """Analyze unknown file type structure"""
            return {
                "type": "unknown",
                "path": mod_path,
                "size": os.path.getsize(mod_path) if os.path.exists(mod_path) else 0,
                "analysis_note": "Unknown file type - limited analysis available",
            }

        def _create_file_inventory(mod_path: str, mod_type: str) -> Dict:
            """Create comprehensive file inventory"""
            inventory = {"by_type": {}, "by_size": {}, "total_count": 0, "total_size": 0}

            if mod_type == "jar":
                inventory = _inventory_jar_files(mod_path)
            elif mod_type == "source":
                inventory = _inventory_source_files(mod_path)

            return inventory

        def _inventory_jar_files(jar_path: str) -> Dict:
            """Create inventory of JAR file contents"""
            inventory = {"by_type": {}, "by_size": {}, "total_count": 0, "total_size": 0}

            try:
                with zipfile.ZipFile(jar_path, "r") as jar:
                    for info in jar.infolist():
                        if not info.is_dir():
                            file_ext = Path(info.filename).suffix.lower()
                            file_size = info.file_size

                            inventory["by_type"][file_ext] = (
                                inventory["by_type"].get(file_ext, 0) + 1
                            )
                            inventory["total_count"] += 1
                            inventory["total_size"] += file_size

                            # Categorize by size
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

            return inventory

        def _inventory_source_files(source_path: str) -> Dict:
            """Create inventory of source directory contents"""
            inventory = {"by_type": {}, "by_size": {}, "total_count": 0, "total_size": 0}

            try:
                for root, dirs, files in os.walk(source_path):
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        file_ext = Path(file_name).suffix.lower()
                        file_size = os.path.getsize(file_path)

                        inventory["by_type"][file_ext] = inventory["by_type"].get(file_ext, 0) + 1
                        inventory["total_count"] += 1
                        inventory["total_size"] += file_size

                        # Categorize by size
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

            # Factor in number of files
            total_files = file_inventory.get("total_count", 0)
            if total_files > 100:
                score += 2
                factors.append("Large number of files")
            elif total_files > 50:
                score += 1
                factors.append("Moderate number of files")

            # Factor in package structure complexity (for JARs)
            if "package_structure" in structure:
                packages = len(structure["package_structure"])
                if packages > 10:
                    score += 2
                    factors.append("Complex package structure")
                elif packages > 5:
                    score += 1
                    factors.append("Moderate package structure")

            # Factor in resource files
            resource_count = len(structure.get("resource_files", []))
            if resource_count > 50:
                score += 2
                factors.append("Many resource files")
            elif resource_count > 20:
                score += 1
                factors.append("Moderate resource files")

            # Determine overall complexity
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

        def _is_main_class(class_path: str) -> bool:
            """Check if a class is a main mod class

            More robust detection of main mod classes by examining:
            1. Package structure for mod-related naming
            2. Class name for mod-related keywords
            3. Position in package hierarchy (shallower classes more likely to be main)
            """
            # More robust detection of main mod classes
            class_name = class_path.split("/")[-1].replace(".class", "")
            package_path = "/".join(class_path.split("/")[:-1])

            # Check for common mod main class patterns
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

            # Check if it's in a likely mod package structure
            package_parts = package_path.split("/")
            has_mod_package = any(
                "mod" in part.lower() or "plugin" in part.lower() for part in package_parts if part
            )

            # Check if class name contains mod indicators
            has_mod_name = any(indicator in class_name for indicator in mod_indicators)

            # Classes closer to root are more likely to be main classes
            is_shallow = class_path.count("/") <= 3

            return (has_mod_package and has_mod_name) or is_shallow

        def _generate_analysis_recommendations(analysis: Dict) -> List[str]:
            """Generate recommendations based on analysis"""
            return ["Complete feature extraction for detailed conversion planning"]

        try:
            logger.info(f"Current working directory in JavaAnalyzerAgent: {os.getcwd()}")
            # Handle both JSON string and direct file path inputs
            if isinstance(mod_data, str):
                try:
                    data = json.loads(mod_data)
                    # Check if CrewAI wrapped the parameter
                    if "mod_data" in data:
                        mod_path = data["mod_data"]
                        analysis_depth = data.get("analysis_depth", "standard")
                    else:
                        mod_path = data.get("mod_path", "")
                        analysis_depth = data.get("analysis_depth", "standard")
                except json.JSONDecodeError:
                    # If JSON parsing fails, treat as direct file path
                    mod_path = mod_data
                    analysis_depth = "standard"
            else:
                # Handle dict or other object types
                data = mod_data if isinstance(mod_data, dict) else {"mod_path": str(mod_data)}
                # Check if CrewAI wrapped the parameter
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

            # Determine mod type and framework
            mod_info = _determine_mod_type_and_framework(mod_path)
            analysis_results["mod_type"] = mod_info["type"]
            analysis_results["framework"] = mod_info["framework"]

            # Analyze structure based on mod type
            if mod_info["type"] == "jar":
                structure = _analyze_jar_structure(mod_path, analysis_depth)
            elif mod_info["type"] == "source":
                structure = _analyze_source_structure(mod_path, analysis_depth)
            else:
                structure = _analyze_unknown_structure(mod_path, analysis_depth)

            analysis_results["structure_analysis"] = structure

            # Create file inventory
            file_inventory = _create_file_inventory(mod_path, mod_info["type"])
            analysis_results["file_inventory"] = file_inventory

            # Assess complexity
            complexity = _assess_mod_complexity(structure, file_inventory)
            analysis_results["complexity_assessment"] = complexity

            response = {
                "success": True,
                "analysis_results": analysis_results,
                "recommendations": _generate_analysis_recommendations(analysis_results),
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

    @tool
    @staticmethod
    def extract_mod_metadata_tool(mod_data: Union[str, Dict]) -> str:
        """
        Extract metadata from mod files.

        Args:
            mod_data: JSON string containing mod file path

        Returns:
            JSON string with metadata
        """
        agent = JavaAnalyzerAgent.get_instance()

        def _extract_jar_metadata(jar_path: str) -> Dict:
            """Extract metadata from JAR file"""
            metadata = {}

            try:
                with zipfile.ZipFile(jar_path, "r") as jar:
                    # Look for metadata files
                    for metadata_file in agent.file_patterns["metadata_files"]:
                        if metadata_file in jar.namelist():
                            try:
                                content = jar.read(metadata_file).decode("utf-8")
                                if metadata_file.endswith(".json"):
                                    metadata.update(json.loads(content))
                                else:
                                    # Handle other format parsing as needed
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

        def _summarize_metadata(metadata: Dict) -> Dict:
            """Summarize extracted metadata"""
            return {"summary": "Metadata extraction completed"}

        try:
            # Handle both JSON string and direct file path inputs
            if isinstance(mod_data, str):
                try:
                    data = json.loads(mod_data)
                    # Check if CrewAI wrapped the parameter
                    if "mod_data" in data:
                        mod_path = data["mod_data"]
                    else:
                        mod_path = data.get("mod_path", "")
                except json.JSONDecodeError:
                    # If JSON parsing fails, treat as direct file path
                    mod_path = mod_data
                    data = {"mod_path": mod_path}
            else:
                # Handle dict or other object types
                data = mod_data if isinstance(mod_data, dict) else {"mod_path": str(mod_data)}
                # Check if CrewAI wrapped the parameter
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

            # Extract metadata based on mod type
            if mod_path.endswith((".jar", ".zip")):
                metadata = _extract_jar_metadata(mod_path)
            else:
                metadata = _extract_source_metadata(mod_path)

            metadata_results.update(metadata)

            response = {
                "success": True,
                "metadata": metadata_results,
                "extraction_summary": _summarize_metadata(metadata_results),
            }

            logger.info(f"Extracted metadata from: {mod_path}")
            return json.dumps(response)

        except Exception as e:
            error_response = {"success": False, "error": f"Failed to extract metadata: {str(e)}"}
            logger.error(f"Metadata extraction error: {e}")
            return json.dumps(error_response)

    @tool
    @staticmethod
    def identify_features_tool(mod_data: Union[str, Dict]) -> str:
        """
        Identify features in the mod.

        Args:
            mod_data: JSON string containing analysis data

        Returns:
            JSON string with identified features
        """
        agent = JavaAnalyzerAgent.get_instance()

        def _extract_features_from_jar(jar_path: str, extraction_mode: str) -> List[Dict]:
            """Extract features from JAR file"""
            features = []

            try:
                with zipfile.ZipFile(jar_path, "r") as jar:
                    for file_info in jar.infolist():
                        if file_info.filename.endswith(".class"):
                            # Simplified feature extraction from class names
                            class_name = Path(file_info.filename).stem
                            detected_features = _detect_features_from_class_name(class_name)
                            features.extend(detected_features)

            except Exception as e:
                logger.warning(f"Error extracting features from JAR: {e}")

            return features

        def _extract_features_from_source(source_path: str, extraction_mode: str) -> List[Dict]:
            """Extract features from source directory"""
            features = []

            try:
                for root, dirs, files in os.walk(source_path):
                    for file_name in files:
                        if file_name.endswith(".java"):
                            file_path = os.path.join(root, file_name)
                            try:
                                with open(file_path, "r", encoding="utf-8") as f:
                                    content = f.read()
                                    detected_features = _detect_features_from_content(
                                        content, file_name
                                    )
                                    features.extend(detected_features)
                            except Exception as e:
                                logger.warning(f"Error reading {file_path}: {e}")

            except Exception as e:
                logger.warning(f"Error extracting features from source: {e}")

            return features

        def _detect_features_from_class_name(class_name: str) -> List[Dict]:
            """Detect features based on class name patterns"""
            features = []

            for feature_type, patterns in agent.feature_patterns.items():
                for pattern in patterns:
                    if pattern.lower() in class_name.lower():
                        features.append(
                            {
                                "feature_id": f"{feature_type}_{class_name.lower()}",
                                "feature_type": feature_type,
                                "name": class_name,
                                "source": "class_name_analysis",
                                "confidence": "medium",
                                "original_data": {"class_name": class_name},
                            }
                        )
                        break  # Only add one feature per class

            return features

        def _detect_features_from_content(content: str, file_name: str) -> List[Dict]:
            """Detect features from source file content"""
            features = []

            for feature_type, patterns in agent.feature_patterns.items():
                for pattern in patterns:
                    if pattern in content:
                        features.append(
                            {
                                "feature_id": f"{feature_type}_{Path(file_name).stem.lower()}",
                                "feature_type": feature_type,
                                "name": f"{feature_type.title()} in {Path(file_name).stem}",
                                "source": "content_analysis",
                                "confidence": "high",
                                "original_data": {
                                    "file_name": file_name,
                                    "detected_pattern": pattern,
                                },
                            }
                        )
                        break  # Only add one feature per type per file

            return features

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

        def _generate_feature_summary(results: Dict) -> Dict:
            """Generate feature summary"""
            return {"summary": f"Identified {len(results.get('identified_features', []))} features"}

        try:
            # Handle both JSON string and direct file path inputs
            if isinstance(mod_data, str):
                try:
                    data = json.loads(mod_data)
                    # Check if CrewAI wrapped the parameter
                    if "mod_data" in data:
                        mod_path = data["mod_data"]
                        data.get("structure_analysis", {})
                        extraction_mode = data.get("extraction_mode", "comprehensive")
                    else:
                        mod_path = data.get("mod_path", "")
                        data.get("structure_analysis", {})
                        extraction_mode = data.get("extraction_mode", "comprehensive")
                except json.JSONDecodeError:
                    # If JSON parsing fails, treat as direct file path
                    mod_path = mod_data
                    data = {"mod_path": mod_path}
                    extraction_mode = "comprehensive"
            else:
                # Handle dict or other object types
                data = mod_data if isinstance(mod_data, dict) else {"mod_path": str(mod_data)}
                # Check if CrewAI wrapped the parameter
                if "mod_data" in data:
                    mod_path = data["mod_data"]
                    data.get("structure_analysis", {})
                    extraction_mode = data.get("extraction_mode", "comprehensive")
                else:
                    mod_path = data.get("mod_path", str(mod_data))
                    data.get("structure_analysis", {})
                    extraction_mode = data.get("extraction_mode", "comprehensive")

            feature_results = {
                "identified_features": [],
                "feature_categories": {},
                "feature_complexity": {},
                "conversion_challenges": [],
            }

            # Use our enhanced analyzer for JAR files
            if mod_path.endswith((".jar", ".zip")):
                # Get a new instance of the analyzer to avoid state issues
                analyzer_instance = JavaAnalyzerAgent.get_instance()
                ast_result = analyzer_instance.analyze_jar_with_ast(mod_path)
                if ast_result["success"]:
                    # Flatten the features from the AST result
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
                    # Fallback to original approach
                    features = _extract_features_from_jar(mod_path, extraction_mode)
            else:
                features = _extract_features_from_source(mod_path, extraction_mode)

            # Categorize and analyze features
            categorized_features = _categorize_features(features)
            feature_results["identified_features"] = features
            feature_results["feature_categories"] = categorized_features

            # Assess feature complexity
            complexity_analysis = _analyze_feature_complexity(features)
            feature_results["feature_complexity"] = complexity_analysis

            # Identify conversion challenges
            challenges = _identify_conversion_challenges(features, categorized_features)
            feature_results["conversion_challenges"] = challenges

            response = {
                "success": True,
                "feature_results": feature_results,
                "feature_summary": _generate_feature_summary(feature_results),
            }

            logger.info(f"Identified {len(features)} features in: {mod_path}")
            return json.dumps(response)

        except Exception as e:
            error_response = {"success": False, "error": f"Failed to identify features: {str(e)}"}
            logger.error(f"Feature identification error: {e}")
            return json.dumps(error_response)

    @tool
    @staticmethod
    def analyze_dependencies_tool(mod_data: Union[str, Dict]) -> str:
        """
        Analyze mod dependencies.

        Args:
            mod_data: JSON string containing mod information

        Returns:
            JSON string with dependency analysis
        """
        JavaAnalyzerAgent.get_instance()

        def _analyze_direct_dependencies(metadata: Dict) -> List[Dict]:
            """Analyze direct dependencies"""
            return []  # Placeholder

        def _analyze_framework_dependencies(metadata: Dict) -> List[Dict]:
            """Analyze framework dependencies"""
            return []  # Placeholder

        def _assess_dependency_conversion_impact(direct: List, framework: List) -> Dict:
            """Assess conversion impact of dependencies"""
            return {"impact": "low"}  # Placeholder

        def _identify_compatibility_concerns(direct: List, framework: List) -> List[str]:
            """Identify compatibility concerns"""
            return []  # Placeholder

        def _generate_dependency_recommendations(results: Dict) -> List[str]:
            """Generate dependency recommendations"""
            return ["Review dependencies for Bedrock compatibility"]

        try:
            # Handle both JSON string and direct file path inputs
            if isinstance(mod_data, str):
                try:
                    data = json.loads(mod_data)
                    # Check if CrewAI wrapped the parameter
                    if "mod_data" in data:
                        mod_metadata = (
                            data["mod_data"] if isinstance(data["mod_data"], dict) else {}
                        )
                        data.get("analysis_depth", "standard")
                    else:
                        mod_metadata = data.get("mod_metadata", {})
                        data.get("analysis_depth", "standard")
                except json.JSONDecodeError:
                    # If JSON parsing fails, treat as direct file path
                    mod_metadata = {}
                    data = {"mod_metadata": mod_metadata}
            else:
                # Handle dict or other object types
                data = mod_data if isinstance(mod_data, dict) else {"mod_metadata": {}}
                # Check if CrewAI wrapped the parameter
                if "mod_data" in data:
                    mod_metadata = data["mod_data"] if isinstance(data["mod_data"], dict) else {}
                    data.get("analysis_depth", "standard")
                else:
                    mod_metadata = data.get("mod_metadata", {})
                    data.get("analysis_depth", "standard")

            dependency_results = {
                "direct_dependencies": [],
                "transitive_dependencies": [],
                "framework_dependencies": [],
                "conversion_impact": {},
                "compatibility_concerns": [],
            }

            # Analyze direct dependencies
            direct_deps = _analyze_direct_dependencies(mod_metadata)
            dependency_results["direct_dependencies"] = direct_deps

            # Analyze framework dependencies
            framework_deps = _analyze_framework_dependencies(mod_metadata)
            dependency_results["framework_dependencies"] = framework_deps

            # Assess conversion impact
            impact_analysis = _assess_dependency_conversion_impact(direct_deps, framework_deps)
            dependency_results["conversion_impact"] = impact_analysis

            # Identify compatibility concerns
            concerns = _identify_compatibility_concerns(direct_deps, framework_deps)
            dependency_results["compatibility_concerns"] = concerns

            response = {
                "success": True,
                "dependency_analysis": dependency_results,
                "recommendations": _generate_dependency_recommendations(dependency_results),
            }

            logger.info(
                f"Analyzed dependencies: {len(direct_deps)} direct, {len(framework_deps)} framework"
            )
            return json.dumps(response)

        except Exception as e:
            error_response = {
                "success": False,
                "error": f"Failed to analyze dependencies: {str(e)}",
            }
            logger.error(f"Dependency analysis error: {e}")
            return json.dumps(error_response)

    @tool
    @staticmethod
    def extract_assets_tool(mod_data: Union[str, Dict]) -> str:
        """
        Extract assets from the mod.

        Args:
            mod_data: JSON string containing mod file path

        Returns:
            JSON string with asset information
        """
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
            except Exception as e:
                logger.warning(f"Error extracting assets from JAR: {e}")

            return assets

        def _extract_assets_from_source(source_path: str, asset_types: List[str]) -> List[Dict]:
            """Extract assets from source"""
            assets = []
            try:
                for root, dirs, files in os.walk(source_path):
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        rel_path = os.path.relpath(file_path, source_path)

                        if "/textures/" in rel_path and file_name.endswith(
                            (".png", ".jpg", ".jpeg")
                        ):
                            assets.append(
                                {
                                    "type": "texture",
                                    "path": rel_path,
                                    "name": file_name,
                                    "size": os.path.getsize(file_path),
                                }
                            )
                        elif "/models/" in rel_path and file_name.endswith((".json", ".obj")):
                            assets.append(
                                {
                                    "type": "model",
                                    "path": rel_path,
                                    "name": file_name,
                                    "size": os.path.getsize(file_path),
                                }
                            )
                        elif "/sounds/" in rel_path and file_name.endswith((".ogg", ".wav")):
                            assets.append(
                                {
                                    "type": "sound",
                                    "path": rel_path,
                                    "name": file_name,
                                    "size": os.path.getsize(file_path),
                                }
                            )
            except Exception as e:
                logger.warning(f"Error extracting assets from source: {e}")

            return assets

        def _determine_asset_type(asset: Dict) -> str:
            """Determine asset type"""
            asset_type = asset.get("type", "unknown")
            if asset_type in ["texture", "model", "sound"]:
                return f"{asset_type}s"  # Convert to plural form
            return "other_assets"

        def _generate_asset_summary(assets: Dict) -> Dict:
            """Generate asset summary"""
            return {"summary": "Asset extraction completed"}

        def _generate_asset_conversion_notes(assets: Dict) -> List[str]:
            """Generate asset conversion notes"""
            return ["Assets ready for conversion analysis"]

        try:
            # Handle both JSON string and direct file path inputs
            if isinstance(mod_data, str):
                try:
                    data = json.loads(mod_data)
                    # Check if CrewAI wrapped the parameter
                    if "mod_data" in data:
                        mod_path = data["mod_data"]
                        asset_types = data.get("asset_types", ["textures", "models", "sounds"])
                    else:
                        mod_path = data.get("mod_path", "")
                        asset_types = data.get("asset_types", ["textures", "models", "sounds"])
                except json.JSONDecodeError:
                    # If JSON parsing fails, treat as direct file path
                    mod_path = mod_data
                    data = {"mod_path": mod_path}
                    asset_types = ["textures", "models", "sounds"]
            else:
                # Handle dict or other object types
                data = mod_data if isinstance(mod_data, dict) else {"mod_path": str(mod_data)}
                # Check if CrewAI wrapped the parameter
                if "mod_data" in data:
                    mod_path = data["mod_data"]
                    asset_types = data.get("asset_types", ["textures", "models", "sounds"])
                else:
                    mod_path = data.get("mod_path", str(mod_data))
                    asset_types = data.get("asset_types", ["textures", "models", "sounds"])

            asset_results = {
                "textures": [],
                "models": [],
                "sounds": [],
                "other_assets": [],
                "asset_summary": {},
            }

            # Extract assets based on mod type
            if mod_path.endswith((".jar", ".zip")):
                assets = _extract_assets_from_jar(mod_path, asset_types)
            else:
                assets = _extract_assets_from_source(mod_path, asset_types)

            # Categorize assets
            for asset in assets:
                asset_type = _determine_asset_type(asset)
                if asset_type in asset_results:
                    asset_results[asset_type].append(asset)
                else:
                    asset_results["other_assets"].append(asset)

            # Generate asset summary
            summary = _generate_asset_summary(asset_results)
            asset_results["asset_summary"] = summary

            response = {
                "success": True,
                "assets": asset_results,
                "conversion_notes": _generate_asset_conversion_notes(asset_results),
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

    def _generate_embeddings(self, result: dict) -> None:
        """Generate embeddings for the mod content to enable RAG retrieval"""
        try:
            # Check if embedding model is available
            if not self.embedding_generator.model:
                logger.warning("Embedding model not available, skipping embedding generation")
                result["embeddings_data"] = []
                return

            # Collect textual content for embedding generation
            embedding_texts = []

            # Add mod description and metadata
            mod_info = result.get("mod_info", {})
            if mod_info.get("description"):
                embedding_texts.append(f"Mod Description: {mod_info['description']}")

            # Add feature descriptions
            features = result.get("features", {})
            for feature_name, feature_data in features.items():
                if isinstance(feature_data, dict) and feature_data.get("description"):
                    embedding_texts.append(f"Feature {feature_name}: {feature_data['description']}")

            # Add key structural information
            if result.get("structure"):
                structure_info = f"Mod Structure: {json.dumps(result['structure'])}"
                embedding_texts.append(structure_info)

            # Store embedding data for later processing by the RAG system
            if embedding_texts:
                result["embeddings_data"] = [
                    {
                        "text": text,
                        "type": "mod_analysis",
                        "mod_name": mod_info.get("name", "unknown"),
                    }
                    for text in embedding_texts
                ]

        except Exception as e:
            logger.warning(f"Failed to generate embeddings: {e}")
            result["embeddings_data"] = []
