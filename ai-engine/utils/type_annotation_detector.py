"""Type Annotation Detector for Java to Bedrock Conversion.

This module provides functionality to detect and analyze Java type annotations
in source code AST for conversion to TypeScript null-safe types.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set
import re
import javalang
from javalang.tree import Annotation as JavalanAnnotation


# Standard type annotation names
NULLABLE_ANNOTATIONS = {'Nullable', 'Nullable<T>', 'org.jetbrains.annotations.Nullable'}
NOT_NULL_ANNOTATIONS = {'NotNull', 'NonNull', 'NotNull<T>', 'org.jetbrains.annotations.NotNull'}
TYPE_ANNOTATIONS = {'Nullable', 'NotNull', 'NonNull', 'NonNullByDefault', 'CheckForNull', 'ParametersAreNonnullByDefault'}


@dataclass
class TypeAnnotation:
    """Represents a Java type annotation."""
    name: str
    annotation_type: str  # 'nullable', 'not_null', 'custom'
    line_number: Optional[int] = None
    target: Optional[str] = None  # FIELD, PARAMETER, RETURN_TYPE, TYPE_PARAMETER
    is_standard: bool = False
    
    def __repr__(self) -> str:
        return f"TypeAnnotation({self.name}, {self.annotation_type})"


@dataclass
class AnnotatedType:
    """Represents a Java type with annotations."""
    base_type: str
    annotations: List[TypeAnnotation] = field(default_factory=list)
    is_nullable: bool = False
    is_list_element: bool = False
    generic_params: List['AnnotatedType'] = field(default_factory=list)
    
    def to_typescript(self) -> str:
        """Convert to TypeScript type with null safety."""
        base = self.base_type
        
        # Handle generic types
        if self.generic_params:
            generic_str = ', '.join(p.to_typescript() for p in self.generic_params)
            base = f"{base}<{generic_str}>"
        
        # Apply nullability
        if self.is_nullable:
            return f"{base} | null"
        
        return base
    
    def __repr__(self) -> str:
        annots = ', '.join(a.name for a in self.annotations)
        return f"AnnotatedType({self.base_type}, [{annots}])"


class TypeAnnotationDetector:
    """Detects type annotations in Java source code."""
    
    def __init__(self):
        self.annotations: List[TypeAnnotation] = []
        self.annotated_types: Dict[str, AnnotatedType] = {}
    
    def detect(self, source: str) -> List[TypeAnnotation]:
        """Detect all type annotations in Java source code."""
        self.annotations = []
        
        try:
            tree = javalang.parse.parse(source)
            
            for path, node in tree:
                if isinstance(node, JavalanAnnotation):
                    annotation = self._process_annotation(node, path)
                    if annotation:
                        self.annotations.append(annotation)
        except javalang.parser.JavaSyntaxError:
            # Fallback to regex-based detection
            self._detect_with_regex(source)
        
        return self.annotations
    
    def _process_annotation(self, node: JavalanAnnotation, path: List) -> Optional[TypeAnnotation]:
        """Process a javalang annotation node."""
        name = node.name
        
        # Determine annotation type
        annotation_type = 'custom'
        is_standard = False
        
        if name in NULLABLE_ANNOTATIONS:
            annotation_type = 'nullable'
            is_standard = True
        elif name in NOT_NULL_ANNOTATIONS:
            annotation_type = 'not_null'
            is_standard = True
        elif name in TYPE_ANNOTATIONS:
            annotation_type = 'type'
            is_standard = True
        
        # Determine target from AST path
        target = self._determine_target(path)
        
        return TypeAnnotation(
            name=name,
            annotation_type=annotation_type,
            line_number=node.position[0] if node.position else None,
            target=target,
            is_standard=is_standard
        )
    
    def _determine_target(self, path: List) -> Optional[str]:
        """Determine the target of an annotation from AST path."""
        for node in reversed(path):
            if isinstance(node, javalang.tree.MethodDeclaration):
                return 'METHOD'
            elif isinstance(node, javalang.tree.FieldDeclaration):
                return 'FIELD'
            elif isinstance(node, javalang.tree.FormalParameter):
                return 'PARAMETER'
            elif isinstance(node, javalang.tree.ClassDeclaration):
                return 'CLASS'
        return None
    
    def _detect_with_regex(self, source: str) -> None:
        """Fallback regex-based detection for invalid Java syntax."""
        pattern = r'@(\w+(?:\.\w+)*)(?:\([^)]*\))?'
        
        for i, line in enumerate(source.split('\n'), 1):
            for match in re.finditer(pattern, line):
                name = match.group(1)
                
                if name in NULLABLE_ANNOTATIONS:
                    annotation_type = 'nullable'
                    is_standard = True
                elif name in NOT_NULL_ANNOTATIONS:
                    annotation_type = 'not_null'
                    is_standard = True
                else:
                    annotation_type = 'custom'
                    is_standard = name in TYPE_ANNOTATIONS
                
                self.annotations.append(TypeAnnotation(
                    name=name,
                    annotation_type=annotation_type,
                    line_number=i,
                    is_standard=is_standard
                ))
    
    def detect_nullable(self, source: str) -> List[TypeAnnotation]:
        """Detect only nullable annotations."""
        return [a for a in self.detect(source) if a.annotation_type == 'nullable']
    
    def detect_not_null(self, source: str) -> List[TypeAnnotation]:
        """Detect only not-null annotations."""
        return [a for a in self.detect(source) if a.annotation_type == 'not_null']
    
    def get_annotated_types(self, source: str) -> Dict[str, AnnotatedType]:
        """Extract types with their annotations."""
        self.annotated_types = {}
        
        try:
            tree = javalang.parse.parse(source)
            
            for path, node in tree:
                if isinstance(node, javalang.tree.FieldDeclaration):
                    self._process_field_type(node, path)
                elif isinstance(node, javalang.tree.FormalParameter):
                    self._process_parameter_type(node, path)
        except javalang.parser.JavaSyntaxError:
            pass
        
        return self.annotated_types
    
    def _process_field_type(self, node, path: List) -> None:
        """Process a field declaration to extract type annotations."""
        for declarator in node.declarators:
            type_annot = self._find_annotation_for_node(path)
            base_type = str(node.type) if node.type else 'unknown'
            
            is_nullable = any(a.annotation_type == 'nullable' for a in type_annot)
            
            self.annotated_types[declarator.name] = AnnotatedType(
                base_type=base_type,
                annotations=type_annot,
                is_nullable=is_nullable
            )
    
    def _process_parameter_type(self, node, path: List) -> None:
        """Process a formal parameter to extract type annotations."""
        type_annot = self._find_annotation_for_node(path)
        base_type = str(node.type) if node.type else 'unknown'
        
        is_nullable = any(a.annotation_type == 'nullable' for a in type_annot)
        
        self.annotated_types[node.name] = AnnotatedType(
            base_type=base_type,
            annotations=type_annot,
            is_nullable=is_nullable
        )
    
    def _find_annotation_for_node(self, path: List) -> List[TypeAnnotation]:
        """Find annotations for a node from the path."""
        annotations = []
        
        for node in path:
            if isinstance(node, javalang.tree.Annotation) or (
                hasattr(node, 'annotations') and node.annotations
            ):
                annots = getattr(node, 'annotations', None) or []
                for annot in annots:
                    name = annot.name if hasattr(annot, 'name') else str(annot)
                    
                    if name in NULLABLE_ANNOTATIONS:
                        annotations.append(TypeAnnotation(
                            name=name,
                            annotation_type='nullable',
                            is_standard=True
                        ))
                    elif name in NOT_NULL_ANNOTATIONS:
                        annotations.append(TypeAnnotation(
                            name=name,
                            annotation_type='not_null',
                            is_standard=True
                        ))
        
        return annotations


# Convenience function
def detect_type_annotations(source: str) -> List[TypeAnnotation]:
    """Detect all type annotations in Java source code."""
    detector = TypeAnnotationDetector()
    return detector.detect(source)


def is_nullable_type(annotated_type: AnnotatedType) -> bool:
    """Check if a type is nullable."""
    return annotated_type.is_nullable


def to_typescript_nullable(annotated_type: AnnotatedType) -> str:
    """Convert annotated type to TypeScript with null safety."""
    return annotated_type.to_typescript()
