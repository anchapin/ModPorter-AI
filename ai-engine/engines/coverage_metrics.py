"""
Test Coverage Metrics System

This module provides coverage tracking, quality scoring, and metrics
for the QA Suite (Phase 09).

Features:
- Coverage tracking by mod category and complexity
- Quality scoring with composite grades (A/B/C/D/F)
- Mod type metrics
- Trend analysis
- Benchmark suite
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict


@dataclass
class CoverageMetrics:
    """Coverage metrics for a conversion."""
    conversion_id: str
    mod_type: str
    complexity_level: str  # "simple", "moderate", "complex"
    java_coverage: float  # 0.0 - 1.0
    bedrock_coverage: float  # 0.0 - 1.0
    asset_coverage: float  # 0.0 - 1.0
    overall_coverage: float  # 0.0 - 1.0
    coverage_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityScore:
    """Quality score with breakdown."""
    conversion_id: str
    overall_score: float  # 0.0 - 1.0
    grade: str  # A, B, C, D, F
    breakdown: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class CoverageTracker:
    """Tracks coverage metrics for conversions."""
    
    def __init__(self, storage_path: str = "data/metrics"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.metrics: Dict[str, CoverageMetrics] = {}
        self._load_metrics()
    
    def _load_metrics(self):
        """Load metrics from storage."""
        index_file = self.storage_path / "coverage_index.json"
        if index_file.exists():
            with open(index_file, 'r') as f:
                data = json.load(f)
                for cid, mdata in data.items():
                    self.metrics[cid] = CoverageMetrics(**mdata)
    
    def _save_metrics(self):
        """Save metrics index."""
        index_file = self.storage_path / "coverage_index.json"
        data = {cid: {
            'conversion_id': m.conversion_id,
            'mod_type': m.mod_type,
            'complexity_level': m.complexity_level,
            'java_coverage': m.java_coverage,
            'bedrock_coverage': m.bedrock_coverage,
            'asset_coverage': m.asset_coverage,
            'overall_coverage': m.overall_coverage,
            'coverage_details': m.coverage_details
        } for cid, m in self.metrics.items()}
        with open(index_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _determine_complexity(self, java_code: str, bedrock_code: str) -> str:
        """Determine complexity level based on code."""
        total_lines = len(java_code.split('\n')) + len(bedrock_code.split('\n'))
        
        # Check for complex patterns
        import re
        complexity_indicators = len(re.findall(r'\b(if|else|for|while|switch|case|try|catch)\b', java_code))
        complexity_indicators += len(re.findall(r'\b(if|else|for|while|switch|case|try|catch)\b', bedrock_code))
        
        if total_lines < 50 and complexity_indicators < 5:
            return "simple"
        elif total_lines < 200 and complexity_indicators < 20:
            return "moderate"
        else:
            return "complex"
    
    def _calculate_java_coverage(self, java_code: str) -> float:
        """Calculate Java code coverage."""
        if not java_code:
            return 0.0
        
        lines = java_code.split('\n')
        code_lines = [l for l in lines if l.strip() and not l.strip().startswith('//')]
        
        # Simple coverage based on structure
        coverage = 0.0
        
        # Has class definition
        if 'class ' in java_code:
            coverage += 0.2
        
        # Has methods
        if 'void ' in java_code or 'public ' in java_code or 'private ' in java_code:
            coverage += 0.2
        
        # Has imports
        if 'import ' in java_code:
            coverage += 0.1
        
        # Has field declarations
        if 'private ' in java_code or 'public ' in java_code or 'protected ' in java_code:
            coverage += 0.1
        
        # Has comments
        if '//' in java_code or '/*' in java_code:
            coverage += 0.1
        
        # Has proper structure
        if '{' in java_code and '}' in java_code:
            coverage += 0.1
        
        # Code is non-trivial
        if len(code_lines) > 5:
            coverage += 0.2
        
        return min(coverage, 1.0)
    
    def _calculate_bedrock_coverage(self, bedrock_code: str) -> float:
        """Calculate Bedrock code coverage."""
        if not bedrock_code:
            return 0.0
        
        coverage = 0.0
        
        # Has functions
        if 'function' in bedrock_code:
            coverage += 0.2
        
        # Has proper structure
        if '{' in bedrock_code and '}' in bedrock_code:
            coverage += 0.2
        
        # Has comments
        if '//' in bedrock_code:
            coverage += 0.1
        
        # Has event handlers
        if 'event' in bedrock_code.lower() or 'trigger' in bedrock_code.lower():
            coverage += 0.1
        
        # Has variables
        if 'let ' in bedrock_code or 'const ' in bedrock_code or 'var ' in bedrock_code:
            coverage += 0.1
        
        # Has console logging
        if 'console.' in bedrock_code:
            coverage += 0.1
        
        # Code is non-trivial
        lines = [l for l in bedrock_code.split('\n') if l.strip() and not l.strip().startswith('//')]
        if len(lines) > 3:
            coverage += 0.2
        
        return min(coverage, 1.0)
    
    def _calculate_asset_coverage(self, assets: List[str]) -> float:
        """Calculate asset coverage."""
        if not assets:
            return 0.5  # Neutral if no assets
        
        # Check for expected asset types
        expected_types = {'textures', 'models', 'sounds', 'animations', 'particles'}
        found_types = set()
        
        for asset in assets:
            asset_lower = asset.lower()
            for exp_type in expected_types:
                if exp_type in asset_lower:
                    found_types.add(exp_type)
        
        # More types = better coverage
        return min(len(found_types) / 3.0, 1.0)
    
    def track_conversion(
        self,
        conversion_id: str,
        mod_type: str,
        java_code: str,
        bedrock_code: str,
        assets: Optional[List[str]] = None
    ) -> CoverageMetrics:
        """Track coverage metrics for a conversion."""
        
        complexity = self._determine_complexity(java_code, bedrock_code)
        java_coverage = self._calculate_java_coverage(java_code)
        bedrock_coverage = self._calculate_bedrock_coverage(bedrock_code)
        asset_coverage = self._calculate_asset_coverage(assets or [])
        
        # Calculate overall coverage
        overall_coverage = (
            java_coverage * 0.4 +
            bedrock_coverage * 0.4 +
            asset_coverage * 0.2
        )
        
        details = {
            'java_lines': len(java_code.split('\n')),
            'bedrock_lines': len(bedrock_code.split('\n')),
            'asset_count': len(assets or [])
        }
        
        metrics = CoverageMetrics(
            conversion_id=conversion_id,
            mod_type=mod_type,
            complexity_level=complexity,
            java_coverage=java_coverage,
            bedrock_coverage=bedrock_coverage,
            asset_coverage=asset_coverage,
            overall_coverage=overall_coverage,
            coverage_details=details
        )
        
        self.metrics[conversion_id] = metrics
        self._save_metrics()
        
        return metrics
    
    def get_coverage(self, conversion_id: str) -> Optional[CoverageMetrics]:
        """Get coverage metrics for a conversion."""
        return self.metrics.get(conversion_id)
    
    def get_coverage_by_type(self, mod_type: str) -> List[CoverageMetrics]:
        """Get all coverage metrics for a mod type."""
        return [m for m in self.metrics.values() if m.mod_type == mod_type]
    
    def get_average_coverage(self) -> float:
        """Get average coverage across all conversions."""
        if not self.metrics:
            return 0.0
        return sum(m.overall_coverage for m in self.metrics.values()) / len(self.metrics)


class QualityScorer:
    """Generates quality scores with composite grades."""
    
    def __init__(self):
        self.coverage_tracker = CoverageTracker()
        
        # Grade thresholds
        self.grade_thresholds = {
            'A': 0.90,
            'B': 0.75,
            'C': 0.60,
            'D': 0.40,
        }
    
    def _calculate_grade(self, score: float) -> str:
        """Calculate grade from score."""
        for grade, threshold in self.grade_thresholds.items():
            if score >= threshold:
                return grade
        return 'F'
    
    def calculate_quality_score(
        self,
        conversion_id: str,
        mod_type: str,
        java_code: str,
        bedrock_code: str,
        validation_score: float,
        assets: Optional[List[str]] = None
    ) -> QualityScore:
        """Calculate quality score for a conversion."""
        
        # Get or create coverage metrics
        coverage = self.coverage_tracker.track_conversion(
            conversion_id=conversion_id,
            mod_type=mod_type,
            java_code=java_code,
            bedrock_code=bedrock_code,
            assets=assets
        )
        
        # Calculate breakdown
        breakdown = {
            'validation_confidence': validation_score * 0.40,
            'java_coverage': coverage.java_coverage * 0.20,
            'bedrock_coverage': coverage.bedrock_coverage * 0.20,
            'asset_coverage': coverage.asset_coverage * 0.10,
            'structure_quality': self._calculate_structure_score(bedrock_code) * 0.10
        }
        
        overall_score = sum(breakdown.values())
        
        # Adjust for complexity
        if coverage.complexity_level == "simple":
            overall_score *= 1.1  # Bonus for simple
        elif coverage.complexity_level == "complex":
            overall_score *= 0.9  # Penalty for complex
        
        overall_score = min(overall_score, 1.0)
        
        grade = self._calculate_grade(overall_score)
        
        # Generate recommendations
        recommendations = []
        if breakdown['validation_confidence'] < 0.5:
            recommendations.append("Low validation confidence - review conversion quality")
        if breakdown['java_coverage'] < 0.5:
            recommendations.append("Low Java code coverage - some code may not be converted")
        if breakdown['bedrock_coverage'] < 0.5:
            recommendations.append("Low Bedrock code coverage - incomplete conversion")
        if breakdown['structure_quality'] < 0.5:
            recommendations.append("Structure quality issues detected")
        
        if not recommendations:
            recommendations.append("Quality looks good!")
        
        return QualityScore(
            conversion_id=conversion_id,
            overall_score=overall_score,
            grade=grade,
            breakdown=breakdown,
            recommendations=recommendations
        )
    
    def _calculate_structure_score(self, bedrock_code: str) -> float:
        """Calculate structural quality score."""
        if not bedrock_code:
            return 0.0
        
        score = 0.0
        
        # Proper braces
        if bedrock_code.count('{') == bedrock_code.count('}'):
            score += 0.3
        
        # Proper parentheses
        if bedrock_code.count('(') == bedrock_code.count(')'):
            score += 0.2
        
        # Has functions
        if 'function' in bedrock_code:
            score += 0.2
        
        # Has proper statements
        if ';' in bedrock_code or '{' in bedrock_code:
            score += 0.2
        
        # Has error handling
        if 'try' in bedrock_code or 'catch' in bedrock_code:
            score += 0.1
        
        return min(score, 1.0)


class TrendAnalyzer:
    """Analyzes trends in conversion quality over time."""
    
    def __init__(self):
        self.coverage_tracker = CoverageTracker()
    
    def analyze_trends(self, days: int = 30) -> Dict[str, Any]:
        """Analyze quality trends over time."""
        # For now, return aggregated data from coverage tracker
        all_metrics = list(self.coverage_tracker.metrics.values())
        
        if not all_metrics:
            return {
                'trend': 'insufficient_data',
                'message': 'Not enough data for trend analysis'
            }
        
        # Calculate average coverage by mod type
        by_type = defaultdict(list)
        for m in all_metrics:
            by_type[m.mod_type].append(m.overall_coverage)
        
        type_averages = {
            mod_type: sum(coverages) / len(coverages)
            for mod_type, coverages in by_type.items()
        }
        
        # Determine trend
        avg_coverage = self.coverage_tracker.get_average_coverage()
        
        if avg_coverage >= 0.8:
            trend = 'excellent'
        elif avg_coverage >= 0.6:
            trend = 'good'
        elif avg_coverage >= 0.4:
            trend = 'needs_improvement'
        else:
            trend = 'critical'
        
        return {
            'trend': trend,
            'average_coverage': avg_coverage,
            'coverage_by_type': type_averages,
            'total_conversions': len(all_metrics),
            'days_analyzed': days
        }


class BenchmarkSuite:
    """Benchmark suite for conversion quality testing."""
    
    def __init__(self):
        self.benchmarks: Dict[str, Dict[str, Any]] = {}
        self.results: List[Dict[str, Any]] = []
        self._load_benchmarks()
    
    def _load_benchmarks(self):
        """Load benchmark definitions."""
        # Define default benchmarks
        self.benchmarks = {
            'simple_item': {
                'mod_type': 'item',
                'complexity': 'simple',
                'expected_coverage': 0.7,
                'expected_quality': 0.7
            },
            'simple_block': {
                'mod_type': 'block',
                'complexity': 'simple',
                'expected_coverage': 0.7,
                'expected_quality': 0.7
            },
            'complex_entity': {
                'mod_type': 'entity',
                'complexity': 'complex',
                'expected_coverage': 0.6,
                'expected_quality': 0.6
            },
            'recipe': {
                'mod_type': 'recipe',
                'complexity': 'simple',
                'expected_coverage': 0.8,
                'expected_quality': 0.8
            }
        }
    
    def run_benchmark(
        self,
        benchmark_id: str,
        java_code: str,
        bedrock_code: str,
        validation_score: float
    ) -> Dict[str, Any]:
        """Run a benchmark test."""
        
        if benchmark_id not in self.benchmarks:
            return {'error': f'Unknown benchmark: {benchmark_id}'}
        
        benchmark = self.benchmarks[benchmark_id]
        
        # Calculate actual metrics
        from engines.regression_engine import get_regression_detector
        detector = get_regression_detector()
        
        # Get coverage
        coverage_tracker = CoverageTracker()
        coverage = coverage_tracker.track_conversion(
            conversion_id=f'benchmark_{benchmark_id}',
            mod_type=benchmark['mod_type'],
            java_code=java_code,
            bedrock_code=bedrock_code
        )
        
        # Determine pass/fail
        coverage_pass = coverage.overall_coverage >= benchmark['expected_coverage']
        quality_pass = validation_score >= benchmark['expected_quality']
        
        result = {
            'benchmark_id': benchmark_id,
            'expected_coverage': benchmark['expected_coverage'],
            'actual_coverage': coverage.overall_coverage,
            'coverage_pass': coverage_pass,
            'expected_quality': benchmark['expected_quality'],
            'actual_quality': validation_score,
            'quality_pass': quality_pass,
            'overall_pass': coverage_pass and quality_pass,
            'timestamp': datetime.now().isoformat()
        }
        
        self.results.append(result)
        return result
    
    def get_benchmark_summary(self) -> Dict[str, Any]:
        """Get summary of all benchmark results."""
        if not self.results:
            return {'message': 'No benchmarks run yet'}
        
        passed = sum(1 for r in self.results if r['overall_pass'])
        total = len(self.results)
        
        return {
            'total_benchmarks': total,
            'passed': passed,
            'failed': total - passed,
            'pass_rate': passed / total if total > 0 else 0.0,
            'results': self.results[-10:]  # Last 10 results
        }


# Singleton instances
_coverage_tracker: Optional[CoverageTracker] = None
_quality_scorer: Optional[QualityScorer] = None
_trend_analyzer: Optional[TrendAnalyzer] = None
_benchmark_suite: Optional[BenchmarkSuite] = None


def get_coverage_tracker() -> CoverageTracker:
    """Get coverage tracker singleton."""
    global _coverage_tracker
    if _coverage_tracker is None:
        _coverage_tracker = CoverageTracker()
    return _coverage_tracker


def get_quality_scorer() -> QualityScorer:
    """Get quality scorer singleton."""
    global _quality_scorer
    if _quality_scorer is None:
        _quality_scorer = QualityScorer()
    return _quality_scorer


def get_trend_analyzer() -> TrendAnalyzer:
    """Get trend analyzer singleton."""
    global _trend_analyzer
    if _trend_analyzer is None:
        _trend_analyzer = TrendAnalyzer()
    return _trend_analyzer


def get_benchmark_suite() -> BenchmarkSuite:
    """Get benchmark suite singleton."""
    global _benchmark_suite
    if _benchmark_suite is None:
        _benchmark_suite = BenchmarkSuite()
    return _benchmark_suite
