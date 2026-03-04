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
    SearchCandidate
)

from search.reranking_engine import (
    CrossEncoderReRanker,
    NeuralReRanker,
    HybridReRanker,
    FeatureBasedReRanker,
    ContextualReRanker,
    EnsembleReRanker,
    ReRankingStrategy,
    ReRankingFeature,
    ReRankingResult
)

from search.query_expansion import (
    QueryExpansionEngine,
    ExpansionStrategy,
    ExpansionTerm,
    ExpandedQuery,
    MinecraftDomainExpander,
    SynonymExpander,
    ContextualExpander
)

# Alias for backwards compatibility
QueryExpander = QueryExpansionEngine

__all__ = [
    # Hybrid search
    'HybridSearchEngine',
    'UnifiedSearchEngine',
    'KeywordSearchEngine',
    'SearchMode',
    'RankingStrategy',
    'SearchCandidate',
    
    # Reranking
    'CrossEncoderReRanker',
    'NeuralReRanker',
    'HybridReRanker',
    'FeatureBasedReRanker',
    'ContextualReRanker',
    'EnsembleReRanker',
    'ReRankingStrategy',
    'ReRankingFeature',
    'ReRankingResult',
    
    # Query expansion
    'QueryExpansionEngine',
    'QueryExpander',
    'ExpansionStrategy',
    'ExpansionTerm',
    'ExpandedQuery',
    'MinecraftDomainExpander',
    'SynonymExpander',
    'ContextualExpander',
]
