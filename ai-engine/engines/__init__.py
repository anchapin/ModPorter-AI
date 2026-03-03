"""
Engines package for ModPorter AI

This package contains specialized engines for code analysis, validation,
and translation.

Modules:
- comparison_engine: Comparison between Java and Bedrock code
- javascript_validator: JavaScript code validation (Issue #570)
- translation_warnings: Translation warning detection (Issue #570)
"""

# Safe imports that won't break the package
try:
    from .comparison_engine import ComparisonEngine
except ImportError:
    ComparisonEngine = None

from .javascript_validator import JavaScriptValidator, ValidationResult, Severity, ValidationIssue
from .translation_warnings import TranslationWarningDetector, WarningReport, ImpactLevel, TranslationWarning

__all__ = [
    'ComparisonEngine',
    'JavaScriptValidator',
    'ValidationResult',
    'Severity',
    'ValidationIssue',
    'TranslationWarningDetector',
    'WarningReport',
    'ImpactLevel',
    'TranslationWarning',
]
