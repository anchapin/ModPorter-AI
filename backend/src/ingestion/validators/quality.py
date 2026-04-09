"""
Quality validation for ingested documents.

Validates documents before indexing to ensure quality.
"""

import re
import logging
from dataclasses import dataclass
from typing import Dict, Any, List


logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """
    Result of quality validation.

    Attributes:
        is_valid: Whether document passes validation
        errors: List of error messages (critical issues)
        warnings: List of warning messages (non-critical issues)
    """

    is_valid: bool
    errors: List[str]
    warnings: List[str]


class QualityValidator:
    """
    Validate document quality before indexing.

    Checks:
    - Length bounds (min/max characters)
    - Meaningful content (alphanumeric ratio)
    - Metadata completeness (title, source)
    """

    MIN_LENGTH = 50  # Minimum characters
    MAX_LENGTH = 100000  # Maximum characters
    MIN_ALPHANUMERIC_RATIO = 0.3  # 30% alphanumeric content

    def validate(self, content: str, metadata: Dict[str, Any]) -> ValidationResult:
        """
        Validate document quality.

        Args:
            content: Document content
            metadata: Document metadata

        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []

        # Check length bounds
        if len(content) < self.MIN_LENGTH:
            errors.append(f"Content too short: {len(content)} chars (minimum: {self.MIN_LENGTH})")

        if len(content) > self.MAX_LENGTH:
            errors.append(f"Content too long: {len(content)} chars (maximum: {self.MAX_LENGTH})")

        # Check for meaningful content
        if not self._is_meaningful(content):
            errors.append(
                f"Content lacks meaningful text (alphanumeric ratio < {self.MIN_ALPHANUMERIC_RATIO})"
            )

        # Check metadata completeness
        if not metadata.get("title"):
            warnings.append("Missing document title")

        if not metadata.get("source"):
            warnings.append("Missing document source")

        # Check for empty or whitespace-only content
        if not content.strip():
            errors.append("Content is empty or whitespace only")

        # Check for repetitive content (potential spam)
        if self._is_repetitive(content):
            warnings.append("Content appears repetitive (may be spam)")

        # Determine if valid
        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
        )

    def _is_meaningful(self, content: str) -> bool:
        """
        Check if content has meaningful text.

        Args:
            content: Document content

        Returns:
            True if alphanumeric ratio >= threshold
        """
        # Count alphanumeric characters
        alphanumeric = sum(1 for c in content if c.isalnum())

        # Calculate ratio
        if len(content) == 0:
            return False

        ratio = alphanumeric / len(content)

        return ratio >= self.MIN_ALPHANUMERIC_RATIO

    def _is_repetitive(self, content: str) -> bool:
        """
        Check if content is repetitive (potential spam).

        Args:
            content: Document content

        Returns:
            True if content appears repetitive
        """
        # Simple check: if the same sentence appears 5+ times
        sentences = re.split(r"[.!?]+", content)
        sentences = [s.strip().lower() for s in sentences if len(s.strip()) > 20]

        # Count occurrences
        from collections import Counter

        sentence_counts = Counter(sentences)

        # If any sentence appears 5+ times, it's repetitive
        for sentence, count in sentence_counts.items():
            if count >= 5:
                return True

        return False
