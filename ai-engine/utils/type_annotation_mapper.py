"""Type Annotation Mapper for Java to TypeScript conversion.

This module provides functionality to map Java type annotations
to TypeScript null-safe types and JSDoc comments.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from .type_annotation_detector import TypeAnnotation, AnnotatedType, TypeAnnotationDetector


# Mapping of Java annotations to TypeScript equivalents
NULLABLE_TO_TS = {
    'Nullable': 'T | null',
    'Nullable<T>': 'T | null',
    'org.jetbrains.annotations.Nullable': 'T | null',
    'CheckForNull': 'T | null',
    'javax.annotation.Nullable': 'T | null',
    'jakarta.annotation.Nullable': 'T | null',
}

NOT_NULL_TO_TS = {
    'NotNull': 'T',
    'NotNull<T>': 'T',
    'NonNull': 'T',
    'NonNull<T>': 'T',
    'org.jetbrains.annotations.NotNull': 'T',
    'javax.annotation.NotNull': 'T',
    'jakarta.annotation.NotNull': 'T',
    'ParametersAreNonnullByDefault': 'T',
    'NonNullByDefault': 'T',
}

# JSDoc equivalents for annotations
ANNOTATION_TO_JSDOC = {
    '@Nullable': '@nullable',
    '@NotNull': '@non-null',
    '@NonNull': '@non-null',
    '@CheckForNull': '@nullable',
    '@NonNullByDefault': '@non-null',
}


@dataclass
class TypeMappingResult:
    """Result of mapping a Java type annotation to TypeScript."""
    typescript_type: str
    jsdoc_comment: Optional[str] = None
    null_annotation: Optional[str] = None  # 'nullable', 'not_null', or None
    
    def __repr__(self) -> str:
        return f"TypeMappingResult({self.typescript_type}, jsdoc={self.jsdoc_comment is not None})"


class TypeAnnotationMapper:
    """Maps Java type annotations to TypeScript types."""
    
    def __init__(self):
        self.detector = TypeAnnotationDetector()
        self.mappings: Dict[str, TypeMappingResult] = {}
    
    def map(self, source: str) -> Dict[str, TypeMappingResult]:
        """Map all type annotations in source to TypeScript."""
        annotations = self.detector.detect(source)
        annotated_types = self.detector.get_annotated_types(source)
        
        self.mappings = {}
        
        # Process annotated types
        for name, annotated_type in annotated_types.items():
            self.mappings[name] = self.map_annotated_type(annotated_type)
        
        return self.mappings
    
    def map_annotated_type(self, annotated_type: AnnotatedType) -> TypeMappingResult:
        """Map an AnnotatedType to TypeScript."""
        ts_type = annotated_type.to_typescript()
        
        # Build JSDoc comment if needed
        jsdoc = self._build_jsdoc(annotated_type)
        
        # Determine null annotation
        null_annot = None
        if annotated_type.is_nullable:
            null_annot = 'nullable'
        elif annotated_type.annotations:
            for annot in annotated_type.annotations:
                if annot.annotation_type == 'not_null':
                    null_annot = 'not_null'
                    break
        
        return TypeMappingResult(
            typescript_type=ts_type,
            jsdoc_comment=jsdoc,
            null_annotation=null_annot
        )
    
    def map_annotation(self, annotation: TypeAnnotation) -> TypeMappingResult:
        """Map a single TypeAnnotation to TypeScript."""
        if annotation.annotation_type == 'nullable':
            ts_type = NULLABLE_TO_TS.get(annotation.name, 'T | null')
            return TypeMappingResult(
                typescript_type=ts_type,
                jsdoc_comment=f"@nullable - {annotation.name}",
                null_annotation='nullable'
            )
        elif annotation.annotation_type == 'not_null':
            ts_type = NOT_NULL_TO_TS.get(annotation.name, 'T')
            return TypeMappingResult(
                typescript_type=ts_type,
                jsdoc_comment=f"@non-null - {annotation.name}",
                null_annotation='not_null'
            )
        else:
            # Custom annotation - just add as JSDoc
            return TypeMappingResult(
                typescript_type='T',
                jsdoc_comment=f"@annotation {annotation.name}",
                null_annotation=None
            )
    
    def map_nullable(self, base_type: str, annotations: List[TypeAnnotation]) -> str:
        """Map a base type with nullable annotations to TypeScript."""
        is_nullable = any(a.annotation_type == 'nullable' for a in annotations)
        
        # Convert Java array syntax to TypeScript
        ts_type = self._convert_to_typescript_type(base_type)
        
        if is_nullable:
            return f"{ts_type} | null"
        
        return ts_type
    
    def _convert_to_typescript_type(self, java_type: str) -> str:
        """Convert Java type to TypeScript equivalent."""
        # Handle arrays
        if '[]' in java_type:
            element_type = java_type.replace('[]', '')
            ts_element = self._convert_to_typescript_type(element_type)
            return f"{ts_element}[]"
        
        # Handle primitives
        type_map = {
            'int': 'number',
            'long': 'number',
            'float': 'number',
            'double': 'number',
            'boolean': 'boolean',
            'byte': 'number',
            'short': 'number',
            'char': 'string',
            'String': 'string',
            'Object': 'object',
            'void': 'void',
        }
        
        return type_map.get(java_type, java_type)
    
    def _build_jsdoc(self, annotated_type: AnnotatedType) -> Optional[str]:
        """Build JSDoc comment for an annotated type."""
        if not annotated_type.annotations:
            return None
        
        jsdoc_parts = []
        
        for annotation in annotated_type.annotations:
            if annotation.name in ANNOTATION_TO_JSDOC:
                jsdoc_parts.append(ANNOTATION_TO_JSDOC[annotation.name])
            else:
                jsdoc_parts.append(f"@annotation {annotation.name}")
        
        if jsdoc_parts:
            return '\n'.join(jsdoc_parts)
        
        return None
    
    def map_parameter(self, param_type: str, annotations: List[TypeAnnotation]) -> str:
        """Map a parameter type with annotations to TypeScript."""
        return self.map_nullable(param_type, annotations)
    
    def map_return_type(self, return_type: str, annotations: List[TypeAnnotation]) -> str:
        """Map a return type with annotations to TypeScript."""
        return self.map_nullable(return_type, annotations)
    
    def map_field(self, field_type: str, annotations: List[TypeAnnotation]) -> str:
        """Map a field type with annotations to TypeScript."""
        return self.map_nullable(field_type, annotations)


class GenericTypeAnnotationHandler:
    """Handles type annotations on generic type parameters."""
    
    def __init__(self):
        self.mapper = TypeAnnotationMapper()
    
    def handle_generic_param(self, param: str, annotations: List[TypeAnnotation]) -> str:
        """Handle annotations on generic type parameters.
        
        Example: List<@Nullable String> -> Array<string | null>
        """
        # Check for nullable
        is_nullable = any(a.annotation_type == 'nullable' for a in annotations)
        
        # Clean up annotation prefix from param name
        clean_param = param.lstrip('@').strip()
        
        # Convert to TypeScript
        ts_type = self.mapper._convert_to_typescript_type(clean_param)
        
        if is_nullable:
            return f"{ts_type} | null"
        
        return ts_type
    
    def handle_complex_generic(self, base: str, params: list) -> str:
        """Handle complex generic types with annotated parameters.
        
        Args:
            base: Base type (e.g., 'Map', 'List')
            params: List of (param_type, annotations) tuples
        """
        mapped_params = []
        
        for param_type, annotations in params:
            mapped = self.handle_generic_param(param_type, annotations)
            mapped_params.append(mapped)
        
        return f"{base}<{', '.join(mapped_params)}>"
    
    def convert_minecraft_generic(self, java_generic: str) -> str:
        """Convert Minecraft-specific generic types.
        
        Example: List<NBTTagCompound> -> Array<NBTTagCompound>
        """
        # Handle common Minecraft collections
        conversions = {
            'List<NBTTagCompound>': 'NBTTagCompound[]',
            'List<NBTTagList>': 'NBTTagList[]',
            'List<NBTBase>': 'NBTBase[]',
            'Map<String, NBTBase>': 'Map<string, NBTBase>',
            'Map<String, NBTTagCompound>': 'Map<string, NBTTagCompound>',
        }
        
        return conversions.get(java_generic, java_generic)


# Convenience functions
def map_type_annotation(annotation: TypeAnnotation) -> TypeMappingResult:
    """Map a single type annotation to TypeScript."""
    mapper = TypeAnnotationMapper()
    return mapper.map_annotation(annotation)


def to_nullable_typescript(base_type: str, is_nullable: bool) -> str:
    """Convert base type to TypeScript with optional null."""
    mapper = TypeAnnotationMapper()
    ts_type = mapper._convert_to_typescript_type(base_type)
    
    if is_nullable:
        return f"{ts_type} | null"
    
    return ts_type


def convert_java_to_ts_nullable(java_type: str, annotations: List[TypeAnnotation]) -> str:
    """Convert Java type with annotations to TypeScript nullable type."""
    mapper = TypeAnnotationMapper()
    return mapper.map_nullable(java_type, annotations)
