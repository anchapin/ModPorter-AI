"""
Comprehensive tests for KnowledgeGraphCRUD.

This module tests the CRUD operations for knowledge graph models,
including nodes, relationships, patterns, and community contributions.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import uuid

from src.db.models import (
    KnowledgeNode, KnowledgeRelationship, ConversionPattern,
    CommunityContribution, VersionCompatibility
)
from src.db.knowledge_graph_crud import (
    KnowledgeNodeCRUD, KnowledgeRelationshipCRUD, ConversionPatternCRUD,
    CommunityContributionCRUD, VersionCompatibilityCRUD
)


class TestKnowledgeNodeCRUD:
    """Test cases for KnowledgeNodeCRUD class."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session for testing."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        return session

    @pytest.fixture
    def mock_graph_db(self):
        """Create a mock graph database for testing."""
        graph = MagicMock()
        graph.create_node = AsyncMock(return_value="neo4j_id_123")
        graph.update_node = AsyncMock(return_value=True)
        graph.delete_node = AsyncMock(return_value=True)
        graph.get_node = AsyncMock(return_value={
            "id": "neo4j_id_123",
            "labels": ["JavaConcept"],
            "properties": {
                "name": "TestNode",
                "node_type": "java_concept",
                "platform": "java",
                "minecraft_version": "1.18.2"
            }
        })
        graph.find_nodes = AsyncMock(return_value=[
            {
                "id": "neo4j_id_123",
                "labels": ["JavaConcept"],
                "properties": {
                    "name": "TestNode",
                    "node_type": "java_concept"
                }
            }
        ])
        graph.get_node_relationships = AsyncMock(return_value=[
            {
                "id": "rel_1",
                "type": "CONVERTS_TO",
                "source": "neo4j_id_123",
                "target": "neo4j_id_456",
                "properties": {"confidence": 0.85}
            }
        ])
        return graph

    @pytest.fixture
    def sample_knowledge_node(self):
        """Sample knowledge node for testing."""
        return KnowledgeNode(
            id=uuid.uuid4(),
            title="Test Java Block",
            description="A test Java block for unit testing",
            node_type="java_concept",
            metadata={
                "class": "Block",
                "package": "net.minecraft.block",
                "minecraft_version": "1.18.2"
            },
            embedding=[0.1, 0.2, 0.3],
            platform="java",
            minecraft_version="1.18.2",
            created_by="test_user",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

    @pytest.fixture
    def sample_node_data(self):
        """Sample node data for creating a knowledge node."""
        return {
            "title": "Test Bedrock Component",
            "description": "A test Bedrock component for unit testing",
            "node_type": "bedrock_concept",
            "metadata": {
                "component": "minecraft:block",
                "format_version": "1.16.0",
                "minecraft_version": "1.18.0"
            },
            "embedding": [0.2, 0.3, 0.4],
            "platform": "bedrock",
            "minecraft_version": "1.18.0",
            "created_by": "test_user"
        }

    @pytest.mark.asyncio
    async def test_create_node(self, mock_db_session, mock_graph_db, sample_node_data):
        """Test creating a new knowledge node."""
        # Mock the database query result
        mock_node = KnowledgeNode(
            id=uuid.uuid4(),
            title=sample_node_data["title"],
            description=sample_node_data["description"],
            node_type=sample_node_data["node_type"],
            metadata=sample_node_data["metadata"],
            embedding=sample_node_data["embedding"],
            platform=sample_node_data["platform"],
            minecraft_version=sample_node_data["minecraft_version"],
            created_by=sample_node_data["created_by"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        mock_db_session.add = MagicMock()
        mock_db_session.execute.return_value = None

        # Mock the database refresh
        mock_db_session.refresh.return_value = None
        mock_db_session.execute.return_value = None

        with patch('src.db.knowledge_graph_crud.optimized_graph_db', mock_graph_db):
            # Call the method
            result = await KnowledgeNodeCRUD.create(mock_db_session, sample_node_data)

            # Verify the result
            assert result is not None
            assert result.title == sample_node_data["title"]
            assert result.node_type == sample_node_data["node_type"]
            assert result.platform == sample_node_data["platform"]
            assert result.minecraft_version == sample_node_data["minecraft_version"]

            # Verify database operations were called
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called()
            mock_db_session.refresh.assert_called()
            mock_graph_db.create_node.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_node_by_id(self, mock_db_session, mock_graph_db, sample_knowledge_node):
        """Test getting a knowledge node by ID."""
        # Mock database query to return our sample node
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = sample_knowledge_node

        with patch('src.db.knowledge_graph_crud.optimized_graph_db', mock_graph_db):
            # Call the method
            result = await KnowledgeNodeCRUD.get_by_id(mock_db_session, sample_knowledge_node.id)

            # Verify the result
            assert result is not None
            assert result.id == sample_knowledge_node.id
            assert result.title == sample_knowledge_node.title
            assert result.node_type == sample_knowledge_node.node_type

            # Verify database operations were called
            mock_db_session.execute.assert_called_once()
            mock_graph_db.get_node.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_node_by_id_not_found(self, mock_db_session, mock_graph_db):
        """Test getting a knowledge node by ID when not found."""
        # Mock database query to return None
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None

        with patch('src.db.knowledge_graph_crud.optimized_graph_db', mock_graph_db):
            # Call the method
            result = await KnowledgeNodeCRUD.get_by_id(mock_db_session, uuid.uuid4())

            # Verify the result is None
            assert result is None

            # Verify database operations were called
            mock_db_session.execute.assert_called_once()
            mock_graph_db.get_node.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_nodes_by_type(self, mock_db_session, sample_knowledge_node):
        """Test getting knowledge nodes by type."""
        # Mock database query to return a list of nodes
        nodes = [sample_knowledge_node]
        mock_db_session.execute.return_value.scalars().all.return_value = nodes

        # Call the method
        result = await KnowledgeNodeCRUD.get_by_type(mock_db_session, "java_concept")

        # Verify the result
        assert result is not None
        assert len(result) == 1
        assert result[0].id == sample_knowledge_node.id
        assert result[0].node_type == "java_concept"

        # Verify database operations were called
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_nodes_by_platform(self, mock_db_session, sample_knowledge_node):
        """Test getting knowledge nodes by platform."""
        # Mock database query to return a list of nodes
        nodes = [sample_knowledge_node]
        mock_db_session.execute.return_value.scalars().all.return_value = nodes

        # Call the method
        result = await KnowledgeNodeCRUD.get_by_platform(mock_db_session, "java")

        # Verify the result
        assert result is not None
        assert len(result) == 1
        assert result[0].id == sample_knowledge_node.id
        assert result[0].platform == "java"

        # Verify database operations were called
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_nodes(self, mock_db_session, sample_knowledge_node):
        """Test searching for knowledge nodes."""
        # Mock database query to return a list of nodes
        nodes = [sample_knowledge_node]
        mock_db_session.execute.return_value.scalars().all.return_value = nodes

        # Call the method
        result = await KnowledgeNodeCRUD.search(mock_db_session, "Block", limit=10)

        # Verify the result
        assert result is not None
        assert len(result) == 1
        assert result[0].id == sample_knowledge_node.id
        assert "Block" in result[0].title

        # Verify database operations were called
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_node(self, mock_db_session, mock_graph_db, sample_knowledge_node):
        """Test updating a knowledge node."""
        # Mock database query to return our sample node
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = sample_knowledge_node

        # Mock update data
        update_data = {
            "title": "Updated Node Title",
            "description": "Updated description",
            "metadata": {"updated": True}
        }

        with patch('src.db.knowledge_graph_crud.optimized_graph_db', mock_graph_db):
            # Call the method
            result = await KnowledgeNodeCRUD.update(mock_db_session, sample_knowledge_node.id, update_data)

            # Verify the result
            assert result is not None
            assert result.id == sample_knowledge_node.id

            # Verify database operations were called
            mock_db_session.commit.assert_called()
            mock_db_session.refresh.assert_called()
            mock_graph_db.update_node.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_node(self, mock_db_session, mock_graph_db, sample_knowledge_node):
        """Test deleting a knowledge node."""
        # Mock database query to return our sample node
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = sample_knowledge_node

        with patch('src.db.knowledge_graph_crud.optimized_graph_db', mock_graph_db):
            # Call the method
            result = await KnowledgeNodeCRUD.delete(mock_db_session, sample_knowledge_node.id)

            # Verify the result
            assert result is True

            # Verify database operations were called
            mock_db_session.delete.assert_called_once()
            mock_db_session.commit.assert_called()
            mock_graph_db.delete_node.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_node_not_found(self, mock_db_session, mock_graph_db):
        """Test deleting a knowledge node when not found."""
        # Mock database query to return None
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None

        with patch('src.db.knowledge_graph_crud.optimized_graph_db', mock_graph_db):
            # Call the method
            result = await KnowledgeNodeCRUD.delete(mock_db_session, uuid.uuid4())

            # Verify the result
            assert result is False

            # Verify database operations were called
            mock_db_session.delete.assert_not_called()
            mock_db_session.commit.assert_not_called()
            mock_graph_db.delete_node.assert_not_called()


class TestKnowledgeRelationshipCRUD:
    """Test cases for KnowledgeRelationshipCRUD class."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session for testing."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        session.delete = MagicMock()
        return session

    @pytest.fixture
    def mock_graph_db(self):
        """Create a mock graph database for testing."""
        graph = MagicMock()
        graph.create_relationship = AsyncMock(return_value="rel_id_123")
        graph.update_relationship = AsyncMock(return_value=True)
        graph.delete_relationship = AsyncMock(return_value=True)
        graph.get_relationship = AsyncMock(return_value={
            "id": "rel_id_123",
            "type": "CONVERTS_TO",
            "source": "neo4j_id_123",
            "target": "neo4j_id_456",
            "properties": {"confidence": 0.85}
        })
        graph.find_relationships = AsyncMock(return_value=[
            {
                "id": "rel_id_123",
                "type": "CONVERTS_TO",
                "source": "neo4j_id_123",
                "target": "neo4j_id_456",
                "properties": {"confidence": 0.85}
            }
        ])
        return graph

    @pytest.fixture
    def sample_knowledge_relationship(self):
        """Sample knowledge relationship for testing."""
        return KnowledgeRelationship(
            id=uuid.uuid4(),
            source_id=uuid.uuid4(),
            target_id=uuid.uuid4(),
            relationship_type="converts_to",
            confidence=0.85,
            metadata={
                "conversion_difficulty": "medium",
                "notes": "Standard conversion pattern"
            },
            created_at=datetime.utcnow()
        )

    @pytest.fixture
    def sample_relationship_data(self):
        """Sample relationship data for creating a knowledge relationship."""
        return {
            "source_id": uuid.uuid4(),
            "target_id": uuid.uuid4(),
            "relationship_type": "converts_to",
            "confidence": 0.9,
            "metadata": {
                "conversion_difficulty": "low",
                "notes": "Simple conversion"
            }
        }

    @pytest.mark.asyncio
    async def test_create_relationship(self, mock_db_session, mock_graph_db, sample_relationship_data):
        """Test creating a new knowledge relationship."""
        # Mock the database query result
        mock_relationship = KnowledgeRelationship(
            id=uuid.uuid4(),
            source_id=sample_relationship_data["source_id"],
            target_id=sample_relationship_data["target_id"],
            relationship_type=sample_relationship_data["relationship_type"],
            confidence=sample_relationship_data["confidence"],
            metadata=sample_relationship_data["metadata"],
            created_at=datetime.utcnow()
        )
        mock_db_session.add = MagicMock()
        mock_db_session.execute.return_value = None

        # Mock the database refresh
        mock_db_session.refresh.return_value = None
        mock_db_session.execute.return_value = None

        with patch('src.db.knowledge_graph_crud.optimized_graph_db', mock_graph_db):
            # Call the method
            result = await KnowledgeRelationshipCRUD.create(mock_db_session, sample_relationship_data)

            # Verify the result
            assert result is not None
            assert result.source_id == sample_relationship_data["source_id"]
            assert result.target_id == sample_relationship_data["target_id"]
            assert result.relationship_type == sample_relationship_data["relationship_type"]
            assert result.confidence == sample_relationship_data["confidence"]

            # Verify database operations were called
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called()
            mock_db_session.refresh.assert_called()
            mock_graph_db.create_relationship.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_relationship_by_id(self, mock_db_session, mock_graph_db, sample_knowledge_relationship):
        """Test getting a knowledge relationship by ID."""
        # Mock database query to return our sample relationship
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = sample_knowledge_relationship

        with patch('src.db.knowledge_graph_crud.optimized_graph_db', mock_graph_db):
            # Call the method
            result = await KnowledgeRelationshipCRUD.get_by_id(mock_db_session, sample_knowledge_relationship.id)

            # Verify the result
            assert result is not None
            assert result.id == sample_knowledge_relationship.id
            assert result.source_id == sample_knowledge_relationship.source_id
            assert result.target_id == sample_knowledge_relationship.target_id
            assert result.relationship_type == sample_knowledge_relationship.relationship_type

            # Verify database operations were called
            mock_db_session.execute.assert_called_once()
            mock_graph_db.get_relationship.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_relationships_by_source(self, mock_db_session, sample_knowledge_relationship):
        """Test getting relationships by source node ID."""
        # Mock database query to return a list of relationships
        relationships = [sample_knowledge_relationship]
        mock_db_session.execute.return_value.scalars().all.return_value = relationships

        # Call the method
        result = await KnowledgeRelationshipCRUD.get_by_source(mock_db_session, sample_knowledge_relationship.source_id)

        # Verify the result
        assert result is not None
        assert len(result) == 1
        assert result[0].id == sample_knowledge_relationship.id
        assert result[0].source_id == sample_knowledge_relationship.source_id

        # Verify database operations were called
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_relationships_by_target(self, mock_db_session, sample_knowledge_relationship):
        """Test getting relationships by target node ID."""
        # Mock database query to return a list of relationships
        relationships = [sample_knowledge_relationship]
        mock_db_session.execute.return_value.scalars().all.return_value = relationships

        # Call the method
        result = await KnowledgeRelationshipCRUD.get_by_target(mock_db_session, sample_knowledge_relationship.target_id)

        # Verify the result
        assert result is not None
        assert len(result) == 1
        assert result[0].id == sample_knowledge_relationship.id
        assert result[0].target_id == sample_knowledge_relationship.target_id

        # Verify database operations were called
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_relationships_by_type(self, mock_db_session, sample_knowledge_relationship):
        """Test getting relationships by type."""
        # Mock database query to return a list of relationships
        relationships = [sample_knowledge_relationship]
        mock_db_session.execute.return_value.scalars().all.return_value = relationships

        # Call the method
        result = await KnowledgeRelationshipCRUD.get_by_type(mock_db_session, "converts_to")

        # Verify the result
        assert result is not None
        assert len(result) == 1
        assert result[0].id == sample_knowledge_relationship.id
        assert result[0].relationship_type == "converts_to"

        # Verify database operations were called
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_relationship(self, mock_db_session, mock_graph_db, sample_knowledge_relationship):
        """Test updating a knowledge relationship."""
        # Mock database query to return our sample relationship
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = sample_knowledge_relationship

        # Mock update data
        update_data = {
            "confidence": 0.95,
            "metadata": {"updated": True}
        }

        with patch('src.db.knowledge_graph_crud.optimized_graph_db', mock_graph_db):
            # Call the method
            result = await KnowledgeRelationshipCRUD.update(mock_db_session, sample_knowledge_relationship.id, update_data)

            # Verify the result
            assert result is not None
            assert result.id == sample_knowledge_relationship.id

            # Verify database operations were called
            mock_db_session.commit.assert_called()
            mock_db_session.refresh.assert_called()
            mock_graph_db.update_relationship.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_relationship(self, mock_db_session, mock_graph_db, sample_knowledge_relationship):
        """Test deleting a knowledge relationship."""
        # Mock database query to return our sample relationship
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = sample_knowledge_relationship

        with patch('src.db.knowledge_graph_crud.optimized_graph_db', mock_graph_db):
            # Call the method
            result = await KnowledgeRelationshipCRUD.delete(mock_db_session, sample_knowledge_relationship.id)

            # Verify the result
            assert result is True

            # Verify database operations were called
            mock_db_session.delete.assert_called_once()
            mock_db_session.commit.assert_called()
            mock_graph_db.delete_relationship.assert_called_once()


class TestConversionPatternCRUD:
    """Test cases for ConversionPatternCRUD class."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session for testing."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        session.delete = MagicMock()
        return session

    @pytest.fixture
    def sample_conversion_pattern(self):
        """Sample conversion pattern for testing."""
        return ConversionPattern(
            id=uuid.uuid4(),
            name="Java Block to Bedrock Component",
            description="Standard conversion from Java Block class to Bedrock block component",
            java_template="public class {class_name} extends Block { ... }",
            bedrock_template="{ \"format_version\": \"1.16.0\", \"minecraft:block\": { ... } }",
            variables=["class_name", "identifier"],
            success_rate=0.85,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

    @pytest.fixture
    def sample_pattern_data(self):
        """Sample pattern data for creating a conversion pattern."""
        return {
            "name": "Java Item to Bedrock Item",
            "description": "Standard conversion from Java Item class to Bedrock item",
            "java_template=": "public class {class_name} extends Item { ... }",
            "bedrock_template": "{ \"format_version\": \"1.16.0\", \"minecraft:item\": { ... } }",
            "variables": ["class_name", "identifier"],
            "success_rate": 0.9
        }

    @pytest.mark.asyncio
    async def test_create_pattern(self, mock_db_session, sample_pattern_data):
        """Test creating a new conversion pattern."""
        # Mock the database query result
        mock_pattern = ConversionPattern(
            id=uuid.uuid4(),
            name=sample_pattern_data["name"],
            description=sample_pattern_data["description"],
            java_template=sample_pattern_data["java_template="],
            bedrock_template=sample_pattern_data["bedrock_template"],
            variables=sample_pattern_data["variables"],
            success_rate=sample_pattern_data["success_rate"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        mock_db_session.add = MagicMock()
        mock_db_session.execute.return_value = None
        mock_db_session.refresh.return_value = None

        # Call the method
        result = await ConversionPatternCRUD.create(mock_db_session, sample_pattern_data)

        # Verify the result
        assert result is not None
        assert result.name == sample_pattern_data["name"]
        assert result.description == sample_pattern_data["description"]
        assert result.java_template == sample_pattern_data["java_template="]
        assert result.bedrock_template == sample_pattern_data["bedrock_template"]
        assert result.variables == sample_pattern_data["variables"]
        assert result.success_rate == sample_pattern_data["success_rate"]

        # Verify database operations were called
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pattern_by_id(self, mock_db_session, sample_conversion_pattern):
        """Test getting a conversion pattern by ID."""
        # Mock database query to return our sample pattern
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = sample_conversion_pattern

        # Call the method
        result = await ConversionPatternCRUD.get_by_id(mock_db_session, sample_conversion_pattern.id)

        # Verify the result
        assert result is not None
        assert result.id == sample_conversion_pattern.id
        assert result.name == sample_conversion_pattern.name
        assert result.description == sample_conversion_pattern.description

        # Verify database operations were called
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_patterns_by_name(self, mock_db_session, sample_conversion_pattern):
        """Test getting conversion patterns by name."""
        # Mock database query to return a list of patterns
        patterns = [sample_conversion_pattern]
        mock_db_session.execute.return_value.scalars().all.return_value = patterns

        # Call the method
        result = await ConversionPatternCRUD.get_by_name(mock_db_session, "Java Block to Bedrock Component")

        # Verify the result
        assert result is not None
        assert len(result) == 1
        assert result[0].id == sample_conversion_pattern.id
        assert result[0].name == sample_conversion_pattern.name

        # Verify database operations were called
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_pattern(self, mock_db_session, sample_conversion_pattern):
        """Test updating a conversion pattern."""
        # Mock database query to return our sample pattern
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = sample_conversion_pattern

        # Mock update data
        update_data = {
            "success_rate": 0.9,
            "description": "Updated description"
        }

        # Call the method
        result = await ConversionPatternCRUD.update(mock_db_session, sample_conversion_pattern.id, update_data)

        # Verify the result
        assert result is not None
        assert result.id == sample_conversion_pattern.id

        # Verify database operations were called
        mock_db_session.commit.assert_called()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_pattern(self, mock_db_session, sample_conversion_pattern):
        """Test deleting a conversion pattern."""
        # Mock database query to return our sample pattern
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = sample_conversion_pattern

        # Call the method
        result = await ConversionPatternCRUD.delete(mock_db_session, sample_conversion_pattern.id)

        # Verify the result
        assert result is True

        # Verify database operations were called
        mock_db_session.delete.assert_called_once()
        mock_db_session.commit.assert_called_once()


class TestVersionCompatibilityCRUD:
    """Test cases for VersionCompatibilityCRUD class."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session for testing."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        session.delete = MagicMock()
        return session

    @pytest.fixture
    def sample_version_compatibility(self):
        """Sample version compatibility for testing."""
        return VersionCompatibility(
            id=uuid.uuid4(),
            java_version="1.18.2",
            bedrock_version="1.18.0",
            compatibility_score=0.9,
            issues=[
                {
                    "category": "block_properties",
                    "description": "Some block properties differ between Java and Bedrock",
                    "severity": "medium",
                    "workaround": "Use alternative properties"
                }
            ],
            features_supported=[
                "basic_blocks",
                "custom_items",
                "simple_entities"
            ],
            features_unsupported=[
                "advanced_redstone",
                "complex_entity_ai"
            ],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

    @pytest.fixture
    def sample_compatibility_data(self):
        """Sample compatibility data for creating a version compatibility entry."""
        return {
            "java_version": "1.19.0",
            "bedrock_version": "1.19.0",
            "compatibility_score": 0.85,
            "issues": [
                {
                    "category": "item_components",
                    "description": "Item components have different implementations",
                    "severity": "low",
                    "workaround": "Use component translation layer"
                }
            ],
            "features_supported": [
                "basic_blocks",
                "custom_items",
                "simple_entities",
                "advanced_redstone"
            ],
            "features_unsupported": [
                "complex_entity_ai",
                "custom_dimensions"
            ]
        }

    @pytest.mark.asyncio
    async def test_create_compatibility(self, mock_db_session, sample_compatibility_data):
        """Test creating a new version compatibility entry."""
        # Mock the database query result
        mock_compatibility = VersionCompatibility(
            id=uuid.uuid4(),
            java_version=sample_compatibility_data["java_version"],
            bedrock_version=sample_compatibility_data["bedrock_version"],
            compatibility_score=sample_compatibility_data["compatibility_score"],
            issues=sample_compatibility_data["issues"],
            features_supported=sample_compatibility_data["features_supported"],
            features_unsupported=sample_compatibility_data["features_unsupported"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        mock_db_session.add = MagicMock()
        mock_db_session.execute.return_value = None
        mock_db_session.refresh.return_value = None

        # Call the method
        result = await VersionCompatibilityCRUD.create(mock_db_session, sample_compatibility_data)

        # Verify the result
        assert result is not None
        assert result.java_version == sample_compatibility_data["java_version"]
        assert result.bedrock_version == sample_compatibility_data["bedrock_version"]
        assert result.compatibility_score == sample_compatibility_data["compatibility_score"]

        # Verify database operations were called
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_compatibility(self, mock_db_session, sample_version_compatibility):
        """Test getting version compatibility by Java and Bedrock versions."""
        # Mock database query to return our sample compatibility
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = sample_version_compatibility

        # Call the method
        result = await VersionCompatibilityCRUD.get_compatibility(
            mock_db_session,
            sample_version_compatibility.java_version,
            sample_version_compatibility.bedrock_version
        )

        # Verify the result
        assert result is not None
        assert result.id == sample_version_compatibility.id
        assert result.java_version == sample_version_compatibility.java_version
        assert result.bedrock_version == sample_version_compatibility.bedrock_version
        assert result.compatibility_score == sample_version_compatibility.compatibility_score

        # Verify database operations were called
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_compatibility_by_java_version(self, mock_db_session, sample_version_compatibility):
        """Test getting version compatibilities by Java version."""
        # Mock database query to return a list of compatibilities
        compatibilities = [sample_version_compatibility]
        mock_db_session.execute.return_value.scalars().all.return_value = compatibilities

        # Call the method
        result = await VersionCompatibilityCRUD.get_by_java_version(
            mock_db_session,
            sample_version_compatibility.java_version
        )

        # Verify the result
        assert result is not None
        assert len(result) == 1
        assert result[0].id == sample_version_compatibility.id
        assert result[0].java_version == sample_version_compatibility.java_version

        # Verify database operations were called
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_compatibility_by_bedrock_version(self, mock_db_session, sample_version_compatibility):
        """Test getting version compatibilities by Bedrock version."""
        # Mock database query to return a list of compatibilities
        compatibilities = [sample_version_compatibility]
        mock_db_session.execute.return_value.scalars().all.return_value = compatibilities

        # Call the method
        result = await VersionCompatibilityCRUD.get_by_bedrock_version(
            mock_db_session,
            sample_version_compatibility.bedrock_version
        )

        # Verify the result
        assert result is not None
        assert len(result) == 1
        assert result[0].id == sample_version_compatibility.id
        assert result[0].bedrock_version == sample_version_compatibility.bedrock_version

        # Verify database operations were called
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_compatibility(self, mock_db_session, sample_version_compatibility):
        """Test updating a version compatibility entry."""
        # Mock database query to return our sample compatibility
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = sample_version_compatibility

        # Mock update data
        update_data = {
            "compatibility_score": 0.95,
            "features_supported": ["basic_blocks", "custom_items", "advanced_redstone"]
        }

        # Call the method
        result = await VersionCompatibilityCRUD.update(
            mock_db_session,
            sample_version_compatibility.id,
            update_data
        )

        # Verify the result
        assert result is not None
        assert result.id == sample_version_compatibility.id

        # Verify database operations were called
        mock_db_session.commit.assert_called()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_compatibility(self, mock_db_session, sample_version_compatibility):
        """Test deleting a version compatibility entry."""
        # Mock database query to return our sample compatibility
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = sample_version_compatibility

        # Call the method
        result = await VersionCompatibilityCRUD.delete(mock_db_session, sample_version_compatibility.id)

        # Verify the result
        assert result is True

        # Verify database operations were called
        mock_db_session.delete.assert_called_once()
        mock_db_session.commit.assert_called_once()


class TestCommunityContributionCRUD:
    """Test cases for CommunityContributionCRUD class."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session for testing."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        session.delete = MagicMock()
        return session

    @pytest.fixture
    def sample_community_contribution(self):
        """Sample community contribution for testing."""
        return CommunityContribution(
            id=uuid.uuid4(),
            author_id="user_123",
            contribution_type="pattern_improvement",
            target_id=uuid.uuid4(),
            title="Improved block conversion pattern",
            description="Enhanced the block conversion pattern with better material mapping",
            data={
                "java_improvement": "Added support for custom block properties",
                "bedrock_improvement": "Improved component structure validation"
            },
            status="approved",
            votes=15,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

    @pytest.fixture
    def sample_contribution_data(self):
        """Sample contribution data for creating a community contribution."""
        return {
            "author_id": "user_456",
            "contribution_type": "new_pattern",
            "target_id": uuid.uuid4(),
            "title": "New entity conversion pattern",
            "description": "Added support for converting complex entities",
            "data": {
                "java_entity": "CustomEntity",
                "bedrock_entity": "custom:entity",
                "components": ["minecraft:health", "minecraft:movement"]
            },
            "status": "pending"
        }

    @pytest.mark.asyncio
    async def test_create_contribution(self, mock_db_session, sample_contribution_data):
        """Test creating a new community contribution."""
        # Mock the database query result
        mock_contribution = CommunityContribution(
            id=uuid.uuid4(),
            author_id=sample_contribution_data["author_id"],
            contribution_type=sample_contribution_data["contribution_type"],
            target_id=sample_contribution_data["target_id"],
            title=sample_contribution_data["title"],
            description=sample_contribution_data["description"],
            data=sample_contribution_data["data"],
            status=sample_contribution_data["status"],
            votes=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        mock_db_session.add = MagicMock()
        mock_db_session.execute.return_value = None
        mock_db_session.refresh.return_value = None

        # Call the method
        result = await CommunityContributionCRUD.create(mock_db_session, sample_contribution_data)

        # Verify the result
        assert result is not None
        assert result.author_id == sample_contribution_data["author_id"]
        assert result.contribution_type == sample_contribution_data["contribution_type"]
        assert result.title == sample_contribution_data["title"]
        assert result.description == sample_contribution_data["description"]
        assert result.status == sample_contribution_data["status"]
        assert result.votes == 0  # Default value

        # Verify database operations were called
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_contribution_by_id(self, mock_db_session, sample_community_contribution):
        """Test getting a community contribution by ID."""
        # Mock database query to return our sample contribution
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = sample_community_contribution

        # Call the method
        result = await CommunityContributionCRUD.get_by_id(mock_db_session, sample_community_contribution.id)

        # Verify the result
        assert result is not None
        assert result.id == sample_community_contribution.id
        assert result.author_id == sample_community_contribution.author_id
        assert result.title == sample_community_contribution.title

        # Verify database operations were called
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_contributions_by_author(self, mock_db_session, sample_community_contribution):
        """Test getting contributions by author ID."""
        # Mock database query to return a list of contributions
        contributions = [sample_community_contribution]
        mock_db_session.execute.return_value.scalars().all.return_value = contributions

        # Call the method
        result = await CommunityContributionCRUD.get_by_author(
            mock_db_session,
            sample_community_contribution.author_id
        )

        # Verify the result
        assert result is not None
        assert len(result) == 1
        assert result[0].id == sample_community_contribution.id
        assert result[0].author_id == sample_community_contribution.author_id

        # Verify database operations were called
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_contributions_by_status(self, mock_db_session, sample_community_contribution):
        """Test getting contributions by status."""
        # Mock database query to return a list of contributions
        contributions = [sample_community_contribution]
        mock_db_session.execute.return_value.scalars().all.return_value = contributions

        # Call the method
        result = await CommunityContributionCRUD.get_by_status(mock_db_session, "approved")

        # Verify the result
        assert result is not None
        assert len(result) == 1
        assert result[0].id == sample_community_contribution.id
        assert result[0].status == "approved"

        # Verify database operations were called
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_contribution(self, mock_db_session, sample_community_contribution):
        """Test updating a community contribution."""
        # Mock database query to return our sample contribution
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = sample_community_contribution

        # Mock update data
        update_data = {
            "status": "approved",
            "votes": 20
        }

        # Call the method
        result = await CommunityContributionCRUD.update(
            mock_db_session,
            sample_community_contribution.id,
            update_data
        )

        # Verify the result
        assert result is not None
        assert result.id == sample_community_contribution.id

        # Verify database operations were called
        mock_db_session.commit.assert_called()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_upvote_contribution(self, mock_db_session, sample_community_contribution):
        """Test upvoting a community contribution."""
        # Mock database query to return our sample contribution
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = sample_community_contribution

        # Call the method
        result = await CommunityContributionCRUD.upvote(mock_db_session, sample_community_contribution.id)

        # Verify the result
        assert result is True

        # Verify database operations were called
        mock_db_session.commit.assert_called()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_downvote_contribution(self, mock_db_session, sample_community_contribution):
        """Test downvoting a community contribution."""
        # Mock database query to return our sample contribution
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = sample_community_contribution

        # Call the method
        result = await CommunityContributionCRUD.downvote(mock_db_session, sample_community_contribution.id)

        # Verify the result
        assert result is True

        # Verify database operations were called
        mock_db_session.commit.assert_called()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_contribution(self, mock_db_session, sample_community_contribution):
        """Test deleting a community contribution."""
        # Mock database query to return our sample contribution
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = sample_community_contribution

        # Call the method
        result = await CommunityContributionCRUD.delete(mock_db_session, sample_community_contribution.id)

        # Verify the result
        assert result is True

        # Verify database operations were called
        mock_db_session.delete.assert_called_once()
        mock_db_session.commit.assert_called_once()
