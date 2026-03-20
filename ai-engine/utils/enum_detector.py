"""Enum Detector for Java to Bedrock Conversion.

This module provides functionality to detect and analyze Java enums
in source code for conversion to TypeScript-compatible format.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set
import re


@dataclass
class EnumConstant:
    """Represents a single constant in a Java enum."""
    name: str
    value: Optional[Any] = None
    arguments: List[Any] = field(default_factory=list)
    body: Optional[str] = None
    ordinal: Optional[int] = None
    
    def __repr__(self) -> str:
        if self.value is not None:
            return f"EnumConstant({self.name}={self.value})"
        return f"EnumConstant({self.name})"


@dataclass
class JavaEnum:
    """Represents a complete Java enum declaration."""
    name: str
    constants: List[EnumConstant] = field(default_factory=list)
    implements: List[str] = field(default_factory=list)
    body: Optional[str] = None
    line_number: Optional[int] = None
    has_methods: bool = False
    has_constructor: bool = False
    is_implicit_extends_java_lang_enum: bool = True
    
    def __repr__(self) -> str:
        return f"JavaEnum({self.name}, {len(self.constants)} constants)"
    
    @property
    def constant_names(self) -> List[str]:
        """Get list of constant names."""
        return [c.name for c in self.constants]


class EnumDetector:
    """Detects and analyzes Java enums in source code."""
    
    # Regex patterns for enum detection
    BASIC_ENUM_PATTERN = r'enum\s+(\w+)\s*\{(.*?)\n\s*\}'
    ENUM_WITH_IMPLEMENTS_PATTERN = r'enum\s+(\w+)\s+implements\s+([^{]+)\s*\{(.*?)\n\s*\}'
    CONSTANT_PATTERN = r'(\w+)(?:\s*\(\s*([^)]*)\s*\))?(?:\s*\{([^}]*)\})?'
    CONSTANT_VALUE_PATTERN = r'(\w+)\s*=\s*([^,}\s]+)'
    
    def __init__(self):
        self.enums: List[JavaEnum] = []
        self._source_lines: List[str] = []
    
    def reset(self):
        """Reset detector state for new source."""
        self.enums = []
        self._source_lines = []
    
    def detect_from_source(self, source_code: str) -> List[JavaEnum]:
        """Detect all enums in source code.
        
        Args:
            source_code: Java source code string
            
        Returns:
            List of detected JavaEnum objects
        """
        self.reset()
        self._source_lines = source_code.split('\n')
        
        # Detect enums using regex
        self._detect_enums(source_code)
        
        # Also try AST-based detection if javalang is available
        try:
            self._detect_with_javalang(source_code)
        except Exception:
            pass  # Fall back to regex-only detection
        
        return self.enums
    
    def _detect_enums(self, source: str) -> None:
        """Detect enums using regex patterns."""
        
        # Use javalang for primary detection - more accurate
        try:
            self._detect_with_javalang(source)
            if self.enums:
                return  # javalang found enums, skip regex
        except Exception:
            pass  # Fall back to regex
        
        # Fallback: detect enums using regex patterns
        
        # First: detect enums with implements clause
        implements_matches = re.finditer(
            self.ENUM_WITH_IMPLEMENTS_PATTERN,
            source,
            re.MULTILINE | re.DOTALL
        )
        
        for match in implements_matches:
            enum_name = match.group(1)
            implements_str = match.group(2)
            body = match.group(3)
            
            java_enum = JavaEnum(
                name=enum_name,
                implements=[i.strip() for i in implements_str.split(',')],
                body=body,
                line_number=self._find_line_number(source, match.start())
            )
            
            self._parse_enum_body(java_enum, body)
            self.enums.append(java_enum)
        
        # Second: detect basic enums (not already captured)
        basic_matches = re.finditer(
            self.BASIC_ENUM_PATTERN,
            source,
            re.MULTILINE | re.DOTALL
        )
        
        for match in basic_matches:
            enum_name = match.group(1)
            body = match.group(2)
            
            # Skip if already detected with implements
            if any(e.name == enum_name for e in self.enums):
                continue
            
            java_enum = JavaEnum(
                name=enum_name,
                body=body,
                line_number=self._find_line_number(source, match.start())
            )
            
            self._parse_enum_body(java_enum, body)
            self.enums.append(java_enum)
    
    def _parse_enum_body(self, enum: JavaEnum, body: str) -> None:
        """Parse the body of an enum to extract constants and methods."""
        if not body:
            return
        
        lines = body.split('\n')
        
        # Track if we've seen methods (after constants)
        in_constant_section = True
        constant_ordinal = 0
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('//') or stripped.startswith('/*'):
                continue
            
            # Check if we're entering method section
            if stripped.startswith('public') or stripped.startswith('private') or \
               stripped.startswith('protected') or stripped.startswith('static') or \
               stripped.startswith('abstract'):
                if in_constant_section:
                    in_constant_section = False
                enum.has_methods = True
                continue
            
            # Try to match constant with value: NAME = value
            value_match = re.match(self.CONSTANT_VALUE_PATTERN, stripped)
            if value_match:
                const_name = value_match.group(1)
                const_value = value_match.group(2).strip()
                
                enum.constants.append(EnumConstant(
                    name=const_name,
                    value=const_value,
                    ordinal=constant_ordinal
                ))
                constant_ordinal += 1
                continue
            
            # Try to match constant without value: NAME or NAME()
            const_match = re.match(r'(\w+)(?:\(\))?', stripped)
            if const_match and in_constant_section:
                const_name = const_match.group(1)
                
                # Skip if it's a keyword or method
                if const_name in ('class', 'interface', 'enum', 'true', 'false', 'null'):
                    continue
                
                # Check for body (anonymous class-like constant)
                body_match = re.search(r'\{([^}]*)\}', stripped)
                const_body = body_match.group(1) if body_match else None
                
                enum.constants.append(EnumConstant(
                    name=const_name,
                    body=const_body,
                    ordinal=constant_ordinal
                ))
                constant_ordinal += 1
    
    def _find_line_number(self, source: str, position: int) -> int:
        """Find line number for a position in source."""
        return source[:position].count('\n') + 1
    
    def _detect_with_javalang(self, source: str) -> None:
        """Detect enums using javalang AST library."""
        try:
            import javalang
        except ImportError:
            return
        
        try:
            tree = javalang.parse.parse(source)
            
            for path, node in tree.filter(javalang.tree.EnumDeclaration):
                enum_name = node.name
                implements = [i.name for i in node.implements] if node.implements else []
                
                java_enum = JavaEnum(
                    name=enum_name,
                    implements=implements,
                    line_number=node.position.line if node.position else None
                )
                
                # Extract constants from EnumBody
                if node.body:
                    # Handle EnumBody - has 'constants' and 'declarations' attributes
                    if hasattr(node.body, 'constants'):
                        for const_decl in node.body.constants:
                            const_name = const_decl.name
                            const_args = []
                            if const_decl.arguments:
                                const_args = [arg.value for arg in const_decl.arguments]
                            
                            # Check if constant has body (methods)
                            has_body = const_decl.body is not None
                            
                            java_enum.constants.append(EnumConstant(
                                name=const_name,
                                arguments=const_args,
                                body=str(const_decl.body) if has_body else None,
                                ordinal=len(java_enum.constants)
                            ))
                            
                            # If any constant has a body, the enum has methods
                            if has_body:
                                java_enum.has_methods = True
                    
                    # Handle declarations (methods, constructors, etc.)
                    if hasattr(node.body, 'declarations'):
                        for decl in node.body.declarations:
                            if isinstance(decl, javalang.tree.MethodDeclaration):
                                java_enum.has_methods = True
                            elif isinstance(decl, javalang.tree.ConstructorDeclaration):
                                java_enum.has_constructor = True
                
                # Skip if already detected
                if not any(e.name == enum_name for e in self.enums):
                    self.enums.append(java_enum)
        
        except Exception:
            pass  # Fall back to regex
    
    def is_enum_type(self, type_name: str) -> bool:
        """Check if a type name refers to an enum."""
        return any(e.name == type_name for e in self.enums)
    
    def get_enum(self, type_name: str) -> Optional[JavaEnum]:
        """Get enum by type name."""
        for enum in self.enums:
            if enum.name == type_name:
                return enum
        return None


def detect_enums(source_code: str) -> List[JavaEnum]:
    """Convenience function to detect enums in source code.
    
    Args:
        source_code: Java source code string
        
    Returns:
        List of detected JavaEnum objects
    """
    detector = EnumDetector()
    return detector.detect_from_source(source_code)


def is_enum_type(source_code: str, type_name: str) -> bool:
    """Convenience function to check if a type is an enum.
    
    Args:
        source_code: Java source code string
        type_name: Type name to check
        
    Returns:
        True if type_name is an enum in the source
    """
    detector = EnumDetector()
    detector.detect_from_source(source_code)
    return detector.is_enum_type(type_name)
