"""
Integration tests for UAE RAG upgrade.

Tests the complete UAE pipeline including:
- Benchmark dataset creation
- Training pipeline
- Integration with ConversionRAGPipeline
- Hallucination tracking
- A/B comparison
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch

from search.bedrock_uae_benchmark import (
    BedrockUAEBenchmarkDataset,
    BedrockDoc,
    EvaluationQuery,
    ConversionHistoryEntry,
    create_bedrock_uae_dataset,
)
from search.uae_training_pipeline import (
    UAETrainingPipeline,
    TrainingConfig,
    TrainingMetrics,
    create_uae_training_pipeline,
    run_quick_benchmark,
)
from search.hallucination_tracker import (
    BedrockComponentHallucinationTracker,
    HallucinatedComponent,
    HallucinationReport,
    create_hallucination_tracker,
)
from utils.uae_utils import (
    UtilityLabel,
    UtilityLabelCalculator,
    ContrastiveUtilityLoss,
    UAETrainingPair,
    RetrievalBenchmarker,
    normalize_utility_scores,
)


class TestBedrockUAEBenchmarkDataset:
    """Tests for the Bedrock UAE benchmark dataset."""

    def test_dataset_creation(self):
        """Test dataset can be created."""
        dataset = BedrockUAEBenchmarkDataset()
        assert dataset is not None
        assert len(dataset.documents) > 0
        assert len(dataset.queries) > 0

    def test_documents_have_required_fields(self):
        """Test all documents have required fields."""
        dataset = BedrockUAEBenchmarkDataset()
        for doc_id, doc in dataset.documents.items():
            assert doc.doc_id == doc_id
            assert doc.title
            assert doc.content
            assert doc.component_type
            assert doc.api_class

    def test_evaluation_queries_have_ground_truth(self):
        """Test evaluation queries have ground truth useful docs."""
        dataset = BedrockUAEBenchmarkDataset()
        for query_id, query in dataset.queries.items():
            assert query.query_id == query_id
            assert query.java_query
            assert len(query.useful_doc_ids) > 0

    def test_conversion_history_has_utility_labels(self):
        """Test conversion history entries have utility info."""
        dataset = BedrockUAEBenchmarkDataset()
        for entry in dataset.conversion_history:
            assert entry.job_id
            assert entry.java_query
            assert len(entry.retrieved_doc_ids) > 0
            assert entry.successful in (True, False)

    def test_factory_function(self):
        """Test factory function creates dataset."""
        dataset = create_bedrock_uae_dataset()
        assert dataset is not None
        assert len(dataset.documents) >= 25

    def test_get_documents_by_type(self):
        """Test filtering documents by component type."""
        dataset = BedrockUAEBenchmarkDataset()
        entity_docs = dataset.get_documents_by_type("entity")
        assert len(entity_docs) > 0
        assert all(doc.component_type == "entity" for doc in entity_docs)

    def test_get_retrieved_docs_for_query(self):
        """Test mock retrieval scores for queries."""
        dataset = BedrockUAEBenchmarkDataset()
        scores = dataset.get_retrieved_docs_for_query("entity AI behavior")
        assert len(scores) > 0
        assert all(0 <= s <= 1 for s in scores.values())


class TestUAETrainingPipeline:
    """Tests for the UAE training pipeline."""

    def test_pipeline_creation(self):
        """Test pipeline can be created."""
        pipeline = UAETrainingPipeline()
        assert pipeline is not None
        assert pipeline.config is not None

    def test_pipeline_with_custom_config(self):
        """Test pipeline with custom configuration."""
        config = TrainingConfig(epochs=5, batch_size=32)
        pipeline = UAETrainingPipeline(config=config)
        assert pipeline.config.epochs == 5
        assert pipeline.config.batch_size == 32

    def test_create_training_pairs_from_history(self):
        """Test creating training pairs from conversion history."""
        pipeline = UAETrainingPipeline()
        history = [
            ConversionHistoryEntry(
                job_id="job_001",
                java_query="register entity AI goal",
                retrieved_doc_ids=["doc1", "doc2", "doc3"],
                output="Used doc1 and doc3",
                successful=True,
                hallucinated_components=[],
                used_doc_ids=["doc1", "doc3"],
            )
        ]

        pairs = pipeline._create_training_pairs_from_history(history)
        assert len(pairs) == 1
        assert pairs[0].query == "register entity AI goal"
        assert "doc1" in pairs[0].positive_docs
        assert "doc2" in pairs[0].negative_docs

    def test_benchmark_retriever(self):
        """Test benchmarking a retriever."""
        pipeline = UAETrainingPipeline()

        with patch.object(pipeline._baseline_engine, "benchmark") as mock_bench:
            mock_bench.return_value = RetrievalBenchmarker(k=5).benchmark(
                queries=["query1", "query2"],
                retrieved_docs_per_query={
                    "query1": ["doc1", "doc2"],
                    "query2": ["doc1", "doc3"],
                },
                useful_docs_per_query={
                    "query1": ["doc1"],
                    "query2": ["doc3"],
                },
            )

            result = pipeline._benchmark_retriever(pipeline._baseline_engine, use_uae=False)
            assert result is not None

    def test_pipeline_is_not_trained_initially(self):
        """Test pipeline is not trained initially."""
        pipeline = UAETrainingPipeline()
        assert pipeline.is_trained() is False
        assert pipeline.get_improvement_metrics() is None

    def test_factory_function(self):
        """Test factory function creates pipeline."""
        import asyncio
        pipeline = asyncio.run(create_uae_training_pipeline())
        assert pipeline is not None


class TestQuickBenchmark:
    """Tests for quick benchmark function."""

    def test_quick_benchmark_runs(self):
        """Test quick benchmark function executes."""
        import asyncio
        result = asyncio.run(run_quick_benchmark())

        assert "baseline" in result
        assert "uae" in result
        assert "improvement_percent" in result
        assert "target_met" in result

        assert result["baseline"]["precision_at_5"] >= 0
        assert result["uae"]["precision_at_5"] >= 0


class TestHallucinationTracker:
    """Tests for hallucination tracker."""

    def test_tracker_creation(self):
        """Test tracker can be created."""
        tracker = BedrockComponentHallucinationTracker()
        assert tracker is not None

    def test_extract_valid_components(self):
        """Test extracting valid components from text."""
        tracker = BedrockComponentHallucinationTracker()
        text = '"minecraft:behavior.nearest_attackable"'
        components = tracker.extract_components_from_text(text)
        assert "minecraft:behavior.nearest_attackable" in components

    def test_is_valid_component(self):
        """Test valid component detection."""
        tracker = BedrockComponentHallucinationTracker()

        assert tracker.is_valid_component("minecraft:behavior.nearest_attackable")
        assert tracker.is_valid_component("minecraft:health")
        assert not tracker.is_valid_component("minecraft:fake_component")
        assert not tracker.is_valid_component("fake:fake")

    def test_detect_hallucinations_in_valid_text(self):
        """Test detection with valid Bedrock code."""
        tracker = BedrockComponentHallucinationTracker()
        text = """
        {
            "minecraft:behavior.nearest_attackable": {
                "priority": 2
            },
            "minecraft:health": {
                "value": 20
            }
        }
        """
        report = tracker.detect_hallucinations(text)
        assert report.hallucinated_count == 0
        assert report.hallucination_rate == 0.0

    def test_detect_hallucinations_with_fake_component(self):
        """Test detection with hallucinated component."""
        tracker = BedrockComponentHallucinationTracker()
        text = '''
        {
            "minecraft:fake_component": {
                "priority": 2
            }
        }
        '''
        report = tracker.detect_hallucinations(text)
        assert report.hallucinated_count >= 1
        assert report.hallucination_rate > 0

    def test_compare_before_after(self):
        """Test comparing hallucination before and after."""
        tracker = BedrockComponentHallucinationTracker()

        before_text = '''
        {
            "minecraft:fake_component": {},
            "minecraft:behavior.nearest_attackable": {}
        }
        '''

        after_text = '''
        {
            "minecraft:behavior.nearest_attackable": {}
        }
        '''

        result = tracker.compare_before_after(before_text, after_text)

        assert "before" in result
        assert "after" in result
        assert "reduction" in result
        assert result["before"]["hallucination_rate"] > 0
        assert result["after"]["hallucination_rate"] == 0

    def test_factory_function(self):
        """Test factory function creates tracker."""
        tracker = create_hallucination_tracker()
        assert tracker is not None

    def test_get_average_hallucination_rate(self):
        """Test getting average hallucination rate."""
        tracker = BedrockComponentHallucinationTracker()

        tracker.detect_hallucinations('{"minecraft:fake": {}}')
        tracker.detect_hallucinations('{"minecraft:fake2": {}}')

        avg_rate = tracker.get_average_hallucination_rate()
        assert avg_rate > 0

    def test_extract_components_from_json(self):
        """Test extracting components from JSON string."""
        tracker = BedrockComponentHallucinationTracker()
        text = '''
        {
            "events": {
                "my_event": {
                    "add": { "component_groups": ["group1"] }
                }
            }
        }
        '''
        components = tracker.extract_components_from_json(text)
        assert "my_event" in components


class TestContrastiveUtilityLoss:
    """Tests for utility-weighted contrastive loss."""

    def test_compute_loss_with_valid_embeddings(self):
        """Test loss computation with valid embeddings."""
        loss_fn = ContrastiveUtilityLoss(margin=0.5, temperature=0.1)

        anchor = np.random.randn(384).astype(np.float32)
        anchor = anchor / np.linalg.norm(anchor)

        positive = [np.random.randn(384).astype(np.float32) for _ in range(2)]
        for p in positive:
            p[:] = p / np.linalg.norm(p)

        negative = [np.random.randn(384).astype(np.float32)]
        for n in negative:
            n[:] = n / np.linalg.norm(n)

        loss = loss_fn.compute(
            anchor_embedding=anchor,
            positive_embeddings=positive,
            negative_embeddings=negative,
            utility_weights=[0.9, 0.7],
        )

        assert loss >= 0

    def test_compute_loss_empty_positives(self):
        """Test loss with empty positives returns 0."""
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


class TestRetrievalBenchmarker:
    """Tests for retrieval benchmarking."""

    def test_benchmark_precision_recall(self):
        """Test benchmark calculates precision and recall."""
        benchmarker = RetrievalBenchmarker(k=5)

        queries = ["q1", "q2"]
        retrieved = {
            "q1": ["d1", "d2", "d3"],
            "q2": ["d1", "d2", "d4"],
        }
        useful = {
            "q1": ["d1", "d2"],
            "q2": ["d2", "d4"],
        }

        result = benchmarker.benchmark(queries, retrieved, useful)

        assert result.total_queries == 2
        assert result.precision_at_k >= 0
        assert result.recall_at_k >= 0

    def test_benchmark_empty_useful_docs(self):
        """Test benchmark with empty useful docs."""
        benchmarker = RetrievalBenchmarker(k=5)

        queries = ["q1"]
        retrieved = {"q1": ["d1", "d2"]}
        useful = {"q1": []}

        result = benchmarker.benchmark(queries, retrieved, useful)
        assert result.precision_at_k == 0.0


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

    def test_training_pair_query_id_is_deterministic(self):
        """Test same query produces same query_id."""
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
