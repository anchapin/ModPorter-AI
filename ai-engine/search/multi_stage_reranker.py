"""
Multi-stage reranker for sequential application of multiple reranking strategies.

This module provides a configurable multi-stage reranking system that applies
different reranking strategies in sequence for improved result quality.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from schemas.multimodal_schema import SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class ReRankingStrategy(str, Enum):
    """Re-ranking strategies available."""

    CROSS_ENCODER = "cross_encoder"
    FEATURE_BASED = "feature_based"
    NEURAL_RERANKER = "neural_reranker"
    ENSEMBLE = "ensemble"
    CONTEXTUAL = "contextual"


@dataclass
class RerankStageConfig:
    """Configuration for a single reranking stage."""

    name: str
    strategy: ReRankingStrategy
    top_k: Optional[int] = None
    weight: float = 1.0
    model_name: Optional[str] = None


STANDARD = [
    RerankStageConfig(
        name="feature", strategy=ReRankingStrategy.FEATURE_BASED, top_k=50, weight=0.6
    ),
    RerankStageConfig(
        name="cross_encoder",
        strategy=ReRankingStrategy.CROSS_ENCODER,
        top_k=20,
        weight=0.4,
        model_name="msmarco",
    ),
]

LIGHTWEIGHT = [
    RerankStageConfig(
        name="feature", strategy=ReRankingStrategy.FEATURE_BASED, top_k=30, weight=1.0
    ),
]

COMPREHENSIVE = [
    RerankStageConfig(
        name="feature", strategy=ReRankingStrategy.FEATURE_BASED, top_k=100, weight=0.3
    ),
    RerankStageConfig(
        name="neural", strategy=ReRankingStrategy.NEURAL_RERANKER, top_k=50, weight=0.3
    ),
    RerankStageConfig(
        name="cross_encoder",
        strategy=ReRankingStrategy.CROSS_ENCODER,
        top_k=20,
        weight=0.25,
        model_name="msmarco",
    ),
    RerankStageConfig(name="ensemble", strategy=ReRankingStrategy.ENSEMBLE, top_k=10, weight=0.15),
]


@dataclass
class RerankStageResult:
    """Result from a single reranking stage."""

    stage_name: str
    original_results: List[SearchResult]
    reranked_results: List[SearchResult]
    score_changes: List[float]
    execution_time_ms: float


class MultiStageReranker:
    """
    Multi-stage reranker that applies sequential reranking strategies.

    Each stage can reduce or expand the result set, and scores are combined
    using configurable weighting strategies.
    """

    def __init__(self, stages: List[RerankStageConfig] = None):
        self.stages = stages or STANDARD
        self.rerankers = {}
        self._init_rerankers()
        self.stage_history: List[RerankStageResult] = []

        logger.info(f"MultiStageReranker initialized with {len(self.stages)} stages")

    def _init_rerankers(self):
        """Initialize reranker instances."""
        try:
            from search.reranking_engine import (
                ContextualReRanker,
                CrossEncoderReRanker,
                EnsembleReRanker,
                FeatureBasedReRanker,
                NeuralReRanker,
            )

            for stage in self.stages:
                if stage.strategy == ReRankingStrategy.FEATURE_BASED:
                    if "feature" not in self.rerankers:
                        self.rerankers["feature"] = FeatureBasedReRanker()

                elif stage.strategy == ReRankingStrategy.CROSS_ENCODER:
                    if "cross_encoder" not in self.rerankers:
                        self.rerankers["cross_encoder"] = CrossEncoderReRanker(
                            model_name=stage.model_name or "msmarco"
                        )

                elif stage.strategy == ReRankingStrategy.NEURAL_RERANKER:
                    if "neural" not in self.rerankers:
                        self.rerankers["neural"] = NeuralReRanker()

                elif stage.strategy == ReRankingStrategy.ENSEMBLE:
                    if "ensemble" not in self.rerankers:
                        self.rerankers["ensemble"] = EnsembleReRanker()

                elif stage.strategy == ReRankingStrategy.CONTEXTUAL:
                    if "contextual" not in self.rerankers:
                        self.rerankers["contextual"] = ContextualReRanker()

        except ImportError as e:
            logger.warning(f"Could not import rerankers: {e}")

    def rerank(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """
        Apply multi-stage reranking to results.

        Args:
            query: Original search query
            results: List of search results to rerank

        Returns:
            Reranked list of search results
        """
        if not results:
            return results

        import time

        self.stage_history = []

        current_results = results.copy()
        stage_names = []

        for stage_config in self.stages:
            if not current_results:
                break

            stage_start = time.time()

            if stage_config.strategy == ReRankingStrategy.FEATURE_BASED:
                current_results = self._rerank_feature(current_results, stage_config, query)

            elif stage_config.strategy == ReRankingStrategy.CROSS_ENCODER:
                current_results = self._rerank_cross_encoder(current_results, stage_config, query)

            elif stage_config.strategy == ReRankingStrategy.NEURAL_RERANKER:
                current_results = self._rerank_neural(current_results, stage_config, query)

            elif stage_config.strategy == ReRankingStrategy.ENSEMBLE:
                current_results = self._rerank_ensemble(current_results, stage_config, query)

            elif stage_config.strategy == ReRankingStrategy.CONTEXTUAL:
                current_results = self._rerank_contextual(current_results, stage_config, query)

            if stage_config.top_k and len(current_results) > stage_config.top_k:
                current_results = current_results[: stage_config.top_k]

            exec_time = (time.time() - stage_start) * 1000
            score_changes = self._calculate_score_changes(results, current_results)

            stage_result = RerankStageResult(
                stage_name=stage_config.name,
                original_results=results,
                reranked_results=current_results.copy(),
                score_changes=score_changes,
                execution_time_ms=exec_time,
            )
            self.stage_history.append(stage_result)
            stage_names.append(stage_config.name)

            logger.info(
                f"Stage '{stage_config.name}' completed in {exec_time:.2f}ms, "
                f"{len(current_results)} results"
            )

        for i, r in enumerate(current_results):
            r.rank = i + 1

        return current_results

    def _rerank_feature(
        self, results: List[SearchResult], stage_config: RerankStageConfig, query: str
    ) -> List[SearchResult]:
        """Apply feature-based reranking."""
        reranker = self.rerankers.get("feature")
        if not reranker:
            return results

        try:
            search_query = SearchQuery(query_text=query, top_k=len(results))
            reranked, _ = reranker.rerank_results(search_query, results)
            return reranked
        except Exception as e:
            logger.warning(f"Feature reranking failed: {e}")
            return results

    def _rerank_cross_encoder(
        self, results: List[SearchResult], stage_config: RerankStageConfig, query: str
    ) -> List[SearchResult]:
        """Apply cross-encoder reranking."""
        reranker = self.rerankers.get("cross_encoder")
        if not reranker:
            return results

        try:
            ce_results = reranker.rerank(query, results)
            if ce_results:
                result_map = {r.document.id: r for r in results}
                for ce_r in ce_results:
                    if ce_r.document.id in result_map:
                        result_map[ce_r.document.id].final_score = ce_r.final_score
                results.sort(key=lambda x: x.final_score, reverse=True)
            return results
        except Exception as e:
            logger.warning(f"Cross-encoder reranking failed: {e}")
            return results

    def _rerank_neural(
        self, results: List[SearchResult], stage_config: RerankStageConfig, query: str
    ) -> List[SearchResult]:
        """Apply neural reranking."""
        reranker = self.rerankers.get("neural")
        if not reranker:
            return results

        try:
            ce_results = reranker.rerank(query, results)
            if ce_results:
                result_map = {r.document.id: r for r in results}
                for ce_r in ce_results:
                    if ce_r.document.id in result_map:
                        result_map[ce_r.document.id].final_score = ce_r.final_score
                results.sort(key=lambda x: x.final_score, reverse=True)
            return results
        except Exception as e:
            logger.warning(f"Neural reranking failed: {e}")
            return results

    def _rerank_ensemble(
        self, results: List[SearchResult], stage_config: RerankStageConfig, query: str
    ) -> List[SearchResult]:
        """Apply ensemble reranking."""
        reranker = self.rerankers.get("ensemble")
        if not reranker:
            return results

        try:
            search_query = SearchQuery(query_text=query, top_k=len(results))
            reranked, _ = reranker.ensemble_rerank(search_query, results)
            return reranked
        except Exception as e:
            logger.warning(f"Ensemble reranking failed: {e}")
            return results

    def _rerank_contextual(
        self, results: List[SearchResult], stage_config: RerankStageConfig, query: str
    ) -> List[SearchResult]:
        """Apply contextual reranking."""
        reranker = self.rerankers.get("contextual")
        if not reranker:
            return results

        try:
            search_query = SearchQuery(query_text=query, top_k=len(results))
            return reranker.contextual_rerank(search_query, results)
        except Exception as e:
            logger.warning(f"Contextual reranking failed: {e}")
            return results

    def _calculate_score_changes(
        self, original: List[SearchResult], reranked: List[SearchResult]
    ) -> List[float]:
        """Calculate score changes between original and reranked."""
        if not original or not reranked:
            return []

        original_map = {r.document.id: r.final_score for r in original}
        changes = []

        for r in reranked:
            if r.document.id in original_map:
                changes.append(r.final_score - original_map[r.document.id])

        return changes

    def add_stage(self, name: str, strategy: ReRankingStrategy, config: Dict = None):
        """Add a new reranking stage."""
        stage_config = RerankStageConfig(
            name=name,
            strategy=strategy,
            top_k=config.get("top_k") if config else None,
            weight=config.get("weight", 1.0) if config else 1.0,
            model_name=config.get("model_name") if config else None,
        )
        self.stages.append(stage_config)
        self._init_rerankers()

        logger.info(f"Added reranking stage: {name} with strategy {strategy}")

    def get_stage_history(self) -> List[RerankStageResult]:
        """Get the history of reranking stages applied."""
        return self.stage_history

    def should_continue(self, results: List[SearchResult]) -> bool:
        """Check if more reranking stages should be applied based on convergence."""
        if len(self.stage_history) < 2:
            return True

        last_changes = self.stage_history[-1].score_changes
        if not last_changes:
            return False

        avg_change = sum(abs(c) for c in last_changes) / len(last_changes)

        return avg_change > 0.01

    def get_stats(self) -> Dict[str, Any]:
        """Get reranking statistics."""
        total_time = sum(s.execution_time_ms for s in self.stage_history)
        return {
            "stages_count": len(self.stages),
            "stages_applied": len(self.stage_history),
            "total_time_ms": total_time,
            "stage_times": {s.stage_name: s.execution_time_ms for s in self.stage_history},
        }
