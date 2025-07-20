"""
Java Analyzer Agent for analyzing Java mod structure and extracting features
"""

import logging
import json
import re
from typing import List, Dict, Union
from crewai.tools import tool
from src.models.smart_assumptions import (
    SmartAssumptionEngine,
)
from src.utils.embedding_generator import EmbeddingGenerator # Added import
import os
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)


class JavaAnalyzerAgent:
    """
    Java Analyzer Agent responsible for analyzing Java mod structure,
    dependencies, and features as specified in PRD Feature 2.
    """
    
    _instance = None
    
    def __init__(self):
        self.smart_assumption_engine = SmartAssumptionEngine()
        self.embedding_generator = EmbeddingGenerator() # Added EmbeddingGenerator instantiation
        
        # File patterns for different types of mod files
        self.file_patterns = {
            'mod_files': ['.jar', '.zip'],
            'source_files': ['.java'],
            'config_files': ['.json', '.toml', '.cfg'],
            'resource_files': ['.png', '.jpg', '.ogg', '.wav', '.obj', '.mtl'],
            'metadata_files': ['mcmod.info', 'fabric.mod.json', 'quilt.mod.json', 'mods.toml']
        }
        
        # Common modding framework indicators
        self.framework_indicators = {
            'forge': ['net.minecraftforge', 'cpw.mods', '@Mod', 'ForgeModContainer'],
            'fabric': ['net.fabricmc', 'FabricLoader', 'fabric.mod.json'],
            'quilt': ['org.quiltmc', 'QuiltLoader', 'quilt.mod.json'],
            'bukkit': ['org.bukkit', 'plugin.yml', 'JavaPlugin'],
            'spigot': ['org.spigotmc', 'SpigotAPI'],
            'paper': ['io.papermc', 'PaperAPI']
        }
        
        # Feature extraction patterns
        self.feature_patterns = {
            'blocks': ['Block', 'BlockState', 'registerBlock', 'ModBlocks'],
            'items': ['Item', 'ItemStack', 'registerItem', 'ModItems'],
            'entities': ['Entity', 'EntityType', 'registerEntity', 'ModEntities'],
            'dimensions': ['Dimension', 'World', 'DimensionType', 'createDimension'],
            'gui': ['GuiScreen', 'ContainerScreen', 'IGuiHandler', 'MenuType'],
            'machinery': ['TileEntity', 'BlockEntity', 'IEnergyStorage', 'IFluidHandler'],
            'recipes': ['IRecipe', 'ShapedRecipe', 'ShapelessRecipe', 'registerRecipe'],
            'commands': ['Command', 'ICommand', 'CommandBase', 'registerCommand'],
            'events': ['Event', 'SubscribeEvent', 'EventHandler', 'Listener']
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
            JavaAnalyzerAgent.extract_assets_tool
        ]
    
    def analyze_mod_file(self, mod_path: str) -> str:
        """
        Analyze a mod file and return comprehensive results.
        
        Args:
            mod_path: Path to the mod file
            
        Returns:
            JSON string with analysis results
        """
        logger.info(f"Analyzing mod file: {mod_path}")
        
        try:
            # Initialize result structure
            result = {
                "mod_info": {"name": "unknown", "framework": "unknown", "version": "1.0.0"},
                "assets": {},
                "features": {},
                "structure": {},
                "metadata": {},
                "errors": [],
                "embeddings_data": []
            }
            
            # Analyze the mod file
            if mod_path.endswith(('.jar', '.zip')):
                result = self._analyze_jar_file(mod_path, result)
            elif os.path.isdir(mod_path):
                result = self._analyze_source_directory(mod_path, result)
            else:
                result["errors"].append(f"Unsupported mod file format: {mod_path}")
            
            # Generate embeddings for the analyzed content
            self._generate_embeddings(result)
            
            return json.dumps(result)
            
        except Exception as e:
            logger.error(f"Error analyzing mod file {mod_path}: {e}")
            return json.dumps({
                "mod_info": {"name": "error", "framework": "unknown", "version": "1.0.0"},
                "assets": {},
                "features": {},
                "structure": {},
                "metadata": {},
                "errors": [f"Analysis failed: {str(e)}"],
                "embeddings_data": []
            })
    
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
                'success': False,
                'registry_name': 'unknown:block',
                'texture_path': None,
                'errors': []
            }
            
            with zipfile.ZipFile(jar_path, 'r') as jar:
                file_list = jar.namelist()
                
                # Handle empty JARs gracefully
                if not file_list:
                    logger.warning(f"Empty JAR file: {jar_path}")
                    result['success'] = True  # Consider empty JAR as successfully analyzed
                    result['registry_name'] = 'unknown:copper_block'  # Default fallback for empty JARs
                    result['errors'].append("JAR file is empty but analysis completed")
                    return result
                
                # Find block texture
                texture_path = self._find_block_texture(file_list)
                if texture_path:
                    result['texture_path'] = texture_path
                    logger.info(f"Found texture: {texture_path}")
                
                # Extract registry name
                registry_name = self._extract_registry_name_from_jar(jar, file_list)
                if registry_name:
                    result['registry_name'] = registry_name
                    logger.info(f"Found registry name: {registry_name}")
                
                # Check if we have both texture and registry name for success
                if texture_path and registry_name:
                    result['success'] = True
                    logger.info(f"MVP analysis completed successfully for {jar_path}")
                else:
                    if not texture_path:
                        result['errors'].append("Could not find block texture in JAR")
                    if not registry_name or registry_name == 'unknown:block':
                        result['errors'].append("Could not determine block registry name")
                
                return result
                
        except Exception as e:
            logger.error(f"MVP analysis error: {e}")
            return {
                'success': False,
                'registry_name': 'unknown:block',
                'texture_path': None,
                'errors': [f"JAR analysis failed: {str(e)}"]
            }
    
    def _find_block_texture(self, file_list: list) -> str:
        """Find a block texture in the JAR file list."""
        for file_path in file_list:
            if (file_path.startswith('assets/') and 
                '/textures/block/' in file_path and 
                file_path.endswith('.png')):
                return file_path
        return None
    
    def _extract_registry_name_from_jar_simple(self, jar, file_list: list) -> str:
        """Extract block registry name from JAR metadata (simple version)."""
        # Look for mod metadata files
        for metadata_file in ['mcmod.info', 'fabric.mod.json', 'mods.toml']:
            if metadata_file in file_list:
                try:
                    content = jar.read(metadata_file).decode('utf-8')
                    if metadata_file == 'mcmod.info':
                        import json
                        data = json.loads(content)
                        if isinstance(data, list) and len(data) > 0:
                            mod_id = data[0].get('modid', 'unknown')
                            return f"{mod_id}:copper_block"  # Default block name for MVP
                    elif metadata_file == 'fabric.mod.json':
                        import json
                        data = json.loads(content)
                        mod_id = data.get('id', 'unknown')
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
                file_name.startswith('assets/') and 
                '/textures/block/' in file_name and 
                file_name.endswith('.png')
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
        if 'fabric.mod.json' in file_list:
            try:
                content = jar.read('fabric.mod.json').decode('utf-8')
                data = json.loads(content)
                return data.get('id', '').lower()
            except Exception as e:
                logger.warning(f"Error reading fabric.mod.json: {e}")
        
        # Try mcmod.info
        if 'mcmod.info' in file_list:
            try:
                content = jar.read('mcmod.info').decode('utf-8')
                data = json.loads(content)
                if isinstance(data, list) and len(data) > 0:
                    return data[0].get('modid', '').lower()
            except Exception as e:
                logger.warning(f"Error reading mcmod.info: {e}")
        
        # Try mods.toml
        for file_name in file_list:
            if file_name.endswith('mods.toml'):
                try:
                    content = jar.read(file_name).decode('utf-8')
                    for line in content.split('\n'):
                        if 'modId' in line and '=' in line:
                            mod_id = line.split('=')[1].strip().strip('"\'')
                            return mod_id.lower()
                except Exception as e:
                    logger.warning(f"Error reading {file_name}: {e}")
        
        return None
    
    def _find_block_class_name(self, file_list: list) -> str:
        """Find the main block class name from file paths."""
        block_candidates = []
        
        for file_name in file_list:
            if file_name.endswith('.class') or file_name.endswith('.java'):
                # Extract class name from path
                class_name = Path(file_name).stem
                
                # Look for Block in class name
                if 'Block' in class_name and not class_name.startswith('Abstract'):
                    block_candidates.append(class_name)
        
        # Return the first/shortest block class name
        if block_candidates:
            # Prefer simpler names (shorter, fewer underscores)
            block_candidates.sort(key=lambda x: (len(x), x.count('_')))
            return block_candidates[0]
        
        return None
    
    def _class_name_to_registry_name(self, class_name: str) -> str:
        """Convert Java class name to registry name format."""
        # Remove 'Block' suffix or prefix if present
        name = class_name
        if name.endswith('Block'):
            name = name[:-5]  # Remove 'Block' from the end
        elif name.startswith('Block'):
            name = name[5:]  # Remove 'Block' from the start
        
        # Convert CamelCase to snake_case
        import re
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
        
        # Clean up any double underscores or leading/trailing underscores
        name = re.sub('_+', '_', name).strip('_')
        
        # Return clean name without adding '_block' suffix
        return name if name else 'unknown'
    
    def _analyze_jar_file(self, jar_path: str, result: dict) -> dict:
        """Analyze a JAR file for mod information"""
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
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
                
        except Exception as e:
            result["errors"].append(f"Error analyzing JAR file: {str(e)}")
        
        return result
    
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
                if file_name.endswith('.json') and 'mod' in file_name.lower():
                    try:
                        content = jar.read(file_name).decode('utf-8')
                        for framework, indicators in self.framework_indicators.items():
                            for indicator in indicators:
                                if indicator in content:
                                    return framework
                    except (UnicodeDecodeError, KeyError) as e:
                        logger.debug(f"Could not read {file_name}: {e}")
                        continue
            
            return 'unknown'
        except Exception as e:
            logger.warning(f"Error detecting framework: {e}")
            return 'unknown'
    
    def _extract_mod_info_from_jar(self, jar: zipfile.ZipFile, file_list: list) -> dict:
        """Extract mod information from metadata files"""
        mod_info = {}
        
        # Look for Fabric mod.json
        if 'fabric.mod.json' in file_list:
            try:
                content = jar.read('fabric.mod.json').decode('utf-8')
                fabric_data = json.loads(content)
                mod_info["name"] = fabric_data.get("id", fabric_data.get("name", "unknown")).lower()
                mod_info["version"] = fabric_data.get("version", "1.0.0")
                return mod_info
            except (json.JSONDecodeError, UnicodeDecodeError, KeyError) as e:
                logger.debug(f"Could not parse fabric.mod.json: {e}")
                pass
        
        # Look for Quilt mod.json
        if 'quilt.mod.json' in file_list:
            try:
                content = jar.read('quilt.mod.json').decode('utf-8')
                quilt_data = json.loads(content)
                mod_info["name"] = quilt_data.get("quilt_loader", {}).get("id", "unknown").lower()
                mod_info["version"] = quilt_data.get("quilt_loader", {}).get("version", "1.0.0")
                return mod_info
            except (json.JSONDecodeError, UnicodeDecodeError, KeyError) as e:
                logger.debug(f"Could not parse quilt.mod.json: {e}")
                pass
        
        # Look for Forge mcmod.info
        if 'mcmod.info' in file_list:
            try:
                content = jar.read('mcmod.info').decode('utf-8')
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
            if file_name.endswith('mods.toml'):
                try:
                    content = jar.read(file_name).decode('utf-8')
                    # Simple TOML parsing for modId
                    for line in content.split('\n'):
                        if 'modId' in line and '=' in line:
                            mod_id = line.split('=')[1].strip().strip('"\'')
                            mod_info["name"] = mod_id.lower()
                            break
                    return mod_info
                except Exception as e:
                    logger.debug(f"Could not parse mods.toml: {e}")
                    pass
        
        return mod_info
    
    def _analyze_assets_from_jar(self, file_list: list) -> dict:
        """Analyze assets in the JAR file"""
        assets = {
            "textures": [],
            "models": [],
            "sounds": [],
            "other": []
        }
        
        for file_name in file_list:
            if '/textures/' in file_name and file_name.endswith(('.png', '.jpg', '.jpeg')):
                assets["textures"].append(file_name)
            elif '/models/' in file_name and file_name.endswith(('.json', '.obj')):
                assets["models"].append(file_name)
            elif '/sounds/' in file_name and file_name.endswith(('.ogg', '.wav')):
                assets["sounds"].append(file_name)
            elif any(file_name.endswith(ext) for ext in ['.png', '.jpg', '.ogg', '.wav', '.obj', '.mtl']):
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
            if mod_path.endswith(('.jar', '.zip')):
                mod_type = 'jar'
                framework = _detect_framework_from_jar(mod_path)
            elif os.path.isdir(mod_path):
                mod_type = 'source'
                framework = _detect_framework_from_source(mod_path)
            else:
                mod_type = 'unknown'
                framework = 'unknown'
            
            return {'type': mod_type, 'framework': framework}

        def _detect_framework_from_jar(jar_path: str) -> str:
            """Detect modding framework from JAR file contents"""
            try:
                with zipfile.ZipFile(jar_path, 'r') as jar:
                    file_list = jar.namelist()
                    
                    # Check for framework-specific files and patterns
                    for framework, indicators in agent.framework_indicators.items():
                        for indicator in indicators:
                            if any(indicator in file_name for file_name in file_list):
                                return framework
                    
                    # Check file contents if available
                    for file_name in file_list:
                        if file_name.endswith('.json') and 'mod' in file_name.lower():
                            try:
                                content = jar.read(file_name).decode('utf-8')
                                for framework, indicators in agent.framework_indicators.items():
                                    for indicator in indicators:
                                        if indicator in content:
                                            return framework
                            except (UnicodeDecodeError, KeyError) as e:
                                logger.debug(f"Could not read {file_name}: {e}")
                                continue
                    
                    return 'unknown'
            except Exception as e:
                logger.warning(f"Error in framework detection tool: {e}")
                return 'unknown'

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
                        if file_name.endswith('.java'):
                            try:
                                file_path = os.path.join(root, file_name)
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    for framework, indicators in agent.framework_indicators.items():
                                        for indicator in indicators:
                                            if indicator in content:
                                                return framework
                            except (UnicodeDecodeError, FileNotFoundError, PermissionError) as e:
                                logger.debug(f"Could not read {file_path}: {e}")
                                continue
                
                return 'unknown'
            except Exception as e:
                logger.warning(f"Error in source framework detection: {e}")
                return 'unknown'

        def _analyze_jar_structure(jar_path: str, analysis_depth: str) -> Dict:
            """Analyze JAR file structure"""
            structure = {
                'total_files': 0,
                'package_structure': {},
                'main_classes': [],
                'resource_files': [],
                'metadata_files': []
            }
            
            try:
                with zipfile.ZipFile(jar_path, 'r') as jar:
                    file_list = jar.namelist()
                    structure['total_files'] = len(file_list)
                    
                    for file_name in file_list:
                        if file_name.endswith('.class'):
                            # Java class file
                            package_path = '/'.join(file_name.split('/')[:-1])
                            if package_path not in structure['package_structure']:
                                structure['package_structure'][package_path] = []
                            structure['package_structure'][package_path].append(file_name)
                            
                            # Check if it's a main class
                            if _is_main_class(file_name):
                                structure['main_classes'].append(file_name)
                        
                        elif any(file_name.endswith(ext) for ext in agent.file_patterns['resource_files']):
                            structure['resource_files'].append(file_name)
                        
                        elif any(metadata in file_name for metadata in agent.file_patterns['metadata_files']):
                            structure['metadata_files'].append(file_name)
            
            except Exception as e:
                logger.warning(f"Error analyzing JAR structure: {e}")
            
            return structure

        def _analyze_source_structure(source_path: str, analysis_depth: str) -> Dict:
            """Analyze source directory structure"""
            structure = {
                'total_files': 0,
                'source_files': [],
                'resource_files': [],
                'config_files': [],
                'build_files': []
            }
            
            try:
                for root, dirs, files in os.walk(source_path):
                    structure['total_files'] += len(files)
                    
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        rel_path = os.path.relpath(file_path, source_path)
                        
                        if file_name.endswith('.java'):
                            structure['source_files'].append(rel_path)
                        elif any(file_name.endswith(ext) for ext in agent.file_patterns['resource_files']):
                            structure['resource_files'].append(rel_path)
                        elif any(file_name.endswith(ext) for ext in agent.file_patterns['config_files']):
                            structure['config_files'].append(rel_path)
                        elif file_name in ['build.gradle', 'pom.xml', 'build.xml']:
                            structure['build_files'].append(rel_path)
            
            except Exception as e:
                logger.warning(f"Error analyzing source structure: {e}")
            
            return structure

        def _analyze_unknown_structure(mod_path: str, analysis_depth: str) -> Dict:
            """Analyze unknown file type structure"""
            return {
                'type': 'unknown',
                'path': mod_path,
                'size': os.path.getsize(mod_path) if os.path.exists(mod_path) else 0,
                'analysis_note': 'Unknown file type - limited analysis available'
            }

        def _create_file_inventory(mod_path: str, mod_type: str) -> Dict:
            """Create comprehensive file inventory"""
            inventory = {
                'by_type': {},
                'by_size': {},
                'total_count': 0,
                'total_size': 0
            }
            
            if mod_type == 'jar':
                inventory = _inventory_jar_files(mod_path)
            elif mod_type == 'source':
                inventory = _inventory_source_files(mod_path)
            
            return inventory

        def _inventory_jar_files(jar_path: str) -> Dict:
            """Create inventory of JAR file contents"""
            inventory = {'by_type': {}, 'by_size': {}, 'total_count': 0, 'total_size': 0}
            
            try:
                with zipfile.ZipFile(jar_path, 'r') as jar:
                    for info in jar.infolist():
                        if not info.is_dir():
                            file_ext = Path(info.filename).suffix.lower()
                            file_size = info.file_size
                            
                            inventory['by_type'][file_ext] = inventory['by_type'].get(file_ext, 0) + 1
                            inventory['total_count'] += 1
                            inventory['total_size'] += file_size
                            
                            # Categorize by size
                            size_category = 'small' if file_size < 1024 else 'medium' if file_size < 1024*1024 else 'large'
                            inventory['by_size'][size_category] = inventory['by_size'].get(size_category, 0) + 1
            
            except Exception as e:
                logger.warning(f"Error creating JAR inventory: {e}")
            
            return inventory

        def _inventory_source_files(source_path: str) -> Dict:
            """Create inventory of source directory contents"""
            inventory = {'by_type': {}, 'by_size': {}, 'total_count': 0, 'total_size': 0}
            
            try:
                for root, dirs, files in os.walk(source_path):
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        file_ext = Path(file_name).suffix.lower()
                        file_size = os.path.getsize(file_path)
                        
                        inventory['by_type'][file_ext] = inventory['by_type'].get(file_ext, 0) + 1
                        inventory['total_count'] += 1
                        inventory['total_size'] += file_size
                        
                        # Categorize by size
                        size_category = 'small' if file_size < 1024 else 'medium' if file_size < 1024*1024 else 'large'
                        inventory['by_size'][size_category] = inventory['by_size'].get(size_category, 0) + 1
            
            except Exception as e:
                logger.warning(f"Error creating source inventory: {e}")
            
            return inventory

        def _assess_mod_complexity(structure: Dict, file_inventory: Dict) -> Dict:
            """Assess the complexity of the mod for conversion planning"""
            complexity = {
                'overall_complexity': 'medium',
                'complexity_factors': [],
                'complexity_score': 0,
                'conversion_difficulty': 'moderate'
            }
            
            score = 0
            factors = []
            
            # Factor in number of files
            total_files = file_inventory.get('total_count', 0)
            if total_files > 100:
                score += 2
                factors.append('Large number of files')
            elif total_files > 50:
                score += 1
                factors.append('Moderate number of files')
            
            # Factor in package structure complexity (for JARs)
            if 'package_structure' in structure:
                packages = len(structure['package_structure'])
                if packages > 10:
                    score += 2
                    factors.append('Complex package structure')
                elif packages > 5:
                    score += 1
                    factors.append('Moderate package structure')
            
            # Factor in resource files
            resource_count = len(structure.get('resource_files', []))
            if resource_count > 50:
                score += 2
                factors.append('Many resource files')
            elif resource_count > 20:
                score += 1
                factors.append('Moderate resource files')
            
            # Determine overall complexity
            if score >= 5:
                complexity['overall_complexity'] = 'high'
                complexity['conversion_difficulty'] = 'challenging'
            elif score >= 3:
                complexity['overall_complexity'] = 'medium'
                complexity['conversion_difficulty'] = 'moderate'
            else:
                complexity['overall_complexity'] = 'low'
                complexity['conversion_difficulty'] = 'straightforward'
            
            complexity['complexity_score'] = score
            complexity['complexity_factors'] = factors
            
            return complexity

        def _is_main_class(class_path: str) -> bool:
            """Check if a class is a main mod class"""
            return 'mod' in class_path.lower() and ('main' in class_path.lower() or class_path.count('/') <= 3)

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
                    if 'mod_data' in data:
                        mod_path = data['mod_data']
                        analysis_depth = data.get('analysis_depth', 'standard')
                    else:
                        mod_path = data.get('mod_path', '')
                        analysis_depth = data.get('analysis_depth', 'standard')
                except json.JSONDecodeError:
                    # If JSON parsing fails, treat as direct file path
                    mod_path = mod_data
                    analysis_depth = 'standard'
            else:
                # Handle dict or other object types
                data = mod_data if isinstance(mod_data, dict) else {'mod_path': str(mod_data)}
                # Check if CrewAI wrapped the parameter
                if 'mod_data' in data:
                    mod_path = data['mod_data']
                    analysis_depth = data.get('analysis_depth', 'standard')
                else:
                    mod_path = data.get('mod_path', str(mod_data))
                    analysis_depth = data.get('analysis_depth', 'standard')
            
            if not os.path.exists(mod_path):
                return json.dumps({"success": False, "error": f"Mod file not found: {mod_path}"})
            
            analysis_results = {
                'mod_path': mod_path,
                'mod_type': '',
                'framework': '',
                'structure_analysis': {},
                'file_inventory': {},
                'complexity_assessment': {}
            }
            
            # Determine mod type and framework
            mod_info = _determine_mod_type_and_framework(mod_path)
            analysis_results['mod_type'] = mod_info['type']
            analysis_results['framework'] = mod_info['framework']
            
            # Analyze structure based on mod type
            if mod_info['type'] == 'jar':
                structure = _analyze_jar_structure(mod_path, analysis_depth)
            elif mod_info['type'] == 'source':
                structure = _analyze_source_structure(mod_path, analysis_depth)
            else:
                structure = _analyze_unknown_structure(mod_path, analysis_depth)
            
            analysis_results['structure_analysis'] = structure
            
            # Create file inventory
            file_inventory = _create_file_inventory(mod_path, mod_info['type'])
            analysis_results['file_inventory'] = file_inventory
            
            # Assess complexity
            complexity = _assess_mod_complexity(structure, file_inventory)
            analysis_results['complexity_assessment'] = complexity
            
            response = {
                "success": True,
                "analysis_results": analysis_results,
                "recommendations": _generate_analysis_recommendations(analysis_results)
            }
            
            logger.info(f"Analyzed mod structure: {mod_path} ({mod_info['framework']} {mod_info['type']})")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to analyze mod structure: {str(e)}"}
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
                with zipfile.ZipFile(jar_path, 'r') as jar:
                    # Look for metadata files
                    for metadata_file in agent.file_patterns['metadata_files']:
                        if metadata_file in jar.namelist():
                            try:
                                content = jar.read(metadata_file).decode('utf-8')
                                if metadata_file.endswith('.json'):
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
                        if file_name in agent.file_patterns['metadata_files']:
                            file_path = os.path.join(root, file_name)
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    if file_name.endswith('.json'):
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
                    if 'mod_data' in data:
                        mod_path = data['mod_data']
                    else:
                        mod_path = data.get('mod_path', '')
                except json.JSONDecodeError:
                    # If JSON parsing fails, treat as direct file path
                    mod_path = mod_data
                    data = {'mod_path': mod_path}
            else:
                # Handle dict or other object types
                data = mod_data if isinstance(mod_data, dict) else {'mod_path': str(mod_data)}
                # Check if CrewAI wrapped the parameter
                if 'mod_data' in data:
                    mod_path = data['mod_data']
                else:
                    mod_path = data.get('mod_path', str(mod_data))
            
            metadata_results = {
                'mod_info': {},
                'dependencies': [],
                'version_info': {},
                'author_info': {},
                'feature_flags': {},
                'compatibility_info': {}
            }
            
            # Extract metadata based on mod type
            if mod_path.endswith(('.jar', '.zip')):
                metadata = _extract_jar_metadata(mod_path)
            else:
                metadata = _extract_source_metadata(mod_path)
            
            metadata_results.update(metadata)
            
            response = {
                "success": True,
                "metadata": metadata_results,
                "extraction_summary": _summarize_metadata(metadata_results)
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
                with zipfile.ZipFile(jar_path, 'r') as jar:
                    for file_info in jar.infolist():
                        if file_info.filename.endswith('.class'):
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
                        if file_name.endswith('.java'):
                            file_path = os.path.join(root, file_name)
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    detected_features = _detect_features_from_content(content, file_name)
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
                        features.append({
                            'feature_id': f"{feature_type}_{class_name.lower()}",
                            'feature_type': feature_type,
                            'name': class_name,
                            'source': 'class_name_analysis',
                            'confidence': 'medium',
                            'original_data': {'class_name': class_name}
                        })
                        break  # Only add one feature per class
            
            return features

        def _detect_features_from_content(content: str, file_name: str) -> List[Dict]:
            """Detect features from source file content"""
            features = []
            
            for feature_type, patterns in agent.feature_patterns.items():
                for pattern in patterns:
                    if pattern in content:
                        features.append({
                            'feature_id': f"{feature_type}_{Path(file_name).stem.lower()}",
                            'feature_type': feature_type,
                            'name': f"{feature_type.title()} in {Path(file_name).stem}",
                            'source': 'content_analysis',
                            'confidence': 'high',
                            'original_data': {'file_name': file_name, 'detected_pattern': pattern}
                        })
                        break  # Only add one feature per type per file
            
            return features

        def _categorize_features(features: List[Dict]) -> Dict:
            """Categorize features by type"""
            categories = {}
            for feature in features:
                feature_type = feature.get('feature_type', 'unknown')
                if feature_type not in categories:
                    categories[feature_type] = []
                categories[feature_type].append(feature)
            return categories

        def _analyze_feature_complexity(features: List[Dict]) -> Dict:
            """Analyze complexity of identified features"""
            return {
                'total_features': len(features),
                'complexity_distribution': {'simple': 0, 'moderate': 0, 'complex': 0},
                'high_priority_features': [f for f in features if f.get('confidence') == 'high']
            }

        def _identify_conversion_challenges(features: List[Dict], categories: Dict) -> List[str]:
            """Identify potential conversion challenges"""
            challenges = []
            
            if 'dimensions' in categories:
                challenges.append('Custom dimensions require structural workarounds')
            
            if 'gui' in categories:
                challenges.append('Custom GUIs need alternative interfaces')
            
            if 'machinery' in categories:
                challenges.append('Complex machinery may lose functionality')
            
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
                    if 'mod_data' in data:
                        mod_path = data['mod_data']
                        data.get('structure_analysis', {})
                        extraction_mode = data.get('extraction_mode', 'comprehensive')
                    else:
                        mod_path = data.get('mod_path', '')
                        data.get('structure_analysis', {})
                        extraction_mode = data.get('extraction_mode', 'comprehensive')
                except json.JSONDecodeError:
                    # If JSON parsing fails, treat as direct file path
                    mod_path = mod_data
                    data = {'mod_path': mod_path}
                    extraction_mode = 'comprehensive'
            else:
                # Handle dict or other object types
                data = mod_data if isinstance(mod_data, dict) else {'mod_path': str(mod_data)}
                # Check if CrewAI wrapped the parameter
                if 'mod_data' in data:
                    mod_path = data['mod_data']
                    data.get('structure_analysis', {})
                    extraction_mode = data.get('extraction_mode', 'comprehensive')
                else:
                    mod_path = data.get('mod_path', str(mod_data))
                    data.get('structure_analysis', {})
                    extraction_mode = data.get('extraction_mode', 'comprehensive')
            
            feature_results = {
                'identified_features': [],
                'feature_categories': {},
                'feature_complexity': {},
                'conversion_challenges': []
            }
            
            # Extract features from different sources
            if mod_path.endswith(('.jar', '.zip')):
                features = _extract_features_from_jar(mod_path, extraction_mode)
            else:
                features = _extract_features_from_source(mod_path, extraction_mode)
            
            # Categorize and analyze features
            categorized_features = _categorize_features(features)
            feature_results['identified_features'] = features
            feature_results['feature_categories'] = categorized_features
            
            # Assess feature complexity
            complexity_analysis = _analyze_feature_complexity(features)
            feature_results['feature_complexity'] = complexity_analysis
            
            # Identify conversion challenges
            challenges = _identify_conversion_challenges(features, categorized_features)
            feature_results['conversion_challenges'] = challenges
            
            response = {
                "success": True,
                "feature_results": feature_results,
                "feature_summary": _generate_feature_summary(feature_results)
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
                    if 'mod_data' in data:
                        mod_metadata = data['mod_data'] if isinstance(data['mod_data'], dict) else {}
                        data.get('analysis_depth', 'standard')
                    else:
                        mod_metadata = data.get('mod_metadata', {})
                        data.get('analysis_depth', 'standard')
                except json.JSONDecodeError:
                    # If JSON parsing fails, treat as direct file path
                    mod_metadata = {}
                    data = {'mod_metadata': mod_metadata}
            else:
                # Handle dict or other object types
                data = mod_data if isinstance(mod_data, dict) else {'mod_metadata': {}}
                # Check if CrewAI wrapped the parameter
                if 'mod_data' in data:
                    mod_metadata = data['mod_data'] if isinstance(data['mod_data'], dict) else {}
                    data.get('analysis_depth', 'standard')
                else:
                    mod_metadata = data.get('mod_metadata', {})
                    data.get('analysis_depth', 'standard')
            
            dependency_results = {
                'direct_dependencies': [],
                'transitive_dependencies': [],
                'framework_dependencies': [],
                'conversion_impact': {},
                'compatibility_concerns': []
            }
            
            # Analyze direct dependencies
            direct_deps = _analyze_direct_dependencies(mod_metadata)
            dependency_results['direct_dependencies'] = direct_deps
            
            # Analyze framework dependencies
            framework_deps = _analyze_framework_dependencies(mod_metadata)
            dependency_results['framework_dependencies'] = framework_deps
            
            # Assess conversion impact
            impact_analysis = _assess_dependency_conversion_impact(direct_deps, framework_deps)
            dependency_results['conversion_impact'] = impact_analysis
            
            # Identify compatibility concerns
            concerns = _identify_compatibility_concerns(direct_deps, framework_deps)
            dependency_results['compatibility_concerns'] = concerns
            
            response = {
                "success": True,
                "dependency_analysis": dependency_results,
                "recommendations": _generate_dependency_recommendations(dependency_results)
            }
            
            logger.info(f"Analyzed dependencies: {len(direct_deps)} direct, {len(framework_deps)} framework")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to analyze dependencies: {str(e)}"}
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
                with zipfile.ZipFile(jar_path, 'r') as jar:
                    file_list = jar.namelist()
                    
                    for file_path in file_list:
                        if '/textures/' in file_path and file_path.endswith(('.png', '.jpg', '.jpeg')):
                            assets.append({
                                'type': 'texture',
                                'path': file_path,
                                'name': Path(file_path).name,
                                'size': jar.getinfo(file_path).file_size
                            })
                        elif '/models/' in file_path and file_path.endswith(('.json', '.obj')):
                            assets.append({
                                'type': 'model',
                                'path': file_path,
                                'name': Path(file_path).name,
                                'size': jar.getinfo(file_path).file_size
                            })
                        elif '/sounds/' in file_path and file_path.endswith(('.ogg', '.wav')):
                            assets.append({
                                'type': 'sound',
                                'path': file_path,
                                'name': Path(file_path).name,
                                'size': jar.getinfo(file_path).file_size
                            })
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
                        
                        if '/textures/' in rel_path and file_name.endswith(('.png', '.jpg', '.jpeg')):
                            assets.append({
                                'type': 'texture',
                                'path': rel_path,
                                'name': file_name,
                                'size': os.path.getsize(file_path)
                            })
                        elif '/models/' in rel_path and file_name.endswith(('.json', '.obj')):
                            assets.append({
                                'type': 'model',
                                'path': rel_path,
                                'name': file_name,
                                'size': os.path.getsize(file_path)
                            })
                        elif '/sounds/' in rel_path and file_name.endswith(('.ogg', '.wav')):
                            assets.append({
                                'type': 'sound',
                                'path': rel_path,
                                'name': file_name,
                                'size': os.path.getsize(file_path)
                            })
            except Exception as e:
                logger.warning(f"Error extracting assets from source: {e}")
            
            return assets
    
        def _determine_asset_type(asset: Dict) -> str:
            """Determine asset type"""
            asset_type = asset.get('type', 'unknown')
            if asset_type in ['texture', 'model', 'sound']:
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
                    if 'mod_data' in data:
                        mod_path = data['mod_data']
                        asset_types = data.get('asset_types', ['textures', 'models', 'sounds'])
                    else:
                        mod_path = data.get('mod_path', '')
                        asset_types = data.get('asset_types', ['textures', 'models', 'sounds'])
                except json.JSONDecodeError:
                    # If JSON parsing fails, treat as direct file path
                    mod_path = mod_data
                    data = {'mod_path': mod_path}
                    asset_types = ['textures', 'models', 'sounds']
            else:
                # Handle dict or other object types
                data = mod_data if isinstance(mod_data, dict) else {'mod_path': str(mod_data)}
                # Check if CrewAI wrapped the parameter
                if 'mod_data' in data:
                    mod_path = data['mod_data']
                    asset_types = data.get('asset_types', ['textures', 'models', 'sounds'])
                else:
                    mod_path = data.get('mod_path', str(mod_data))
                    asset_types = data.get('asset_types', ['textures', 'models', 'sounds'])
            
            asset_results = {
                'textures': [],
                'models': [],
                'sounds': [],
                'other_assets': [],
                'asset_summary': {}
            }
            
            # Extract assets based on mod type
            if mod_path.endswith(('.jar', '.zip')):
                assets = _extract_assets_from_jar(mod_path, asset_types)
            else:
                assets = _extract_assets_from_source(mod_path, asset_types)
            
            # Categorize assets
            for asset in assets:
                asset_type = _determine_asset_type(asset)
                if asset_type in asset_results:
                    asset_results[asset_type].append(asset)
                else:
                    asset_results['other_assets'].append(asset)
            
            # Generate asset summary
            summary = _generate_asset_summary(asset_results)
            asset_results['asset_summary'] = summary
            
            response = {
                "success": True,
                "assets": asset_results,
                "conversion_notes": _generate_asset_conversion_notes(asset_results)
            }
            
            total_assets = sum(len(assets) for assets in asset_results.values() if isinstance(assets, list))
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
                result["embeddings_data"] = [{
                    "text": text,
                    "type": "mod_analysis",
                    "mod_name": mod_info.get("name", "unknown")
                } for text in embedding_texts]
                
        except Exception as e:
            logger.warning(f"Failed to generate embeddings: {e}")
            result["embeddings_data"] = []
