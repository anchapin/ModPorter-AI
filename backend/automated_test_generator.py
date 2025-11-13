#!/usr/bin/env python3
"""
Automated Test Generator for ModPorter-AI
==========================================

This script provides comprehensive automated test generation capabilities:
1. AI-powered test generation using OpenAI/DeepSeek APIs
2. Coverage analysis and gap identification
3. Mutation testing with mutmut
4. Property-based testing with Hypothesis
5. Automated test template generation

Usage:
    python automated_test_generator.py --target src/services/your_service.py
    python automated_test_generator.py --coverage-analysis
    python automated_test_generator.py --mutation-test
    python automated_test_generator.py --auto-generate --target-coverage 80
"""

import ast
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import importlib.util
import inspect
from dataclasses import dataclass

# Try to import optional dependencies
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: OpenAI not available. Install with: pip install openai")

try:
    import mutmut
    MUTMUT_AVAILABLE = True
except ImportError:
    MUTMUT_AVAILABLE = False
    print("Warning: mutmut not available. Install with: pip install mutmut")

try:
    from hypothesis import given, strategies as st
    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False
    print("Warning: hypothesis not available. Install with: pip install hypothesis")


@dataclass
class TestGenerationResult:
    """Result of test generation operation"""
    success: bool
    test_file_path: Optional[str] = None
    coverage_before: Optional[float] = None
    coverage_after: Optional[float] = None
    generated_tests: int = 0
    error_message: Optional[str] = None
    suggestions: List[str] = None

    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []


class CoverageAnalyzer:
    """Analyzes code coverage and identifies gaps"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.coverage_json = project_root / "coverage.json"
        
    def get_current_coverage(self) -> Dict[str, Any]:
        """Load current coverage data"""
        if not self.coverage_json.exists():
            return {"totals": {"percent_covered": 0}, "files": {}}
            
        with open(self.coverage_json, 'r') as f:
            return json.load(f)
    
    def get_low_coverage_files(self, threshold: float = 50.0) -> List[Tuple[str, float]]:
        """Get files with coverage below threshold"""
        coverage_data = self.get_current_coverage()
        low_coverage = []
        
        for file_path, file_data in coverage_data["files"].items():
            coverage_percent = file_data["summary"]["percent_covered"]
            if coverage_percent < threshold:
                low_coverage.append((file_path, coverage_percent))
        
        return sorted(low_coverage, key=lambda x: x[1])
    
    def get_uncovered_lines(self, file_path: str) -> List[int]:
        """Get list of uncovered line numbers for a file"""
        coverage_data = self.get_current_coverage()
        if file_path not in coverage_data["files"]:
            return []
            
        missing_lines = coverage_data["files"][file_path]["summary"]["missing_lines"]
        return [int(line) for line in missing_lines.split(",") if line.strip()]


class AITestGenerator:
    """AI-powered test generation using OpenAI/DeepSeek APIs"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
        self.model = model
        self.client = None
        
        if self.api_key and OPENAI_AVAILABLE:
            self.client = OpenAI(api_key=self.api_key)
    
    def generate_test_for_function(self, source_code: str, function_name: str, context: str = "") -> Optional[str]:
        """Generate tests for a specific function"""
        if not self.client:
            return self._generate_template_test(source_code, function_name)
            
        prompt = f"""
Generate comprehensive pytest tests for this Python function:

```python
{source_code}
```

Context: {context}

Requirements:
1. Use pytest framework with proper fixtures
2. Test all happy paths, edge cases, and error conditions
3. Include parameterized tests where appropriate
4. Mock external dependencies using unittest.mock
5. Add type hints and docstrings
6. Target 80%+ code coverage
7. Include assertions for return values, exceptions, and side effects

Function to test: {function_name}

Generate only the test code, no explanations:
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"AI generation failed: {e}")
            return self._generate_template_test(source_code, function_name)
    
    def _generate_template_test(self, source_code: str, function_name: str) -> str:
        """Fallback template-based test generation"""
        return f'''
def test_{function_name}_basic():
    """Basic test for {function_name}"""
    # TODO: Implement test based on function behavior
    assert True  # Placeholder

def test_{function_name}_edge_cases():
    """Edge case tests for {function_name}"""
    # TODO: Add edge case testing
    assert True  # Placeholder
'''


class TemplateTestGenerator:
    """Template-based test generation for common patterns"""
    
    @staticmethod
    def generate_api_tests(route_info: Dict[str, Any]) -> str:
        """Generate API endpoint tests"""
        endpoint = route_info.get("endpoint", "")
        method = route_info.get("method", "GET")
        path_params = route_info.get("path_params", [])
        
        test_name = f"test_{method.lower()}_{endpoint.strip('/').replace('/', '_')}"
        
        return f'''
@pytest.mark.asyncio
async def {test_name}_success():
    """Test successful {method} {endpoint}"""
    # TODO: Implement test for successful response
    response = client.{method.lower()}("{endpoint}")
    assert response.status_code == 200

@pytest.mark.asyncio
async def {test_name}_not_found():
    """Test {method} {endpoint} with missing resource"""
    # TODO: Implement test for 404 response
    response = client.{method.lower()}("{endpoint}/99999")
    assert response.status_code == 404

@pytest.mark.asyncio
async def {test_name}_validation_error():
    """Test {method} {endpoint} with invalid data"""
    # TODO: Implement test for validation errors
    invalid_data = {{"invalid": "data"}}
    response = client.{method.lower()}("{endpoint}", json=invalid_data)
    assert response.status_code == 422
'''
    
    @staticmethod
    def generate_service_tests(service_info: Dict[str, Any]) -> str:
        """Generate service layer tests"""
        class_name = service_info.get("class_name", "Service")
        methods = service_info.get("methods", [])
        
        tests = []
        for method in methods:
            test_name = f"test_{class_name.lower()}_{method['name']}"
            tests.append(f'''
def {test_name}_basic():
    """Test {class_name}.{method['name']}"""
    # TODO: Setup mocks and test basic functionality
    # Mock external dependencies
    # Test return values
    assert True  # Placeholder
''')
        
        return "\n".join(tests)


class PropertyTestGenerator:
    """Generate property-based tests using Hypothesis"""
    
    @staticmethod
    def generate_property_tests(function_info: Dict[str, Any]) -> str:
        """Generate property-based tests"""
        if not HYPOTHESIS_AVAILABLE:
            return "# Hypothesis not available for property-based testing\n"
        
        func_name = function_info.get("name", "function")
        params = function_info.get("parameters", [])
        
        strategies = []
        for param in params:
            param_type = param.get("type", "str")
            if param_type == "int":
                strategies.append("st.integers(min_value=0, max_value=1000)")
            elif param_type == "str":
                strategies.append("st.text(min_size=1, max_size=10)")
            elif param_type == "float":
                strategies.append("st.floats(min_value=0.0, max_value=100.0)")
            else:
                strategies.append("st.just(None)")
        
        strategy_args = ", ".join([f"arg{i}" for i in range(len(strategies))])
        param_args = ", ".join([f"arg{i}" for i in range(len(strategies))])
        
        return f'''
@given({strategy_args})
def test_{func_name}_properties({param_args}):
    """Property-based test for {func_name}"""
    # TODO: Test properties that should always hold
    # Example: assert output >= 0 if function returns positive numbers
    # result = {func_name}({param_args})
    # assert isinstance(result, expected_type)
    pass
'''


class MutationTester:
    """Wrapper for mutmut mutation testing"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        if not MUTMUT_AVAILABLE:
            print("Warning: mutmut not available. Install with: pip install mutmut")
    
    def run_mutation_test(self, target_dir: str = "src") -> Dict[str, Any]:
        """Run mutation testing and return results"""
        if not MUTMUT_AVAILABLE:
            return {"error": "mutmut not available"}
        
        try:
            # Run mutmut
            result = subprocess.run(
                ["python", "-m", "mutmut", "run", "--paths-to-mutate", target_dir],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            # Get results
            result_process = subprocess.run(
                ["python", "-m", "mutmut", "results"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            return {
                "run_output": result.stdout,
                "results_output": result_process.stdout,
                "run_returncode": result.returncode,
                "results_returncode": result_process.returncode
            }
        except Exception as e:
            return {"error": str(e)}


class CodeAnalyzer:
    """Analyze Python source code to extract information for test generation"""
    
    @staticmethod
    def analyze_file(file_path: Path) -> Dict[str, Any]:
        """Analyze a Python file and extract test-relevant information"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            tree = ast.parse(source_code)
            
            analysis = {
                "file_path": str(file_path),
                "source_code": source_code,
                "imports": [],
                "classes": [],
                "functions": [],
                "decorators": [],
                "async_functions": [],
                "test_candidates": []
            }
            
            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        analysis["imports"].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        analysis["imports"].append(f"{module}.{alias.name}")
            
            # Extract classes and functions
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    class_info = {
                        "name": node.name,
                        "methods": [],
                        "bases": [base.id for base in node.bases if isinstance(base, ast.Name)],
                        "decorators": [decorator.id for decorator in node.decorator_list 
                                    if isinstance(decorator, ast.Name)]
                    }
                    
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_info = {
                                "name": item.name,
                                "args": [arg.arg for arg in item.args.args],
                                "decorators": [d.id for d in item.decorator_list if isinstance(d, ast.Name)],
                                "is_async": isinstance(item, ast.AsyncFunctionDef)
                            }
                            class_info["methods"].append(method_info)
                            
                            if item.name not in ["__init__", "__str__", "__repr__"]:
                                analysis["test_candidates"].append({
                                    "type": "method",
                                    "class": node.name,
                                    "name": item.name,
                                    "source": ast.get_source_segment(source_code, item)
                                })
                    
                    analysis["classes"].append(class_info)
                
                elif isinstance(node, ast.FunctionDef):
                    func_info = {
                        "name": node.name,
                        "args": [arg.arg for arg in node.args.args],
                        "decorators": [d.id for d in node.decorator_list if isinstance(d, ast.Name)],
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        "source": ast.get_source_segment(source_code, node)
                    }
                    analysis["functions"].append(func_info)
                    
                    if not node.name.startswith("_"):
                        analysis["test_candidates"].append({
                            "type": "function",
                            "name": node.name,
                            "source": func_info["source"]
                        })
            
            return analysis
            
        except Exception as e:
            return {"error": str(e), "file_path": str(file_path)}


class AutomatedTestGenerator:
    """Main orchestrator for automated test generation"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.coverage_analyzer = CoverageAnalyzer(project_root)
        self.ai_generator = AITestGenerator()
        self.template_generator = TemplateTestGenerator()
        self.property_generator = PropertyTestGenerator()
        self.mutation_tester = MutationTester(project_root)
        self.code_analyzer = CodeAnalyzer()
    
    def generate_tests_for_file(self, file_path: Path, strategy: str = "hybrid") -> TestGenerationResult:
        """Generate tests for a specific Python file"""
        try:
            # Analyze the file
            analysis = self.code_analyzer.analyze_file(file_path)
            if "error" in analysis:
                return TestGenerationResult(False, error_message=analysis["error"])
            
            # Get current coverage
            coverage_before = self._get_file_coverage(str(file_path))
            
            # Determine test file path
            test_dir = self.project_root / "tests"
            test_file_path = test_dir / f"test_{file_path.stem}.py"
            
            # Generate test content
            test_content = self._generate_test_content(analysis, strategy)
            
            # Write test file
            test_dir.mkdir(exist_ok=True)
            with open(test_file_path, 'w', encoding='utf-8') as f:
                f.write(test_content)
            
            # Run tests and get new coverage
            coverage_after = self._run_tests_and_get_coverage()
            generated_tests = self._count_generated_tests(test_content)
            
            suggestions = self._generate_suggestions(analysis, coverage_before, coverage_after)
            
            return TestGenerationResult(
                success=True,
                test_file_path=str(test_file_path),
                coverage_before=coverage_before,
                coverage_after=coverage_after,
                generated_tests=generated_tests,
                suggestions=suggestions
            )
            
        except Exception as e:
            return TestGenerationResult(False, error_message=str(e))
    
    def _generate_test_content(self, analysis: Dict[str, Any], strategy: str) -> str:
        """Generate test content based on analysis"""
        content = []
        
        # Add imports
        content.append('"""')
        content.append(f'Auto-generated tests for {Path(analysis["file_path"]).name}')
        content.append('Generated by automated_test_generator.py')
        content.append('"""')
        content.append('')
        
        # Standard imports
        imports = [
            "import pytest",
            "import asyncio",
            "from unittest.mock import Mock, patch, AsyncMock",
            "import sys",
            "import os",
        ]
        
        # Add project path
        project_rel_path = self.project_root.relative_to(Path.cwd())
        content.append(f'sys.path.insert(0, r"{self.project_root}")')
        content.append('')
        
        # Add analysis-specific imports
        for imp in analysis["imports"]:
            if not imp.startswith(("os.", "sys.", "json.", "asyncio")):
                content.append(f"try:")
                content.append(f"    from {imp} import *")
                content.append(f"except ImportError:")
                content.append(f"    pass  # Import may not be available in test environment")
        
        content.extend(imports)
        content.append('')
        
        # Add fixtures if needed
        if any(candidate.get("is_async", False) for candidate in analysis["test_candidates"]):
            content.append('@pytest.fixture')
            content.append('def event_loop():')
            content.append('    """Create an event loop for async tests"""')
            content.append('    loop = asyncio.new_event_loop()')
            content.append('    yield loop')
            content.append('    loop.close()')
            content.append('')
        
        # Generate tests for each candidate
        for i, candidate in enumerate(analysis["test_candidates"]):
            if strategy == "ai" and self.ai_generator.client:
                test_code = self.ai_generator.generate_test_for_function(
                    candidate["source"], candidate["name"]
                )
            elif strategy == "template":
                if candidate["type"] == "method":
                    test_code = self.template_generator.generate_service_tests({
                        "class_name": candidate["class"],
                        "methods": [{"name": candidate["name"]}]
                    })
                else:
                    test_code = self.template_generator.generate_service_tests({
                        "class_name": candidate["name"],
                        "methods": []
                    })
            else:  # hybrid
                # Use AI for complex functions, templates for simple ones
                test_code = self._generate_hybrid_test(candidate, analysis)
            
            if test_code:
                content.append(f'# Tests for {candidate["name"]}')
                content.append(test_code)
                content.append('')
        
        return "\n".join(content)
    
    def _generate_hybrid_test(self, candidate: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Generate test using hybrid approach"""
        if self.ai_generator.client and len(candidate.get("source", "").split('\n')) > 5:
            # Use AI for complex functions
            return self.ai_generator.generate_test_for_function(
                candidate["source"], candidate["name"]
            )
        else:
            # Use template for simple functions
            return f'''
@pytest.mark.asyncio
async def test_{candidate["name"]}_basic():
    """Basic test for {candidate["name"]}"""
    # TODO: Implement test based on function behavior
    # Setup test data
    # Call the function
    # Assert results
    assert True  # Remove this and implement proper test
'''
    
    def _get_file_coverage(self, file_path: str) -> float:
        """Get current coverage for a specific file"""
        coverage_data = self.coverage_analyzer.get_current_coverage()
        normalized_path = file_path.replace('\\', '/')
        
        for path, data in coverage_data["files"].items():
            if normalized_path in path or path in normalized_path:
                return data["summary"]["percent_covered"]
        
        return 0.0
    
    def _run_tests_and_get_coverage(self) -> float:
        """Run tests and return new coverage percentage"""
        try:
            # Run tests with coverage
            result = subprocess.run(
                ["python", "-m", "pytest", "--cov=src", "--cov-report=json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                # Reload coverage data
                coverage_data = self.coverage_analyzer.get_current_coverage()
                return coverage_data.get("totals", {}).get("percent_covered", 0.0)
            
        except Exception:
            pass
        
        return 0.0
    
    def _count_generated_tests(self, test_content: str) -> int:
        """Count the number of test functions generated"""
        test_functions = re.findall(r'def (test_[a-zA-Z_][a-zA-Z0-9_]*)', test_content)
        return len(test_functions)
    
    def _generate_suggestions(self, analysis: Dict[str, Any], before: float, after: float) -> List[str]:
        """Generate improvement suggestions"""
        suggestions = []
        
        if after < before + 10:  # Less than 10% improvement
            suggestions.append("Consider adding more comprehensive edge case testing")
            suggestions.append("Review the generated tests and add specific assertions")
        
        if len(analysis["test_candidates"]) > 10:
            suggestions.append("Consider splitting tests into multiple test classes")
        
        for candidate in analysis["test_candidates"]:
            if candidate.get("is_async", False):
                suggestions.append(f"Ensure {candidate['name']} has proper async test setup")
        
        if any("db" in imp.lower() or "database" in imp.lower() for imp in analysis["imports"]):
            suggestions.append("Consider adding database mocking for service tests")
        
        return suggestions


def main():
    parser = argparse.ArgumentParser(description="Automated Test Generator for ModPorter-AI")
    parser.add_argument("--target", "-t", help="Target file or directory for test generation")
    parser.add_argument("--coverage-analysis", "-c", action="store_true", help="Analyze current coverage")
    parser.add_argument("--mutation-test", "-m", action="store_true", help="Run mutation testing")
    parser.add_argument("--auto-generate", "-a", action="store_true", help="Auto-generate tests for low coverage files")
    parser.add_argument("--target-coverage", type=float, default=80.0, help="Target coverage percentage")
    parser.add_argument("--strategy", choices=["ai", "template", "hybrid"], default="hybrid", 
                       help="Test generation strategy")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    
    args = parser.parse_args()
    
    project_root = Path(args.project_root).resolve()
    generator = AutomatedTestGenerator(project_root)
    
    if args.coverage_analysis:
        print("=== Coverage Analysis ===")
        coverage_data = generator.coverage_analyzer.get_current_coverage()
        overall = coverage_data.get("totals", {}).get("percent_covered", 0)
        print(f"Overall coverage: {overall:.1f}%")
        
        low_coverage = generator.coverage_analyzer.get_low_coverage_files(args.target_coverage)
        print(f"\nFiles below {args.target_coverage}% coverage:")
        for file_path, coverage in low_coverage[:10]:
            print(f"  {file_path}: {coverage:.1f}%")
        
        if low_coverage:
            print(f"\nFound {len(low_coverage)} files needing test improvement")
        
        return
    
    if args.mutation_test:
        print("=== Mutation Testing ===")
        results = generator.mutation_tester.run_mutation_test()
        if "error" in results:
            print(f"Error: {results['error']}")
        else:
            print("Mutation testing results:")
            print(results.get("results_output", "No results available"))
        return
    
    if args.auto_generate:
        print("=== Auto-generating Tests ===")
        low_coverage = generator.coverage_analyzer.get_low_coverage_files(args.target_coverage)
        
        for file_path, current_coverage in low_coverage[:5]:  # Limit to top 5
            print(f"\nGenerating tests for {file_path} (current: {current_coverage:.1f}%)")
            
            # Convert to actual file path
            src_file = project_root / file_path
            if not src_file.exists():
                print(f"  File not found: {src_file}")
                continue
            
            result = generator.generate_tests_for_file(src_file, args.strategy)
            
            if result.success:
                print(f"  [+] Generated {result.generated_tests} tests")
                print(f"  [FILE] Test file: {result.test_file_path}")
                if result.coverage_after and result.coverage_before:
                    improvement = result.coverage_after - result.coverage_before
                    print(f"  [COV] Coverage improvement: +{improvement:.1f}%")
                
                if result.suggestions:
                    print("  [SUGGESTIONS]:")
                    for suggestion in result.suggestions:
                        print(f"    - {suggestion}")
            else:
                print(f"  ✗ Failed: {result.error_message}")
        
        return
    
    if args.target:
        print(f"=== Generating Tests for {args.target} ===")
        target_path = project_root / args.target
        
        if target_path.is_file():
            result = generator.generate_tests_for_file(target_path, args.strategy)
            print_result(result)
        elif target_path.is_dir():
            # Generate for all Python files in directory
            for py_file in target_path.glob("**/*.py"):
                if "test_" not in py_file.name:
                    print(f"\nProcessing {py_file}")
                    result = generator.generate_tests_for_file(py_file, args.strategy)
                    print_result(result)
        else:
            print(f"Target not found: {target_path}")
    else:
        parser.print_help()


def print_result(result: TestGenerationResult):
    """Print test generation result"""
    if result.success:
        print(f"  [+] Success! Generated {result.generated_tests} tests")
        print(f"  [FILE] Test file: {result.test_file_path}")
        if result.coverage_before is not None:
            print(f"  [COV] Coverage before: {result.coverage_before:.1f}%")
        if result.coverage_after is not None:
            print(f"  [COV] Coverage after: {result.coverage_after:.1f}%")
            if result.coverage_before:
                improvement = result.coverage_after - result.coverage_before
                print(f"  [+] Improvement: +{improvement:.1f}%")
        
        if result.suggestions:
            print("  [SUGGESTIONS]:")
            for suggestion in result.suggestions:
                print(f"    - {suggestion}")
    else:
        print(f"  [ERROR] Failed: {result.error_message}")


if __name__ == "__main__":
    main()
