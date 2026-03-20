"""Annotation Mapper for Java to Bedrock Conversion.

This module provides functionality to map Java annotations to
Bedrock-compatible format (JSDoc comments, TypeScript types, etc.).
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum

from utils.annotation_detector import (
    JavaAnnotation,
    AnnotationDetector,
    AnnotationParameter,
    detect_annotations,
)


class ConversionStyle(Enum):
    """Style for annotation conversion."""
    JSDOC = "jsdoc"           # Use JSDoc comments
    TYPESCRIPT = "typescript"  # Use TypeScript union types
    COMMENTS = "comments"      # Use plain comments
    MIXED = "mixed"            # Combination of above


@dataclass
class MappedAnnotation:
    """Represents a mapped annotation for Bedrock output."""
    original: JavaAnnotation
    converted_comment: Optional[str] = None
    typescript_type: Optional[str] = None
    conversion_style: ConversionStyle = ConversionStyle.JSDOC
    
    def __repr__(self) -> str:
        parts = [f"JavaAnnotation({self.original.name})"]
        if self.converted_comment:
            parts.append(f"comment={self.converted_comment[:30]}...")
        if self.typescript_type:
            parts.append(f"type={self.typescript_type}")
        return f"MappedAnnotation({', '.join(parts)})"


@dataclass
class AnnotationMappingResult:
    """Result of mapping annotations to Bedrock format."""
    mapped: List[MappedAnnotation]
    jsdoc_comment: Optional[str] = None
    added_type_hints: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0
    
    def __repr__(self) -> str:
        return f"AnnotationMappingResult(mapped={len(self.mapped)}, jsdoc={self.jsdoc_comment is not None})"


class AnnotationMapper:
    """Maps Java annotations to Bedrock-compatible format."""
    
    # Mapping from Java annotations to their meanings
    ANNOTATION_MEANINGS = {
        'Override': 'This method overrides a parent class method',
        'Deprecated': 'This element is deprecated and may be removed in future versions',
        'Nullable': 'This value may be null',
        'NonNull': 'This value must not be null',
        'NotNull': 'This value must not be null',
        'NonnullByDefault': 'All parameters and return values in this scope must not be null',
        'SuppressWarnings': 'Suppresses compiler warnings',
        'SafeVarargs': 'Safe with respect to varargs',
        'FunctionalInterface': 'This interface is a functional interface',
    }
    
    # Mapping from Java annotations to TypeScript type equivalents
    TYPE_MAPPINGS = {
        'Nullable': '| null',
        'NonNull': '',  # No additional type needed
        'NotNull': '',  # No additional type needed
        'NonnullByDefault': '',  # Handle at method level
    }
    
    def __init__(self, style: ConversionStyle = ConversionStyle.MIXED):
        self.style = style
        self.detector = AnnotationDetector()
    
    def map_annotation(self, annotation: JavaAnnotation) -> MappedAnnotation:
        """Map a single annotation to Bedrock format.
        
        Args:
            annotation: The Java annotation to map
            
        Returns:
            MappedAnnotation with converted format
        """
        converted_comment = None
        typescript_type = None
        
        # Handle standard annotations
        if annotation.is_standard:
            converted_comment = self._map_standard_annotation(annotation)
            
            # Add type mapping for nullable annotations
            if annotation.name in self.TYPE_MAPPINGS:
                typescript_type = self.TYPE_MAPPINGS[annotation.name]
        
        # Handle custom annotations - preserve as documentation
        if annotation.is_custom:
            converted_comment = self._map_custom_annotation(annotation)
        
        # Determine best conversion style
        style = self._determine_style(annotation)
        
        return MappedAnnotation(
            original=annotation,
            converted_comment=converted_comment,
            typescript_type=typescript_type,
            conversion_style=style
        )
    
    def map_from_source(self, source_code: str) -> AnnotationMappingResult:
        """Detect and map all annotations in source code.
        
        Args:
            source_code: Java source code string
            
        Returns:
            AnnotationMappingResult with all mapped annotations
        """
        annotations = self.detector.detect_from_source(source_code)
        
        mapped_annotations = []
        jsdoc_parts = []
        added_type_hints = []
        warnings = []
        
        for annotation in annotations:
            mapped = self.map_annotation(annotation)
            mapped_annotations.append(mapped)
            
            if mapped.converted_comment:
                jsdoc_parts.append(mapped.converted_comment)
                
            if mapped.typescript_type:
                added_type_hints.append(f"{annotation.name} -> {mapped.typescript_type}")
        
        # Build JSDoc comment if we have any
        jsdoc_comment = None
        if jsdoc_parts:
            jsdoc_comment = self._build_jsdoc_comment(jsdoc_parts)
        
        # Add warnings for custom annotations
        for annotation in annotations:
            if annotation.is_custom:
                warnings.append(
                    f"Custom annotation @{annotation.name} converted to comment - "
                    "verify behavior manually"
                )
        
        return AnnotationMappingResult(
            mapped=mapped_annotations,
            jsdoc_comment=jsdoc_comment,
            added_type_hints=added_type_hints,
            warnings=warnings
        )
    
    def _map_standard_annotation(self, annotation: JavaAnnotation) -> str:
        """Map a standard Java annotation to descriptive comment."""
        meaning = self.ANNOTATION_MEANINGS.get(
            annotation.name,
            f"Java annotation @{annotation.name}"
        )
        
        # Add parameter info if present
        if annotation.parameters:
            param_info = []
            for param in annotation.parameters:
                if param.name:
                    param_info.append(f"{param.name}={param.value}")
                else:
                    param_info.append(str(param.value))
            if param_info:
                meaning += f" (params: {', '.join(param_info)})"
        
        return meaning
    
    def _map_custom_annotation(self, annotation: JavaAnnotation) -> str:
        """Map a custom annotation to descriptive comment."""
        parts = [f"Custom annotation: @{annotation.name}"]
        
        if annotation.parameters:
            param_parts = []
            for param in annotation.parameters:
                if param.name:
                    param_parts.append(f"{param.name}={param.value}")
                else:
                    param_parts.append(str(param.value))
            if param_parts:
                parts.append(f"Parameters: {', '.join(param_parts)}")
        
        return " - ".join(parts)
    
    # Class-level constant for type annotations
    TYPE_ANNOTATIONS = {'Nullable', 'NonNull', 'NotNull', 'NonnullByDefault'}
    
    def _determine_style(self, annotation: JavaAnnotation) -> ConversionStyle:
        """Determine the best conversion style for an annotation."""
        # Type annotations use TypeScript types
        if annotation.name in self.TYPE_ANNOTATIONS:
            return ConversionStyle.TYPESCRIPT
        
        # Other standard annotations use JSDoc
        if annotation.is_standard:
            return ConversionStyle.JSDOC
        
        # Custom annotations use comments
        return ConversionStyle.COMMENTS
    
    def _build_jsdoc_comment(self, parts: List[str]) -> str:
        """Build a JSDoc comment from parts."""
        if not parts:
            return None
        
        lines = ["/**"]
        for part in parts:
            lines.append(f" * {part}")
        lines.append(" */")
        
        return "\n".join(lines)
    
    def convert_override_to_comment(self, annotation: JavaAnnotation) -> str:
        """Convert @Override to JSDoc @override tag."""
        return "@override"
    
    def convert_deprecated_to_comment(self, annotation: JavaAnnotation) -> str:
        """Convert @Deprecated to JSDoc @deprecated tag."""
        meaning = self.ANNOTATION_MEANINGS.get('Deprecated', 'Deprecated')
        
        # Check for since or forRemoval parameters
        since = annotation.get_parameter_value('since')
        for_removal = annotation.get_parameter_value('forRemoval')
        
        parts = [meaning]
        if since:
            parts.append(f"Since: {since}")
        if for_removal:
            parts.append("Scheduled for removal in future version")
        
        return "@deprecated " + " - ".join(parts)
    
    def convert_nullable_to_type(self, annotation: JavaAnnotation) -> str:
        """Convert @Nullable to TypeScript union type."""
        # Returns the suffix to add to a type
        return " | null"
    
    def convert_nonnull_to_jsdoc(self, annotation: JavaAnnotation) -> str:
        """Convert @NonNull/@NotNull to JSDoc @non-null tag."""
        return "@non-null"


# Convenience functions

def map_annotations(source_code: str, style: ConversionStyle = ConversionStyle.MIXED) -> AnnotationMappingResult:
    """Convenience function to map all annotations in source code.
    
    Args:
        source_code: Java source code string
        style: Conversion style to use
        
    Returns:
        AnnotationMappingResult with mapped annotations
    """
    mapper = AnnotationMapper(style=style)
    return mapper.map_from_source(source_code)


def annotation_to_jsdoc(annotation: JavaAnnotation) -> str:
    """Convenience function to convert annotation to JSDoc comment.
    
    Args:
        annotation: Java annotation
        
    Returns:
        JSDoc formatted string
    """
    mapper = AnnotationMapper()
    mapped = mapper.map_annotation(annotation)
    return mapped.converted_comment or ""


def annotation_to_typescript(annotation: JavaAnnotation) -> Optional[str]:
    """Convenience function to get TypeScript type equivalent.
    
    Args:
        annotation: Java annotation
        
    Returns:
        TypeScript type string or None
    """
    mapper = AnnotationMapper()
    mapped = mapper.map_annotation(annotation)
    return mapped.typescript_type



