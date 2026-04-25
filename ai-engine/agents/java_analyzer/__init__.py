"""
Java Analyzer package - modular Java mod analysis.

Provides the same public API as the original java_analyzer module
by re-exporting JavaAnalyzerAgent from java_analyzer.java_analyzer.
"""

from pathlib import Path

from agents.java_analyzer.feature_extractor import JAVASSIST_AVAILABLE, TREE_SITTER_AVAILABLE
from agents.java_analyzer.java_analyzer import JavaAnalyzerAgent, logger
from models.smart_assumptions import SmartAssumptionEngine
from utils.embedding_generator import LocalEmbeddingGenerator

JavaAnalyzer = JavaAnalyzerAgent

__all__ = [
    "JavaAnalyzerAgent",
    "JavaAnalyzer",
    "JAVASSIST_AVAILABLE",
    "TREE_SITTER_AVAILABLE",
    "SmartAssumptionEngine",
    "LocalEmbeddingGenerator",
    "logger",
    "Path",
]
