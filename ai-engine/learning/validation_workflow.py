"""
Correction validation workflow for user correction learning system.

Provides validation logic to ensure corrections meet quality criteria
before being approved and applied to the knowledge base.
"""

import json
import re
import sys
import uuid
from pathlib import Path
from typing import List, Optional, Tuple

ai_engine_path = str(Path(__file__).parent.parent.parent)
if ai_engine_path not in sys.path:
    sys.path.insert(0, ai_engine_path)


class ValidationResult:
    """Result of correction validation."""

    def __init__(
        self,
        is_valid: bool,
        confidence: float,
        issues: List[str],
        suggestions: List[str],
    ):
        self.is_valid = is_valid
        self.confidence = confidence
        self.issues = issues
        self.suggestions = suggestions

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "confidence": self.confidence,
            "issues": self.issues,
            "suggestions": self.suggestions,
        }


class CorrectionValidator:
    """Validate corrections before approval."""

    def __init__(self):
        self._db_session = None
        self._correction_store = None

    async def initialize(self, db_session):
        """Initialize with database session."""
        self._db_session = db_session
        from learning.correction_store import CorrectionStore

        self._correction_store = CorrectionStore()
        await self._correction_store.initialize(db_session)

    async def validate_correction(
        self,
        original_output: str,
        corrected_output: str,
        correction_rationale: Optional[str] = None,
    ) -> ValidationResult:
        """Validate a correction meets quality criteria.

        Checks:
        - Syntax validity of corrected output
        - Semantic coherence (not just random changes)
        - Length reasonableness (not truncating)
        - No malicious code patterns
        """
        issues = []
        suggestions = []
        confidence = 1.0

        if not corrected_output or len(corrected_output.strip()) == 0:
            issues.append("Corrected output is empty")
            return ValidationResult(False, 0.0, issues, suggestions)

        if len(corrected_output.strip()) < 3:
            issues.append("Corrected output is too short (less than 3 characters)")
            return ValidationResult(False, 0.1, issues, suggestions)

        if original_output.strip() == corrected_output.strip():
            issues.append("Corrected output is identical to original")
            return ValidationResult(False, 0.0, issues, suggestions)

        original_len = len(original_output)
        corrected_len = len(corrected_output)
        length_ratio = corrected_len / max(original_len, 1)

        if length_ratio > 3.0:
            issues.append(f"Corrected output is too long ({length_ratio:.1f}x original length)")
            confidence -= 0.3
        elif length_ratio < 0.2:
            issues.append(f"Corrected output is too short ({length_ratio:.1f}x original length)")
            confidence -= 0.3

        if self._contains_malicious_patterns(corrected_output):
            issues.append("Corrected output contains potentially malicious patterns")
            confidence -= 0.5
            suggestions.append("Review for security concerns before approval")

        syntax_valid = self._validate_syntax(corrected_output)
        if not syntax_valid["valid"]:
            issues.extend(syntax_valid["issues"])
            confidence -= 0.2 * len(syntax_valid["issues"])

        semantic_coherence = self._check_semantic_coherence(original_output, corrected_output)
        if not semantic_coherence["coherent"]:
            suggestions.append(semantic_coherence["reason"])

        confidence = max(0.0, min(1.0, confidence))

        is_valid = len(issues) == 0 and confidence >= 0.5

        return ValidationResult(is_valid, confidence, issues, suggestions)

    def _contains_malicious_patterns(self, text: str) -> bool:
        """Check for potentially malicious code patterns."""
        malicious_patterns = [
            r"eval\s*\(",
            r"exec\s*\(",
            r"__import__\s*\(",
            r"import\s+os",
            r"import\s+sys",
            r"subprocess",
            r"requests\.post",
            r"eval\s*<",
            r"<script",
            r"javascript:",
        ]
        text_lower = text.lower()
        for pattern in malicious_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False

    def _validate_syntax(self, text: str) -> dict:
        """Basic syntax validation for JSON/JS."""
        issues = []

        if text.startswith("{") and text.endswith("}"):
            try:
                json.loads(text)
            except json.JSONDecodeError as e:
                issues.append(f"Invalid JSON syntax: {str(e)}")
                return {"valid": False, "issues": issues}

        if "function(" in text or "=>" in text:
            brace_count = text.count("{") - text.count("}")
            if brace_count != 0:
                issues.append("Unbalanced braces in code")

        if "def " in text or "class " in text:
            if "def " in text:
                paren_count = text.count("(") - text.count(")")
                if paren_count != 0:
                    issues.append("Unbalanced parentheses in function definition")

        return {"valid": len(issues) == 0, "issues": issues}

    def _check_semantic_coherence(self, original: str, corrected: str) -> dict:
        """Check if the correction is semantically coherent."""
        original_words = set(original.lower().split())
        corrected_words = set(corrected.lower().split())

        if not original_words or not corrected_words:
            return {"coherent": False, "reason": "Empty text"}

        overlap = len(original_words.intersection(corrected_words))
        total_words = len(original_words.union(corrected_words))

        jaccard_similarity = overlap / max(total_words, 1)

        if jaccard_similarity < 0.2:
            return {
                "coherent": False,
                "reason": f"Low word overlap ({jaccard_similarity:.2f}) between original and corrected",
            }

        return {"coherent": True, "reason": ""}

    async def approve_correction(
        self,
        correction_id: uuid.UUID,
        validator_notes: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Approve a correction after validation passes.

        Returns (success, message).
        """
        if not self._correction_store:
            raise RuntimeError("CorrectionValidator not initialized. Call initialize() first.")

        corrections = await self._correction_store.get_corrections(
            job_id=None, status=None, limit=1000
        )

        correction = None
        for c in corrections:
            if c["id"] == str(correction_id):
                correction = c
                break

        if not correction:
            return False, f"Correction {correction_id} not found"

        validation = await self.validate_correction(
            correction["original_output"],
            correction["corrected_output"],
            correction.get("correction_rationale"),
        )

        if not validation.is_valid:
            issues = ", ".join(validation.issues) if validation.issues else "Unknown issues"
            return False, f"Validation failed: {issues}"

        try:
            await self._correction_store.update_correction_status(
                correction_id,
                "approved",
                reviewed_by="validator",
                review_notes=validator_notes or "Auto-approved after validation",
            )
            return True, "Correction approved successfully"
        except Exception as e:
            return False, f"Failed to approve correction: {str(e)}"

    async def batch_validate(
        self, correction_ids: List[uuid.UUID]
    ) -> List[Tuple[uuid.UUID, ValidationResult]]:
        """Validate multiple corrections at once."""
        if not self._correction_store:
            raise RuntimeError("CorrectionValidator not initialized. Call initialize() first.")

        results = []
        corrections = await self._correction_store.get_corrections(
            job_id=None, status=None, limit=1000
        )

        correction_map = {c["id"]: c for c in corrections}

        for correction_id in correction_ids:
            correction = correction_map.get(str(correction_id))
            if not correction:
                results.append(
                    (
                        correction_id,
                        ValidationResult(False, 0.0, [f"Correction {correction_id} not found"], []),
                    )
                )
                continue

            validation = await self.validate_correction(
                correction["original_output"],
                correction["corrected_output"],
                correction.get("correction_rationale"),
            )
            results.append((correction_id, validation))

        return results


async def validate_correction(
    original_output: str,
    corrected_output: str,
    correction_rationale: Optional[str] = None,
) -> ValidationResult:
    """Standalone function to validate a correction."""
    validator = CorrectionValidator()
    return await validator.validate_correction(
        original_output, corrected_output, correction_rationale
    )
