"""
Hybrid Search for RAG

Combines semantic search (vector similarity) with keyword search (BM25).
"""

import logging
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)


class HybridSearch:
    """Hybrid search combining semantic and keyword search."""
    
    def __init__(self):
        self._examples = []
        self._embeddings = None
        self._bm25_index = None
    
    def index_examples(
        self,
        examples: List[Dict[str, Any]],
        embeddings: np.ndarray,
    ):
        """
        Index examples for search.
        
        Args:
            examples: List of examples
            embeddings: Pre-computed embeddings matrix
        """
        self._examples = examples
        self._embeddings = embeddings
        
        # Build BM25 index for keyword search
        self._build_bm25_index(examples)
        
        logger.info(f"Indexed {len(examples)} examples for hybrid search")
    
    def _build_bm25_index(self, examples: List[Dict[str, Any]]):
        """Build BM25 index for keyword search."""
        try:
            from rank_bm25 import BM25Okapi
            
            # Tokenize documents
            documents = []
            for ex in examples:
                text = f"{ex.get('java_code', '')} {ex.get('metadata', {})}"
                tokens = text.lower().split()
                documents.append(tokens)
            
            self._bm25_index = BM25Okapi(documents)
            logger.debug("BM25 index built")
            
        except ImportError:
            logger.warning("rank-bm25 not installed. Using simple keyword search.")
            self._bm25_index = None
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        query_embedding: Optional[np.ndarray] = None,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining semantic and keyword search.
        
        Args:
            query: Search query
            top_k: Number of results
            semantic_weight: Weight for semantic search (0-1)
            keyword_weight: Weight for keyword search (0-1)
            query_embedding: Pre-computed query embedding
        
        Returns:
            List of results with scores
        """
        if not self._examples:
            return []
        
        # Get semantic scores
        semantic_scores = self._semantic_search(query_embedding, query)
        
        # Get keyword scores
        keyword_scores = self._keyword_search(query)
        
        # Combine scores
        combined_scores = []
        for i, example in enumerate(self._examples):
            semantic_score = semantic_scores.get(i, 0.0)
            keyword_score = keyword_scores.get(i, 0.0)
            
            combined_score = (
                semantic_weight * semantic_score +
                keyword_weight * keyword_score
            )
            
            combined_scores.append({
                "example": example,
                "score": combined_score,
                "semantic_score": semantic_score,
                "keyword_score": keyword_score,
            })
        
        # Sort by combined score
        combined_scores.sort(key=lambda x: x["score"], reverse=True)
        
        return combined_scores[:top_k]
    
    def _semantic_search(
        self,
        query_embedding: Optional[np.ndarray],
        query: str,
    ) -> Dict[int, float]:
        """
        Semantic search using vector similarity.
        
        Args:
            query_embedding: Query embedding (or None to compute from query)
            query: Query text
        
        Returns:
            Dict mapping example index to similarity score
        """
        if self._embeddings is None or len(self._examples) == 0:
            return {}
        
        # Use provided embedding or compute from query
        if query_embedding is None:
            from .embedding_generator import get_embedding_generator
            generator = get_embedding_generator()
            query_embedding = generator.generate_embedding(query)
        
        # Compute cosine similarity
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)
        
        scores = {}
        for i, embedding in enumerate(self._embeddings):
            emb_norm = embedding / (np.linalg.norm(embedding) + 1e-8)
            similarity = np.dot(query_norm, emb_norm)
            # Normalize to 0-1 range
            scores[i] = (similarity + 1) / 2
        
        return scores
    
    def _keyword_search(self, query: str) -> Dict[int, float]:
        """
        Keyword search using BM25.
        
        Args:
            query: Search query
        
        Returns:
            Dict mapping example index to score
        """
        if not self._examples:
            return {}
        
        if self._bm25_index is not None:
            # Use BM25
            query_tokens = query.lower().split()
            scores = self._bm25_index.get_scores(query_tokens)
            
            # Normalize to 0-1 range
            max_score = max(scores) if len(scores) > 0 else 1.0
            if max_score > 0:
                scores = scores / max_score
            
            return {i: float(score) for i, score in enumerate(scores)}
        else:
            # Simple keyword matching
            query_lower = query.lower()
            scores = {}
            
            for i, example in enumerate(self._examples):
                text = f"{example.get('java_code', '')} {example.get('metadata', {})}".lower()
                if query_lower in text:
                    scores[i] = 0.8
                else:
                    # Partial match
                    query_words = query_lower.split()
                    matches = sum(1 for word in query_words if word in text)
                    scores[i] = matches / len(query_words) if query_words else 0.0
            
            return scores


# Singleton instance
_hybrid_search = None


def get_hybrid_search() -> HybridSearch:
    """Get or create hybrid search singleton."""
    global _hybrid_search
    if _hybrid_search is None:
        _hybrid_search = HybridSearch()
    return _hybrid_search
