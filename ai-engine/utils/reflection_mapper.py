"""
Reflection API Mapping Module

Converts Java Reflection API patterns to JavaScript equivalents or generates warnings.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from utils.reflection_detector import (
    ReflectionDetector,
    ReflectionCall,
    DynamicClassLoad,
    FieldAccess,
    MethodInvocation,
    AnnotationAccess,
)


class Severity(Enum):
    """Warning severity levels."""
    HIGH = "HIGH"      # Likely to break in Bedrock
    MEDIUM = "MEDIUM"  # May need manual intervention
    LOW = "LOW"        # Informational


@dataclass
class ReflectionWarning:
    """Warning for a reflection pattern that cannot be directly converted."""
    pattern: str
    severity: Severity
    message: str
    suggestion: str
    line_number: int = 0


@dataclass
class ConversionResult:
    """Result of converting reflection patterns."""
    converted_code: str = ""
    warnings: List[ReflectionWarning] = field(default_factory=list)
    has_errors: bool = False
    success: bool = True


class PatternType(Enum):
    """Classification of reflection patterns."""
    CONVERTIBLE = "CONVERTIBLE"       # Can be directly converted
    WARNING = "WARNING"                # Needs attention but can work
    UNSUPPORTED = "UNSUPPORTED"       # No JavaScript equivalent


# Pattern classification and conversion rules
CONVERSION_RULES = {
    # Class methods that can be converted
    'getSimpleName': {
        'type': PatternType.CONVERTIBLE,
        'conversion': "class.name",
        'example': 'Class.getSimpleName() → class.name'
    },
    'getName': {
        'type': PatternType.CONVERTIBLE,
        'conversion': "class.name",
        'example': 'Class.getName() → class.name'
    },
    'getCanonicalName': {
        'type': PatternType.WARNING,
        'message': 'getCanonicalName() may return null for anonymous classes',
        'suggestion': 'Use getSimpleName() or getName() instead'
    },
    
    # Field methods that can be converted
    'getDeclaredFields': {
        'type': PatternType.CONVERTIBLE,
        'conversion': "Object.getOwnPropertyNames(obj)",
        'example': 'getDeclaredFields() → Object.getOwnPropertyNames()'
    },
    'getFields': {
        'type': PatternType.CONVERTIBLE,
        'conversion': "Object.keys(obj)",
        'example': 'getFields() → Object.keys(obj)'
    },
    'getDeclaredField': {
        'type': PatternType.CONVERTIBLE,
        'conversion': "obj[fieldName]",
        'example': 'getDeclaredField("x") → obj.x or obj["x"]'
    },
    
    # Method methods
    'getDeclaredMethods': {
        'type': PatternType.CONVERTIBLE,
        'conversion': "Object.getOwnPropertyNames(obj).filter(p => typeof obj[p] === 'function')",
        'example': 'getDeclaredMethods() → filter for functions'
    },
    'getMethods': {
        'type': PatternType.CONVERTIBLE,
        'conversion': "Object.keys(obj).filter(p => typeof obj[p] === 'function')",
        'example': 'getMethods() → Object.keys + function filter'
    },
    
    # Dynamic patterns that need warnings
    'forName': {
        'type': PatternType.UNSUPPORTED,
        'message': 'Dynamic class loading not supported in Bedrock',
        'suggestion': 'Use static imports or define classes explicitly'
    },
    'invoke': {
        'type': PatternType.UNSUPPORTED,
        'message': 'Dynamic method invocation not directly supported',
        'suggestion': 'Convert to direct method calls or use function references'
    },
    'newInstance': {
        'type': PatternType.UNSUPPORTED,
        'message': 'Dynamic object instantiation not supported',
        'suggestion': 'Use constructor functions or class declarations'
    },
    'setAccessible': {
        'type': PatternType.UNSUPPORTED,
        'message': 'Private field/method access not meaningful in JavaScript',
        'suggestion': 'JavaScript does not have access modifiers; remove setAccessible'
    },
    
    # Annotation methods - generally unsupported
    'getAnnotation': {
        'type': PatternType.UNSUPPORTED,
        'message': 'Annotations are not available at runtime in JavaScript',
        'suggestion': 'Convert annotations to comment metadata or runtime properties'
    },
    'getAnnotations': {
        'type': PatternType.UNSUPPORTED,
        'message': 'Annotations are not available at runtime in JavaScript',
        'suggestion': 'Convert annotations to comment metadata or runtime properties'
    },
    'getDeclaredAnnotations': {
        'type': PatternType.UNSUPPORTED,
        'message': 'Annotations are not available at runtime in JavaScript',
        'suggestion': 'Convert annotations to comment metadata or runtime properties'
    },
    'isAnnotationPresent': {
        'type': PatternType.UNSUPPORTED,
        'message': 'Annotation checking not supported in JavaScript',
        'suggestion': 'Check for presence of metadata properties instead'
    },
}


class ReflectionMapper:
    """
    Maps Java Reflection API patterns to JavaScript equivalents.
    
    Usage:
        mapper = ReflectionMapper()
        result = mapper.map_reflection(java_code)
        print(result.converted_code)
        for warning in result.warnings:
            print(f"Warning: {warning.message}")
    """
    
    def __init__(self):
        self.detector = ReflectionDetector()
        self.warnings: List[ReflectionWarning] = []
    
    def map_reflection(self, source: str) -> ConversionResult:
        """
        Detect and convert reflection patterns in source code.
        
        Args:
            source: Java source code
            
        Returns:
            ConversionResult with converted code and warnings
        """
        self.warnings = []
        
        # First detect all reflection patterns
        details = self.detector.detect_with_details(source)
        
        if not details['reflection_calls']:
            # No reflection found, return original
            return ConversionResult(
                converted_code=source,
                warnings=[],
                success=True
            )
        
        # Process each reflection call
        converted = source
        for call in details['reflection_calls']:
            rule = CONVERSION_RULES.get(call.method_name)
            
            if not rule:
                # Unknown reflection method
                self.warnings.append(ReflectionWarning(
                    pattern=call.method_name,
                    severity=Severity.MEDIUM,
                    message=f"Unknown reflection method: {call.method_name}",
                    suggestion="Manual review required",
                    line_number=call.line_number
                ))
                continue
            
            pattern_type = rule['type']
            
            if pattern_type == PatternType.CONVERTIBLE:
                # Apply conversion (we don't modify source, just warn about it)
                # The actual conversion would happen in the translation engine
                pass
            
            elif pattern_type == PatternType.WARNING:
                self.warnings.append(ReflectionWarning(
                    pattern=call.method_name,
                    severity=Severity.MEDIUM,
                    message=rule.get('message', f'{call.method_name} needs attention'),
                    suggestion=rule.get('suggestion', ''),
                    line_number=call.line_number
                ))
            
            elif pattern_type == PatternType.UNSUPPORTED:
                self.warnings.append(ReflectionWarning(
                    pattern=call.method_name,
                    severity=Severity.HIGH,
                    message=rule.get('message', f'{call.method_name} is not supported'),
                    suggestion=rule.get('suggestion', ''),
                    line_number=call.line_number
                ))
        
        # Process dynamic class loads
        for dcl in details['dynamic_class_loads']:
            self.warnings.append(ReflectionWarning(
                pattern='Class.forName',
                severity=Severity.HIGH,
                message=f"Dynamic class loading: {dcl.class_name}",
                suggestion="Use static imports or explicit class definitions",
                line_number=dcl.line_number
            ))
        
        # Process method invocations
        for mi in details['method_invocations']:
            if mi.target_method == 'dynamic':
                self.warnings.append(ReflectionWarning(
                    pattern='Method.invoke',
                    severity=Severity.HIGH,
                    message="Dynamic method invocation detected",
                    suggestion="Convert to direct method call or use function reference",
                    line_number=mi.line_number
                ))
        
        # Return result
        return ConversionResult(
            converted_code=source,  # Return original - conversion happens elsewhere
            warnings=self.warnings,
            has_errors=any(w.severity == Severity.HIGH for w in self.warnings),
            success=True
        )
    
    def map_single_pattern(self, method_name: str) -> ConversionResult:
        """
        Map a single reflection method name to its conversion or warning.
        
        Args:
            method_name: Name of the reflection method
            
        Returns:
            ConversionResult with conversion info or warning
        """
        rule = CONVERSION_RULES.get(method_name)
        
        if not rule:
            return ConversionResult(
                warnings=[ReflectionWarning(
                    pattern=method_name,
                    severity=Severity.MEDIUM,
                    message=f"Unknown reflection pattern: {method_name}",
                    suggestion="Manual review required"
                )]
            )
        
        pattern_type = rule['type']
        
        if pattern_type == PatternType.CONVERTIBLE:
            return ConversionResult(
                converted_code=rule['conversion'],
                warnings=[],
                success=True
            )
        else:
            return ConversionResult(
                warnings=[ReflectionWarning(
                    pattern=method_name,
                    severity=Severity.HIGH if pattern_type == PatternType.UNSUPPORTED else Severity.MEDIUM,
                    message=rule.get('message', ''),
                    suggestion=rule.get('suggestion', '')
                )],
                has_errors=pattern_type == PatternType.UNSUPPORTED,
                success=pattern_type != PatternType.UNSUPPORTED
            )
    
    def get_warning_summary(self, result: ConversionResult) -> Dict[str, Any]:
        """
        Get a summary of warnings for reporting.
        
        Args:
            result: ConversionResult from map_reflection
            
        Returns:
            Dictionary with warning counts and details
        """
        high = [w for w in result.warnings if w.severity == Severity.HIGH]
        medium = [w for w in result.warnings if w.severity == Severity.MEDIUM]
        low = [w for w in result.warnings if w.severity == Severity.LOW]
        
        return {
            'total': len(result.warnings),
            'high': len(high),
            'medium': len(medium),
            'low': len(low),
            'has_blocking': len(high) > 0,
            'warnings': result.warnings
        }


def map_reflection(source: str) -> ConversionResult:
    """
    Convenience function to map reflection patterns in source code.
    
    Args:
        source: Java source code
        
    Returns:
        ConversionResult with converted code and warnings
    """
    mapper = ReflectionMapper()
    return mapper.map_reflection(source)


def map_reflection_single(method_name: str) -> ConversionResult:
    """
    Convenience function to map a single reflection pattern.
    
    Args:
        method_name: Reflection method name
        
    Returns:
        ConversionResult with conversion or warning
    """
    mapper = ReflectionMapper()
    return mapper.map_single_pattern(method_name)
