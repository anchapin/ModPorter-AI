"""
Hybrid re-ranker combining multiple re-ranking strategies.
"""

import logging
from typing import Any, List

from schemas.multimodal_schema import SearchResult

from .base import ReRankingResult

logger = logging.getLogger(__name__)


class HybridReRanker:
    """
    Hybrid re-ranker combining multiple re-ranking strategies.

    This re-ranker combines cross-encoder, neural, and feature-based
    reranking to achieve better overall relevance ranking.
    """

    def __init__(
        self, rerankers: List[Any] = None, weights: List[float] = None, strategy: str = "weighted"
    ):
        """
        Initialize hybrid re-ranker.

        Args:
            rerankers: List of re-ranker instances
            weights: Weights for each re-ranker's scores
            strategy: Combination strategy ('weighted', 'rrf', 'cascade')
        """
        self.rerankers = rerankers or []
        self.weights = weights or [1.0] * len(self.rerankers)
        self.strategy = strategy

        if len(self.weights) != len(self.rerankers):
            self.weights = [1.0 / len(self.rerankers)] * len(self.rerankers)

        logger.info(f"HybridReRanker initialized with {len(self.rerankers)} rerankers")

    def rerank(
        self, query: str, results: List[SearchResult], top_k: int = None
    ) -> List[ReRankingResult]:
        """
        Re-rank using multiple strategies.
        """
        if not results:
            return []

        if not self.rerankers:
            return self._simple_rerank(results, top_k)

        all_scores = []
        for reranker in self.rerankers:
            try:
                reranked = reranker.rerank(query, results)
                scores = [r.final_score for r in reranked]
                all_scores.append(scores)
            except Exception as e:
                logger.warning(f"Reranker failed: {e}")
                all_scores.append(None)

        if self.strategy == "weighted":
            combined = self._weighted_combination(results, all_scores)
        elif self.strategy == "rrf":
            combined = self._rrf_combination(results, all_scores)
        else:
            combined = self._weighted_combination(results, all_scores)

        final_results = []
        for i, (result, score) in enumerate(zip(results, combined)):
            final_results.append(
                ReRankingResult(
                    document=result.document,
                    original_rank=result.rank,
                    new_rank=0,
                    original_score=result.final_score,
                    reranked_score=score,
                    final_score=score,
                    features_used=[],
                    relevance_features={
                        "hybrid_score": score,
                        "reranker_count": len([s for s in all_scores if s]),
                    },
                    confidence=score,
                    explanation=f"Hybrid score: {score:.4f}",
                )
            )

        final_results.sort(key=lambda x: x.final_score, reverse=True)

        for i, r in enumerate(final_results):
            r.new_rank = i + 1

        return final_results[:top_k] if top_k else final_results

    def _weighted_combination(
        self, results: List[SearchResult], all_scores: List[List[float]]
    ) -> List[float]:
        """Weighted combination of scores."""
        combined = [0.0] * len(results)
        total_weight = 0.0

        for scores, weight in zip(all_scores, self.weights):
            if scores is None:
                continue
            for i, score in enumerate(scores):
                combined[i] += score * weight
            total_weight += weight

        if total_weight > 0:
            combined = [s / total_weight * len(self.weights) for s in combined]

        return combined

    def _rrf_combination(
        self, results: List[SearchResult], all_scores: List[List[float]]
    ) -> List[float]:
        """Reciprocal Rank Fusion combination."""
        k = 60

        combined = [0.0] * len(results)

        for scores in all_scores:
            if scores is None:
                continue
            ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
            for rank, idx in enumerate(ranked_indices):
                combined[idx] += 1.0 / (k + rank + 1)

        return combined

    def _simple_rerank(
        self, results: List[SearchResult], top_k: int = None
    ) -> List[ReRankingResult]:
        """Simple fallback reranking."""
        reranked = []
        for i, r in enumerate(results):
            combined = 0.5 * r.similarity_score + 0.5 * r.keyword_score
            reranked.append(
                ReRankingResult(
                    document=r.document,
                    original_rank=r.rank,
                    new_rank=0,
                    original_score=r.final_score,
                    reranked_score=combined,
                    final_score=combined,
                    features_used=[],
                    relevance_features={"fallback": combined},
                    confidence=combined,
                    explanation=f"Fallback combined score: {combined:.4f}",
                )
            )

        reranked.sort(key=lambda x: x.final_score, reverse=True)
        for i, r in enumerate(reranked):
            r.new_rank = i + 1

        return reranked[:top_k] if top_k else reranked
