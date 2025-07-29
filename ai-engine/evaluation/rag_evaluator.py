"""
Evaluation framework for the advanced RAG system.

This module provides comprehensive evaluation metrics and tools for assessing
the performance of the advanced RAG system across multiple dimensions.
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
from collections import defaultdict, Counter
import math
from datetime import datetime

from schemas.multimodal_schema import SearchQuery, SearchResult
from agents.advanced_rag_agent import RAGResponse

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of evaluation metrics."""
    RETRIEVAL = "retrieval"
    GENERATION = "generation"
    RELEVANCE = "relevance"
    DIVERSITY = "diversity"
    EFFICIENCY = "efficiency"
    USER_SATISFACTION = "user_satisfaction"


@dataclass
class EvaluationResult:
    """Result of a single evaluation."""
    query_id: str
    query_text: str
    expected_answer: Optional[str]
    expected_sources: List[str]
    actual_response: RAGResponse
    metrics: Dict[str, float]
    passed_tests: List[str]
    failed_tests: List[str]
    evaluation_timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            **asdict(self),
            'actual_response': self.actual_response.to_dict() if self.actual_response else None
        }


@dataclass
class GoldenDatasetItem:
    """Item in the golden evaluation dataset."""
    query_id: str
    query_text: str
    query_type: str  # 'how_to', 'explanation', 'example', 'troubleshooting'
    difficulty_level: str  # 'beginner', 'intermediate', 'advanced'
    domain: str  # 'blocks', 'items', 'entities', 'recipes', 'modding'
    expected_answer: Optional[str]
    expected_sources: List[str]  # List of document IDs that should be retrieved
    required_keywords: List[str]  # Keywords that must appear in the answer
    prohibited_keywords: List[str]  # Keywords that should not appear
    min_sources: int  # Minimum number of sources expected
    max_response_time_ms: float  # Maximum acceptable response time
    min_confidence: float  # Minimum confidence score expected
    content_types: Optional[List[str]]  # Expected content types in results
    metadata: Dict[str, Any]  # Additional metadata


class RetrievalMetrics:
    """Metrics for evaluating retrieval quality."""
    
    @staticmethod
    def precision_at_k(retrieved_docs: List[str], relevant_docs: List[str], k: int) -> float:
        """Calculate precision at k."""
        if not retrieved_docs or k == 0:
            return 0.0
        
        retrieved_k = retrieved_docs[:k]
        relevant_retrieved = len([doc for doc in retrieved_k if doc in relevant_docs])
        
        return relevant_retrieved / len(retrieved_k)
    
    @staticmethod
    def recall_at_k(retrieved_docs: List[str], relevant_docs: List[str], k: int) -> float:
        """Calculate recall at k."""
        if not relevant_docs:
            return 1.0 if not retrieved_docs else 0.0
        
        retrieved_k = retrieved_docs[:k]
        relevant_retrieved = len([doc for doc in retrieved_k if doc in relevant_docs])
        
        return relevant_retrieved / len(relevant_docs)
    
    @staticmethod
    def f1_at_k(retrieved_docs: List[str], relevant_docs: List[str], k: int) -> float:
        """Calculate F1 score at k."""
        precision = RetrievalMetrics.precision_at_k(retrieved_docs, relevant_docs, k)
        recall = RetrievalMetrics.recall_at_k(retrieved_docs, relevant_docs, k)
        
        if precision + recall == 0:
            return 0.0
        
        return 2 * (precision * recall) / (precision + recall)
    
    @staticmethod
    def mean_reciprocal_rank(retrieved_docs: List[str], relevant_docs: List[str]) -> float:
        """Calculate Mean Reciprocal Rank."""
        for i, doc in enumerate(retrieved_docs, 1):
            if doc in relevant_docs:
                return 1.0 / i
        return 0.0
    
    @staticmethod
    def normalized_discounted_cumulative_gain(
        retrieved_docs: List[str], 
        relevant_docs: List[str],
        relevance_scores: Optional[Dict[str, float]] = None
    ) -> float:
        """Calculate Normalized Discounted Cumulative Gain."""
        if not retrieved_docs:
            return 0.0
        
        # Use binary relevance if no scores provided
        if relevance_scores is None:
            relevance_scores = {doc: 1.0 for doc in relevant_docs}
        
        # Calculate DCG
        dcg = 0.0
        for i, doc in enumerate(retrieved_docs, 1):
            relevance = relevance_scores.get(doc, 0.0)
            dcg += relevance / math.log2(i + 1)
        
        # Calculate IDCG (ideal DCG)
        ideal_order = sorted(relevant_docs, key=lambda x: relevance_scores.get(x, 0.0), reverse=True)
        idcg = 0.0
        for i, doc in enumerate(ideal_order, 1):
            relevance = relevance_scores.get(doc, 0.0)
            idcg += relevance / math.log2(i + 1)
        
        return dcg / idcg if idcg > 0 else 0.0
    
    @staticmethod
    def hit_rate(retrieved_docs: List[str], relevant_docs: List[str]) -> float:
        """Calculate hit rate (whether any relevant doc was retrieved)."""
        return 1.0 if any(doc in relevant_docs for doc in retrieved_docs) else 0.0


class GenerationMetrics:
    """Metrics for evaluating answer generation quality."""
    
    @staticmethod
    def keyword_coverage(answer: str, required_keywords: List[str]) -> float:
        """Calculate coverage of required keywords in the answer."""
        if not required_keywords:
            return 1.0
        
        answer_lower = answer.lower()
        covered_keywords = sum(1 for keyword in required_keywords if keyword.lower() in answer_lower)
        
        return covered_keywords / len(required_keywords)
    
    @staticmethod
    def keyword_prohibition_compliance(answer: str, prohibited_keywords: List[str]) -> float:
        """Calculate compliance with prohibited keywords (1.0 = no prohibited keywords found)."""
        if not prohibited_keywords:
            return 1.0
        
        answer_lower = answer.lower()
        violated_keywords = sum(1 for keyword in prohibited_keywords if keyword.lower() in answer_lower)
        
        return 1.0 - (violated_keywords / len(prohibited_keywords))
    
    @staticmethod
    def answer_length_appropriateness(answer: str, query_type: str) -> float:
        """Evaluate answer length appropriateness based on query type."""
        answer_length = len(answer.split())
        
        # Expected length ranges for different query types
        expected_ranges = {
            'explanation': (50, 200),
            'how_to': (100, 300),
            'example': (30, 150),
            'troubleshooting': (50, 250),
            'general': (30, 200)
        }
        
        min_len, max_len = expected_ranges.get(query_type, (30, 200))
        
        if min_len <= answer_length <= max_len:
            return 1.0
        elif answer_length < min_len:
            return answer_length / min_len
        else:
            # Penalty for overly long answers
            excess = answer_length - max_len
            return max(0.0, 1.0 - (excess / max_len))
    
    @staticmethod
    def source_citation_quality(answer: str, sources: List[SearchResult]) -> float:
        """Evaluate quality of source citations in the answer."""
        if not sources:
            return 0.0
        
        # Check if answer references sources appropriately
        citation_indicators = [
            'according to', 'based on', 'source', 'documentation',
            'from the', 'as described', 'as shown'
        ]
        
        answer_lower = answer.lower()
        citation_score = 0.0
        
        # Check for citation indicators
        citation_count = sum(1 for indicator in citation_indicators if indicator in answer_lower)
        citation_score += min(citation_count / 2, 0.5)  # Up to 0.5 for citations
        
        # Check if source information is integrated well
        source_paths = [source.document.source_path for source in sources]
        source_integration = 0.0
        
        for source_path in source_paths:
            filename = source_path.split('/')[-1].split('.')[0]
            if filename.lower() in answer_lower:
                source_integration += 0.1
        
        citation_score += min(source_integration, 0.5)  # Up to 0.5 for integration
        
        return min(citation_score, 1.0)
    
    @staticmethod
    def coherence_score(answer: str) -> float:
        """Evaluate coherence and readability of the answer."""
        if not answer:
            return 0.0
        
        sentences = [s.strip() for s in answer.split('.') if s.strip()]
        if len(sentences) < 2:
            return 0.5  # Single sentence answers get medium score
        
        coherence_score = 0.0
        
        # Check sentence length variation (good coherence has varied sentence lengths)
        sentence_lengths = [len(s.split()) for s in sentences]
        avg_length = np.mean(sentence_lengths)
        length_variance = np.var(sentence_lengths)
        
        # Moderate variance is good (not all sentences same length)
        if 5 < avg_length < 25 and 10 < length_variance < 100:
            coherence_score += 0.3
        
        # Check for transitional phrases
        transitions = [
            'however', 'therefore', 'additionally', 'furthermore', 'moreover',
            'on the other hand', 'in contrast', 'similarly', 'for example',
            'as a result', 'consequently', 'meanwhile', 'first', 'second', 'finally'
        ]
        
        transition_count = sum(1 for transition in transitions if transition in answer.lower())
        coherence_score += min(transition_count / 5, 0.3)  # Up to 0.3 for transitions
        
        # Check for proper paragraph structure
        paragraphs = answer.split('\n\n')
        if len(paragraphs) > 1 and all(len(p.strip()) > 20 for p in paragraphs):
            coherence_score += 0.2
        
        # Check for lists or structured content
        if any(indicator in answer for indicator in ['1.', '2.', '•', '-', 'Example:']):
            coherence_score += 0.2
        
        return min(coherence_score, 1.0)


class DiversityMetrics:
    """Metrics for evaluating diversity of retrieved sources."""
    
    @staticmethod
    def content_type_diversity(sources: List[SearchResult]) -> float:
        """Calculate diversity of content types in results."""
        if not sources:
            return 0.0
        
        content_types = [source.document.content_type for source in sources]
        unique_types = len(set(content_types))
        
        # Normalize by maximum possible diversity (assuming 4 main content types)
        max_diversity = min(4, len(content_types))
        return unique_types / max_diversity if max_diversity > 0 else 0.0
    
    @staticmethod
    def source_diversity(sources: List[SearchResult]) -> float:
        """Calculate diversity of source paths."""
        if not sources:
            return 0.0
        
        source_paths = [source.document.source_path for source in sources]
        unique_sources = len(set(source_paths))
        
        return unique_sources / len(source_paths) if source_paths else 0.0
    
    @staticmethod
    def topic_diversity_score(sources: List[SearchResult]) -> float:
        """Calculate topical diversity using tags."""
        if not sources:
            return 0.0
        
        all_tags = []
        for source in sources:
            all_tags.extend(source.document.tags)
        
        if not all_tags:
            return 0.0
        
        unique_tags = len(set(all_tags))
        total_tags = len(all_tags)
        
        # Higher diversity = more unique tags relative to total
        return unique_tags / total_tags if total_tags > 0 else 0.0


class RAGEvaluator:
    """
    Comprehensive evaluator for the Advanced RAG system.
    
    This evaluator assesses RAG performance across multiple dimensions
    including retrieval quality, generation quality, and efficiency.
    """
    
    def __init__(self):
        self.golden_dataset = []
        self.evaluation_history = []
        self.metrics_calculators = {
            MetricType.RETRIEVAL: RetrievalMetrics(),
            MetricType.GENERATION: GenerationMetrics(),
            MetricType.DIVERSITY: DiversityMetrics()
        }
    
    def load_golden_dataset(self, dataset_path: str) -> int:
        """
        Load golden dataset from file.
        
        Args:
            dataset_path: Path to the golden dataset JSON file
            
        Returns:
            Number of items loaded
        """
        try:
            with open(dataset_path, 'r') as f:
                dataset_data = json.load(f)
            
            self.golden_dataset = []
            for item_data in dataset_data.get('items', []):
                item = GoldenDatasetItem(**item_data)
                self.golden_dataset.append(item)
            
            logger.info(f"Loaded {len(self.golden_dataset)} items from golden dataset")
            return len(self.golden_dataset)
            
        except Exception as e:
            logger.error(f"Error loading golden dataset: {e}")
            return 0
    
    def create_sample_golden_dataset(self) -> List[GoldenDatasetItem]:
        """Create a sample golden dataset for testing."""
        sample_items = [
            GoldenDatasetItem(
                query_id="blocks_001",
                query_text="How to create a custom block in Minecraft Java Edition",
                query_type="how_to",
                difficulty_level="intermediate",
                domain="blocks",
                expected_answer="To create a custom block in Minecraft Java Edition, you need to create a class that extends Block, define the block properties, and register it with the game registry.",
                expected_sources=["java_blocks", "modding_guide"],
                required_keywords=["class", "Block", "registry", "properties"],
                prohibited_keywords=["Bedrock", "behavior pack"],
                min_sources=2,
                max_response_time_ms=2000.0,
                min_confidence=0.7,
                content_types=["code", "documentation"],
                metadata={"difficulty": "intermediate", "language": "java"}
            ),
            GoldenDatasetItem(
                query_id="recipes_001",
                query_text="What is a shaped crafting recipe in Minecraft",
                query_type="explanation",
                difficulty_level="beginner",
                domain="recipes",
                expected_answer="A shaped crafting recipe is a recipe where the arrangement of ingredients in the crafting grid matters.",
                expected_sources=["recipe_system"],
                required_keywords=["shaped", "crafting", "recipe", "pattern"],
                prohibited_keywords=[],
                min_sources=1,
                max_response_time_ms=1500.0,
                min_confidence=0.8,
                content_types=["documentation"],
                metadata={"difficulty": "beginner"}
            ),
            GoldenDatasetItem(
                query_id="bedrock_001",
                query_text="Show me an example of a Bedrock block behavior file",
                query_type="example",
                difficulty_level="intermediate",
                domain="blocks",
                expected_answer="A Bedrock block behavior file is a JSON file that defines block properties and components.",
                expected_sources=["bedrock_blocks"],
                required_keywords=["JSON", "behavior", "components", "example"],
                prohibited_keywords=["Java", "class"],
                min_sources=1,
                max_response_time_ms=1800.0,
                min_confidence=0.6,
                content_types=["documentation"],
                metadata={"platform": "bedrock", "format": "json"}
            )
        ]
        
        self.golden_dataset = sample_items
        logger.info(f"Created sample golden dataset with {len(sample_items)} items")
        return sample_items
    
    async def evaluate_single_query(
        self,
        rag_agent,
        golden_item: GoldenDatasetItem
    ) -> EvaluationResult:
        """
        Evaluate RAG performance on a single query.
        
        Args:
            rag_agent: The RAG agent to evaluate
            golden_item: Golden dataset item to evaluate against
            
        Returns:
            Evaluation result with metrics
        """
        start_time = datetime.utcnow()
        
        try:
            # Execute the query
            response = await rag_agent.query(
                query_text=golden_item.query_text,
                content_types=[ContentType(ct) for ct in golden_item.content_types] if golden_item.content_types else None,
                session_id=f"eval_{golden_item.query_id}"
            )
            
            # Calculate metrics
            metrics = {}
            passed_tests = []
            failed_tests = []
            
            # Retrieval metrics
            retrieved_doc_ids = [source.document.id for source in response.sources]
            
            metrics['precision_at_5'] = RetrievalMetrics.precision_at_k(
                retrieved_doc_ids, golden_item.expected_sources, 5
            )
            metrics['recall_at_5'] = RetrievalMetrics.recall_at_k(
                retrieved_doc_ids, golden_item.expected_sources, 5
            )
            metrics['f1_at_5'] = RetrievalMetrics.f1_at_k(
                retrieved_doc_ids, golden_item.expected_sources, 5
            )
            metrics['mrr'] = RetrievalMetrics.mean_reciprocal_rank(
                retrieved_doc_ids, golden_item.expected_sources
            )
            metrics['hit_rate'] = RetrievalMetrics.hit_rate(
                retrieved_doc_ids, golden_item.expected_sources
            )
            
            # Generation metrics
            metrics['keyword_coverage'] = GenerationMetrics.keyword_coverage(
                response.answer, golden_item.required_keywords
            )
            metrics['keyword_prohibition_compliance'] = GenerationMetrics.keyword_prohibition_compliance(
                response.answer, golden_item.prohibited_keywords
            )
            metrics['answer_length_appropriateness'] = GenerationMetrics.answer_length_appropriateness(
                response.answer, golden_item.query_type
            )
            metrics['source_citation_quality'] = GenerationMetrics.source_citation_quality(
                response.answer, response.sources
            )
            metrics['coherence_score'] = GenerationMetrics.coherence_score(response.answer)
            
            # Diversity metrics
            metrics['content_type_diversity'] = DiversityMetrics.content_type_diversity(response.sources)
            metrics['source_diversity'] = DiversityMetrics.source_diversity(response.sources)
            metrics['topic_diversity'] = DiversityMetrics.topic_diversity_score(response.sources)
            
            # Efficiency metrics
            metrics['response_time_ms'] = response.processing_time_ms
            metrics['confidence_score'] = response.confidence
            metrics['sources_count'] = len(response.sources)
            
            # Test conditions
            if metrics['precision_at_5'] >= 0.6:
                passed_tests.append("precision_threshold")
            else:
                failed_tests.append("precision_threshold")
            
            if metrics['keyword_coverage'] >= 0.8:
                passed_tests.append("keyword_coverage")
            else:
                failed_tests.append("keyword_coverage")
            
            if metrics['keyword_prohibition_compliance'] >= 0.9:
                passed_tests.append("keyword_prohibition")
            else:
                failed_tests.append("keyword_prohibition")
            
            if response.processing_time_ms <= golden_item.max_response_time_ms:
                passed_tests.append("response_time")
            else:
                failed_tests.append("response_time")
            
            if response.confidence >= golden_item.min_confidence:
                passed_tests.append("confidence_threshold")
            else:
                failed_tests.append("confidence_threshold")
            
            if len(response.sources) >= golden_item.min_sources:
                passed_tests.append("min_sources")
            else:
                failed_tests.append("min_sources")
            
            # Create evaluation result
            result = EvaluationResult(
                query_id=golden_item.query_id,
                query_text=golden_item.query_text,
                expected_answer=golden_item.expected_answer,
                expected_sources=golden_item.expected_sources,
                actual_response=response,
                metrics=metrics,
                passed_tests=passed_tests,
                failed_tests=failed_tests,
                evaluation_timestamp=start_time.isoformat()
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error evaluating query {golden_item.query_id}: {e}")
            
            # Return error result
            return EvaluationResult(
                query_id=golden_item.query_id,
                query_text=golden_item.query_text,
                expected_answer=golden_item.expected_answer,
                expected_sources=golden_item.expected_sources,
                actual_response=None,
                metrics={'error': 1.0},
                passed_tests=[],
                failed_tests=['execution_error'],
                evaluation_timestamp=start_time.isoformat()
            )
    
    async def evaluate_full_dataset(
        self,
        rag_agent,
        dataset_items: Optional[List[GoldenDatasetItem]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate RAG performance on the full dataset.
        
        Args:
            rag_agent: The RAG agent to evaluate
            dataset_items: Optional specific items to evaluate (defaults to full dataset)
            
        Returns:
            Comprehensive evaluation report
        """
        if dataset_items is None:
            dataset_items = self.golden_dataset
        
        if not dataset_items:
            logger.warning("No dataset items to evaluate")
            return {'error': 'No dataset items available'}
        
        logger.info(f"Starting full dataset evaluation with {len(dataset_items)} items")
        
        evaluation_results = []
        
        # Evaluate each item
        for item in dataset_items:
            try:
                result = await self.evaluate_single_query(rag_agent, item)
                evaluation_results.append(result)
                logger.info(f"Evaluated query {item.query_id}: {len(result.passed_tests)} passed, {len(result.failed_tests)} failed")
            except Exception as e:
                logger.error(f"Failed to evaluate query {item.query_id}: {e}")
        
        # Compile overall statistics
        report = self._compile_evaluation_report(evaluation_results)
        
        # Store evaluation history
        self.evaluation_history.append({
            'timestamp': datetime.utcnow().isoformat(),
            'results': evaluation_results,
            'summary': report
        })
        
        logger.info(f"Full dataset evaluation completed. Overall score: {report.get('overall_score', 0.0):.3f}")
        
        return report
    
    def _compile_evaluation_report(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """Compile comprehensive evaluation report from individual results."""
        if not results:
            return {'error': 'No evaluation results to compile'}
        
        # Aggregate metrics
        all_metrics = defaultdict(list)
        test_results = defaultdict(int)
        
        successful_evaluations = [r for r in results if r.actual_response is not None]
        
        for result in successful_evaluations:
            for metric_name, metric_value in result.metrics.items():
                if isinstance(metric_value, (int, float)):
                    all_metrics[metric_name].append(metric_value)
            
            for test in result.passed_tests:
                test_results[f"{test}_passed"] += 1
            
            for test in result.failed_tests:
                test_results[f"{test}_failed"] += 1
        
        # Calculate summary statistics
        metric_summaries = {}
        for metric_name, values in all_metrics.items():
            metric_summaries[metric_name] = {
                'mean': np.mean(values),
                'std': np.std(values),
                'min': np.min(values),
                'max': np.max(values),
                'median': np.median(values)
            }
        
        # Calculate category scores
        retrieval_metrics = ['precision_at_5', 'recall_at_5', 'f1_at_5', 'mrr', 'hit_rate']
        generation_metrics = ['keyword_coverage', 'keyword_prohibition_compliance', 
                            'answer_length_appropriateness', 'source_citation_quality', 'coherence_score']
        diversity_metrics = ['content_type_diversity', 'source_diversity', 'topic_diversity']
        efficiency_metrics = ['response_time_ms', 'confidence_score']
        
        category_scores = {}
        
        for category, metrics in [
            ('retrieval', retrieval_metrics),
            ('generation', generation_metrics),
            ('diversity', diversity_metrics)
        ]:
            category_values = []
            for metric in metrics:
                if metric in metric_summaries:
                    category_values.append(metric_summaries[metric]['mean'])
            
            category_scores[category] = np.mean(category_values) if category_values else 0.0
        
        # Overall score (weighted average)
        overall_score = (
            category_scores.get('retrieval', 0.0) * 0.4 +
            category_scores.get('generation', 0.0) * 0.4 +
            category_scores.get('diversity', 0.0) * 0.2
        )
        
        # Test pass rates
        total_tests = len(successful_evaluations)
        test_pass_rates = {}
        for test_name in ['precision_threshold', 'keyword_coverage', 'keyword_prohibition', 
                         'response_time', 'confidence_threshold', 'min_sources']:
            passed = test_results.get(f"{test_name}_passed", 0)
            test_pass_rates[test_name] = passed / total_tests if total_tests > 0 else 0.0
        
        # Performance breakdown by query type
        query_type_performance = defaultdict(list)
        difficulty_performance = defaultdict(list)
        domain_performance = defaultdict(list)
        
        for result in successful_evaluations:
            # Find corresponding golden item for metadata
            golden_item = next(
                (item for item in self.golden_dataset if item.query_id == result.query_id),
                None
            )
            
            if golden_item:
                overall_result_score = np.mean([
                    result.metrics.get('precision_at_5', 0.0),
                    result.metrics.get('keyword_coverage', 0.0),
                    result.metrics.get('coherence_score', 0.0)
                ])
                
                query_type_performance[golden_item.query_type].append(overall_result_score)
                difficulty_performance[golden_item.difficulty_level].append(overall_result_score)
                domain_performance[golden_item.domain].append(overall_result_score)
        
        # Compile final report
        report = {
            'evaluation_summary': {
                'total_queries': len(results),
                'successful_evaluations': len(successful_evaluations),
                'failed_evaluations': len(results) - len(successful_evaluations),
                'overall_score': overall_score,
                'evaluation_timestamp': datetime.utcnow().isoformat()
            },
            'category_scores': category_scores,
            'metric_summaries': metric_summaries,
            'test_pass_rates': test_pass_rates,
            'performance_breakdown': {
                'by_query_type': {qtype: np.mean(scores) for qtype, scores in query_type_performance.items()},
                'by_difficulty': {diff: np.mean(scores) for diff, scores in difficulty_performance.items()},
                'by_domain': {domain: np.mean(scores) for domain, scores in domain_performance.items()}
            },
            'recommendations': self._generate_recommendations(metric_summaries, test_pass_rates, category_scores)
        }
        
        return report
    
    def _generate_recommendations(
        self,
        metric_summaries: Dict[str, Dict[str, float]],
        test_pass_rates: Dict[str, float],
        category_scores: Dict[str, float]
    ) -> List[str]:
        """Generate recommendations based on evaluation results."""
        recommendations = []
        
        # Retrieval recommendations
        if category_scores.get('retrieval', 0.0) < 0.6:
            recommendations.append("Consider improving retrieval quality: precision and recall are below optimal levels")
            
            if metric_summaries.get('precision_at_5', {}).get('mean', 0.0) < 0.5:
                recommendations.append("Low precision: Review relevance scoring and ranking algorithms")
            
            if metric_summaries.get('recall_at_5', {}).get('mean', 0.0) < 0.5:
                recommendations.append("Low recall: Consider expanding query or improving document coverage")
        
        # Generation recommendations
        if category_scores.get('generation', 0.0) < 0.6:
            recommendations.append("Consider improving answer generation quality")
            
            if metric_summaries.get('keyword_coverage', {}).get('mean', 0.0) < 0.7:
                recommendations.append("Improve keyword coverage in generated answers")
            
            if metric_summaries.get('coherence_score', {}).get('mean', 0.0) < 0.6:
                recommendations.append("Focus on improving answer coherence and structure")
        
        # Efficiency recommendations
        avg_response_time = metric_summaries.get('response_time_ms', {}).get('mean', 0.0)
        if avg_response_time > 2000:
            recommendations.append("Consider optimizing response time: average exceeds 2 seconds")
        
        # Diversity recommendations
        if category_scores.get('diversity', 0.0) < 0.5:
            recommendations.append("Improve source diversity to provide more comprehensive answers")
        
        # Test-specific recommendations
        if test_pass_rates.get('confidence_threshold', 0.0) < 0.7:
            recommendations.append("Low confidence scores: Review confidence calculation and thresholds")
        
        if not recommendations:
            recommendations.append("System performance is within acceptable ranges across all categories")
        
        return recommendations
    
    def export_evaluation_report(self, report: Dict[str, Any], output_path: str):
        """Export evaluation report to file."""
        try:
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"Evaluation report exported to {output_path}")
        except Exception as e:
            logger.error(f"Error exporting evaluation report: {e}")
    
    def get_evaluation_history(self) -> List[Dict[str, Any]]:
        """Get evaluation history."""
        return self.evaluation_history