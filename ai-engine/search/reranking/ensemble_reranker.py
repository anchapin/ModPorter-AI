"""
Ensemble re-ranker combining multiple re-ranking strategies.
"""

import logging
from typing import List, Dict, Any, Tuple
from collections import defaultdict

from schemas.multimodal_schema import SearchQuery, SearchResult

from .feature_reranker import FeatureBasedReRanker
from .contextual_reranker import ContextualReRanker

logger = logging.getLogger(__name__)


class EnsembleReRanker:
    """
    Ensemble re-ranker that combines multiple re-ranking strategies.

    This re-ranker uses multiple approaches and combines their outputs
    for more robust ranking decisions.
    """

    def __init__(self):
        self.feature_reranker = FeatureBasedReRanker()
        self.contextual_reranker = ContextualReRanker()
        self.strategy_weights = {"feature_based": 0.7, "contextual": 0.3}

    def ensemble_rerank(
        self, query: SearchQuery, results: List[SearchResult], session_id: str = "default"
    ) -> Tuple[List[SearchResult], Dict[str, Any]]:
        """
        Re-rank using ensemble of strategies.

        Args:
            query: Search query
            results: Initial results
            session_id: Session identifier for contextual ranking

        Returns:
            Tuple of (reranked_results, explanation_metadata)
        """
        if not results:
            return results, {}

        logger.info(f"Ensemble re-ranking {len(results)} results")

        feature_results, feature_explanations = self.feature_reranker.rerank_results(
            query, results.copy()
        )

        contextual_results = self.contextual_reranker.contextual_rerank(
            query, results.copy(), session_id
        )

        final_results = self._combine_rankings(
            [
                (feature_results, self.strategy_weights["feature_based"]),
                (contextual_results, self.strategy_weights["contextual"]),
            ]
        )

        self.contextual_reranker.update_session_context(query, final_results)

        explanation_metadata = {
            "strategies_used": list(self.strategy_weights.keys()),
            "strategy_weights": self.strategy_weights,
            "feature_explanations": feature_explanations,
            "total_candidates": len(results),
            "reranked_candidates": len(final_results),
        }

        return final_results, explanation_metadata

    def _combine_rankings(
        self, strategy_results: List[Tuple[List[SearchResult], float]]
    ) -> List[SearchResult]:
        """Combine rankings from multiple strategies."""
        if not strategy_results:
            return []

        result_map = defaultdict(list)

        for results, weight in strategy_results:
            for result in results:
                result_map[result.document.id].append((result, weight))

        combined_results = []

        for doc_id, result_weight_pairs in result_map.items():
            if not result_weight_pairs:
                continue

            base_result = result_weight_pairs[0][0]

            total_weighted_score = 0.0
            total_weight = 0.0

            for result, weight in result_weight_pairs:
                total_weighted_score += result.final_score * weight
                total_weight += weight

            combined_score = total_weighted_score / total_weight if total_weight > 0 else 0.0

            combined_result = SearchResult(
                document=base_result.document,
                similarity_score=base_result.similarity_score,
                keyword_score=base_result.keyword_score,
                final_score=combined_score,
                rank=0,
                embedding_model_used=base_result.embedding_model_used,
                matched_content=base_result.matched_content,
                match_explanation=f"Ensemble score: {combined_score:.3f}",
            )

            combined_results.append(combined_result)

        combined_results.sort(key=lambda x: x.final_score, reverse=True)
        for i, result in enumerate(combined_results):
            result.rank = i + 1

        return combined_results
