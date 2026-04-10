"""
Cross-reference detection for knowledge base concept linking.

This module provides functionality to detect and manage relationships between
concepts across the knowledge base, enabling semantic linking and discovery
of related content.
"""

import re
import uuid
import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


JAVA_PATTERNS = {
    "class": re.compile(r"class\s+(\w+)(?:\s+extends\s+\w+)?(?:\s+implements\s+[\w,\s]+)?"),
    "method": re.compile(r"(?:public|private|protected|static|\s)+\s+[\w<>[\]]+\s+(\w+)\s*\("),
    "extends": re.compile(r"class\s+\w+\s+extends\s+(\w+)"),
    "implements": re.compile(r"(?:class\s+\w+\s+(?:extends\s+\w+\s+)?)?implements\s+([\w,\s]+)"),
    "import": re.compile(r"import\s+([\w.]+);"),
    "method_call": re.compile(r"(\w+)\s*\("),
    "variable": re.compile(r"(?:private|public|protected)?\s*(?:\w+)\s+(\w+)\s*="),
}


@dataclass
class DetectedConcept:
    """A concept detected from text."""

    name: str
    concept_type: str
    confidence: float
    context: str


@dataclass
class RelationshipCandidate:
    """A potential relationship between concepts."""

    source_concept: str
    target_concept: str
    relationship_type: str
    confidence: float


class CrossReferenceDetector:
    """
    Detects cross-references and relationships between concepts in document chunks.

    This detector analyzes chunk content to identify:
    - Class definitions and references
    - Method calls and definitions
    - Import statements
    - Semantic relationships via embeddings

    Relationships are stored in the ConceptRelationship table with confidence scores.
    """

    def __init__(self, db_session=None, embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize the cross-reference detector.

        Args:
            db_session: Optional database session for storing relationships
            embedding_model: Name of the embedding model for semantic similarity
        """
        self._db_session = db_session
        self._embedding_model = embedding_model
        self._model = None
        self._initialized = False
        self._concept_cache: Dict[str, List[str]] = {}

    async def initialize(self, db_session):
        """Initialize with database session."""
        self._db_session = db_session
        self._initialized = True
        try:
            self._load_embedding_model()
        except Exception as e:
            logger.warning(f"Failed to load embedding model: {e}")

    def _load_embedding_model(self):
        """Load the sentence transformer embedding model."""
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._embedding_model)
            logger.info(f"Embedding model loaded: {self._embedding_model}")
        except ImportError:
            logger.warning("sentence-transformers not installed, semantic similarity disabled")
        except Exception as e:
            logger.warning(f"Failed to load embedding model: {e}")

    def detect_concepts(
        self, chunk_content: str, chunk_id: Optional[str] = None
    ) -> List[DetectedConcept]:
        """
        Detect concepts in chunk content.

        Args:
            chunk_content: The text content of the chunk
            chunk_id: Optional chunk identifier

        Returns:
            List of detected concepts with type and confidence
        """
        concepts = []

        for match in JAVA_PATTERNS["class"].finditer(chunk_content):
            concepts.append(
                DetectedConcept(
                    name=match.group(1),
                    concept_type="class",
                    confidence=0.9,
                    context=chunk_content[max(0, match.start() - 50) : match.end() + 50],
                )
            )

        for match in JAVA_PATTERNS["extends"].finditer(chunk_content):
            concepts.append(
                DetectedConcept(
                    name=match.group(1),
                    concept_type="class",
                    confidence=0.85,
                    context=chunk_content[max(0, match.start() - 50) : match.end() + 50],
                )
            )

        for match in JAVA_PATTERNS["implements"].finditer(chunk_content):
            interface_names = [n.strip() for n in match.group(1).split(",")]
            for name in interface_names:
                concepts.append(
                    DetectedConcept(
                        name=name,
                        concept_type="interface",
                        confidence=0.85,
                        context=chunk_content[max(0, match.start() - 50) : match.end() + 50],
                    )
                )

        for match in JAVA_PATTERNS["import"].finditer(chunk_content):
            import_path = match.group(1)
            concepts.append(
                DetectedConcept(
                    name=import_path.split(".")[-1],
                    concept_type="import",
                    confidence=0.8,
                    context=chunk_content[max(0, match.start() - 50) : match.end() + 50],
                )
            )

        for match in JAVA_PATTERNS["method"].finditer(chunk_content):
            method_name = match.group(1)
            if method_name not in ["if", "while", "for", "switch", "catch", "class"]:
                concepts.append(
                    DetectedConcept(
                        name=method_name,
                        concept_type="method",
                        confidence=0.75,
                        context=chunk_content[max(0, match.start() - 50) : match.end() + 50],
                    )
                )

        unique_concepts = {}
        for concept in concepts:
            key = (concept.name, concept.concept_type)
            if key not in unique_concepts or unique_concepts[key].confidence < concept.confidence:
                unique_concepts[key] = concept

        return list(unique_concepts.values())

    def detect_relationships(
        self,
        chunk_content: str,
        chunk_id: Optional[str] = None,
    ) -> List[RelationshipCandidate]:
        """
        Detect relationships between concepts in chunk content.

        Uses pattern matching to find:
        - extends relationships
        - implements relationships
        - method calls
        - import usages

        Args:
            chunk_content: The text content of the chunk
            chunk_id: Optional chunk identifier

        Returns:
            List of detected relationships with type and confidence
        """
        relationships = []
        concepts = self.detect_concepts(chunk_content, chunk_id)

        class_names = {c.name for c in concepts if c.concept_type == "class"}
        method_names = {c.name for c in concepts if c.concept_type == "method"}

        for match in JAVA_PATTERNS["extends"].finditer(chunk_content):
            parent_class = match.group(1)
            relationships.append(
                RelationshipCandidate(
                    source_concept=chunk_content[
                        max(0, match.start() - 30) : match.start()
                    ].split()[-1]
                    if chunk_content
                    else "",
                    target_concept=parent_class,
                    relationship_type="extends",
                    confidence=0.9,
                )
            )

        for match in JAVA_PATTERNS["implements"].finditer(chunk_content):
            interfaces = [i.strip() for i in match.group(1).split(",")]
            for interface in interfaces:
                relationships.append(
                    RelationshipCandidate(
                        source_concept=chunk_content[
                            max(0, match.start() - 30) : match.start()
                        ].split()[-1]
                        if chunk_content
                        else "",
                        target_concept=interface,
                        relationship_type="implements",
                        confidence=0.85,
                    )
                )

        for match in JAVA_PATTERNS["method_call"].finditer(chunk_content):
            method_name = match.group(1)
            if method_name in method_names or method_name in class_names:
                relationships.append(
                    RelationshipCandidate(
                        source_concept=method_name,
                        target_concept=method_name,
                        relationship_type="calls",
                        confidence=0.7,
                    )
                )

        return relationships

    async def find_related_chunks(
        self,
        chunk_id: str,
        limit: int = 5,
        relationship_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find chunks related to a given chunk.

        Args:
            chunk_id: The ID of the chunk to find related chunks for
            limit: Maximum number of related chunks to return
            relationship_type: Optional filter for relationship type

        Returns:
            List of related chunks with relationship info
        """
        if not self._initialized or self._db_session is None:
            logger.warning("CrossReferenceDetector not initialized, returning empty results")
            return []

        try:
            query = (
                "SELECT cr.relationship_type, cr.confidence, "
                "cn.id as related_node_id, cn.name as related_name, cn.type as related_type "
                "FROM concept_relationships cr "
                "JOIN concept_nodes cn ON cn.id = cr.target_node_id "
                "WHERE cr.source_node_id IN ("
                "  SELECT id FROM concept_nodes WHERE document_id = $1"
                ") "
            )

            params = [chunk_id]
            if relationship_type:
                query += " AND cr.relationship_type = $2"
                params.append(relationship_type)

            query += f" ORDER BY cr.confidence DESC LIMIT ${len(params) + 1}"
            params.append(limit)

            result = await self._db_session.execute(query, params)
            rows = result.fetchall()

            related_chunks = []
            for row in rows:
                related_chunks.append(
                    {
                        "chunk_id": str(row.related_node_id),
                        "title": row.related_name,
                        "relationship_type": row.relationship_type,
                        "confidence": float(row.confidence),
                    }
                )

            return related_chunks

        except Exception as e:
            logger.error(f"Error finding related chunks: {e}")
            return []

    async def store_concepts_and_relationships(
        self,
        chunk_id: str,
        chunk_content: str,
    ) -> Dict[str, Any]:
        """
        Detect and store concepts and relationships for a chunk.

        Args:
            chunk_id: The ID of the chunk
            chunk_content: The text content of the chunk

        Returns:
            Summary of stored concepts and relationships
        """
        if not self._initialized or self._db_session is None:
            logger.warning("CrossReferenceDetector not initialized, skipping storage")
            return {"stored": False}

        try:
            from knowledge.schema import ConceptNode, ConceptRelationship

            concepts = self.detect_concepts(chunk_content, chunk_id)
            relationships = self.detect_relationships(chunk_content, chunk_id)

            stored_concepts = []
            concept_name_to_id = {}

            for concept in concepts:
                node = ConceptNode(
                    name=concept.name,
                    type=concept.concept_type,
                    document_id=chunk_id,
                    description=concept.context[:500] if concept.context else None,
                )
                self._db_session.add(node)
                await self._db_session.flush()
                concept_name_to_id[concept.name] = str(node.id)
                stored_concepts.append(str(node.id))

            for rel in relationships:
                if (
                    rel.source_concept in concept_name_to_id
                    and rel.target_concept in concept_name_to_id
                ):
                    relationship = ConceptRelationship(
                        source_node_id=concept_name_to_id[rel.source_concept],
                        target_node_id=concept_name_to_id[rel.target_concept],
                        relationship_type=rel.relationship_type,
                        confidence=rel.confidence,
                    )
                    self._db_session.add(relationship)

            await self._db_session.commit()

            return {
                "stored": True,
                "concepts_count": len(stored_concepts),
                "relationships_count": len(relationships),
            }

        except Exception as e:
            logger.error(f"Error storing concepts and relationships: {e}")
            await self._db_session.rollback()
            return {"stored": False, "error": str(e)}

    async def build_concept_graph(
        self,
        chunks: List[Dict[str, Any]],
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Build the concept graph by processing multiple chunks.

        Args:
            chunks: List of chunks with 'id' and 'content' keys
            batch_size: Number of chunks to process in each batch

        Returns:
            Summary of the graph building process
        """
        total_concepts = 0
        total_relationships = 0
        processed = 0
        failed = 0

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]

            for chunk in batch:
                try:
                    result = await self.store_concepts_and_relationships(
                        chunk_id=chunk.get("id", str(uuid.uuid4())),
                        chunk_content=chunk.get("content", ""),
                    )
                    if result.get("stored"):
                        total_concepts += result.get("concepts_count", 0)
                        total_relationships += result.get("relationships_count", 0)
                        processed += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"Error processing chunk: {e}")
                    failed += 1

        return {
            "total_chunks": len(chunks),
            "processed": processed,
            "failed": failed,
            "total_concepts": total_concepts,
            "total_relationships": total_relationships,
        }

    async def get_semantic_similar_chunks(
        self,
        chunk_content: str,
        existing_embeddings: Dict[str, List[float]],
        top_k: int = 5,
    ) -> List[Tuple[str, float]]:
        """
        Find semantically similar chunks using embeddings.

        Args:
            chunk_content: Content to find similar chunks for
            existing_embeddings: Dictionary mapping chunk IDs to embeddings
            top_k: Number of similar chunks to return

        Returns:
            List of (chunk_id, similarity_score) tuples
        """
        if self._model is None or not existing_embeddings:
            return []

        try:
            query_embedding = self._model.encode([chunk_content])[0]

            similarities = []
            for chunk_id, embeddings in existing_embeddings.items():
                if embeddings is not None and (
                    isinstance(embeddings, list) or isinstance(embeddings, np.ndarray)
                ):
                    doc_embedding = (
                        np.array(embeddings[0])
                        if isinstance(embeddings, list)
                        else np.array(embeddings)
                    )
                    if doc_embedding.shape[0] == query_embedding.shape[0]:
                        similarity = np.dot(query_embedding, doc_embedding) / (
                            np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding)
                        )
                        similarities.append((chunk_id, float(similarity)))

            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:top_k]

        except Exception as e:
            logger.error(f"Error finding semantic similar chunks: {e}")
            return []
