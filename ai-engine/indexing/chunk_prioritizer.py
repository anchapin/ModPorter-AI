"""
Chunk prioritizer for relevance-based ranking.

This module provides:
- RelevanceScore: Dataclass for scoring chunks
- ChunkPrioritizer: Ranks chunks by relevance with explainable scores
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from indexing.chunking_strategies import Chunk


@dataclass
class RelevanceScore:
    """
    Relevance score for a chunk with explanation.

    Attributes:
        chunk_id: Unique identifier for the chunk
        score: Overall relevance score (0-1)
        reasons: List of explanation strings for the score
        keyword_score: Keyword overlap component (0-1)
        position_score: Position-based component (0-1)
        heading_score: Heading context component (0-1)
        semantic_score: Semantic similarity component (0-1)
    """

    chunk_id: str
    score: float
    reasons: List[str] = field(default_factory=list)
    keyword_score: float = 0.0
    position_score: float = 0.0
    heading_score: float = 0.0
    semantic_score: float = 0.0

    def __repr__(self) -> str:
        return f"RelevanceScore(id={self.chunk_id}, score={self.score:.3f})"


class ChunkPrioritizer:
    """
    Prioritizes chunks based on relevance to a query.

    Scoring factors:
    - Keyword overlap (exact matches)
    - Semantic similarity (embedding cosine)
    - Position weight (earlier chunks in document)
    - Heading context (chunks near headings)

    Weights (configurable):
    - keyword_weight: 0.35
    - position_weight: 0.15
    - heading_weight: 0.20
    - semantic_weight: 0.30
    """

    DEFAULT_WEIGHTS = {
        "keyword": 0.35,
        "position": 0.15,
        "heading": 0.20,
        "semantic": 0.30,
    }

    def __init__(
        self, weights: Optional[Dict[str, float]] = None, embedding_model: Optional[Any] = None
    ):
        """
        Initialize the chunk prioritizer.

        Args:
            weights: Custom weights for scoring components
            embedding_model: Optional embedding model for semantic similarity
        """
        self.weights = self.DEFAULT_WEIGHTS.copy()
        if weights:
            self.weights.update(weights)
        self.embedding_model = embedding_model
        self._stop_words = self._load_stop_words()

    def _load_stop_words(self) -> set:
        """Load common stop words to filter out."""
        return {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "can",
            "this",
            "that",
            "these",
            "those",
            "it",
            "its",
            "from",
            "as",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "between",
            "under",
            "again",
            "further",
            "then",
            "once",
        }

    def prioritize(
        self, query: str, chunks: List[Chunk], embeddings: Optional[Dict[str, List[float]]] = None
    ) -> List[Tuple[Chunk, RelevanceScore]]:
        """
        Prioritize chunks by relevance to query.

        Args:
            query: The search query
            chunks: List of chunks to prioritize
            embeddings: Optional dict of chunk_id to embedding vectors

        Returns:
            List of (chunk, RelevanceScore) tuples sorted by relevance
        """
        if not chunks:
            return []

        # Extract query keywords
        query_keywords = self._extract_keywords(query)

        # Score each chunk
        scored_chunks = []

        for chunk in chunks:
            score = self._score_chunk(
                query=query,
                query_keywords=query_keywords,
                chunk=chunk,
                total_chunks=len(chunks),
                embedding=embeddings.get(chunk.content_hash) if embeddings else None,
            )
            scored_chunks.append((chunk, score))

        # Sort by overall score (descending)
        scored_chunks.sort(key=lambda x: x[1].score, reverse=True)

        return scored_chunks

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        # Clean and tokenize
        text = re.sub(r"[^\w\s]", " ", text.lower())
        tokens = text.split()

        # Filter stop words and short tokens
        keywords = [t for t in tokens if t not in self._stop_words and len(t) > 2]

        return keywords

    def _score_chunk(
        self,
        query: str,
        query_keywords: List[str],
        chunk: Chunk,
        total_chunks: int,
        embedding: Optional[List[float]] = None,
    ) -> RelevanceScore:
        """Score a single chunk against the query."""
        reasons = []

        # 1. Keyword overlap score
        keyword_score, keyword_reasons = self._calculate_keyword_score(query_keywords, chunk)
        reasons.extend(keyword_reasons)

        # 2. Position score
        position_score, position_reason = self._calculate_position_score(chunk.index, total_chunks)
        if position_reason:
            reasons.append(position_reason)

        # 3. Heading context score
        heading_score, heading_reason = self._calculate_heading_score(chunk)
        if heading_reason:
            reasons.append(heading_reason)

        # 4. Semantic similarity score
        semantic_score = 0.0
        if embedding and self.embedding_model:
            semantic_score, semantic_reason = self._calculate_semantic_score(
                query, chunk, embedding
            )
            if semantic_reason:
                reasons.append(semantic_reason)

        # Combine scores with weights
        weights = self.weights
        final_score = (
            weights["keyword"] * keyword_score
            + weights["position"] * position_score
            + weights["heading"] * heading_score
            + weights["semantic"] * semantic_score
        )

        # Normalize score to 0-1
        final_score = min(max(final_score, 0.0), 1.0)

        return RelevanceScore(
            chunk_id=str(chunk.index),
            score=final_score,
            reasons=reasons,
            keyword_score=keyword_score,
            position_score=position_score,
            heading_score=heading_score,
            semantic_score=semantic_score,
        )

    def _calculate_keyword_score(
        self, query_keywords: List[str], chunk: Chunk
    ) -> Tuple[float, List[str]]:
        """Calculate keyword overlap score."""
        if not query_keywords:
            return 0.0, []

        # Extract chunk keywords
        chunk_keywords = self._extract_keywords(chunk.content)

        if not chunk_keywords:
            return 0.0, []

        # Calculate overlap
        query_set = set(query_keywords)
        chunk_set = set(chunk_keywords)

        exact_matches = query_set & chunk_set
        partial_matches = 0

        # Check for partial matches (stemming-like)
        for q in query_set:
            for c in chunk_set:
                if q in c or c in q:
                    if q != c:
                        partial_matches += 1
                    break

        # Calculate score
        total_matches = len(exact_matches) + (partial_matches * 0.5)
        score = min(total_matches / len(query_set), 1.0)

        reasons = []
        if exact_matches:
            reasons.append(f"Exact keyword matches: {', '.join(exact_matches)}")
        if partial_matches:
            reasons.append(f"Partial keyword matches: {partial_matches}")

        return score, reasons

    def _calculate_position_score(self, chunk_index: int, total_chunks: int) -> Tuple[float, str]:
        """
        Calculate position-based score.

        Earlier chunks in a document tend to be more important
        (introduction, overview, etc.)
        """
        if total_chunks <= 1:
            return 1.0, "First chunk in document"

        # Position ratio (0 = first, 1 = last)
        position_ratio = chunk_index / (total_chunks - 1)

        # Score decreases linearly from first to last
        score = 1.0 - (position_ratio * 0.5)

        reason = ""
        if chunk_index == 0:
            reason = "First chunk - highest position priority"
        elif chunk_index < total_chunks // 3:
            reason = f"Early chunk (position {chunk_index + 1}/{total_chunks})"

        return score, reason

    def _calculate_heading_score(self, chunk: Chunk) -> Tuple[float, str]:
        """
        Calculate heading context score.

        Chunks near headings are more likely to contain
        relevant topic-specific content.
        """
        score = 0.0
        reasons = []

        # Check if chunk has original heading
        if chunk.original_heading:
            score += 0.5
            reasons.append(f"Near heading: '{chunk.original_heading}'")

        # Check heading context
        if chunk.heading_context:
            # More heading context = higher score
            context_bonus = min(len(chunk.heading_context) * 0.1, 0.5)
            score += context_bonus
            if not reasons:
                reasons.append(f"Heading context: {len(chunk.heading_context)} headings")

        # Normalize to 0-1
        score = min(score, 1.0)

        reason = reasons[0] if reasons else ""

        return score, reason

    def _calculate_semantic_score(
        self, query: str, chunk: Chunk, chunk_embedding: List[float]
    ) -> Tuple[float, str]:
        """
        Calculate semantic similarity score.

        Uses embedding cosine similarity if available.
        """
        # This is a placeholder - actual implementation would use
        # the embedding model to compute cosine similarity
        # For now, return a default score

        # In production, this would be:
        # query_embedding = self.embedding_model.encode(query)
        # similarity = cosine_similarity(query_embedding, chunk_embedding)

        # Return moderate score as placeholder
        return 0.5, "Semantic similarity (placeholder)"

    def get_top_chunks(
        self,
        query: str,
        chunks: List[Chunk],
        top_k: int = 10,
        embeddings: Optional[Dict[str, List[float]]] = None,
    ) -> List[Chunk]:
        """
        Get top K chunks by relevance.

        Args:
            query: The search query
            chunks: List of chunks
            top_k: Number of top chunks to return
            embeddings: Optional embeddings for semantic scoring

        Returns:
            List of top K chunks
        """
        scored = self.prioritize(query, chunks, embeddings)
        return [chunk for chunk, _ in scored[:top_k]]

    def explain_scores(
        self, query: str, chunks: List[Chunk], embeddings: Optional[Dict[str, List[float]]] = None
    ) -> List[RelevanceScore]:
        """
        Get detailed score explanations for chunks.

        Args:
            query: The search query
            chunks: List of chunks
            embeddings: Optional embeddings

        Returns:
            List of RelevanceScore objects with explanations
        """
        scored = self.prioritize(query, chunks, embeddings)
        return [score for _, score in scored]
