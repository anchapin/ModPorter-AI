"""
Unit tests for correction learning system.

Tests:
- CorrectionStore: Storage and retrieval of corrections
- CorrectionValidator: Validation of corrections before approval
- FeedbackReranker: Re-ranking based on correction patterns
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch


class TestCorrectionValidator:
    """Tests for CorrectionValidator class."""

    @pytest.fixture
    def validator(self):
        """Create a validator for testing."""
        from learning.validation_workflow import CorrectionValidator

        return CorrectionValidator()

    @pytest.mark.asyncio
    async def test_validator_valid_correction(self, validator):
        """Test validation of a valid correction."""
        original = "public class Block {}"
        corrected = "public class CustomBlock extends Block { private int value; }"

        result = await validator.validate_correction(original, corrected)

        assert result.is_valid is True
        assert result.confidence > 0.5
        assert len(result.issues) == 0

    @pytest.mark.asyncio
    async def test_validator_invalid_empty(self, validator):
        """Test validation fails for empty output."""
        original = "public class Block {}"
        corrected = ""

        result = await validator.validate_correction(original, corrected)

        assert result.is_valid is False
        assert "empty" in result.issues[0].lower()

    @pytest.mark.asyncio
    async def test_validator_invalid_identical(self, validator):
        """Test validation fails for identical output."""
        original = "public class Block {}"
        corrected = "public class Block {}"

        result = await validator.validate_correction(original, corrected)

        assert result.is_valid is False
        assert "identical" in result.issues[0].lower()

    @pytest.mark.asyncio
    async def test_validator_invalid_too_long(self, validator):
        """Test validation fails for excessively long correction."""
        original = "x"
        corrected = "x" * 1000

        result = await validator.validate_correction(original, corrected)

        assert result.confidence < 1.0

    @pytest.mark.asyncio
    async def test_validator_json_syntax(self, validator):
        """Test validation of JSON syntax."""
        original = '{"key": "value"}'
        corrected = '{"key": "value", "new_key": 123}'

        result = await validator.validate_correction(original, corrected)

        assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_validator_json_invalid(self, validator):
        """Test validation catches invalid JSON."""
        original = '{"key": "value"}'
        corrected = '{"key": "value", "broken"}'

        result = await validator.validate_correction(original, corrected)

        assert "JSON" in result.issues[0] or "json" in str(result.issues).lower()

    @pytest.mark.asyncio
    async def test_validator_semantic_coherence(self, validator):
        """Test semantic coherence check."""
        original = "public class Block extends Block {}"
        corrected = "completely unrelated text"

        result = await validator.validate_correction(original, corrected)

        if not result.is_valid:
            assert len(result.suggestions) > 0 or "low" in str(result.issues).lower()


class TestFeedbackReranker:
    """Tests for FeedbackReranker class."""

    @pytest.fixture
    def reranker(self):
        """Create a reranker for testing."""
        from search.feedback_reranker import FeedbackReranker

        return FeedbackReranker(decay_factor=0.95)

    def test_reranker_initialization(self, reranker):
        """Test reranker initializes with correct parameters."""
        assert reranker.decay_factor == 0.95

    def test_calculate_boost_score_zero_corrections(self, reranker):
        """Test boost calculation with no corrections."""
        boost = reranker._calculate_boost_score(0, None, [])
        assert boost == 0.0

    def test_calculate_boost_score_approved_correction(self, reranker):
        """Test boost calculation with approved correction."""
        boost = reranker._calculate_boost_score(1, None, [1.0])
        assert boost > 0

    def test_calculate_boost_score_rejected_correction(self, reranker):
        """Test boost calculation with rejected correction."""
        boost = reranker._calculate_boost_score(1, None, [-0.5])
        assert boost < 0

    def test_feedback_boost_calculation_for_corrections(self, reranker):
        """Test boost calculation from correction list."""
        corrections = [
            {
                "status": "approved",
                "submitted_at": datetime.utcnow().isoformat(),
            }
        ]
        boost = reranker._calculate_boost_score_for_corrections(corrections)
        assert boost > 0

    @pytest.mark.asyncio
    async def test_rerank_empty_results(self, reranker):
        """Test re-ranking with empty results."""
        from schemas.multimodal_schema import SearchResult

        results = []
        reranked = await reranker.rerank_with_feedback("query", results)
        assert reranked == []


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """Test ValidationResult can be created."""
        from learning.validation_workflow import ValidationResult

        result = ValidationResult(
            is_valid=True, confidence=0.8, issues=[], suggestions=["Looks good"]
        )

        assert result.is_valid is True
        assert result.confidence == 0.8
        assert result.suggestions == ["Looks good"]

    def test_validation_result_to_dict(self):
        """Test ValidationResult converts to dict."""
        from learning.validation_workflow import ValidationResult

        result = ValidationResult(
            is_valid=False, confidence=0.2, issues=["Issue 1"], suggestions=[]
        )

        d = result.to_dict()

        assert d["is_valid"] is False
        assert d["confidence"] == 0.2
        assert d["issues"] == ["Issue 1"]


class TestStandaloneFunctions:
    """Tests for standalone validation functions."""

    @pytest.mark.asyncio
    async def test_validate_correction_function(self):
        """Test standalone validate_correction function."""
        from learning.validation_workflow import validate_correction

        result = await validate_correction(
            original_output="test",
            corrected_output="test corrected",
        )

        assert isinstance(result.is_valid, bool)
        assert isinstance(result.confidence, float)
