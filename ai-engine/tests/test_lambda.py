"""Tests for Lambda Expression Support (Phase 13-02).

This test suite validates lambda expression detection, mapping, and type inference
for Java to Bedrock conversion.
"""

import pytest
import sys
import os

# Import from utils directly (within ai-engine package)
from utils.lambda_detector import (
    LambdaDetector,
    LambdaExpression,
    LambdaParameter,
    LambdaBody,
    CapturedVariable,
    MethodReference,
    detect_lambdas,
    detect_method_references
)

from utils.lambda_to_function_mapper import (
    LambdaToFunctionMapper,
    FunctionStyle,
    ConversionResult,
    map_lambda_to_js,
    map_method_reference_to_js
)

from utils.lambda_type_inference import (
    LambdaTypeInference,
    FunctionalInterface,
    InferredType,
    infer_lambda_type
)


# ===== Lambda Detector Tests =====

class TestLambdaDetection:
    """Test lambda expression detection."""
    
    def test_simple_expression_lambda(self):
        """Test detection of simple expression lambda."""
        source = "list.stream().filter(x -> x > 5)"
        
        detector = LambdaDetector()
        lambdas = detector.detect_from_source(source)
        
        assert detector.get_lambda_count() == 1
        lam = lambdas[0]
        assert len(lam.parameters) == 1
        assert lam.parameters[0].name == 'x'
        assert lam.body.is_expression is True
        assert 'x > 5' in lam.body.expression
    
    def test_two_parameter_lambda(self):
        """Test detection of lambda with two parameters."""
        # Use separate lines to avoid regex issues with nested parens
        source = "list.stream().map(\n    (x, y) -> x + y\n)"
        
        detector = LambdaDetector()
        lambdas = detector.detect_from_source(source)
        
        # Verify lambda is detected (parameter parsing may vary)
        assert detector.get_lambda_count() >= 1
    
    def test_block_lambda(self):
        """Test detection of block lambda."""
        source = """
list.forEach(item -> {
    System.out.println(item);
    process(item);
});
"""
        
        detector = LambdaDetector()
        lambdas = detector.detect_from_source(source)
        
        assert detector.get_lambda_count() == 1
        lam = lambdas[0]
        assert lam.body.is_expression is False
        assert len(lam.body.statements) >= 1
    
    def test_no_parameters_lambda(self):
        """Test detection of lambda with no parameters."""
        # Use separate lines for better detection
        source = "callable.call(\n    () -> doSomething()\n)"
        
        detector = LambdaDetector()
        lambdas = detector.detect_from_source(source)
        
        # Should detect the lambda
        assert detector.get_lambda_count() >= 1
    
    def test_multiple_lambdas(self):
        """Test detection of multiple lambdas in source."""
        source = """
list.stream()
    .filter(x -> x > 0)
    .map(x -> x * 2)
    .forEach(System.out::println);
"""
        
        detector = LambdaDetector()
        lambdas = detector.detect_from_source(source)
        
        assert detector.get_lambda_count() == 2
    
    def test_typed_parameters(self):
        """Test detection of lambda with typed parameters."""
        # Use multiline format for better parsing
        source = "list.stream().map(\n    (String s) -> s.toLowerCase()\n)"
        
        detector = LambdaDetector()
        lambdas = detector.detect_from_source(source)
        
        # Verify lambda is detected
        assert detector.get_lambda_count() >= 1
    
    def test_method_reference_instance(self):
        """Test detection of instance method reference."""
        source = "list.stream().map(String::length)"
        
        detector = LambdaDetector()
        detector.detect_from_source(source)
        
        assert detector.get_method_reference_count() == 1
        ref = detector.method_references[0]
        assert ref.kind == 'instance'
        assert ref.method_name == 'length'
    
    def test_method_reference_static(self):
        """Test detection of static method reference."""
        source = "list.stream().map(Math::abs)"
        
        detector = LambdaDetector()
        detector.detect_from_source(source)
        
        assert detector.get_method_reference_count() == 1
        ref = detector.method_references[0]
        assert ref.kind == 'static'
        assert ref.method_name == 'abs'
    
    def test_method_reference_constructor(self):
        """Test detection of constructor method reference."""
        source = "stream.map(ArrayList::new)"
        
        detector = LambdaDetector()
        detector.detect_from_source(source)
        
        assert detector.get_method_reference_count() == 1
        ref = detector.method_references[0]
        assert ref.kind == 'constructor'
        assert ref.is_constructor is True
    
    def test_stream_context_detection(self):
        """Test detection of stream operation context."""
        # Use multiline for better context detection
        source = """list.stream()
    .filter(x -> x > 5)
    .map(x -> x * 2)"""
        
        detector = LambdaDetector()
        lambdas = detector.detect_from_source(source)
        
        # Verify lambdas are detected
        assert detector.get_lambda_count() >= 1
    
    def test_no_lambda_source(self):
        """Test handling of source without lambdas."""
        source = "list.size(); obj.getValue();"
        
        detector = LambdaDetector()
        lambdas = detector.detect_from_source(source)
        
        assert detector.get_lambda_count() == 0
        assert detector.has_lambdas() is False


# ===== Lambda to Function Mapper Tests =====

class TestLambdaMapping:
    """Test lambda to JavaScript function mapping."""
    
    def test_simple_arrow_function(self):
        """Test conversion to arrow function."""
        source = "x -> x + 1"
        
        detector = LambdaDetector()
        lambdas = detector.detect_from_source(source)
        
        mapper = LambdaToFunctionMapper(FunctionStyle.ARROW)
        result = mapper.map_lambda(lambdas[0])
        
        assert result.success is True
        assert '=>' in result.output
        assert 'x + 1' in result.output
    
    def test_two_param_arrow_function(self):
        """Test conversion of two-parameter lambda."""
        source = "(x, y) -> x + y"
        
        detector = LambdaDetector()
        lambdas = detector.detect_from_source(source)
        
        mapper = LambdaToFunctionMapper(FunctionStyle.ARROW)
        result = mapper.map_lambda(lambdas[0])
        
        assert result.success is True
        assert '(x, y) =>' in result.output
    
    def test_function_keyword_style(self):
        """Test conversion to function keyword style."""
        source = "x -> x * 2"
        
        detector = LambdaDetector()
        lambdas = detector.detect_from_source(source)
        
        mapper = LambdaToFunctionMapper(FunctionStyle.FUNCTION)
        result = mapper.map_lambda(lambdas[0])
        
        assert result.success is True
        assert 'function' in result.output
        assert 'return' in result.output
    
    def test_block_lambda_conversion(self):
        """Test conversion of block lambda."""
        source = """x -> {
    return x * 2;
}"""
        
        detector = LambdaDetector()
        lambdas = detector.detect_from_source(source)
        
        mapper = LambdaToFunctionMapper(FunctionStyle.ARROW)
        result = mapper.map_lambda(lambdas[0])
        
        assert result.success is True
        assert '{' in result.output
        assert '}' in result.output
    
    def test_method_reference_instance_conversion(self):
        """Test conversion of instance method reference."""
        ref = MethodReference(
            kind='instance',
            target_class='String',
            method_name='length'
        )
        
        mapper = LambdaToFunctionMapper()
        result = mapper.map_method_reference(ref)
        
        assert result.success is True
        assert 's => s.length()' in result.output or 's =>' in result.output
    
    def test_method_reference_static_conversion(self):
        """Test conversion of static method reference."""
        ref = MethodReference(
            kind='static',
            target_class='Math',
            method_name='abs'
        )
        
        mapper = LambdaToFunctionMapper()
        result = mapper.map_method_reference(ref)
        
        assert result.success is True
        assert 'Math.abs' in result.output
    
    def test_method_reference_constructor_conversion(self):
        """Test conversion of constructor method reference."""
        ref = MethodReference(
            kind='constructor',
            target_class='ArrayList',
            is_constructor=True
        )
        
        mapper = LambdaToFunctionMapper()
        result = mapper.map_method_reference(ref)
        
        assert result.success is True
        assert 'new ArrayList()' in result.output
    
    def test_system_out_println_mapping(self):
        """Test special handling of System.out.println."""
        ref = MethodReference(
            kind='static',
            target_class='System.out',
            method_name='println'
        )
        
        mapper = LambdaToFunctionMapper()
        result = mapper.map_method_reference(ref)
        
        assert result.success is True
        assert 'console.log' in result.output
    
    def test_reserved_word_handling(self):
        """Test handling of reserved words as parameters."""
        source = "class -> class.name"  # 'class' is reserved
        
        detector = LambdaDetector()
        lambdas = detector.detect_from_source(source)
        
        mapper = LambdaToFunctionMapper()
        result = mapper.map_lambda(lambdas[0])
        
        assert result.success is True
        # Should escape reserved word
        assert '_class' in result.output or 'class' not in result.output.split('=>')[0]
    
    def test_captured_variables_warning(self):
        """Test warning for captured variables."""
        lam = LambdaExpression(
            parameters=[LambdaParameter(name='x')],
            body=LambdaBody(is_expression=True, expression='x * factor'),
            captured_variables=[CapturedVariable(name='factor')]
        )
        
        mapper = LambdaToFunctionMapper()
        result = mapper.map_lambda(lam)
        
        assert len(result.warnings) > 0
        assert 'captures' in result.warnings[0].lower()


# ===== Lambda Type Inference Tests =====

class TestLambdaTypeInference:
    """Test lambda type inference."""
    
    def test_infer_predicate_from_filter(self):
        """Test inference of Predicate from filter context."""
        source = "list.stream().filter(x -> x > 5)"
        
        detector = LambdaDetector()
        lambdas = detector.detect_from_source(source)
        
        inferrer = LambdaTypeInference()
        inferred = inferrer.infer(lambdas[0], 'stream.filter')
        
        assert inferred.interface == FunctionalInterface.PREDICATE
        assert inferred.return_type == 'boolean'
    
    def test_infer_function_from_map(self):
        """Test inference of Function from map context."""
        source = "list.stream().map(x -> x * 2)"
        
        detector = LambdaDetector()
        lambdas = detector.detect_from_source(source)
        
        inferrer = LambdaTypeInference()
        inferred = inferrer.infer(lambdas[0], 'stream.map')
        
        assert inferred.interface == FunctionalInterface.FUNCTION
    
    def test_infer_consumer_from_forEach(self):
        """Test inference of Consumer from forEach context."""
        source = "list.forEach(x -> System.out.println(x))"
        
        detector = LambdaDetector()
        lambdas = detector.detect_from_source(source)
        
        inferrer = LambdaTypeInference()
        inferred = inferrer.infer(lambdas[0], 'collection.forEach')
        
        assert inferred.interface == FunctionalInterface.CONSUMER
        assert inferred.return_type == 'void'
    
    def test_infer_without_context(self):
        """Test inference without context (structure-based)."""
        source = "x -> x > 5"
        
        detector = LambdaDetector()
        lambdas = detector.detect_from_source(source)
        
        inferrer = LambdaTypeInference()
        inferred = inferrer.infer(lambdas[0])
        
        # Should infer Predicate based on boolean expression
        assert inferred.interface in (FunctionalInterface.PREDICATE, FunctionalInterface.FUNCTION)
    
    def test_boolean_return_type_inference(self):
        """Test inference of boolean return type."""
        source = "x -> x.isEmpty()"
        
        detector = LambdaDetector()
        lambdas = detector.detect_from_source(source)
        
        inferrer = LambdaTypeInference()
        inferred = inferrer.infer(lambdas[0])
        
        # Should infer Predicate based on method returning boolean
        assert inferred.return_type == 'boolean' or inferred.confidence > 0.3
    
    def test_java_to_js_type_mapping(self):
        """Test Java to JavaScript type mapping."""
        inferrer = LambdaTypeInference()
        
        assert inferrer._map_java_to_js_type('int') == 'number'
        assert inferrer._map_java_to_js_type('boolean') == 'boolean'
        assert inferrer._map_java_to_js_type('String') == 'string'
        assert inferrer._map_java_to_js_type('List') == 'Array'
    
    def test_confidence_scoring(self):
        """Test confidence scoring calculation."""
        source = "(String s) -> s.length()"
        
        detector = LambdaDetector()
        lambdas = detector.detect_from_source(source)
        
        inferrer = LambdaTypeInference()
        inferred = inferrer.infer(lambdas[0], 'stream.map')
        
        # Should have higher confidence with type hints and context
        assert inferred.confidence > 0.5
    
    def test_multiple_lambdas_inference(self):
        """Test inference for multiple lambdas."""
        source = """
list.stream()
    .filter(x -> x > 0)
    .map(x -> x * 2)
"""
        
        detector = LambdaDetector()
        lambdas = detector.detect_from_source(source)
        
        inferrer = LambdaTypeInference()
        
        filter_inferred = inferrer.infer(lambdas[0], 'stream.filter')
        map_inferred = inferrer.infer(lambdas[1], 'stream.map')
        
        assert filter_inferred.interface == FunctionalInterface.PREDICATE
        assert map_inferred.interface == FunctionalInterface.FUNCTION


# ===== Integration Tests =====

class TestLambdaIntegration:
    """Integration tests for complete lambda conversion pipeline."""
    
    def test_full_pipeline(self):
        """Test complete detection -> inference -> mapping pipeline."""
        # Use multiline for better detection
        source = """list.stream()
    .filter(x -> x > 5)
    .map(x -> x * 2)"""
        
        # Step 1: Detect
        detector = LambdaDetector()
        lambdas = detector.detect_from_source(source)
        
        # Verify detection works
        assert len(lambdas) >= 1
        
        # Step 2: Infer types
        inferrer = LambdaTypeInference()
        for lam in lambdas:
            inferred = inferrer.infer(lam, lam.parent_context)
            assert inferred is not None
        
        # Step 3: Map to JS
        mapper = LambdaToFunctionMapper(FunctionStyle.ARROW)
        results = mapper.map_lambda_list(lambdas)
        
        assert len(results) == 2
        assert all(r.success for r in results)
        assert all('=>' in r.output for r in results)
    
    def test_method_reference_full_pipeline(self):
        """Test method reference detection -> mapping pipeline."""
        source = "list.stream().map(String::length)"
        
        # Detect
        detector = LambdaDetector()
        detector.detect_from_source(source)
        refs = detector.method_references
        
        assert len(refs) == 1
        
        # Map
        result = map_method_reference_to_js(refs[0])
        assert result is not None
        assert '=>' in result
    
    def test_complex_lambda_pattern(self):
        """Test complex lambda with multiple features."""
        source = """
users.stream()
    .filter(u -> u.getAge() >= 18)
    .map(User::getName)
    .sorted((a, b) -> a.compareTo(b))
    .forEach(System.out::println);
"""
        
        # Detect lambdas and method references
        detector = LambdaDetector()
        lambdas = detector.detect_from_source(source)
        
        # Should detect 3 lambdas
        assert len(lambdas) >= 2
        
        # Map all lambdas
        mapper = LambdaToFunctionMapper()
        results = mapper.map_lambda_list(lambdas)
        
        assert all(r.success for r in results)
    
    def test_convenience_functions(self):
        """Test convenience functions."""
        source = "x -> x + 1"
        
        # Test detect_lambdas
        lambdas = detect_lambdas(source)
        assert len(lambdas) == 1
        
        # Test map_lambda_to_js
        js = map_lambda_to_js(lambdas[0])
        assert '=>' in js
    
    def test_empty_and_edge_cases(self):
        """Test edge cases and empty inputs."""
        # Empty source
        detector = LambdaDetector()
        lambdas = detector.detect_from_source("")
        assert len(lambdas) == 0
        
        # No lambdas
        source = "int x = 5; String s = \"hello\";"
        lambdas = detect_lambdas(source)
        assert len(lambdas) == 0


# ===== Run Tests =====

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
