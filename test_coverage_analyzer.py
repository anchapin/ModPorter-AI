#!/usr/bin/env python3
"""
Comprehensive Test Coverage Analyzer and Gap Detection Tool
Analyzes codebase and identifies test coverage gaps with prioritized recommendations
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class CoverageMetrics:
    """Metrics for a module's test coverage status"""
    file_path: str
    lines_of_code: int
    complexity: int
    has_tests: bool
    test_files: List[str]
    coverage_percentage: float
    priority_score: float
    business_critical: bool


class CoverageAnalyzer:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.metrics: List[CoverageMetrics] = []

    def analyze_directory(self, src_dir: str, test_dir: str) -> List[CoverageMetrics]:
        """Analyze source directory vs test directory"""
        src_path = self.project_root / src_dir
        test_path = self.project_root / test_dir

        if not src_path.exists():
            print(f"Warning: Source directory {src_path} not found")
            return []

        # Get all Python source files
        source_files = list(src_path.rglob("*.py"))
        source_files = [f for f in source_files if f.name != "__init__.py"]

        # Get all test files
        test_files = list(test_path.rglob("test*.py")) if test_path.exists() else []
        test_file_names = {f.name for f in test_files}

        # Map source files to their potential test files
        metrics = []
        for src_file in source_files:
            metrics.append(self._analyze_file(src_file, test_file_names, src_path, test_path))

        return metrics

    def _analyze_file(self, src_file: Path, test_files: Set[str],
                      src_base: Path, test_base: Path) -> CoverageMetrics:
        """Analyze individual source file for test coverage"""

        # Read and parse the source file
        try:
            with open(src_file, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)
            lines_of_code = len([line for line in content.split('\n') if line.strip()])
            complexity = self._calculate_complexity(tree)

        except Exception as e:
            print(f"Error parsing {src_file}: {e}")
            return CoverageMetrics(
                file_path=str(src_file),
                lines_of_code=0,
                complexity=0,
                has_tests=False,
                test_files=[],
                coverage_percentage=0.0,
                priority_score=0.0,
                business_critical=False
            )

        # Check for corresponding test files
        expected_test_names = [
            f"test_{src_file.name}",
            f"test_{src_file.stem}.py",
            src_file.name.replace('.py', '_test.py')
        ]

        found_tests = [name for name in expected_test_names if name in test_files]
        has_tests = len(found_tests) > 0

        # Determine if business critical
        business_critical = self._is_business_critical(src_file, content)

        # Calculate priority score
        priority_score = self._calculate_priority_score(
            lines_of_code, complexity, business_critical, not has_tests
        )

        # Estimate coverage (simplified)
        coverage_percentage = 70.0 if has_tests else 0.0
        if has_tests and "comprehensive" in str(found_tests):
            coverage_percentage = 90.0
        elif has_tests and lines_of_code < 500:
            coverage_percentage = 85.0

        return CoverageMetrics(
            file_path=str(src_file.relative_to(self.project_root)),
            lines_of_code=lines_of_code,
            complexity=complexity,
            has_tests=has_tests,
            test_files=found_tests,
            coverage_percentage=coverage_percentage,
            priority_score=priority_score,
            business_critical=business_critical
        )

    def _calculate_complexity(self, tree: ast.AST) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1  # Base complexity

        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                complexity += 1
            elif isinstance(node, ast.While):
                complexity += 1
            elif isinstance(node, ast.For):
                complexity += 1
            elif isinstance(node, ast.AsyncFor):
                complexity += 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            elif isinstance(node, ast.With):
                complexity += 1
            elif isinstance(node, ast.AsyncWith):
                complexity += 1
            elif isinstance(node, ast.And):
                complexity += 1
            elif isinstance(node, ast.Or):
                complexity += 1
            elif isinstance(node, ast.ListComp):
                complexity += 1
            elif isinstance(node, ast.DictComp):
                complexity += 1
            elif isinstance(node, ast.Try):
                complexity += 1
            elif isinstance(node, ast.Finally):
                complexity += 1

        return complexity

    def _is_business_critical(self, file_path: Path, content: str) -> bool:
        """Determine if module is business critical based on patterns"""
        critical_patterns = [
            'conversion', 'payment', 'auth', 'security', 'database', 'api',
            'export', 'import', 'core', 'main', 'critical', 'essential'
        ]

        file_path_str = str(file_path).lower()
        content_lower = content.lower()

        # Check file path
        if any(pattern in file_path_str for pattern in critical_patterns):
            return True

        # Check content for critical keywords
        critical_keywords = ['class.*API', 'class.*Controller', 'class.*Service',
                           'def.*convert', 'def.*process', 'def.*handle']

        for keyword in critical_keywords:
            if any(keyword.lower() in line for line in content_lower.split('\n')):
                return True

        return False

    def _calculate_priority_score(self, loc: int, complexity: int,
                                business_critical: bool, missing_tests: bool) -> float:
        """Calculate priority score for test implementation"""
        score = 0.0

        # Lines of code factor
        score += min(loc / 1000, 1.0) * 30

        # Complexity factor
        score += min(complexity / 50, 1.0) * 25

        # Business critical factor
        if business_critical:
            score += 30

        # Missing tests factor
        if missing_tests:
            score += 15

        return min(score, 100.0)

    def generate_report(self, metrics: List[CoverageMetrics]) -> Dict:
        """Generate comprehensive coverage report"""
        total_files = len(metrics)
        files_with_tests = sum(1 for m in metrics if m.has_tests)
        total_loc = sum(m.lines_of_code for m in metrics)

        # Calculate overall coverage estimate
        covered_loc = sum(m.lines_of_code * (m.coverage_percentage / 100) for m in metrics)
        overall_coverage = (covered_loc / total_loc * 100) if total_loc > 0 else 0

        # Find high priority gaps
        critical_gaps = [m for m in metrics if not m.has_tests and m.business_critical]
        high_priority = [m for m in metrics if m.priority_score > 70]

        return {
            'summary': {
                'total_files': total_files,
                'files_with_tests': files_with_tests,
                'test_coverage_ratio': files_with_tests / total_files if total_files > 0 else 0,
                'total_lines_of_code': total_loc,
                'overall_coverage_estimate': overall_coverage
            },
            'critical_gaps': critical_gaps,
            'high_priority_items': high_priority,
            'recommendations': self._generate_recommendations(metrics)
        }

    def _generate_recommendations(self, metrics: List[CoverageMetrics]) -> List[Dict]:
        """Generate prioritized recommendations"""
        recommendations = []

        # Group by priority
        high_priority = sorted([m for m in metrics if m.priority_score > 80],
                             key=lambda x: x.priority_score, reverse=True)
        medium_priority = sorted([m for m in metrics if 50 < m.priority_score <= 80],
                               key=lambda x: x.priority_score, reverse=True)

        # Phase 1 recommendations (Critical business logic)
        phase1_files = high_priority[:10]
        if phase1_files:
            recommendations.append({
                'phase': 'Phase 1: Critical Business Logic',
                'target_coverage': '65%',
                'estimated_effort': '2 weeks',
                'files': [self._file_to_dict(m) for m in phase1_files],
                'description': 'Focus on high-impact business logic with no test coverage'
            })

        # Phase 2 recommendations (Infrastructure)
        phase2_files = high_priority[10:20] + medium_priority[:5]
        if phase2_files:
            recommendations.append({
                'phase': 'Phase 2: Infrastructure & Core Services',
                'target_coverage': '75%',
                'estimated_effort': '2 weeks',
                'files': [self._file_to_dict(m) for m in phase2_files],
                'description': 'Cover infrastructure components and core services'
            })

        # Phase 3 recommendations (AI Engine)
        ai_engine_files = [m for m in metrics if 'ai-engine' in m.file_path and m.priority_score > 40]
        ai_engine_files = sorted(ai_engine_files, key=lambda x: x.priority_score, reverse=True)[:15]
        if ai_engine_files:
            recommendations.append({
                'phase': 'Phase 3: AI Engine Components',
                'target_coverage': '80%',
                'estimated_effort': '2 weeks',
                'files': [self._file_to_dict(m) for m in ai_engine_files],
                'description': 'Comprehensive testing of AI/ML components'
            })

        return recommendations

    def _file_to_dict(self, metric: CoverageMetrics) -> Dict:
        """Convert metric to dictionary for reporting"""
        return {
            'file': metric.file_path,
            'lines': metric.lines_of_code,
            'complexity': metric.complexity,
            'priority_score': metric.priority_score,
            'business_critical': metric.business_critical,
            'estimated_test_effort': f"{max(1, metric.lines_of_code // 100)} days"
        }


def main():
    """Main execution function"""
    project_root = os.path.dirname(os.path.abspath(__file__))

    analyzer = CoverageAnalyzer(project_root)

    print("Analyzing Test Coverage Gaps...")
    print("=" * 50)

    # Analyze backend
    print("\nBackend Analysis:")
    backend_metrics = analyzer.analyze_directory("backend/src", "backend/tests")

    # Analyze AI Engine (if exists)
    print("\nAI Engine Analysis:")
    ai_engine_metrics = []
    if os.path.exists(os.path.join(project_root, "ai-engine")):
        ai_engine_metrics = analyzer.analyze_directory("ai-engine/src", "ai-engine/tests")

    # Combine all metrics
    all_metrics = backend_metrics + ai_engine_metrics

    # Generate report
    report = analyzer.generate_report(all_metrics)

    # Print summary
    summary = report['summary']
    print(f"\nCoverage Summary:")
    print(f"   Total Files: {summary['total_files']}")
    print(f"   Files with Tests: {summary['files_with_tests']}")
    print(f"   Test Coverage Ratio: {summary['test_coverage_ratio']:.1%}")
    print(f"   Total Lines of Code: {summary['total_lines_of_code']:,}")
    print(f"   Estimated Overall Coverage: {summary['overall_coverage_estimate']:.1f}%")

    # Print critical gaps
    critical_gaps = report['critical_gaps']
    if critical_gaps:
        print(f"\nCritical Gaps ({len(critical_gaps)} files):")
        for gap in critical_gaps[:5]:  # Show top 5
            print(f"   - {gap.file_path} ({gap.lines_of_code} lines, priority: {gap.priority_score:.0f})")

    # Print recommendations
    recommendations = report['recommendations']
    if recommendations:
        print(f"\nImplementation Plan:")
        for rec in recommendations:
            print(f"\n   {rec['phase']}")
            print(f"   Target: {rec['target_coverage']}")
            print(f"   Effort: {rec['estimated_effort']}")
            print(f"   Files: {len(rec['files'])}")
            print(f"   {rec['description']}")

    print(f"\nAnalysis Complete!")
    print(f"Goal: Reach 80% coverage across all modules")
    print(f"Estimated Timeline: 6-8 weeks")


if __name__ == "__main__":
    main()