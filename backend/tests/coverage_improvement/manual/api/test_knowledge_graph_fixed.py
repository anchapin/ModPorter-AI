"""
Fixed tests for knowledge_graph API that properly test the actual implementation
This file replaces the problematic test with proper tests that match API behavior
"""

import pytest
import sys
import os
from unittest.mock import Mock
from fastapi.testclient import TestClient

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

# Mock magic library before importing modules that use it
sys.modules["magic"] = Mock()
sys.modules["magic"].open = Mock(return_value=Mock())
sys.modules["magic"].from_buffer = Mock(return_value="application/octet-stream")
sys.modules["magic"].from_file = Mock(return_value="data")

# Mock other dependencies
sys.modules["neo4j"] = Mock()
sys.modules["crewai"] = Mock()
sys.modules["langchain"] = Mock()
sys.modules["javalang"] = Mock()

# Import module to test
from src.api.knowledge_graph import router


class TestKnowledgeGraphAPIFixed:
    """Test class for knowledge graph API endpoints with proper implementation"""

    @pytest.fixture
    def client(self):
        """Create test client for FastAPI router"""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        return TestClient(app)

    def test_router_import(self):
        """Test that the router can be imported successfully"""
        assert router is not None
        assert hasattr(router, "routes")

    def test_health_check(self, client):
        """Test the health check endpoint"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["api"] == "knowledge_graph"

    def test_create_knowledge_node_valid(self, client):
        """Test creating a knowledge node with valid data"""
        node_data = {
            "name": "Test Node",
            "node_type": "java_class",
            "properties": {"test": "value"},
            "platform": "java",
        }

        response = client.post("/api/v1/nodes", json=node_data)

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Node"
        assert data["node_type"] == "java_class"
        assert data["platform"] == "java"
        assert data["properties"] == {"test": "value"}
        assert data["expert_validated"] is False
        assert data["community_rating"] == 0.0

    def test_create_knowledge_node_invalid_type(self, client):
        """Test creating a knowledge node with invalid node_type"""
        node_data = {
            "name": "Test Node",
            "node_type": "invalid_type",
            "platform": "java",
        }

        response = client.post("/api/v1/nodes", json=node_data)
        assert response.status_code == 422

    def test_create_knowledge_node_invalid_properties(self, client):
        """Test creating a knowledge node with invalid properties"""
        node_data = {
            "name": "Test Node",
            "node_type": "java_class",
            "properties": "not_a_dict",
            "platform": "java",
        }

        response = client.post("/api/v1/nodes", json=node_data)
        assert response.status_code == 422

    def test_get_knowledge_node_existing(self, client):
        """Test getting an existing knowledge node"""
        # First create a node
        node_data = {
            "name": "Test Node for Get",
            "node_type": "java_class",
            "platform": "java",
        }
        create_response = client.post("/api/v1/nodes", json=node_data)
        created_node = create_response.json()
        node_id = created_node["id"]

        # Get the node
        response = client.get(f"/api/v1/nodes/{node_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == node_id
        assert data["name"] == "Test Node for Get"

    def test_get_knowledge_node_nonexistent(self, client):
        """Test getting a non-existent knowledge node"""
        response = client.get("/api/v1/nodes/non-existent-id")
        assert response.status_code == 404

    def test_get_knowledge_nodes_list(self, client):
        """Test getting knowledge nodes list"""
        response = client.get("/api/v1/nodes")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Test with parameters
        response = client.get("/api/v1/nodes?node_type=java_class&limit=10")
        assert response.status_code == 200

        response = client.get(
            "/api/v1/nodes?search=test&minecraft_version=1.19.0&limit=5"
        )
        assert response.status_code == 200

    def test_create_knowledge_relationship_valid(self, client):
        """Test creating a knowledge relationship with valid data"""
        # First create two nodes
        node1_data = {"name": "Node 1", "node_type": "java_class", "platform": "java"}
        node2_data = {
            "name": "Node 2",
            "node_type": "minecraft_block",
            "platform": "bedrock",
        }

        node1_response = client.post("/api/v1/nodes", json=node1_data)
        node2_response = client.post("/api/v1/nodes", json=node2_data)

        node1_id = node1_response.json()["id"]
        node2_id = node2_response.json()["id"]

        # Create relationship
        relationship_data = {
            "source_id": node1_id,
            "target_id": node2_id,
            "relationship_type": "related_to",
            "properties": {"strength": 0.8},
        }

        response = client.post("/api/v1/relationships", json=relationship_data)
        assert response.status_code == 200

    def test_create_knowledge_relationship_invalid(self, client):
        """Test creating a knowledge relationship with invalid data"""
        # Missing required fields
        relationship_data = {"relationship_type": "related_to"}

        response = client.post("/api/v1/relationships", json=relationship_data)
        assert response.status_code == 422

    def test_get_relationships(self, client):
        """Test getting relationships"""
        response = client.get("/api/v1/relationships")
        assert response.status_code == 200
        data = response.json()
        assert "relationships" in data
        assert "graph_data" in data

        response = client.get("/api/v1/relationships/specific-node")
        assert response.status_code == 200

        response = client.get(
            "/api/v1/relationships/specific-node?relationship_type=related_to"
        )
        assert response.status_code == 200

    def test_get_relationships_alt_endpoint(self, client):
        """Test getting relationships using /edges endpoint"""
        response = client.get("/api/v1/edges")
        assert response.status_code == 200

        response = client.get("/api/v1/edges/specific-node")
        assert response.status_code == 200

    def test_create_pattern(self, client):
        """Test creating a conversion pattern"""
        pattern_data = {
            "name": "Test Pattern",
            "java_pattern": "test_java_pattern",
            "bedrock_pattern": "test_bedrock_pattern",
            "success_rate": 0.85,
            "usage_count": 10,
            "validation_status": "validated",
        }

        response = client.post("/api/v1/patterns", json=pattern_data)
        assert response.status_code == 200

    def test_get_patterns(self, client):
        """Test getting conversion patterns"""
        response = client.get("/api/v1/patterns")
        assert response.status_code == 200

        response = client.get("/api/v1/patterns/?validation_status=validated&limit=10")
        assert response.status_code == 200

    def test_create_community_contribution(self, client):
        """Test creating a community contribution"""
        contribution_data = {
            "contributor_id": "test-contributor",
            "title": "Test Contribution",
            "content": "Test contribution content",
            "contribution_type": "pattern",
            "related_nodes": ["node1", "node2"],
        }

        response = client.post("/api/v1/contributions", json=contribution_data)
        assert response.status_code == 200

    def test_get_community_contributions(self, client):
        """Test getting community contributions"""
        response = client.get("/api/v1/contributions")
        assert response.status_code == 200

        response = client.get(
            "/api/v1/contributions/?contributor_id=test-contributor&review_status=pending"
        )
        assert response.status_code == 200

    def test_create_version_compatibility(self, client):
        """Test creating version compatibility entry"""
        compatibility_data = {
            "java_version": "1.19.0",
            "bedrock_version": "1.19.80",
            "compatibility_score": 0.95,
            "features_supported": ["feature1", "feature2"],
            "limitations": ["limitation1"],
            "migration_guide": "Test migration guide",
        }

        response = client.post("/api/v1/compatibility", json=compatibility_data)
        assert response.status_code == 200

    def test_get_version_compatibility(self, client):
        """Test getting version compatibility"""
        response = client.get("/api/v1/compatibility/")
        assert response.status_code == 200

        response = client.get("/api/v1/compatibility/1.19.0/1.19.80")
        assert response.status_code == 200

    def test_search_knowledge_graph(self, client):
        """Test searching knowledge graph"""
        response = client.get("/api/v1/graph/search?query=test&limit=10")
        assert response.status_code == 200

    def test_get_conversion_paths(self, client):
        """Test getting conversion paths"""
        response = client.get("/api/v1/graph/paths/test-node-id")
        assert response.status_code == 200

    def test_get_node_neighbors(self, client):
        """Test getting node neighbors"""
        response = client.get("/api/v1/nodes/test-node/neighbors")
        assert response.status_code == 200

    def test_search_endpoint(self, client):
        """Test the search endpoint"""
        response = client.get("/api/v1/search/?q=test&limit=20")
        assert response.status_code == 200

    def test_get_statistics(self, client):
        """Test getting statistics"""
        response = client.get("/api/v1/statistics/")
        assert response.status_code == 200

    def test_get_conversion_path(self, client):
        """Test getting specific conversion path"""
        response = client.get("/api/v1/path/source-id/target-id")
        assert response.status_code == 200

    def test_get_subgraph(self, client):
        """Test getting subgraph"""
        response = client.get("/api/v1/subgraph/test-node")
        assert response.status_code == 200

    def test_visualization(self, client):
        """Test getting visualization data"""
        response = client.get("/api/v1/visualization/")
        assert response.status_code == 200

    def test_insights(self, client):
        """Test getting insights"""
        response = client.get("/api/v1/insights/")
        assert response.status_code == 200

    def test_edge_cases(self, client):
        """Test edge cases and error conditions"""
        # Test with invalid JSON
        response = client.post("/api/v1/nodes", data="invalid json")
        assert response.status_code == 422

        # Test with missing required fields
        response = client.post("/api/v1/nodes", json={"name": "test"})
        assert response.status_code == 422

        # Test with very long strings
        long_string = "x" * 10000
        response = client.post(
            "/api/v1/nodes",
            json={"name": long_string, "node_type": "java_class", "platform": "java"},
        )
        assert response.status_code in [200, 422]  # May work or fail validation
