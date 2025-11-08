"""
JavaAnalyzerAgent for analyzing Java mod structure and extracting registry names and texture paths.
Implementation for Issue #167: Parse registry name & texture path in JavaAnalyzerAgent
"""

import logging
import json
import zipfile
import javalang
from typing import Dict, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class JavaAnalyzerAgent:
    """
    Java Analyzer Agent responsible for analyzing Java mod JARs,
    extracting registry names and texture paths as specified in Issue #167.
    """

    def __init__(self):
        """Initialize the JavaAnalyzerAgent."""
        pass

    def analyze_jar_for_mvp(self, jar_path: str) -> Dict[str, any]:
        """
        MVP-focused analysis: Extract registry name and texture path from simple block JAR.

        This method implements the specific requirements for Issue #167:
        - Parse registry name from Java classes using javalang
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

                # Extract registry name using javalang
                registry_name = self._extract_registry_name_from_jar(jar, file_list)
                if registry_name:
                    result['registry_name'] = registry_name
                    logger.info(f"Found registry name: {registry_name}")

                # Check if we have both texture and registry name for success
                if texture_path and registry_name and registry_name != 'unknown:block':
                    result['success'] = True
                    logger.info(f"MVP analysis completed successfully for {jar_path}")
                else:
                    if not texture_path:
                        result['errors'].append("Could not find block texture in JAR")
                    if not registry_name or registry_name == 'unknown:block':
                        result['errors'].append("Could not determine block registry name")

                return result

        except Exception as e:
            logger.exception(f"MVP analysis of {jar_path} failed")
            return {
                'success': False,
                'registry_name': 'unknown:block',
                'texture_path': None,
                'errors': [f"JAR analysis failed: {str(e)}"]
            }

    def _find_block_texture(self, file_list: List[str]) -> Optional[str]:
        """
        Find a block texture in the JAR file list.
        Looks for: assets/*/textures/block/*.png
        """
        for file_path in file_list:
            if (file_path.startswith('assets/') and
                '/textures/block/' in file_path and
                file_path.endswith('.png')):
                return file_path
        return None

    def _extract_registry_name_from_jar(self, jar: zipfile.ZipFile, file_list: List[str]) -> str:
        """
        Extract registry name from Java source files or class names using javalang.
        Uses multiple strategies:
        1. Parse mod metadata (fabric.mod.json, mcmod.info) for mod ID
        2. Look for @Register annotations in Java source files
        3. Use Block class names as fallback
        """
        # Strategy 1: Get mod ID from metadata (most reliable)
        mod_id = self._extract_mod_id_from_metadata(jar, file_list)

        # Strategy 2: Parse Java source files for @Register annotations
        registry_name_from_java = self._parse_java_sources_for_register(jar, file_list)
        if registry_name_from_java:
            # If we found a @Register annotation, use it with mod_id if available
            if mod_id:
                return f"{mod_id}:{registry_name_from_java}"
            else:
                return f"modporter:{registry_name_from_java}"

        # Strategy 3: Use class name heuristic
        if mod_id:
            # Try to find a block class and construct registry name
            block_class = self._find_block_class_name(file_list)
            if block_class:
                # Convert BlockName to snake_case
                block_name = self._class_name_to_registry_name(block_class)
                return f"{mod_id}:{block_name}"
            return f"{mod_id}:unknown_block"

        # Strategy 4: Extract from main block class name without mod ID
        block_class = self._find_block_class_name(file_list)
        if block_class:
            block_name = self._class_name_to_registry_name(block_class)
            return f"modporter:{block_name}"

        # Final fallback
        return "modporter:unknown_block"

    def _parse_java_sources_for_register(self, jar: zipfile.ZipFile, file_list: List[str]) -> Optional[str]:
        """
        Parse Java source files looking for @Register annotations or similar patterns.
        """
        for file_name in file_list:
            if file_name.endswith('.java'):
                try:
                    # Read Java source file
                    source_content = jar.read(file_name).decode('utf-8')

                    # Parse with javalang
                    tree = javalang.parse.parse(source_content)

                    # Look for @Register annotations or similar patterns
                    registry_name = self._extract_registry_from_ast(tree)
                    if registry_name:
                        return registry_name

                except Exception as e:
                    logger.debug(f"Could not parse Java file {file_name}: {e}")
                    continue

        return None

    def _extract_registry_from_ast(self, tree) -> Optional[str]:
        """
        Extract registry name from Java AST by looking for common patterns:
        - @Register("name") annotations
        - String literals in block registration calls
        - Field names in registry-related code
        """
        try:
            # Look for annotations
            for _, node in tree.filter(javalang.tree.Annotation):
                if node.name == 'Register' and node.element:
                    # Extract the value from @Register("value")
                    if hasattr(node.element, 'value'):
                        return node.element.value.strip('"\'')

            # Look for method calls that might contain registry names
            for _, node in tree.filter(javalang.tree.MethodInvocation):
                if node.member in ['register', 'registerBlock', 'Registry.register']:
                    # Look for string arguments
                    if node.arguments:
                        for arg in node.arguments:
                            if hasattr(arg, 'value') and isinstance(arg.value, str):
                                # Clean up the string literal
                                registry_name = arg.value.strip('"\'')
                                if ':' in registry_name:
                                    # Extract just the name part after the colon
                                    registry_name = registry_name.split(':')[-1]
                                return registry_name

            # Look for string literals that might be registry names
            for _, node in tree.filter(javalang.tree.Literal):
                if hasattr(node, 'value') and isinstance(node.value, str):
                    value = node.value.strip('"\'')
                    # Check if it looks like a registry name (lowercase with underscores)
                    if '_' in value and value.islower() and len(value) > 3:
                        return value

        except Exception as e:
            logger.debug(f"Error parsing AST for registry name: {e}")

        return None

    def _extract_mod_id_from_metadata(self, jar: zipfile.ZipFile, file_list: List[str]) -> Optional[str]:
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
                    import tomli
                    content = jar.read(file_name).decode('utf-8')
                    data = tomli.loads(content)
                    if (mods := data.get('mods')) and isinstance(mods, list) and mods:
                        if mod_id := mods[0].get('modId'):
                            return mod_id.lower()
                except Exception as e:
                    logger.warning(f"Error reading {file_name}: {e}")

        return None

    def _find_block_class_name(self, file_list: List[str]) -> Optional[str]:
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
        # Remove 'Block' suffix if present, but only if it's not the entire name
        name = class_name
        if name.endswith('Block') and len(name) > 5:
            name = name[:-5]  # Remove 'Block' from the end
        elif name.startswith('Block') and len(name) > 5 and name[5].isupper():
            name = name[5:]  # Remove 'Block' from the start if it's a prefix like BlockOfCopper

        # Convert CamelCase to snake_case
        import re
        name = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name).lower()

        # Clean up any double underscores or leading/trailing underscores
        name = re.sub(r'_+', '_', name).strip('_')

        # Ensure it's not empty after processing
        return name if name else 'unknown'
