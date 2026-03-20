"""Switch Mapper for Java to Bedrock Conversion.

This module provides functionality to map Java switch expressions and statements
to JavaScript/TypeScript compatible format.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set

from utils.switch_detector import (
    JavaSwitchExpression, 
    SwitchCase, 
    SwitchDetector,
    detect_switches
)


class ConversionStyle:
    """Style options for switch conversion."""
    IF_CHAIN = "if_chain"           # if-else if-else chain
    OBJECT_LITERAL = "object_literal"  # object literal with keys (for String/enum)
    SWITCH_STATEMENT = "switch_statement"  # Native switch (preserves Java style)
    TERNARY_CHAIN = "ternary_chain"   # Nested ternary operators


@dataclass
class MappedSwitch:
    """Represents a mapped JavaScript switch."""
    original_expression: str
    style: ConversionStyle
    mapped_code: str
    type_definition: str = ""
    warnings: List[str] = field(default_factory=list)
    
    def __repr__(self) -> str:
        return f"MappedSwitch({self.style})"


@dataclass 
class SwitchMappingResult:
    """Result of switch mapping operation."""
    success: bool
    source_switch: Optional[JavaSwitchExpression] = None
    mapped_switch: Optional[MappedSwitch] = None
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def __repr__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return f"SwitchMappingResult({status}, {self.source_switch.expression if self.source_switch else 'N/A'})"


class SwitchMapper:
    """Maps Java switch expressions/statements to JavaScript formats."""
    
    def __init__(self, style: ConversionStyle = ConversionStyle.SWITCH_STATEMENT):
        self.style = style
        self._custom_mappings: Dict[str, str] = {}
    
    def map_switch(self, java_switch: JavaSwitchExpression) -> SwitchMappingResult:
        """Map a Java switch to JavaScript format.
        
        Args:
            java_switch: The Java switch to map
            
        Returns:
            SwitchMappingResult with mapped JavaScript
        """
        result = SwitchMappingResult(
            success=False,
            source_switch=java_switch
        )
        
        if not java_switch.cases:
            result.errors.append("Switch has no cases")
            return result
        
        try:
            if self.style == ConversionStyle.SWITCH_STATEMENT:
                mapped_code = self._map_to_switch_statement(java_switch)
            elif self.style == ConversionStyle.IF_CHAIN:
                mapped_code = self._map_to_if_chain(java_switch)
            elif self.style == ConversionStyle.OBJECT_LITERAL:
                mapped_code = self._map_to_object_literal(java_switch)
            elif self.style == ConversionStyle.TERNARY_CHAIN:
                mapped_code = self._map_to_ternary_chain(java_switch)
            else:
                result.errors.append(f"Unknown style: {self.style}")
                return result
            
            # Check for potential issues
            warnings = self._check_for_issues(java_switch, mapped_code)
            
            result.mapped_switch = MappedSwitch(
                original_expression=java_switch.expression,
                style=self.style,
                mapped_code=mapped_code,
                warnings=warnings
            )
            result.success = True
            result.warnings = warnings
            
        except Exception as e:
            result.errors.append(f"Mapping error: {str(e)}")
        
        return result
    
    def _map_to_switch_statement(self, java_switch: JavaSwitchExpression) -> str:
        """Map to native JavaScript switch statement."""
        lines = [f"switch ({java_switch.expression}) {{"]
        
        for case in java_switch.cases:
            for label in case.labels:
                if case.is_default:
                    lines.append("default:")
                else:
                    lines.append(f"case {label.replace('case ', '').replace(' =>', '')}:")
            
            # Add body with proper indentation
            if case.body:
                for body_line in case.body.split('\n'):
                    if body_line.strip():
                        lines.append(f"    {body_line}")
            
            # Handle fall-through warning
            if case.falls_through and not case.is_arrow_style:
                lines.append("    // Fall-through")
        
        lines.append("}")
        return '\n'.join(lines)
    
    def _map_to_if_chain(self, java_switch: JavaSwitchExpression) -> str:
        """Map to if-else if chain."""
        lines = []
        expr = java_switch.expression
        
        # Build condition for each case
        for i, case in enumerate(java_switch.cases):
            if case.is_default:
                # Default case becomes final else
                lines.append(f"else {{")
            else:
                # Build conditions from labels
                conditions = []
                for label in case.labels:
                    label_val = label.replace('case ', '').replace(':', '').replace(' =>', '').strip()
                    # Handle multiple values: case 1, 2, 3:
                    if ',' in label_val:
                        for val in label_val.split(','):
                            conditions.append(f"{expr} === {val.strip()}")
                    else:
                        conditions.append(f"{expr} === {label_val}")
                
                condition = " || ".join(conditions)
                
                if i == 0:
                    lines.append(f"if ({condition}) {{")
                else:
                    lines.append(f"else if ({condition}) {{")
            
            # Add body with proper indentation
            if case.body:
                for body_line in case.body.split('\n'):
                    if body_line.strip():
                        lines.append(f"    {body_line}")
            
            lines.append("}")
        
        return '\n'.join(lines)
    
    def _map_to_object_literal(self, java_switch: JavaSwitchExpression) -> str:
        """Map to object literal (best for String/enum switches)."""
        if not java_switch.switch_type in ['String', 'enum']:
            # Fall back to switch statement for non-String/enum types
            return self._map_to_switch_statement(java_switch)
        
        cases_dict = {}
        
        for case in java_switch.cases:
            if case.is_default:
                cases_dict['_default'] = case.body if case.body else "null"
            else:
                for label in case.labels:
                    label_val = label.replace('case ', '').replace(':', '').replace(' =>', '').strip()
                    # Handle multiple values
                    if ',' in label_val:
                        for val in label_val.split(','):
                            cases_dict[val.strip()] = case.body if case.body else "null"
                    else:
                        cases_dict[label_val] = case.body if case.body else "null"
        
        # Build object literal
        lines = ["({" if java_switch.is_expression else "const switchMap = {"]
        
        for key, value in cases_dict.items():
            if key == '_default':
                lines.append(f"    default: {value},")
            else:
                lines.append(f"    {key}: {value},")
        
        lines.append("})" if java_switch.is_expression else "};")
        
        # Add lookup
        if java_switch.is_expression:
            return f"const result = {''.join(lines)}\nswitchMap[{java_switch.expression}] || switchMap.default"
        
        return '\n'.join(lines)
    
    def _map_to_ternary_chain(self, java_switch: JavaSwitchExpression) -> str:
        """Map to ternary operator chain (use sparingly)."""
        # Only suitable for simple expressions
        if len(java_switch.cases) > 4:
            self._warnings.append("Ternary chain with >4 cases may be hard to read")
        
        parts = []
        
        for case in java_switch.cases:
            if case.is_default:
                parts.append(case.body if case.body else "null")
            else:
                for label in case.labels:
                    label_val = label.replace('case ', '').replace(':', '').replace(' =>', '').strip()
                    condition = f"{java_switch.expression} === {label_val}"
                    value = case.body if case.body else "null"
                    parts.append(f"{condition} ? {value}")
        
        if parts:
            # Default is last in ternary chain
            return " ? ".join(parts) + " : null"
        
        return "null"
    
    def _check_for_issues(self, java_switch: JavaSwitchExpression, mapped_code: str) -> List[str]:
        """Check for potential issues in the conversion."""
        warnings = []
        
        # Check for missing default case
        if not java_switch.has_default:
            warnings.append("Switch has no default case - consider adding one for safety")
        
        # Check for fall-through cases
        fall_through_count = sum(1 for c in java_switch.cases if c.falls_through)
        if fall_through_count > 0:
            warnings.append(f"Found {fall_through_count} potential fall-through case(s)")
        
        # Check for complex body
        for case in java_switch.cases:
            if case.body and len(case.body.split('\n')) > 10:
                warnings.append("Some cases have complex bodies - verify conversion")
                break
        
        return warnings
    
    def add_case_mapping(self, java_value: str, js_value: str) -> None:
        """Add custom mapping for specific case values."""
        self._custom_mappings[java_value] = js_value


def map_switch(
    java_switch: JavaSwitchExpression, 
    style: ConversionStyle = ConversionStyle.SWITCH_STATEMENT
) -> SwitchMappingResult:
    """Convenience function to map a Java switch to JavaScript.
    
    Args:
        java_switch: The Java switch to map
        style: Conversion style to use
        
    Returns:
        SwitchMappingResult with mapped JavaScript
    """
    mapper = SwitchMapper(style=style)
    return mapper.map_switch(java_switch)


def map_switches(
    java_switches: List[JavaSwitchExpression],
    style: ConversionStyle = ConversionStyle.SWITCH_STATEMENT
) -> List[SwitchMappingResult]:
    """Map multiple Java switches to JavaScript.
    
    Args:
        java_switches: List of Java switches to map
        style: Conversion style to use
        
    Returns:
        List of SwitchMappingResult
    """
    mapper = SwitchMapper(style=style)
    return [mapper.map_switch(s) for s in java_switches]
