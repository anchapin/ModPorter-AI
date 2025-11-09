"""
Comprehensive tests for Expert Knowledge Capture System API
"""
import pytest
import json
from uuid import uuid4
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestExpertKnowledgeAPI:
    """Test suite for Expert Knowledge Capture System endpoints"""

    @pytest.mark.asyncio
    async def test_capture_expert_contribution(self, async_client: AsyncClient):
        """Test capturing expert knowledge contribution"""
        contribution_data = {
            "content": """
            package com.example.mod;
            
            import net.minecraft.block.Block;
            import net.minecraft.block.material.Material;
            
            public class CustomBlock extends Block {
                public static final String NAME = "custom_block";
                
                public CustomBlock() {
                    super(Material.ROCK);
                    setHardness(2.0f);
                    setResistance(10.0f);
                }
            }
            """,
            "content_type": "code",
            "contributor_id": str(uuid4()),
            "title": "Custom Block Implementation",
            "description": "Efficient way to create custom blocks in Forge mods",
            "minecraft_version": "1.19.2"
        }
        
        response = await async_client.post("/api/v1/expert-knowledge/capture-contribution", json=contribution_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "contribution_id" in data
        assert "nodes_created" in data
        assert "relationships_created" in data
        assert "patterns_created" in data
        assert "quality_score" in data
        assert "validation_comments" in data

    @pytest.mark.asyncio
    async def test_validate_knowledge_quality(self, async_client: AsyncClient):
        """Test knowledge validation"""
        validation_data = {
            "knowledge_data": {
                "type": "java_class",
                "name": "CustomBlock",
                "properties": {
                    "extends": "Block",
                    "material": "ROCK",
                    "hardness": 2.0
                }
            },
            "validation_rules": ["extends_block", "material_exists", "hardness_range"],
            "domain": "minecraft"
        }
        
        response = await async_client.post("/api/v1/expert-knowledge/validate-knowledge", json=validation_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        assert "validation_results" in data
        assert "confidence_score" in data
        assert "suggestions" in data

    @pytest.mark.asyncio
    async def test_batch_capture_contributions(self, async_client: AsyncClient):
        """Test batch processing of contributions"""
        batch_data = {
            "contributions": [
                {
                    "content": f"Batch contribution {i}",
                    "content_type": "text",
                    "contributor_id": str(uuid4()),
                    "title": f"Batch Contribution {i}",
                    "description": f"Description for batch {i}",
                    "minecraft_version": "1.19.2"
                }
                for i in range(3)
            ],
            "parallel_processing": True
        }
        
        response = await async_client.post("/api/v1/expert-knowledge/batch-capture", json=batch_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "total_processed" in data
        assert "successful" in data
        assert "failed" in data
        assert "results" in data

    @pytest.mark.asyncio
    async def test_get_domain_summary(self, async_client: AsyncClient):
        """Test getting domain knowledge summary"""
        response = await async_client.get("/api/v1/expert-knowledge/domain-summary/entities")
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        assert data["success"] is True
        assert "domain" in data
        assert "summary" in data

    @pytest.mark.asyncio
    async def test_get_expert_recommendations(self, async_client: AsyncClient):
        """Test getting expert recommendations"""
        context_data = {
            "context": "creating_custom_block",
            "contribution_type": "pattern"
        }
        
        response = await async_client.post("/api/v1/expert-knowledge/get-recommendations", json=context_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        assert "recommendations" in data
        assert "best_practices" in data

    @pytest.mark.asyncio
    async def test_get_available_domains(self, async_client: AsyncClient):
        """Test getting available knowledge domains"""
        response = await async_client.get("/api/v1/expert-knowledge/available-domains")
        assert response.status_code == 200
        
        data = response.json()
        assert "domains" in data
        assert "total_domains" in data
        assert len(data["domains"]) > 0
        
        # Check domain structure
        domain = data["domains"][0]
        assert "domain" in domain
        assert "description" in domain
        assert "knowledge_count" in domain
        assert "last_updated" in domain

    @pytest.mark.asyncio
    async def test_get_capture_statistics(self, async_client: AsyncClient):
        """Test getting capture statistics"""
        response = await async_client.get("/api/v1/expert-knowledge/capture-stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "period_days" in data
        assert "contributions_processed" in data
        assert "success_rate" in data
        assert "average_quality_score" in data
        assert "total_nodes_created" in data
        assert "total_relationships_created" in data
        assert "total_patterns_created" in data

    @pytest.mark.asyncio
    async def test_health_check(self, async_client: AsyncClient):
        """Test health check endpoint"""
        # Test main health endpoint first
        response = await async_client.get("/api/v1/health")
        print(f"Main health status: {response.status_code}")
        if response.status_code == 200:
            print(f"Main health response: {response.text}")
        
        assert response.status_code == 200
        
        # Now test expert-knowledge health endpoint
        response = await async_client.get("/api/v1/expert-knowledge/health")
        print(f"Expert health status: {response.status_code}")
        if response.status_code == 200:
            print(f"Expert health response: {response.text}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "components" in data
        assert "timestamp" in data
        
        # Check components structure
        components = data["components"]
        assert "ai_engine" in components
        assert "database" in components
        assert "system" in components

    @pytest.mark.asyncio
    async def test_capture_contribution_file(self, async_client: AsyncClient):
        """Test capturing expert knowledge from uploaded file"""
        import io
        
        # Create a mock file
        file_content = """
        // Example Java code for file upload test
        package com.example.mod;
        
        import net.minecraft.item.Item;
        
        public class CustomItem extends Item {
            public static final String NAME = "custom_item";
            
            public CustomItem() {
                super(new Item.Properties());
            }
        }
        """
        
        files = {
            "file": ("CustomItem.java", io.BytesIO(file_content.encode()), "text/plain")
        }
        
        data = {
            "content_type": "code",
            "contributor_id": str(uuid4()),
            "title": "Custom Item Example",
            "description": "Example of custom item implementation"
        }
        
        response = await async_client.post(
            "/api/v1/expert-knowledge/capture-contribution-file",
            files=files,
            data=data
        )
        
        assert response.status_code == 200
        
        result = response.json()
        assert "contribution_id" in result
        assert "filename" in result
        assert "nodes_created" in result
        assert "relationships_created" in result

    @pytest.mark.asyncio
    async def test_invalid_contribution_data(self, async_client: AsyncClient):
        """Test validation of invalid contribution data"""
        invalid_data = {
            "content": "",  # Empty content
            "content_type": "invalid_type",
            "contributor_id": "",  # Empty contributor ID
            "title": "",  # Empty title
            "description": ""  # Empty description
        }
        
        response = await async_client.post("/api/v1/expert-knowledge/capture-contribution", json=invalid_data)
        # Should return 422 for validation errors or 400 for processing errors
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_knowledge_quality_workflow(self, async_client: AsyncClient):
        """Test end-to-end knowledge quality workflow"""
        # Step 1: Submit a contribution
        contribution_data = {
            "content": """
            package com.example.mod;
            
            import net.minecraft.entity.EntityType;
            import net.minecraft.entity.MobEntity;
            import net.minecraft.world.World;
            
            public class CustomEntity extends MobEntity {
                public CustomEntity(EntityType<? extends CustomEntity> type, World world) {
                    super(type, world);
                }
            }
            """,
            "content_type": "code",
            "contributor_id": str(uuid4()),
            "title": "Custom Entity Implementation",
            "description": "Best practices for creating custom entities",
            "minecraft_version": "1.19.2"
        }
        
        create_response = await async_client.post("/api/v1/expert-knowledge/capture-contribution", json=contribution_data)
        assert create_response.status_code == 200
        
        create_data = create_response.json()
        assert create_data["quality_score"] is not None
        
        # Step 2: Get domain summary to verify contribution was processed
        summary_response = await async_client.get("/api/v1/expert-knowledge/domain-summary/entities")
        assert summary_response.status_code == 200
        
        # Step 3: Get recommendations for similar contributions
        recommendations_response = await async_client.post("/api/v1/expert-knowledge/get-recommendations", json={
            "context": "custom_entity_creation",
            "contribution_type": "pattern"
        })
        assert recommendations_response.status_code == 200

    @pytest.mark.asyncio
    async def test_statistics_and_monitoring(self, async_client: AsyncClient):
        """Test statistics and monitoring endpoints"""
        # Get capture statistics
        stats_response = await async_client.get("/api/v1/expert-knowledge/capture-stats")
        assert stats_response.status_code == 200
        
        stats = stats_response.json()
        assert "quality_trends" in stats
        assert "processing_performance" in stats
        assert "top_contributors" in stats
        assert "domain_coverage" in stats
        
        # Check health status
        health_response = await async_client.get("/api/v1/expert-knowledge/health")
        assert health_response.status_code == 200
        
        health = health_response.json()
        assert health["status"] in ["healthy", "degraded", "unhealthy"]
