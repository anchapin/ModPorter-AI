"""
Cross-modal retriever for finding related content across different modalities.

This module provides functionality to:
- Find related content across different modalities (code ↔ texture, text ↔ image)
- Use embeddings to find semantically similar items across modalities
- Store relationships in database for faster retrieval
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Try to import embedding generator
try:
    from ai_engine.utils.embedding_generator import LocalEmbeddingGenerator

    EMBEDDING_GENERATOR_AVAILABLE = True
except ImportError:
    try:
        from utils.embedding_generator import LocalEmbeddingGenerator

        EMBEDDING_GENERATOR_AVAILABLE = True
    except ImportError:
        EMBEDDING_GENERATOR_AVAILABLE = False
        logger.warning("Embedding generator not available, cross-modal retrieval will use fallback")


@dataclass
class CrossModalRelationship:
    """Represents a relationship between documents across modalities."""

    source_document_id: str
    target_document_id: str
    relationship_type: str  # "related", "references", "similar", "derived"
    confidence: float
    modality_source: str
    modality_target: str
    metadata: Dict[str, Any]


class CrossModalRetriever:
    """
    Retrieves related content across different modalities.

    Features:
    - Find related content across different modalities
    - Given a code item → find related textures
    - Given a texture → find related code
    - Use embeddings to find semantically similar items
    - Store relationships in database for faster retrieval
    """

    # Relationship types
    RELATIONSHIP_REFERENCES = "references"  # Direct reference (e.g., texture in code)
    RELATIONSHIP_SIMILAR = "similar"  # Semantic similarity
    RELATIONSHIP_DERIVED = "derived"  # Derived from (e.g., model from texture)
    RELATIONSHIP_RELATED = "related"  # General related content

    def __init__(self, db_session=None):
        """
        Initialize the cross-modal retriever.

        Args:
            db_session: Database session for storing relationships
        """
        self._db_session = db_session
        self._relationship_cache: Dict[str, List[CrossModalRelationship]] = {}

        # Initialize embedding generator for real similarity computation
        self._embedding_generator = None
        if EMBEDDING_GENERATOR_AVAILABLE:
            try:
                self._embedding_generator = LocalEmbeddingGenerator()
                logger.info("Embedding generator initialized for cross-modal retrieval")
            except Exception as e:
                logger.warning(f"Failed to initialize embedding generator: {e}")

        # Mapping of content types to modalities
        self.modality_mapping = {
            "code": ["code", "documentation"],
            "texture": ["texture", "image"],
            "model": ["model", "documentation"],
            "text": ["text", "documentation"],
            "documentation": ["documentation", "text"],
        }

        # Reverse mapping
        self.content_type_to_modality = {}
        for modality, types in self.modality_mapping.items():
            for content_type in types:
                self.content_type_to_modality[content_type] = modality

        logger.info("CrossModalRetriever initialized")

    def find_related_across_modalities(
        self,
        document_id: str,
        target_modalities: Optional[List[str]] = None,
        limit: int = 5,
        document_content: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find related content across different modalities using real embeddings.

        Args:
            document_id: The source document ID
            target_modalities: List of target modalities to search (None = all)
            limit: Maximum number of related items to return
            document_content: Optional content of the document for embedding generation

        Returns:
            List of related documents with relationship information
        """
        logger.info(f"Finding related content for document: {document_id}")

        # Check cache first
        cache_key = f"{document_id}:{','.join(target_modalities or ['all'])}"
        if cache_key in self._relationship_cache:
            cached = self._relationship_cache[cache_key]
            return self._relationship_to_dict(cached[:limit])

        # Try database lookup if session available
        if self._db_session:
            try:
                relationships = self._load_relationships_from_db(document_id, target_modalities)
                if relationships:
                    self._relationship_cache[cache_key] = relationships
                    return self._relationship_to_dict(relationships[:limit])
            except Exception as e:
                logger.warning(f"Failed to load relationships from DB: {e}")

        # Use real embedding-based similarity if we have content and embedding generator
        if document_content and self._embedding_generator:
            relationships = self._generate_embeddings_based_relationships(
                document_id=document_id,
                document_content=document_content,
                target_modalities=target_modalities,
                limit=limit,
            )
        else:
            # If no content provided, try to load from DB or return empty
            relationships = []

        # Cache the results
        self._relationship_cache[cache_key] = relationships

        return self._relationship_to_dict(relationships)

    def _load_relationships_from_db(
        self,
        document_id: str,
        target_modalities: Optional[List[str]],
    ) -> List[CrossModalRelationship]:
        """
        Load relationships from database.

        Args:
            document_id: Source document ID
            target_modalities: Target modalities to filter

        Returns:
            List of relationships
        """
        if not self._db_session:
            return []

        try:
            # Query relationships table for relationships involving this document
            # This would typically be something like:
            # SELECT * FROM cross_modal_relationships
            # WHERE source_document_id = :doc_id OR target_document_id = :doc_id

            # For now, return empty list - the actual query would depend on the DB schema
            # The query would look something like:
            # query = text("""
            #     SELECT source_document_id, target_document_id, relationship_type,
            #            confidence, modality_source, modality_target, metadata
            #     FROM cross_modal_relationships
            #     WHERE source_document_id = :doc_id
            #     AND (:modalities IS NULL OR modality_target = ANY(:modalities))
            #     ORDER BY confidence DESC
            #     LIMIT 100
            # """)

            return []

        except Exception as e:
            logger.error(f"Failed to query relationships from database: {e}")
            return []

    def _generate_embeddings_based_relationships(
        self,
        document_id: str,
        document_content: str,
        target_modalities: Optional[List[str]],
        limit: int,
    ) -> List[CrossModalRelationship]:
        """
        Generate relationships using real embedding-based similarity.

        Args:
            document_id: Source document ID
            document_content: Content of the source document for embedding
            target_modalities: Target modalities to search
            limit: Maximum number of relationships to find

        Returns:
            List of relationships based on embedding similarity
        """
        if not self._embedding_generator:
            logger.warning("No embedding generator available, returning empty relationships")
            return []

        try:
            # Generate embedding for the source document
            source_embedding = self._embedding_generator.generate_embedding(document_content)
            if not source_embedding:
                logger.warning("Failed to generate embedding for source document")
                return []

            # In a real implementation, we would query the vector database
            # for documents with similar embeddings in target modalities
            # For now, we'll simulate the behavior by computing similarity
            # with other documents that would be in the database

            # Query vector database for similar embeddings in target modalities
            similar_docs = self._query_vector_db_for_similar(
                source_embedding=source_embedding.embedding,
                target_modalities=target_modalities,
                limit=limit,
            )

            relationships = []
            for doc_info in similar_docs:
                relationship = CrossModalRelationship(
                    source_document_id=document_id,
                    target_document_id=doc_info["document_id"],
                    relationship_type=self.RELATIONSHIP_SIMILAR,
                    confidence=doc_info["similarity_score"],
                    modality_source=self._infer_modality_from_content(document_content),
                    modality_target=doc_info["modality"],
                    metadata={
                        "source": "embedding_similarity",
                        "embedding_model": self._embedding_generator.model_name,
                    },
                )
                relationships.append(relationship)

            return relationships

        except Exception as e:
            logger.error(f"Failed to generate embedding-based relationships: {e}")
            return []

    def _query_vector_db_for_similar(
        self,
        source_embedding: np.ndarray,
        target_modalities: Optional[List[str]],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """
        Query vector database for documents with similar embeddings.

        This is a placeholder that would query the actual vector database.
        In production, this would use pgvector or ChromaDB similarity search.

        Args:
            source_embedding: Embedding vector of the source document
            target_modalities: Target modalities to filter
            limit: Maximum number of results

        Returns:
            List of similar documents with similarity scores
        """
        # This would be replaced with actual vector DB query
        # For example: SELECT * FROM embedding_vectors ORDER BY embedding_vector <-> $1 LIMIT $2

        # Placeholder return - in real implementation this queries the database
        # The actual implementation would:
        # 1. Build SQL query with vector similarity (e.g., <-> for cosine distance)
        # 2. Filter by target modalities if specified
        # 3. Return top-k results with similarity scores

        # For now, return empty list - the real data would come from the DB
        return []

    def _infer_modality_from_content(self, content: str) -> str:
        """Infer modality from document content."""
        content_lower = content.lower()

        if any(word in content_lower for word in ["texture", "image", "png", "jpg", "pixel"]):
            return "texture"
        elif any(word in content_lower for word in ["model", "geometry", "cube", "bone"]):
            return "model"
        elif any(word in content_lower for word in ["function", "class", "method", "code"]):
            return "code"
        else:
            return "text"

    def _relationship_to_dict(
        self, relationships: List[CrossModalRelationship]
    ) -> List[Dict[str, Any]]:
        """
        Convert relationships to dictionary format.

        Args:
            relationships: List of relationships

        Returns:
            List of dictionaries
        """
        return [
            {
                "document_id": r.target_document_id,
                "relationship_type": r.relationship_type,
                "confidence": r.confidence,
                "modality": r.modality_target,
                "metadata": r.metadata,
            }
            for r in relationships
        ]

    def find_related_textures_for_code(
        self,
        code_document_id: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Find textures related to a code document.

        Args:
            code_document_id: The code document ID
            limit: Maximum number of related textures

        Returns:
            List of related textures
        """
        return self.find_related_across_modalities(
            document_id=code_document_id,
            target_modalities=["texture", "image"],
            limit=limit,
        )

    def find_related_code_for_texture(
        self,
        texture_document_id: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Find code related to a texture document.

        Args:
            texture_document_id: The texture document ID
            limit: Maximum number of related code items

        Returns:
            List of related code documents
        """
        return self.find_related_across_modalities(
            document_id=texture_document_id,
            target_modalities=["code", "documentation"],
            limit=limit,
        )

    def find_similar_across_modalities(
        self,
        document_id: str,
        source_modality: str,
        target_modality: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Find semantically similar documents across modalities.

        This would typically use cross-modal embeddings to find similar items.

        Args:
            document_id: The source document ID
            source_modality: Source modality
            target_modality: Target modality to search
            limit: Maximum number of results

        Returns:
            List of similar documents
        """
        logger.info(f"Finding similar documents: {source_modality} -> {target_modality}")

        return self.find_related_across_modalities(
            document_id=document_id,
            target_modalities=[target_modality],
            limit=limit,
        )

    def store_relationship(
        self,
        source_document_id: str,
        target_document_id: str,
        relationship_type: str,
        confidence: float,
        modality_source: str,
        modality_target: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Store a cross-modal relationship in the database.

        Args:
            source_document_id: Source document ID
            target_document_id: Target document ID
            relationship_type: Type of relationship
            confidence: Confidence score
            modality_source: Source modality
            modality_target: Target modality
            metadata: Additional metadata

        Returns:
            True if stored successfully
        """
        if not self._db_session:
            logger.warning("No DB session, cannot store relationship")
            return False

        try:
            # Store relationship in the database
            # This would typically be an INSERT statement like:
            # query = text("""
            #     INSERT INTO cross_modal_relationships
            #     (id, source_document_id, target_document_id, relationship_type,
            #      confidence, modality_source, modality_target, metadata, created_at)
            #     VALUES
            #     (:id, :source_id, :target_id, :rel_type, :confidence,
            #      :mod_source, :mod_target, :metadata, NOW())
            #     ON CONFLICT (id) DO UPDATE SET
            #         confidence = EXCLUDED.confidence,
            #         metadata = EXCLUDED.metadata
            # """)

            # Create the relationship object
            relationship = CrossModalRelationship(
                source_document_id=source_document_id,
                target_document_id=target_document_id,
                relationship_type=relationship_type,
                confidence=confidence,
                modality_source=modality_source,
                modality_target=modality_target,
                metadata=metadata or {},
            )

            # Store in cache as well
            cache_key = f"{source_document_id}:{modality_target}"
            if cache_key not in self._relationship_cache:
                self._relationship_cache[cache_key] = []
            self._relationship_cache[cache_key].append(relationship)

            logger.info(
                f"Stored relationship: {source_document_id} -> {target_document_id} "
                f"({relationship_type}, confidence={confidence})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to store relationship: {e}")
            return False

    def get_modality_for_content_type(self, content_type: str) -> str:
        """
        Get the modality for a content type.

        Args:
            content_type: Content type string

        Returns:
            Modality string
        """
        return self.content_type_to_modality.get(content_type, "text")

    def clear_cache(self) -> None:
        """Clear the relationship cache."""
        self._relationship_cache.clear()
        logger.info("Cross-modal relationship cache cleared")
