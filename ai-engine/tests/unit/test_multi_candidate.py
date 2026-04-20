"""
Tests for Multi-Candidate Consistency Checker (DPC-Style)
"""

import pytest
from qa.multi_candidate import (
    MultiCandidateConsistencyChecker,
    CandidateGenerator,
    ConversionCandidate,
    ConsistencyResult,
    CandidateConfig,
    SelectionStrategy,
    create_candidate_result,
    dpc_consistency_check,
)


class TestConversionCandidate:
    """Tests for ConversionCandidate dataclass."""

    def test_create_candidate(self):
        """Test basic candidate creation."""
        cand = ConversionCandidate(candidate_id=0, code="test code")
        assert cand.candidate_id == 0
        assert cand.code == "test code"
        assert cand.temperature == 0.3
        assert cand.prompt_suffix == ""

    def test_get_fingerprint(self):
        """Test fingerprint generation."""
        cand = ConversionCandidate(candidate_id=0, code="test code")
        fp = cand.get_fingerprint()
        assert isinstance(fp, str)
        assert len(fp) == 16

    def test_fingerprint_normalization(self):
        """Test that fingerprints normalize code properly."""
        cand1 = ConversionCandidate(candidate_id=0, code="test_code")
        cand2 = ConversionCandidate(candidate_id=1, code="TESTCODE")
        cand3 = ConversionCandidate(candidate_id=2, code="test-code")

        assert cand1.get_fingerprint() == cand2.get_fingerprint()
        assert cand2.get_fingerprint() == cand3.get_fingerprint()

    def test_fingerprint_different_content(self):
        """Test that different code produces different fingerprints."""
        cand1 = ConversionCandidate(candidate_id=0, code="code_a")
        cand2 = ConversionCandidate(candidate_id=1, code="code_b")

        assert cand1.get_fingerprint() != cand2.get_fingerprint()


class TestMultiCandidateConsistencyChecker:
    """Tests for MultiCandidateConsistencyChecker."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = CandidateConfig(
            candidate_count=3,
            agreement_threshold=0.7,
            selection_strategy=SelectionStrategy.DPC_CONSISTENCY,
        )
        self.checker = MultiCandidateConsistencyChecker(self.config)

    def test_generate_candidate_configs(self):
        """Test candidate config generation."""
        configs = self.checker.generate_candidate_configs()
        assert len(configs) == 3
        assert all("candidate_id" in c for c in configs)
        assert all("temperature" in c for c in configs)
        assert all("prompt_suffix" in c for c in configs)

    def test_generate_candidate_configs_single(self):
        """Test config generation with single candidate."""
        config = CandidateConfig(candidate_count=1)
        checker = MultiCandidateConsistencyChecker(config)
        configs = checker.generate_candidate_configs()
        assert len(configs) == 1

    def test_compute_pairwise_agreement(self):
        """Test pairwise agreement matrix computation."""
        candidates = [
            ConversionCandidate(candidate_id=0, code="same_code"),
            ConversionCandidate(candidate_id=1, code="same_code"),
            ConversionCandidate(candidate_id=2, code="same_code"),
        ]

        matrix = self.checker.compute_pairwise_agreement(candidates)
        assert len(matrix) == 3
        assert all(len(row) == 3 for row in matrix)
        assert matrix[0][0] == 1.0
        assert matrix[0][1] == 1.0

    def test_compute_agreement_scores_all_same(self):
        """Test agreement scores when all candidates are same."""
        candidates = [
            ConversionCandidate(candidate_id=0, code="same_code"),
            ConversionCandidate(candidate_id=1, code="same_code"),
            ConversionCandidate(candidate_id=2, code="same_code"),
        ]

        scores = self.checker.compute_agreement_scores(candidates)
        assert len(scores) == 3
        assert all(s == 1.0 for s in scores)

    def test_compute_agreement_scores_all_different(self):
        """Test agreement scores when all candidates are different."""
        candidates = [
            ConversionCandidate(candidate_id=0, code="code_a"),
            ConversionCandidate(candidate_id=1, code="code_b"),
            ConversionCandidate(candidate_id=2, code="code_c"),
        ]

        scores = self.checker.compute_agreement_scores(candidates)
        assert len(scores) == 3
        assert all(s < 1.0 for s in scores)

    def test_rank_candidates(self):
        """Test candidate ranking."""
        candidates = [
            ConversionCandidate(candidate_id=0, code="code_a"),
            ConversionCandidate(candidate_id=1, code="same_code"),
            ConversionCandidate(candidate_id=2, code="same_code"),
        ]

        rankings = self.checker.rank_candidates(candidates)
        assert len(rankings) == 3
        assert rankings[0][0] == 1
        assert rankings[0][1] >= rankings[1][1]

    def test_find_consensus_code_all_same(self):
        """Test consensus finding when all candidates agree."""
        candidates = [
            ConversionCandidate(candidate_id=0, code="same"),
            ConversionCandidate(candidate_id=1, code="same"),
            ConversionCandidate(candidate_id=2, code="same"),
        ]

        code, rate = self.checker.find_consensus_code(candidates)
        assert code == "same"
        assert rate == 1.0

    def test_find_consensus_code_majority(self):
        """Test consensus with majority agreement."""
        candidates = [
            ConversionCandidate(candidate_id=0, code="majority"),
            ConversionCandidate(candidate_id=1, code="majority"),
            ConversionCandidate(candidate_id=2, code="different"),
        ]

        code, rate = self.checker.find_consensus_code(candidates)
        assert code == "majority"
        assert rate == 2 / 3

    def test_check_consistency_all_agree(self):
        """Test consistency check when all candidates agree."""
        candidates = [
            ConversionCandidate(candidate_id=0, code="all_same"),
            ConversionCandidate(candidate_id=1, code="all_same"),
            ConversionCandidate(candidate_id=2, code="all_same"),
        ]

        result = self.checker.check_consistency(candidates)
        assert result.selected_candidate is not None
        assert result.agreement_score == 1.0
        assert len(result.flagged_candidates) == 0
        assert result.needs_review is False

    def test_check_consistency_with_disagreement(self):
        """Test consistency check with disagreeing candidates."""
        candidates = [
            ConversionCandidate(candidate_id=0, code="code_a"),
            ConversionCandidate(candidate_id=1, code="code_b"),
            ConversionCandidate(candidate_id=2, code="code_c"),
        ]

        result = self.checker.check_consistency(candidates)
        assert len(result.flagged_candidates) >= 1
        assert result.needs_review is True
        assert result.agreement_score < 1.0

    def test_check_consistency_single_candidate(self):
        """Test consistency check with single candidate."""
        candidates = [ConversionCandidate(candidate_id=0, code="single")]

        result = self.checker.check_consistency(candidates)
        assert result.selected_candidate == candidates[0]
        assert result.agreement_score == 1.0
        assert len(result.flagged_candidates) == 0

    def test_select_best_candidate_dpc(self):
        """Test DPC selection strategy."""
        candidates = [
            ConversionCandidate(candidate_id=0, code="code_a"),
            ConversionCandidate(candidate_id=1, code="same"),
            ConversionCandidate(candidate_id=2, code="same"),
        ]

        selected, result = self.checker.select_best_candidate(
            candidates, SelectionStrategy.DPC_CONSISTENCY
        )
        assert selected is not None
        assert selected.candidate_id in [1, 2]

    def test_select_best_candidate_majority(self):
        """Test majority vote selection."""
        candidates = [
            ConversionCandidate(candidate_id=0, code="majority"),
            ConversionCandidate(candidate_id=1, code="majority"),
            ConversionCandidate(candidate_id=2, code="different"),
        ]

        selected, result = self.checker.select_best_candidate(
            candidates, SelectionStrategy.MAJORITY_VOTE
        )
        assert selected is not None
        assert selected.code == "majority"


class TestConsistencyResult:
    """Tests for ConsistencyResult dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = ConsistencyResult(
            selected_candidate=ConversionCandidate(candidate_id=0, code="test"),
            agreement_score=0.85,
            candidate_rankings=[(0, 0.9), (1, 0.8), (2, 0.7)],
            flagged_candidates=[2],
            consensus_code="test",
            confidence=0.75,
            needs_review=True,
        )

        d = result.to_dict()
        assert d["selected_candidate_id"] == 0
        assert d["agreement_score"] == 0.85
        assert d["flagged_candidates"] == [2]
        assert d["needs_review"] is True


class TestCandidateGenerator:
    """Tests for CandidateGenerator."""

    def test_create_candidate(self):
        """Test candidate creation helper."""
        gen = CandidateGenerator()
        cand = gen.create_candidate(
            candidate_id=1, code="test", temperature=0.4, prompt_suffix="test suffix"
        )
        assert cand.candidate_id == 1
        assert cand.code == "test"
        assert cand.temperature == 0.4
        assert cand.prompt_suffix == "test suffix"

    def test_generate_candidates(self):
        """Test candidate generation with mock conversion function."""
        gen = CandidateGenerator()

        def mock_convert(java_code: str, config: dict) -> str:
            return f"bedrock_{java_code}"

        candidates = gen.generate_candidates(
            segment_id="test_seg", conversion_func=mock_convert, java_segment="java_code"
        )
        assert len(candidates) == 3
        assert all("bedrock_" in c.code for c in candidates)


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_create_candidate_result(self):
        """Test helper function."""
        cand = create_candidate_result(candidate_id=5, code="test_code")
        assert cand.candidate_id == 5
        assert cand.code == "test_code"

    def test_dpc_consistency_check(self):
        """Test DPC convenience function."""
        candidates = [
            ConversionCandidate(candidate_id=0, code="same"),
            ConversionCandidate(candidate_id=1, code="same"),
            ConversionCandidate(candidate_id=2, code="different"),
        ]

        result = dpc_consistency_check(candidates, agreement_threshold=0.7)
        assert isinstance(result, ConsistencyResult)
        assert result.selected_candidate is not None
        assert len(result.flagged_candidates) >= 1


class TestEdgeCases:
    """Tests for edge cases."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = CandidateConfig(
            candidate_count=3,
            agreement_threshold=0.7,
            selection_strategy=SelectionStrategy.DPC_CONSISTENCY,
        )
        self.checker = MultiCandidateConsistencyChecker(self.config)

    def test_empty_candidates(self):
        """Test handling of empty candidate list."""
        checker = MultiCandidateConsistencyChecker()
        result = checker.check_consistency([])
        assert result.selected_candidate is None
        assert result.agreement_score == 1.0

    def test_two_candidates_partial_agreement(self):
        """Test with two candidates having partial agreement."""
        candidates = [
            ConversionCandidate(candidate_id=0, code="aaaa"),
            ConversionCandidate(candidate_id=1, code="bbbb"),
        ]

        result = self.checker.check_consistency(candidates)
        assert result.selected_candidate is not None
        assert result.agreement_score < 1.0

    def test_whitespace_differences_normalized(self):
        """Test that whitespace differences are normalized."""
        candidates = [
            ConversionCandidate(candidate_id=0, code="code with spaces"),
            ConversionCandidate(candidate_id=1, code="code withspaces"),
            ConversionCandidate(candidate_id=2, code="codewith spaces"),
        ]

        scores = self.checker.compute_agreement_scores(candidates)
        assert all(s == 1.0 for s in scores)

    def test_low_agreement_threshold(self):
        """Test with low agreement threshold."""
        config = CandidateConfig(agreement_threshold=0.5)
        checker = MultiCandidateConsistencyChecker(config)
        candidates = [
            ConversionCandidate(candidate_id=0, code="same"),
            ConversionCandidate(candidate_id=1, code="same"),
            ConversionCandidate(candidate_id=2, code="different"),
        ]

        result = checker.check_consistency(candidates)
        assert result.selected_candidate is not None
        assert len(result.candidate_rankings) == 3

    def test_high_agreement_threshold(self):
        """Test with very high agreement threshold."""
        config = CandidateConfig(agreement_threshold=0.95)
        checker = MultiCandidateConsistencyChecker(config)
        candidates = [
            ConversionCandidate(candidate_id=0, code="aaaa"),
            ConversionCandidate(candidate_id=1, code="bbbb"),
            ConversionCandidate(candidate_id=2, code="cccc"),
        ]

        result = checker.check_consistency(candidates)
        assert len(result.flagged_candidates) == 3
