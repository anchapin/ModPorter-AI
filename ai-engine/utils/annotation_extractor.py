"""Annotation Extractor for Java to Bedrock Conversion.

This module provides functionality to extract annotation values and
build metadata for conversion reports.
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


class ExtractionTarget(Enum):
    """Target type for annotation extraction."""
    METHOD = "method"
    FIELD = "field"
    PARAMETER = "parameter"
    CLASS = "class"
    CONSTRUCTOR = "constructor"
    INTERFACE = "interface"


@dataclass
class AnnotationMetadata:
    """Metadata about an extracted annotation."""
    annotation_name: str
    target: ExtractionTarget
    line_number: int
    parameters: Dict[str, Any] = field(default_factory=dict)
    is_standard: bool = False
    is_custom: bool = False
    conversion_strategy: str = "jsdoc"  # jsdoc, typescript, comment, mixed
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            'annotation_name': self.annotation_name,
            'target': self.target.value,
            'line_number': self.line_number,
            'parameters': self.parameters,
            'is_standard': self.is_standard,
            'is_custom': self.is_custom,
            'conversion_strategy': self.conversion_strategy,
        }


@dataclass
class ExtractionResult:
    """Result of extracting annotations from source."""
    metadata: List[AnnotationMetadata] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    custom_annotations: List[str] = field(default_factory=list)
    
    def get_annotation_names(self) -> List[str]:
        """Get list of unique annotation names."""
        return list(self.summary.keys())
    
    def has_override(self) -> bool:
        """Check if any @Override was found."""
        return 'Override' in self.summary
    
    def has_deprecated(self) -> bool:
        """Check if any @Deprecated was found."""
        return 'Deprecated' in self.summary
    
    def has_nullable(self) -> bool:
        """Check if any @Nullable was found."""
        return 'Nullable' in self.summary
    
    def total_count(self) -> int:
        """Get total count of annotations."""
        return sum(self.summary.values())


class AnnotationExtractor:
    """Extracts annotation values and builds metadata for conversion reports."""
    
    # Mapping of annotation to conversion strategy
    CONVERSION_STRATEGIES = {
        'Override': 'jsdoc',
        'Deprecated': 'jsdoc',
        'Nullable': 'typescript',
        'NonNull': 'mixed',
        'NotNull': 'mixed',
        'NonnullByDefault': 'mixed',
        'SuppressWarnings': 'comment',
        'SafeVarargs': 'comment',
        'FunctionalInterface': 'jsdoc',
    }
    
    def __init__(self):
        self.detector = AnnotationDetector()
    
    def extract(self, source_code: str) -> ExtractionResult:
        """Extract all annotations and build metadata.
        
        Args:
            source_code: Java source code string
            
        Returns:
            ExtractionResult with metadata and summary
        """
        annotations = self.detector.detect_from_source(source_code)
        
        metadata_list = []
        summary: Dict[str, int] = {}
        custom_annotations: List[str] = []
        
        for annotation in annotations:
            # Build parameters dict
            params = {}
            for param in annotation.parameters:
                if param.name:
                    params[param.name] = param.value
                else:
                    params['value'] = param.value
            
            # Determine conversion strategy
            strategy = self._get_conversion_strategy(annotation.name)
            
            # Determine target
            target = self._infer_target(annotation)
            
            metadata = AnnotationMetadata(
                annotation_name=annotation.name,
                target=target,
                line_number=annotation.line_number or 0,
                parameters=params,
                is_standard=annotation.is_standard,
                is_custom=annotation.is_custom,
                conversion_strategy=strategy
            )
            metadata_list.append(metadata)
            
            # Update summary
            summary[annotation.name] = summary.get(annotation.name, 0) + 1
            
            # Track custom annotations
            if annotation.is_custom and annotation.name not in custom_annotations:
                custom_annotations.append(annotation.name)
        
        return ExtractionResult(
            metadata=metadata_list,
            summary=summary,
            custom_annotations=custom_annotations
        )
    
    def extract_for_method(self, source_code: str, method_signature: str) -> ExtractionResult:
        """Extract annotations specifically for a method.
        
        Args:
            source_code: Java source code string
            method_signature: The method signature to find
            
        Returns:
            ExtractionResult with method-specific annotations
        """
        result = self.extract(source_code)
        
        # Filter metadata for the given method (based on line proximity)
        # This is a simplified version - full implementation would track
        # which annotation belongs to which method
        
        return result
    
    def extract_value(self, annotation: JavaAnnotation, param_name: str) -> Optional[Any]:
        """Extract a specific parameter value from an annotation.
        
        Args:
            annotation: The annotation to extract from
            param_name: Name of the parameter
            
        Returns:
            The parameter value or None
        """
        return annotation.get_parameter_value(param_name)
    
    def extract_all_values(self, annotation: JavaAnnotation) -> Dict[str, Any]:
        """Extract all parameter values from an annotation.
        
        Args:
            annotation: The annotation to extract from
            
        Returns:
            Dictionary of parameter names to values
        """
        result = {}
        for param in annotation.parameters:
            if param.name:
                result[param.name] = param.value
            else:
                result['value'] = param.value
        return result
    
    def _get_conversion_strategy(self, annotation_name: str) -> str:
        """Get the conversion strategy for an annotation."""
        return self.CONVERSION_STRATEGIES.get(annotation_name, 'jsdoc')
    
    def _infer_target(self, annotation: JavaAnnotation) -> ExtractionTarget:
        """Infer the target type for an annotation."""
        # Use target from detector if available
        if annotation.target:
            target_map = {
                'METHOD': ExtractionTarget.METHOD,
                'FIELD': ExtractionTarget.FIELD,
                'PARAMETER': ExtractionTarget.PARAMETER,
                'CLASS': ExtractionTarget.CLASS,
                'CONSTRUCTOR': ExtractionTarget.CONSTRUCTOR,
            }
            return target_map.get(annotation.target.upper(), ExtractionTarget.METHOD)
        
        # Infer from annotation name
        if annotation.name in {'Override', 'Deprecated', 'SuppressWarnings', 'SafeVarargs'}:
            return ExtractionTarget.METHOD
        elif annotation.name in {'Nullable', 'NonNull', 'NotNull', 'NonnullByDefault'}:
            return ExtractionTarget.PARAMETER
        else:
            return ExtractionTarget.METHOD
    
    def get_deprecation_info(self, annotation: JavaAnnotation) -> Dict[str, Any]:
        """Extract detailed deprecation information from @Deprecated.
        
        Args:
            annotation: The @Deprecated annotation
            
        Returns:
            Dictionary with deprecation details
        """
        info = {
            'deprecated': True,
        }
        
        # Extract 'since' parameter
        since = annotation.get_parameter_value('since')
        if since:
            info['since'] = since
        
        # Extract 'forRemoval' parameter
        for_removal = annotation.get_parameter_value('forRemoval')
        if for_removal:
            info['for_removal'] = for_removal.lower() == 'true'
        
        return info
    
    def get_override_info(self, annotation: JavaAnnotation) -> Dict[str, Any]:
        """Extract information from @Override annotation.
        
        Args:
            annotation: The @Override annotation
            
        Returns:
            Dictionary with override details
        """
        # @Override doesn't have standard parameters
        # but we can track that this method overrides a parent
        return {
            'overrides': True,
            'method': 'parent_method',  # Would need AST analysis to determine actual method
        }


# Convenience functions

def extract_annotations(source_code: str) -> ExtractionResult:
    """Convenience function to extract all annotations from source.
    
    Args:
        source_code: Java source code string
        
    Returns:
        ExtractionResult with metadata
    """
    extractor = AnnotationExtractor()
    return extractor.extract(source_code)


def extract_annotation_metadata(source_code: str) -> List[AnnotationMetadata]:
    """Convenience function to get annotation metadata list.
    
    Args:
        source_code: Java source code string
        
    Returns:
        List of AnnotationMetadata
    """
    extractor = AnnotationExtractor()
    result = extractor.extract(source_code)
    return result.metadata


def get_annotation_summary(source_code: str) -> Dict[str, int]:
    """Convenience function to get annotation summary.
    
    Args:
        source_code: Java source code string
        
    Returns:
        Dictionary of annotation names to counts
    """
    extractor = AnnotationExtractor()
    result = extractor.extract(source_code)
    return result.summary
