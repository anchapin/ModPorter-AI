"""Enum Value Extractor for Java to Bedrock Conversion.

This module provides functionality to extract enum constant values
and build reverse lookup maps.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set
import re

from utils.enum_detector import JavaEnum, EnumConstant, EnumDetector


@dataclass
class EnumValueInfo:
    """Information about an enum constant value."""
    constant_name: str
    value: Any
    value_type: str  # 'string', 'int', 'float', 'expression'
    line_number: Optional[int] = None
    
    def __repr__(self) -> str:
        return f"EnumValueInfo({self.constant_name}={self.value})"


@dataclass
class ExtractionResult:
    """Result of enum value extraction."""
    enum_name: str
    values: List[EnumValueInfo] = field(default_factory=list)
    reverse_lookup: Dict[Any, str] = field(default_factory=dict)
    has_duplicates: bool = False
    warnings: List[str] = field(default_factory=list)
    
    @property
    def value_to_name_map(self) -> Dict[Any, str]:
        """Get map from value to constant name."""
        return self.reverse_lookup
    
    @property
    def names(self) -> List[str]:
        """Get list of constant names."""
        return [v.constant_name for v in self.values]
    
    @property
    def ts_values(self) -> Dict[str, Any]:
        """Get TypeScript-compatible value map."""
        result = {}
        for v in self.values:
            if v.value_type == 'string':
                result[v.constant_name] = str(v.value)
            elif v.value_type in ('int', 'float'):
                result[v.constant_name] = v.value
            else:
                # For expressions, use name as fallback
                result[v.constant_name] = v.constant_name
        return result


class EnumValueExtractor:
    """Extracts and processes enum constant values."""
    
    def __init__(self):
        self._value_cache: Dict[str, Dict[Any, str]] = {}
    
    def extract(self, java_enum: JavaEnum) -> ExtractionResult:
        """Extract values from an enum.
        
        Args:
            java_enum: The Java enum to extract values from
            
        Returns:
            ExtractionResult with extracted values and reverse lookup
        """
        result = ExtractionResult(enum_name=java_enum.name)
        
        for const in java_enum.constants:
            # Always extract constants, even if value is None
            value_info = self._parse_constant_value(const)
            result.values.append(value_info)
            
            # Build reverse lookup only for constants with explicit values
            if value_info.value is not None:
                if value_info.value in result.reverse_lookup:
                    result.has_duplicates = True
                    result.warnings.append(
                        f"Duplicate value '{value_info.value}' for "
                        f"{const.name} and {result.reverse_lookup[value_info.value]}"
                    )
                else:
                    result.reverse_lookup[value_info.value] = const.name
        
        return result
    
    def _parse_constant_value(self, const: EnumConstant) -> EnumValueInfo:
        """Parse a constant's value."""
        value = const.value
        value_type = 'expression'
        parsed_value = value
        
        if value is None:
            # Use ordinal for constants without explicit value
            parsed_value = const.ordinal
            value_type = 'int'
        elif isinstance(value, int) and not isinstance(value, bool):
            # Already a numeric value (not string)
            parsed_value = value
            value_type = 'int'
        elif isinstance(value, float):
            # Already a float value
            parsed_value = value
            value_type = 'float'
        elif isinstance(value, str):
            # Determine type and parse
            value = value.strip()
            
            # String literal
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                parsed_value = value[1:-1]
                value_type = 'string'
            # Numeric
            else:
                try:
                    if '.' in value:
                        parsed_value = float(value)
                        value_type = 'float'
                    else:
                        parsed_value = int(value)
                        value_type = 'int'
                except ValueError:
                    # Expression or identifier - keep as-is
                    value_type = 'expression'
        
        return EnumValueInfo(
            constant_name=const.name,
            value=parsed_value,
            value_type=value_type,
            line_number=None
        )
    
    def build_reverse_lookup(
        self, 
        values: Dict[str, Any]
    ) -> Dict[Any, str]:
        """Build reverse lookup map (value -> name).
        
        Args:
            values: Map of constant names to values
            
        Returns:
            Map of values to constant names
        """
        reverse: Dict[Any, str] = {}
        
        for name, value in values.items():
            if value is not None and value != '':
                # Convert value to hashable type
                hashable_value = value if isinstance(value, (int, float, str)) else str(value)
                
                if hashable_value in reverse:
                    # Duplicate value - prefer first occurrence
                    pass
                else:
                    reverse[hashable_value] = name
        
        return reverse
    
    def extract_all_enums(self, enums: List[JavaEnum]) -> List[ExtractionResult]:
        """Extract values from multiple enums.
        
        Args:
            enums: List of Java enums
            
        Returns:
            List of ExtractionResult for each enum
        """
        return [self.extract(e) for e in enums]
    
    def get_type_for_enum(self, java_enum: JavaEnum) -> str:
        """Determine the best TypeScript type for an enum.
        
        Args:
            java_enum: The Java enum
            
        Returns:
            TypeScript type string
        """
        if not java_enum.constants:
            return "never"
        
        # First extract values to get proper types
        extraction = self.extract(java_enum)
        
        if not extraction.values:
            # No explicit values - use string
            return "string"
        
        # Check extracted value types
        string_values = sum(1 for v in extraction.values if v.value_type == 'string')
        numeric_values = sum(1 for v in extraction.values if v.value_type in ('int', 'float'))
        
        total = len(extraction.values)
        
        if string_values == total:
            return "string"
        elif numeric_values == total:
            return "number"
        
        # Mixed or no values - use string union
        return "string"


def extract_enum_values(java_enum: JavaEnum) -> ExtractionResult:
    """Convenience function to extract enum values.
    
    Args:
        java_enum: The Java enum to extract from
        
    Returns:
        ExtractionResult with extracted values
    """
    extractor = EnumValueExtractor()
    return extractor.extract(java_enum)


def extract_all_enum_values(enums: List[JavaEnum]) -> List[ExtractionResult]:
    """Convenience function to extract values from multiple enums.
    
    Args:
        enums: List of Java enums
        
    Returns:
        List of ExtractionResult for each enum
    """
    extractor = EnumValueExtractor()
    return extractor.extract_all_enums(enums)
