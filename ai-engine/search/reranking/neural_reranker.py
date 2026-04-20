"""
Neural network-based re-ranker using bi-encoder embeddings.
"""

import logging
from typing import List, Optional

from schemas.multimodal_schema import SearchResult

from .base import ReRankingResult

logger = logging.getLogger(__name__)


class NeuralReRanker:
    """
    Neural network-based re-ranker using bi-encoder embeddings.

    This re-ranker uses sentence transformer embeddings to compute
    semantic similarity between query and documents for re-ranking.
    """

    DEFAULT_EMBEDDING_MODELS = [
        "all-MiniLM-L6-v2",
        "all-mpnet-base-v2",
        "multi-qa-mpnet-base-dot-v1",
    ]

    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        device: str = "cpu",
        score_combination: str = "weighted",
    ):
        """
        Initialize the neural re-ranker.

        Args:
            embedding_model: Name of the embedding model
            device: Device to run embeddings on
            score_combination: How to combine scores ('weighted', 'rrf', 'additive')
        """
        self.embedding_model = embedding_model
        self.device = device
        self.score_combination = score_combination
        self.model = None
        self._is_loaded = False

        logger.info(f"NeuralReRanker initialized with model: {embedding_model}")

    def _load_model(self):
        """Load the embedding model."""
        if self._is_loaded:
            return

        try:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(self.embedding_model, device=self.device)
            self._is_loaded = True
            logger.info(f"Embedding model loaded: {self.embedding_model}")

        except ImportError:
            logger.warning("sentence-transformers not installed")
            self._is_loaded = False

    def rerank(
        self, query: str, results: List[SearchResult], top_k: int = None
    ) -> List[ReRankingResult]:
        """
        Re-rank results using neural embeddings.
        """
        if not results:
            return []

        self._load_model()

        if not self._is_loaded:
            return self._fallback_rerank(query, results, top_k)

        docs = []
        for result in results:
            content = result.matched_content or ""
            if hasattr(result.document, "content"):
                content = result.document.content[:1000]
            docs.append(content)

        try:
            query_embedding = self.model.encode(query, convert_to_tensor=True)
            doc_embeddings = self.model.encode(docs, convert_to_tensor=True)

            from sentence_transformers import util

            scores = util.cos_sim(query_embedding, doc_embeddings)[0].tolist()

            reranked_results = []
            for i, (result, score) in enumerate(zip(results, scores)):
                reranked_results.append(
                    ReRankingResult(
                        document=result.document,
                        original_rank=result.rank,
                        new_rank=0,
                        original_score=result.final_score,
                        final_score=float(score),
                        features_used=[],
                        relevance_features={
                            "neural_similarity": float(score),
                            "original_similarity": result.similarity_score,
                            "keyword_score": result.keyword_score,
                        },
                        confidence=float(score),
                        explanation=f"Neural similarity: {score:.4f}",
                    )
                )

            reranked_results.sort(key=lambda x: x.final_score, reverse=True)

            for i, r in enumerate(reranked_results):
                r.new_rank = i + 1

            if top_k:
                return reranked_results[:top_k]
            return reranked_results

        except Exception as e:
            logger.error(f"Neural reranking error: {e}")
            return self._fallback_rerank(query, results, top_k)

    def _fallback_rerank(
        self, query: str, results: List[SearchResult], top_k: int = None
    ) -> List[ReRankingResult]:
        """Fallback to simple score combination."""
        return self._simple_rerank(results, top_k)

    def _simple_rerank(
        self, results: List[SearchResult], top_k: int = None
    ) -> List[ReRankingResult]:
        """Simple re-ranking based on existing scores."""
        reranked = []
        for i, r in enumerate(results):
            combined = 0.6 * r.similarity_score + 0.4 * r.keyword_score
            reranked.append(
                ReRankingResult(
                    document=r.document,
                    original_rank=r.rank,
                    new_rank=0,
                    original_score=r.final_score,
                    reranked_score=combined,
                    final_score=combined,
                    features_used=[],
                    relevance_features={"combined": combined},
                    confidence=combined,
                    explanation=f"Fallback combined score: {combined:.4f}",
                )
            )

        reranked.sort(key=lambda x: x.final_score, reverse=True)
        for i, r in enumerate(reranked):
            r.new_rank = i + 1

        return reranked[:top_k] if top_k else reranked
