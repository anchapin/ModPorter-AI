"""
Base dataclasses and enums for re-ranking.
"""

import logging
from enum import Enum
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ReRankingStrategy(str, Enum):
    """Re-ranking strategies available."""

    CROSS_ENCODER = "cross_encoder"
    FEATURE_BASED = "feature_based"
    NEURAL_RERANKER = "neural_reranker"
    ENSEMBLE = "ensemble"
    CONTEXTUAL = "contextual"


class ReRankingFeature:
    """Feature used for re-ranking with its weight and value."""

    def __init__(self, name: str, value: float, weight: float, explanation: str):
        self.name = name
        self.value = value
        self.weight = weight
        self.explanation = explanation

    def __repr__(self) -> str:
        return (
            f"ReRankingFeature(name={self.name}, value={self.value:.3f}, weight={self.weight:.3f})"
        )


class ReRankingResult:
    """Result of re-ranking with detailed explanation."""

    def __init__(
        self,
        document: Any,
        original_rank: int,
        new_rank: int,
        original_score: float,
        reranked_score: float,
        final_score: float,
        features_used: List[ReRankingFeature],
        relevance_features: Dict[str, Any],
        confidence: float,
        explanation: str,
    ):
        self.document = document
        self.original_rank = original_rank
        self.new_rank = new_rank
        self.original_score = original_score
        self.reranked_score = reranked_score
        self.final_score = final_score
        self.features_used = features_used
        self.relevance_features = relevance_features
        self.confidence = confidence
        self.explanation = explanation

    def __repr__(self) -> str:
        return f"ReRankingResult(doc={getattr(self.document, 'id', 'unknown')}, rank: {self.original_rank} -> {self.new_rank})"
