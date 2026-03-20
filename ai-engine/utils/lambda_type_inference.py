"""Lambda Type Inference for Java to Bedrock Conversion.

This module provides type inference for lambda expressions by detecting
the target functional interface from usage context.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Set
from enum import Enum

from .lambda_detector import LambdaExpression, LambdaParameter, LambdaBody


class FunctionalInterface(Enum):
    """Common Java functional interfaces."""
    PREDICATE = "java.util.function.Predicate"
    FUNCTION = "java.util.function.Function"
    CONSUMER = "java.util.function.Consumer"
    SUPPLIER = "java.util.function.Supplier"
    BIPREDICATE = "java.util.function.BiPredicate"
    BIFUNCTION = "java.util.function.BiFunction"
    BICONSUMER = "java.util.function.BiConsumer"
    UNARY_OPERATOR = "java.util.function.UnaryOperator"
    BINARY_OPERATOR = "java.util.function.BinaryOperator"
    RUNNABLE = "java.lang.Runnable"
    CALLABLE = "java.util.concurrent.Callable"
    COMPARATOR = "java.util.Comparator"


@dataclass
class InferredType:
    """Represents an inferred type for a lambda parameter or return."""
    interface: FunctionalInterface
    parameter_types: List[Optional[str]]
    return_type: Optional[str]
    confidence: float  # 0.0 to 1.0
    
    def __repr__(self) -> str:
        params = ", ".join(str(p) for p in self.parameter_types)
        return f"InferredType({self.interface.value}, params=[{params}], return={self.return_type}, conf={self.confidence})"


class LambdaTypeInference:
    """Infers functional interface types from lambda context."""
    
    # Mapping of common method names to functional interfaces
    CONTEXT_TO_INTERFACE: Dict[str, FunctionalInterface] = {
        # Stream operations
        'filter': FunctionalInterface.PREDICATE,
        'map': FunctionalInterface.FUNCTION,
        'flatMap': FunctionalInterface.FUNCTION,
        'anyMatch': FunctionalInterface.PREDICATE,
        'allMatch': FunctionalInterface.PREDICATE,
        'noneMatch': FunctionalInterface.PREDICATE,
        'forEach': FunctionalInterface.CONSUMER,
        'sorted': FunctionalInterface.COMPARATOR,
        'reduce': FunctionalInterface.BINARY_OPERATOR,
        
        # Collection operations
        'removeIf': FunctionalInterface.PREDICATE,
        'replaceAll': FunctionalInterface.FUNCTION,
        'computeIfAbsent': FunctionalInterface.FUNCTION,
        'computeIfPresent': FunctionalInterface.FUNCTION,
        'merge': FunctionalInterface.BIFUNCTION,
        
        # General
        'andThen': FunctionalInterface.FUNCTION,
        'compose': FunctionalInterface.FUNCTION,
        'test': FunctionalInterface.PREDICATE,
        'accept': FunctionalInterface.CONSUMER,
        'get': FunctionalInterface.SUPPLIER,
        'apply': FunctionalInterface.FUNCTION,
    }
    
    # Parameter count to interface mapping
    PARAM_COUNT_MAP = {
        0: {FunctionalInterface.SUPPLIER, FunctionalInterface.RUNNABLE, FunctionalInterface.CALLABLE},
        1: {
            FunctionalInterface.PREDICATE, 
            FunctionalInterface.CONSUMER, 
            FunctionalInterface.FUNCTION,
            FunctionalInterface.UNARY_OPERATOR
        },
        2: {
            FunctionalInterface.BIPREDICATE,
            FunctionalInterface.BICONSUMER,
            FunctionalInterface.BIFUNCTION,
            FunctionalInterface.BINARY_OPERATOR,
            FunctionalInterface.COMPARATOR,
        },
    }
    
    def __init__(self):
        self._inference_cache: Dict[int, InferredType] = {}
    
    def infer(self, lambda_expr: LambdaExpression, 
              context: Optional[str] = None) -> InferredType:
        """Infer the functional interface type for a lambda.
        
        Args:
            lambda_expr: Lambda to infer type for
            context: Optional context string (e.g., "stream.filter")
            
        Returns:
            InferredType with inferred interface and parameter/return types
        """
        # Try context-based inference first
        if context:
            inferred = self._infer_from_context(lambda_expr, context)
            if inferred:
                return inferred
        
        # Fall back to structure-based inference
        return self._infer_from_structure(lambda_expr)
    
    def _infer_from_context(self, lambda_expr: LambdaExpression, 
                           context: str) -> Optional[InferredType]:
        """Infer type from context string."""
        # Parse context (e.g., "stream.filter")
        parts = context.split('.')
        
        if len(parts) >= 2:
            operation = parts[-1]
            
            if operation in self.CONTEXT_TO_INTERFACE:
                interface = self.CONTEXT_TO_INTERFACE[operation]
                return self._create_inferred_type(lambda_expr, interface)
        
        # Try to infer from full context
        full_context = context.lower()
        
        for op, interface in self.CONTEXT_TO_INTERFACE.items():
            if op in full_context:
                return self._create_inferred_type(lambda_expr, interface)
        
        return None
    
    def _infer_from_structure(self, lambda_expr: LambdaExpression) -> InferredType:
        """Infer type from lambda structure (parameter count, body)."""
        param_count = len(lambda_expr.parameters)
        
        # Get possible interfaces for this parameter count
        possible_interfaces = self.PARAM_COUNT_MAP.get(
            param_count, 
            {FunctionalInterface.FUNCTION}
        )
        
        # Analyze body to narrow down
        interface = self._select_interface_from_body(
            lambda_expr.body, 
            possible_interfaces
        )
        
        return self._create_inferred_type(lambda_expr, interface)
    
    def _select_interface_from_body(self, body: LambdaBody, 
                                    candidates: Set[FunctionalInterface]) -> FunctionalInterface:
        """Select the best interface based on body analysis."""
        # Check if body has return value or is void-like
        has_return = False
        return_type = None
        
        if body.is_expression:
            # Expression always produces a value
            has_return = True
            return_type = self._infer_expression_type(body.expression)
        else:
            # Block lambda - check last statement
            if body.statements:
                last_stmt = body.statements[-1]
                if last_stmt.strip().startswith('return'):
                    has_return = True
                # Check if it's void (no return, just action)
                void_keywords = {'System.out.print', 'setXxx', 'add', 'remove'}
                if any(kw in last_stmt for kw in void_keywords):
                    has_return = False
        
        # Select based on return analysis
        if not has_return:
            # Likely Consumer or BiConsumer
            if len(candidates) >= 2:
                if FunctionalInterface.CONSUMER in candidates:
                    return FunctionalInterface.CONSUMER
                return FunctionalInterface.BICONSUMER
        
        # Has return - select Function/Predicate/Supplier
        if return_type == 'boolean':
            if FunctionalInterface.PREDICATE in candidates:
                return FunctionalInterface.PREDICATE
            if FunctionalInterface.BIPREDICATE in candidates:
                return FunctionalInterface.BIPREDICATE
        
        if not has_return and (FunctionalInterface.SUPPLIER in candidates):
            return FunctionalInterface.SUPPLIER
        
        # Default to Function
        if param_count := 1:
            return FunctionalInterface.FUNCTION
        return FunctionalInterface.BIFUNCTION
    
    def _infer_expression_type(self, expr: str) -> Optional[str]:
        """Infer the type of an expression."""
        if not expr:
            return None
        
        expr = expr.strip()
        
        # Boolean expressions
        bool_ops = {'==', '!=', '>', '<', '>=', '<=', '&&', '||', '!', 
                   'equals', 'isEmpty', 'contains', 'startsWith', 'endsWith'}
        if any(op in expr for op in bool_ops):
            return 'boolean'
        
        # Arithmetic
        arithmetic_ops = {'+', '-', '*', '/', '%'}
        if any(op in expr for op in arithmetic_ops):
            # Check for String concatenation
            if '+' in expr and ('"' in expr or "'" in expr):
                return 'String'
            return 'Number'
        
        # Method calls that return specific types
        method_returns = {
            'length': 'int',
            'size': 'int', 
            'getName': 'String',
            'getValue': 'Object',
            'hashCode': 'int',
            'toString': 'String',
            'clone': 'Object',
        }
        
        for method, ret_type in method_returns.items():
            if f'.{method}(' in expr or f'.{method} ' in expr:
                return ret_type
        
        # Default
        return None
    
    def _create_inferred_type(self, lambda_expr: LambdaExpression,
                              interface: FunctionalInterface) -> InferredType:
        """Create InferredType from interface."""
        param_count = len(lambda_expr.parameters)
        
        # Determine parameter types based on interface
        if interface in (FunctionalInterface.PREDICATE, 
                        FunctionalInterface.CONSUMER,
                        FunctionalInterface.FUNCTION,
                        FunctionalInterface.UNARY_OPERATOR,
                        FunctionalInterface.RUNNABLE,
                        FunctionalInterface.CALLABLE):
            param_types = self._infer_param_types(
                lambda_expr.parameters, 
                param_count
            )
        else:
            param_types = self._infer_param_types(
                lambda_expr.parameters,
                param_count
            )
        
        # Determine return type based on interface
        return_type = self._get_return_type(interface)
        
        # Calculate confidence
        confidence = self._calculate_confidence(lambda_expr, interface)
        
        return InferredType(
            interface=interface,
            parameter_types=param_types,
            return_type=return_type,
            confidence=confidence
        )
    
    def _infer_param_types(self, params: List[LambdaParameter], 
                          count: int) -> List[Optional[str]]:
        """Infer parameter types from lambda parameters."""
        types = []
        
        for param in params:
            if param.type_hint:
                types.append(self._map_java_to_js_type(param.type_hint))
            else:
                types.append(None)  # Unknown, will be inferred
        
        return types
    
    def _map_java_to_js_type(self, java_type: str) -> str:
        """Map Java type to JavaScript type hint."""
        type_mapping = {
            'int': 'number',
            'long': 'number',
            'float': 'number',
            'double': 'number',
            'boolean': 'boolean',
            'char': 'string',
            'byte': 'number',
            'short': 'number',
            'String': 'string',
            'Object': 'any',
            'List': 'Array',
            'Map': 'Object',
            'Set': 'Set',
            'Collection': 'Array',
        }
        
        # Handle generic types
        if '<' in java_type:
            base = java_type[:java_type.index('<')]
            if base in type_mapping:
                return type_mapping[base]
        
        return type_mapping.get(java_type, 'any')
    
    def _get_return_type(self, interface: FunctionalInterface) -> Optional[str]:
        """Get return type for a functional interface."""
        return_type_map = {
            FunctionalInterface.PREDICATE: 'boolean',
            FunctionalInterface.FUNCTION: 'any',
            FunctionalInterface.CONSUMER: 'void',
            FunctionalInterface.SUPPLIER: 'any',
            FunctionalInterface.BIPREDICATE: 'boolean',
            FunctionalInterface.BIFUNCTION: 'any',
            FunctionalInterface.BICONSUMER: 'void',
            FunctionalInterface.UNARY_OPERATOR: 'any',
            FunctionalInterface.BINARY_OPERATOR: 'any',
            FunctionalInterface.RUNNABLE: 'void',
            FunctionalInterface.CALLABLE: 'any',
            FunctionalInterface.COMPARATOR: 'int',
        }
        
        return return_type_map.get(interface)
    
    def _calculate_confidence(self, lambda_expr: LambdaExpression,
                             interface: FunctionalInterface) -> float:
        """Calculate confidence score for inference."""
        confidence = 0.5  # Base confidence
        
        # Higher confidence if we have explicit type hints
        typed_params = sum(1 for p in lambda_expr.parameters if p.type_hint)
        if lambda_expr.parameters:
            confidence += 0.2 * (typed_params / len(lambda_expr.parameters))
        
        # Higher confidence if we have context
        if lambda_expr.parent_context:
            confidence += 0.2
        
        # Higher confidence if body is simple
        if lambda_expr.body.is_expression:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def infer_from_source(self, source_code: str) -> Dict[int, InferredType]:
        """Infer types for all lambdas in source.
        
        Args:
            source_code: Java source code
            
        Returns:
            Dictionary mapping lambda hash to InferredType
        """
        from .lambda_detector import LambdaDetector
        
        detector = LambdaDetector()
        lambdas = detector.detect_from_source(source_code)
        
        results = {}
        for lam in lambdas:
            inferred = self.infer(lam, lam.parent_context)
            results[id(lam)] = inferred
        
        return results


def infer_lambda_type(lambda_expr: LambdaExpression, 
                     context: Optional[str] = None) -> InferredType:
    """Convenience function to infer lambda type.
    
    Args:
        lambda_expr: Lambda to infer type for
        context: Optional context string
        
    Returns:
        InferredType with inferred interface
    """
    inferrer = LambdaTypeInference()
    return inferrer.infer(lambda_expr, context)
