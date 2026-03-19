"""
Correlation Checker

Verifies output components match input mod structure.
"""

import logging
import zipfile
from typing import Dict, Any, List, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class CorrelationResult:
    """Result of correlation verification."""
    is_correlated: bool
    correlation_score: float
    input_elements: List[str] = field(default_factory=list)
    output_elements: List[str] = field(default_factory=list)
    mapped_elements: List[Dict[str, Any]] = field(default_factory=list)
    orphaned_output: List[str] = field(default_factory=list)
    missing_components: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class CorrelationChecker:
    """
    Verifies output components match input mod.
    
    Maps input elements to output files to ensure
    conversion properly represents the original mod.
    """
    
    # Keywords that indicate certain mod elements
    ELEMENT_KEYWORDS = {
        'block': ['block', 'cube', 'block_model'],
        'item': ['item', 'tool', 'weapon', 'armor', 'food'],
        'recipe': ['recipe', 'crafting', 'smelting', 'shaped', 'shapeless'],
        'entity': ['entity', 'mob', 'creature', 'animal', 'monster'],
        'biome': ['biome', 'dimension', 'world'],
        'loot_table': ['loot', 'drop', 'treasure'],
        'function': ['function', 'command', 'tick', 'load'],
        'structure': ['structure', 'schematic', 'voxel'],
        'texture': ['texture', 'image', 'skin', 'sprite'],
        'sound': ['sound', 'audio', 'music', 'ambient'],
    }
    
    def __init__(self, min_correlation_threshold: float = 0.5):
        self.min_correlation_threshold = min_correlation_threshold
    
    async def verify_correlation(
        self,
        input_mod: Dict[str, Any],
        output_package: str
    ) -> CorrelationResult:
        """
        Verify output matches input structure.
        
        Args:
            input_mod: Analysis of the input mod
            output_package: Path to the generated .mcaddon package
            
        Returns:
            CorrelationResult with mapping details
        """
        # Extract input elements
        input_elements = self._extract_input_elements(input_mod)
        
        # Extract output elements
        output_elements = self._extract_output_elements(output_package)
        
        # Map elements
        mapped, orphaned = self._map_elements(input_elements, output_elements)
        
        # Find missing components
        missing = self._find_missing_components(input_elements, mapped)
        
        # Calculate correlation score
        if len(input_elements) > 0:
            correlation_score = len(mapped) / len(input_elements)
        else:
            correlation_score = 1.0 if len(output_elements) > 0 else 0.0
        
        is_correlated = correlation_score >= self.min_correlation_threshold
        
        return CorrelationResult(
            is_correlated=is_correlated,
            correlation_score=correlation_score,
            input_elements=list(input_elements),
            output_elements=output_elements,
            mapped_elements=mapped,
            orphaned_output=orphaned,
            missing_components=missing,
            details={
                'input_element_count': len(input_elements),
                'output_element_count': len(output_elements),
                'mapped_count': len(mapped),
                'orphaned_count': len(orphaned),
                'missing_count': len(missing)
            }
        )
    
    def _extract_input_elements(self, input_mod: Dict[str, Any]) -> Set[str]:
        """Extract all identifiable elements from input mod."""
        elements = set()
        
        # Extract from components
        components = input_mod.get('components', {})
        for comp_type, comp_list in components.items():
            if isinstance(comp_list, list):
                for comp in comp_list:
                    if isinstance(comp, dict):
                        name = comp.get('name') or comp.get('identifier') or comp.get('id')
                        if name:
                            elements.add(f"{comp_type}:{name}")
        
        # Extract from direct keys
        for key in ['blocks', 'items', 'recipes', 'entities', 'biomes', 
                    'loot_tables', 'functions', 'structures']:
            if key in input_mod:
                items = input_mod[key]
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            name = item.get('name') or item.get('identifier')
                            if name:
                                elements.add(f"{key}:{name}")
        
        # Extract class names from Java code (if available)
        java_code = input_mod.get('java_code', input_mod.get('source_code', ''))
        if java_code:
            class_names = self._extract_java_classes(java_code)
            elements.update(class_names)
        
        return elements
    
    def _extract_java_classes(self, java_code: str) -> Set[str]:
        """Extract class names from Java source code."""
        import re
        classes = set()
        
        # Match class declarations
        class_pattern = r'(?:public\s+|private\s+|protected\s+)?class\s+(\w+)'
        for match in re.finditer(class_pattern, java_code):
            class_name = match.group(1)
            classes.add(f"java_class:{class_name}")
        
        return classes
    
    def _extract_output_elements(self, package_path: str) -> List[str]:
        """Extract all identifiable elements from output package."""
        elements = []
        
        try:
            with zipfile.ZipFile(package_path, 'r') as zf:
                for file_path in zf.namelist():
                    if file_path.endswith('/'):
                        continue
                    
                    # Normalize path
                    normalized = file_path.lower().replace('\\', '/')
                    
                    # Extract element from path
                    # Example: "blocks/minecraft/block_grass.json" -> "block_grass"
                    parts = normalized.split('/')
                    
                    # Try to identify element type
                    element_type = None
                    element_name = None
                    
                    for i, part in enumerate(parts):
                        for etype, keywords in self.ELEMENT_KEYWORDS.items():
                            if any(kw in part for kw in keywords):
                                element_type = etype
                                # Try to get name from filename
                                if i + 1 < len(parts):
                                    name_part = parts[i + 1]
                                    if '.' in name_part:
                                        name_part = name_part.rsplit('.', 1)[0]
                                    element_name = name_part
                                break
                        if element_type:
                            break
                    
                    if element_type and element_name:
                        elements.append(f"{element_type}:{element_name}")
                    elif element_type:
                        elements.append(f"{element_type}:unknown")
        
        except Exception as e:
            logger.error(f"Failed to extract output elements: {e}")
        
        return elements
    
    def _map_elements(
        self,
        input_elements: Set[str],
        output_elements: List[str]
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Map input elements to output elements."""
        mapped = []
        orphaned = []
        
        output_lower = [e.lower() for e in output_elements]
        
        for input_elem in input_elements:
            input_type, _, input_name = input_elem.partition(':')
            input_name_lower = input_name.lower()
            
            found = False
            matched_output = None
            
            for i, output_elem in enumerate(output_elements):
                output_type, _, output_name = output_elem.partition(':')
                
                # Check for type match and name similarity
                if input_type == output_type:
                    # Check for name similarity
                    if (input_name_lower in output_name.lower() or 
                        output_name.lower() in input_name_lower or
                        self._similar_names(input_name_lower, output_name.lower())):
                        found = True
                        matched_output = output_elem
                        break
            
            mapped.append({
                'input': input_elem,
                'output': matched_output,
                'matched': found
            })
        
        # Find orphaned output (output not mapped to any input)
        mapped_outputs = [m['output'] for m in mapped if m['output']]
        for output_elem in output_elements:
            if output_elem not in mapped_outputs:
                orphaned.append(output_elem)
        
        return mapped, orphaned
    
    def _similar_names(self, name1: str, name2: str) -> bool:
        """Check if two names are similar (simple fuzzy matching)."""
        if not name1 or not name2:
            return False
        
        # Check if one is substring of other
        if name1 in name2 or name2 in name1:
            return True
        
        # Check first word match
        words1 = name1.split('_')
        words2 = name2.split('_')
        
        if words1[0] == words2[0]:
            return True
        
        return False
    
    def _find_missing_components(
        self,
        input_elements: Set[str],
        mapped: List[Dict[str, Any]]
    ) -> List[str]:
        """Find components that were expected but not found in output."""
        missing = []
        
        for mapping in mapped:
            if not mapping['matched']:
                missing.append(mapping['input'])
        
        return missing
