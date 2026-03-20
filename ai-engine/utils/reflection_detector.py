"""
Reflection API Detection Module

Detects Java Reflection API usage in source code for conversion to Bedrock.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Set
import javalang


@dataclass
class ReflectionCall:
    """Represents a detected reflection API call."""
    method_name: str
    object_type: str  # Class, Field, Method, Constructor
    arguments: List[str] = field(default_factory=list)
    line_number: int = 0
    source_snippet: str = ""


@dataclass
class DynamicClassLoad:
    """Represents a Class.forName() call."""
    class_name: str
    line_number: int = 0
    source_snippet: str = ""


@dataclass
class FieldAccess:
    """Represents field get/set operations."""
    field_name: str
    operation: str  # 'get' or 'set'
    is_static: bool = False
    line_number: int = 0
    source_snippet: str = ""


@dataclass
class MethodInvocation:
    """Represents Method.invoke() or Constructor.newInstance() calls."""
    target_method: str
    arguments: List[str] = field(default_factory=list)
    is_static: bool = False
    line_number: int = 0
    source_snippet: str = ""


@dataclass
class AnnotationAccess:
    """Represents annotation access patterns."""
    annotation_type: str
    target: str  # field, method, class
    line_number: int = 0
    source_snippet: str = ""


# Reflection method patterns to detect
CLASS_METHODS = {
    'forName': 'dynamic_class_load',
    'getName': 'class_name',
    'getSimpleName': 'class_simple_name',
    'getCanonicalName': 'class_canonical_name',
    'newInstance': 'class_new_instance',
}

FIELD_METHODS = {
    'get': 'field_read',
    'set': 'field_write',
    'getInt': 'field_read_int',
    'setInt': 'field_write_int',
    'getBoolean': 'field_read_boolean',
    'setBoolean': 'field_write_boolean',
    'getDeclaredFields': 'all_fields',
    'getFields': 'public_fields',
    'getDeclaredField': 'specific_field',
    'getField': 'public_specific_field',
}

METHOD_METHODS = {
    'invoke': 'method_invoke',
    'getDeclaredMethods': 'all_methods',
    'getMethods': 'public_methods',
    'getDeclaredMethod': 'specific_method',
    'getMethod': 'public_specific_method',
}

CONSTRUCTOR_METHODS = {
    'newInstance': 'constructor_new_instance',
    'getDeclaredConstructors': 'all_constructors',
    'getConstructors': 'public_constructors',
}

ANNOTATION_METHODS = {
    'getAnnotation': 'get_annotation',
    'getAnnotations': 'get_all_annotations',
    'getDeclaredAnnotations': 'get_declared_annotations',
    'isAnnotationPresent': 'check_annotation',
}

ACCESS_METHODS = {
    'setAccessible': 'accessibility_change',
}


class ReflectionDetector:
    """
    Detects Java Reflection API patterns in source code.
    
    Usage:
        detector = ReflectionDetector()
        calls = detector.detect_from_source(java_code)
        for call in calls:
            print(f"Found: {call.method_name} at line {call.line_number}")
    """
    
    def __init__(self):
        self.reflection_calls: List[ReflectionCall] = []
        self.dynamic_class_loads: List[DynamicClassLoad] = []
        self.field_accesses: List[FieldAccess] = []
        self.method_invocations: List[MethodInvocation] = []
        self.annotation_accesses: List[AnnotationAccess] = []
        self.set_accessible_calls: List[ReflectionCall] = []
    
    def detect_from_source(self, source: str) -> List[ReflectionCall]:
        """
        Parse source code and detect all reflection API calls.
        
        Args:
            source: Java source code string
            
        Returns:
            List of ReflectionCall objects
        """
        self._reset()
        
        try:
            tree = javalang.parse.parse(source)
        except javalang.parser.JavaSyntaxError as e:
            # Return empty list for unparseable code
            return []
        
        # Find all method invocations
        for path, node in tree:
            if isinstance(node, javalang.tree.MethodInvocation):
                self._process_method_invocation(node, path)
            elif isinstance(node, javalang.tree.ClassCreator):  # newInstance patterns
                self._process_class_creator(node, path)
        
        return self.reflection_calls
    
    def detect_with_details(self, source: str) -> dict:
        """
        Detect reflection patterns and return detailed information.
        
        Args:
            source: Java source code string
            
        Returns:
            Dictionary with all detected patterns
        """
        self.detect_from_source(source)
        
        return {
            'reflection_calls': self.reflection_calls,
            'dynamic_class_loads': self.dynamic_class_loads,
            'field_accesses': self.field_accesses,
            'method_invocations': self.method_invocations,
            'annotation_accesses': self.annotation_accesses,
            'set_accessible_calls': self.set_accessible_calls,
            'summary': self._get_summary()
        }
    
    def _reset(self):
        """Reset all detected patterns."""
        self.reflection_calls = []
        self.dynamic_class_loads = []
        self.field_accesses = []
        self.method_invocations = []
        self.annotation_accesses = []
        self.set_accessible_calls = []
    
    def _process_method_invocation(self, node: javalang.tree.MethodInvocation, path: list):
        """Process a method invocation node for reflection patterns."""
        method_name = node.member
        
        # Get line number
        line_number = node.position.line if node.position else 0
        
        # Get source snippet
        source_snippet = self._get_source_snippet(node)
        
        # Check for Class.* methods
        if self._is_static_reflection_call(node, CLASS_METHODS, path):
            call = ReflectionCall(
                method_name=method_name,
                object_type='Class',
                arguments=self._get_arguments(node),
                line_number=line_number,
                source_snippet=source_snippet
            )
            self.reflection_calls.append(call)
            
            if method_name == 'forName':
                class_name = self._extract_class_name_argument(node)
                if class_name:
                    self.dynamic_class_loads.append(DynamicClassLoad(
                        class_name=class_name,
                        line_number=line_number,
                        source_snippet=source_snippet
                    ))
        
        # Check for Field.* methods
        elif self._is_field_method(method_name):
            call = ReflectionCall(
                method_name=method_name,
                object_type='Field',
                arguments=self._get_arguments(node),
                line_number=line_number,
                source_snippet=source_snippet
            )
            self.reflection_calls.append(call)
            
            if method_name in ('getDeclaredFields', 'getFields'):
                self.field_accesses.append(FieldAccess(
                    field_name='*',
                    operation='read_all',
                    line_number=line_number,
                    source_snippet=source_snippet
                ))
            elif method_name in ('get', 'set', 'getInt', 'setInt', 'getBoolean', 'setBoolean'):
                field_name = self._extract_field_name(node)
                if field_name:
                    operation = 'get' if method_name in ('get', 'getInt', 'getBoolean') else 'set'
                    self.field_accesses.append(FieldAccess(
                        field_name=field_name,
                        operation=operation,
                        line_number=line_number,
                        source_snippet=source_snippet
                    ))
        
        # Check for Method.* methods
        elif self._is_method_method(method_name):
            call = ReflectionCall(
                method_name=method_name,
                object_type='Method',
                arguments=self._get_arguments(node),
                line_number=line_number,
                source_snippet=source_snippet
            )
            self.reflection_calls.append(call)
            
            if method_name == 'invoke':
                self.method_invocations.append(MethodInvocation(
                    target_method='dynamic',
                    arguments=self._get_arguments(node),
                    line_number=line_number,
                    source_snippet=source_snippet
                ))
        
        # Check for Constructor.* methods
        elif self._is_constructor_method(method_name):
            call = ReflectionCall(
                method_name=method_name,
                object_type='Constructor',
                arguments=self._get_arguments(node),
                line_number=line_number,
                source_snippet=source_snippet
            )
            self.reflection_calls.append(call)
            
            if method_name == 'newInstance':
                self.method_invocations.append(MethodInvocation(
                    target_method='constructor',
                    arguments=self._get_arguments(node),
                    line_number=line_number,
                    source_snippet=source_snippet
                ))
        
        # Check for annotation methods
        elif self._is_annotation_method(method_name):
            call = ReflectionCall(
                method_name=method_name,
                object_type='Annotation',
                arguments=self._get_arguments(node),
                line_number=line_number,
                source_snippet=source_snippet
            )
            self.reflection_calls.append(call)
            
            annotation_type = self._extract_annotation_type(node)
            if annotation_type:
                self.annotation_accesses.append(AnnotationAccess(
                    annotation_type=annotation_type,
                    target='unknown',
                    line_number=line_number,
                    source_snippet=source_snippet
                ))
        
        # Check for setAccessible
        elif method_name == 'setAccessible':
            call = ReflectionCall(
                method_name=method_name,
                object_type='AccessibleObject',
                arguments=self._get_arguments(node),
                line_number=line_number,
                source_snippet=source_snippet
            )
            self.reflection_calls.append(call)
            self.set_accessible_calls.append(call)
    
    def _process_class_creator(self, node: javalang.tree.ClassCreator, path: list):
        """Process class creation that might be from reflection."""
        # Handle Constructor.newInstance() patterns where
        # the constructor was obtained via reflection
        line_number = node.position.line if node.position else 0
        source_snippet = str(node)[:100]
        
        # Check if this looks like it came from reflection
        # This is detected via the MethodInvocation that creates the constructor reference
        pass
    
    def _is_static_reflection_call(self, node: javalang.tree.MethodInvocation, patterns: dict, path: list) -> bool:
        """Check if method invocation is a static reflection call on Class."""
        # Check if it's a static method call on a Class literal or type
        # Common patterns: Class.forName, Class.getMethod, MyClass.class.getSimpleName()
        
        # If it matches our known patterns, consider it a reflection call
        method_name = node.member
        if method_name in patterns:
            # Check for .class qualifier (e.g., MyClass.class)
            if node.qualifier and '.class' in node.qualifier.lower():
                return True
            # Check for direct Class reference
            if node.qualifier == 'Class':
                return True
            # If there's a chain of selectors after, it's likely on a Class object
            if hasattr(node, 'selectors') and node.selectors:
                return True
        
        # Also check if parent is a ClassReference (MyClass.class pattern)
        for parent in path:
            if isinstance(parent, javalang.tree.ClassReference):
                return True
        
        return False
    
    def _is_field_method(self, method_name: str) -> bool:
        """Check if method name is a Field reflection method."""
        return method_name in FIELD_METHODS
    
    def _is_method_method(self, method_name: str) -> bool:
        """Check if method name is a Method reflection method."""
        return method_name in METHOD_METHODS
    
    def _is_constructor_method(self, method_name: str) -> bool:
        """Check if method name is a Constructor reflection method."""
        return method_name in CONSTRUCTOR_METHODS
    
    def _is_annotation_method(self, method_name: str) -> bool:
        """Check if method name is an annotation reflection method."""
        return method_name in ANNOTATION_METHODS
    
    def _get_arguments(self, node: javalang.tree.MethodInvocation) -> List[str]:
        """Extract argument strings from method invocation."""
        if not node.arguments:
            return []
        
        args = []
        for arg in node.arguments:
            if isinstance(arg, javalang.tree.Literal):
                args.append(str(arg.value) if arg.value else '')
            elif isinstance(arg, javalang.tree.ElementValuePair):
                args.append(arg.name)
            else:
                # For complex expressions, just indicate presence
                args.append('<expr>')
        return args
    
    def _extract_class_name_argument(self, node: javalang.tree.MethodInvocation) -> Optional[str]:
        """Extract class name from Class.forName() argument."""
        if node.arguments and len(node.arguments) > 0:
            first_arg = node.arguments[0]
            if isinstance(first_arg, javalang.tree.Literal):
                value = str(first_arg.value) if first_arg.value else ''
                # Remove quotes
                if value.startswith('"') and value.endswith('"'):
                    return value[1:-1]
                if value.startswith("'") and value.endswith("'"):
                    return value[1:-1]
        return None
    
    def _extract_field_name(self, node: javalang.tree.MethodInvocation) -> Optional[str]:
        """Extract field name from Field.* method calls."""
        if node.arguments and len(node.arguments) > 0:
            first_arg = node.arguments[0]
            if isinstance(first_arg, javalang.tree.Literal):
                value = str(first_arg.value) if first_arg.value else ''
                if value.startswith('"') and value.endswith('"'):
                    return value[1:-1]
        return None
    
    def _extract_annotation_type(self, node: javalang.tree.MethodInvocation) -> Optional[str]:
        """Extract annotation type from annotation method calls."""
        if node.arguments and len(node.arguments) > 0:
            first_arg = node.arguments[0]
            # Could be a Class literal or type name
            if isinstance(first_arg, javalang.tree.ClassReference):
                # ClassReference has different attributes
                if hasattr(first_arg, 'name'):
                    return first_arg.name
                elif hasattr(first_arg, 'qualified_name'):
                    return first_arg.qualified_name
                # Try to get from children
                return 'Annotation'
            elif isinstance(first_arg, javalang.tree.Literal):
                value = str(first_arg.value) if first_arg.value else ''
                if value.startswith('"') and value.endswith('"'):
                    return value[1:-1]
        return None
    
    def _get_source_snippet(self, node) -> str:
        """Get source code snippet for a node."""
        if hasattr(node, 'position') and node.position:
            # Return a reasonable snippet
            return f"line {node.position.line}"
        return ""
    
    def _get_summary(self) -> dict:
        """Get summary of detected patterns."""
        return {
            'total_reflection_calls': len(self.reflection_calls),
            'dynamic_class_loads': len(self.dynamic_class_loads),
            'field_accesses': len(self.field_accesses),
            'method_invocations': len(self.method_invocations),
            'annotation_accesses': len(self.annotation_accesses),
            'set_accessible_calls': len(self.set_accessible_calls),
        }


def detect_reflection(source: str) -> List[ReflectionCall]:
    """
    Convenience function to detect reflection patterns in source code.
    
    Args:
        source: Java source code string
        
    Returns:
        List of detected ReflectionCall objects
    """
    detector = ReflectionDetector()
    return detector.detect_from_source(source)


def detect_reflection_detailed(source: str) -> dict:
    """
    Convenience function to detect reflection with full details.
    
    Args:
        source: Java source code string
        
    Returns:
        Dictionary with all detected patterns
    """
    detector = ReflectionDetector()
    return detector.detect_with_details(source)
