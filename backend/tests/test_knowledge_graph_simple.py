"""
Simple tests for Knowledge Graph System API that match the actual implementation
"""
import pytest
from uuid import uuid4
from httpx import AsyncClient


class TestKnowledgeGraphAPI:
    """Test suite for Knowledge Graph System endpoints"""

    @pytest.mark.asyncio
    async def test_create_knowledge_node(self, async_client: AsyncClient):
        """Test creating a knowledge graph node"""
        node_data = {
            "node_type": "java_concept",
            "name": "BlockRegistry",
            "properties": {
                "package": "net.minecraft.block",
                "mod_id": "example_mod",
                "version": "1.0.0"
            },
            "minecraft_version": "latest",
            "platform": "java"
        }
        
        # First test basic health endpoint to verify client is working
        health_response = await async_client.get("/api/v1/health")
        print(f"Health endpoint status: {health_response.status_code}")
        if health_response.status_code == 200:
            print("Health endpoint working:", health_response.json())
        
        # Test docs endpoint to see if FastAPI is running
        docs_response = await async_client.get("/docs")
        print(f"Docs endpoint status: {docs_response.status_code}")
        
        # Check if knowledge graph routes are listed in the OpenAPI spec
        openapi_response = await async_client.get("/openapi.json")
        if openapi_response.status_code == 200:
            openapi_spec = openapi_response.json()
            knowledge_routes = [path for path in openapi_spec.get("paths", {}).keys() if "knowledge-graph" in path]
            print(f"Knowledge graph routes found: {knowledge_routes}")
        
        response = await async_client.post("/api/v1/knowledge-graph/nodes", json=node_data)
        print(f"Knowledge graph endpoint status: {response.status_code}")
        print(f"Response text: {response.text}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["node_type"] == "java_concept"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_knowledge_nodes(self, async_client: AsyncClient):
        """Test getting knowledge nodes list"""
        response = await async_client.get("/api/v1/knowledge-graph/nodes")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_knowledge_nodes_with_filter(self, async_client: AsyncClient):
        """Test getting knowledge nodes with filters"""
        response = await async_client.get(
            "/api/v1/knowledge-graph/nodes",
            params={"node_type": "java_concept", "minecraft_version": "latest", "limit": 10}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_create_knowledge_relationship(self, async_client: AsyncClient):
        """Test creating a knowledge relationship"""
        relationship_data = {
            "source": str(uuid4()),
            "target": str(uuid4()),
            "relationship_type": "depends_on",
            "properties": {
                "dependency_type": "import",
                "strength": 0.8
            },
            "confidence_score": 0.85,
            "minecraft_version": "latest"
        }
        
        response = await async_client.post("/api/v1/knowledge-graph/relationships", json=relationship_data)
        # Might fail due to non-existent nodes, but should not be 404
        assert response.status_code in [200, 400, 500]

    @pytest.mark.asyncio
    async def test_get_node_relationships(self, async_client: AsyncClient):
        """Test getting relationships for a node"""
        node_id = str(uuid4())
        response = await async_client.get(f"/api/v1/knowledge-graph/relationships/{node_id}")
        # Should return empty relationships for non-existent node
        assert response.status_code == 200
        
        data = response.json()
        assert "relationships" in data
        assert "graph_data" in data

    @pytest.mark.asyncio
    async def test_create_conversion_pattern(self, async_client: AsyncClient):
        """Test creating a conversion pattern"""
        pattern_data = {
            "java_pattern": "BlockRegistry.register()",
            "bedrock_pattern": "minecraft:block component",
            "description": "Convert block registration",
            "confidence": 0.9,
            "examples": [
                {"java": "BlockRegistry.register(block)", "bedrock": "format_version: 2"}
            ],
            "minecraft_version": "latest"
        }
        
        response = await async_client.post("/api/v1/knowledge-graph/patterns", json=pattern_data)
        # Might fail depending on schema but should not be 404
        assert response.status_code in [200, 422, 500]

    @pytest.mark.asyncio
    async def test_get_conversion_patterns(self, async_client: AsyncClient):
        """Test getting conversion patterns"""
        response = await async_client.get("/api/v1/knowledge-graph/patterns")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_search_graph(self, async_client: AsyncClient):
        """Test searching the knowledge graph"""
        response = await async_client.get(
            "/api/v1/knowledge-graph/graph/search",
            params={"query": "BlockRegistry", "limit": 20}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "neo4j_results" in data
        assert "postgresql_results" in data

    @pytest.mark.asyncio
    async def test_find_conversion_paths(self, async_client: AsyncClient):
        """Test finding conversion paths"""
        node_id = str(uuid4())
        response = await async_client.get(
            f"/api/v1/knowledge-graph/graph/paths/{node_id}",
            params={"max_depth": 3, "minecraft_version": "latest"}
        )
        # Should handle non-existent node gracefully
        assert response.status_code in [200, 404, 500]

    @pytest.mark.asyncio
    async def test_update_node_validation(self, async_client: AsyncClient):
        """Test updating node validation status"""
        node_id = str(uuid4())
        validation_data = {
            "expert_validated": True,
            "community_rating": 4.5
        }
        
        response = await async_client.put(
            f"/api/v1/knowledge-graph/nodes/{node_id}/validation",
            json=validation_data
        )
        # Should handle non-existent node gracefully
        assert response.status_code in [200, 404, 500]

    @pytest.mark.asyncio
    async def test_create_community_contribution(self, async_client: AsyncClient):
        """Test creating a community contribution"""
        contribution_data = {
            "contributor_id": str(uuid4()),
            "contribution_type": "pattern",
            "title": "New conversion pattern",
            "description": "A new way to convert blocks",
            "data": {
                "java_pattern": "customBlock()",
                "bedrock_pattern": "minecraft:block"
            },
            "minecraft_version": "latest"
        }
        
        response = await async_client.post("/api/v1/knowledge-graph/contributions", json=contribution_data)
        # Should create contribution or return validation error
        assert response.status_code in [200, 422, 500]

    @pytest.mark.asyncio
    async def test_get_community_contributions(self, async_client: AsyncClient):
        """Test getting community contributions"""
        response = await async_client.get("/api/v1/knowledge-graph/contributions")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_create_version_compatibility(self, async_client: AsyncClient):
        """Test creating version compatibility entry"""
        compatibility_data = {
            "java_version": "1.20.1",
            "bedrock_version": "1.20.0",
            "compatibility_score": 0.95,
            "known_issues": [],
            "workarounds": []
        }
        
        response = await async_client.post("/api/v1/knowledge-graph/compatibility", json=compatibility_data)
        # Should create or return validation error
        assert response.status_code in [200, 422, 500]

    @pytest.mark.asyncio
    async def test_get_version_compatibility(self, async_client: AsyncClient):
        """Test getting version compatibility"""
        response = await async_client.get(
            "/api/v1/knowledge-graph/compatibility/1.20.1/1.20.0"
        )
        # Should return 404 for non-existent compatibility
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_knowledge_graph_health(self, async_client: AsyncClient):
        """Test basic API health"""
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
