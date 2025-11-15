"""
Script to identify coverage gaps in the ModPorter AI project.

This script analyzes the codebase to identify files, functions, and classes
that lack test coverage or have insufficient coverage. It helps prioritize
testing efforts by focusing on the most critical and complex areas.
"""

import os
import sys
import ast
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
import json
import re

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class CoverageAnalyzer:
    """Analyzes code to identify coverage gaps."""

    def __init__(self, project_root: Path):
        """Initialize the analyzer."""
        self.project_root = project_root
        self.backend_dir = project_root / "backend" / "src"
        self.ai_engine_dir = project_root / "ai-engine" / "src"
        self.frontend_dir = project_root / "frontend" / "src"

    def analyze_directory(
        self,
        directory: Path,
        test_directory: Optional[Path] = None
    ) -> Dict:
        """
        Analyze a source directory to identify coverage gaps.

        Args:
            directory: Source code directory to analyze
            test_directory: Corresponding test directory (if exists)

        Returns:
            Dictionary with analysis results
        """
        if not directory.exists():
            return {"error": f"Directory {directory} does not exist"}

        # Find all Python files
        source_files = list(directory.rglob("*.py"))
        if not source_files:
            return {"error": f"No Python files found in {directory}"}

        # Parse source files to extract functions and classes
        source_analysis = self._parse_source_files(source_files)

        # If test directory is provided, analyze test files
        test_analysis = {}
        if test_directory and test_directory.exists():
            test_files = list(test_directory.rglob("test_*.py"))
            test_analysis = self._parse_test_files(test_files, directory)

        # Find coverage gaps
        coverage_gaps = self._find_coverage_gaps(source_analysis, test_analysis)

        # Calculate complexity metrics
        complexity_metrics = self._calculate_complexity(source_files)

        return {
            "directory": str(directory),
            "source_files": len(source_files),
            "source_analysis": source_analysis,
            "test_analysis": test_analysis,
            "coverage_gaps": coverage_gaps,
            "complexity_metrics": complexity_metrics
        }

    def _parse_source_files(self, files: List[Path]) -> Dict:
        """Parse Python source files to extract functions and classes."""
        analysis = {
            "files": {},
            "functions": defaultdict(list),
            "classes": defaultdict(list)
        }

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Parse the AST
                tree = ast.parse(content)

                file_key = str(file_path.relative_to(self.project_root))
                analysis["files"][file_key] = {
                    "functions": [],
                    "classes": [],
                    "imports": [],
                    "lines": len(content.splitlines())
                }

                # Extract functions, classes, and imports
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_name = node.name
                        analysis["files"][file_key]["functions"].append({
                            "name": func_name,
                            "line": node.lineno,
                            "is_test": func_name.startswith("test_")
                        })
                        if func_name not in analysis["functions"][file_key]:
                            analysis["functions"][file_key].append(func_name)

                    elif isinstance(node, ast.ClassDef):
                        class_name = node.name
                        analysis["files"][file_key]["classes"].append({
                            "name": class_name,
                            "line": node.lineno
                        })
                        if class_name not in analysis["classes"][file_key]:
                            analysis["classes"][file_key].append(class_name)

                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            analysis["files"][file_key]["imports"].append({
                                "name": alias.name,
                                "alias": alias.asname
                            })

                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ""
                        for alias in node.names:
                            analysis["files"][file_key]["imports"].append({
                                "name": f"{module}.{alias.name}",
                                "alias": alias.asname
                            })

            except Exception as e:
                file_key = str(file_path.relative_to(self.project_root))
                analysis["files"][file_key] = {
                    "error": str(e),
                    "functions": [],
                    "classes": [],
                    "imports": [],
                    "lines": 0
                }

        return analysis

    def _parse_test_files(self, test_files: List[Path], source_dir: Path) -> Dict:
        """Parse test files to identify what is being tested."""
        analysis = {
            "files": {},
            "tested_functions": defaultdict(set),
            "tested_classes": defaultdict(set),
            "imported_modules": defaultdict(set)
        }

        for test_file in test_files:
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Parse the AST
                tree = ast.parse(content)

                file_key = str(test_file.relative_to(self.project_root))
                analysis["files"][file_key] = {
                    "functions": [],
                    "imports": []
                }

                # Extract test functions and imports
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        if node.name.startswith("test_"):
                            analysis["files"][file_key]["functions"].append({
                                "name": node.name,
                                "line": node.lineno
                            })

                            # Try to infer what is being tested based on naming
                            self._infer_test_target(node.name, source_dir, analysis)

                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            analysis["files"][file_key]["imports"].append({
                                "name": alias.name,
                                "alias": alias.asname
                            })

                            # Track what modules are imported from src
                            if alias.name.startswith("src.") or alias.name in ["services", "api", "models"]:
                                module_parts = alias.name.split(".")
                                if len(module_parts) >= 2:
                                    module = module_parts[1]  # Get the module after src.
                                    analysis["imported_modules"][module].add(file_key)

                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ""
                        if module.startswith("src.") or module in ["services", "api", "models"]:
                            module_parts = module.split(".")
                            if len(module_parts) >= 1:
                                module_name = module_parts[0] if module_parts[0] != "src" else module_parts[1]
                                analysis["imported_modules"][module_name].add(file_key)

            except Exception as e:
                file_key = str(test_file.relative_to(self.project_root))
                analysis["files"][file_key] = {
                    "error": str(e),
                    "functions": [],
                    "imports": []
                }

        return analysis

    def _infer_test_target(
        self,
        test_name: str,
        source_dir: Path,
        analysis: Dict
    ):
        """Infer what module or function is being tested based on test name."""
        # Extract module and function name from test name
        # e.g., test_cache_service_set_job_status -> cache_service, set_job_status
        pattern = r"test_(\w+)(?:_?(\w+))?"
        match = re.match(pattern, test_name)

        if match:
            module_name = match.group(1)
            function_name = match.group(2)

            # Look for source files that might contain the tested module
            for file_path, file_info in analysis["source_analysis"]["files"].items():
                if module_name in file_path:
                    # Check if this function is defined in the file
                    if function_name:
                        for func in file_info["functions"]:
                            if function_name in func["name"]:
                                analysis["tested_functions"][file_path].add(function_name)

                    # If no specific function, assume the module is tested
                    analysis["tested_functions"][file_path].add("module_level")

    def _find_coverage_gaps(self, source_analysis: Dict, test_analysis: Dict) -> Dict:
        """Identify coverage gaps between source and test files."""
        gaps = {
            "untested_files": [],
            "untested_functions": defaultdict(list),
            "untested_classes": defaultdict(list),
            "partially_tested_files": []
        }

        for file_path, file_info in source_analysis["files"].items():
            # Check if this file is tested at all
            is_tested = file_path in test_analysis.get("tested_functions", {})

            if not is_tested:
                # Check if any tests import this file
                file_basename = os.path.splitext(os.path.basename(file_path))[0]
                is_imported = file_basename in test_analysis.get("imported_modules", {})
                if not is_imported:
                    gaps["untested_files"].append(file_path)
                else:
                    gaps["partially_tested_files"].append(file_path)

            # Check individual functions
            for func in file_info.get("functions", []):
                func_name = func["name"]
                tested_functions = test_analysis.get("tested_functions", {}).get(file_path, set())

                if func_name not in tested_functions and "module_level" not in tested_functions:
                    gaps["untested_functions"][file_path].append(func_name)

            # Check individual classes
            for cls in file_info.get("classes", []):
                class_name = cls["name"]
                tested_functions = test_analysis.get("tested_functions", {}).get(file_path, set())

                # For classes, we're checking if any test method references the class
                is_class_tested = False
                for test_func in tested_functions:
                    if class_name.lower() in test_func.lower():
                        is_class_tested = True
                        break

                if not is_class_tested and "module_level" not in tested_functions:
                    gaps["untested_classes"][file_path].append(class_name)

        return gaps

    def _calculate_complexity(self, files: List[Path]) -> Dict:
        """Calculate complexity metrics for source files."""
        complexity = {
            "file_complexity": {},
            "most_complex_files": [],
            "large_files": []
        }

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Simple complexity measure based on lines and code structure
                lines = content.splitlines()
                line_count = len(lines)
                code_lines = len([l for l in lines if l.strip() and not l.strip().startswith("#")])
                comment_lines = line_count - code_lines

                # Count AST nodes as a measure of complexity
                tree = ast.parse(content)
                node_count = len(list(ast.walk(tree)))
                class_count = len([n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)])
                func_count = len([n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)])

                complexity_score = (
                    code_lines * 0.1 +
                    node_count * 0.05 +
                    class_count * 2 +
                    func_count
                )

                file_key = str(file_path.relative_to(self.project_root))
                complexity["file_complexity"][file_key] = {
                    "line_count": line_count,
                    "code_lines": code_lines,
                    "comment_lines": comment_lines,
                    "node_count": node_count,
                    "class_count": class_count,
                    "func_count": func_count,
                    "complexity_score": complexity_score
                }

                # Track large files (> 300 lines)
                if line_count > 300:
                    complexity["large_files"].append((file_key, line_count))

                # Track complex files
                if complexity_score > 100:
                    complexity["most_complex_files"].append((file_key, complexity_score))

            except Exception:
                # Skip files that can't be parsed
                pass

        # Sort by complexity
        complexity["most_complex_files"].sort(key=lambda x: x[1], reverse=True)
        complexity["large_files"].sort(key=lambda x: x[1], reverse=True)

        return complexity

    def generate_prioritized_recommendations(self, analysis_results: Dict) -> List[Dict]:
        """Generate prioritized recommendations for improving test coverage."""
        recommendations = []

        # Priority 1: Critical untested API endpoints
        for dir_name, result in analysis_results.items():
            if dir_name == "backend" or dir_name == "ai-engine":
                coverage_gaps = result.get("coverage_gaps", {})
                untested_files = coverage_gaps.get("untested_files", [])

                for file_path in untested_files:
                    if "api" in file_path or "router" in file_path:
                        recommendations.append({
                            "priority": "high",
                            "type": "untested_api",
                            "file": file_path,
                            "service": dir_name,
                            "reason": "Critical API endpoint without tests",
                            "suggestion": f"Create test_{os.path.basename(file_path).replace('.py', '')}.py in the appropriate test directory"
                        })

        # Priority 2: Untested core service classes
        for dir_name, result in analysis_results.items():
            if dir_name == "backend" or dir_name == "ai-engine":
                coverage_gaps = result.get("coverage_gaps", {})
                untested_classes = coverage_gaps.get("untested_classes", {})

                for file_path, classes in untested_classes.items():
                    for class_name in classes:
                        if not class_name.startswith("Test") and "Base" not in class_name:
                            recommendations.append({
                                "priority": "high",
                                "type": "untested_class",
                                "file": file_path,
                                "class": class_name,
                                "service": dir_name,
                                "reason": f"Core service class {class_name} without tests",
                                "suggestion": f"Create unit tests for {class_name} in test_{os.path.basename(file_path).replace('.py', '')}.py"
                            })

        # Priority 3: Complex functions without tests
        for dir_name, result in analysis_results.items():
            if dir_name == "backend" or dir_name == "ai-engine":
                coverage_gaps = result.get("coverage_gaps", {})
                untested_functions = coverage_gaps.get("untested_functions", {})
                complexity = result.get("complexity_metrics", {})
                file_complexity = complexity.get("file_complexity", {})

                for file_path, functions in untested_functions.items():
                    for func_name in functions:
                        if not func_name.startswith("_") and not func_name.startswith("test"):
                            # Check if this file is complex
                            complexity_info = file_complexity.get(file_path, {})
                            complexity_score = complexity_info.get("complexity_score", 0)

                            if complexity_score > 50:
                                recommendations.append({
                                    "priority": "medium",
                                    "type": "untested_complex_function",
                                    "file": file_path,
                                    "function": func_name,
                                    "service": dir_name,
                                    "reason": f"Complex function {func_name} without tests",
                                    "suggestion": f"Create unit test for {func_name} with various input scenarios"
                                })

        # Priority 4: Large files with minimal coverage
        for dir_name, result in analysis_results.items():
            if dir_name == "backend" or dir_name == "ai-engine":
                complexity = result.get("complexity_metrics", {})
                large_files = complexity.get("large_files", [])
                partially_tested = result.get("coverage_gaps", {}).get("partially_tested_files", [])

                for file_path, line_count in large_files:
                    if file_path in partially_tested:
                        recommendations.append({
                            "priority": "medium",
                            "type": "partially_tested_large_file",
                            "file": file_path,
                            "line_count": line_count,
                            "service": dir_name,
                            "reason": f"Large file ({line_count} lines) with minimal test coverage",
                            "suggestion": f"Add comprehensive tests for {file_path}, focusing on critical paths"
                        })

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda x: priority_order.get(x["priority"], 3))

        return recommendations

    def save_analysis_report(
        self,
        analysis_results: Dict,
        output_file: str = "coverage_gaps_report.json"
    ):
        """Save the analysis results to a JSON file."""
        # Generate recommendations
        recommendations = self.generate_prioritized_recommendations(analysis_results)

        # Create comprehensive report
        report = {
            "timestamp": str(Path(__file__).stat().st_mtime),
            "analysis_results": analysis_results,
            "recommendations": recommendations,
            "summary": {
                "total_recommendations": len(recommendations),
                "high_priority": len([r for r in recommendations if r["priority"] == "high"]),
                "medium_priority": len([r for r in recommendations if r["priority"] == "medium"]),
                "low_priority": len([r for r in recommendations if r["priority"] == "low"])
            }
        }

        # Write report to file
        report_path = self.project_root / output_file
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        print(f"Coverage gaps report saved to: {report_path}")
        return report_path

    def print_summary(self, analysis_results: Dict):
        """Print a summary of the coverage gaps analysis."""
        print("\n" + "="*70)
        print("COVERAGE GAPS ANALYSIS SUMMARY")
        print("="*70)

        # Generate recommendations for summary
        recommendations = self.generate_prioritized_recommendations(analysis_results)

        print(f"\nTotal Recommendations: {len(recommendations)}")
        print(f"High Priority: {len([r for r in recommendations if r['priority'] == 'high'])}")
        print(f"Medium Priority: {len([r for r in recommendations if r['priority'] == 'medium'])}")
        print(f"Low Priority: {len([r for r in recommendations if r['priority'] == 'low'])}")

        print("\nTOP 10 HIGH PRIORITY RECOMMENDATIONS:")
        print("-"*70)
        high_priority = [r for r in recommendations if r["priority"] == "high"][:10]

        for i, rec in enumerate(high_priority, 1):
            print(f"\n{i}. {rec['type'].replace('_', ' ').title()}")
            print(f"   File: {rec['file']}")
            if 'class' in rec:
                print(f"   Class: {rec['class']}")
            if 'function' in rec:
                print(f"   Function: {rec['function']}")
            print(f"   Reason: {rec['reason']}")
            print(f"   Suggestion: {rec['suggestion']}")

        print("\n" + "="*70)


def main():
    """Main function to run the coverage gaps analysis."""
    parser = argparse.ArgumentParser(
        description="Analyze ModPorter AI codebase to identify test coverage gaps"
    )

    parser.add_argument(
        "--service",
        choices=["backend", "ai-engine", "frontend", "all"],
        default="all",
        help="Service to analyze"
    )

    parser.add_argument(
        "--output",
        default="coverage_gaps_report.json",
        help="Output file for the analysis report"
    )

    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Skip printing summary to console"
    )

    args = parser.parse_args()

    # Initialize analyzer
    analyzer = CoverageAnalyzer(project_root)

    # Determine which directories to analyze
    directories = []
    test_directories = []

    if args.service in ["backend", "all"]:
        directories.append(analyzer.backend_dir)
        test_directories.append(project_root / "backend" / "tests")

    if args.service in ["ai-engine", "all"]:
        directories.append(analyzer.ai_engine_dir)
        test_directories.append(project_root / "ai-engine" / "tests")

    if args.service in ["frontend", "all"]:
        directories.append(analyzer.frontend_dir)
        test_directories.append(project_root / "frontend" / "src" / "__tests__")

    # Analyze each directory
    analysis_results = {}

    for i, directory in enumerate(directories):
        service_name = directory.parent.name
        test_directory = test_directories[i] if i < len(test_directories) else None

        print(f"\nAnalyzing {service_name}...")
        result = analyzer.analyze_directory(directory, test_directory)
        analysis_results[service_name] = result

        if "error" in result:
            print(f"  Error: {result['error']}")
        else:
            print(f"  Found {result['source_files']} source files")
            coverage_gaps = result.get("coverage_gaps", {})
            print(f"  Untested files: {len(coverage_gaps.get('untested_files', []))}")
            print(f"  Partially tested files: {len(coverage_gaps.get('partially_tested_files', []))}")

    # Save analysis report
    report_path = analyzer.save_analysis_report(analysis_results, args.output)

    # Print summary if requested
    if not args.no_summary:
        analyzer.print_summary(analysis_results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
