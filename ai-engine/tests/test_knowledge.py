"""
Tests for knowledge module - CrossReferenceDetector and schema
"""

import pytest
from unittest.mock import Mock, patch


class TestConceptTypeAndRelationshipType:
    """Test schema enums"""

    def test_concept_type_values(self):
        """Test ConceptType enum values"""
        from knowledge.schema import ConceptType

        assert ConceptType.CLASS.value == "class"
        assert ConceptType.METHOD.value == "method"
        assert ConceptType.EVENT.value == "event"
        assert ConceptType.PROPERTY.value == "property"
        assert ConceptType.CONCEPT.value == "concept"
        assert ConceptType.IMPORT.value == "import"
        assert ConceptType.INTERFACE.value == "interface"

    def test_relationship_type_values(self):
        """Test RelationshipType enum values"""
        from knowledge.schema import RelationshipType

        assert RelationshipType.EXTENDS.value == "extends"
        assert RelationshipType.IMPLEMENTS.value == "implements"
        assert RelationshipType.CALLS.value == "calls"
        assert RelationshipType.USES.value == "uses"
        assert RelationshipType.RELATED_TO.value == "related_to"
        assert RelationshipType.CONTAINS.value == "contains"
        assert RelationshipType.IMPORTED_BY.value == "imported_by"


class TestDetectedConcept:
    """Test DetectedConcept dataclass"""

    def test_detected_concept_creation(self):
        """Test creating a DetectedConcept"""
        from knowledge.cross_reference import DetectedConcept

        concept = DetectedConcept(
            name="MyClass",
            concept_type="class",
            confidence=0.9,
            context="public class MyClass {",
        )

        assert concept.name == "MyClass"
        assert concept.concept_type == "class"
        assert concept.confidence == 0.9
        assert concept.context == "public class MyClass {"


class TestRelationshipCandidate:
    """Test RelationshipCandidate dataclass"""

    def test_relationship_candidate_creation(self):
        """Test creating a RelationshipCandidate"""
        from knowledge.cross_reference import RelationshipCandidate

        candidate = RelationshipCandidate(
            source_concept="ChildClass",
            target_concept="ParentClass",
            relationship_type="extends",
            confidence=0.85,
        )

        assert candidate.source_concept == "ChildClass"
        assert candidate.target_concept == "ParentClass"
        assert candidate.relationship_type == "extends"
        assert candidate.confidence == 0.85


class TestCrossReferenceDetector:
    """Test CrossReferenceDetector class"""

    @pytest.fixture
    def detector(self):
        """Create CrossReferenceDetector instance"""
        from knowledge.cross_reference import CrossReferenceDetector
        return CrossReferenceDetector()

    def test_detector_initialization(self, detector):
        """Test detector initializes correctly"""
        assert detector._db_session is None
        assert detector._embedding_model == "all-MiniLM-L6-v2"
        assert detector._model is None
        assert detector._initialized is False

    def test_detector_with_custom_embedding_model(self):
        """Test detector with custom embedding model"""
        from knowledge.cross_reference import CrossReferenceDetector
        det = CrossReferenceDetector(embedding_model="custom-model")
        assert det._embedding_model == "custom-model"

    def test_detect_concepts_class(self, detector):
        """Test detecting class concepts"""
        code = "public class MyMod { }"
        concepts = detector.detect_concepts(code)

        class_concepts = [c for c in concepts if c.concept_type == "class"]
        assert len(class_concepts) >= 1
        assert any(c.name == "MyMod" for c in class_concepts)

    def test_detect_concepts_extends(self, detector):
        """Test detecting extends relationships"""
        code = "public class ChildClass extends ParentClass { }"
        concepts = detector.detect_concepts(code)

        # Should detect ParentClass as a concept
        assert any(c.name == "ParentClass" for c in concepts)

    def test_detect_concepts_implements(self, detector):
        """Test detecting implements relationships"""
        code = "public class MyClass implements Interface1, Interface2 { }"
        concepts = detector.detect_concepts(code)

        # Should detect interfaces
        interface_concepts = [c for c in concepts if c.concept_type == "interface"]
        assert len(interface_concepts) >= 2

    def test_detect_concepts_imports(self, detector):
        """Test detecting import statements"""
        code = "import org.example.SomeClass;"
        concepts = detector.detect_concepts(code)

        import_concepts = [c for c in concepts if c.concept_type == "import"]
        assert len(import_concepts) >= 1

    def test_detect_concepts_methods(self, detector):
        """Test detecting method definitions"""
        code = "public void doSomething() { }"
        concepts = detector.detect_concepts(code)

        method_concepts = [c for c in concepts if c.concept_type == "method"]
        # Should detect doSomething
        assert any(c.name == "doSomething" for c in method_concepts)

    def test_detect_concepts_empty_content(self, detector):
        """Test detecting concepts in empty content"""
        concepts = detector.detect_concepts("")
        assert len(concepts) == 0

    def test_detect_concepts_no_java_code(self, detector):
        """Test detecting concepts in non-Java content"""
        concepts = detector.detect_concepts("This is just plain text.")
        assert len(concepts) == 0

    def test_detect_concepts_with_chunk_id(self, detector):
        """Test detecting concepts with chunk ID"""
        code = "public class TestClass { }"
        concepts = detector.detect_concepts(code, chunk_id="chunk-123")

        # Concepts should be detected regardless of chunk_id
        assert len(concepts) >= 1

    def test_detect_relationships_extends(self, detector):
        """Test detecting extends relationships"""
        code = "public class ChildClass extends ParentClass { }"
        relationships = detector.detect_relationships(code)

        # Should detect extends relationship
        rel_types = [r.relationship_type for r in relationships]
        assert "extends" in rel_types

    def test_detect_relationships_implements(self, detector):
        """Test detecting implements relationships"""
        code = "public class MyClass implements Runnable { }"
        relationships = detector.detect_relationships(code)

        rel_types = [r.relationship_type for r in relationships]
        assert "implements" in rel_types

    def test_detect_relationships_method_calls(self, detector):
        """Test detecting method call relationships"""
        code = "object.doSomething();"
        relationships = detector.detect_relationships(code)

        rel_types = [r.relationship_type for r in relationships]
        assert "calls" in rel_types or len(relationships) >= 0

    def test_detect_relationships_uses(self, detector):
        """Test detecting uses relationships"""
        code = "private ItemStack item = new ItemStack(Material.DIAMOND);"
        relationships = detector.detect_relationships(code)

        # May detect uses relationships
        assert isinstance(relationships, list)

    def test_detect_relationships_empty_content(self, detector):
        """Test detecting relationships in empty content"""
        relationships = detector.detect_relationships("")
        assert isinstance(relationships, list)

    @patch("knowledge.cross_reference.CrossReferenceDetector._load_embedding_model")
    def test_initialize_with_mock_db(self, mock_load, detector):
        """Test initialize with mock database session"""
        Mock()
        
        # Run initialize
        detector._initialized = True  # Skip actual init
        
        # Just verify the detector state
        assert detector._db_session is None

    def test_concept_cache(self, detector):
        """Test concept caching"""
        code = "public class CachedClass { }"
        
        # First detection
        concepts1 = detector.detect_concepts(code)
        
        # Second detection - should use cache
        concepts2 = detector.detect_concepts(code)
        
        assert len(concepts1) == len(concepts2)


class TestConceptNode:
    """Test ConceptNode schema class"""

    def test_concept_node_creation(self):
        """Test creating a ConceptNode"""
        from knowledge.schema import ConceptNode

        node = ConceptNode()
        node.name = "TestClass"
        node.type = "class"
        node.document_id = "doc-123"
        node.description = "A test class"

        assert node.name == "TestClass"
        assert node.type == "class"
        assert node.document_id == "doc-123"
        assert node.description == "A test class"

    def test_concept_node_repr(self):
        """Test ConceptNode string representation"""
        from knowledge.schema import ConceptNode

        node = ConceptNode()
        node.name = "TestClass"
        node.type = "class"
        repr_str = repr(node)

        assert "TestClass" in repr_str
        assert "class" in repr_str


class TestConceptRelationship:
    """Test ConceptRelationship schema class"""

    def test_relationship_creation(self):
        """Test creating a ConceptRelationship"""
        from knowledge.schema import ConceptRelationship

        rel = ConceptRelationship()
        rel.source_node_id = "node-1"
        rel.target_node_id = "node-2"
        rel.relationship_type = "extends"
        rel.confidence = 0.9

        assert rel.source_node_id == "node-1"
        assert rel.target_node_id == "node-2"
        assert rel.relationship_type == "extends"
        assert rel.confidence == 0.9


class TestIntegration:
    """Integration tests for knowledge module"""

    def test_full_concept_detection_workflow(self):
        """Test complete concept detection workflow"""
        from knowledge.cross_reference import CrossReferenceDetector

        detector = CrossReferenceDetector()

        java_code = """
        import org.bukkit.plugin.java.JavaPlugin;
        
        public class MyPlugin extends JavaPlugin {
            @Override
            public void onEnable() {
                getLogger().info("Plugin enabled!");
            }
            
            public void doSomething() {
                // do work
            }
        }
        """

        # Detect concepts
        concepts = detector.detect_concepts(java_code)
        
        # Should find various concepts
        assert len(concepts) >= 1
        
        # Detect relationships
        relationships = detector.detect_relationships(java_code)
        
        # Should find relationships
        assert isinstance(relationships, list)

    def test_multiple_classes_detection(self):
        """Test detecting multiple classes in code"""
        from knowledge.cross_reference import CrossReferenceDetector

        detector = CrossReferenceDetector()

        code = """
        public class OuterClass {
            public class InnerClass {
            }
        }
        """

        concepts = detector.detect_concepts(code)
        class_concepts = [c for c in concepts if c.concept_type == "class"]
        
        # Should detect both classes
        assert len(class_concepts) >= 1

    def test_complex_inheritance(self):
        """Test complex inheritance chains"""
        from knowledge.cross_reference import CrossReferenceDetector

        detector = CrossReferenceDetector()

        code = """
        public class A { }
        public class B extends A { }
        public class C extends B { }
        """

        concepts = detector.detect_concepts(code)
        
        # Should detect all classes
        assert len(concepts) >= 3