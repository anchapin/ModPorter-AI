"""
Java Analyzer Agent for analyzing Java mod structure and extracting features
"""

import javalang
import re
import logging
import json
from typing import List, Dict, Any, Optional
from crewai.tools import tool
from src.models.smart_assumptions import (
    SmartAssumptionEngine,
)
import os
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)


class JavaAnalyzerAgent:
    """
    Java Analyzer Agent responsible for analyzing Java mod structure,
    dependencies, and features as specified in PRD Feature 2.
    """
    
    def __init__(self):
        self.smart_assumption_engine = SmartAssumptionEngine()
        
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
    
    def get_tools(self) -> List:
        """Get tools available to this agent"""
        # Return the actual decorated tool instances created by @tool decorator
        return [
            self.analyze_mod_structure_tool,
            self.extract_mod_metadata_tool,
            self.identify_features_tool,
            self.analyze_dependencies_tool,
            self.extract_assets_tool
        ]

    @tool
    def analyze_mod_structure_tool(self, mod_data: str) -> str:
        """
        Analyze the overall structure of a Java mod.
        
        Args:
            mod_data: JSON string containing mod file path and analysis options
        
        Returns:
            JSON string with structural analysis results
        """
        return self.analyze_mod_structure(mod_data)

    @tool
    def extract_mod_metadata_tool(self, mod_data: str) -> str:
        """
        Extract metadata from mod files.
        
        Args:
            mod_data: JSON string containing mod file path
        
        Returns:
            JSON string with metadata
        """
        return self.extract_mod_metadata(mod_data)

    @tool 
    def identify_features_tool(self, mod_data: str) -> str:
        """
        Identify features in the mod.
        
        Args:
            mod_data: JSON string containing analysis data
        
        Returns:
            JSON string with identified features
        """
        return self.identify_features(mod_data)

    @tool
    def analyze_dependencies_tool(self, mod_data: str) -> str:
        """
        Analyze mod dependencies.
        
        Args:
            mod_data: JSON string containing mod information
        
        Returns:
            JSON string with dependency analysis
        """
        return self.analyze_dependencies(mod_data)

    @tool
    def extract_assets_tool(self, mod_data: str) -> str:
        """
        Extract assets from the mod.
        
        Args:
            mod_data: JSON string containing mod file path
        
        Returns:
            JSON string with asset information
        """
        return self.extract_assets(mod_data)
    
    def analyze_mod_file(self, mod_path: str) -> str:
        """
        Analyze a mod file and return comprehensive analysis results.
        
        Args:
            mod_path: Path to the mod file
        
        Returns:
            JSON string with complete mod analysis
        """
        try:
            # Create analysis data structure
            analysis_data = {
                "mod_path": mod_path,
                "analysis_depth": "standard"
            }
            
            # Run comprehensive analysis
            structure_result = self.analyze_mod_structure(json.dumps(analysis_data))
            structure_data = json.loads(structure_result)
            
            # Extract features
            features_result = self.identify_features(json.dumps(analysis_data))
            features_data = json.loads(features_result)
            
            # Extract assets
            assets_result = self.extract_assets(json.dumps(analysis_data))
            assets_data = json.loads(assets_result)
            
            # Analyze dependencies
            dependencies_result = self.analyze_dependencies(json.dumps(analysis_data))
            dependencies_data = json.loads(dependencies_result)
            
            # Extract mod name from path
            mod_name = Path(mod_path).stem.lower().replace('.jar', '').replace('.zip', '')
            
            # Combine all results
            complete_analysis = {
                "mod_info": {
                    "name": mod_name,
                    "path": mod_path,
                    "type": structure_data.get("analysis_results", {}).get("mod_type", "unknown"),
                    "framework": structure_data.get("analysis_results", {}).get("framework", "unknown"),
                    **structure_data.get("analysis_results", {})
                },
                "assets": assets_data.get("assets", {}),
                "features": features_data.get("features", {}),
                "dependencies": dependencies_data.get("dependencies", {}),
                "errors": []
            }
            
            # Add any errors from sub-analyses
            for result_data in [structure_data, features_data, assets_data, dependencies_data]:
                if "errors" in result_data:
                    complete_analysis["errors"].extend(result_data["errors"])
            
            return json.dumps(complete_analysis, indent=2)
            
        except Exception as e:
            logger.error(f"Error in analyze_mod_file: {str(e)}")
            return json.dumps({
                "mod_info": {},
                "assets": {},
                "features": {},
                "dependencies": {},
                "errors": [f"Analysis failed: {str(e)}"]
            })
    
    def analyze_mod_structure(self, mod_data: str) -> str:
        """
        Analyze the overall structure of a Java mod.
        
        Args:
            mod_data: JSON string containing mod file path and analysis options
        
        Returns:
            JSON string with structural analysis results
        """
        try:
            data = json.loads(mod_data)
            mod_path = data.get('mod_path', '')
            analysis_depth = data.get('analysis_depth', 'standard')  # basic, standard, deep
            
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
            mod_info = self._determine_mod_type_and_framework(mod_path)
            analysis_results['mod_type'] = mod_info['type']
            analysis_results['framework'] = mod_info['framework']
            
            # Analyze structure based on mod type
            if mod_info['type'] == 'jar':
                structure = self._analyze_jar_structure(mod_path, analysis_depth)
            elif mod_info['type'] == 'source':
                structure = self._analyze_source_structure(mod_path, analysis_depth)
            else:
                structure = self._analyze_unknown_structure(mod_path, analysis_depth)
            
            analysis_results['structure_analysis'] = structure
            
            # Create file inventory
            file_inventory = self._create_file_inventory(mod_path, mod_info['type'])
            analysis_results['file_inventory'] = file_inventory
            
            # Assess complexity
            complexity = self._assess_mod_complexity(structure, file_inventory)
            analysis_results['complexity_assessment'] = complexity
            
            response = {
                "success": True,
                "analysis_results": analysis_results,
                "recommendations": self._generate_analysis_recommendations(analysis_results)
            }
            
            logger.info(f"Analyzed mod structure: {mod_path} ({mod_info['framework']} {mod_info['type']})")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to analyze mod structure: {str(e)}"}
            logger.error(f"Mod structure analysis error: {e}")
            return json.dumps(error_response)
    
    def extract_mod_metadata(self, metadata_data: str) -> str:
        """
        Extract metadata from mod files (mcmod.info, fabric.mod.json, etc.).
        
        Args:
            metadata_data: JSON string containing mod path and metadata extraction options
        
        Returns:
            JSON string with extracted metadata
        """
        try:
            data = json.loads(metadata_data)
            mod_path = data.get('mod_path', '')
            
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
                metadata = self._extract_jar_metadata(mod_path)
            else:
                metadata = self._extract_source_metadata(mod_path)
            
            metadata_results.update(metadata)
            
            response = {
                "success": True,
                "metadata": metadata_results,
                "extraction_summary": self._summarize_metadata(metadata_results)
            }
            
            logger.info(f"Extracted metadata from: {mod_path}")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to extract metadata: {str(e)}"}
            logger.error(f"Metadata extraction error: {e}")
            return json.dumps(error_response)
    
    def identify_features(self, feature_data: str) -> str:
        """
        Identify and categorize features present in the Java mod.
        
        Args:
            feature_data: JSON string containing mod analysis results and feature extraction options
        
        Returns:
            JSON string with identified features and their contexts
        """
        try:
            data = json.loads(feature_data)
            mod_path = data.get('mod_path', '')
            structure_analysis = data.get('structure_analysis', {})
            extraction_mode = data.get('extraction_mode', 'comprehensive')  # basic, comprehensive, detailed
            
            feature_results = {
                'identified_features': [],
                'feature_categories': {},
                'feature_complexity': {},
                'conversion_challenges': []
            }
            
            # Extract features from different sources
            if mod_path.endswith(('.jar', '.zip')):
                features = self._extract_features_from_jar(mod_path, extraction_mode)
            else:
                features = self._extract_features_from_source(mod_path, extraction_mode)
            
            # Categorize and analyze features
            categorized_features = self._categorize_features(features)
            feature_results['identified_features'] = features
            feature_results['feature_categories'] = categorized_features
            
            # Assess feature complexity
            complexity_analysis = self._analyze_feature_complexity(features)
            feature_results['feature_complexity'] = complexity_analysis
            
            # Identify conversion challenges
            challenges = self._identify_conversion_challenges(features, categorized_features)
            feature_results['conversion_challenges'] = challenges
            
            response = {
                "success": True,
                "feature_results": feature_results,
                "feature_summary": self._generate_feature_summary(feature_results)
            }
            
            logger.info(f"Identified {len(features)} features in: {mod_path}")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to identify features: {str(e)}"}
            logger.error(f"Feature identification error: {e}")
            return json.dumps(error_response)
    
    def analyze_dependencies(self, dependency_data: str) -> str:
        """
        Analyze mod dependencies and their impact on conversion.
        
        Args:
            dependency_data: JSON string containing mod metadata and dependency analysis options
        
        Returns:
            JSON string with dependency analysis results
        """
        try:
            data = json.loads(dependency_data)
            mod_metadata = data.get('mod_metadata', {})
            analysis_depth = data.get('analysis_depth', 'standard')
            
            dependency_results = {
                'direct_dependencies': [],
                'transitive_dependencies': [],
                'framework_dependencies': [],
                'conversion_impact': {},
                'compatibility_concerns': []
            }
            
            # Analyze direct dependencies
            direct_deps = self._analyze_direct_dependencies(mod_metadata)
            dependency_results['direct_dependencies'] = direct_deps
            
            # Analyze framework dependencies
            framework_deps = self._analyze_framework_dependencies(mod_metadata)
            dependency_results['framework_dependencies'] = framework_deps
            
            # Assess conversion impact
            impact_analysis = self._assess_dependency_conversion_impact(direct_deps, framework_deps)
            dependency_results['conversion_impact'] = impact_analysis
            
            # Identify compatibility concerns
            concerns = self._identify_compatibility_concerns(direct_deps, framework_deps)
            dependency_results['compatibility_concerns'] = concerns
            
            response = {
                "success": True,
                "dependency_analysis": dependency_results,
                "recommendations": self._generate_dependency_recommendations(dependency_results)
            }
            
            logger.info(f"Analyzed dependencies: {len(direct_deps)} direct, {len(framework_deps)} framework")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to analyze dependencies: {str(e)}"}
            logger.error(f"Dependency analysis error: {e}")
            return json.dumps(error_response)
    
    def extract_assets(self, asset_data: str) -> str:
        """
        Extract and categorize assets from the Java mod.
        
        Args:
            asset_data: JSON string containing mod path and asset extraction options
        
        Returns:
            JSON string with extracted asset information
        """
        try:
            data = json.loads(asset_data)
            mod_path = data.get('mod_path', '')
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
                assets = self._extract_assets_from_jar(mod_path, asset_types)
            else:
                assets = self._extract_assets_from_source(mod_path, asset_types)
            
            # Categorize assets
            for asset in assets:
                asset_type = self._determine_asset_type(asset)
                if asset_type in asset_results:
                    asset_results[asset_type].append(asset)
                else:
                    asset_results['other_assets'].append(asset)
            
            # Generate asset summary
            summary = self._generate_asset_summary(asset_results)
            asset_results['asset_summary'] = summary
            
            response = {
                "success": True,
                "assets": asset_results,
                "conversion_notes": self._generate_asset_conversion_notes(asset_results)
            }
            
            total_assets = sum(len(assets) for assets in asset_results.values() if isinstance(assets, list))
            logger.info(f"Extracted {total_assets} assets from: {mod_path}")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to extract assets: {str(e)}"}
            logger.error(f"Asset extraction error: {e}")
            return json.dumps(error_response)
    
    # Helper methods for mod analysis
    
    def _determine_mod_type_and_framework(self, mod_path: str) -> Dict[str, str]:
        """Determine mod type (jar, source, etc.) and framework (forge, fabric, etc.)"""
        if mod_path.endswith(('.jar', '.zip')):
            mod_type = 'jar'
            framework = self._detect_framework_from_jar(mod_path)
        elif os.path.isdir(mod_path):
            mod_type = 'source'
            framework = self._detect_framework_from_source(mod_path)
        else:
            mod_type = 'unknown'
            framework = 'unknown'
        
        return {'type': mod_type, 'framework': framework}
    
    def _detect_framework_from_jar(self, jar_path: str) -> str:
        """Detect modding framework from JAR file contents"""
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                file_list = jar.namelist()
                
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
                        except:
                            continue
                
                return 'unknown'
        except:
            return 'unknown'
    
    def _detect_framework_from_source(self, source_path: str) -> str:
        """Detect modding framework from source directory"""
        try:
            # Check for framework-specific files
            for root, dirs, files in os.walk(source_path):
                for file_name in files:
                    for framework, indicators in self.framework_indicators.items():
                        if file_name in indicators:
                            return framework
                
                # Check file contents
                for file_name in files:
                    if file_name.endswith('.java'):
                        try:
                            file_path = os.path.join(root, file_name)
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                for framework, indicators in self.framework_indicators.items():
                                    for indicator in indicators:
                                        if indicator in content:
                                            return framework
                        except:
                            continue
            
            return 'unknown'
        except:
            return 'unknown'
    
    def _analyze_jar_structure(self, jar_path: str, analysis_depth: str) -> Dict:
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
                        if self._is_main_class(file_name):
                            structure['main_classes'].append(file_name)
                    
                    elif any(file_name.endswith(ext) for ext in self.file_patterns['resource_files']):
                        structure['resource_files'].append(file_name)
                    
                    elif any(metadata in file_name for metadata in self.file_patterns['metadata_files']):
                        structure['metadata_files'].append(file_name)
        
        except Exception as e:
            logger.warning(f"Error analyzing JAR structure: {e}")
        
        return structure
    
    def _analyze_source_structure(self, source_path: str, analysis_depth: str) -> Dict:
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
                    elif any(file_name.endswith(ext) for ext in self.file_patterns['resource_files']):
                        structure['resource_files'].append(rel_path)
                    elif any(file_name.endswith(ext) for ext in self.file_patterns['config_files']):
                        structure['config_files'].append(rel_path)
                    elif file_name in ['build.gradle', 'pom.xml', 'build.xml']:
                        structure['build_files'].append(rel_path)
        
        except Exception as e:
            logger.warning(f"Error analyzing source structure: {e}")
        
        return structure
    
    def _analyze_unknown_structure(self, mod_path: str, analysis_depth: str) -> Dict:
        """Analyze unknown file type structure"""
        return {
            'type': 'unknown',
            'path': mod_path,
            'size': os.path.getsize(mod_path) if os.path.exists(mod_path) else 0,
            'analysis_note': 'Unknown file type - limited analysis available'
        }
    
    def _create_file_inventory(self, mod_path: str, mod_type: str) -> Dict:
        """Create comprehensive file inventory"""
        inventory = {
            'by_type': {},
            'by_size': {},
            'total_count': 0,
            'total_size': 0
        }
        
        if mod_type == 'jar':
            inventory = self._inventory_jar_files(mod_path)
        elif mod_type == 'source':
            inventory = self._inventory_source_files(mod_path)
        
        return inventory
    
    def _inventory_jar_files(self, jar_path: str) -> Dict:
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
    
    def _inventory_source_files(self, source_path: str) -> Dict:
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
    
    def _assess_mod_complexity(self, structure: Dict, file_inventory: Dict) -> Dict:
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
    
    def _extract_features_from_jar(self, jar_path: str, extraction_mode: str) -> List[Dict]:
        """Extract features from JAR file"""
        features = []
        
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                for file_info in jar.infolist():
                    if file_info.filename.endswith('.class'):
                        # Simplified feature extraction from class names
                        class_name = Path(file_info.filename).stem
                        detected_features = self._detect_features_from_class_name(class_name)
                        features.extend(detected_features)
        
        except Exception as e:
            logger.warning(f"Error extracting features from JAR: {e}")
        
        return features
    
    def _extract_features_from_source(self, source_path: str, extraction_mode: str) -> List[Dict]:
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
                                detected_features = self._detect_features_from_content(content, file_name)
                                features.extend(detected_features)
                        except Exception as e:
                            logger.warning(f"Error reading {file_path}: {e}")
        
        except Exception as e:
            logger.warning(f"Error extracting features from source: {e}")
        
        return features
    
    def _detect_features_from_class_name(self, class_name: str) -> List[Dict]:
        """Detect features based on class name patterns"""
        features = []
        
        for feature_type, patterns in self.feature_patterns.items():
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
    
    def _detect_features_from_content(self, content: str, file_name: str) -> List[Dict]:
        """Detect features from source file content"""
        features = []
        
        for feature_type, patterns in self.feature_patterns.items():
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
    
    # Additional helper methods (simplified for space)
    
    def _categorize_features(self, features: List[Dict]) -> Dict:
        """Categorize features by type"""
        categories = {}
        for feature in features:
            feature_type = feature.get('feature_type', 'unknown')
            if feature_type not in categories:
                categories[feature_type] = []
            categories[feature_type].append(feature)
        return categories
    
    def _analyze_feature_complexity(self, features: List[Dict]) -> Dict:
        """Analyze complexity of identified features"""
        return {
            'total_features': len(features),
            'complexity_distribution': {'simple': 0, 'moderate': 0, 'complex': 0},
            'high_priority_features': [f for f in features if f.get('confidence') == 'high']
        }
    
    def _identify_conversion_challenges(self, features: List[Dict], categories: Dict) -> List[str]:
        """Identify potential conversion challenges"""
        challenges = []
        
        if 'dimensions' in categories:
            challenges.append('Custom dimensions require structural workarounds')
        
        if 'gui' in categories:
            challenges.append('Custom GUIs need alternative interfaces')
        
        if 'machinery' in categories:
            challenges.append('Complex machinery may lose functionality')
        
        return challenges
    
    def _extract_jar_metadata(self, jar_path: str) -> Dict:
        """Extract metadata from JAR file"""
        metadata = {}
        
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                # Look for metadata files
                for metadata_file in self.file_patterns['metadata_files']:
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
    
    def _extract_source_metadata(self, source_path: str) -> Dict:
        """Extract metadata from source directory"""
        metadata = {}
        
        try:
            for root, dirs, files in os.walk(source_path):
                for file_name in files:
                    if file_name in self.file_patterns['metadata_files']:
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
    
    # Additional placeholder methods
    def _is_main_class(self, class_path: str) -> bool:
        """Check if a class is a main mod class"""
        return 'mod' in class_path.lower() and ('main' in class_path.lower() or class_path.count('/') <= 3)
    
    def _generate_analysis_recommendations(self, analysis: Dict) -> List[str]:
        """Generate recommendations based on analysis"""
        return ["Complete feature extraction for detailed conversion planning"]
    
    def _summarize_metadata(self, metadata: Dict) -> Dict:
        """Summarize extracted metadata"""
        return {"summary": "Metadata extraction completed"}
    
    def _generate_feature_summary(self, results: Dict) -> Dict:
        """Generate feature summary"""
        return {"summary": f"Identified {len(results.get('identified_features', []))} features"}
    
    def _analyze_direct_dependencies(self, metadata: Dict) -> List[Dict]:
        """Analyze direct dependencies"""
        return []  # Placeholder
    
    def _analyze_framework_dependencies(self, metadata: Dict) -> List[Dict]:
        """Analyze framework dependencies"""
        return []  # Placeholder
    
    def _assess_dependency_conversion_impact(self, direct: List, framework: List) -> Dict:
        """Assess conversion impact of dependencies"""
        return {"impact": "low"}  # Placeholder
    
    def _identify_compatibility_concerns(self, direct: List, framework: List) -> List[str]:
        """Identify compatibility concerns"""
        return []  # Placeholder
    
    def _generate_dependency_recommendations(self, results: Dict) -> List[str]:
        """Generate dependency recommendations"""
        return ["Review dependencies for Bedrock compatibility"]
    
    def _extract_assets_from_jar(self, jar_path: str, asset_types: List[str]) -> List[Dict]:
        """Extract assets from JAR"""
        return []  # Placeholder
    
    def _extract_assets_from_source(self, source_path: str, asset_types: List[str]) -> List[Dict]:
        """Extract assets from source"""
        return []  # Placeholder
    
    def _determine_asset_type(self, asset: Dict) -> str:
        """Determine asset type"""
        return "other_assets"  # Placeholder
    
    def _generate_asset_summary(self, assets: Dict) -> Dict:
        """Generate asset summary"""
        return {"summary": "Asset extraction completed"}
    
    def _generate_asset_conversion_notes(self, assets: Dict) -> List[str]:
        """Generate asset conversion notes"""
        return ["Assets ready for conversion analysis"]
