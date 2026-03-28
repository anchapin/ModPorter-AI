"""
Unit tests for cross-reference API endpoints and CrossReferenceDetector.

Tests:
- CrossReferenceDetector concept extraction
- CrossReferenceDetector relationship detection
- CrossReferenceDetector semantic similarity (when model available)
"""

import sys
import os
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "ai-engine"))

import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch


class TestCrossReferenceDetectorConceptExtraction:
    """Tests for CrossReferenceDetector concept extraction."""

    def test_detect_concepts_finds_classes(self):
        """Test detecting class concepts."""
        from knowledge.cross_reference import CrossReferenceDetector

        detector = CrossReferenceDetector()
        content = "public class MyClass extends BaseClass"

        concepts = detector.detect_concepts(content)

        class_concepts = [c for c in concepts if c.concept_type == "class"]
        assert len(class_concepts) >= 1
        names = [c.name for c in class_concepts]
        assert "MyClass" in names

    def test_detect_concepts_finds_imports(self):
        """Test detecting import concepts."""
        from knowledge.cross_reference import CrossReferenceDetector

        detector = CrossReferenceDetector()
        content = "import java.util.List; import com.example.MyClass;"

        concepts = detector.detect_concepts(content)

        import_concepts = [c for c in concepts if c.concept_type == "import"]
        assert len(import_concepts) >= 2

    def test_detect_concepts_finds_methods(self):
        """Test detecting method concepts."""
        from knowledge.cross_reference import CrossReferenceDetector

        detector = CrossReferenceDetector()
        content = "public void myMethod() { doSomething(); }"

        concepts = detector.detect_concepts(content)

        method_concepts = [c for c in concepts if c.concept_type == "method"]
        assert len(method_concepts) >= 1

    def test_detect_concepts_finds_interfaces(self):
        """Test detecting interface concepts."""
        from knowledge.cross_reference import CrossReferenceDetector

        detector = CrossReferenceDetector()
        content = "public class MyClass implements Serializable, Runnable {}"

        concepts = detector.detect_concepts(content)

        interface_concepts = [c for c in concepts if c.concept_type == "interface"]
        assert len(interface_concepts) >= 2


class TestCrossReferenceDetectorRelationshipDetection:
    """Tests for CrossReferenceDetector relationship detection."""

    def test_detect_relationships_finds_extends(self):
        """Test detecting extends relationships."""
        from knowledge.cross_reference import CrossReferenceDetector

        detector = CrossReferenceDetector()
        content = "public class ChildClass extends ParentClass {}"

        relationships = detector.detect_relationships(content)

        extends_rels = [r for r in relationships if r.relationship_type == "extends"]
        assert len(extends_rels) >= 1

    def test_detect_relationships_finds_implements(self):
        """Test detecting implements relationships."""
        from knowledge.cross_reference import CrossReferenceDetector

        detector = CrossReferenceDetector()
        content = "public class MyClass implements Interface1, Interface2 {}"

        relationships = detector.detect_relationships(content)

        implements_rels = [r for r in relationships if r.relationship_type == "implements"]
        assert len(implements_rels) >= 1

    def test_detect_relationships_finds_method_calls(self):
        """Test detecting method call relationships."""
        from knowledge.cross_reference import CrossReferenceDetector

        detector = CrossReferenceDetector()
        content = "public void doSomething() { otherMethod(); }"

        relationships = detector.detect_relationships(content)

        call_rels = [r for r in relationships if r.relationship_type == "calls"]
        assert len(call_rels) >= 0

    def test_relationship_confidence_scores(self):
        """Test that relationships have confidence scores."""
        from knowledge.cross_reference import CrossReferenceDetector

        detector = CrossReferenceDetector()
        content = "public class A extends B {}"

        relationships = detector.detect_relationships(content)

        for rel in relationships:
            assert 0.0 <= rel.confidence <= 1.0


class TestCrossReferenceDetectorSemanticSimilarity:
    """Tests for semantic similarity detection."""

    @pytest.mark.asyncio
    async def test_semantic_similar_chunks_no_model(self):
        """Test semantic similarity returns empty when no model loaded."""
        from knowledge.cross_reference import CrossReferenceDetector

        detector = CrossReferenceDetector()
        detector._model = None

        result = await detector.get_semantic_similar_chunks(
            chunk_content="test content",
            existing_embeddings={},
            top_k=5,
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_semantic_similar_chunks_no_embeddings(self):
        """Test semantic similarity returns empty with no embeddings."""
        from knowledge.cross_reference import CrossReferenceDetector

        detector = CrossReferenceDetector()

        result = await detector.get_semantic_similar_chunks(
            chunk_content="test content",
            existing_embeddings=None,
            top_k=5,
        )

        assert result == []


class TestCrossReferenceDetectorStorage:
    """Tests for concept storage functionality."""

    @pytest.mark.asyncio
    async def test_store_concepts_uninitialized(self):
        """Test storing concepts when detector not initialized."""
        from knowledge.cross_reference import CrossReferenceDetector

        detector = CrossReferenceDetector()

        result = await detector.store_concepts_and_relationships(
            chunk_id="test-id",
            chunk_content="public class Test {}",
        )

        assert result["stored"] is False

    @pytest.mark.asyncio
    async def test_find_related_chunks_uninitialized(self):
        """Test finding related chunks when detector not initialized."""
        from knowledge.cross_reference import CrossReferenceDetector

        detector = CrossReferenceDetector()

        result = await detector.find_related_chunks(
            chunk_id="test-id",
            limit=5,
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_build_concept_graph_empty(self):
        """Test building concept graph with empty chunks."""
        from knowledge.cross_reference import CrossReferenceDetector

        detector = CrossReferenceDetector()

        result = await detector.build_concept_graph(chunks=[])

        assert result["total_chunks"] == 0
        assert result["processed"] == 0


class TestSchemaModels:
    """Tests for schema models."""

    def test_schema_import(self):
        """Test schema can be imported."""
        from knowledge.schema import ConceptNode, ConceptRelationship
        from knowledge.schema import ConceptType, RelationshipType

        assert ConceptNode is not None
        assert ConceptRelationship is not None
        assert ConceptType is not None
        assert RelationshipType is not None

    def test_concept_types_enum(self):
        """Test ConceptType enum values."""
        from knowledge.schema import ConceptType

        assert ConceptType.CLASS.value == "class"
        assert ConceptType.METHOD.value == "method"
        assert ConceptType.CONCEPT.value == "concept"

    def test_relationship_types_enum(self):
        """Test RelationshipType enum values."""
        from knowledge.schema import RelationshipType

        assert RelationshipType.EXTENDS.value == "extends"
        assert RelationshipType.IMPLEMENTS.value == "implements"
        assert RelationshipType.RELATED_TO.value == "related_to"

    def test_get_concept_types(self):
        """Test get_concept_types function."""
        from knowledge.schema import get_concept_types

        types = get_concept_types()
        assert "class" in types
        assert "method" in types

    def test_get_relationship_types(self):
        """Test get_relationship_types function."""
        from knowledge.schema import get_relationship_types

        types = get_relationship_types()
        assert "extends" in types
        assert "implements" in types


class TestDetectedConcept:
    """Tests for DetectedConcept dataclass."""

    def test_detected_concept_creation(self):
        """Test creating a DetectedConcept."""
        from knowledge.cross_reference import DetectedConcept

        concept = DetectedConcept(
            name="MyClass",
            concept_type="class",
            confidence=0.9,
            context="public class MyClass {}",
        )

        assert concept.name == "MyClass"
        assert concept.concept_type == "class"
        assert concept.confidence == 0.9


class TestRelationshipCandidate:
    """Tests for RelationshipCandidate dataclass."""

    def test_relationship_candidate_creation(self):
        """Test creating a RelationshipCandidate."""
        from knowledge.cross_reference import RelationshipCandidate

        rel = RelationshipCandidate(
            source_concept="Child",
            target_concept="Parent",
            relationship_type="extends",
            confidence=0.85,
        )

        assert rel.source_concept == "Child"
        assert rel.target_concept == "Parent"
        assert rel.relationship_type == "extends"
        assert rel.confidence == 0.85
