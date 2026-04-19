"""Unit tests for conformal_scorer.py - per-segment confidence scoring."""

import pytest
from qa.report.conformal_scorer import (
    ConformalScorer,
    CandidateResult,
    create_candidate_result,
)
from qa.report.models import SegmentConfidence, ConfidenceDistribution, ConfidenceLevel


class TestConformalScorer:
    """Test suite for ConformalScorer."""

    def test_score_segment_no_candidates(self):
        """Test scoring when no candidates are provided."""
        scorer = ConformalScorer()
        result = scorer.score_segment("test_block", [])

        assert result.confidence == 0.0
        assert result.review_flag is True
        assert "No candidates generated" in result.confidence_reasons
        assert result.candidate_count == 0

    def test_score_segment_single_candidate_high_assertion(self):
        """Test scoring with single candidate with high assertion pass rate."""
        scorer = ConformalScorer()
        candidate = CandidateResult(
            candidate_id=0,
            code="test code",
            assertion_results=[True, True, True, True],
            semantic_score=0.9,
        )

        result = scorer.score_segment("test_block", [candidate])

        assert result.candidate_count == 1
        assert result.assertion_pass_rate == 1.0
        assert result.confidence > 0.5
        assert result.is_high_confidence or result.is_soft_flag

    def test_score_segment_single_candidate_low_assertion(self):
        """Test scoring with single candidate with low assertion pass rate."""
        scorer = ConformalScorer()
        candidate = CandidateResult(
            candidate_id=0,
            code="test code",
            assertion_results=[True, False, False],
            semantic_score=0.3,
        )

        result = scorer.score_segment("test_block", [candidate])

        assert result.candidate_count == 1
        assert result.assertion_pass_rate == pytest.approx(0.333, rel=0.1)
        assert result.is_soft_flag or result.is_hard_flag

    def test_score_segment_three_agreeing_candidates(self):
        """Test scoring with 3 candidates that agree."""
        scorer = ConformalScorer(candidate_count=3)
        candidates = [
            CandidateResult(candidate_id=0, code="same code", assertion_results=[True, True]),
            CandidateResult(candidate_id=1, code="same code", assertion_results=[True, True]),
            CandidateResult(candidate_id=2, code="same code", assertion_results=[True, True]),
        ]

        result = scorer.score_segment("test_block", candidates)

        assert result.candidate_count == 3
        assert result.agreement_score == 1.0
        assert result.is_high_confidence
        assert "High candidate agreement (3/3)" in result.confidence_reasons

    def test_score_segment_three_disagreeing_candidates(self):
        """Test scoring with 3 candidates that disagree."""
        scorer = ConformalScorer(candidate_count=3)
        candidates = [
            CandidateResult(candidate_id=0, code="code type A", assertion_results=[True]),
            CandidateResult(candidate_id=1, code="code type B", assertion_results=[False]),
            CandidateResult(candidate_id=2, code="code type C", assertion_results=[False]),
        ]

        result = scorer.score_segment("test_block", candidates)

        assert result.candidate_count == 3
        assert result.agreement_score < 1.0
        assert result.review_flag is True

    def test_score_segment_partial_agreement(self):
        """Test scoring with 2 agreeing and 1 disagreeing candidate."""
        scorer = ConformalScorer(candidate_count=3)
        candidates = [
            CandidateResult(candidate_id=0, code="same", assertion_results=[True, True]),
            CandidateResult(candidate_id=1, code="same", assertion_results=[True, True]),
            CandidateResult(candidate_id=2, code="different", assertion_results=[False, False]),
        ]

        result = scorer.score_segment("test_block", candidates)

        assert result.candidate_count == 3
        assert 0.0 < result.agreement_score < 1.0

    def test_score_segment_mixed_assertions(self):
        """Test scoring with mixed assertion results."""
        scorer = ConformalScorer()
        candidates = [
            CandidateResult(
                candidate_id=0,
                code="test",
                assertion_results=[True, True, False, True],
            ),
            CandidateResult(
                candidate_id=1,
                code="test",
                assertion_results=[True, False, False, True],
            ),
            CandidateResult(
                candidate_id=2,
                code="test",
                assertion_results=[False, False, True, False],
            ),
        ]

        result = scorer.score_segment("test_block", candidates)

        expected_rate = 6 / 12
        assert result.assertion_pass_rate == pytest.approx(expected_rate, rel=0.1)

    def test_score_batch_empty(self):
        """Test batch scoring with empty input."""
        scorer = ConformalScorer()
        segments = []

        results, distribution = scorer.score_batch(segments)

        assert results == []
        assert distribution.total_segments == 0
        assert distribution.high_confidence_count == 0

    def test_score_batch_mixed_segments(self):
        """Test batch scoring with mixed confidence segments."""
        scorer = ConformalScorer()
        segments = [
            {
                "block_id": "high_conf",
                "candidates": [
                    {"code": "same", "assertions": [True, True], "semantic_score": 0.9},
                    {"code": "same", "assertions": [True, True], "semantic_score": 0.9},
                    {"code": "same", "assertions": [True, True], "semantic_score": 0.9},
                ],
            },
            {
                "block_id": "low_conf",
                "candidates": [
                    {"code": "type A", "assertions": [False], "semantic_score": 0.3},
                    {"code": "type B", "assertions": [False], "semantic_score": 0.3},
                    {"code": "type C", "assertions": [False], "semantic_score": 0.3},
                ],
            },
            {
                "block_id": "soft_flag",
                "candidates": [
                    {"code": "code1", "assertions": [True, False], "semantic_score": 0.6},
                    {"code": "code2", "assertions": [True, False], "semantic_score": 0.6},
                ],
            },
        ]

        results, distribution = scorer.score_batch(segments)

        assert len(results) == 3
        assert distribution.total_segments == 3
        assert distribution.high_confidence_count >= 1
        assert distribution.hard_flag_count >= 1

    def test_confidence_thresholds(self):
        """Test confidence level classification."""
        scorer = ConformalScorer(high_threshold=0.80, soft_threshold=0.60)

        high_result = scorer.score_segment(
            "block",
            [
                CandidateResult(
                    candidate_id=0, code="a", assertion_results=[True] * 10, semantic_score=0.95
                )
            ],
        )
        assert high_result.confidence_level == ConfidenceLevel.HIGH

        soft_result = scorer.score_segment(
            "block",
            [
                CandidateResult(
                    candidate_id=0, code="a", assertion_results=[True, True], semantic_score=0.65
                )
            ],
        )
        assert soft_result.confidence_level == ConfidenceLevel.SOFT_FLAG

        hard_result = scorer.score_segment(
            "block",
            [
                CandidateResult(
                    candidate_id=0, code="a", assertion_results=[False], semantic_score=0.3
                )
            ],
        )
        assert hard_result.confidence_level == ConfidenceLevel.HARD_FLAG

    def test_create_candidate_result(self):
        """Test helper function for creating candidate results."""
        candidate = create_candidate_result(
            candidate_id=1,
            code="test code",
            assertions=[True, False, True],
            semantic_score=0.75,
        )

        assert candidate.candidate_id == 1
        assert candidate.code == "test code"
        assert candidate.assertion_pass_rate == pytest.approx(0.667, rel=0.1)
        assert candidate.semantic_score == 0.75


class TestSegmentConfidence:
    """Test suite for SegmentConfidence model."""

    def test_segment_confidence_properties(self):
        """Test SegmentConfidence property methods."""
        segment = SegmentConfidence(
            block_id="test.Block",
            confidence=0.87,
            review_flag=False,
            confidence_reasons=["High agreement"],
            candidate_count=3,
            agreement_score=0.9,
            assertion_pass_rate=0.85,
        )

        assert segment.is_high_confidence
        assert not segment.is_soft_flag
        assert not segment.is_hard_flag
        assert segment.confidence_level == ConfidenceLevel.HIGH

    def test_segment_confidence_soft_flag(self):
        """Test soft flag classification."""
        segment = SegmentConfidence(
            block_id="test.Block",
            confidence=0.70,
            review_flag=True,
            confidence_reasons=["Review recommended"],
        )

        assert not segment.is_high_confidence
        assert segment.is_soft_flag
        assert not segment.is_hard_flag
        assert segment.confidence_level == ConfidenceLevel.SOFT_FLAG

    def test_segment_confidence_hard_flag(self):
        """Test hard flag classification."""
        segment = SegmentConfidence(
            block_id="test.Block",
            confidence=0.45,
            review_flag=True,
            confidence_reasons=["Manual conversion required"],
        )

        assert not segment.is_high_confidence
        assert not segment.is_soft_flag
        assert segment.is_hard_flag
        assert segment.confidence_level == ConfidenceLevel.HARD_FLAG

    def test_segment_confidence_to_dict(self):
        """Test SegmentConfidence serialization."""
        segment = SegmentConfidence(
            block_id="entity.AttackBehavior",
            confidence=0.87,
            review_flag=False,
            confidence_reasons=["High agreement (3/3)", "Schema validation passed"],
            candidate_count=3,
            agreement_score=1.0,
            assertion_pass_rate=0.9,
        )

        result = segment.to_dict()

        assert result["block_id"] == "entity.AttackBehavior"
        assert result["confidence"] == 0.87
        assert result["review_flag"] is False
        assert result["confidence_level"] == "high"
        assert len(result["confidence_reasons"]) == 2

    def test_confidence_bounded_to_0_1(self):
        """Test confidence is bounded between 0 and 1."""
        segment_high = SegmentConfidence(
            block_id="test",
            confidence=1.5,
            review_flag=False,
        )
        assert segment_high.confidence == 1.0

        segment_low = SegmentConfidence(
            block_id="test",
            confidence=-0.5,
            review_flag=True,
        )
        assert segment_low.confidence == 0.0


class TestConfidenceDistribution:
    """Test suite for ConfidenceDistribution model."""

    def test_confidence_distribution_empty(self):
        """Test empty distribution."""
        dist = ConfidenceDistribution()

        assert dist.high_confidence_pct == 0.0
        assert dist.soft_flag_pct == 0.0
        assert dist.hard_flag_pct == 0.0
        assert dist.total_segments == 0

    def test_confidence_distribution_percentages(self):
        """Test percentage calculations."""
        dist = ConfidenceDistribution(
            high_confidence_count=7,
            soft_flag_count=2,
            hard_flag_count=1,
            total_segments=10,
        )

        assert dist.high_confidence_pct == 70.0
        assert dist.soft_flag_pct == 20.0
        assert dist.hard_flag_pct == 10.0

    def test_confidence_distribution_histogram(self):
        """Test histogram output."""
        dist = ConfidenceDistribution(
            high_confidence_count=5,
            soft_flag_count=3,
            hard_flag_count=2,
            total_segments=10,
        )

        hist = dist.to_histogram()

        assert hist["high_confidence"] == 50.0
        assert hist["soft_flag"] == 30.0
        assert hist["hard_flag"] == 20.0

    def test_confidence_distribution_zero_total(self):
        """Test distribution with zero total segments."""
        dist = ConfidenceDistribution(
            high_confidence_count=0,
            soft_flag_count=0,
            hard_flag_count=0,
            total_segments=0,
        )

        assert dist.high_confidence_pct == 0.0
        assert dist.soft_flag_pct == 0.0
        assert dist.hard_flag_pct == 0.0


class TestConfidenceLevel:
    """Test suite for ConfidenceLevel enum."""

    def test_confidence_level_from_score_high(self):
        """Test high confidence classification."""
        assert ConfidenceLevel.from_score(0.80) == ConfidenceLevel.HIGH
        assert ConfidenceLevel.from_score(0.95) == ConfidenceLevel.HIGH
        assert ConfidenceLevel.from_score(1.0) == ConfidenceLevel.HIGH

    def test_confidence_level_from_score_soft(self):
        """Test soft flag classification."""
        assert ConfidenceLevel.from_score(0.79) == ConfidenceLevel.SOFT_FLAG
        assert ConfidenceLevel.from_score(0.60) == ConfidenceLevel.SOFT_FLAG
        assert ConfidenceLevel.from_score(0.65) == ConfidenceLevel.SOFT_FLAG

    def test_confidence_level_from_score_hard(self):
        """Test hard flag classification."""
        assert ConfidenceLevel.from_score(0.59) == ConfidenceLevel.HARD_FLAG
        assert ConfidenceLevel.from_score(0.30) == ConfidenceLevel.HARD_FLAG
        assert ConfidenceLevel.from_score(0.0) == ConfidenceLevel.HARD_FLAG


class TestEdgeCases:
    """Test edge cases for conformal scoring."""

    def test_empty_assertion_results(self):
        """Test candidate with empty assertion results."""
        scorer = ConformalScorer()
        candidate = CandidateResult(
            candidate_id=0,
            code="test",
            assertion_results=[],
            semantic_score=0.5,
        )

        result = scorer.score_segment("block", [candidate])

        assert result.assertion_pass_rate == 0.0

    def test_all_assertions_fail(self):
        """Test candidate with all failing assertions."""
        scorer = ConformalScorer()
        candidates = [
            CandidateResult(
                candidate_id=i,
                code=f"code_{i}",
                assertion_results=[False, False, False],
                semantic_score=0.2,
            )
            for i in range(3)
        ]

        result = scorer.score_segment("block", candidates)

        assert result.assertion_pass_rate == 0.0
        assert result.is_hard_flag

    def test_identical_candidates_different_normalized(self):
        """Test that structurally identical but textually different code is handled."""
        scorer = ConformalScorer()
        candidates = [
            CandidateResult(
                candidate_id=0,
                code="function test() { return 1; }",
                assertion_results=[True],
            ),
            CandidateResult(
                candidate_id=1,
                code="function test(){return 1;}",
                assertion_results=[True],
            ),
        ]

        result = scorer.score_segment("block", candidates)

        assert result.agreement_score > 0.0

    def test_weights_sum_not_one(self):
        """Test that weights don't need to sum to 1."""
        scorer = ConformalScorer(agreement_weight=0.3, assertion_weight=0.3)

        assert scorer.agreement_weight == 0.3
        assert scorer.assertion_weight == 0.3
