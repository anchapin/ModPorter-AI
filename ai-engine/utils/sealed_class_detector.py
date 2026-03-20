"""Sealed Class Detector for Java 17+ to TypeScript conversion.

This module provides functionality to detect and analyze Java sealed classes
in source code AST for conversion to TypeScript discriminated unions.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import re
import javalang
from javalang.tree import ClassDeclaration


@dataclass
class SealedClass:
    """Represents a Java sealed class."""
    name: str
    is_interface: bool = False
    permits: List[str] = field(default_factory=list)
    line_number: Optional[int] = None
    is_nested: bool = False
    
    def __repr__(self) -> str:
        return f"SealedClass({self.name}, permits={self.permits})"


@dataclass
class PermittedSubclass:
    """Represents a permitted subclass of a sealed class."""
    name: str
    is_sealed: bool = False
    is_final: bool = False
    is_non_sealed: bool = False
    extends: Optional[str] = None
    line_number: Optional[int] = None
    
    def __repr__(self) -> str:
        return f"PermittedSubclass({self.name}, sealed={self.is_sealed}, final={self.is_final})"


class SealedClassDetector:
    """Detects Java sealed classes in source code."""
    
    def __init__(self):
        self.sealed_classes: List[SealedClass] = []
        self.permitted_subclasses: List[PermittedSubclass] = []
    
    def detect(self, source: str) -> List[SealedClass]:
        """Detect all Java sealed classes in source code."""
        self.sealed_classes = []
        self.permitted_subclasses = []
        
        try:
            tree = javalang.parse.parse(source)
            
            for path, node in tree:
                if isinstance(node, ClassDeclaration):
                    # Check for sealed modifier
                    if self._is_sealed(node):
                        sealed_class = self._process_sealed_class(node, path)
                        if sealed_class:
                            self.sealed_classes.append(sealed_class)
                    
                    # Check for permitted subclass (non-sealed, final)
                    if self._is_permitted_subclass(node):
                        subclass = self._process_subclass(node, path)
                        if subclass:
                            self.permitted_subclasses.append(subclass)
        except javalang.parser.JavaSyntaxError:
            # Fallback to regex detection
            self._detect_with_regex(source)
        
        return self.sealed_classes
    
    def _is_sealed(self, node: ClassDeclaration) -> bool:
        """Check if a class is sealed."""
        if hasattr(node, 'modifiers'):
            modifiers = node.modifiers
            if modifiers and 'sealed' in str(modifiers).lower():
                return True
        return False
    
    def _is_permitted_subclass(self, node: ClassDeclaration) -> bool:
        """Check if a class is a permitted subclass (non-sealed or final)."""
        if hasattr(node, 'modifiers'):
            modifiers = node.modifiers
            if modifiers:
                mod_str = str(modifiers).lower()
                return 'non-sealed' in mod_str or 'final' in mod_str
        return False
    
    def _process_sealed_class(self, node: ClassDeclaration, path: List) -> Optional[SealedClass]:
        """Process a sealed class declaration."""
        is_interface = hasattr(node, 'interface') and node.interface
        
        # Extract permits clause from body
        permits = []
        if hasattr(node, 'body') and node.body:
            for item in node.body:
                # Look for permits declaration
                if hasattr(item, '__class__'):
                    class_name = item.__class__.__name__
                    if 'Permits' in class_name or (hasattr(item, 'references') and item.references):
                        # This is a permits clause
                        if hasattr(item, 'references'):
                            permits = [str(r) for r in item.references]
        
        return SealedClass(
            name=node.name,
            is_interface=is_interface,
            permits=permits,
            line_number=node.position[0] if node.position else None,
            is_nested=len(path) > 1
        )
    
    def _process_subclass(self, node: ClassDeclaration, path: List) -> Optional[PermittedSubclass]:
        """Process a permitted subclass declaration."""
        modifiers = str(node.modifiers) if hasattr(node, 'modifiers') else ''
        
        subclass = PermittedSubclass(
            name=node.name,
            is_sealed='sealed' in modifiers.lower(),
            is_final='final' in modifiers.lower(),
            is_non_sealed='non-sealed' in modifiers.lower(),
            line_number=node.position[0] if node.position else None
        )
        
        if hasattr(node, 'extenders') and node.extenders:
            subclass.extends = str(node.extenders[0]) if node.extenders else None
        
        return subclass
    
    def _detect_with_regex(self, source: str) -> None:
        """Fallback regex-based sealed class detection."""
        # Match sealed class declarations
        sealed_pattern = r'(sealed|non-sealed|final)\s+(class|interface)\s+(\w+)\s+(?:permits\s+([^{]+))?\{'
        
        for match in re.finditer(sealed_pattern, source):
            modifier = match.group(1)
            is_interface = match.group(2) == 'interface'
            name = match.group(3)
            permits_str = match.group(4)
            
            if modifier == 'sealed':
                permits = []
                if permits_str:
                    permits = [p.strip() for p in permits_str.split(',')]
                
                self.sealed_classes.append(SealedClass(
                    name=name,
                    is_interface=is_interface,
                    permits=permits
                ))
            else:
                self.permitted_subclasses.append(PermittedSubclass(
                    name=name,
                    is_final=modifier == 'final',
                    is_non_sealed=modifier == 'non-sealed'
                ))
    
    def get_sealed_class(self, name: str) -> Optional[SealedClass]:
        """Get a sealed class by name."""
        for sc in self.sealed_classes:
            if sc.name == name:
                return sc
        return None
    
    def get_subclasses_for(self, sealed_name: str) -> List[PermittedSubclass]:
        """Get permitted subclasses for a sealed class."""
        # Find the sealed class to get its permits
        sealed = self.get_sealed_class(sealed_name)
        if not sealed:
            return []
        
        # Return subclasses that are in the permits list
        return [s for s in self.permitted_subclasses if s.name in sealed.permits]


# Convenience function
def detect_sealed_classes(source: str) -> List[SealedClass]:
    """Detect all Java sealed classes in source code."""
    detector = SealedClassDetector()
    return detector.detect(source)


def is_sealed_class(source: str, name: str) -> bool:
    """Check if a class is sealed in the source."""
    detector = SealedClassDetector()
    sealed_classes = detector.detect(source)
    return any(sc.name == name for sc in sealed_classes)
