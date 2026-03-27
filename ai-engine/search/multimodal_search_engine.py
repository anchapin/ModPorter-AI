"""
Multi-modal search engine for content type filtering and modality-aware scoring.

This module extends the hybrid search engine to support:
- Content type filtering (texture, model, code, text, documentation)
- Modality-aware scoring (weight results by content type relevance)
- Cross-modal expansion (find related content across modalities)
"""

import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field

import numpy as np

from schemas.multimodal_schema import (
    SearchQuery,
    SearchResult,
    MultiModalDocument,
    ContentType,
    EmbeddingModel,
)
from search.hybrid_search_engine import HybridSearchEngine, SearchMode

# Try to import embedding generator
try:
    from utils.embedding_generator import LocalEmbeddingGenerator

    EMBEDDING_GENERATOR_AVAILABLE = True
except ImportError:
    try:
        from ai_engine.utils.embedding_generator import LocalEmbeddingGenerator

        EMBEDDING_GENERATOR_AVAILABLE = True
    except ImportError:
        EMBEDDING_GENERATOR_AVAILABLE = False
        logger.warning("Embedding generator not available for multi-modal search")

logger = logging.getLogger(__name__)


# Default weights for modality-aware scoring
DEFAULT_MODALITY_WEIGHTS = {
    "code": {"code": 1.0, "text": 0.5, "documentation": 0.3, "image": 0.2, "multimodal": 0.3},
    "text": {"text": 1.0, "documentation": 0.7, "code": 0.3, "image": 0.2, "multimodal": 0.4},
    "documentation": {
        "documentation": 1.0,
        "text": 0.7,
        "code": 0.3,
        "image": 0.2,
        "multimodal": 0.4,
    },
    "image": {"image": 1.0, "multimodal": 0.6, "texture": 0.8, "text": 0.3, "code": 0.2},
    "texture": {"texture": 1.0, "image": 0.8, "code": 0.3, "text": 0.2, "documentation": 0.2},
    "model": {"model": 1.0, "documentation": 0.5, "code": 0.3, "texture": 0.3, "image": 0.3},
}


@dataclass
class CrossModalResult:
    """Represents a result with cross-modal related items."""

    document: MultiModalDocument
    similarity_score: float
    keyword_score: float
    final_score: float
    rank: int
    related_modalities: List[Dict[str, Any]] = field(default_factory=list)


class MultiModalSearchEngine:
    """
    Multi-modal search engine with content type filtering and modality-aware scoring.

    Features:
    - Content type filtering (texture, model, code, text, documentation)
    - Modality-aware scoring (weight results based on query type)
    - Cross-modal expansion (find related content across modalities)
    """

    def __init__(
        self,
        db_session=None,
        modality_weights: Optional[Dict[str, Dict[str, float]]] = None,
        enable_cross_modal: bool = True,
    ):
        """
        Initialize the multi-modal search engine.

        Args:
            db_session: Database session for storing cross-modal relationships
            modality_weights: Custom modality weights for scoring
            enable_cross_modal: Whether to enable cross-modal expansion
        """
        self.hybrid_engine = HybridSearchEngine(db_session=db_session)
        self.modality_weights = modality_weights or DEFAULT_MODALITY_WEIGHTS
        self.enable_cross_modal = enable_cross_modal
        self._db_session = db_session

        # Initialize embedding generator for real embedding-based search
        self._embedding_generator = None
        if EMBEDDING_GENERATOR_AVAILABLE:
            try:
                self._embedding_generator = LocalEmbeddingGenerator()
                logger.info("Embedding generator initialized for multi-modal search")
            except Exception as e:
                logger.warning(f"Failed to initialize embedding generator: {e}")

        # Content type to modality mapping
        self.content_type_modality = {
            ContentType.CODE: "code",
            ContentType.TEXT: "text",
            ContentType.DOCUMENTATION: "documentation",
            ContentType.IMAGE: "image",
            ContentType.MULTIMODAL: "multimodal",
            ContentType.CONFIGURATION: "code",  # Treat config as code
        }

        logger.info(f"MultiModalSearchEngine initialized with cross_modal={enable_cross_modal}")

    def search(
        self,
        query: SearchQuery,
        documents: Dict[str, MultiModalDocument],
        embeddings: Optional[Dict[str, List]] = None,
        query_embedding: Optional[List[float]] = None,
    ) -> List[SearchResult]:
        """
        Perform multi-modal search with content type filtering and scoring.

        Args:
            query: Search query with parameters
            documents: Available documents to search
            embeddings: Optional document embeddings
            query_embedding: Optional query embedding vector

        Returns:
            Ranked list of search results with modality awareness
        """
        logger.info(f"Multi-modal search for: {query.query_text}")

        # Determine the primary modality from content types
        primary_modality = self._infer_modality(query)

        # If content types are specified, filter documents
        filtered_docs = documents
        if query.content_types:
            filtered_docs = {
                doc_id: doc
                for doc_id, doc in documents.items()
                if doc.content_type in query.content_types
            }
            logger.info(f"Filtered to {len(filtered_docs)} documents by content type")

        # Use embedding-based search
        # If hybrid engine is available with embeddings, use it
        if hasattr(self.hybrid_engine, "search") and embeddings and query_embedding:
            results = self.hybrid_engine.search(
                query=query,
                documents=filtered_docs,
                embeddings=embeddings,
                query_embedding=query_embedding,
                search_mode=SearchMode.HYBRID,
            )
        elif hasattr(self.hybrid_engine, "search"):
            # Hybrid engine available but no embeddings provided
            # Generate embeddings for query
            query_emb = self._generate_query_embedding(query.query_text)
            if query_emb:
                results = self.hybrid_engine.search(
                    query=query,
                    documents=filtered_docs,
                    embeddings={},  # Will use query embedding for similarity
                    query_embedding=query_emb,
                    search_mode=SearchMode.VECTOR_ONLY,
                )
            else:
                # No embedding generation available - use hybrid without embeddings
                results = self.hybrid_engine.search(
                    query=query,
                    documents=filtered_docs,
                    embeddings={},
                    query_embedding=[],
                    search_mode=SearchMode.KEYWORD_ONLY,
                )
        else:
            # No hybrid engine available - use basic vector similarity
            results = self._embedding_based_search(query, filtered_docs)

        # Apply modality-aware scoring
        if primary_modality and query.content_types and len(query.content_types) > 1:
            results = self._apply_modality_scoring(results, primary_modality)

        # Add cross-modal related items if enabled
        if self.enable_cross_modal:
            results = self._add_cross_modal_related(results, query)

        return results

    def _infer_modality(self, query: SearchQuery) -> Optional[str]:
        """
        Infer the primary modality from the query and content types.

        Args:
            query: Search query

        Returns:
            Primary modality string or None
        """
        if query.content_types and len(query.content_types) == 1:
            content_type = query.content_types[0]
            return self.content_type_modality.get(content_type)

        # Infer from query text
        query_lower = query.query_text.lower()

        if any(word in query_lower for word in ["texture", "image", "visual", "skin", "sprite"]):
            return "texture"
        elif any(
            word in query_lower for word in ["model", "geometry", "cube", "bone", "animation"]
        ):
            return "model"
        elif any(word in query_lower for word in ["code", "function", "class", "method", "api"]):
            return "code"
        elif any(word in query_lower for word in ["doc", "documentation", "guide", "tutorial"]):
            return "documentation"

        return None

    def _simple_search(
        self, query: SearchQuery, documents: Dict[str, MultiModalDocument]
    ) -> List[SearchResult]:
        """
        Simple search when hybrid search is not available.

        Args:
            query: Search query
            documents: Documents to search

        Returns:
            List of search results
        """
        results = []

        # Simple keyword matching
        query_keywords = set(query.query_text.lower().split())

        for doc_id, doc in documents.items():
            score = 0.0
            if doc.content_text:
                doc_keywords = set(doc.content_text.lower().split())
                matches = query_keywords & doc_keywords
                score = len(matches) / max(len(query_keywords), 1)

            results.append(
                SearchResult(
                    document=doc,
                    similarity_score=score,
                    keyword_score=score,
                    final_score=score,
                    rank=0,
                    embedding_model_used="simple",
                )
            )

        # Sort by score
        results.sort(key=lambda r: r.final_score, reverse=True)

        # Assign ranks
        for i, result in enumerate(results):
            result.rank = i + 1

        return results[: query.top_k]

    def _generate_query_embedding(self, query_text: str) -> Optional[List[float]]:
        """
        Generate embedding for query text using the embedding generator.

        Args:
            query_text: The query text to embed

        Returns:
            Query embedding vector or None if generation fails
        """
        if not self._embedding_generator:
            return None

        try:
            result = self._embedding_generator.generate_embedding(query_text)
            if result:
                return result.embedding.tolist()
            return None
        except Exception as e:
            logger.warning(f"Failed to generate query embedding: {e}")
            return None

    def _embedding_based_search(
        self, query: SearchQuery, documents: Dict[str, MultiModalDocument]
    ) -> List[SearchResult]:
        """
        Perform embedding-based search when hybrid engine is not available.

        Args:
            query: Search query
            documents: Documents to search

        Returns:
            List of search results based on embedding similarity
        """
        if not self._embedding_generator:
            # Fallback to simple search if no embedding generator
            logger.warning("No embedding generator available, falling back to simple search")
            return self._simple_search(query, documents)

        try:
            # Generate query embedding
            query_embedding = self._generate_query_embedding(query.query_text)
            if not query_embedding:
                return self._simple_search(query, documents)

            results = []

            for doc_id, doc in documents.items():
                if not doc.content_text:
                    continue

                # Generate embedding for document content
                doc_embedding = self._generate_query_embedding(doc.content_text)
                if not doc_embedding:
                    continue

                # Calculate cosine similarity
                similarity = self._cosine_similarity(query_embedding, doc_embedding)

                results.append(
                    SearchResult(
                        document=doc,
                        similarity_score=similarity,
                        keyword_score=0.0,
                        final_score=similarity,
                        rank=0,
                        embedding_model_used=EmbeddingModel.SENTENCE_TRANSFORMER,
                    )
                )

            # Sort by score
            results.sort(key=lambda r: r.final_score, reverse=True)

            # Assign ranks
            for i, result in enumerate(results):
                result.rank = i + 1

            return results[: query.top_k]

        except Exception as e:
            logger.error(f"Embedding-based search failed: {e}")
            return self._simple_search(query, documents)

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score
        """
        v1 = np.array(vec1)
        v2 = np.array(vec2)

        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def _apply_modality_scoring(
        self, results: List[SearchResult], primary_modality: str
    ) -> List[SearchResult]:
        """
        Apply modality-aware scoring to results.

        Args:
            results: Search results
            primary_modality: The primary modality being searched for

        Returns:
            Results with modality-adjusted scores
        """
        weights = self.modality_weights.get(primary_modality, {})

        for result in results:
            content_type = result.document.content_type
            modality = self.content_type_modality.get(content_type, "text")

            # Get weight for this modality
            weight = weights.get(modality, 0.5)

            # Adjust final score
            result.final_score = result.final_score * weight

            # Update explanation
            if result.match_explanation:
                result.match_explanation += f"; Modality weight: {weight}"

        # Re-sort by adjusted scores
        results.sort(key=lambda r: r.final_score, reverse=True)

        # Re-assign ranks
        for i, result in enumerate(results):
            result.rank = i + 1

        return results

    def _add_cross_modal_related(
        self, results: List[SearchResult], query: SearchQuery
    ) -> List[SearchResult]:
        """
        Add cross-modal related items to results.

        Args:
            results: Search results
            query: Original query

        Returns:
            Results with cross-modal related items added
        """
        if not query.expand_query:
            return results

        # Check if cross-modal retrieval is available
        try:
            from ai_engine.search.cross_modal_retriever import CrossModalRetriever

            retriever = CrossModalRetriever(db_session=self._db_session)

            for result in results:
                doc_id = result.document.id

                # Find related content across modalities
                related = retriever.find_related_across_modalities(
                    document_id=doc_id,
                    target_modalities=None,  # Find all related
                    limit=3,
                )

                if related:
                    # Add to result metadata
                    if not hasattr(result, "metadata"):
                        result.metadata = {}
                    result.metadata["cross_modal_related"] = related

        except ImportError:
            logger.debug("CrossModalRetriever not available, skipping cross-modal expansion")
        except Exception as e:
            logger.warning(f"Failed to add cross-modal related items: {e}")

        return results

    def search_by_modality(
        self,
        query_text: str,
        modalities: List[str],
        top_k: int = 10,
    ) -> List[SearchResult]:
        """
        Search specifically by modalities.

        Args:
            query_text: The search query text
            modalities: List of modalities to search (texture, model, code, text, documentation)
            top_k: Number of results to return

        Returns:
            Ranked list of search results
        """
        # Convert modalities to content types
        content_types = []
        modality_to_type = {
            "texture": ContentType.IMAGE,
            "model": ContentType.MULTIMODAL,
            "code": ContentType.CODE,
            "text": ContentType.TEXT,
            "documentation": ContentType.DOCUMENTATION,
        }

        for modality in modalities:
            content_type = modality_to_type.get(modality.lower())
            if content_type:
                content_types.append(content_type)

        # Create search query
        query = SearchQuery(
            query_text=query_text,
            content_types=content_types if content_types else None,
            top_k=top_k,
        )

        # Search with empty documents (subclass should populate this)
        return self.search(query, {})

    def get_modality_stats(self) -> Dict[str, int]:
        """
        Get statistics about modalities in the search index.

        Returns:
            Dictionary of modality counts
        """
        # This would typically query the database
        # For now, return placeholder
        return {
            "texture": 0,
            "model": 0,
            "code": 0,
            "text": 0,
            "documentation": 0,
        }
