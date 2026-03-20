"""Inner Classes Handler for Java to Bedrock Conversion.

This module provides functionality to detect, analyze, and convert Java inner classes
(static nested classes, non-static inner classes, local classes, and anonymous classes)
to JavaScript/TypeScript.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
import re


class InnerClassType(Enum):
    """Types of inner classes in Java."""
    STATIC_NESTED = "static_nested"
    NON_STATIC_INNER = "non_static_inner"
    LOCAL = "local"
    ANONYMOUS = "anonymous"


@dataclass
class InnerClassParameter:
    """Represents a parameter in an inner class constructor or context."""
    name: str
    type_hint: Optional[str] = None
    is_final: bool = False
    
    def __repr__(self) -> str:
        if self.type_hint:
            return f"InnerClassParameter({self.name}: {self.type_hint})"
        return f"InnerClassParameter({self.name})"


@dataclass
class EnclosingClassReference:
    """Represents a reference to the enclosing class (e.g., OuterClass.this)."""
    enclosing_class_name: str
    reference_type: str  # 'this', 'member_access'
    member_name: Optional[str] = None
    
    def __repr__(self) -> str:
        if self.member_name:
            return f"{self.enclosing_class_name}.{self.member_name}"
        return f"{self.enclosing_class_name}.this"


@dataclass
class InnerClass:
    """Represents a complete inner class definition."""
    name: str
    inner_class_type: InnerClassType
    enclosing_class: Optional[str] = None
    modifiers: List[str] = field(default_factory=list)
    extends: Optional[str] = None
    implements: List[str] = field(default_factory=list)
    members: List[str] = field(default_factory=list)
    enclosing_references: List[EnclosingClassReference] = field(default_factory=list)
    captured_variables: List[str] = field(default_factory=list)
    line_number: Optional[int] = None
    is_accessing_enclosing_members: bool = False
    
    def __repr__(self) -> str:
        return f"InnerClass({self.inner_class_type.value}: {self.name})"


@dataclass
class ConversionResult:
    """Result of converting an inner class to JavaScript/TypeScript."""
    success: bool
    converted_code: str
    converted_name: str
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class InnerClassDetector:
    """Detects and analyzes inner classes in Java source code."""
    
    # Java modifier patterns
    MODIFIER_PATTERN = r'(?:(public|private|protected|static|final|abstract|strictfp)\s+)*'
    
    # Pattern for static nested class
    STATIC_NESTED_PATTERN = re.compile(
        r'(?:(public|private|protected)\s+)?static\s+class\s+(\w+)'
    )
    
    # Pattern for non-static inner class
    INNER_CLASS_PATTERN = re.compile(
        r'(?:(public|private|protected)\s+)?(?:final\s+)?class\s+(\w+)(?:\s+extends\s+([\w.]+))?(?:\s+implements\s+([\w.,\s]+))?'
    )
    
    # Pattern for anonymous class
    ANONYMOUS_PATTERN = re.compile(
        r'new\s+([\w.]+)\s*\('
    )
    
    # Pattern for OuterClass.this reference
    OUTER_THIS_PATTERN = re.compile(
        r'(\w+)\.this(?:\.(\w+))?'
    )
    
    # Common local class patterns (class defined inside method)
    LOCAL_CLASS_PATTERN = re.compile(
        r'(?:public|private|protected)?\s*class\s+(\w+)(?:\s+extends\s+([\w.]+))?'
    )
    
    def __init__(self):
        self.inner_classes: List[InnerClass] = []
        self.enclosing_class_stack: List[str] = []
    
    def detect_from_source(self, source: str) -> List[InnerClass]:
        """Detect inner classes from Java source code.
        
        Args:
            source: Java source code string
            
        Returns:
            List of detected InnerClass objects
        """
        self.inner_classes = []
        self.enclosing_class_stack = []
        
        lines = source.split('\n')
        brace_depth = 0
        in_class_body = False
        in_method_body = False
        current_class_modifiers = []
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Track brace depth for proper nesting detection
            brace_depth += stripped.count('{') - stripped.count('}')
            
            # Detect top-level class (enclosing class)
            top_level_match = re.match(r'(?:(@\w+\s+)*)(public|private|protected)?\s*(class|interface|enum)\s+(\w+)(?:\s+extends\s+([\w.]+))?(?:\s+implements\s+([\w.,\s]+))?', stripped)
            if top_level_match and brace_depth <= 1 and len(self.enclosing_class_stack) == 0:
                class_name = top_level_match.group(4)
                extends = top_level_match.group(5)
                implements_str = top_level_match.group(6)
                implements = [imp.strip() for imp in implements_str.split(',')] if implements_str else []
                
                self.enclosing_class_stack.append(class_name)
                current_class_modifiers = []
                if 'static' in stripped:
                    current_class_modifiers.append('static')
                in_class_body = True
                in_method_body = False
                continue
            
            # Detect method definition - marks start of potential local class context
            method_match = re.match(r'(?:(public|private|protected|static|\w+)\s+)*\w+\s+\w+\s*\([^)]*\)\s*\{', stripped)
            if method_match and brace_depth >= 1:
                in_method_body = True
                continue
            
            # Check for end of method (decrease in brace depth)
            if stripped == '}' and brace_depth == 1:
                in_method_body = False
            
            # Check for end of class
            if stripped == '}' and in_class_body and brace_depth == 0:
                if self.enclosing_class_stack:
                    self.enclosing_class_stack.pop()
                in_class_body = False
                in_method_body = False
                continue
            
            # Only look for inner classes if we're inside a class
            if not self.enclosing_class_stack:
                continue
            
            # Detect static nested class with extends/implements
            static_match = re.search(r'static\s+class\s+(\w+)(?:\s+extends\s+([\w.]+))?(?:\s+implements\s+([\w.,\s]+))?', stripped)
            if static_match:
                class_name = static_match.group(1)
                extends = static_match.group(2)
                implements_str = static_match.group(3)
                implements = [imp.strip() for imp in implements_str.split(',')] if implements_str else []
                
                inner = self._create_inner_class(
                    class_name, InnerClassType.STATIC_NESTED, i,
                    extends=extends, implements=implements, modifiers=['static']
                )
                self.inner_classes.append(inner)
                continue
            
            # Detect non-static inner class (class inside class at brace_depth >= 1)
            inner_match = re.search(r'(?:(public|private|protected)\s+)?(?:final\s+)?class\s+(\w+)(?:\s+extends\s+([\w.]+))?(?:\s+implements\s+([\w.,\s]+))?', stripped)
            if inner_match and brace_depth >= 1 and not in_method_body and 'static' not in stripped:
                class_name = inner_match.group(2)
                extends = inner_match.group(3)
                implements_str = inner_match.group(4)
                implements = [imp.strip() for imp in implements_str.split(',')] if implements_str else []
                modifiers = [inner_match.group(1)] if inner_match.group(1) else []
                
                inner = self._create_inner_class(
                    class_name, InnerClassType.NON_STATIC_INNER, i,
                    extends=extends, implements=implements, modifiers=modifiers
                )
                self.inner_classes.append(inner)
                continue
            
            # Detect local class (class defined inside method)
            if in_method_body and 'class' in stripped:
                local_match = re.search(r'class\s+(\w+)(?:\s+extends\s+([\w.]+))?', stripped)
                if local_match:
                    class_name = local_match.group(1)
                    extends = local_match.group(2)
                    inner = self._create_inner_class(
                        class_name, InnerClassType.LOCAL, i,
                        extends=extends
                    )
                    self.inner_classes.append(inner)
                    continue
            
            # Detect anonymous class (new X() { ... })
            if 'new ' in stripped and '{' in stripped and 'class' not in stripped:
                # Look for interface/class instantiation
                anon_match = re.search(r'new\s+([\w.]+)\s*\(', stripped)
                if anon_match:
                    target_class = anon_match.group(1)
                    inner = InnerClass(
                        name=f"Anonymous_{target_class}",
                        inner_class_type=InnerClassType.ANONYMOUS,
                        enclosing_class=self.enclosing_class_stack[-1] if self.enclosing_class_stack else None,
                        line_number=i
                    )
                    self.inner_classes.append(inner)
                    continue
            
            # Detect OuterClass.this references
            outer_refs = self.OUTER_THIS_PATTERN.findall(stripped)
            for ref in outer_refs:
                if ref[0] in self.enclosing_class_stack:
                    enclosing_ref = EnclosingClassReference(
                        enclosing_class_name=ref[0],
                        reference_type='this' if not ref[1] else 'member_access',
                        member_name=ref[1] if ref[1] else None
                    )
                    # Add to most recent inner class
                    if self.inner_classes:
                        self.inner_classes[-1].enclosing_references.append(enclosing_ref)
                        self.inner_classes[-1].is_accessing_enclosing_members = True
        
        return self.inner_classes
    
    def _create_inner_class(self, name: str, inner_type: InnerClassType, line: int, 
                           extends: Optional[str] = None, implements: Optional[List[str]] = None,
                           modifiers: Optional[List[str]] = None) -> InnerClass:
        """Create an InnerClass object with basic info."""
        return InnerClass(
            name=name,
            inner_class_type=inner_type,
            enclosing_class=self.enclosing_class_stack[-1] if self.enclosing_class_stack else None,
            line_number=line,
            extends=extends,
            implements=implements or [],
            modifiers=modifiers or []
        )
    
    def get_inner_class_count(self) -> int:
        """Get the count of detected inner classes."""
        return len(self.inner_classes)
    
    def get_by_type(self, inner_type: InnerClassType) -> List[InnerClass]:
        """Get inner classes filtered by type."""
        return [ic for ic in self.inner_classes if ic.inner_class_type == inner_type]
    
    def has_access_to_enclosing(self) -> bool:
        """Check if any inner class accesses enclosing class members."""
        return any(ic.is_accessing_enclosing_members for ic in self.inner_classes)


class InnerClassMapper:
    """Maps Java inner classes to JavaScript/TypeScript equivalents."""
    
    def __init__(self):
        self.converted_classes: Dict[str, ConversionResult] = {}
    
    def map_to_js(self, inner_class: InnerClass, use_typescript: bool = True) -> ConversionResult:
        """Convert a Java inner class to JavaScript/TypeScript.
        
        Args:
            inner_class: The InnerClass to convert
            use_typescript: Whether to use TypeScript syntax
            
        Returns:
            ConversionResult with converted code
        """
        warnings = []
        errors = []
        
        if inner_class.inner_class_type == InnerClassType.STATIC_NESTED:
            return self._convert_static_nested(inner_class, use_typescript)
        
        elif inner_class.inner_class_type == InnerClassType.NON_STATIC_INNER:
            return self._convert_non_static_inner(inner_class, use_typescript)
        
        elif inner_class.inner_class_type == InnerClassType.LOCAL:
            return self._convert_local_class(inner_class, use_typescript)
        
        elif inner_class.inner_class_type == InnerClassType.ANONYMOUS:
            return self._convert_anonymous_class(inner_class, use_typescript)
        
        else:
            errors.append(f"Unknown inner class type: {inner_class.inner_class_type}")
            return ConversionResult(
                success=False,
                converted_code="",
                converted_name=inner_class.name,
                errors=errors
            )
    
    def _convert_static_nested(self, inner_class: InnerClass, use_typescript: bool) -> ConversionResult:
        """Convert static nested class to ES6 module or TypeScript."""
        warnings = []
        
        # Static nested classes can be exported as separate modules or nested classes
        ts_type = "class" if use_typescript else "class"
        
        code_lines = [
            f"// Static nested class converted from Java",
            f"// Original: {inner_class.enclosing_class}.{inner_class.name}",
            f"",
        ]
        
        if use_typescript:
            code_lines.append(f"export {ts_type} {inner_class.name} {{")
        else:
            code_lines.append(f"// Use as: OuterClass.{inner_class.name}")
            code_lines.append(f"class {inner_class.name} {{")
        
        # Add placeholder members
        code_lines.append("    // Members converted from Java")
        code_lines.append("    constructor() {")
        
        if inner_class.extends:
            code_lines.append(f"        super(); // extends {inner_class.extends}")
        
        code_lines.append("    }")
        code_lines.append("}")
        
        converted_code = "\n".join(code_lines)
        
        return ConversionResult(
            success=True,
            converted_code=converted_code,
            converted_name=inner_class.name,
            warnings=warnings
        )
    
    def _convert_non_static_inner(self, inner_class: InnerClass, use_typescript: bool) -> ConversionResult:
        """Convert non-static inner class with closure handling."""
        warnings = ["Non-static inner class requires closure to access enclosing instance"]
        
        outer_ref = inner_class.enclosing_class or "OuterClass"
        
        code_lines = [
            f"// Non-static inner class converted from Java",
            f"// Original: {outer_ref}.{inner_class.name}",
            f"",
        ]
        
        # Create factory function pattern for inner class
        if use_typescript:
            code_lines.append(f"export class {inner_class.name} {{")
            code_lines.append(f"    private outer: {outer_ref};")
            code_lines.append(f"")
            code_lines.append(f"    constructor(outer: {outer_ref}) {{")
            code_lines.append(f"        this.outer = outer;")
            code_lines.append(f"    }}")
        else:
            code_lines.append(f"class {inner_class.name} {{")
            code_lines.append(f"    constructor(outer) {{")
            code_lines.append(f"        this.outer = outer;")
            code_lines.append(f"    }}")
        
        # Handle enclosing class member access
        if inner_class.is_accessing_enclosing_members:
            outer_ref = inner_class.enclosing_class or "Outer"
            code_lines.append(f"")
            if use_typescript:
                code_lines.append(f"    // Access to enclosing class members via this.outer")
                code_lines.append(f"    getOuter(): {outer_ref} {{")
                code_lines.append(f"        return this.outer;")
                code_lines.append(f"    }}")
            else:
                code_lines.append(f"    // Access to enclosing class members via this.outer")
                code_lines.append(f"    getOuter() {{")
                code_lines.append(f"        return this.outer;")
                code_lines.append(f"    }}")
        
        code_lines.append("}")
        
        # Add factory function
        code_lines.append(f"")
        code_lines.append(f"// Factory function to create {inner_class.name} instance")
        if use_typescript:
            code_lines.append(f"export function create{inner_class.name}(outer: {outer_ref}): {inner_class.name} {{")
        else:
            code_lines.append(f"function create{inner_class.name}(outer) {{")
        code_lines.append(f"    return new {inner_class.name}(outer);")
        code_lines.append("}")
        
        converted_code = "\n".join(code_lines)
        
        return ConversionResult(
            success=True,
            converted_code=converted_code,
            converted_name=inner_class.name,
            warnings=warnings
        )
    
    def _convert_local_class(self, inner_class: InnerClass, use_typescript: bool) -> ConversionResult:
        """Convert local class (defined inside method)."""
        warnings = ["Local classes are converted to function-scoped or module-level exports"]
        
        code_lines = [
            f"// Local class converted from Java",
            f"// Original location: method within {inner_class.enclosing_class}",
            f"",
        ]
        
        if use_typescript:
            code_lines.append(f"export class {inner_class.name} {{")
            code_lines.append(f"    // Members converted from Java local class")
            code_lines.append(f"    constructor() {{")
            code_lines.append(f"        // Constructor logic")
            code_lines.append(f"    }}")
            code_lines.append(f"}}")
        else:
            code_lines.append(f"class {inner_class.name} {{")
            code_lines.append(f"    constructor() {{")
            code_lines.append(f"        // Constructor logic")
            code_lines.append(f"    }}")
            code_lines.append(f"}}")
        
        converted_code = "\n".join(code_lines)
        
        return ConversionResult(
            success=True,
            converted_code=converted_code,
            converted_name=inner_class.name,
            warnings=warnings
        )
    
    def _convert_anonymous_class(self, inner_class: InnerClass, use_typescript: bool) -> ConversionResult:
        """Convert anonymous class to function expression or named function."""
        warnings = ["Anonymous classes converted to function expressions"]
        
        # Extract the base class from the name (e.g., "Runnable" from "Anonymous_java.lang.Runnable")
        base_name = inner_class.name.replace("Anonymous_", "")
        
        code_lines = [
            f"// Anonymous class converted from Java",
            f"// Original: new {base_name}(...)",
            f"",
        ]
        
        if use_typescript:
            code_lines.append(f"export const {base_name}Impl = (): {base_name} => {{")
        else:
            code_lines.append(f"const {base_name}Impl = () => {{")
        
        code_lines.append(f"    return {{")
        code_lines.append(f"        // Implement interface methods")
        code_lines.append(f"    }};")
        code_lines.append(f"}};")
        
        converted_code = "\n".join(code_lines)
        
        return ConversionResult(
            success=True,
            converted_code=converted_code,
            converted_name=f"{base_name}Impl",
            warnings=warnings
        )


class ClassHierarchyAnalyzer:
    """Analyzes class hierarchy and handles enclosing class context."""
    
    def __init__(self):
        self.class_hierarchy: Dict[str, Dict[str, Any]] = {}
        self.current_context: Optional[str] = None
    
    def analyze(self, source: str) -> Dict[str, Any]:
        """Analyze class hierarchy from source code.
        
        Args:
            source: Java source code
            
        Returns:
            Dictionary with hierarchy information
        """
        hierarchy = {
            "classes": {},
            "inner_class_relationships": [],
            "enclosing_references": []
        }
        
        # Extract class definitions with better parsing
        lines = source.split('\n')
        brace_depth = 0
        current_class = None
        
        for line in lines:
            stripped = line.strip()
            brace_depth += stripped.count('{') - stripped.count('}')
            
            # Detect class definition
            class_match = re.match(
                r'(?:(public|private|protected)\s+)?(?:static\s+)?(?:final\s+)?'
                r'class\s+(\w+)(?:\s+extends\s+([\w.]+))?(?:\s+implements\s+([\w.,\s]+))?',
                stripped
            )
            
            if class_match:
                full_match = class_match.group(0)
                modifiers = [m for m in [class_match.group(1)] if m]
                class_name = class_match.group(2)
                extends = class_match.group(3)
                implements_str = class_match.group(4)
                
                # Check if static is present in the full match
                has_static = 'static' in full_match
                
                # Determine if this is an inner class based on brace depth
                is_inner = brace_depth > 1
                
                hierarchy["classes"][class_name] = {
                    "modifiers": modifiers,
                    "extends": extends,
                    "implements": [i.strip() for i in implements_str.split(',') if i.strip()] if implements_str else [],
                    "is_static": has_static,
                    "is_inner": is_inner
                }
                
                if is_inner and current_class:
                    hierarchy["inner_class_relationships"].append({
                        "outer": current_class,
                        "inner": class_name,
                        "relationship": "contains"
                    })
                
                current_class = class_name
            
            # Track end of class
            if stripped == '}' and brace_depth == 0:
                current_class = None
        
        # Track inner class relationships more accurately
        outer_pattern = re.compile(r'class\s+(\w+)\s*\{[^}]*?class\s+(\w+)')
        outer_classes = outer_pattern.findall(source)
        for outer, inner in outer_classes:
            # Check if already added
            existing = [r for r in hierarchy["inner_class_relationships"] 
                       if r["outer"] == outer and r["inner"] == inner]
            if not existing:
                hierarchy["inner_class_relationships"].append({
                    "outer": outer,
                    "inner": inner,
                    "relationship": "contains"
                })
        
        # Track OuterClass.this references
        this_pattern = re.compile(r'(\w+)\.this(?:\.(\w+))?')
        this_refs = this_pattern.findall(source)
        
        for ref in this_refs:
            hierarchy["enclosing_references"].append({
                "enclosing_class": ref[0],
                "member": ref[1] if ref[1] else None,
                "type": "member_access" if ref[1] else "this_reference"
            })
        
        return hierarchy
    
    def get_enclosing_context(self, class_name: str) -> Optional[str]:
        """Get the enclosing class for an inner class."""
        for rel in self.class_hierarchy.get("inner_class_relationships", []):
            if rel["inner"] == class_name:
                return rel["outer"]
        return None
    
    def has_enclosing_access(self, class_name: str) -> bool:
        """Check if a class accesses enclosing class members."""
        for ref in self.class_hierarchy.get("enclosing_references", []):
            # Check if the reference is within this class context
            return True  # Simplified - would need line numbers for accuracy
        return False


# ===== Convenience Functions =====

def detect_inner_classes(source: str) -> List[InnerClass]:
    """Detect inner classes in Java source code.
    
    Args:
        source: Java source code string
        
    Returns:
        List of detected InnerClass objects
    """
    detector = InnerClassDetector()
    return detector.detect_from_source(source)


def map_inner_class_to_js(inner_class: InnerClass, use_typescript: bool = True) -> ConversionResult:
    """Map a Java inner class to JavaScript/TypeScript.
    
    Args:
        inner_class: The InnerClass to convert
        use_typescript: Whether to use TypeScript syntax
        
    Returns:
        ConversionResult with converted code
    """
    mapper = InnerClassMapper()
    return mapper.map_to_js(inner_class, use_typescript)


def analyze_class_hierarchy(source: str) -> Dict[str, Any]:
    """Analyze class hierarchy in Java source.
    
    Args:
        source: Java source code
        
    Returns:
        Hierarchy analysis results
    """
    analyzer = ClassHierarchyAnalyzer()
    return analyzer.analyze(source)
