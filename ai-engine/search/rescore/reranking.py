"""
Re-ranking module for improving search result quality.

This module provides various re-ranking strategies including:
- Semantic re-ranking
- Keyword-based re-ranking  
- Hybrid re-ranking
- Cross-encoder re-ranking
- Learning-to-rank approaches
"""

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RerankingStrategy(str, Enum):
    """Available re-ranking strategies."""
    
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
    CROSS_ENCODER = "cross_encoder"
    LEARNING_TO_RANK = "learning_to_rank"


class SearchQuery:
    """Represents a search query."""
    
    def __init__(
        self,
        text: str,
        filters: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.text = text
        self.filters = filters or {}
        self.metadata = metadata or {}


class SearchResult:
    """Represents a search result."""
    
    def __init__(
        self,
        document_id: str,
        content: str,
        score: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.document_id = document_id
        self.content = content
        self.score = score
        self.metadata = metadata or {}


@dataclass
class RerankingConfig:
    """Configuration for re-ranking operations.
    
    Attributes:
        strategy: Re-ranking strategy to use
        top_k: Number of top results to return after re-ranking
        min_score: Minimum score threshold for inclusion
        weight_semantic: Weight for semantic similarity (0-1)
        weight_keyword: Weight for keyword matching (0-1)
        enable_diversity: Whether to apply diversity penalty
        diversity_penalty: Penalty factor for repeated categories
        cross_encoder_model: Model name for cross-encoder re-ranking
    """
    
    strategy: RerankingStrategy = RerankingStrategy.HYBRID
    top_k: int = 10
    min_score: float = 0.0
    weight_semantic: float = 0.6
    weight_keyword: float = 0.4
    enable_diversity: bool = True
    diversity_penalty: float = 0.2
    cross_encoder_model: Optional[str] = None


class ReRankingEngine:
    """
    Engine for re-ranking search results based on various strategies.
    """
    
    def __init__(self, config: RerankingConfig):
        """Initialize the re-ranking engine with configuration.
        
        Args:
            config: RerankingConfig object containing re-ranking settings
        """
        self.config = config
        self._initialize_strategy()
    
    def _initialize_strategy(self) -> None:
        """Initialize the appropriate re-ranking strategy."""
        if self.config.strategy == RerankingStrategy.CROSS_ENCODER:
            if not self.config.cross_encoder_model:
                raise ValueError(
                    "Cross-encoder model must be specified for cross-encoder re-ranking"
                )
    
    def rerank(
        self,
        query: SearchQuery,
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """
        Re-rank search results based on the configured strategy.
        
        Args:
            query: Original search query
            results: List of search results to re-rank
            
        Returns:
            Re-ranked list of search results
        """
        if not results:
            return results
        
        # Apply different re-ranking strategies
        if self.config.strategy == RerankingStrategy.SEMANTIC:
            return self._semantic_rerank(query, results)
        elif self.config.strategy == RerankingStrategy.KEYWORD:
            return self._keyword_rerank(query, results)
        elif self.config.strategy == RerankingStrategy.HYBRID:
            return self._hybrid_rerank(query, results)
        elif self.config.strategy == RerankingStrategy.CROSS_ENCODER:
            return self._cross_encoder_rerank(query, results)
        else:
            return results
    
    def _semantic_rerank(
        self,
        query: SearchQuery,
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """Re-rank based on semantic similarity."""
        # Sort by semantic score
        reranked = sorted(
            results,
            key=lambda x: x.metadata.get("semantic_score", 0.0),
            reverse=True
        )
        return self._apply_diversity(reranked)[:self.config.top_k]
    
    def _keyword_rerank(
        self,
        query: SearchQuery,
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """Re-rank based on keyword matching."""
        # Sort by keyword score
        reranked = sorted(
            results,
            key=lambda x: x.metadata.get("keyword_score", 0.0),
            reverse=True
        )
        return self._apply_diversity(reranked)[:self.config.top_k]
    
    def _hybrid_rerank(
        self,
        query: SearchQuery,
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """Re-rank using a hybrid approach combining semantic and keyword scores."""
        # Calculate combined scores
        for result in results:
            semantic = result.metadata.get("semantic_score", 0.0)
            keyword = result.metadata.get("keyword_score", 0.0)
            combined = (
                self.config.weight_semantic * semantic +
                self.config.weight_keyword * keyword
            )
            result.metadata["hybrid_score"] = combined
        
        # Sort by combined score
        reranked = sorted(
            results,
            key=lambda x: x.metadata.get("hybrid_score", 0.0),
            reverse=True
        )
        return self._apply_diversity(reranked)[:self.config.top_k]
    
    def _cross_encoder_rerank(
        self,
        query: SearchQuery,
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """Re-rank using cross-encoder model (requires model loading)."""
        # Placeholder for cross-encoder re-ranking
        # In practice, would use sentence-transformers cross-encoder
        print(
            f"Cross-encoder re-ranking with model: {self.config.cross_encoder_model}"
        )
        
        # For now, fall back to semantic re-ranking
        return self._semantic_rerank(query, results)
    
    def _apply_diversity(
        self,
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """Apply diversity penalty to promote diverse results.
        
        Args:
            results: Sorted list of results
            
        Returns:
            Results with diversity penalty applied
        """
        if not self.config.enable_diversity:
            return results
        
        # Group by category/type and apply diversity penalty
        used_categories: Dict[str, int] = {}
        
        for result in results:
            category = result.metadata.get("category", "default")
            
            # Apply penalty for repeated categories
            if category in used_categories and used_categories[category] > 0:
                penalty = self.config.diversity_penalty * used_categories[category]
                current_score = result.metadata.get("hybrid_score", 
                                                     result.metadata.get("semantic_score", 0.0))
                result.metadata["diversified_score"] = current_score - penalty
            else:
                result.metadata["diversified_score"] = result.metadata.get(
                    "hybrid_score", result.metadata.get("semantic_score", 0.0)
                )
            
            used_categories[category] = used_categories.get(category, 0) + 1
        
        # Re-sort by diversified score
        return sorted(results, key=lambda x: x.metadata.get("diversified_score", 0.0), reverse=True)


class EnsembleReRanker:
    """
    Ensemble re-ranker combining multiple re-ranking strategies.
    """
    
    def __init__(self, rankers: List[ReRankingEngine]):
        """Initialize ensemble with multiple rankers.
        
        Args:
            rankers: List of ReRankingEngine instances
        """
        self.rankers = rankers
    
    def rerank(
        self,
        query: SearchQuery,
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """
        Re-rank using ensemble of strategies with score aggregation.
        
        Args:
            query: Original search query
            results: List of search results
            
        Returns:
            Re-ranked results from ensemble
        """
        # Get scores from each ranker
        all_scores: Dict[str, List[float]] = defaultdict(list)
        
        for ranker in self.rankers:
            reranked = ranker.rerank(query, results)
            
            # Collect scores
            for result in reranked:
                doc_id = result.document_id
                score = result.metadata.get("hybrid_score",
                                           result.metadata.get("semantic_score", 0.0))
                all_scores[doc_id].append(score)
        
        # Aggregate scores (mean)
        final_scores: Dict[str, float] = {}
        for doc_id, scores in all_scores.items():
            final_scores[doc_id] = sum(scores) / len(scores) if scores else 0.0
        
        # Apply final scores to results and sort
        for result in results:
            result.metadata["ensemble_score"] = final_scores.get(result.document_id, 0.0)
        
        return sorted(
            results,
            key=lambda x: x.metadata.get("ensemble_score", 0.0),
            reverse=True
        )[:self.rankers[0].config.top_k]
