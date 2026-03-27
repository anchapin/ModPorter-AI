"""
Query complexity analyzer for dynamic context window sizing.

This module classifies search queries into complexity levels (SIMPLE/STANDARD/COMPLEX)
to enable dynamic adjustment of context window size for optimal RAG performance.
"""

import re
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple


class ComplexityLevel(Enum):
    """Query complexity classification levels."""

    SIMPLE = "simple"
    STANDARD = "standard"
    COMPLEX = "complex"


@dataclass
class ComplexityAnalysis:
    """Result of query complexity analysis."""

    level: ComplexityLevel
    confidence: float
    reasoning: List[str]
    token_count: int
    features: dict


class QueryComplexityAnalyzer:
    """
    Analyzes query complexity using heuristics and pattern matching.

    Classification criteria:
    - SIMPLE: Single concept, <5 tokens, no technical terms
    - STANDARD: Multiple concepts, 5-15 tokens, basic technical terms
    - COMPLEX: Multi-part question, >15 tokens, multiple technical terms, conditional logic
    """

    # Technical terms that indicate STANDARD or COMPLEX queries
    TECHNICAL_TERMS = {
        # Programming terms
        "class",
        "method",
        "function",
        "variable",
        "interface",
        "abstract",
        "constructor",
        "import",
        "export",
        "callback",
        "async",
        "await",
        "parameter",
        "return",
        "type",
        "generic",
        "inheritance",
        "override",
        "implementation",
        "api",
        "sdk",
        "library",
        "module",
        "package",
        # Minecraft modding terms
        "block",
        "item",
        "entity",
        "tile_entity",
        "recipe",
        "crafting",
        "behavior",
        "definition",
        "texture",
        "model",
        "animation",
        "event",
        "registry",
        "resource",
        "datapack",
        "tag",
        " loot_table",
        "advancement",
        # General technical terms
        "convert",
        "translate",
        "transform",
        "migrate",
        "port",
        "adapt",
        "implement",
        "configure",
        "setup",
        "install",
        "deploy",
        "build",
        # Cross-platform terms
        "java",
        "bedrock",
        "edition",
        "edition",
        "python",
        "javascript",
        "ai",
        "behavior",
        "custom",
        "server",
        "client",
    }

    # Question words that indicate more complex queries
    QUESTION_WORDS = {
        "how",
        "what",
        "why",
        "when",
        "where",
        "which",
        "who",
        "can",
        "could",
        "should",
        "would",
        "is",
        "are",
        "does",
        "do",
        "will",
    }

    # Logical operators and connectors
    LOGICAL_TERMS = {
        "and",
        "or",
        "but",
        "if",
        "then",
        "else",
        "because",
        "however",
        "while",
        "when",
        "between",
        "among",
        "except",
        "without",
        "despite",
    }

    # Comparative/superlative indicators
    COMPARISON_TERMS = {
        "better",
        "best",
        "worse",
        "worst",
        "more",
        "most",
        "less",
        "least",
        "compare",
        "difference",
        "versus",
        "vs",
        "opposite",
        "similar",
    }

    def __init__(self):
        self._technical_terms_lower = {term.lower() for term in self.TECHNICAL_TERMS}
        self._question_words_lower = {word.lower() for word in self.QUESTION_WORDS}
        self._logical_terms_lower = {term.lower() for term in self.LOGICAL_TERMS}
        self._comparison_terms_lower = {term.lower() for term in self.COMPARISON_TERMS}

    def analyze(self, query: str) -> Tuple[ComplexityLevel, float]:
        """
        Analyze query complexity.

        Args:
            query: The search query string

        Returns:
            Tuple of (ComplexityLevel, confidence_score)
        """
        analysis = self._analyze_detailed(query)
        return analysis.level, analysis.confidence

    def _analyze_detailed(self, query: str) -> ComplexityAnalysis:
        """Perform detailed complexity analysis."""
        # Tokenize
        tokens = self._tokenize(query)
        token_count = len(tokens)

        reasoning = []
        features = {}

        # Feature 1: Token count
        features["token_count"] = token_count
        if token_count < 5:
            reasoning.append(f"Token count ({token_count}) is low")
        elif token_count > 15:
            reasoning.append(f"Token count ({token_count}) is high")

        # Feature 2: Technical term detection
        tech_terms_found = self._count_technical_terms(tokens)
        features["technical_terms"] = tech_terms_found
        if tech_terms_found > 0:
            reasoning.append(f"Found {tech_terms_found} technical terms")

        # Feature 3: Question detection
        has_question = self._has_question_structure(tokens)
        features["has_question"] = has_question
        if has_question:
            reasoning.append("Query has question structure")

        # Feature 4: Multi-part detection (multiple clauses)
        is_multi_part = self._is_multi_part(query, tokens)
        features["multi_part"] = is_multi_part
        if is_multi_part:
            reasoning.append("Query has multiple parts/clauses")

        # Feature 5: Logical operators
        has_logical = self._has_logical_operators(tokens)
        features["has_logical"] = has_logical
        if has_logical:
            reasoning.append("Query contains logical operators")

        # Feature 6: Comparison/contrast
        has_comparison = self._has_comparison(tokens)
        features["has_comparison"] = has_comparison
        if has_comparison:
            reasoning.append("Query involves comparison")

        # Feature 7: Conditional language
        has_conditional = self._has_conditional(query)
        features["has_conditional"] = has_conditional
        if has_conditional:
            reasoning.append("Query contains conditional logic")

        # Calculate complexity score
        score = self._calculate_complexity_score(
            token_count=token_count,
            tech_terms=tech_terms_found,
            has_question=has_question,
            is_multi_part=is_multi_part,
            has_logical=has_logical,
            has_comparison=has_comparison,
            has_conditional=has_conditional,
        )

        # Determine level and confidence
        level, confidence = self._score_to_level(score, reasoning)

        return ComplexityAnalysis(
            level=level,
            confidence=confidence,
            reasoning=reasoning,
            token_count=token_count,
            features=features,
        )

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        # Remove punctuation and split
        text = re.sub(r"[^\w\s]", " ", text.lower())
        tokens = text.split()
        return [t for t in tokens if len(t) > 1]

    def _count_technical_terms(self, tokens: List[str]) -> int:
        """Count technical terms in tokens."""
        return sum(1 for t in tokens if t in self._technical_terms_lower)

    def _has_question_structure(self, tokens: List[str]) -> bool:
        """Check if query has question structure."""
        return any(t in self._question_words_lower for t in tokens)

    def _is_multi_part(self, query: str, tokens: List[str]) -> bool:
        """Check if query has multiple parts/clauses."""
        # Check for multiple clauses separated by punctuation or conjunctions
        clause_markers = [",", ";", " and ", " or ", " but ", " then "]

        # Count clause markers
        marker_count = sum(query.lower().count(m) for m in clause_markers)

        # Check for multiple question patterns
        question_patterns = [r"\?.*\?", r"\bhow\b.*\b(and|or)\b", r"\bwhat\b.*\b(and|or)\b"]
        multi_pattern = any(re.search(p, query.lower()) for p in question_patterns)

        return marker_count > 1 or multi_pattern

    def _has_logical_operators(self, tokens: List[str]) -> bool:
        """Check for logical operators."""
        return any(t in self._logical_terms_lower for t in tokens)

    def _has_comparison(self, tokens: List[str]) -> bool:
        """Check for comparison/contrast terms."""
        return any(t in self._comparison_terms_lower for t in tokens)

    def _has_conditional(self, query: str) -> bool:
        """Check for conditional language."""
        query_lower = query.lower()
        conditionals = [
            "if ",
            "when ",
            "unless ",
            "except ",
            "only ",
            "depends on",
            "requires ",
            "should ",
            "must ",
        ]
        return any(c in query_lower for c in conditionals)

    def _calculate_complexity_score(
        self,
        token_count: int,
        tech_terms: int,
        has_question: bool,
        is_multi_part: bool,
        has_logical: bool,
        has_comparison: bool,
        has_conditional: bool,
    ) -> float:
        """Calculate complexity score (0-1, higher = more complex)."""
        score = 0.0

        # Token count contribution (0-0.40) - higher weight for long queries
        if token_count < 5:
            score += 0.0
        elif token_count < 8:
            score += 0.10
        elif token_count < 12:
            score += 0.18
        elif token_count < 18:
            score += 0.28
        else:
            score += 0.40

        # Technical terms contribution (0-0.30) - higher weight
        score += min(tech_terms * 0.08, 0.30)

        # Question structure contribution (0-0.1)
        if has_question:
            score += 0.1

        # Multi-part contribution (0-0.15)
        if is_multi_part:
            score += 0.15

        # Logical operators contribution (0-0.1)
        if has_logical:
            score += 0.1

        # Comparison contribution (0-0.1)
        if has_comparison:
            score += 0.1

        # Conditional contribution (0-0.1)
        if has_conditional:
            score += 0.1

        return min(score, 1.0)

    def _score_to_level(self, score: float, reasoning: List[str]) -> Tuple[ComplexityLevel, float]:
        """Convert score to complexity level with confidence."""
        # Thresholds tuned to match acceptance criteria
        if score < 0.20:
            return ComplexityLevel.SIMPLE, max(0.85, 1.0 - score)
        elif score < 0.48:
            return ComplexityLevel.STANDARD, max(0.75, 1.0 - abs(score - 0.34))
        else:
            return ComplexityLevel.COMPLEX, max(0.70, 1.0 - (score - 0.48))


# Convenience function for quick analysis
def analyze_query_complexity(query: str) -> Tuple[ComplexityLevel, float]:
    """
    Convenience function to analyze query complexity.

    Args:
        query: The search query string

    Returns:
        Tuple of (ComplexityLevel, confidence_score)
    """
    analyzer = QueryComplexityAnalyzer()
    return analyzer.analyze(query)
