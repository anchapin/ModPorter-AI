"""Annotation Detector for Java to Bedrock Conversion.

This module provides functionality to detect and analyze Java annotations
in source code AST for conversion to Bedrock-compatible format.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set
import re


@dataclass
class AnnotationParameter:
    """Represents a parameter in an annotation."""
    name: str
    value: Any
    
    def __repr__(self) -> str:
        if self.name:
            return f"AnnotationParameter({self.name}={self.value})"
        return f"AnnotationParameter({self.value})"


@dataclass
class JavaAnnotation:
    """Represents a complete Java annotation."""
    name: str
    parameters: List[AnnotationParameter] = field(default_factory=list)
    line_number: Optional[int] = None
    is_standard: bool = False  # True for @Override, @Deprecated, @Nullable, etc.
    is_custom: bool = False   # True for user-defined annotations
    target: Optional[str] = None  # METHOD, FIELD, PARAMETER, CLASS, etc.
    
    def __repr__(self) -> str:
        param_str = ", ".join(str(p) for p in self.parameters)
        return f"JavaAnnotation({self.name}({param_str}))"
    
    def has_parameter(self, param_name: str) -> bool:
        """Check if annotation has a specific parameter."""
        return any(p.name == param_name for p in self.parameters)
    
    def get_parameter_value(self, param_name: str) -> Optional[Any]:
        """Get value of a specific parameter."""
        for p in self.parameters:
            if p.name == param_name:
                return p.value
        return None


class AnnotationDetector:
    """Detects and analyzes Java annotations in source code."""
    
    # Standard Java annotations that have special meaning
    STANDARD_ANNOTATIONS: Set[str] = {
        'Override',
        'Deprecated',
        'Nullable',
        'NonNull',
        'NotNull',
        'SuppressWarnings',
        'SafeVarargs',
        'FunctionalInterface',
        'Deprecated',
        'Generated',
        'SuppressFBWarnings',
        'NonnullByDefault',
    }
    
    # Annotations that map to TypeScript types
    TYPE_ANNOTATIONS: Set[str] = {
        'Nullable',
        'NonNull', 
        'NotNull',
        'NonnullByDefault',
    }
    
    # Annotation targets (where they can be applied)
    ANNOTATION_TARGETS: Dict[str, Set[str]] = {
        'METHOD': {'Override', 'Deprecated', 'SuppressWarnings', 'SafeVarargs'},
        'CLASS': {'Deprecated', 'SuppressWarnings'},
        'FIELD': {'Deprecated', 'Nullable', 'NonNull', 'NotNull'},
        'PARAMETER': {'Nullable', 'NonNull', 'NotNull', 'NonnullByDefault'},
        'CONSTRUCTOR': {'Deprecated', 'Nullable', 'NonNull'},
    }
    
    def __init__(self):
        self.annotations: List[JavaAnnotation] = []
        self._custom_annotations: Set[str] = set()
        self._source_lines: List[str] = []
    
    def reset(self):
        """Reset detector state for new source."""
        self.annotations = []
        self._custom_annotations = set()
        self._source_lines = []
    
    def detect_from_source(self, source_code: str) -> List[JavaAnnotation]:
        """Detect all annotations in source code.
        
        Args:
            source_code: Java source code string
            
        Returns:
            List of detected JavaAnnotation objects
        """
        self.reset()
        self._source_lines = source_code.split('\n')
        
        # Detect annotations using regex
        self._detect_with_regex(source_code)
        
        # Also check for javalang-based AST if available
        try:
            self._detect_with_javalang(source_code)
        except Exception:
            pass  # Fall back to regex-only detection
            
        return self.annotations
    
    def _detect_with_regex(self, source: str) -> None:
        """Detect annotations using regex patterns."""
        # Pattern to match annotations:
        # @Annotation
        # @Annotation()
        # @Annotation(param = value)
        # @Annotation(value)
        annotation_pattern = r'@([A-Z][A-Za-z0-9_]*(?:<[^>]+>)?(?:\(\))?)'
        
        # More sophisticated pattern to handle parameters
        # @Annotation
        # @Annotation()
        # @Annotation(value)
        # @Annotation(param = value)
        # @Annotation(param1 = value1, param2 = value2)
        full_pattern = r'@([A-Z][A-Za-z0-9_]*(?:<[^>]+>)?)\s*(?:\(([^)]*)\))?'
        
        for i, line in enumerate(self._source_lines, 1):
            # Skip comments
            if '//' in line:
                line = line[:line.index('//')]
            
            # Find all annotations in this line
            matches = re.finditer(full_pattern, line)
            
            for match in matches:
                annotation_name = match.group(1)
                params_str = match.group(2)
                
                # Determine if standard or custom
                is_standard = annotation_name in self.STANDARD_ANNOTATIONS
                
                # Track custom annotations
                if not is_standard:
                    self._custom_annotations.add(annotation_name)
                
                # Parse parameters
                parameters = self._parse_parameters(params_str)
                
                # Determine target (heuristic based on context)
                target = self._infer_target(i - 1)
                
                annotation = JavaAnnotation(
                    name=annotation_name,
                    parameters=parameters,
                    line_number=i,
                    is_standard=is_standard,
                    is_custom=not is_standard,
                    target=target
                )
                self.annotations.append(annotation)
    
    def _detect_with_javalang(self, source: str) -> None:
        """Detect annotations using javalang AST."""
        try:
            import javalang
            
            tree = javalang.parse.parse(source)
            
            for path, node in tree:
                # Look for annotation declarations
                if isinstance(node, javalang.tree.Annotation):
                    annotation_name = node.name
                    if isinstance(annotation_name, javalang.tree.Declared):
                        annotation_name = annotation_name.name
                    
                    # Parse parameters
                    parameters = []
                    if hasattr(node, 'element') and node.element:
                        for elem in node.element:
                            if hasattr(elem, 'value'):
                                # Simple element
                                param = AnnotationParameter(
                                    name='',
                                    value=str(elem.value)
                                )
                                parameters.append(param)
                            elif hasattr(elem, 'name') and hasattr(elem, 'value'):
                                # Named element
                                param = AnnotationParameter(
                                    name=elem.name,
                                    value=str(elem.value.value) if hasattr(elem.value, 'value') else str(elem.value)
                                )
                                parameters.append(param)
                    
                    # Get line number
                    line_number = None
                    if hasattr(node, 'position') and node.position:
                        line_number = node.position.line
                    
                    is_standard = annotation_name in self.STANDARD_ANNOTATIONS
                    
                    annotation = JavaAnnotation(
                        name=annotation_name,
                        parameters=parameters,
                        line_number=line_number,
                        is_standard=is_standard,
                        is_custom=not is_standard
                    )
                    
                    # Only add if not already detected by regex
                    if annotation not in self.annotations:
                        self.annotations.append(annotation)
                        
        except Exception:
            pass  # Fall back to regex-only
    
    def _parse_parameters(self, params_str: Optional[str]) -> List[AnnotationParameter]:
        """Parse annotation parameter string into AnnotationParameter objects."""
        if not params_str or not params_str.strip():
            return []
        
        parameters = []
        
        # Handle simple value case: @Annotation(value)
        # In this case, param name is empty string
        params_str = params_str.strip()
        
        # Check if it's a simple string/number value
        if not '=' in params_str:
            # Single value without name
            value = params_str.strip().strip('"').strip("'")
            return [AnnotationParameter(name='', value=value)]
        
        # Parse named parameters
        # Handle: param1 = value1, param2 = "string", param3 = 123
        parts = []
        current = ''
        depth = 0
        in_string = False
        string_char = None
        
        for char in params_str:
            if char in '([{<' and not in_string:
                depth += 1
                current += char
            elif char in ')]}' and not in_string:
                depth -= 1
                current += char
            elif char in '"\'' and not in_string:
                in_string = True
                string_char = char
                current += char
            elif char in '"\'' and in_string and char == string_char:
                in_string = False
                string_char = None
                current += char
            elif char == ',' and depth == 0 and not in_string:
                parts.append(current)
                current = ''
            else:
                current += char
        
        if current.strip():
            parts.append(current)
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
                
            if '=' in part:
                key, value = part.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                parameters.append(AnnotationParameter(name=key, value=value))
            else:
                # Single value without name
                value = part.strip().strip('"').strip("'")
                parameters.append(AnnotationParameter(name='', value=value))
        
        return parameters
    
    def _infer_target(self, line_idx: int) -> Optional[str]:
        """Infer annotation target from surrounding context."""
        # Look at previous lines for context
        context_lines = self._source_lines[max(0, line_idx - 3):line_idx]
        context_text = '\n'.join(context_lines).lower()
        
        # Check for method declarations
        if re.search(r'\bpublic\s+\w+\s+\w+\s*\(', context_text):
            return 'METHOD'
        if re.search(r'\bprivate\s+\w+\s+\w+\s*\(', context_text):
            return 'METHOD'
        
        # Check for field declarations
        if re.search(r'\b(private|public|protected)\s+\w+\s+\w+\s*=', context_text):
            return 'FIELD'
        
        # Check for class declarations
        if re.search(r'\b(class|interface|enum)\s+\w+', context_text):
            return 'CLASS'
        
        # Check for parameter (look for method signature)
        for line in context_lines:
            if '(' in line and ')' in line:
                return 'PARAMETER'
        
        return None
    
    def get_annotation_by_name(self, name: str) -> List[JavaAnnotation]:
        """Get all annotations with a specific name."""
        return [a for a in self.annotations if a.name == name]
    
    def get_standard_annotations(self) -> List[JavaAnnotation]:
        """Get all standard annotations."""
        return [a for a in self.annotations if a.is_standard]
    
    def get_custom_annotations(self) -> List[JavaAnnotation]:
        """Get all custom (user-defined) annotations."""
        return [a for a in self.annotations if a.is_custom]
    
    def get_annotation_count(self) -> int:
        """Return total count of detected annotations."""
        return len(self.annotations)
    
    def has_annotation(self, name: str) -> bool:
        """Check if a specific annotation exists."""
        return any(a.name == name for a in self.annotations)
    
    def has_override(self) -> bool:
        """Check if @Override annotation exists."""
        return self.has_annotation('Override')
    
    def has_deprecated(self) -> bool:
        """Check if @Deprecated annotation exists."""
        return self.has_annotation('Deprecated')
    
    def has_nullable(self) -> bool:
        """Check if @Nullable annotation exists."""
        return self.has_annotation('Nullable')


def detect_annotations(source_code: str) -> List[JavaAnnotation]:
    """Convenience function to detect annotations in source code.
    
    Args:
        source_code: Java source code string
        
    Returns:
        List of detected JavaAnnotation objects
    """
    detector = AnnotationDetector()
    return detector.detect_from_source(source_code)


def has_override_annotation(source_code: str) -> bool:
    """Convenience function to check for @Override.
    
    Args:
        source_code: Java source code string
        
    Returns:
        True if @Override is present
    """
    detector = AnnotationDetector()
    detector.detect_from_source(source_code)
    return detector.has_override()


def has_deprecated_annotation(source_code: str) -> bool:
    """Convenience function to check for @Deprecated.
    
    Args:
        source_code: Java source code string
        
    Returns:
        True if @Deprecated is present
    """
    detector = AnnotationDetector()
    detector.detect_from_source(source_code)
    return detector.has_deprecated()
