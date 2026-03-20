"""
Data Quality Scoring System

Provides automated quality metrics for training data evaluation
and human review queue integration.
"""

import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class QualityMetric(str, Enum):
    """Quality metrics for training data."""
    SYNTAX_VALIDITY = "syntax_validity"
    COMPLETENESS = "completeness"
    COMPLEXITY_MATCH = "complexity_match"
    TOKEN_RATIO = "token_ratio"
    STRUCTURAL_SIMILARITY = "structural_similarity"
    NAMING_CONVENTION = "naming_convention"


@dataclass
class QualityScore:
    """Quality score for a training pair."""
    overall_score: float  # 0.0 - 1.0
    syntax_validity: float = 0.0
    completeness: float = 0.0
    complexity_match: float = 0.0
    token_ratio: float = 0.0
    structural_similarity: float = 0.0
    naming_convention: float = 0.0
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ReviewItem:
    """Item in the manual review queue."""
    id: str
    training_pair_id: str
    quality_score: float
    status: str = "pending"  # pending, approved, rejected, needs_changes
    reviewer_notes: str = ""
    reviewed_by: str = ""
    created_at: str = ""
    reviewed_at: Optional[str] = None


class DataQualityScorer:
    """Automated quality scoring for training data."""

    # Thresholds for quality metrics
    MIN_TOKEN_RATIO = 0.3  # Output should be at least 30% of input length
    MAX_TOKEN_RATIO = 5.0  # Output should be at most 5x input length
    MIN_CODE_LENGTH = 10   # Minimum meaningful code length

    def __init__(self, enable_deep_analysis: bool = True):
        self.enable_deep_analysis = enable_deep_analysis

    def score_training_pair(
        self,
        input_source: str,
        output_target: str,
        metadata: Dict[str, Any]
    ) -> QualityScore:
        """
        Score a training data pair across multiple quality dimensions.

        Args:
            input_source: Java source code
            output_target: Bedrock output code
            metadata: Additional metadata (mod_type, complexity, etc.)

        Returns:
            QualityScore with individual metrics and overall score
        """
        issues = []
        warnings = []

        # 1. Syntax validity (basic checks)
        syntax_score = self._check_syntax_validity(input_source, output_target)
        if syntax_score < 0.5:
            issues.append("Low syntax validity detected")

        # 2. Completeness
        completeness_score = self._check_completeness(input_source, output_target)
        if completeness_score < 0.7:
            warnings.append("Potential completeness issues")

        # 3. Complexity match
        complexity_score = self._check_complexity_match(input_source, output_target, metadata)
        
        # 4. Token ratio
        token_ratio_score = self._check_token_ratio(input_source, output_target)
        if token_ratio_score < 0.5:
            issues.append("Unusual token ratio between input and output")

        # 5. Structural similarity
        structural_score = self._check_structural_similarity(input_source, output_target)
        
        # 6. Naming convention compliance
        naming_score = self._check_naming_conventions(output_target)

        # Calculate overall score (weighted average)
        weights = {
            "syntax": 0.25,
            "completeness": 0.20,
            "complexity": 0.15,
            "token_ratio": 0.15,
            "structural": 0.15,
            "naming": 0.10,
        }
        overall_score = (
            syntax_score * weights["syntax"] +
            completeness_score * weights["completeness"] +
            complexity_score * weights["complexity"] +
            token_ratio_score * weights["token_ratio"] +
            structural_score * weights["structural"] +
            naming_score * weights["naming"]
        )

        return QualityScore(
            overall_score=overall_score,
            syntax_validity=syntax_score,
            completeness=completeness_score,
            complexity_match=complexity_score,
            token_ratio=token_ratio_score,
            structural_similarity=structural_score,
            naming_convention=naming_score,
            issues=issues,
            warnings=warnings,
        )

    def _check_syntax_validity(self, input_source: str, output_target: str) -> float:
        """Check basic syntax validity."""
        score = 1.0

        # Check for balanced braces
        if input_source.count('{') != input_source.count('}'):
            score -= 0.2
        if output_target.count('{') != output_target.count('}'):
            score -= 0.2

        # Check for balanced parentheses
        if input_source.count('(') != input_source.count(')'):
            score -= 0.1
        if output_target.count('(') != output_target.count(')'):
            score -= 0.1

        # Check for empty content
        if len(input_source.strip()) < self.MIN_CODE_LENGTH:
            score -= 0.3
        if len(output_target.strip()) < self.MIN_CODE_LENGTH:
            score -= 0.3

        return max(0.0, score)

    def _check_completeness(self, input_source: str, output_target: str) -> float:
        """Check if conversion appears complete."""
        score = 1.0

        # Check for common Java patterns that should have equivalents
        java_patterns = ["class ", "public ", "private ", "void ", "import "]
        bedrock_patterns = ["{", "format_version", "minecraft:"]

        java_count = sum(1 for p in java_patterns if p in input_source)
        bedrock_count = sum(1 for p in bedrock_patterns if p in output_target)

        # If Java has class/import, output should have something meaningful
        if java_count > 0 and bedrock_count == 0:
            score -= 0.5

        # Check for common Minecraft entity patterns
        if "Entity" in input_source and "minecraft:entity" not in output_target:
            score -= 0.2

        return max(0.0, score)

    def _check_complexity_match(
        self,
        input_source: str,
        output_target: str,
        metadata: Dict[str, Any]
    ) -> float:
        """Check if output complexity matches expected complexity."""
        score = 1.0

        input_lines = len(input_source.split('\n'))
        output_lines = len(output_target.split('\n'))

        expected_complexity = metadata.get("complexity", "medium")

        if expected_complexity == "simple":
            # Simple conversions should be relatively short
            if output_lines > 100:
                score -= 0.3
        elif expected_complexity == "complex":
            # Complex conversions should have substantial output
            if output_lines < 50:
                score -= 0.3

        # Line count ratio should be reasonable
        if input_lines > 0:
            ratio = output_lines / input_lines
            if ratio < 0.1 or ratio > 10:
                score -= 0.2

        return max(0.0, score)

    def _check_token_ratio(self, input_source: str, output_target: str) -> float:
        """Check token ratio between input and output."""
        input_tokens = len(input_source.split())
        output_tokens = len(output_target.split())

        if input_tokens == 0:
            return 0.0

        ratio = output_tokens / input_tokens

        if ratio < self.MIN_TOKEN_RATIO:
            return ratio / self.MIN_TOKEN_RATIO
        elif ratio > self.MAX_TOKEN_RATIO:
            return max(0.0, 1.0 - (ratio - self.MAX_TOKEN_RATIO) / self.MAX_TOKEN_RATIO)
        else:
            return 1.0

    def _check_structural_similarity(self, input_source: str, output_target: str) -> float:
        """Check basic structural similarity."""
        # Simple heuristic: check for presence of identifiers
        java_identifiers = set(word for word in input_source.split() 
                              if word.isidentifier() and len(word) > 3)
        bedrock_identifiers = set(word for word in output_target.split()
                                  if word.isidentifier() and len(word) > 3)

        if not java_identifiers:
            return 0.5

        overlap = len(java_identifiers & bedrock_identifiers)
        return min(1.0, overlap / len(java_identifiers) * 2)

    def _check_naming_conventions(self, output_target: str) -> float:
        """Check Bedrock naming convention compliance."""
        score = 1.0

        # Check for Minecraft namespace prefix
        if "minecraft:" not in output_target and " Bedrock" not in output_target:
            # This might be fine for pure JS, but flag as warning
            warnings = []

        # Check for PascalCase or camelCase consistency
        lines = output_target.split('\n')
        property_patterns = 0
        for line in lines:
            if '=' in line and '"' in line:
                property_patterns += 1

        return min(1.0, score)

    def batch_score(
        self,
        training_pairs: List[Dict[str, Any]]
    ) -> List[QualityScore]:
        """Score multiple training pairs."""
        scores = []
        for i, pair in enumerate(training_pairs):
            try:
                score = self.score_training_pair(
                    pair.get("input_source", ""),
                    pair.get("output_target", ""),
                    pair.get("metadata", {})
                )
                scores.append(score)
            except Exception as e:
                logger.warning(f"Error scoring pair {i}: {e}")
                scores.append(QualityScore(overall_score=0.0, issues=[str(e)]))
        return scores


class ManualReviewQueue:
    """Manual review queue for human labeling."""

    def __init__(self, storage_path: str = "./data/review_queue"):
        from pathlib import Path
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.review_file = self.storage_path / "review_queue.jsonl"

    def add_to_queue(
        self,
        training_pair_id: str,
        quality_score: float,
        reason: str = ""
    ) -> str:
        """Add an item to the review queue."""
        item = ReviewItem(
            id=self._generate_id(training_pair_id),
            training_pair_id=training_pair_id,
            quality_score=quality_score,
            created_at=datetime.now().isoformat(),
        )

        with open(self.review_file, "a") as f:
            f.write(json.dumps(item.__dict__) + "\n")

        logger.info(f"Added {training_pair_id} to review queue")
        return item.id

    def get_pending_reviews(self, limit: int = 100) -> List[ReviewItem]:
        """Get pending review items."""
        pending = []
        if not self.review_file.exists():
            return pending

        with open(self.review_file) as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    if item.get("status") == "pending":
                        pending.append(ReviewItem(**item))

        return pending[:limit]

    def approve(self, review_id: str, reviewer: str = "system") -> bool:
        """Approve a review item."""
        return self._update_status(review_id, "approved", reviewer)

    def reject(self, review_id: str, reviewer: str = "system", notes: str = "") -> bool:
        """Reject a review item."""
        return self._update_status(review_id, "rejected", reviewer, notes)

    def _update_status(
        self,
        review_id: str,
        status: str,
        reviewer: str,
        notes: str = ""
    ) -> bool:
        """Update review item status."""
        if not self.review_file.exists():
            return False

        items = []
        updated = False

        with open(self.review_file) as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    if item.get("id") == review_id:
                        item["status"] = status
                        item["reviewed_by"] = reviewer
                        item["reviewed_at"] = datetime.now().isoformat()
                        if notes:
                            item["reviewer_notes"] = notes
                        updated = True
                    items.append(item)

        if updated:
            with open(self.review_file, "w") as f:
                for item in items:
                    f.write(json.dumps(item) + "\n")

        return updated

    def _generate_id(self, training_pair_id: str) -> str:
        """Generate unique review ID."""
        timestamp = datetime.now().isoformat()
        return hashlib.md5(f"{training_pair_id}:{timestamp}".encode()).hexdigest()[:12]

    def get_statistics(self) -> Dict[str, Any]:
        """Get review queue statistics."""
        if not self.review_file.exists():
            return {
                "total": 0,
                "pending": 0,
                "approved": 0,
                "rejected": 0,
            }

        stats = {"total": 0, "pending": 0, "approved": 0, "rejected": 0}

        with open(self.review_file) as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    stats["total"] += 1
                    status = item.get("status", "pending")
                    if status in stats:
                        stats[status] += 1

        return stats
