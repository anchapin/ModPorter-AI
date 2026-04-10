"""
Adaptive Fusion - Query-type-aware score fusion for search results.

This module provides intelligent score fusion based on query type
and complexity to optimize search result relevance.
"""

import logging
from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum

from schemas.multimodal_schema import SearchResult

logger = logging.getLogger(__name__)


class QueryType(str, Enum):
    """Query type classification."""

    INFORMATIONAL = "informational"
    NAVIGATIONAL = "navigational"
    TRANSACTIONAL = "transactional"
    COMPLEX = "complex"
    SIMPLE = "simple"


class ComplexityLevel(str, Enum):
    """Query complexity levels."""

    SIMPLE = "simple"
    STANDARD = "standard"
    COMPLEX = "complex"


class FusionStrategy(str, Enum):
    """Fusion strategies."""

    RECIPROCAL_RANK_FUSION = "reciprocal_rank"
    WEIGHTED_SUM = "weighted_sum"
    SCORE_AVERAGING = "score_averaging"
    CONFIDENCE_WEIGHTED = "confidence_weighted"


@dataclass
class FusionConfig:
    """Configuration for adaptive fusion."""

    strategy: FusionStrategy = FusionStrategy.RECIPROCAL_RANK_FUSION
    semantic_weight: float = 0.5
    keyword_weight: float = 0.3
    contextual_weight: float = 0.2


class AdaptiveFusion:
    """
    Adaptive fusion that selects strategy based on query type.

    Different query types benefit from different fusion strategies:
    - INFORMATIONAL: Semantic-first (vector scores weighted higher)
    - NAVIGATIONAL: Keyword-first (BM25 scores weighted higher)
    - TRANSACTIONAL: Hybrid balanced
    - COMPLEX: Ensemble with all signals
    - SIMPLE: Fast single-source
    """

    def __init__(self, default_strategy: str = "reciprocal_rank"):
        self.default_strategy = FusionStrategy(default_strategy)

        self.query_type_weights = {
            QueryType.INFORMATIONAL: {
                "semantic": 0.6,
                "keyword": 0.2,
                "contextual": 0.2,
            },
            QueryType.NAVIGATIONAL: {
                "semantic": 0.2,
                "keyword": 0.7,
                "contextual": 0.1,
            },
            QueryType.TRANSACTIONAL: {
                "semantic": 0.4,
                "keyword": 0.4,
                "contextual": 0.2,
            },
            QueryType.COMPLEX: {
                "semantic": 0.5,
                "keyword": 0.3,
                "contextual": 0.2,
            },
            QueryType.SIMPLE: {
                "semantic": 0.7,
                "keyword": 0.2,
                "contextual": 0.1,
            },
        }

        logger.info(f"AdaptiveFusion initialized with default: {default_strategy}")

    def fuse(
        self,
        results: Dict[str, List[SearchResult]],
        query_type: QueryType = None,
        complexity: ComplexityLevel = None,
    ) -> List[SearchResult]:
        """
        Fuse results from multiple sources.

        Args:
            results: Dict mapping source name to list of results
            query_type: Type of query
            complexity: Query complexity

        Returns:
            Fused and ranked list of results
        """
        if not results:
            return []

        if len(results) == 1:
            source_name = list(results.keys())[0]
            single_results = results[source_name]
            self._update_ranks(single_results)
            return single_results

        weights = self._get_weights(query_type, complexity)
        strategy = self.select_strategy(query_type, complexity)

        if strategy == FusionStrategy.RECIPROCAL_RANK_FUSION:
            return self._reciprocal_rank_fusion(results, weights)
        elif strategy == FusionStrategy.WEIGHTED_SUM:
            return self._weighted_sum_fusion(results, weights)
        elif strategy == FusionStrategy.SCORE_AVERAGING:
            return self._score_averaging_fusion(results)
        elif strategy == FusionStrategy.CONFIDENCE_WEIGHTED:
            return self._confidence_weighted_fusion(results)

        return self._reciprocal_rank_fusion(results, weights)

    def _get_weights(
        self, query_type: QueryType = None, complexity: ComplexityLevel = None
    ) -> Dict[str, float]:
        """Get weights for the given query type."""
        if query_type and query_type in self.query_type_weights:
            return self.query_type_weights[query_type]

        return {
            "semantic": 0.5,
            "keyword": 0.3,
            "contextual": 0.2,
        }

    def select_strategy(
        self, query_type: QueryType = None, complexity: ComplexityLevel = None
    ) -> FusionStrategy:
        """Select fusion strategy based on query type and complexity."""
        if complexity == ComplexityLevel.SIMPLE:
            return FusionStrategy.RECIPROCAL_RANK_FUSION

        if complexity == ComplexityLevel.COMPLEX:
            return FusionStrategy.WEIGHTED_SUM

        if query_type == QueryType.NAVIGATIONAL:
            return FusionStrategy.WEIGHTED_SUM

        if query_type == QueryType.INFORMATIONAL:
            return FusionStrategy.RECIPROCAL_RANK_FUSION

        return self.default_strategy

    def _reciprocal_rank_fusion(
        self, results: Dict[str, List[SearchResult]], weights: Dict[str, float]
    ) -> List[SearchResult]:
        """Apply reciprocal rank fusion."""
        doc_scores = {}

        for source_name, source_results in results.items():
            weight = weights.get(source_name, 1.0)

            for rank, result in enumerate(source_results, 1):
                doc_id = result.document.id

                if doc_id not in doc_scores:
                    doc_scores[doc_id] = {
                        "document": result.document,
                        "score": 0.0,
                        "sources": [],
                    }

                rrf_score = weight / (60 + rank)
                doc_scores[doc_id]["score"] += rrf_score
                doc_scores[doc_id]["sources"].append(source_name)

        fused = sorted(doc_scores.values(), key=lambda x: x["score"], reverse=True)

        final_results = []
        for i, item in enumerate(fused):
            result = SearchResult(
                document=item["document"],
                similarity_score=0.0,
                keyword_score=0.0,
                final_score=item["score"],
                rank=i + 1,
                embedding_model_used="fusion",
                matched_content="",
                match_explanation=f"Fused from {len(item['sources'])} sources",
            )
            final_results.append(result)

        return final_results

    def _weighted_sum_fusion(
        self, results: Dict[str, List[SearchResult]], weights: Dict[str, float]
    ) -> List[SearchResult]:
        """Apply weighted sum fusion."""
        doc_scores = {}

        for source_name, source_results in results.items():
            weight = weights.get(source_name, 1.0) / len(results)

            for result in source_results:
                doc_id = result.document.id

                if doc_id not in doc_scores:
                    doc_scores[doc_id] = {
                        "document": result.document,
                        "score": 0.0,
                        "similarity": 0.0,
                        "keyword": 0.0,
                    }

                doc_scores[doc_id]["score"] += result.final_score * weight
                doc_scores[doc_id]["similarity"] += result.similarity_score * weight
                doc_scores[doc_id]["keyword"] += result.keyword_score * weight

        fused = sorted(doc_scores.values(), key=lambda x: x["score"], reverse=True)

        final_results = []
        for i, item in enumerate(fused):
            result = SearchResult(
                document=item["document"],
                similarity_score=item["similarity"],
                keyword_score=item["keyword"],
                final_score=item["score"],
                rank=i + 1,
                embedding_model_used="fusion",
                matched_content="",
                match_explanation="Weighted sum fusion",
            )
            final_results.append(result)

        return final_results

    def _score_averaging_fusion(self, results: Dict[str, List[SearchResult]]) -> List[SearchResult]:
        """Apply score averaging fusion."""
        doc_scores = {}

        for source_results in results.values():
            for result in source_results:
                doc_id = result.document.id

                if doc_id not in doc_scores:
                    doc_scores[doc_id] = {
                        "document": result.document,
                        "total_score": 0.0,
                        "count": 0,
                    }

                doc_scores[doc_id]["total_score"] += result.final_score
                doc_scores[doc_id]["count"] += 1

        for item in doc_scores.values():
            if item["count"] > 0:
                item["score"] = item["total_score"] / item["count"]

        fused = sorted(doc_scores.values(), key=lambda x: x["score"], reverse=True)

        final_results = []
        for i, item in enumerate(fused):
            result = SearchResult(
                document=item["document"],
                similarity_score=0.0,
                keyword_score=0.0,
                final_score=item["score"],
                rank=i + 1,
                embedding_model_used="fusion",
                matched_content="",
                match_explanation="Score averaging fusion",
            )
            final_results.append(result)

        return final_results

    def _confidence_weighted_fusion(
        self, results: Dict[str, List[SearchResult]]
    ) -> List[SearchResult]:
        """Apply confidence-weighted fusion."""
        return self._score_averaging_fusion(results)

    def _update_ranks(self, results: List[SearchResult]) -> None:
        """Update ranks for a list of results."""
        for i, result in enumerate(results):
            result.rank = i + 1

    def get_stats(self) -> Dict[str, Any]:
        """Get fusion statistics."""
        return {
            "default_strategy": self.default_strategy.value,
            "query_type_weights": {k.value: v for k, v in self.query_type_weights.items()},
        }
