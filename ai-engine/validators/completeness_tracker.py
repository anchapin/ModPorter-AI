"""
Completeness Tracker

Tracks output completeness vs. expected components from mod analysis.
"""

import logging
import zipfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ComponentMatch:
    """Represents a matched component between input and output."""
    component_type: str
    component_name: str
    expected: bool
    found: bool
    output_path: Optional[str] = None


@dataclass
class CompletenessResult:
    """Result of completeness verification."""
    completeness_percentage: float
    matched_components: List[ComponentMatch] = field(default_factory=list)
    missing_components: List[str] = field(default_factory=list)
    unexpected_components: List[str] = field(default_factory=list)
    component_counts: Dict[str, int] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)


class CompletenessTracker:
    """
    Tracks output completeness vs. expected components.
    
    Compares generated output against expected components from
    the input mod analysis.
    """
    
    # Component type mappings
    COMPONENT_TYPE_MAPPING = {
        'blocks': ['blocks.json', 'block/', 'blocks/'],
        'items': ['items.json', 'item/', 'items/'],
        'recipes': ['recipes.json', 'recipe/', 'recipes/'],
        'loot_tables': ['loot_tables/', 'loot_table/'],
        'entities': ['entity/', 'entities/'],
        'biomes': ['biomes/', 'biome/'],
        'functions': ['functions/', 'function/'],
        'structures': ['structures/', 'structure/'],
        'textures': ['textures/', 'texture/', 'textures/'],
        'sounds': ['sounds/', 'sound/'],
        'models': ['models/', 'model/'],
        'animations': ['animations/', 'animation/'],
    }
    
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
    
    async def verify_completeness(
        self,
        input_analysis: Dict[str, Any],
        output_package: str
    ) -> CompletenessResult:
        """
        Verify all expected components were generated.
        
        Args:
            input_analysis: Analysis of the input mod (from JavaAnalyzerAgent)
            output_package: Path to the generated .mcaddon package
            
        Returns:
            CompletenessResult with detailed breakdown
        """
        # Extract expected components from input analysis
        expected_components = self._extract_expected_components(input_analysis)
        
        # List generated files from output package
        generated_files = self._list_generated_files(output_package)
        
        # Match components
        matched, missing, unexpected = self._match_components(
            expected_components, 
            generated_files
        )
        
        # Calculate completeness percentage
        total_expected = len(expected_components)
        total_matched = len(matched)
        
        if total_expected > 0:
            completeness = (total_matched / total_expected) * 100
        elif len(generated_files) > 0:
            completeness = 100.0  # No expected components but has output
        else:
            completeness = 0.0
        
        # Component counts
        component_counts = self._count_components(generated_files)
        
        return CompletenessResult(
            completeness_percentage=completeness,
            matched_components=matched,
            missing_components=missing,
            unexpected_components=unexpected,
            component_counts=component_counts,
            details={
                'total_expected': total_expected,
                'total_found': total_matched,
                'total_generated_files': len(generated_files)
            }
        )
    
    def _extract_expected_components(
        self, 
        input_analysis: Dict[str, Any]
    ) -> Set[str]:
        """Extract expected components from input analysis."""
        expected = set()
        
        # Get detected components from analysis
        components = input_analysis.get('components', {})
        
        for component_type, component_list in components.items():
            if isinstance(component_list, list):
                for item in component_list:
                    if isinstance(item, dict):
                        name = item.get('name', item.get('identifier', 'unknown'))
                    else:
                        name = str(item)
                    expected.add(f"{component_type}:{name}")
        
        # Also check for detected blocks, items, recipes, etc.
        for key in ['blocks', 'items', 'recipes', 'entities', 'biomes', 
                    'loot_tables', 'functions', 'structures']:
            if key in input_analysis:
                items = input_analysis[key]
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            name = item.get('name', item.get('identifier', 'unknown'))
                        else:
                            name = str(item)
                        expected.add(f"{key}:{name}")
        
        return expected
    
    def _list_generated_files(self, package_path: str) -> List[str]:
        """List all files in the generated package."""
        generated = []
        
        try:
            with zipfile.ZipFile(package_path, 'r') as zf:
                generated = [f for f in zf.namelist() if not f.endswith('/')]
        except Exception as e:
            logger.error(f"Failed to read package {package_path}: {e}")
        
        return generated
    
    def _match_components(
        self,
        expected: Set[str],
        generated_files: List[str]
    ) -> tuple:
        """Match expected components to generated files."""
        matched = []
        missing = []
        generated_lower = [f.lower() for f in generated_files]
        
        for component in expected:
            found = False
            output_path = None
            
            component_type, _, name = component.partition(':')
            
            # Check for matching files
            patterns = self.COMPONENT_TYPE_MAPPING.get(
                component_type, 
                [component_type.lower() + '/']
            )
            
            for pattern in patterns:
                pattern_lower = pattern.lower()
                for generated_file in generated_files:
                    if pattern_lower in generated_file.lower():
                        if name.lower() in generated_file.lower():
                            found = True
                            output_path = generated_file
                            break
                if found:
                    break
            
            matched.append(ComponentMatch(
                component_type=component_type,
                component_name=name,
                expected=True,
                found=found,
                output_path=output_path
            ))
            
            if not found:
                missing.append(component)
        
        # Find unexpected components (generated but not expected)
        unexpected = []
        # For now, we don't flag unexpected as problematic
        
        return matched, missing, unexpected
    
    def _count_components(self, generated_files: List[str]) -> Dict[str, int]:
        """Count components by type."""
        counts = {
            'json': 0,
            'javascript': 0,
            'textures': 0,
            'sounds': 0,
            'other': 0
        }
        
        for file_path in generated_files:
            file_lower = file_path.lower()
            
            if file_lower.endswith(('.json', '.jsonc')):
                counts['json'] += 1
            elif file_lower.endswith(('.js', '.ts', '.mjs')):
                counts['javascript'] += 1
            elif file_lower.endswith(('.png', '.jpg', '.jpeg')):
                counts['textures'] += 1
            elif file_lower.endswith(('.ogg', '.wav', '.mp3')):
                counts['sounds'] += 1
            else:
                counts['other'] += 1
        
        return counts
