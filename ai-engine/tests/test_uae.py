"""
Tests for UAE (Utility-Aligned Embeddings) module.

Tests the utility label calculation, contrastive loss, and benchmarking
functionality for the UAE retriever.
"""

import numpy as np
from utils.uae_utils import (
    UtilityLabel,
    UtilityLabelCalculator,
    ContrastiveUtilityLoss,
    UAETrainingPair,
    RetrievalBenchmarker,
    normalize_utility_scores,
    UtilitySignal,
)


class TestUtilityLabelCalculator:
    """Tests for utility label calculation."""

    def test_calculate_from_successful_conversion(self):
        """Test utility labels from successful conversion."""
        calculator = UtilityLabelCalculator()
        
        query = "register entity with custom AI goal"
        retrieved_docs = ["doc1", "doc2", "doc3"]
        output = "Using script with EntityAI goal definition"
        successful = True
        
        labels = calculator.calculate_from_conversion_history(
            query=query,
            retrieved_doc_ids=retrieved_docs,
            conversion_output=output,
            conversion_successful=successful,
        )
        
        assert len(labels) == 3
        assert all(label.utility_score >= 0 for label in labels)

    def test_calculate_from_failed_conversion(self):
        """Test utility labels from failed conversion."""
        calculator = UtilityLabelCalculator()
        
        query = "test query"
        retrieved_docs = ["doc1", "doc2"]
        output = ""
        successful = False
        
        labels = calculator.calculate_from_conversion_history(
            query=query,
            retrieved_doc_ids=retrieved_docs,
            conversion_output=output,
            conversion_successful=successful,
        )
        
        assert len(labels) == 2
        assert all(label.utility_score < 0 for label in labels)
        assert all(label.signal_source == UtilitySignal.VALIDATION_FAIL for label in labels)

    def test_calculate_from_llm_perplexity(self):
        """Test utility based on LLM perplexity."""
        calculator = UtilityLabelCalculator()
        
        query = "test query"
        doc_content = "Some document content"
        perplexity_score = 0.2
        
        label = calculator.calculate_from_llm_perplexity(
            query=query,
            doc_content=doc_content,
            perplexity_score=perplexity_score,
        )
        
        assert label.utility_score >= 0.8
        assert label.signal_source == UtilitySignal.LLM_PERPLEXITY


class TestContrastiveUtilityLoss:
    """Tests for utility-weighted contrastive loss."""

    def test_compute_loss_with_valid_embeddings(self):
        """Test loss computation with valid embeddings."""
        loss_fn = ContrastiveUtilityLoss(margin=0.5, temperature=0.1)
        
        anchor = np.random.randn(384).astype(np.float32)
        anchor = anchor / np.linalg.norm(anchor)
        
        positive = [
            np.random.randn(384).astype(np.float32) for _ in range(3)
        ]
        for p in positive:
            p[:] = p / np.linalg.norm(p)
        
        negative = [
            np.random.randn(384).astype(np.float32) for _ in range(2)
        ]
        for n in negative:
            n[:] = n / np.linalg.norm(n)
        
        utility_weights = [0.9, 0.7, 0.5]
        
        loss = loss_fn.compute(
            anchor_embedding=anchor,
            positive_embeddings=positive,
            negative_embeddings=negative,
            utility_weights=utility_weights,
        )
        
        assert loss >= 0

    def test_compute_loss_with_empty_positives(self):
        """Test loss with empty positive list."""
        loss_fn = ContrastiveUtilityLoss()
        
        anchor = np.random.randn(384).astype(np.float32)
        negative = [np.random.randn(384).astype(np.float32)]
        
        loss = loss_fn.compute(
            anchor_embedding=anchor,
            positive_embeddings=[],
            negative_embeddings=negative,
            utility_weights=[],
        )
        
        assert loss == 0.0

    def test_compute_loss_with_empty_negatives(self):
        """Test loss with empty negative list."""
        loss_fn = ContrastiveUtilityLoss()
        
        anchor = np.random.randn(384).astype(np.float32)
        positive = [np.random.randn(384).astype(np.float32)]
        
        loss = loss_fn.compute(
            anchor_embedding=anchor,
            positive_embeddings=positive,
            negative_embeddings=[],
            utility_weights=[1.0],
        )
        
        assert loss == 0.0


class TestRetrievalBenchmarker:
    """Tests for retrieval benchmarking."""

    def test_benchmark_precision_recall(self):
        """Test benchmark calculation."""
        benchmarker = RetrievalBenchmarker(k=5)
        
        queries = ["query1", "query2"]
        retrieved = {
            "query1": ["doc1", "doc2", "doc3"],
            "query2": ["doc1", "doc2", "doc4", "doc5"],
        }
        useful = {
            "query1": ["doc1", "doc2"],
            "query2": ["doc2", "doc4"],
        }
        
        result = benchmarker.benchmark(
            queries=queries,
            retrieved_docs_per_query=retrieved,
            useful_docs_per_query=useful,
        )
        
        assert result.total_queries == 2
        assert result.precision_at_k >= 0
        assert result.recall_at_k >= 0
        assert result.mrr >= 0

    def test_benchmark_with_no_useful_docs(self):
        """Test benchmark when there are no useful docs."""
        benchmarker = RetrievalBenchmarker(k=5)
        
        queries = ["query1"]
        retrieved = {"query1": ["doc1", "doc2"]}
        useful = {"query1": []}
        
        result = benchmarker.benchmark(
            queries=queries,
            retrieved_docs_per_query=retrieved,
            useful_docs_per_query=useful,
        )
        
        assert result.total_queries == 1
        assert result.precision_at_k == 0.0

    def test_ndcg_calculation(self):
        """Test NDCG calculation."""
        benchmarker = RetrievalBenchmarker(k=5)
        
        retrieved = {"doc1", "doc2", "doc3"}
        useful = {"doc1", "doc3", "doc5"}
        
        ndcg = benchmarker._ndcg_at_k(retrieved, useful, 5)
        
        assert 0 <= ndcg <= 1.0


class TestNormalizeUtilityScores:
    """Tests for utility score normalization."""

    def test_normalize_utility_scores(self):
        """Test normalization of utility scores."""
        labels = [
            UtilityLabel(
                query_id="q1",
                document_id="d1",
                utility_score=0.0,
                signal_source=UtilitySignal.CORRECT_CONVERSION,
                metadata={},
            ),
            UtilityLabel(
                query_id="q1",
                document_id="d2",
                utility_score=0.5,
                signal_source=UtilitySignal.CORRECT_CONVERSION,
                metadata={},
            ),
            UtilityLabel(
                query_id="q1",
                document_id="d3",
                utility_score=1.0,
                signal_source=UtilitySignal.CORRECT_CONVERSION,
                metadata={},
            ),
        ]
        
        normalized = normalize_utility_scores(labels)
        
        assert normalized[0].utility_score == 0.0
        assert normalized[1].utility_score == 0.5
        assert normalized[2].utility_score == 1.0

    def test_normalize_empty_labels(self):
        """Test normalization with empty labels."""
        normalized = normalize_utility_scores([])
        assert normalized == []


class TestUAETrainingPair:
    """Tests for UAE training pair."""

    def test_training_pair_creation(self):
        """Test training pair creation."""
        pair = UAETrainingPair(
            query="test query",
            positive_docs=["doc1", "doc2"],
            negative_docs=["doc3"],
            utility_labels=[],
        )
        
        assert pair.query == "test query"
        assert len(pair.positive_docs) == 2
        assert len(pair.negative_docs) == 1
        assert pair.query_id != ""

    def test_training_pair_query_id_generation(self):
        """Test that query ID is generated from query hash."""
        pair1 = UAETrainingPair(
            query="same query",
            positive_docs=["doc1"],
            negative_docs=[],
            utility_labels=[],
        )
        pair2 = UAETrainingPair(
            query="same query",
            positive_docs=["doc1"],
            negative_docs=[],
            utility_labels=[],
        )
        
        assert pair1.query_id == pair2.query_id


class TestUtilitySignal:
    """Tests for utility signal enum."""

    def test_utility_signal_values(self):
        """Test utility signal enum values."""
        assert UtilitySignal.CORRECT_CONVERSION.value == "correct_conversion"
        assert UtilitySignal.INCORRECT_CONVERSION.value == "incorrect_conversion"
        assert UtilitySignal.LLM_PERPLEXITY.value == "llm_perplexity"
        assert UtilitySignal.HUMAN_FEEDBACK.value == "human_feedback"


class TestUtilityLabel:
    """Tests for utility label dataclass."""

    def test_is_positive(self):
        """Test positive utility detection."""
        positive_label = UtilityLabel(
            query_id="q1",
            document_id="d1",
            utility_score=0.8,
            signal_source=UtilitySignal.CORRECT_CONVERSION,
            metadata={},
        )
        
        negative_label = UtilityLabel(
            query_id="q1",
            document_id="d2",
            utility_score=0.2,
            signal_source=UtilitySignal.INCORRECT_CONVERSION,
            metadata={},
        )
        
        assert positive_label.is_positive() is True
        assert negative_label.is_positive() is False
