"""
Search module for RAG system.

This module provides hybrid search capabilities combining keyword and semantic search,
along with reranking functionality for improved result quality.
"""

# Import directly from modules (not relative imports)
from search.context_manager import (
    ContextConfig,
    ContextManager,
    ContextStrategy,
    DynamicContextSizer,
    Turn,
)
from search.feedback_reranker import FeedbackBoost, FeedbackReranker, rerank_with_feedback
from search.hybrid_search_engine import (
    HybridSearchEngine,
    KeywordSearchEngine,
    RankingStrategy,
    SearchCandidate,
    SearchMode,
    UnifiedSearchEngine,
)
from search.query_complexity_analyzer import (
    ComplexityAnalysis,
    ComplexityLevel,
    QueryComplexityAnalyzer,
    analyze_query_complexity,
)
from search.query_expansion import (
    ContextualExpander,
    ExpandedQuery,
    ExpansionStrategy,
    ExpansionTerm,
    MinecraftDomainExpander,
    QueryExpansionEngine,
    SynonymExpander,
)
from search.reranking_engine import (
    ContextualReRanker,
    CrossEncoderReRanker,
    EnsembleReRanker,
    FeatureBasedReRanker,
    HybridReRanker,
    NeuralReRanker,
    ReRankingFeature,
    ReRankingResult,
    ReRankingStrategy,
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
