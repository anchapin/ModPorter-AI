"""Enum Mapper for Java to Bedrock Conversion.

This module provides functionality to map Java enums to TypeScript
compatible formats.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set
import re

from utils.enum_detector import JavaEnum, EnumConstant, EnumDetector


class ConversionStyle:
    """Style options for enum conversion."""
    CONST_ENUM = "const_enum"           # const enum { RED, GREEN }
    STRING_UNION = "string_union"       # type Color = "RED" | "GREEN"
    CONST_OBJECT = "const_object"       # const Color = { RED: "RED", ... }
    CONST_OBJECT_WITH_VALUES = "const_object_values"  # const Color = { RED: "#ff0000", ... }


@dataclass
class MappedEnum:
    """Represents a mapped TypeScript enum."""
    name: str
    style: ConversionStyle
    constants: List[str] = field(default_factory=list)
    type_definition: str = ""
    values: Dict[str, Any] = field(default_factory=dict)
    reverse_lookup: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    def __repr__(self) -> str:
        return f"MappedEnum({self.name}, style={self.style})"


@dataclass 
class EnumMappingResult:
    """Result of enum mapping operation."""
    success: bool
    source_enum: Optional[JavaEnum] = None
    mapped_enum: Optional[MappedEnum] = None
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def __repr__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return f"EnumMappingResult({status}, {self.source_enum.name if self.source_enum else 'N/A'})"


class EnumMapper:
    """Maps Java enums to TypeScript formats."""
    
    # Java enums implicitly extend java.lang.Enum
    JAVA_LANG_ENUM_METHODS = {
        'ordinal', 'name', 'valueOf', 'compareTo', 
        'equals', 'hashCode', 'toString', 'getDeclaringClass'
    }
    
    def __init__(self, style: ConversionStyle = ConversionStyle.STRING_UNION):
        self.style = style
        self._custom_mappings: Dict[str, str] = {}
    
    def map_enum(self, java_enum: JavaEnum) -> EnumMappingResult:
        """Map a Java enum to TypeScript format.
        
        Args:
            java_enum: The Java enum to map
            
        Returns:
            EnumMappingResult with mapped TypeScript enum
        """
        result = EnumMappingResult(
            success=False,
            source_enum=java_enum
        )
        
        if not java_enum.constants:
            result.errors.append(f"Enum {java_enum.name} has no constants")
            return result
        
        try:
            if java_enum.has_methods or java_enum.has_constructor:
                # Complex enum with methods - use const object with functions
                mapped = self._map_complex_enum(java_enum)
            else:
                # Simple enum - use preferred style
                mapped = self._map_simple_enum(java_enum)
            
            result.mapped_enum = mapped
            result.success = True
            
            # Copy warnings from mapped enum
            result.warnings = mapped.warnings
            
        except Exception as e:
            result.errors.append(f"Mapping error: {str(e)}")
        
        return result
    
    def _map_simple_enum(self, java_enum: JavaEnum) -> MappedEnum:
        """Map a simple enum (no methods)."""
        name = java_enum.name
        
        if self.style == ConversionStyle.STRING_UNION:
            return self._to_string_union(java_enum, name)
        elif self.style == ConversionStyle.CONST_ENUM:
            return self._to_const_enum(java_enum, name)
        elif self.style == ConversionStyle.CONST_OBJECT:
            return self._to_const_object(java_enum, name)
        else:
            return self._to_const_object_with_values(java_enum, name)
    
    def _map_complex_enum(self, java_enum: JavaEnum) -> MappedEnum:
        """Map an enum with methods - requires more complex handling."""
        name = java_enum.name
        
        # For enums with methods, we need const object format
        result = self._to_const_object(java_enum, name)
        
        # Add warning about method handling
        result.warnings.append(
            f"Enum {name} has methods/constructors - manual review recommended"
        )
        
        # Try to extract method signatures for documentation
        if java_enum.body:
            method_sigs = self._extract_method_signatures(java_enum.body)
            if method_sigs:
                result.type_definition += f"\n// Methods: {', '.join(method_sigs)}"
        
        return result
    
    def _to_string_union(self, java_enum: JavaEnum, name: str) -> MappedEnum:
        """Convert to TypeScript string union type."""
        constants = [f'"{c.name}"' for c in java_enum.constants]
        type_def = f"type {name} = {' | '.join(constants)};"
        
        return MappedEnum(
            name=name,
            style=ConversionStyle.STRING_UNION,
            constants=constants,
            type_definition=type_def
        )
    
    def _to_const_enum(self, java_enum: JavaEnum, name: str) -> MappedEnum:
        """Convert to TypeScript const enum."""
        const_list = ", ".join(c.name for c in java_enum.constants)
        type_def = f"const enum {name} {{ {const_list} }}"
        
        return MappedEnum(
            name=name,
            style=ConversionStyle.CONST_ENUM,
            constants=[c.name for c in java_enum.constants],
            type_definition=type_def
        )
    
    def _to_const_object(self, java_enum: JavaEnum, name: str) -> MappedEnum:
        """Convert to const object with string values."""
        values = {c.name: c.name for c in java_enum.constants}
        
        # Build type definition
        const_lines = [f"  {c.name}: '{c.name}'," for c in java_enum.constants]
        type_def = f"const {name} = {{\n{chr(10).join(const_lines)}\n}} as const;"
        
        # Create reverse lookup
        reverse_values = {c.name: c.name for c in java_enum.constants}
        
        return MappedEnum(
            name=name,
            style=ConversionStyle.CONST_OBJECT,
            constants=[c.name for c in java_enum.constants],
            type_definition=type_def,
            values=values,
            reverse_lookup=self._create_reverse_lookup(name, values)
        )
    
    def _to_const_object_with_values(self, java_enum: JavaEnum, name: str) -> MappedEnum:
        """Convert to const object with actual values."""
        values = {}
        
        for c in java_enum.constants:
            if c.value is not None:
                # Try to parse the value
                value = self._parse_value(c.value)
                values[c.name] = value
            else:
                # Use name as value for constants without explicit value
                values[c.name] = c.name
        
        # Build type definition
        const_lines = []
        for c in java_enum.constants:
            if c.value is not None:
                value = values[c.name]
                if isinstance(value, str):
                    const_lines.append(f"  {c.name}: '{value}',")
                else:
                    const_lines.append(f"  {c.name}: {value},")
            else:
                const_lines.append(f"  {c.name}: '{c.name}',")
        
        type_def = f"const {name} = {{\n{chr(10).join(const_lines)}\n}} as const;"
        
        return MappedEnum(
            name=name,
            style=ConversionStyle.CONST_OBJECT_WITH_VALUES,
            constants=[c.name for c in java_enum.constants],
            type_definition=type_def,
            values=values,
            reverse_lookup=self._create_reverse_lookup(name, values)
        )
    
    def _parse_value(self, value: str) -> Any:
        """Parse a Java enum value to appropriate TypeScript value."""
        value = value.strip()
        
        # Handle string literals
        if value.startswith('"') and value.endswith('"'):
            return value[1:-1]
        if value.startswith("'") and value.endswith("'"):
            return value[1:-1]
        
        # Handle numeric values
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        
        # Handle expressions (fall back to string)
        return value
    
    def _create_reverse_lookup(self, name: str, values: Dict[str, Any]) -> str:
        """Create a reverse lookup function/object."""
        reverse_values = {v: k for k, v in values.items() if isinstance(v, str)}
        
        if not reverse_values:
            return ""
        
        lines = [f"  '{v}': '{k}'," for k, v in reverse_values.items()]
        return f"const {name}Reverse = {{\n{chr(10).join(lines)}\n}} as const;"
    
    def _extract_method_signatures(self, body: str) -> List[str]:
        """Extract method signatures from enum body."""
        signatures = []
        
        # Pattern for method declarations
        pattern = r'(?:public|private|protected|static|final)?\s*(\w+(?:<[^>]+>)?(?:\[\])?)\s+(\w+)\s*\([^)]*\)'
        
        for match in re.finditer(pattern, body):
            return_type = match.group(1)
            method_name = match.group(2)
            
            # Skip constructors and java.lang.Enum methods
            if method_name not in self.JAVA_LANG_ENUM_METHODS:
                signatures.append(f"{return_type} {method_name}()")
        
        return signatures
    
    def map_java_lang_enum_methods(self) -> Dict[str, str]:
        """Map java.lang.Enum methods to TypeScript equivalents."""
        return {
            'ordinal': '/* ordinal not directly available - use index */',
            'name': '/* use enum constant directly */',
            'valueOf': '/* use key-value lookup */',
            'compareTo': '/* implement custom compare if needed */',
            'equals': '===',
            'hashCode': '/* not needed in TypeScript */',
            'toString': '/* use name property */',
            'getDeclaringClass': '/* not applicable */',
        }


def map_enum(
    java_enum: JavaEnum, 
    style: ConversionStyle = ConversionStyle.STRING_UNION
) -> EnumMappingResult:
    """Convenience function to map a Java enum.
    
    Args:
        java_enum: The Java enum to map
        style: Conversion style to use
        
    Returns:
        EnumMappingResult with mapped TypeScript enum
    """
    mapper = EnumMapper(style=style)
    return mapper.map_enum(java_enum)


def map_enums(
    java_enums: List[JavaEnum],
    style: ConversionStyle = ConversionStyle.STRING_UNION
) -> List[EnumMappingResult]:
    """Convenience function to map multiple Java enums.
    
    Args:
        java_enums: List of Java enums to map
        style: Conversion style to use
        
    Returns:
        List of EnumMappingResult objects
    """
    mapper = EnumMapper(style=style)
    return [mapper.map_enum(e) for e in java_enums]
