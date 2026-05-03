"""
Community contribution system for knowledge base.

Provides user-submitted patterns, validation, and review workflow.
"""

from .submission import (
    CommunityPatternManager,
    PatternSubmission,
    SubmissionStatus,
)
from .validation import PatternValidator, ValidationResult

__all__ = [
    "CommunityPatternManager",
    "PatternSubmission",
    "SubmissionStatus",
    "PatternValidator",
    "ValidationResult",
]
