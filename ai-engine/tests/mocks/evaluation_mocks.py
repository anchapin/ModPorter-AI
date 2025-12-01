"""
Mocks for evaluation components to avoid complex dependencies in tests.

This module provides mocks for:
- evaluation.rag_evaluator
"""

import sys
from unittest.mock import MagicMock, Mock
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass

# Mock evaluation.rag_evaluator
def mock_evaluation_rag_evaluator():
    """Create a comprehensive mock for rag_evaluator module."""
    rag_evaluator_mock = MagicMock()

    # Create GoldenDatasetItem
    @dataclass
    class MockGoldenDatasetItem:
        query_id: str
        query_text: str
        expected_answer: str
        expected_sources: List[str]
        content_types: List[str]
        metadata: Dict

    rag_evaluator_mock.GoldenDatasetItem = MockGoldenDatasetItem

    # Create EvaluationResult
    @dataclass
    class MockEvaluationResult:
        query_id: str
        query_text: str
        answer: str
        sources: List[str]
        metrics: Dict[str, float]
        passed_tests: List[str]
        failed_tests: List[str]
        evaluation_timestamp: str

    rag_evaluator_mock.EvaluationResult = MockEvaluationResult

    # Create EvaluationReport
    @dataclass
    class MockEvaluationReport:
        evaluation_summary: Dict[str, Any]
        category_scores: Dict[str, float]
        metric_summaries: Dict[str, Any]
        recommendations: List[str]

    rag_evaluator_mock.EvaluationReport = MockEvaluationReport

    # Create RAGEvaluator class
    class MockRAGEvaluator:
        def __init__(self, **kwargs):
            self.golden_dataset = []
            self.metrics = {
                "retrieval": {"precision": 0.8, "recall": 0.7},
                "generation": {"coherence": 0.85, "accuracy": 0.75},
                "diversity": {"variety": 0.7, "novelty": 0.6}
            }

        def create_sample_golden_dataset(self):
            """Create a sample golden dataset for testing."""
            self.golden_dataset = [
                MockGoldenDatasetItem(
                    query_id="test_001",
                    query_text="How to create a custom block in Minecraft?",
                    expected_answer="To create a custom block in Minecraft, you need to...",
                    expected_sources=["block_creation_guide.md", "minecraft_api.md"],
                    content_types=["documentation", "code"],
                    metadata={"category": "block_creation"}
                ),
                MockGoldenDatasetItem(
                    query_id="test_002",
                    query_text="What is the structure of a Bedrock add-on?",
                    expected_answer="A Bedrock add-on consists of several key components...",
                    expected_sources=["bedrock_structure.md", "addon_examples.md"],
                    content_types=["documentation", "configuration"],
                    metadata={"category": "addon_structure"}
                )
            ]

        async def evaluate_full_dataset(self, rag_agent):
            """Evaluate RAG agent against the full golden dataset."""
            results = []
            for item in self.golden_dataset:
                result = await self.evaluate_single_query(rag_agent, item)
                results.append(result)

            # Generate summary statistics
            total_queries = len(results)
            passed_tests = sum(len(r.passed_tests) for r in results)
            failed_tests = sum(len(r.failed_tests) for r in results)
            overall_score = (passed_tests / (passed_tests + failed_tests)) if (passed_tests + failed_tests) > 0 else 0.0

            # Calculate category scores
            retrieval_scores = []
            generation_scores = []
            diversity_scores = []

            for result in results:
                for metric_name, value in result.metrics.items():
                    if "precision" in metric_name or "recall" in metric_name:
                        retrieval_scores.append(value)
                    elif "coherence" in metric_name or "accuracy" in metric_name:
                        generation_scores.append(value)
                    elif "variety" in metric_name or "novelty" in metric_name:
                        diversity_scores.append(value)

            avg_retrieval = sum(retrieval_scores) / len(retrieval_scores) if retrieval_scores else 0.0
            avg_generation = sum(generation_scores) / len(generation_scores) if generation_scores else 0.0
            avg_diversity = sum(diversity_scores) / len(diversity_scores) if diversity_scores else 0.0

            # Generate recommendations
            recommendations = []
            if avg_retrieval < 0.8:
                recommendations.append("Improve retrieval precision and recall")
            if avg_generation < 0.8:
                recommendations.append("Enhance generation coherence and accuracy")
            if avg_diversity < 0.8:
                recommendations.append("Increase response diversity and novelty")

            return {
                "evaluation_summary": {
                    "total_queries": total_queries,
                    "overall_score": overall_score,
                    "passed_tests": passed_tests,
                    "failed_tests": failed_tests,
                    "evaluation_timestamp": datetime.now().isoformat()
                },
                "category_scores": {
                    "retrieval": avg_retrieval,
                    "generation": avg_generation,
                    "diversity": avg_diversity
                },
                "metric_summaries": {
                    "retrieval_metrics": self.metrics["retrieval"],
                    "generation_metrics": self.metrics["generation"],
                    "diversity_metrics": self.metrics["diversity"]
                },
                "recommendations": recommendations,
                "detailed_results": results
            }

        async def evaluate_single_query(self, rag_agent, golden_item):
            """Evaluate RAG agent against a single golden dataset item."""
            # Simulate getting a response from the agent
            response = Mock()
            response.answer = "Mock response for evaluation"
            response.sources = [Mock() for _ in range(3)]

            # Generate mock metrics
            metrics = {
                "precision_at_5": 0.8,
                "recall_at_5": 0.7,
                "keyword_coverage": 0.75,
                "semantic_similarity": 0.85,
                "response_coherence": 0.9,
                "factual_accuracy": 0.75,
                "response_diversity": 0.7,
                "response_novelty": 0.6,
                "response_time_ms": 1500.0
            }

            # Determine passed/failed tests based on metrics
            passed_tests = []
            failed_tests = []

            for metric, value in metrics.items():
                if isinstance(value, float) and value > 0.8:
                    passed_tests.append(metric)
                else:
                    failed_tests.append(metric)

            return MockEvaluationResult(
                query_id=golden_item.query_id,
                query_text=golden_item.query_text,
                answer=response.answer,
                sources=[f"source_{i}" for i in range(len(response.sources))],
                metrics=metrics,
                passed_tests=passed_tests,
                failed_tests=failed_tests,
                evaluation_timestamp=datetime.now().isoformat()
            )

        def _compile_evaluation_report(self, results):
            """Compile evaluation results into a report."""
            if not results:
                return {
                    "evaluation_summary": {"error": "No results to compile"},
                    "category_scores": {},
                    "metric_summaries": {},
                    "recommendations": ["No data available for recommendations"]
                }

            # Calculate averages
            total_queries = len(results)
            passed_tests = sum(len(r.passed_tests) for r in results)
            failed_tests = sum(len(r.failed_tests) for r in results)
            overall_score = (passed_tests / (passed_tests + failed_tests)) if (passed_tests + failed_tests) > 0 else 0.0

            # Aggregate metrics
            all_metrics = {}
            for result in results:
                for metric, value in result.metrics.items():
                    if metric not in all_metrics:
                        all_metrics[metric] = []
                    all_metrics[metric].append(value)

            # Calculate averages for each metric
            avg_metrics = {
                metric: sum(values) / len(values) for metric, values in all_metrics.items()
            }

            return {
                "evaluation_summary": {
                    "total_queries": total_queries,
                    "overall_score": overall_score,
                    "passed_tests": passed_tests,
                    "failed_tests": failed_tests,
                    "evaluation_timestamp": datetime.now().isoformat()
                },
                "category_scores": {
                    "retrieval": avg_metrics.get("precision_at_5", 0.0),
                    "generation": avg_metrics.get("response_coherence", 0.0),
                    "diversity": avg_metrics.get("response_diversity", 0.0)
                },
                "metric_summaries": avg_metrics,
                "recommendations": [
                    "Consider improving metrics with scores below 0.8"
                ]
            }

    rag_evaluator_mock.RAGEvaluator = MockRAGEvaluator
    return rag_evaluator_mock

# Apply evaluation mocks
def apply_evaluation_mocks():
    """Apply evaluation mocks to sys.modules."""
    sys.modules['evaluation.rag_evaluator'] = mock_evaluation_rag_evaluator()
    sys.modules['evaluation'] = MagicMock()
