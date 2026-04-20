"""
Cross-encoder based re-ranker for improved search result ranking.
"""

import logging
from typing import List, Dict, Any, Optional

from schemas.multimodal_schema import SearchResult

from .base import ReRankingFeature, ReRankingResult

logger = logging.getLogger(__name__)


class CrossEncoderReRanker:
    """
    Cross-encoder based re-ranker for improved search result ranking.

    This re-ranker uses a cross-encoder neural network to score query-document
    pairs more accurately than bi-encoders. Cross-encoders consider the full
    context of both query and document together, providing more nuanced relevance scoring.

    Cross-encoders are typically more accurate but slower than bi-encoders,
    so they are used for re-ranking a smaller set of candidate results.
    """

    DEFAULT_MODELS = {
        "msmarco": "cross-encoder/ms-marco-MiniLM-L-6-v2",
        "msmarco-large": "cross-encoder/ms-marco-MiniLM-L-12-v2",
        "quora": "cross-encoder/quora-roberta-base",
        "scientific": "cross-encoder/stsb-roberta-base",
        "robust": "cross-encoder/roberta-base-MRPC",
    }

    def __init__(
        self,
        model_name: str = "msmarco",
        device: str = "cpu",
        max_length: int = 512,
        batch_size: int = 32,
        use_pretrained: bool = True,
    ):
        """
        Initialize the cross-encoder re-ranker.

        Args:
            model_name: Name of the cross-encoder model or path to local model
            device: Device to run the model on ('cpu', 'cuda', or 'mps')
            max_length: Maximum sequence length for tokenization
            batch_size: Batch size for scoring multiple documents
            use_pretrained: Whether to load a pretrained model or create a new one
        """
        self.model_name = model_name
        self.device = device
        self.max_length = max_length
        self.batch_size = batch_size
        self.model = None
        self.tokenizer = None
        self.use_pretrained = use_pretrained

        self._is_loaded = False

        self._config = {
            "model_name": model_name,
            "device": device,
            "max_length": max_length,
            "batch_size": batch_size,
        }

        logger.info(f"CrossEncoderReRanker initialized with model: {model_name}")

    def _load_model(self):
        """Load the cross-encoder model and tokenizer."""
        if self._is_loaded:
            return

        try:
            from sentence_transformers import CrossEncoder

            if self.model_name in self.DEFAULT_MODELS:
                full_model_name = self.DEFAULT_MODELS[self.model_name]
            else:
                full_model_name = self.model_name

            self.model = CrossEncoder(
                full_model_name, max_length=self.max_length, device=self.device
            )

            self._is_loaded = True
            logger.info(f"Cross-encoder model loaded: {full_model_name}")

        except ImportError:
            logger.warning("sentence-transformers not installed. Using fallback scoring.")
            self._is_loaded = False
        except Exception as e:
            logger.warning(f"Failed to load cross-encoder model: {e}. Using fallback scoring.")
            self._is_loaded = False

    def rerank(
        self, query: str, results: List[SearchResult], top_k: int = None
    ) -> List[ReRankingResult]:
        """
        Re-rank search results using cross-encoder scoring.

        Args:
            query: The original search query
            results: List of search results to re-rank
            top_k: Number of top results to return (default: all)

        Returns:
            List of re-ranked results
        """
        if not results:
            return []

        self._load_model()

        if not self._is_loaded:
            return self._fallback_rerank(query, results, top_k)

        pairs = []
        for result in results:
            doc_content = result.matched_content or ""
            if hasattr(result.document, "content"):
                doc_content = result.document.content[:1000]
            pairs.append([query, doc_content])

        try:
            scores = self.model.predict(pairs, batch_size=self.batch_size)

            if isinstance(scores, float):
                scores = [scores]

            reranked_results = []
            for i, (result, score) in enumerate(zip(results, scores)):
                reranked_results.append(
                    ReRankingResult(
                        document=result.document,
                        original_rank=result.rank,
                        new_rank=0,
                        original_score=result.final_score,
                        reranked_score=float(score),
                        final_score=float(score),
                        features_used=[
                            ReRankingFeature(
                                name="cross_encoder",
                                weight=1.0,
                                value=float(score),
                                explanation=f"Cross-encoder score: {score:.4f}",
                            )
                        ],
                        relevance_features={
                            "cross_encoder_score": float(score),
                            "semantic_similarity": result.similarity_score,
                            "keyword_match": result.keyword_score,
                        },
                        confidence=float(score),
                        explanation=f"Cross-encoder score: {score:.4f}",
                    )
                )

            reranked_results.sort(key=lambda x: x.final_score, reverse=True)

            for i, result in enumerate(reranked_results):
                result.new_rank = i + 1

            if top_k is not None and top_k < len(reranked_results):
                return reranked_results[:top_k]

            return reranked_results

        except Exception as e:
            logger.error(f"Error during cross-encoder reranking: {e}")
            return self._fallback_rerank(query, results, top_k)

    def _fallback_rerank(
        self, query: str, results: List[SearchResult], top_k: int = None
    ) -> List[ReRankingResult]:
        """
        Fallback reranking using simple combination of existing scores.
        """
        combined_scores = []
        for result in results:
            combined = 0.7 * result.similarity_score + 0.3 * result.keyword_score
            combined_scores.append(combined)

        reranked_results = []
        for i, (result, score) in enumerate(zip(results, combined_scores)):
            reranked_results.append(
                ReRankingResult(
                    document=result.document,
                    original_rank=result.rank,
                    new_rank=0,
                    original_score=result.final_score,
                    reranked_score=score,
                    final_score=score,
                    features_used=[
                        ReRankingFeature(
                            name="combined_score",
                            value=score,
                            weight=1.0,
                            explanation=f"Combined semantic ({result.similarity_score:.3f}) and keyword ({result.keyword_score:.3f}) scores",
                        )
                    ],
                    relevance_features={
                        "combined_score": score,
                        "semantic_similarity": result.similarity_score,
                        "keyword_match": result.keyword_score,
                    },
                    confidence=score,
                    explanation=f"Fallback reranking with combined score: {score:.4f}",
                )
            )

        reranked_results.sort(key=lambda x: x.final_score, reverse=True)

        for i, result in enumerate(reranked_results):
            result.new_rank = i + 1

        if top_k is not None and top_k < len(reranked_results):
            return reranked_results[:top_k]

        return reranked_results

    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration."""
        return self._config.copy()

    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._is_loaded
