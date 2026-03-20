"""Switch Detector for Java to Bedrock Conversion.

This module provides functionality to detect and analyze Java switch expressions
and statements in source code AST for conversion to JavaScript compatible format.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set
import re


@dataclass
class SwitchCase:
    """Represents a single case in a switch statement."""
    labels: List[str]  # Case labels (e.g., ["case 1:", "case 2:"])
    body: str  # Code body for this case
    is_default: bool = False
    is_arrow_style: bool = False  # Java 14+ arrow syntax
    falls_through: bool = False  # Missing break (intentional fall-through)
    
    def __repr__(self) -> str:
        labels = ", ".join(self.labels)
        return f"SwitchCase({labels}, default={self.is_default})"


@dataclass
class SwitchCaseGroup:
    """Group of cases with same body (Java 14+)."""
    labels: List[str]
    body: str
    is_default: bool = False
    
    def __repr__(self) -> str:
        return f"CaseGroup({len(self.labels)} labels)"


@dataclass
class JavaSwitchExpression:
    """Represents a complete Java switch expression/statement."""
    expression: str  # The variable being switched on
    cases: List[SwitchCase]
    is_expression: bool  # True for switch expressions (Java 14+), False for statements
    switch_type: str  # "int", "String", "enum", etc.
    line_number: Optional[int] = None
    has_yield: bool = False  # Java 13+ yield support
    scope: str = "block"  # "block" or "expression"
    
    def __repr__(self) -> str:
        return f"JavaSwitchExpression({self.expression}, {len(self.cases)} cases, expr={self.is_expression})"
    
    @property
    def has_default(self) -> bool:
        """Check if switch has a default case."""
        return any(case.is_default for case in self.cases)


class SwitchDetector:
    """Detects switch expressions and statements in Java code."""
    
    # Pattern for traditional switch statements
    SWITCH_PATTERN = re.compile(
        r'switch\s*\(\s*([^)]+)\s*\)\s*\{',
        re.MULTILINE | re.DOTALL
    )
    
    # Pattern for case labels
    CASE_PATTERN = re.compile(
        r'case\s+([^:]+):|default\s*:',
        re.MULTILINE
    )
    
    # Arrow-style case (Java 14+)
    ARROW_CASE_PATTERN = re.compile(
        r'case\s+([^=]+)\s*=>|default\s*=>',
        re.MULTILINE
    )
    
    # Pattern to detect switch expression (with yield or assignment)
    EXPRESSION_INDICATORS = [
        r'yield\s+',
        r'=\s*switch\s*\(',
        r'return\s+switch\s*\(',
    ]
    
    # Java types that can be used in switch
    VALID_SWITCH_TYPES = {'int', 'long', 'short', 'byte', 'char', 'String', 'enum'}
    
    def __init__(self):
        self._custom_type_mappings: Dict[str, str] = {}
    
    def detect_from_source(self, source: str) -> List[JavaSwitchExpression]:
        """Detect all switch expressions/statements in source code.
        
        Args:
            source: Java source code
            
        Returns:
            List of detected switch expressions/statements
        """
        switches = []
        
        # Find all switch blocks
        for match in self.SWITCH_PATTERN.finditer(source):
            switch_start = match.start()
            switch_expr = match.group(1).strip()
            
            # Find the closing brace
            brace_start = match.end()
            brace_count = 1
            i = brace_start
            
            while i < len(source) and brace_count > 0:
                if source[i] == '{':
                    brace_count += 1
                elif source[i] == '}':
                    brace_count -= 1
                i += 1
            
            switch_body = source[match.start():i]
            line_number = source[:match.start()].count('\n') + 1
            
            # Determine if it's a switch expression or statement
            is_expression = self._is_expression_switch(switch_body, source)
            
            # Determine switch type
            switch_type = self._infer_switch_type(switch_expr, switch_body)
            
            # Parse cases
            cases = self._parse_cases(switch_body)
            
            # Check for yield (Java 13+)
            has_yield = 'yield ' in switch_body
            
            switch = JavaSwitchExpression(
                expression=switch_expr,
                cases=cases,
                is_expression=is_expression,
                switch_type=switch_type,
                line_number=line_number,
                has_yield=has_yield
            )
            switches.append(switch)
        
        return switches
    
    def _is_expression_switch(self, switch_body: str, full_source: str) -> bool:
        """Determine if switch is an expression (returns value) vs statement."""
        # Check for yield (definitively an expression)
        if 'yield ' in switch_body:
            return True
        
        # Check for assignment before switch
        # Look for patterns like: Type var = switch (...)
        # Find the switch keyword position in the source
        switch_keyword_pos = full_source.find('switch', max(0, len(full_source) - len(switch_body) - 50))
        
        if switch_keyword_pos > 0:
            # Get context before the switch keyword
            context_before = full_source[max(0, switch_keyword_pos - 100):switch_keyword_pos]
            lines = context_before.strip().split('\n')
            if lines:
                last_line = lines[-1].strip()
                # Check if this looks like an assignment with switch
                if '=' in last_line:
                    # Expression switch: Type var = switch (...)
                    return True
        
        return False
    
    def _infer_switch_type(self, switch_expr: str, switch_body: str) -> str:
        """Infer the type of the switch expression."""
        expr = switch_expr.strip()
        
        # Check for enum type based on case labels (e.g., case RED:, case Color.RED:)
        # Look for uppercase case labels that might be enum constants
        # Must check switch_body, not source
        # This is the strongest indicator of an enum switch
        if re.search(r'case\s+[A-Z][A-Za-z_]+', switch_body):
            # If we have uppercase case labels, it's likely an enum
            return 'enum'
        
        # Check for enum type (common pattern: EnumClass.CONSTANT in expression)
        if '.' in expr:
            parts = expr.split('.')
            potential_enum = parts[0]
            # Also check for case labels with enum constants (e.g., case Color.RED:)
            if re.search(rf'case\s+{potential_enum}\.\w+', switch_body):
                return 'enum'
        
        # Check for String type declarations in nearby context
        # Look for: String var = switch (...)
        if 'String' in switch_body:
            return 'String'
        
        # Check for int type
        if 'int' in switch_body:
            return 'int'
        
        # Check for String
        if 'String' in expr or expr in ['name()', 'toString()']:
            return 'String'
        
        # Check for char
        if 'char' in expr or expr in ['charAt(', 'character']:
            return 'char'
        
        # Check for int types
        for int_type in ['int', 'long', 'short', 'byte']:
            if int_type in expr:
                return int_type
        
        # Default to String (most common in Bedrock)
        return 'String'
    
    def _parse_cases(self, switch_body: str) -> List[SwitchCase]:
        """Parse all cases from switch body."""
        cases = []
        
        # Remove outer braces and switch header
        body = switch_body.strip()
        
        # Remove the switch(...) { part if present
        if body.startswith('switch'):
            # Find the opening brace after switch
            brace_idx = body.find('{')
            if brace_idx != -1:
                body = body[brace_idx+1:]
        
        # Remove trailing whitespace, then closing brace(s) and semicolon
        body = body.strip()
        while body and (body.endswith('}') or body.endswith('};') or body.endswith(';')):
            if body.endswith('};'):
                body = body[:-2]
            elif body.endswith('}'):
                body = body[:-1]
            elif body.endswith(';'):
                body = body[:-1]
        
        # Split by cases
        lines = body.split('\n')
        current_case = None
        current_body_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines and the closing brace
            if not stripped or stripped == '}':
                continue
            
            # Check for arrow-style case (Java 14+)
            arrow_match = re.match(r'(case\s+[^=>]+|default)\s*->', stripped)
            if arrow_match:
                # Save previous case
                if current_case is not None:
                    current_case.body = '\n'.join(current_body_lines).strip()
                    cases.append(current_case)
                
                # Create new arrow-style case
                label = arrow_match.group(1)
                is_default = label == 'default'
                current_case = SwitchCase(
                    labels=[label + ' ->'],
                    body="",
                    is_default=is_default,
                    is_arrow_style=True
                )
                current_body_lines = [stripped[arrow_match.end():].strip()] if len(stripped) > arrow_match.end() else []
                continue
            
            # Check for traditional colon-style case
            colon_match = re.match(r'(case\s+[^:]+|default)\s*:', stripped)
            if colon_match:
                # Save previous case
                if current_case is not None:
                    current_case.body = '\n'.join(current_body_lines).strip()
                    cases.append(current_case)
                
                # Check for fall-through (previous case had no break/return/throw)
                falls_through = False
                if current_case and current_case.body:
                    last_stmt = current_case.body.strip().split('\n')[-1].strip()
                    falls_through = last_stmt not in ['break;', 'break', 'return;', 'return', 'throw', 'throw;', 'yield ']
                
                # Create new case
                label = colon_match.group(1)
                is_default = label == 'default'
                current_case = SwitchCase(
                    labels=[label + ':'],
                    body="",
                    is_default=is_default,
                    falls_through=falls_through
                )
                current_body_lines = []
                continue
            
            # Add line to current case body
            if current_case is not None:
                current_body_lines.append(line)
        
        # Add last case
        if current_case is not None:
            current_case.body = '\n'.join(current_body_lines).strip()
            cases.append(current_case)
        
        return cases
    
    def detect_switches(self, source: str) -> List[JavaSwitchExpression]:
        """Alias for detect_from_source for compatibility."""
        return self.detect_from_source(source)
    
    def has_switch(self, source: str) -> bool:
        """Check if source contains any switch expression/statement."""
        return 'switch (' in source or 'switch(' in source


def detect_switches(source: str) -> List[JavaSwitchExpression]:
    """Convenience function to detect switches in source code.
    
    Args:
        source: Java source code
        
    Returns:
        List of detected switch expressions/statements
    """
    detector = SwitchDetector()
    return detector.detect_from_source(source)


def is_switch_type(type_name: str) -> bool:
    """Check if a type is valid for switch statements.
    
    Args:
        type_name: The type name to check
        
    Returns:
        True if type is valid for switch
    """
    valid_types = {'int', 'long', 'short', 'byte', 'char', 'string', 'enum'}
    return type_name.lower() in valid_types
