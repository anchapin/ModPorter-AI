"""Record Detector for Java 14+ to TypeScript conversion.

This module provides functionality to detect and analyze Java records
in source code AST for conversion to TypeScript.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import re
import javalang
from javalang.tree import ClassDeclaration


@dataclass
class RecordComponent:
    """Represents a component (field) of a Java record."""
    name: str
    type: str
    
    def __repr__(self) -> str:
        return f"RecordComponent({self.name}: {self.type})"


@dataclass
class RecordMethod:
    """Represents a method in a Java record."""
    name: str
    return_type: str
    parameters: List[tuple] = field(default_factory=list)
    is_compact_constructor: bool = False
    
    def __repr__(self) -> str:
        return f"RecordMethod({self.name}: {self.return_type})"


@dataclass
class JavaRecord:
    """Represents a complete Java record."""
    name: str
    components: List[RecordComponent] = field(default_factory=list)
    methods: List[RecordMethod] = field(default_factory=list)
    extends: Optional[str] = None
    implements: List[str] = field(default_factory=list)
    line_number: Optional[int] = None
    is_nested: bool = False
    
    def __repr__(self) -> str:
        return f"JavaRecord({self.name}, components={len(self.components)}, methods={len(self.methods)})"


class RecordDetector:
    """Detects Java records in source code."""
    
    def __init__(self):
        self.records: List[JavaRecord] = []
    
    def detect(self, source: str) -> List[JavaRecord]:
        """Detect all Java records in source code."""
        self.records = []
        
        try:
            tree = javalang.parse.parse(source)
            
            for path, node in tree:
                if isinstance(node, ClassDeclaration):
                    # Check if this is a record (has record keyword)
                    if self._is_record(node, path):
                        record = self._process_record(node, path)
                        if record:
                            self.records.append(record)
        except javalang.parser.JavaSyntaxError:
            # Fallback to regex detection
            self._detect_with_regex(source)
        
        return self.records
    
    def _is_record(self, node: ClassDeclaration, path: List) -> bool:
        """Check if a class declaration is actually a record."""
        # In javalang, records are represented as classes with special properties
        # Check if it has record components (formal parameters in declaration)
        if hasattr(node, 'extenders') and node.extenders:
            # Check if it extends anything special
            pass
        
        # Use name pattern - records often have "Record" suffix or specific pattern
        if node.name:
            # Check for record declaration in body
            if hasattr(node, 'body') and node.body:
                for item in node.body:
                    if hasattr(item, '__class__') and item.__class__.__name__ == 'RecordDeclaration':
                        return True
        
        return False
    
    def _process_record(self, node: ClassDeclaration, path: List) -> Optional[JavaRecord]:
        """Process a record declaration."""
        record = JavaRecord(
            name=node.name,
            line_number=node.position[0] if node.position else None,
            is_nested=len(path) > 1
        )
        
        # Process extends
        if hasattr(node, 'extenders') and node.extenders:
            record.extends = str(node.extenders[0]) if node.extenders else None
        
        # Process implements
        if hasattr(node, 'implementors') and node.implementors:
            record.implements = [str(i) for i in node.implementors]
        
        # Process body for components and methods
        if hasattr(node, 'body') and node.body:
            for item in node.body:
                if isinstance(item, javalang.tree.FieldDeclaration):
                    # This could be a record component
                    if hasattr(item, 'declarators'):
                        for declarator in item.declarators:
                            record.components.append(RecordComponent(
                                name=declarator.name,
                                type=str(item.type) if item.type else 'unknown'
                            ))
                elif isinstance(item, javalang.tree.MethodDeclaration):
                    record.methods.append(RecordMethod(
                        name=item.name,
                        return_type=str(item.return_type) if item.return_type else 'void'
                    ))
        
        return record
    
    def _detect_with_regex(self, source: str) -> None:
        """Fallback regex-based record detection."""
        # Match record declarations
        record_pattern = r'record\s+(\w+)\s*\(([^)]*)\)(?:\s+implements\s+([^{]+))?(?:\s*\{)'
        
        for match in re.finditer(record_pattern, source):
            name = match.group(1)
            components_str = match.group(2)
            implements_str = match.group(3)
            
            record = JavaRecord(name=name)
            
            # Parse components
            if components_str:
                for comp in components_str.split(','):
                    comp = comp.strip()
                    if comp:
                        parts = comp.split()
                        if len(parts) >= 2:
                            record.components.append(RecordComponent(
                                name=parts[1],
                                type=parts[0]
                            ))
            
            # Parse implements
            if implements_str:
                record.implements = [i.strip() for i in implements_str.split(',')]
            
            self.records.append(record)
    
    def detect_flat(self, source: str) -> List[JavaRecord]:
        """Flatten nested records detection."""
        return self.detect(source)
    
    def get_record_names(self) -> List[str]:
        """Get list of all detected record names."""
        return [r.name for r in self.records]
    
    def find_record(self, name: str) -> Optional[JavaRecord]:
        """Find a record by name."""
        for record in self.records:
            if record.name == name:
                return record
        return None


# Convenience function
def detect_records(source: str) -> List[JavaRecord]:
    """Detect all Java records in source code."""
    detector = RecordDetector()
    return detector.detect(source)


def is_record(source: str, name: str) -> bool:
    """Check if a name refers to a record in the source."""
    detector = RecordDetector()
    records = detector.detect(name)
    return any(r.name == name for r in records)
