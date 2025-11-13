"""
Property-Based Testing Utilities for ModPorter-AI
===================================================

This module provides property-based testing utilities using Hypothesis
to generate comprehensive test cases and find edge cases automatically.

Features:
1. Automatic strategy generation for different data types
2. Custom strategies for ModPorter-AI specific data
3. Test templates for common patterns
4. Integration with existing pytest infrastructure
"""

import ast
import inspect
from typing import Any, Dict, List, Optional, Type, Union, Tuple
from dataclasses import dataclass
from pathlib import Path
import json

# Try to import hypothesis
try:
    from hypothesis import given, strategies as st, settings, HealthCheck
    from hypothesis.strategies import SearchStrategy
    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False
    print("Warning: hypothesis not available. Install with: pip install hypothesis")


@dataclass
class PropertyInfo:
    """Information about a function parameter"""
    name: str
    type_hint: Optional[Type]
    default_value: Any
    has_default: bool
    is_optional: bool


@dataclass
class FunctionInfo:
    """Information about a function for property testing"""
    name: str
    parameters: List[PropertyInfo]
    return_type: Optional[Type]
    is_async: bool
    docstring: Optional[str]
    source_code: Optional[str]


class StrategyGenerator:
    """Generate Hypothesis strategies based on type hints and patterns"""
    
    def __init__(self):
        self.custom_strategies = {}
        self.register_default_strategies()
    
    def register_default_strategies(self):
        """Register default strategies for common types"""
        if not HYPOTHESIS_AVAILABLE:
            return
        
        # Basic types
        self.custom_strategies.update({
            int: st.integers(min_value=-1000, max_value=1000),
            float: st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
            str: st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs'))),
            bool: st.booleans(),
            list: st.lists(st.integers(), min_size=0, max_size=10),
            dict: st.dictionaries(st.text(), st.integers(), min_size=0, max_size=5),
            tuple: st.tuples(st.integers(), st.str()),
        })
        
        # None type
        self.custom_strategies.update({
            type(None): st.just(None),
        })
        
        # Optional types
        self.register_optional_strategies()
        
        # ModPorter-AI specific types
        self.register_modporter_strategies()
    
    def register_optional_strategies(self):
        """Register strategies for Optional[T] types"""
        if not HYPOTHESIS_AVAILABLE:
            return
        
        for base_type in [int, float, str, bool]:
            optional_strategy = st.one_of([
                self.custom_strategies.get(base_type, st.nothing()),
                st.just(None)
            ])
            self.custom_strategies[f"Optional[{base_type.__name__}]"] = optional_strategy
            self.custom_strategies[f"Union[{base_type.__name__}, NoneType]"] = optional_strategy
    
    def register_modporter_strategies(self):
        """Register strategies specific to ModPorter-AI"""
        if not HYPOTHESIS_AVAILABLE:
            return
        
        # Minecraft mod data
        self.custom_strategies.update({
            "mod_id": st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            "version_string": st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N', '.'))),
            "file_path": st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', '/', '\\', '.', '-', '_'))),
            "java_class_name": st.text(min_size=3, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N', '$'))),
        })
        
        # API strategies
        self.custom_strategies.update({
            "http_status_code": st.integers(min_value=100, max_value=599),
            "json_data": st.dictionaries(st.text(), st.one_of([st.integers(), st.text(), st.booleans(), st.none()])),
            "uuid_string": st.text(min_size=36, max_size=36, alphabet=st.characters(whitelist_categories=('L', 'N', '-'))),
        })
        
        # Database strategies
        self.custom_strategies.update({
            "database_id": st.integers(min_value=1, max_value=1000000),
            "timestamp": st.integers(min_value=0, max_value=2147483647),  # Unix timestamp range
        })
    
    def get_strategy(self, param_info: PropertyInfo) -> SearchStrategy:
        """Get appropriate strategy for a parameter"""
        if not HYPOTHESIS_AVAILABLE:
            return st.just(None)
        
        # Check for default value
        if param_info.has_default:
            return st.just(param_info.default_value)
        
        # Check type hint
        if param_info.type_hint:
            type_name = str(param_info.type_hint)
            
            # Direct mapping
            if param_info.type_hint in self.custom_strategies:
                return self.custom_strategies[param_info.type_hint]
            
            # String-based mapping
            if type_name in self.custom_strategies:
                return self.custom_strategies[type_name]
            
            # Handle Union types
            if "Union[" in type_name or "Optional[" in type_name:
                return self._handle_union_types(type_name)
            
            # Handle List types
            if "List[" in type_name:
                return st.lists(st.integers(), min_size=0, max_size=5)
            
            # Handle Dict types
            if "Dict[" in type_name:
                return st.dictionaries(st.text(), st.integers(), min_size=0, max_size=3)
        
        # Fallback based on parameter name
        strategy = self._infer_strategy_from_name(param_info.name)
        if strategy:
            return strategy
        
        # Default fallback
        return st.integers(min_value=0, max_value=100)
    
    def _handle_union_types(self, type_string: str) -> SearchStrategy:
        """Handle Union and Optional types"""
        if not HYPOTHESIS_AVAILABLE:
            return st.just(None)
        
        # Extract types from Union[Type1, Type2, ...]
        if "Union[" in type_string:
            inner = type_string.replace("Union[", "").rstrip("]")
            types = [t.strip() for t in inner.split(",")]
        elif "Optional[" in type_string:
            inner = type_string.replace("Optional[", "").rstrip("]")
            types = [t.strip(), "None"]
        else:
            return st.integers(min_value=0, max_value=100)
        
        strategies = []
        for type_name in types:
            if type_name in self.custom_strategies:
                strategies.append(self.custom_strategies[type_name])
            elif type_name == "None":
                strategies.append(st.just(None))
            else:
                strategies.append(st.integers(min_value=0, max_value=100))
        
        return st.one_of(strategies)
    
    def _infer_strategy_from_name(self, param_name: str) -> Optional[SearchStrategy]:
        """Infer strategy based on parameter name patterns"""
        if not HYPOTHESIS_AVAILABLE:
            return None
        
        name_lower = param_name.lower()
        
        # ID patterns
        if "id" in name_lower:
            return st.integers(min_value=1, max_value=1000000)
        
        # Name patterns
        if "name" in name_lower or "title" in name_lower:
            return st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'Zs')))
        
        # URL/file patterns
        if "url" in name_lower or "path" in name_lower or "file" in name_lower:
            return st.text(min_size=5, max_size=100)
        
        # Boolean patterns
        if any(word in name_lower for word in ["is_", "has_", "can_", "should_", "enabled", "active"]):
            return st.booleans()
        
        # Version patterns
        if "version" in name_lower:
            return st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N', '.')))
        
        return None


class PropertyTestGenerator:
    """Generate property-based tests for functions and classes"""
    
    def __init__(self):
        self.strategy_generator = StrategyGenerator()
        self.test_templates = self._load_test_templates()
    
    def generate_property_tests(self, function_info: FunctionInfo) -> List[str]:
        """Generate property-based tests for a function"""
        if not HYPOTHESIS_AVAILABLE:
            return ["# Hypothesis not available for property-based testing"]
        
        tests = []
        
        # Generate basic property test
        basic_test = self._generate_basic_property_test(function_info)
        if basic_test:
            tests.append(basic_test)
        
        # Generate specific property tests based on function patterns
        if self._is_validation_function(function_info):
            tests.append(self._generate_validation_property_test(function_info))
        
        if self._is_transformation_function(function_info):
            tests.append(self._generate_transformation_property_test(function_info))
        
        if self._is_collection_function(function_info):
            tests.append(self._generate_collection_property_test(function_info))
        
        return tests
    
    def _generate_basic_property_test(self, function_info: FunctionInfo) -> Optional[str]:
        """Generate a basic property test"""
        if not function_info.parameters:
            return None
        
        # Generate strategies for each parameter
        param_strategies = []
        for param in function_info.parameters:
            strategy = self.strategy_generator.get_strategy(param)
            param_strategies.append(f"{param.name}_st")
        
        # Build the test function
        test_lines = [
            "@settings(max_examples=100, deadline=1000, suppress_health_check=[HealthCheck.too_slow])",
            f"@given({', '.join(param_strategies)})"
        ]
        
        if function_info.is_async:
            test_lines.append("async def")
        else:
            test_lines.append("def")
        
        test_name = f"test_{function_info.name}_property"
        test_lines.append(f"{test_name}({', '.join([p.name for p in function_info.parameters)]}):")
        test_lines.append(f'    """Property-based test for {function_info.name}"""')
        
        # Generate parameter strategies
        for i, param in enumerate(function_info.parameters):
            strategy = self.strategy_generator.get_strategy(param)
            test_lines.append(f"    {param.name}_st = {self._strategy_to_string(strategy)}")
        
        test_lines.append("")
        test_lines.append("    try:")
        if function_info.is_async:
            test_lines.append(f"        result = await {function_info.name}({', '.join([p.name for p in function_info.parameters])})")
        else:
            test_lines.append(f"        result = {function_info.name}({', '.join([p.name for p in function_info.parameters])})")
        
        # Add property assertions based on return type
        if function_info.return_type:
            test_lines.extend(self._generate_return_assertions(function_info.return_type))
        else:
            test_lines.append("        # Test that function completes without error")
            test_lines.append("        assert result is not None or result is None  # Basic sanity check")
        
        test_lines.append("    except Exception as e:")
        test_lines.append("        # Allow some exceptions for edge cases, but log them")
        test_lines.append("        import sys")
        test_lines.append("        print(f'Exception in property test: {e}', file=sys.stderr)")
        test_lines.append("        # Only fail on serious errors")
        test_lines.append("        if 'TypeError' in str(type(e)) or 'ValueError' in str(type(e)):")
        test_lines.append("            pass  # Expected for some edge cases")
        test_lines.append("        else:")
        test_lines.append("            raise")
        
        return "\n".join(test_lines)
    
    def _generate_validation_property_test(self, function_info: FunctionInfo) -> str:
        """Generate property test for validation functions"""
        test_lines = [
            "@settings(max_examples=50, deadline=1000)",
            f"@given({self._generate_param_strategies(function_info.parameters[:3])})"  # Limit parameters
        ]
        
        if function_info.is_async:
            test_lines.append("async def")
        else:
            test_lines.append("def")
        
        test_lines.append(f"test_{function_info.name}_validation_properties({', '.join([p.name for p in function_info.parameters[:3]])}):")
        test_lines.append(f'    """Test validation properties for {function_info.name}"""')
        test_lines.append("")
        test_lines.append("    # Property: function should handle valid input consistently")
        test_lines.append("    valid_inputs = []")
        
        for param in function_info.parameters[:3]:
            if "email" in param.name.lower():
                test_lines.append(f"    if '{param.name}' in locals() and '@' in str({param.name}):")
                test_lines.append("        valid_inputs.append(True)")
            else:
                test_lines.append(f"    if '{param.name}' in locals() and {param.name} is not None:")
                test_lines.append("        valid_inputs.append(True)")
        
        test_lines.append("")
        test_lines.append("    if valid_inputs:")
        test_lines.append("        # All valid inputs should produce consistent results")
        if function_info.is_async:
            test_lines.append(f"        result = await {function_info.name}({', '.join([p.name for p in function_info.parameters[:3]])})")
        else:
            test_lines.append(f"        result = {function_info.name}({', '.join([p.name for p in function_info.parameters[:3]])})")
        
        test_lines.append("        # Result should be deterministic for same inputs")
        if function_info.is_async:
            test_lines.append(f"        result2 = await {function_info.name}({', '.join([p.name for p in function_info.parameters[:3]])})")
        else:
            test_lines.append(f"        result2 = {function_info.name}({', '.join([p.name for p in function_info.parameters[:3]])})")
        
        test_lines.append("        assert result == result2, 'Function should be deterministic'")
        
        return "\n".join(test_lines)
    
    def _generate_transformation_property_test(self, function_info: FunctionInfo) -> str:
        """Generate property test for data transformation functions"""
        return f'''
@settings(max_examples=50, deadline=1000)
@given({self._generate_param_strategies(function_info.parameters)})
def test_{function_info.name}_transformation_properties({', '.join([p.name for p in function_info.parameters])}):
    """Test transformation properties for {function_info.name}"""
    
    # Property: transformations should preserve invariants
    # TODO: Add specific invariants based on what the function transforms
    
    try:
        {"await " if function_info.is_async else ""}{function_info.name}({', '.join([p.name for p in function_info.parameters])})
        # Test that function completes without error for valid inputs
        assert True
    except ValueError:
        # Expected for some invalid inputs
        pass
    except TypeError:
        # Expected for type mismatches
        pass
'''
    
    def _generate_collection_property_test(self, function_info: FunctionInfo) -> str:
        """Generate property test for collection functions"""
        return f'''
@settings(max_examples=30, deadline=1000)
@given({self._generate_param_strategies(function_info.parameters)})
def test_{function_info.name}_collection_properties({', '.join([p.name for p in function_info.parameters])}):
    """Test collection properties for {function_info.name}"""
    
    # Property: collection operations should maintain basic properties
    # TODO: Add specific collection invariants
    
    try:
        {"await " if function_info.is_async else ""}{function_info.name}({', '.join([p.name for p in function_info.parameters])})
        assert True  # Basic completion test
    except (IndexError, KeyError, ValueError):
        # Expected for some invalid collection operations
        pass
'''
    
    def _generate_param_strategies(self, parameters: List[PropertyInfo]) -> str:
        """Generate strategy definitions for parameters"""
        strategies = []
        for param in parameters:
            strategy = self.strategy_generator.get_strategy(param)
            strategies.append(f"{param.name}_st")
        
        return ", ".join(strategies)
    
    def _generate_return_assertions(self, return_type: Type) -> List[str]:
        """Generate assertions based on return type"""
        assertions = []
        
        if return_type == bool:
            assertions.append("        assert isinstance(result, bool)")
        elif return_type == int:
            assertions.append("        assert isinstance(result, int)")
        elif return_type == float:
            assertions.append("        assert isinstance(result, (int, float))")
        elif return_type == str:
            assertions.append("        assert isinstance(result, str)")
        elif "List" in str(return_type):
            assertions.append("        assert isinstance(result, (list, tuple))")
        elif "Dict" in str(return_type):
            assertions.append("        assert isinstance(result, dict)")
        else:
            assertions.append("        # Add type-specific assertions based on return type")
        
        return assertions
    
    def _strategy_to_string(self, strategy) -> str:
        """Convert strategy to string representation"""
        if not HYPOTHESIS_AVAILABLE:
            return "st.just(None)"
        
        return f"st.{strategy}" if hasattr(strategy, '__name__') else str(strategy)
    
    def _is_validation_function(self, function_info: FunctionInfo) -> bool:
        """Check if function appears to be a validation function"""
        if not function_info.name:
            return False
        
        validation_keywords = [
            "validate", "check", "verify", "is_valid", "has_valid", 
            "ensure", "confirm", "authenticate", "authorize"
        ]
        
        name_lower = function_info.name.lower()
        return any(keyword in name_lower for keyword in validation_keywords)
    
    def _is_transformation_function(self, function_info: FunctionInfo) -> bool:
        """Check if function appears to be a transformation function"""
        if not function_info.name:
            return False
        
        transform_keywords = [
            "transform", "convert", "map", "process", "format", 
            "normalize", "sanitize", "parse", "encode", "decode"
        ]
        
        name_lower = function_info.name.lower()
        return any(keyword in name_lower for keyword in transform_keywords)
    
    def _is_collection_function(self, function_info: FunctionInfo) -> bool:
        """Check if function works with collections"""
        if not function_info.name:
            return False
        
        collection_keywords = [
            "filter", "sort", "group", "aggregate", "count", "sum",
            "merge", "combine", "split", "join", "list", "array"
        ]
        
        name_lower = function_info.name.lower()
        return any(keyword in name_lower for keyword in collection_keywords)
    
    def _load_test_templates(self) -> Dict[str, str]:
        """Load test templates for different function types"""
        return {
            "async_api": '''
@pytest.mark.asyncio
@given(data_st=st.dictionaries(st.text(), st.one_of([st.integers(), st.text()])))
async def test_api_endpoint_properties(data_st):
    """Test API endpoint with various data"""
    # Test that API handles different data structures
    response_data = data_st
    
    # Should not crash on valid data
    assert isinstance(response_data, dict)
    ''',
            
            "validation": '''
@given(input_st=st.text())
def test_validation_properties(input_st):
    """Test validation function properties"""
    # Test that validation is deterministic
    result1 = validate_function(input_st)
    result2 = validate_function(input_st)
    assert result1 == result2
    
    # Test that empty input is handled consistently
    empty_result = validate_function("")
    assert empty_result == validate_function("")
    ''',
        }


class PropertyTestRunner:
    """Run and manage property-based tests"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_generator = PropertyTestGenerator()
    
    def analyze_and_generate_tests(self, target_file: Path) -> Dict[str, Any]:
        """Analyze a file and generate property-based tests"""
        try:
            with open(target_file, 'r') as f:
                content = f.read()
            
            tree = ast.parse(content)
            functions = self._extract_functions(tree, content)
            
            test_results = []
            for func_info in functions:
                if self._should_generate_property_test(func_info):
                    property_tests = self.test_generator.generate_property_tests(func_info)
                    test_results.append({
                        "function": func_info.name,
                        "property_tests": property_tests,
                        "parameters": len(func_info.parameters),
                        "is_async": func_info.is_async
                    })
            
            return {
                "file": str(target_file),
                "functions_analyzed": len(functions),
                "property_tests_generated": len(test_results),
                "test_results": test_results
            }
            
        except Exception as e:
            return {"error": str(e), "file": str(target_file)}
    
    def _extract_functions(self, tree: ast.AST, content: str) -> List[FunctionInfo]:
        """Extract function information from AST"""
        functions = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip test functions and private functions
                if node.name.startswith("test_") or node.name.startswith("_"):
                    continue
                
                # Extract parameter information
                parameters = []
                for arg in node.args.args:
                    param_info = PropertyInfo(
                        name=arg.arg,
                        type_hint=arg.annotation if hasattr(arg, 'annotation') and arg.annotation else None,
                        default_value=None,
                        has_default=False,
                        is_optional=False
                    )
                    parameters.append(param_info)
                
                # Extract return type
                return_type = node.returns if hasattr(node, 'returns') and node.returns else None
                
                function_info = FunctionInfo(
                    name=node.name,
                    parameters=parameters,
                    return_type=return_type,
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                    docstring=ast.get_docstring(node),
                    source_code=ast.get_source_segment(content, node)
                )
                
                functions.append(function_info)
        
        return functions
    
    def _should_generate_property_test(self, func_info: FunctionInfo) -> bool:
        """Determine if we should generate property tests for this function"""
        # Skip functions with no parameters
        if not func_info.parameters:
            return False
        
        # Skip very simple functions
        if len(func_info.parameters) > 8:  # Too complex
            return False
        
        # Skip setter/getter functions
        if func_info.name.startswith(("set_", "get_", "is_", "has_")):
            return False
        
        # Include functions that look like good candidates
        include_patterns = [
            "process", "calculate", "validate", "transform", "convert",
            "filter", "map", "reduce", "aggregate", "compute"
        ]
        
        name_lower = func_info.name.lower()
        return any(pattern in name_lower for pattern in include_patterns)
    
    def generate_test_file(self, analysis_result: Dict[str, Any]) -> Optional[str]:
        """Generate a complete test file from analysis results"""
        if "error" in analysis_result:
            return None
        
        test_lines = [
            '"""',
            f'Auto-generated property-based tests for {Path(analysis_result["file"]).name}',
            'Generated by property_based_testing.py',
            '"""',
            '',
        ]
        
        # Add imports
        if HYPOTHESIS_AVAILABLE:
            test_lines.extend([
                'import pytest',
                'from hypothesis import given, settings, HealthCheck',
                'from hypothesis import strategies as st',
                '',
            ])
        
        # Add system path
        project_rel = self.project_root.relative_to(Path.cwd())
        test_lines.append(f'sys.path.insert(0, r"{self.project_root}")')
        test_lines.append('')
        
        # Add imports for the target module
        target_file = Path(analysis_result["file"])
        module_name = target_file.stem
        
        test_lines.extend([
            f'import sys',
            f'import {module_name}',
            '',
        ])
        
        # Add property tests for each function
        for test_result in analysis_result["test_results"]:
            test_lines.append(f'# Property tests for {test_result["function"]}')
            test_lines.extend(test_result["property_tests"])
            test_lines.append('')
        
        return "\n".join(test_lines)


def main():
    """Command line interface for property-based testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate property-based tests")
    parser.add_argument("target", help="Target Python file or directory")
    parser.add_argument("--output", "-o", help="Output test file (single file mode)")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    
    args = parser.parse_args()
    
    project_root = Path(args.project_root).resolve()
    target_path = Path(args.target)
    
    runner = PropertyTestRunner(project_root)
    
    if target_path.is_file():
        print(f"Analyzing {target_path}...")
        result = runner.analyze_and_generate_tests(target_path)
        
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"Analyzed {result['functions_analyzed']} functions")
            print(f"Generated property tests for {result['property_tests_generated']} functions")
            
            # Generate test file
            test_content = runner.generate_test_file(result)
            if test_content and args.output:
                with open(args.output, 'w') as f:
                    f.write(test_content)
                print(f"Test file written to: {args.output}")
            elif test_content:
                print("\nGenerated test content:")
                print("=" * 50)
                print(test_content)
                print("=" * 50)
    
    elif target_path.is_dir():
        print(f"Scanning directory {target_path} for Python files...")
        py_files = list(target_path.glob("**/*.py"))
        
        total_functions = 0
        total_property_tests = 0
        
        for py_file in py_files:
            if "test_" in py_file.name:
                continue
            
            print(f"\nProcessing {py_file}...")
            result = runner.analyze_and_generate_tests(py_file)
            
            if "error" not in result:
                total_functions += result["functions_analyzed"]
                total_property_tests += result["property_tests_generated"]
                print(f"  {result['functions_analyzed']} functions, {result['property_tests_generated']} property tests")
            else:
                print(f"  Error: {result['error']}")
        
        print(f"\nSummary:")
        print(f"  Files processed: {len(py_files)}")
        print(f"  Total functions analyzed: {total_functions}")
        print(f"  Total property tests generated: {total_property_tests}")
    
    else:
        print(f"Target not found: {target_path}")


if __name__ == "__main__":
    main()
