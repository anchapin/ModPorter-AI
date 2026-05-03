"""
Comprehensive unit tests for CrossReferenceDetector.
Tests semantic linking, database storage, and graph building.
"""

import pytest
import uuid
import numpy as np
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from knowledge.cross_reference import CrossReferenceDetector, DetectedConcept, RelationshipCandidate

class TestCrossReferenceDetectorComprehensive:
    @pytest.fixture
    def mock_db(self):
        session = MagicMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.flush = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def detector(self, mock_db):
        return CrossReferenceDetector(db_session=mock_db)

    @pytest.mark.asyncio
    async def test_initialize(self, detector, mock_db):
        """Test detector initialization with model loading."""
        with patch('knowledge.cross_reference.CrossReferenceDetector._load_embedding_model') as mock_load:
            await detector.initialize(mock_db)
            assert detector._db_session == mock_db
            assert detector._initialized is True
            mock_load.assert_called_once()

    def test_load_embedding_model_import_error(self, detector):
        """Test handling of ImportError when loading model."""
        with patch('builtins.__import__', side_effect=ImportError):
            detector._load_embedding_model()
            assert detector._model is None

    def test_load_embedding_model_exception(self, detector):
        """Test handling of generic exception when loading model."""
        with patch('sentence_transformers.SentenceTransformer', side_effect=Exception("Load fail")):
            detector._load_embedding_model()
            assert detector._model is None

    def test_detect_concepts_complex(self, detector):
        """Test detecting concepts with varied patterns."""
        code = """
        package com.example;
        import org.bukkit.Material;
        import org.bukkit.block.Block;
        
        public class MyBlock extends BaseBlock implements IObservable, IDisposable {
            private int power = 0;
            public void onPlace() { }
            protected void internalUpdate() { }
        }
        """
        concepts = detector.detect_concepts(code)
        concept_names = {c.name for c in concepts}
        
        assert "MyBlock" in concept_names
        assert "BaseBlock" in concept_names
        assert "IObservable" in concept_names
        assert "IDisposable" in concept_names
        assert "Material" in concept_names
        assert "onPlace" in concept_names
        assert "internalUpdate" in concept_names

    def test_detect_relationships_complex(self, detector):
        """Test detecting relationships between concepts."""
        code = """
        public class Child extends Parent implements IInterface {
            public void test() {
                Parent p = new Parent();
                p.someMethod();
            }
        }
        """
        relationships = detector.detect_relationships(code)
        
        rel_types = [r.relationship_type for r in relationships]
        assert "extends" in rel_types
        assert "implements" in rel_types
        assert "calls" in rel_types

    @pytest.mark.asyncio
    async def test_find_related_chunks(self, detector, mock_db):
        """Test finding related chunks via database query."""
        await detector.initialize(mock_db)
        
        # Mock DB response
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.related_node_id = "node-123"
        mock_row.related_name = "TargetConcept"
        mock_row.relationship_type = "extends"
        mock_row.confidence = 0.95
        mock_result.fetchall.return_value = [mock_row]
        mock_db.execute.return_value = mock_result
        
        results = await detector.find_related_chunks("chunk-1")
        
        assert len(results) == 1
        assert results[0]["chunk_id"] == "node-123"
        assert results[0]["confidence"] == 0.95
        assert mock_db.execute.called

    @pytest.mark.asyncio
    async def test_find_related_chunks_uninitialized(self, detector):
        """Test find_related_chunks fails gracefully when uninitialized."""
        results = await detector.find_related_chunks("id")
        assert results == []

    @pytest.mark.asyncio
    async def test_find_related_chunks_exception(self, detector, mock_db):
        """Test find_related_chunks exception handling."""
        await detector.initialize(mock_db)
        mock_db.execute.side_effect = Exception("Query error")
        
        results = await detector.find_related_chunks("id")
        assert results == []

    @pytest.mark.asyncio
    async def test_store_concepts_and_relationships(self, detector, mock_db):
        """Test storing detected entities in database."""
        await detector.initialize(mock_db)
        
        code = "public class A extends B { }"
        
        # Mock ConceptNode creation to set ID
        with patch('knowledge.schema.ConceptNode') as mock_node_cls, \
             patch('knowledge.schema.ConceptRelationship') as mock_rel_cls:
            
            # Setup mock nodes
            node_a = MagicMock()
            node_a.id = "id-a"
            node_b = MagicMock()
            node_b.id = "id-b"
            mock_node_cls.side_effect = [node_a, node_b]
            
            res = await detector.store_concepts_and_relationships("chunk-1", code)
            
            assert res["stored"] is True
            assert res["concepts_count"] >= 2
            assert mock_db.add.called
            assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_store_concepts_exception(self, detector, mock_db):
        """Test store_concepts exception handling and rollback."""
        await detector.initialize(mock_db)
        mock_db.flush.side_effect = Exception("Storage fail")
        
        # Need a concept to trigger flush
        res = await detector.store_concepts_and_relationships("id", "class Trigger { }")
        assert res["stored"] is False
        assert mock_db.rollback.called

    @pytest.mark.asyncio
    async def test_build_concept_graph(self, detector):
        """Test building graph for multiple chunks."""
        chunks = [
            {"id": "1", "content": "class A {}"},
            {"id": "2", "content": "class B extends A {}"}
        ]
        
        with patch.object(detector, 'store_concepts_and_relationships', 
                         return_value={"stored": True, "concepts_count": 1, "relationships_count": 0}) as mock_store:
            
            res = await detector.build_concept_graph(chunks, batch_size=1)
            
            assert res["processed"] == 2
            assert mock_store.call_count == 2

    @pytest.mark.asyncio
    async def test_get_semantic_similar_chunks(self, detector):
        """Test semantic similarity search."""
        # Mock model
        mock_model = MagicMock()
        mock_model.encode.return_value = [np.array([1.0, 0.0, 0.0])]
        detector._model = mock_model
        
        existing = {
            "chunk-1": np.array([1.0, 0.0, 0.0]),  # Identical
            "chunk-2": np.array([0.0, 1.0, 0.0]),  # Orthogonal
            "chunk-3": np.array([0.8, 0.6, 0.0]),  # Similar
        }
        
        results = await detector.get_semantic_similar_chunks("query", existing, top_k=2)
        
        assert len(results) == 2
        assert results[0][0] == "chunk-1"
        assert results[0][1] > 0.99

    @pytest.mark.asyncio
    async def test_get_semantic_similar_chunks_no_model(self, detector):
        """Test semantic search fails gracefully without model."""
        detector._model = None
        res = await detector.get_semantic_similar_chunks("q", {"1": [1,0]})
        assert res == []

    @pytest.mark.asyncio
    async def test_get_semantic_similar_chunks_exception(self, detector):
        """Test semantic search exception handling."""
        mock_model = MagicMock()
        mock_model.encode.side_effect = Exception("Encode error")
        detector._model = mock_model
        
        res = await detector.get_semantic_similar_chunks("q", {"1": [1,0]})
        assert res == []
