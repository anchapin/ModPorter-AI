"""
Comprehensive tests for knowledge_graph.py API module
This test file targets increasing code coverage for the knowledge graph functionality.
"""

import pytest
import sys
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock the magic library before importing modules that use it
sys.modules['magic'] = Mock()
sys.modules['magic'].open = Mock(return_value=Mock())
sys.modules['magic'].from_buffer = Mock(return_value='application/octet-stream')
sys.modules['magic'].from_file = Mock(return_value='data')

# Import the module we're testing
from api.knowledge_graph_fixed import router, get_knowledge_nodes, create_knowledge_node, update_knowledge_node
from api.knowledge_graph_fixed import get_node_relationships, create_knowledge_relationship
from api.knowledge_graph_fixed import get_knowledge_node
from db.models import KnowledgeNode, KnowledgeRelationship


@pytest.fixture
def mock_db():
    """Create a mock database session"""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def mock_node_data():
    """Mock knowledge node data"""
    return {
        "id": "test-node-1",
        "type": "concept",
        "title": "Test Concept",
        "description": "A test concept for knowledge graph",
        "metadata": {"source": "test", "confidence": 0.9}
    }


@pytest.fixture
def mock_relationship_data():
    """Mock knowledge relationship data"""
    return {
        "id": "test-rel-1",
        "source_node_id": "test-node-1",
        "target_node_id": "test-node-2",
        "relationship_type": "relates_to",
        "weight": 0.8,
        "metadata": {"source": "test"}
    }


@pytest.fixture
def mock_knowledge_node():
    """Create a mock KnowledgeNode instance"""
    node = MagicMock(spec=KnowledgeNode)
    node.id = "test-node-1"
    node.type = "concept"
    node.title = "Test Concept"
    node.description = "A test concept"
    node.metadata = {"source": "test", "confidence": 0.9}
    node.created_at = "2024-01-01T00:00:00"
    node.updated_at = "2024-01-01T00:00:00"
    return node


@pytest.fixture
def mock_knowledge_relationship():
    """Create a mock KnowledgeRelationship instance"""
    rel = MagicMock(spec=KnowledgeRelationship)
    rel.id = "test-rel-1"
    rel.source_node_id = "test-node-1"
    rel.target_node_id = "test-node-2"
    rel.relationship_type = "relates_to"
    rel.weight = 0.8
    rel.metadata = {"source": "test"}
    rel.created_at = "2024-01-01T00:00:00"
    rel.updated_at = "2024-01-01T00:00:00"
    return rel


class TestKnowledgeNodeAPI:
    """Test knowledge node API endpoints"""

    async def test_get_knowledge_nodes_success(self, mock_db):
        """Test successful retrieval of knowledge nodes"""
        # Act
        result = await get_knowledge_nodes(mock_db)

        # Assert
        # The function returns a list directly, not a dict with status
        assert isinstance(result, list)
        assert len(result) == 0  # Mock implementation returns empty list

    async def test_get_knowledge_nodes_with_filters(self, mock_db):
        """Test retrieval of knowledge nodes with filters"""
        # Act
        result = await get_knowledge_nodes(mock_db, node_type="feature", limit=10)

        # Assert
        # The function returns a list directly, not a dict with status
        assert isinstance(result, list)
        assert len(result) == 0  # Mock implementation returns empty list

    async def test_create_knowledge_node_success(self, mock_db, mock_node_data):
        """Test successful creation of a knowledge node"""
        # Act
        result = await create_knowledge_node(mock_node_data, mock_db)

        # Assert
        # The actual implementation returns a dict with id, node_type, etc.
        assert "id" in result
        assert "node_type" in result
        assert "properties" in result
        assert result["node_type"] == mock_node_data["node_type"]
        assert result["properties"] == mock_node_data.get("properties", {})

    async def test_create_knowledge_node_error(self, mock_db, mock_node_data):
        """Test error handling when creating a knowledge node"""
        # Arrange
        invalid_node_data = {
            "node_type": "invalid_type",
            "name": "Test Node"
        }

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_knowledge_node(invalid_node_data, mock_db)

        assert exc_info.value.status_code == 422
        assert "Invalid node_type" in str(exc_info.value.detail)

    @patch('api.knowledge_graph_fixed.KnowledgeNodeCRUD.get_by_id')
    @patch('api.knowledge_graph_fixed.KnowledgeNodeCRUD.update')
    async def test_update_knowledge_node_success(self, mock_update_node, mock_get_node, mock_db, mock_node_data):
        """Test successful update of a knowledge node"""
        # Arrange
        mock_node = MagicMock(spec=KnowledgeNode)
        mock_node.id = "test-node-1"
        mock_node.node_type = "java_class"
        mock_node.name = "Updated Title"
        mock_node.description = "Updated description"
        mock_node.properties = {"field": "value"}
        mock_node.minecraft_version = "1.19.2"
        mock_node.platform = "java"
        mock_node.expert_validated = True
        mock_node.community_rating = 4.5
        mock_node.updated_at = MagicMock()
        mock_node.updated_at.isoformat.return_value = "2025-01-01T00:00:00Z"

        mock_get_node.return_value = mock_node
        mock_update_node.return_value = mock_node

        # Act
        result = await update_knowledge_node("test-node-1", mock_node_data, mock_db)

        # Assert
        assert result["status"] == "success"
        assert result["node_id"] == "test-node-1"
        assert result["node_type"] == "java_class"
        assert result["name"] == "Updated Title"
        assert result["message"] == "Knowledge node updated successfully"
        mock_get_node.assert_called_once_with(mock_db, "test-node-1")
        mock_update_node.assert_called_once_with(mock_db, "test-node-1", mock_node_data)

    @patch('api.knowledge_graph_fixed.KnowledgeNodeCRUD.get_by_id')
    async def test_update_knowledge_node_not_found(self, mock_get_node, mock_db, mock_node_data):
        """Test update when knowledge node is not found"""
        # Arrange
        mock_get_node.return_value = None

        # Act
        result = await update_knowledge_node("nonexistent-node", mock_node_data, mock_db)

        # Assert
        assert result["status"] == "error"
        assert result["message"] == "Knowledge node not found"
        assert result["node_id"] == "nonexistent-node"
        mock_get_node.assert_called_once_with(mock_db, "nonexistent-node")


class TestKnowledgeRelationshipAPI:
    """Test knowledge relationship API endpoints"""

    @patch('api.knowledge_graph.get_all_knowledge_relationships')
    async def test_get_knowledge_relationships_success(self, mock_get_rels, mock_db):
        """Test successful retrieval of knowledge relationships"""
        # Arrange
        mock_rel = MagicMock(spec=KnowledgeRelationship)
        mock_rel.id = "rel-1"
        mock_rel.source_node_id = "node-1"
        mock_rel.target_node_id = "node-2"
        mock_rel.relationship_type = "relates_to"
        mock_get_rels.return_value = [mock_rel]

        # Act
        result = await get_knowledge_relationships(mock_db)

        # Assert
        assert result["status"] == "success"
        assert len(result["data"]) == 1
        assert result["data"][0]["id"] == "rel-1"
        assert result["data"][0]["source_node_id"] == "node-1"
        assert result["data"][0]["target_node_id"] == "node-2"
        mock_get_rels.assert_called_once_with(mock_db)

    @patch('api.knowledge_graph.create_knowledge_relationship_crud')
    async def test_create_knowledge_relationship_success(self, mock_create_rel, mock_db, mock_relationship_data):
        """Test successful creation of a knowledge relationship"""
        # Arrange
        mock_rel = MagicMock(spec=KnowledgeRelationship)
        mock_rel.id = "new-rel-id"
        mock_rel.source_node_id = "node-1"
        mock_rel.target_node_id = "node-2"
        mock_create_rel.return_value = mock_rel

        # Act
        result = await create_knowledge_relationship(mock_relationship_data, mock_db)

        # Assert
        assert result["status"] == "success"
        assert result["data"]["id"] == "new-rel-id"
        assert result["data"]["source_node_id"] == "node-1"
        assert result["data"]["target_node_id"] == "node-2"
        assert result["message"] == "Knowledge relationship created successfully"
        mock_create_rel.assert_called_once_with(mock_relationship_data, mock_db)


class TestKnowledgeGraphSearch:
    """Test knowledge graph search functionality"""

    @patch('api.knowledge_graph.search_knowledge_graph_nodes')
    async def test_search_knowledge_graph_success(self, mock_search, mock_db):
        """Test successful search of the knowledge graph"""
        # Arrange
        mock_node = MagicMock(spec=KnowledgeNode)
        mock_node.id = "node-1"
        mock_node.title = "Java Edition"
        mock_search.return_value = [mock_node]

        # Act
        result = await search_knowledge_graph(query="Java", limit=10, db=mock_db)

        # Assert
        assert result["status"] == "success"
        assert len(result["data"]) == 1
        assert result["data"][0]["id"] == "node-1"
        assert result["query"] == "Java"
        mock_search.assert_called_once_with("Java", mock_db, limit=10)

    @patch('api.knowledge_graph.search_knowledge_graph_nodes')
    async def test_search_knowledge_graph_empty_result(self, mock_search, mock_db):
        """Test search with no results"""
        # Arrange
        mock_search.return_value = []

        # Act
        result = await search_knowledge_graph(query="Nonexistent", limit=10, db=mock_db)

        # Assert
        assert result["status"] == "success"
        assert len(result["data"]) == 0
        assert result["query"] == "Nonexistent"


class TestKnowledgeGraphAnalytics:
    """Test knowledge graph analytics endpoints"""

    @patch('api.knowledge_graph.get_graph_statistics')
    async def test_get_graph_statistics_success(self, mock_stats, mock_db):
        """Test successful retrieval of graph statistics"""
        # Arrange
        mock_stats.return_value = {
            "total_nodes": 150,
            "total_relationships": 300,
            "node_types": {"concept": 50, "feature": 70, "entity": 30},
            "relationship_types": {"relates_to": 150, "contains": 100, "similar_to": 50}
        }

        # Act
        result = await get_graph_statistics(mock_db)

        # Assert
        assert result["status"] == "success"
        assert result["data"]["total_nodes"] == 150
        assert result["data"]["total_relationships"] == 300
        assert result["data"]["node_types"]["concept"] == 50
        mock_stats.assert_called_once_with(mock_db)

    @patch('api.knowledge_graph_fixed.KnowledgeNodeCRUD.get_by_id')
    async def test_get_node_by_id_success(self, mock_get_node, mock_db, mock_knowledge_node):
        """Test successful retrieval of a node by ID"""
        # Arrange
        mock_get_node.return_value = mock_knowledge_node

        # Act
        result = await get_node_by_id("test-node-1", mock_db)

        # Assert
        assert result["status"] == "success"
        assert result["data"]["id"] == "test-node-1"
        assert result["data"]["title"] == "Test Concept"
        mock_get_node.assert_called_once_with(mock_db, "test-node-1")

    @patch('api.knowledge_graph.get_knowledge_relationship_by_id')
    async def test_get_relationship_by_id_success(self, mock_get_rel, mock_db, mock_knowledge_relationship):
        """Test successful retrieval of a relationship by ID"""
        # Arrange
        mock_get_rel.return_value = mock_knowledge_relationship

        # Act
        result = await get_relationship_by_id("test-rel-1", mock_db)

        # Assert
        assert result["status"] == "success"
        assert result["data"]["id"] == "test-rel-1"
        assert result["data"]["source_node_id"] == "test-node-1"
        assert result["data"]["target_node_id"] == "test-node-2"
        mock_get_rel.assert_called_once_with("test-rel-1", mock_db)

    @patch('api.knowledge_graph.get_neighbors')
    async def test_get_neighbors_success(self, mock_get_neighbors, mock_db, mock_knowledge_node):
        """Test successful retrieval of node neighbors"""
        # Arrange
        neighbor = MagicMock(spec=KnowledgeNode)
        neighbor.id = "neighbor-1"
        neighbor.title = "Neighbor Node"
        mock_get_node = MagicMock()
        mock_get_node.return_value = mock_knowledge_node
        mock_get_neighbors.return_value = {
            "node": mock_knowledge_node,
            "neighbors": [neighbor],
            "relationships": [
                {"id": "rel-1", "type": "relates_to", "weight": 0.8}
            ]
        }

        # Act
        result = await get_neighbors("test-node-1", max_depth=1, db=mock_db)

        # Assert
        assert result["status"] == "success"
        assert len(result["data"]["neighbors"]) == 1
        assert result["data"]["neighbors"][0]["id"] == "neighbor-1"
        mock_get_neighbors.assert_called_once_with("test-node-1", mock_db, max_depth=1)


class TestGraphAlgorithms:
    """Test graph algorithm endpoints"""

    @patch('api.knowledge_graph.calculate_shortest_path')
    async def test_get_shortest_path_success(self, mock_path, mock_db):
        """Test successful calculation of shortest path"""
        # Arrange
        node = MagicMock(spec=KnowledgeNode)
        node.id = "node-1"
        node.title = "Node 1"
        mock_path.return_value = {
            "path": [node],
            "length": 1,
            "path_found": True
        }

        # Act
        result = await get_shortest_path("node-1", "node-2", db=mock_db)

        # Assert
        assert result["status"] == "success"
        assert result["data"]["path_found"] is True
        assert len(result["data"]["path"]) == 1
        mock_path.assert_called_once_with("node-1", "node-2", mock_db)

    @patch('api.knowledge_graph.calculate_shortest_path')
    async def test_get_shortest_path_not_found(self, mock_path, mock_db):
        """Test shortest path when no path exists"""
        # Arrange
        mock_path.return_value = {
            "path": [],
            "length": float('inf'),
            "path_found": False
        }

        # Act
        result = await get_shortest_path("node-1", "node-99", db=mock_db)

        # Assert
        assert result["status"] == "success"
        assert result["data"]["path_found"] is False
        assert len(result["data"]["path"]) == 0

    @patch('api.knowledge_graph.identify_central_nodes')
    async def test_get_central_nodes_success(self, mock_central, mock_db):
        """Test successful identification of central nodes"""
        # Arrange
        node = MagicMock(spec=KnowledgeNode)
        node.id = "central-node"
        node.title = "Central Node"
        mock_central.return_value = [
            {"node": node, "centrality_score": 0.9}
        ]

        # Act
        result = await get_central_nodes(algorithm="betweenness", limit=10, db=mock_db)

        # Assert
        assert result["status"] == "success"
        assert len(result["data"]) == 1
        assert result["data"][0]["node"]["id"] == "central-node"
        assert result["data"][0]["centrality_score"] == 0.9
        mock_central.assert_called_once_with("betweenness", mock_db, limit=10)

    @patch('api.knowledge_graph.detect_graph_clusters')
    async def test_get_graph_clusters_success(self, mock_clusters, mock_db):
        """Test successful detection of graph clusters"""
        # Arrange
        node = MagicMock(spec=KnowledgeNode)
        node.id = "cluster-node"
        node.title = "Cluster Node"
        mock_clusters.return_value = [
            {
                "id": "cluster-1",
                "nodes": [node],
                "density": 0.8,
                "modularity": 0.7
            }
        ]

        # Act
        result = await get_graph_clusters(algorithm="louvain", db=mock_db)

        # Assert
        assert result["status"] == "success"
        assert len(result["data"]) == 1
        assert result["data"][0]["id"] == "cluster-1"
        assert len(result["data"][0]["nodes"]) == 1
        mock_clusters.assert_called_once_with("louvain", mock_db)


class TestErrorHandling:
    """Test error handling in knowledge graph API"""

    async def test_invalid_node_type_filter(self, mock_db):
        """Test error handling with invalid node type filter"""
        # Act
        result = await get_knowledge_nodes(mock_db, node_type="invalid_type")

        # Assert - should handle gracefully and return success with empty data
        assert result["status"] == "success"
        assert len(result["data"]) == 0

    async def test_empty_relationship_data(self, mock_db):
        """Test error handling with empty relationship data"""
        # Arrange
        empty_data = {}

        # Act
        with pytest.raises(KeyError):
            await create_knowledge_relationship(empty_data, mock_db)

    async def test_invalid_query_string(self, mock_db):
        """Test search with invalid query string"""
        # Act
        result = await search_knowledge_graph(query="", limit=10, db=mock_db)

        # Assert
        assert result["status"] == "success"
        assert len(result["data"]) == 0
        assert result["query"] == ""
