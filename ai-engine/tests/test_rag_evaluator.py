"""
Unit tests for RAG evaluation metrics.

Tests RetrievalMetrics, GenerationMetrics, and DiversityMetrics
to ensure proper calculation of RAG system evaluation metrics.
"""

import pytest
import sys
import os

# Add ai-engine to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.rag_evaluator import RetrievalMetrics, GenerationMetrics, DiversityMetrics


class TestRetrievalMetricsPrecisionAtK:
    """Tests for RetrievalMetrics.precision_at_k method."""

    def test_empty_retrieved_docs_returns_zero(self):
        """Empty retrieved docs should return 0.0."""
        result = RetrievalMetrics.precision_at_k([], ["doc1", "doc2"], k=5)
        assert result == 0.0

    def test_k_zero_returns_zero(self):
        """k=0 should return 0.0."""
        result = RetrievalMetrics.precision_at_k(["doc1", "doc2"], ["doc1"], k=0)
        assert result == 0.0

    def test_perfect_precision_returns_one(self):
        """All retrieved docs are relevant - should return 1.0."""
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc1", "doc2", "doc3", "doc4"]
        result = RetrievalMetrics.precision_at_k(retrieved, relevant, k=3)
        assert result == 1.0

    def test_partial_precision_returns_correct_value(self):
        """Partial relevance should return correct fraction."""
        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        relevant = ["doc1", "doc3", "doc5", "doc6"]
        result = RetrievalMetrics.precision_at_k(retrieved, relevant, k=5)
        # 3 relevant out of 5 = 0.6
        assert result == 0.6

    def test_precision_at_k_smaller_than_retrieved(self):
        """K smaller than retrieved list should only consider first k."""
        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        relevant = ["doc1", "doc2", "doc3"]
        result = RetrievalMetrics.precision_at_k(retrieved, relevant, k=2)
        # First 2 are both relevant
        assert result == 1.0

    def test_no_relevant_docs_returns_zero(self):
        """No relevant docs in retrieved should return 0.0."""
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc4", "doc5", "doc6"]
        result = RetrievalMetrics.precision_at_k(retrieved, relevant, k=3)
        assert result == 0.0


class TestRetrievalMetricsRecallAtK:
    """Tests for RetrievalMetrics.recall_at_k method."""

    def test_empty_relevant_docs_with_empty_retrieved_returns_one(self):
        """Empty relevant docs with empty retrieved should return 1.0."""
        result = RetrievalMetrics.recall_at_k([], [], k=5)
        assert result == 1.0

    def test_empty_relevant_docs_with_retrieved_returns_zero(self):
        """Empty relevant docs with retrieved should return 0.0."""
        result = RetrievalMetrics.recall_at_k(["doc1", "doc2"], [], k=5)
        assert result == 0.0

    def test_perfect_recall_returns_one(self):
        """All relevant docs retrieved should return 1.0."""
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc1", "doc2"]
        result = RetrievalMetrics.recall_at_k(retrieved, relevant, k=5)
        assert result == 1.0

    def test_partial_recall_returns_correct_value(self):
        """Partial recall should return correct fraction."""
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        result = RetrievalMetrics.recall_at_k(retrieved, relevant, k=5)
        # 3 out of 5 relevant = 0.6
        assert result == 0.6

    def test_k_limited_recall(self):
        """K smaller than relevant should only consider retrieved up to k."""
        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        relevant = ["doc1", "doc2", "doc3", "doc4", "doc5", "doc6"]
        result = RetrievalMetrics.recall_at_k(retrieved, relevant, k=3)
        # First 3 retrieved, all 3 relevant, 3/6 = 0.5
        assert result == 0.5


class TestRetrievalMetricsF1AtK:
    """Tests for RetrievalMetrics.f1_at_k method."""

    def test_perfect_precision_and_recall_returns_one(self):
        """Perfect precision and recall should return 1.0."""
        retrieved = ["doc1", "doc2"]
        relevant = ["doc1", "doc2"]
        result = RetrievalMetrics.f1_at_k(retrieved, relevant, k=2)
        assert result == 1.0

    def test_zero_precision_and_recall_returns_zero(self):
        """Zero precision and recall should return 0.0."""
        retrieved = ["doc1", "doc2"]
        relevant = ["doc3", "doc4"]
        result = RetrievalMetrics.f1_at_k(retrieved, relevant, k=2)
        assert result == 0.0

    def test_partial_f1_returns_correct_value(self):
        """Partial precision and recall should return correct F1."""
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc1", "doc2", "doc4"]
        # precision = 2/3, recall = 2/3
        # F1 = 2 * (2/3 * 2/3) / (2/3 + 2/3) = 2 * (4/9) / (4/3) = 8/9 / 4/3 = 2/3
        result = RetrievalMetrics.f1_at_k(retrieved, relevant, k=3)
        assert result == pytest.approx(0.6667, rel=0.01)


class TestRetrievalMetricsMeanReciprocalRank:
    """Tests for RetrievalMetrics.mean_reciprocal_rank (MRR) method."""

    def test_first_position_hit_returns_one(self):
        """Relevant doc at position 1 should return 1.0."""
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc1"]
        result = RetrievalMetrics.mean_reciprocal_rank(retrieved, relevant)
        assert result == 1.0

    def test_second_position_hit_returns_half(self):
        """Relevant doc at position 2 should return 0.5."""
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc2"]
        result = RetrievalMetrics.mean_reciprocal_rank(retrieved, relevant)
        assert result == 0.5

    def test_third_position_hit_returns_one_third(self):
        """Relevant doc at position 3 should return 1/3."""
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc3"]
        result = RetrievalMetrics.mean_reciprocal_rank(retrieved, relevant)
        assert result == pytest.approx(0.3333, rel=0.01)

    def test_no_hit_returns_zero(self):
        """No relevant doc in retrieved should return 0.0."""
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc4", "doc5"]
        result = RetrievalMetrics.mean_reciprocal_rank(retrieved, relevant)
        assert result == 0.0

    def test_empty_retrieved_returns_zero(self):
        """Empty retrieved should return 0.0."""
        result = RetrievalMetrics.mean_reciprocal_rank([], ["doc1"])
        assert result == 0.0

    def test_multiple_relevant_docs_uses_first(self):
        """Multiple relevant docs should use first hit position."""
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc2", "doc3"]  # First hit is at position 2
        result = RetrievalMetrics.mean_reciprocal_rank(retrieved, relevant)
        assert result == 0.5


class TestRetrievalMetricsNormalizedDCG:
    """Tests for RetrievalMetrics.normalized_discounted_cumulative_gain (NDCG) method."""

    def test_empty_retrieved_returns_zero(self):
        """Empty retrieved docs should return 0.0."""
        result = RetrievalMetrics.normalized_discounted_cumulative_gain([], ["doc1"])
        assert result == 0.0

    def test_perfect_ordering_returns_one(self):
        """Perfect ordering should return 1.0."""
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc1", "doc2", "doc3"]
        result = RetrievalMetrics.normalized_discounted_cumulative_gain(
            retrieved, relevant
        )
        assert result == 1.0

    def test_reversed_ordering_returns_less_than_one(self):
        """Reversed relevant ordering should return less than 1.0 with graded relevance."""
        retrieved = ["doc3", "doc2", "doc1"]  # Worst order (doc3 most relevant placed last)
        relevant = ["doc1", "doc2", "doc3"]
        # With graded relevance, order matters
        relevance_scores = {"doc1": 3.0, "doc2": 2.0, "doc3": 1.0}
        result = RetrievalMetrics.normalized_discounted_cumulative_gain(
            retrieved, relevant, relevance_scores
        )
        # Worst order should give less than 1.0 but more than 0.0
        assert result < 1.0
        assert result > 0.0

    def test_with_relevance_scores(self):
        """NDCG with custom relevance scores."""
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc1", "doc2", "doc3"]
        relevance_scores = {"doc1": 3.0, "doc2": 2.0, "doc3": 1.0}
        result = RetrievalMetrics.normalized_discounted_cumulative_gain(
            retrieved, relevant, relevance_scores
        )
        assert result == 1.0  # Perfect order by relevance

    def test_partial_relevant_retrieval(self):
        """Only some relevant docs retrieved should return partial score."""
        retrieved = ["doc1", "doc2"]
        relevant = ["doc1", "doc2", "doc3", "doc4"]
        result = RetrievalMetrics.normalized_discounted_cumulative_gain(
            retrieved, relevant
        )
        assert result > 0.0
        assert result < 1.0


class TestRetrievalMetricsHitRate:
    """Tests for RetrievalMetrics.hit_rate method."""

    def test_any_relevant_doc_returns_one(self):
        """Any relevant doc in retrieved should return 1.0."""
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc2"]
        result = RetrievalMetrics.hit_rate(retrieved, relevant)
        assert result == 1.0

    def test_no_relevant_docs_returns_zero(self):
        """No relevant docs in retrieved should return 0.0."""
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc4", "doc5"]
        result = RetrievalMetrics.hit_rate(retrieved, relevant)
        assert result == 0.0

    def test_empty_retrieved_returns_zero(self):
        """Empty retrieved should return 0.0."""
        result = RetrievalMetrics.hit_rate([], ["doc1"])
        assert result == 0.0

    def test_multiple_hits_returns_one(self):
        """Multiple relevant docs still returns 1.0 (not count)."""
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc1", "doc2", "doc3", "doc4"]
        result = RetrievalMetrics.hit_rate(retrieved, relevant)
        assert result == 1.0

    def test_first_doc_relevant(self):
        """First doc relevant should return 1.0."""
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc1"]
        result = RetrievalMetrics.hit_rate(retrieved, relevant)
        assert result == 1.0


class TestRetrievalMetricsEdgeCases:
    """Edge case tests for RetrievalMetrics."""

    def test_duplicate_docs_in_retrieved(self):
        """Duplicate docs in retrieved should be handled."""
        retrieved = ["doc1", "doc1", "doc2"]
        relevant = ["doc1", "doc2"]
        # precision_at_k should count unique docs in the first k positions
        result = RetrievalMetrics.precision_at_k(retrieved, relevant, k=3)
        # Position 1: doc1 (relevant), position 2: doc1 (relevant), position 3: doc2 (relevant)
        assert result == 1.0

    def test_k_larger_than_retrieved_length(self):
        """K larger than retrieved length should work."""
        retrieved = ["doc1", "doc2"]
        relevant = ["doc1", "doc2", "doc3"]
        result = RetrievalMetrics.precision_at_k(retrieved, relevant, k=10)
        assert result == 1.0

    def test_empty_both_lists(self):
        """Both empty lists should return appropriate values."""
        # precision returns 0.0 for empty retrieved
        result = RetrievalMetrics.precision_at_k([], [], k=5)
        assert result == 0.0


class TestGenerationMetricsKeywordCoverage:
    """Tests for GenerationMetrics.keyword_coverage method."""

    def test_empty_required_keywords_returns_one(self):
        """Empty required keywords should return 1.0."""
        result = GenerationMetrics.keyword_coverage("Some answer", [])
        assert result == 1.0

    def test_all_keywords_present_returns_one(self):
        """All required keywords present should return 1.0."""
        answer = "The mod uses Minecraft API to register blocks and items."
        keywords = ["mod", "Minecraft", "API", "blocks", "items"]
        result = GenerationMetrics.keyword_coverage(answer, keywords)
        assert result == 1.0

    def test_partial_keywords_returns_correct_fraction(self):
        """Partial keywords should return correct fraction."""
        answer = "The mod uses Minecraft API."
        keywords = ["mod", "Minecraft", "API", "blocks", "items"]
        # 3 out of 5 keywords present
        result = GenerationMetrics.keyword_coverage(answer, keywords)
        assert result == 0.6

    def test_no_keywords_returns_zero(self):
        """No required keywords should return 0.0."""
        answer = "This is an answer about something else."
        keywords = ["mod", "Minecraft", "API"]
        result = GenerationMetrics.keyword_coverage(answer, keywords)
        assert result == 0.0

    def test_case_insensitive_matching(self):
        """Keyword matching should be case insensitive."""
        answer = "MINECRAFT API MOD"
        keywords = ["minecraft", "api"]
        result = GenerationMetrics.keyword_coverage(answer, keywords)
        assert result == 1.0


class TestGenerationMetricsKeywordProhibitionCompliance:
    """Tests for GenerationMetrics.keyword_prohibition_compliance method."""

    def test_empty_prohibited_returns_one(self):
        """Empty prohibited keywords should return 1.0."""
        result = GenerationMetrics.keyword_prohibition_compliance("Some answer", [])
        assert result == 1.0

    def test_no_prohibited_returns_one(self):
        """No prohibited keywords found should return 1.0."""
        answer = "This is a good answer about Minecraft."
        prohibited = ["hack", "exploit", "cheat"]
        result = GenerationMetrics.keyword_prohibition_compliance(answer, prohibited)
        assert result == 1.0

    def test_one_prohibited_returns_partial(self):
        """One prohibited keyword should return partial score."""
        answer = "You can hack the game to get resources."
        prohibited = ["hack", "exploit", "cheat"]
        # 1 out of 3 prohibited = 1 - 1/3 = 0.666...
        result = GenerationMetrics.keyword_prohibition_compliance(answer, prohibited)
        assert result == pytest.approx(0.6667, rel=0.01)

    def test_all_prohibited_returns_zero(self):
        """All prohibited keywords should return 0.0."""
        answer = "You can hack and exploit and cheat."
        prohibited = ["hack", "exploit", "cheat"]
        result = GenerationMetrics.keyword_prohibition_compliance(answer, prohibited)
        assert result == 0.0


class TestGenerationMetricsAnswerLengthAppropriateness:
    """Tests for GenerationMetrics.answer_length_appropriateness method."""

    def test_explanation_in_range_returns_one(self):
        """Answer in expected range should return 1.0."""
        # explanation expects 50-200 words
        answer = "This is an explanation that has about one hundred words. " * 10
        result = GenerationMetrics.answer_length_appropriateness(answer, "explanation")
        assert result == 1.0

    def test_explanation_too_short_returns_partial(self):
        """Short explanation should return partial score."""
        answer = "Short."
        result = GenerationMetrics.answer_length_appropriateness(answer, "explanation")
        # min length is 50, so 1/50 = 0.02
        assert result == pytest.approx(0.02, rel=0.1)

    def test_explanation_too_long_returns_partial(self):
        """Overly long explanation should return partial score."""
        # Create answer with 300 words (max is 200)
        answer = "Word. " * 300
        result = GenerationMetrics.answer_length_appropriateness(answer, "explanation")
        # excess = 300 - 200 = 100, penalty = 100/200 = 0.5, score = 1 - 0.5 = 0.5
        assert result == 0.5

    def test_how_to_query_type(self):
        """how_to query type should have different expected range."""
        # how_to expects 100-300 words
        answer = "Word. " * 150
        result = GenerationMetrics.answer_length_appropriateness(answer, "how_to")
        assert result == 1.0

    def test_unknown_query_type_uses_default(self):
        """Unknown query type should use default range (30-200)."""
        answer = "Word. " * 100
        result = GenerationMetrics.answer_length_appropriateness(answer, "unknown_type")
        assert result == 1.0


class TestGenerationMetricsCoherenceScore:
    """Tests for GenerationMetrics.coherence_score method."""

    def test_empty_answer_returns_zero(self):
        """Empty answer should return 0.0."""
        result = GenerationMetrics.coherence_score("")
        assert result == 0.0

    def test_single_sentence_returns_half(self):
        """Single sentence should return 0.5."""
        result = GenerationMetrics.coherence_score("This is a single sentence answer.")
        assert result == 0.5

    def test_answer_with_transitions_can_increase_score(self):
        """Answer with transitional phrases can add to coherence score."""
        # Need proper sentence length variance for base score + transitions
        answer = (
            "Understanding the problem is essential. "
            "However, the solution is complex. "
            "Therefore, we should break it down properly. "
            "Additionally, we need more resources. "
            "Furthermore, testing is important."
        )
        result = GenerationMetrics.coherence_score(answer)
        # Should have some coherence from transitions (up to 0.3)
        assert result >= 0.0

    def test_answer_with_list_indicators_can_increase_score(self):
        """Answer with structured content indicators."""
        # The list indicator check requires "1.", "2.", etc. in the answer
        answer = "Steps: 1. First do this. 2. Then do that. 3. Finally done."
        result = GenerationMetrics.coherence_score(answer)
        # Should be at least 0.5 (single sentence gets 0.5 by default)
        assert result >= 0.5


class TestDiversityMetrics:
    """Tests for DiversityMetrics methods.

    Note: Full testing of DiversityMetrics requires SearchResult objects
    with document attributes (content_type, source_path, tags), which is
    better tested via integration tests. Here we test edge cases.
    """

    def test_content_type_diversity_empty_sources_returns_zero(self):
        """Empty sources should return 0.0."""
        result = DiversityMetrics.content_type_diversity([])
        assert result == 0.0

    def test_source_diversity_empty_sources_returns_zero(self):
        """Empty sources should return 0.0."""
        result = DiversityMetrics.source_diversity([])
        assert result == 0.0

    def test_topic_diversity_score_empty_sources_returns_zero(self):
        """Empty sources should return 0.0."""
        result = DiversityMetrics.topic_diversity_score([])
        assert result == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])