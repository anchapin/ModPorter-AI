"""
Re-ranking engine for improving search result quality.

This module is DEPRECATED. Import from `search.reranking` instead.

This module implements various re-ranking strategies to improve the final
ordering of search results based on additional relevance signals.
"""

import warnings

warnings.warn(
    "reranking_engine module is deprecated. Import from search.reranking instead.",
    DeprecationWarning,
    stacklevel=2,
)

from search.reranking import (
    ReRankingStrategy,
    ReRankingFeature,
    ReRankingResult,
    FeatureBasedReRanker,
    ContextualReRanker,
    EnsembleReRanker,
    CrossEncoderReRanker,
    NeuralReRanker,
    HybridReRanker,
)

__all__ = [
    "ReRankingStrategy",
    "ReRankingFeature",
    "ReRankingResult",
    "FeatureBasedReRanker",
    "ContextualReRanker",
    "EnsembleReRanker",
    "CrossEncoderReRanker",
    "NeuralReRanker",
    "HybridReRanker",
]
