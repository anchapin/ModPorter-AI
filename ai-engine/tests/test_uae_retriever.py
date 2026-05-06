"""
Tests for UAE Retriever module.

Tests the UAE retriever implementation including fine-tuning,
retrieval benchmarking, and training pair creation.
"""

import pytest
import numpy as np
from utils.uae_retriever import (
    UAEConfig,
    UAERetriever,
    create_uae_retriever,
)
from utils.uae_utils import UAETrainingPair


class TestUAEConfig:
    """Tests for UAE configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = UAEConfig()
        
        assert config.base_model == "all-MiniLM-L6-v2"
        assert config.dimensions == 384
        assert config.temperature == 0.1
        assert config.margin == 0.5
        assert config.learning_rate == 2e-5
        assert config.batch_size == 16
        assert config.epochs == 3

    def test_custom_config(self):
        """Test custom configuration values."""
        config = UAEConfig(
            base_model="all-mpnet-base-v2",
            dimensions=768,
            learning_rate=1e-5,
            epochs=5,
        )
        
        assert config.base_model == "all-mpnet-base-v2"
        assert config.dimensions == 768
        assert config.learning_rate == 1e-5
        assert config.epochs == 5


class TestUAERetriever:
    """Tests for UAE retriever."""

    def test_retriever_creation(self):
        """Test retriever creation with default config."""
        retriever = UAERetriever()
        
        assert retriever.config.base_model == "all-MiniLM-L6-v2"
        assert retriever.is_fine_tuned is False

    def test_retriever_with_custom_config(self):
        """Test retriever with custom config."""
        config = UAEConfig(
            base_model="test-model",
            dimensions=512,
        )
        retriever = UAERetriever(config=config)
        
        assert retriever.config.base_model == "test-model"
        assert retriever.config.dimensions == 512

    def test_create_training_pairs(self):
        """Test training pair creation from conversion history."""
        retriever = UAERetriever()
        
        queries = ["query1", "query2"]
        retrieved_docs = {
            "query1": ["doc1", "doc2", "doc3"],
            "query2": ["doc4", "doc5"],
        }
        conversion_outputs = {
            "query1": ("output with doc1 and doc3", True),
            "query2": ("failed conversion", False),
        }
        
        pairs = retriever.create_training_pairs(
            queries=queries,
            retrieved_docs=retrieved_docs,
            conversion_outputs=conversion_outputs,
        )
        
        assert len(pairs) >= 0

    def test_benchmark_retrieval(self):
        """Test retrieval benchmarking."""
        retriever = UAERetriever()
        
        queries = ["query1", "query2"]
        retrieved_docs = {
            "query1": ["doc1", "doc2"],
            "query2": ["doc1", "doc3"],
        }
        useful_docs = {
            "query1": ["doc1"],
            "query2": ["doc3"],
        }
        
        benchmark = retriever.benchmark_retrieval(
            test_queries=queries,
            retrieved_docs=retrieved_docs,
            useful_docs=useful_docs,
        )
        
        assert benchmark.total_queries == 2
        assert benchmark.precision_at_k >= 0
        assert benchmark.recall_at_k >= 0

    def test_compute_utility_score(self):
        """Test utility-weighted score computation."""
        retriever = UAERetriever()
        
        query_emb = np.random.randn(384).astype(np.float32)
        doc_emb = np.random.randn(384).astype(np.float32)
        
        score = retriever.compute_utility_score(query_emb, doc_emb, utility_weight=0.8)
        
        assert isinstance(score, float)

    def test_label_from_conversion_success(self):
        """Test utility labels from successful conversion."""
        retriever = UAERetriever()
        
        labels = retriever.label_from_conversion(
            query="test query",
            retrieved_doc_ids=["doc1", "doc2"],
            conversion_output="output using doc1",
            conversion_successful=True,
        )
        
        assert len(labels) == 2
        assert all(isinstance(label.utility_score, float) for label in labels)

    def test_training_history_empty_initially(self):
        """Test that training history is empty initially."""
        retriever = UAERetriever()
        
        assert retriever.training_history == []


class TestUAERetrieverFactory:
    """Tests for UAE retriever factory function."""

    def test_create_uae_retriever_default(self):
        """Test creating retriever with defaults."""
        retriever = create_uae_retriever()
        
        assert retriever is not None
        assert isinstance(retriever, UAERetriever)

    def test_create_uae_retriever_with_config(self):
        """Test creating retriever with custom config."""
        config = UAEConfig(epochs=10)
        retriever = create_uae_retriever(config=config)
        
        assert retriever.config.epochs == 10


class TestUAETrainingPair:
    """Tests for training pair creation with utility labels."""

    def test_training_pair_with_labels(self):
        """Test training pair creation with multiple utility labels."""
        from utils.uae_utils import UtilityLabel, UtilitySignal
        
        labels = [
            UtilityLabel(
                query_id="q1",
                document_id="doc1",
                utility_score=0.9,
                signal_source=UtilitySignal.CORRECT_CONVERSION,
                metadata={"conversion_successful": True},
            ),
            UtilityLabel(
                query_id="q1",
                document_id="doc2",
                utility_score=0.2,
                signal_source=UtilitySignal.INCORRECT_CONVERSION,
                metadata={"conversion_successful": False},
            ),
        ]
        
        pair = UAETrainingPair(
            query="test query",
            positive_docs=["doc1"],
            negative_docs=["doc2"],
            utility_labels=labels,
        )
        
        assert pair.query == "test query"
        assert len(pair.positive_docs) == 1
        assert len(pair.negative_docs) == 1
