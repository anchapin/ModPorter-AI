"""Lambda Expression Detector for Java to Bedrock Conversion.

This module provides functionality to detect and analyze lambda expressions
in Java source code AST.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Any
import re


@dataclass
class LambdaParameter:
    """Represents a parameter in a lambda expression."""
    name: str
    type_hint: Optional[str] = None
    is_final: bool = False
    
    def __repr__(self) -> str:
        if self.type_hint:
            return f"LambdaParameter({self.name}: {self.type_hint})"
        return f"LambdaParameter({self.name})"


@dataclass
class LambdaBody:
    """Represents the body of a lambda expression."""
    is_expression: bool  # True for expression lambdas, False for block lambdas
    expression: Optional[str] = None
    statements: List[str] = field(default_factory=list)
    
    def __repr__(self) -> str:
        if self.is_expression:
            return f"LambdaBody(expression={self.expression})"
        return f"LambdaBody(statements={self.statements})"


@dataclass
class CapturedVariable:
    """Represents a variable captured from the enclosing scope."""
    name: str
    declared_type: Optional[str] = None
    is_effectively_final: bool = True
    
    def __repr__(self) -> str:
        return f"CapturedVariable({self.name})"


@dataclass
class LambdaExpression:
    """Represents a complete lambda expression."""
    parameters: List[LambdaParameter]
    body: LambdaBody
    captured_variables: List[CapturedVariable] = field(default_factory=list)
    line_number: Optional[int] = None
    parent_context: Optional[str] = None  # e.g., "stream.filter", "button.addListener"
    
    def __repr__(self) -> str:
        param_str = ", ".join(p.name for p in self.parameters)
        return f"LambdaExpression(({param_str}) -> ...)"


@dataclass 
class MethodReference:
    """Represents a method reference."""
    kind: str  # 'instance', 'static', 'super', 'constructor', 'array_constructor'
    target_class: Optional[str] = None
    method_name: Optional[str] = None
    is_constructor: bool = False
    line_number: Optional[int] = None
    
    def __repr__(self) -> str:
        if self.is_constructor or self.kind == 'constructor':
            return f"MethodReference({self.target_class}::new)"
        return f"MethodReference({self.target_class}::{self.method_name})"


class LambdaDetector:
    """Detects and analyzes lambda expressions in Java AST."""
    
    # Common functional interface names
    FUNCTIONAL_INTERFACES = {
        'java.util.function.Predicate',
        'java.util.function.Function', 
        'java.util.function.Consumer',
        'java.util.function.Supplier',
        'java.util.function.BiPredicate',
        'java.util.function.BiFunction',
        'java.util.function.BiConsumer',
        'java.util.function.UnaryOperator',
        'java.util.function.BinaryOperator',
    }
    
    # Stream operation methods that commonly use lambdas
    STREAM_OPERATIONS = {
        'filter', 'map', 'flatMap', 'distinct', 'sorted',
        'forEach', 'collect', 'reduce', 'anyMatch', 'allMatch',
        'noneMatch', 'findFirst', 'findAny', 'count'
    }
    
    def __init__(self):
        self.lambdas: List[LambdaExpression] = []
        self.method_references: List[MethodReference] = []
        self._captured_vars: List[str] = []
        self._in_lambda_scope: bool = False
    
    def reset(self):
        """Reset detector state for new source."""
        self.lambdas = []
        self.method_references = []
        self._captured_vars = []
        self._in_lambda_scope = False
    
    def detect_from_source(self, source_code: str) -> List[LambdaExpression]:
        """Detect all lambda expressions in source code.
        
        Args:
            source_code: Java source code string
            
        Returns:
            List of detected LambdaExpression objects
        """
        self.reset()
        
        # Use regex-based detection as primary method
        self._detect_with_regex(source_code)
        
        # Also check for javalang-based AST if available
        try:
            self._detect_with_javalang(source_code)
        except Exception:
            pass  # Fall back to regex-only detection
            
        return self.lambdas
    
    def _detect_with_regex(self, source: str) -> None:
        """Detect lambdas using regex patterns."""
        lines = source.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Skip comments
            if '//' in line:
                line = line[:line.index('//')]
            
            # Detect method references first (:: syntax)
            self._detect_method_references_regex(line, i)
            
            # Lambda detection: Need to determine if params are parenthesized
            # Key: Check if there's a CLOSED parenthesis before the arrow
            # - "x -> x + 1" has no parens
            # - "(x) -> x + 1" has closed parens
            # - "filter(x -> x + 1)" has open paren from method call but NOT closed
            
            has_lambda_arrow = '->' in line
            if has_lambda_arrow:
                before_arrow = line.split('->')[0]
                
                # Find last ( and check if there's a matching ) before arrow
                last_open = before_arrow.rfind('(')
                last_close = before_arrow.rfind(')')
                
                if last_open > last_close:
                    # There's an unclosed ( before arrow - this is a simple lambda like "filter(x -> ..."
                    # But the actual lambda params don't have their own parens
                    simple_lambda = re.search(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*->\s*(.+)', line)
                    if simple_lambda:
                        params_str = simple_lambda.group(1)
                        body_str = simple_lambda.group(2)
                        
                        parameters = [LambdaParameter(name=params_str.strip())]
                        is_expression = not body_str.strip().startswith('{')
                        
                        if is_expression:
                            body = LambdaBody(is_expression=True, expression=body_str.strip())
                        else:
                            statements = self._extract_block_statements(body_str)
                            body = LambdaBody(is_expression=False, statements=statements)
                        
                        context = self._detect_context(lines, i - 1)
                        
                        lambda_expr = LambdaExpression(
                            parameters=parameters,
                            body=body,
                            captured_variables=[],
                            line_number=i,
                            parent_context=context
                        )
                        self.lambdas.append(lambda_expr)
                        continue
                elif last_open == -1:
                    # No parens at all before arrow - simple lambda
                    simple_lambda = re.search(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*->\s*(.+)', line)
                    if simple_lambda:
                        params_str = simple_lambda.group(1)
                        body_str = simple_lambda.group(2)
                        
                        parameters = [LambdaParameter(name=params_str.strip())]
                        is_expression = not body_str.strip().startswith('{')
                        
                        if is_expression:
                            body = LambdaBody(is_expression=True, expression=body_str.strip())
                        else:
                            statements = self._extract_block_statements(body_str)
                            body = LambdaBody(is_expression=False, statements=statements)
                        
                        context = self._detect_context(lines, i - 1)
                        
                        lambda_expr = LambdaExpression(
                            parameters=parameters,
                            body=body,
                            captured_variables=[],
                            line_number=i,
                            parent_context=context
                        )
                        self.lambdas.append(lambda_expr)
                        continue
            
            # Pattern for parenthesized parameters: (x, y) -> body
            # This handles: (x) -> ..., (x, y) -> ..., () -> ..., (String s) -> ...
            paren_lambda = re.search(r'\(([^)]*)\)\s*->\s*(.+)', line)
            if paren_lambda:
                params_str = paren_lambda.group(1).strip()
                body_str = paren_lambda.group(2)
                
                if params_str:
                    # Has parameters - split by comma for multi-param
                    # Check for typed parameters: "Type name" format
                    parameters = []
                    for p in params_str.split(','):
                        p = p.strip()
                        if not p:
                            continue
                        parts = p.split()
                        if len(parts) == 2:
                            # Typed param: "Type name"
                            type_hint = parts[0]
                            name = parts[1]
                            parameters.append(LambdaParameter(name=name, type_hint=type_hint))
                        else:
                            # Just name
                            parameters.append(LambdaParameter(name=p))
                else:
                    # No parameters: () -> body
                    parameters = []
                
                is_expression = not body_str.strip().startswith('{')
                
                if is_expression:
                    body = LambdaBody(is_expression=True, expression=body_str.strip())
                else:
                    statements = self._extract_block_statements(body_str)
                    body = LambdaBody(is_expression=False, statements=statements)
                
                context = self._detect_context(lines, i - 1)
                
                lambda_expr = LambdaExpression(
                    parameters=parameters,
                    body=body,
                    captured_variables=[],
                    line_number=i,
                    parent_context=context
                )
                self.lambdas.append(lambda_expr)
    
    def _detect_method_references_regex(self, line: str, line_number: int) -> None:
        """Detect method references using regex."""
        # Pattern: Class::method or object::method or Class::new
        # Instance: String::length
        # Static: System.out::println, Math::abs
        # Constructor: ArrayList::new
        
        # Find all :: occurrences
        ref_pattern = r'([A-Za-z_][A-Za-z0-9_.]*)::([A-Za-z_][A-Za-z0-9_]*)'
        matches = re.finditer(ref_pattern, line)
        
        for match in matches:
            target = match.group(1)
            method = match.group(2)
            
            # Determine kind
            if method == 'new':
                kind = 'constructor'
                is_constructor = True
            elif target in ('super', 'this'):
                kind = 'super' if target == 'super' else 'instance'
                is_constructor = False
            elif '.' in target:
                # Contains a dot - could be instance like System.out::println
                # System.out::println is an instance method
                # But Math.abs would be a static reference (though it has a dot)
                # For simplicity, treat anything with dot as potential instance
                kind = 'instance'
                is_constructor = False
            else:
                # Simple class name like String::length - instance method reference
                # This is calling an instance method on elements of that class type
                kind = 'instance'
                is_constructor = False
            
            # Special case: Math::xxx are static
            if target == 'Math':
                kind = 'static'
            
            ref = MethodReference(
                kind=kind,
                target_class=target,
                method_name=method,
                is_constructor=is_constructor,
                line_number=line_number
            )
            self.method_references.append(ref)
    
    def _detect_with_javalang(self, source: str) -> None:
        """Detect lambdas using javalang AST."""
        try:
            import javalang
        except ImportError:
            return
            
        tree = javalang.parse.parse(source)
        
        for path, node in tree:
            if isinstance(node, javalang.tree.LambdaExpression):
                self._process_javalang_lambda(node, path)
            elif isinstance(node, javalang.tree.MethodReference):
                self._process_javalang_method_ref(node)
    
    def _process_javalang_lambda(self, node, path: tuple) -> None:
        """Process a lambda node from javalang AST."""
        parameters = []
        if node.parameters:
            for param in node.parameters:
                param_type = getattr(param, 'type', None)
                type_hint = None
                if param_type:
                    type_hint = str(param_type)
                parameters.append(LambdaParameter(
                    name=param.name,
                    type_hint=type_hint,
                    is_final=getattr(param, 'final', False)
                ))
        
        # Determine body type
        body_node = node.body
        if body_node:
            is_expression = isinstance(body_node, (
                javalang.tree.BinaryOperation,
                javalang.tree.MethodInvocation,
                javalang.tree.ElementValue,
                javalang.tree.Literal,
            ))
            
            if is_expression:
                body = LambdaBody(is_expression=True, expression=str(body_node))
            else:
                # Extract statements from block
                statements = []
                if hasattr(body_node, 'statements'):
                    for stmt in body_node.statements:
                        statements.append(str(stmt))
                body = LambdaBody(is_expression=False, statements=statements)
        else:
            body = LambdaBody(is_expression=True, expression='')
        
        # Find line number
        line_number = getattr(node, 'position', None)
        if line_number:
            line_number = line_number.line
        
        lambda_expr = LambdaExpression(
            parameters=parameters,
            body=body,
            line_number=line_number,
            parent_context=self._infer_context_from_path(path)
        )
        self.lambdas.append(lambda_expr)
    
    def _process_javalang_method_ref(self, node) -> None:
        """Process a method reference from javalang AST."""
        kind = 'instance'
        target_class = None
        method_name = None
        is_constructor = False
        
        if hasattr(node, 'member'):
            method_name = node.member
        
        if hasattr(node, 'type'):
            target_class = str(node.type) if node.type else None
            
        if hasattr(node, 'object_type'):
            target_class = str(node.object_type)
            
        # Determine kind
        if target_class == 'super':
            kind = 'super'
        elif target_class == 'this':
            kind = 'instance'
        elif method_name == 'new':
            kind = 'constructor'
            is_constructor = True
        
        line_number = getattr(node, 'position', None)
        if line_number:
            line_number = line_number.line
            
        ref = MethodReference(
            kind=kind,
            target_class=target_class,
            method_name=method_name,
            is_constructor=is_constructor,
            line_number=line_number
        )
        self.method_references.append(ref)
    
    def _parse_parameters(self, params_str: str) -> List[LambdaParameter]:
        """Parse lambda parameter string into LambdaParameter objects."""
        if not params_str.strip():
            return []
        
        parameters = []
        
        # Handle no-param lambdas: () -> body
        if params_str.strip() == '()':
            return []
        
        # Split by comma, handling nested generics
        params = self._split_params(params_str)
        
        for param in params:
            param = param.strip()
            if not param:
                continue
            
            # Check for type annotation: Type name (Java style like "String s") or name: Type (TypeScript style)
            if ' ' in param:
                # Could be "Type name" or "name: Type"
                parts = param.split()
                if len(parts) == 2:
                    # Java style: Type name (e.g., "String s")
                    type_hint = parts[0].strip()
                    name = parts[1].strip()
                    parameters.append(LambdaParameter(
                        name=name,
                        type_hint=type_hint
                    ))
                elif len(parts) == 3 and parts[1] == ':':
                    # TypeScript style: name: Type
                    name = parts[0].strip()
                    type_hint = parts[2].strip()
                    parameters.append(LambdaParameter(
                        name=name,
                        type_hint=type_hint
                    ))
                else:
                    # Can't parse, treat as name
                    parameters.append(LambdaParameter(name=param))
            else:
                # Just name - infer type later
                parameters.append(LambdaParameter(name=param.strip()))
        
        return parameters
    
    def _split_params(self, params_str: str) -> List[str]:
        """Split parameters handling nested generics and brackets."""
        result = []
        current = ''
        depth = 0
        
        for char in params_str:
            if char in '(<[':
                depth += 1
                current += char
            elif char in ')>]':
                depth -= 1
                current += char
            elif char == ',' and depth == 0:
                result.append(current)
                current = ''
            else:
                current += char
        
        if current.strip():
            result.append(current)
        
        return result
    
    def _extract_block_statements(self, block_str: str) -> List[str]:
        """Extract statements from a block lambda body."""
        statements = []
        
        # Remove outer braces
        block_str = block_str.strip()
        if block_str.startswith('{') and block_str.endswith('}'):
            block_str = block_str[1:-1].strip()
        
        if not block_str:
            return statements
        
        # Simple statement extraction (handle basic cases)
        lines = block_str.split(';')
        for line in lines:
            line = line.strip()
            if line:
                statements.append(line)
        
        return statements
    
    def _detect_context(self, lines: List[str], line_idx: int) -> Optional[str]:
        """Detect the context where lambda is used."""
        # Look at surrounding lines for context clues
        context_lines = []
        start = max(0, line_idx - 2)
        end = min(len(lines), line_idx + 2)
        
        for i in range(start, end):
            if i != line_idx:
                context_lines.append(lines[i])
        
        context_text = ' '.join(context_lines).lower()
        
        # Check for stream operations
        for op in self.STREAM_OPERATIONS:
            if op in context_text:
                return f"stream.{op}"
        
        # Check for common lambda contexts
        if 'addactionlistener' in context_text:
            return 'button.addActionListener'
        elif 'foreach' in context_text:
            return 'collection.forEach'
        elif 'comparator' in context_text:
            return 'Comparator'
        
        return None
    
    def _detect_captured_variables(self, source: str, 
                                    parameters: List[LambdaParameter]) -> List[CapturedVariable]:
        """Detect variables captured from enclosing scope."""
        captured = []
        param_names = {p.name for p in parameters}
        
        # Simple heuristic: look for variable usage within lambda
        # In a full implementation, this would use AST analysis
        # For now, return empty list (captured vars detection requires deeper analysis)
        
        return captured
    
    def _infer_context_from_path(self, path: tuple) -> Optional[str]:
        """Infer context from AST path."""
        # Walk up the path to find method call context
        for node in reversed(path):
            if hasattr(node, 'member'):
                member = getattr(node, 'member', None)
                if member in self.STREAM_OPERATIONS:
                    return f"stream.{member}"
        return None
    
    def get_lambda_count(self) -> int:
        """Return total count of detected lambdas."""
        return len(self.lambdas)
    
    def get_method_reference_count(self) -> int:
        """Return total count of detected method references."""
        return len(self.method_references)
    
    def has_lambdas(self) -> bool:
        """Check if any lambdas were detected."""
        return len(self.lambdas) > 0


def detect_lambdas(source_code: str) -> List[LambdaExpression]:
    """Convenience function to detect lambdas in source code.
    
    Args:
        source_code: Java source code string
        
    Returns:
        List of detected LambdaExpression objects
    """
    detector = LambdaDetector()
    return detector.detect_from_source(source_code)


def detect_method_references(source_code: str) -> List[MethodReference]:
    """Convenience function to detect method references in source code.
    
    Args:
        source_code: Java source code string
        
    Returns:
        List of detected MethodReference objects
    """
    detector = LambdaDetector()
    detector.detect_from_source(source_code)
    return detector.method_references
