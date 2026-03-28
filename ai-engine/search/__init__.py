"""
Search module for RAG system.

This module provides hybrid search capabilities combining keyword and semantic search,
along with reranking functionality for improved result quality.
"""

# Import directly from modules (not relative imports)
from search.hybrid_search_engine import (
    HybridSearchEngine,
    UnifiedSearchEngine,
    KeywordSearchEngine,
    SearchMode,
    RankingStrategy,
    SearchCandidate,
)

from search.feedback_reranker import FeedbackReranker, FeedbackBoost, rerank_with_feedback

from search.reranking_engine import (
    CrossEncoderReRanker,
    NeuralReRanker,
    HybridReRanker,
    FeatureBasedReRanker,
    ContextualReRanker,
    EnsembleReRanker,
    ReRankingStrategy,
    ReRankingFeature,
    ReRankingResult,
)

from search.query_expansion import (
    QueryExpansionEngine,
    ExpansionStrategy,
    ExpansionTerm,
    ExpandedQuery,
    MinecraftDomainExpander,
    SynonymExpander,
    ContextualExpander,
)

from search.query_complexity_analyzer import (
    QueryComplexityAnalyzer,
    ComplexityLevel,
    ComplexityAnalysis,
    analyze_query_complexity,
)

from search.context_manager import (
    DynamicContextSizer,
    ContextManager,
    ContextConfig,
    ContextStrategy,
    Turn,
)

# Alias for backwards compatibility
QueryExpander = QueryExpansionEngine

__all__ = [
    # Hybrid search
    "HybridSearchEngine",
    "UnifiedSearchEngine",
    "KeywordSearchEngine",
    "SearchMode",
    "RankingStrategy",
    "SearchCandidate",
    # Feedback reranking
    "FeedbackReranker",
    "FeedbackBoost",
    "rerank_with_feedback",
    # Reranking
    "CrossEncoderReRanker",
    "NeuralReRanker",
    "HybridReRanker",
    "FeatureBasedReRanker",
    "ContextualReRanker",
    "EnsembleReRanker",
    "ReRankingStrategy",
    "ReRankingFeature",
    "ReRankingResult",
    # Query expansion
    "QueryExpansionEngine",
    "QueryExpander",
    "ExpansionStrategy",
    "ExpansionTerm",
    "ExpandedQuery",
    "MinecraftDomainExpander",
    "SynonymExpander",
    "ContextualExpander",
    # Query complexity analysis
    "QueryComplexityAnalyzer",
    "ComplexityLevel",
    "ComplexityAnalysis",
    "analyze_query_complexity",
    # Context management
    "DynamicContextSizer",
    "ContextManager",
    "ContextConfig",
    "ContextStrategy",
    "Turn",
]
