"""
Query Rewriter - LLM-based query rewriting for improved search.

This module provides query rewriting capabilities to clarify ambiguous queries
and improve search result quality.
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RewriteType(str, Enum):
    """Types of query rewrites."""

    CLARIFICATION = "clarification"
    SPECIFICATION = "specification"
    DECOMPOSITION = "decomposition"
    NONE = "none"


@dataclass
class RewriteResult:
    """Result of query rewriting."""

    original_query: str
    rewritten_query: str
    confidence: float
    rewrite_type: RewriteType
    explanation: str


class QueryRewriter:
    """
    Query rewriter for improving search queries.

    Supports rule-based and optional LLM-based rewriting to clarify
    ambiguous queries and improve search relevance.
    """

    def __init__(self, llm_client=None, enabled: bool = True):
        self.llm_client = llm_client
        self.enabled = enabled

        self.abbreviation_map = {
            "minecraft": "Minecraft",
            "mc": "Minecraft",
            "java": "Java",
            "api": "application programming interface",
            "sdk": "software development kit",
            "ui": "user interface",
            "ux": "user experience",
            "id": "identifier",
            "config": "configuration",
        }

        self.clarification_patterns = {
            r"\b(how do|how to)\s+(i|we|you)?\s*(\w+)": r"how to \3",
            r"\bwhat('s| is| are)?\s*a\s+(\w+)": r"what is \2",
            r"\bcreate\s+a[n]?\s+(\w+)": r"how to create \1",
        }

        logger.info(f"QueryRewriter initialized (enabled={enabled})")

    def rewrite(self, query: str, context: Dict = None) -> RewriteResult:
        """
        Rewrite a query for improved search.

        Args:
            query: Original query string
            context: Optional context information

        Returns:
            RewriteResult with rewritten query
        """
        if not self.enabled:
            return RewriteResult(
                original_query=query,
                rewritten_query=query,
                confidence=1.0,
                rewrite_type=RewriteType.NONE,
                explanation="Rewriting disabled",
            )

        original = query

        query = self._expand_abbreviations(query)
        rewrite_type, explanation = self._detect_rewrite_type(original, query)

        if rewrite_type == RewriteType.NONE:
            confidence = 1.0
        else:
            confidence = 0.8

        return RewriteResult(
            original_query=original,
            rewritten_query=query,
            confidence=confidence,
            rewrite_type=rewrite_type,
            explanation=explanation,
        )

    def _expand_abbreviations(self, query: str) -> str:
        """Expand common abbreviations in query."""
        query_lower = query.lower()
        words = query_lower.split()

        expanded = []
        for word in words:
            if word in self.abbreviation_map:
                expanded.append(self.abbreviation_map[word])
            else:
                expanded.append(word)

        return " ".join(expanded)

    def _detect_rewrite_type(self, original: str, rewritten: str) -> tuple:
        """Detect what type of rewrite was applied."""
        if original.lower() == rewritten.lower():
            return RewriteType.NONE, "No rewrite needed"

        orig_words = set(original.lower().split())
        new_words = set(rewritten.lower().split())

        added_words = new_words - orig_words

        if added_words:
            return RewriteType.CLARIFICATION, f"Expanded abbreviations: {added_words}"

        return RewriteType.NONE, "Minor modifications applied"

    def should_rewrite(self, query: str, complexity: Any = None) -> bool:
        """
        Determine if a query should be rewritten.

        Args:
            query: Query to evaluate
            complexity: Query complexity (if available)

        Returns:
            True if query should be rewritten
        """
        if not self.enabled:
            return False

        if not query or len(query.strip()) < 3:
            return False

        query_lower = query.lower()

        if any(word in query_lower for word in ["what's", "whats", "hows", "how's"]):
            return True

        for abbr in self.abbreviation_map:
            if abbr in query_lower:
                return True

        if complexity and hasattr(complexity, "value"):
            if complexity.value == "complex":
                return True

        return False

    def rewrite_with_llm(self, query: str) -> Optional[RewriteResult]:
        """Rewrite query using LLM (if available)."""
        if not self.llm_client:
            logger.debug("No LLM client available, using rule-based rewriting")
            return self.rewrite(query)

        try:
            prompt = f"""Rewrite the following search query to be clearer and more searchable.
Original: {query}

Return only the rewritten query, nothing else."""

            response = self.llm_client.generate(prompt)
            rewritten = response.strip()

            return RewriteResult(
                original_query=query,
                rewritten_query=rewritten,
                confidence=0.9,
                rewrite_type=RewriteType.SPECIFICATION,
                explanation="LLM-based rewrite",
            )
        except Exception as e:
            logger.warning(f"LLM rewrite failed: {e}")
            return self.rewrite(query)
