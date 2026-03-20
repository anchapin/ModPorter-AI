"""Lambda to Function Mapper for Java to Bedrock Conversion.

This module maps Java lambda expressions to Bedrock-compatible JavaScript functions.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Callable
from enum import Enum

from .lambda_detector import (
    LambdaExpression, 
    LambdaParameter, 
    LambdaBody, 
    MethodReference,
    CapturedVariable
)


class FunctionStyle(Enum):
    """Output function style for lambda conversion."""
    ARROW = "arrow"           # (x) => x + 1
    FUNCTION = "function"     # function(x) { return x + 1; }
    BIND = "bind"             # someMethod.bind(this)


@dataclass
class ConversionResult:
    """Result of lambda to function conversion."""
    success: bool
    output: str
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class LambdaToFunctionMapper:
    """Maps Java lambda expressions to JavaScript functions."""
    
    # Reserved words that can't be used as parameter names
    JS_RESERVED = {
        'break', 'case', 'catch', 'continue', 'debugger', 'default',
        'delete', 'do', 'else', 'export', 'extends', 'finally', 'for',
        'function', 'if', 'import', 'in', 'instanceof', 'new', 'return',
        'super', 'switch', 'this', 'throw', 'try', 'typeof', 'var',
        'void', 'while', 'with', 'class', 'const', 'enum', 'let',
        'static', 'yield', 'await', 'null', 'true', 'false'
    }
    
    def __init__(self, style: FunctionStyle = FunctionStyle.ARROW):
        self.style = style
        self._counter = 0
        self._name_cache: Dict[str, str] = {}
    
    def reset(self):
        """Reset mapper state."""
        self._counter = 0
        self._name_cache = {}
    
    def map_lambda(self, lambda_expr: LambdaExpression) -> ConversionResult:
        """Convert a LambdaExpression to JavaScript function.
        
        Args:
            lambda_expr: LambdaExpression to convert
            
        Returns:
            ConversionResult with JavaScript output
        """
        warnings = []
        
        # Generate parameter list
        params = self._map_parameters(lambda_expr.parameters)
        
        # Generate body
        body = self._map_body(lambda_expr.body)
        
        # Check for captured variables
        if lambda_expr.captured_variables:
            warnings.append(
                f"Lambda captures {len(lambda_expr.captured_variables)} variables"
            )
        
        # Generate output based on style
        if self.style == FunctionStyle.ARROW:
            if lambda_expr.body.is_expression:
                output = f"({params}) => {body}"
            else:
                output = f"({params}) => {{\n{body}\n}}"
        elif self.style == FunctionStyle.FUNCTION:
            # Add return for expression lambdas
            if lambda_expr.body.is_expression:
                output = f"function({params}) {{\n  return {body};\n}}"
            else:
                output = f"function({params}) {{\n{body}\n}}"
        elif self.style == FunctionStyle.BIND:
            if lambda_expr.body.is_expression:
                output = f"function({params}) {{\n  return {body};\n}}.bind(this)"
            else:
                output = f"function({params}) {{\n{body}\n}}.bind(this)"
        else:
            output = f"({params}) => {body}"
        
        return ConversionResult(
            success=True,
            output=output,
            warnings=warnings
        )
    
    def map_method_reference(self, ref: MethodReference) -> ConversionResult:
        """Convert a MethodReference to JavaScript.
        
        Args:
            ref: MethodReference to convert
            
        Returns:
            ConversionResult with JavaScript output
        """
        warnings = []
        
        if ref.kind == 'constructor':
            # ArrayList::new -> () => new ArrayList()
            if ref.target_class:
                output = f"() => new {ref.target_class}()"
            else:
                output = "() => {}"
                warnings.append("Could not determine constructor class")
                
        elif ref.kind == 'static':
            # System.out::println -> x => console.log(x)
            if ref.target_class and ref.method_name:
                output = self._map_static_method(ref.target_class, ref.method_name)
            else:
                output = "() => {}"
                warnings.append("Could not determine static method")
                
        elif ref.kind == 'instance':
            # String::length -> s => s.length
            if ref.method_name:
                param = self._generate_param_name(ref.method_name)
                output = f"{param} => {param}.{ref.method_name}()"
            else:
                output = "() => {}"
                warnings.append("Could not determine instance method")
                
        elif ref.kind == 'super':
            # super::methodName -> super.methodName.bind(this)
            if ref.method_name:
                output = f"super.{ref.method_name}.bind(this)"
            else:
                output = "() => super()"
                warnings.append("Could not determine super method")
                
        else:
            output = "() => {}"
            warnings.append(f"Unknown method reference kind: {ref.kind}")
        
        return ConversionResult(
            success=True,
            output=output,
            warnings=warnings
        )
    
    def _map_parameters(self, params: List[LambdaParameter]) -> str:
        """Convert lambda parameters to JS parameter list."""
        if not params:
            return ''
        
        param_list = []
        for p in params:
            name = self._sanitize_name(p.name)
            param_list.append(name)
        
        return ', '.join(param_list)
    
    def _map_body(self, body: LambdaBody) -> str:
        """Convert lambda body to JS."""
        if body.is_expression:
            # Expression lambda
            expr = body.expression or ''
            return self._map_expression(expr)
        else:
            # Block lambda
            statements = []
            for stmt in body.statements:
                mapped = self._map_statement(stmt)
                statements.append(f"  {mapped};")
            
            # Add return if last statement looks like return
            if statements and not statements[-1].strip().startswith('return'):
                # Check if we need to add return for last expression
                pass
            
            return '\n'.join(statements)
    
    def _map_expression(self, expr: str) -> str:
        """Map a Java expression to JS."""
        # Handle common Java patterns that need conversion
        
        # Method calls: obj.method() stays the same
        # Static calls: Class.method() stays the same
        # InstanceOf: x instanceof Type -> x instanceof Type
        # Ternary: a ? b : c -> a ? b : c
        
        # Handle method chaining (common in streams)
        expr = self._convert_stream_chains(expr)
        
        return expr
    
    def _map_statement(self, stmt: str) -> str:
        """Map a Java statement to JS."""
        stmt = stmt.strip()
        
        # Handle return statement
        if stmt.startswith('return'):
            rest = stmt[6:].strip()
            # Remove trailing semicolon if present
            if rest.endswith(';'):
                rest = rest[:-1].strip()
            return f"return {rest}"
        
        # Handle other statements as-is
        return stmt
    
    def _convert_stream_chains(self, expr: str) -> str:
        """Convert Java stream chains to JS equivalents."""
        # Java streams use :: for method references
        # JS uses method calls directly
        expr = expr.replace('::', '.')
        
        return expr
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize a parameter name for JS."""
        # Check reserved words
        if name in self.JS_RESERVED:
            return f"_{name}"
        
        # Replace invalid characters
        sanitized = name.replace('-', '_').replace('.', '_')
        
        return sanitized
    
    def _generate_param_name(self, method_name: str) -> str:
        """Generate a parameter name for method reference conversion."""
        if method_name in self._name_cache:
            return self._name_cache[method_name]
        
        # Use generic short names for method reference parameters
        # Don't derive from method name - use simple generic names
        # This ensures String::length becomes s => s.length(), not length => length.length()
        generic_names = ['s', 'x', 'item', 'elem', 'val', 'obj']
        name = generic_names[len(self._name_cache) % len(generic_names)]
        
        # Ensure not reserved
        if name in self.JS_RESERVED:
            name = f"_{name}"
        
        self._name_cache[method_name] = name
        return name
    
    def _map_static_method(self, class_name: str, method_name: str) -> str:
        """Map Java static method to JS equivalent."""
        # Common Java static -> JS mappings
        static_mappings = {
            ('System.out', 'println'): 'console.log',
            ('System.out', 'print'): 'console.log',
            ('System.err', 'println'): 'console.error',
            ('Math', 'abs'): 'Math.abs',
            ('Math', 'max'): 'Math.max',
            ('Math', 'min'): 'Math.min',
            ('Math', 'sqrt'): 'Math.sqrt',
            ('Math', 'pow'): 'Math.pow',
            ('Math', 'random'): 'Math.random',
            ('Arrays', 'asList'): 'Array.from',
        }
        
        key = (class_name, method_name)
        if key in static_mappings:
            js_method = static_mappings[key]
            return f"x => {js_method}(x)"
        
        # Default: wrap in function
        param = self._generate_param_name(method_name)
        return f"{param} => {class_name}.{method_name}({param})"
    
    def map_lambda_list(self, lambdas: List[LambdaExpression]) -> List[ConversionResult]:
        """Convert multiple lambdas.
        
        Args:
            lambdas: List of LambdaExpressions to convert
            
        Returns:
            List of ConversionResults
        """
        self.reset()
        results = []
        
        for lam in lambdas:
            result = self.map_lambda(lam)
            results.append(result)
        
        return results
    
    def create_wrapper_function(self, name: str, 
                                lambdas: List[LambdaExpression],
                                context: Optional[str] = None) -> str:
        """Create a wrapper function containing all lambda conversions.
        
        Args:
            name: Name for the wrapper function
            lambdas: List of lambdas to include
            context: Optional context description
            
        Returns:
            Complete wrapper function as string
        """
        lines = [f"function {name}() {{"]
        
        if context:
            lines.append(f"  // Context: {context}")
        
        for i, lam in enumerate(lambdas):
            result = self.map_lambda(lam)
            lines.append(f"  // Lambda {i + 1} at line {lam.line_number}")
            lines.append(f"  {result.output},")
        
        lines.append("}")
        
        return '\n'.join(lines)


def map_lambda_to_js(lambda_expr: LambdaExpression, 
                     style: FunctionStyle = FunctionStyle.ARROW) -> str:
    """Convenience function to convert a single lambda.
    
    Args:
        lambda_expr: LambdaExpression to convert
        style: Output function style
        
    Returns:
        JavaScript function as string
    """
    mapper = LambdaToFunctionMapper(style)
    result = mapper.map_lambda(lambda_expr)
    return result.output


def map_method_reference_to_js(ref: MethodReference) -> str:
    """Convenience function to convert a method reference.
    
    Args:
        ref: MethodReference to convert
        
    Returns:
        JavaScript function as string
    """
    mapper = LambdaToFunctionMapper()
    result = mapper.map_method_reference(ref)
    return result.output
