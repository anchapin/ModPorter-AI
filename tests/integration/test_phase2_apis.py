"""
Integration tests for Phase 2 APIs
Tests peer review, knowledge graph, expert knowledge, version compatibility, and conversion inference
"""
import pytest
import asyncio
from uuid import uuid4
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestPhase2Integration:
    """Integration tests for all Phase 2 APIs working together"""

    @pytest.mark.asyncio
    async def test_complete_knowledge_capture_workflow(self, async_client: AsyncClient):
        """Test the complete workflow from code submission to knowledge graph population"""
        
        # Step 1: Submit a code contribution
        contribution_data = {
            "contributor_id": str(uuid4()),
            "contribution_type": "code_pattern",
            "title": "Optimal Block Registration Pattern",
            "description": "Efficient pattern for registering custom blocks in Forge mods",
            "content": {
                "pattern_code": """
                    public class ModBlocks {
                        public static final DeferredRegister<Block> BLOCKS = 
                            DeferredRegister.create(ForgeMod.MOD_ID, Registry.BLOCK_REGISTRY);
                        
                        public static final RegistryObject<Block> CUSTOM_BLOCK = 
                            BLOCKS.register("custom_block", CustomBlock::new);
                    }
                """,
                "explanation": "Uses DeferredRegister for thread-safe registration",
                "best_practices": ["deferred_registration", "static_final_fields"]
            },
            "tags": ["forge", "blocks", "registration", "thread_safety"],
            "references": [
                {"type": "documentation", "url": "https://docs.minecraftforge.net/en/latest/blocks/blocks/"},
                {"type": "example", "mod_id": "forge_example_mod"}
            ]
        }
        
        contribution_response = await async_client.post("/api/expert-knowledge/contributions/", json=contribution_data)
        assert contribution_response.status_code == 201
        contribution_id = contribution_response.json()["id"]
        
        # Step 2: Knowledge extraction from the contribution
        extraction_request = {
            "content_type": "code_pattern",
            "content": contribution_data["content"]["pattern_code"],
            "context": {
                "contribution_id": contribution_id,
                "domain": "java_modding",
                "mod_type": "forge"
            }
        }
        
        extraction_response = await async_client.post("/api/expert-knowledge/extract/", json=extraction_request)
        assert extraction_response.status_code == 200
        
        extracted_data = extraction_response.json()
        assert len(extracted_data["extracted_entities"]) > 0
        assert len(extracted_data["relationships"]) > 0
        
        # Step 3: Create knowledge graph nodes from extracted entities
        for entity in extracted_data["extracted_entities"]:
            node_data = {
                "node_type": entity["type"],
                "properties": entity["properties"],
                "metadata": {
                    "source": "expert_contribution",
                    "contribution_id": contribution_id,
                    "extracted_at": datetime.now().isoformat()
                }
            }
            
            node_response = await async_client.post("/api/knowledge-graph/nodes/", json=node_data)
            assert node_response.status_code == 201
            entity["graph_id"] = node_response.json()["id"]
        
        # Step 4: Create knowledge graph edges from relationships
        for relationship in extracted_data["relationships"]:
            source_entity = next(e for e in extracted_data["extracted_entities"] if e["name"] == relationship["source"])
            target_entity = next(e for e in extracted_data["extracted_entities"] if e["name"] == relationship["target"])
            
            edge_data = {
                "source_id": source_entity["graph_id"],
                "target_id": target_entity["graph_id"],
                "relationship_type": relationship["type"],
                "properties": relationship["properties"]
            }
            
            edge_response = await async_client.post("/api/knowledge-graph/edges/", json=edge_data)
            assert edge_response.status_code == 201
        
        # Step 5: Verify knowledge graph has the new nodes and edges
        graph_stats_response = await async_client.get("/api/knowledge-graph/statistics/")
        assert graph_stats_response.status_code == 200
        
        stats = graph_stats_response.json()
        assert stats["node_count"] > 0
        assert stats["edge_count"] > 0

    @pytest.mark.asyncio
    async def test_peer_review_to_version_compatibility_workflow(self, async_client: AsyncClient):
        """Test workflow from peer review to version compatibility matrix updates"""
        
        # Step 1: Submit a contribution about version compatibility
        compatibility_contribution = {
            "contributor_id": str(uuid4()),
            "contribution_type": "migration_guide",
            "title": "1.18.2 to 1.19.2 Block Migration",
            "description": "Complete guide for migrating block code between versions",
            "content": {
                "source_version": "1.18.2",
                "target_version": "1.19.2",
                "breaking_changes": [
                    {
                        "type": "api_change",
                        "description": "BlockBehaviourProperties changed to BlockBehaviour",
                        "impact": "high"
                    }
                ],
                "migration_steps": [
                    "Update block properties references",
                    "Replace deprecated methods",
                    "Test block functionality"
                ]
            },
            "tags": ["migration", "1.18.2", "1.19.2", "blocks"]
        }
        
        contribution_response = await async_client.post("/api/expert-knowledge/contributions/", json=compatibility_contribution)
        if contribution_response.status_code != 201:
            print(f"Error response: {contribution_response.status_code}")
            print(f"Response body: {contribution_response.text}")
        assert contribution_response.status_code == 201
        contribution_id = contribution_response.json()["id"]
        
        # Step 2: Create peer review for the contribution
        review_data = {
            "submission_id": contribution_id,
            "reviewer_id": str(uuid4()),
            "content_analysis": {
                "score": 8.5,
                "clarity": "excellent",
                "completeness": "good",
                "accuracy": "high"
            },
            "technical_review": {
                "score": 9.0,
                "code_examples_correct": True,
                "api_references_current": True,
                "steps_tested": True
            },
            "recommendation": "approve"
        }
        
        review_response = await async_client.post("/api/peer-review/reviews/", json=review_data)
        assert review_response.status_code == 201
        review_id = review_response.json()["id"]
        
        # Step 3: Approve the contribution based on positive review
        approval_response = await async_client.post(f"/api/expert-knowledge/contributions/{contribution_id}/approve", json={
            "approved_by": "system",
            "review_ids": [review_id],
            "approval_notes": "Approved based on positive peer review"
        })
        assert approval_response.status_code == 200
        
        # Step 4: Create version compatibility entry from approved contribution
        compatibility_entry = {
            "source_version": "1.18.2",
            "target_version": "1.19.2",
            "compatibility_score": 0.85,
            "conversion_complexity": "medium",
            "breaking_changes": compatibility_contribution["content"]["breaking_changes"],
            "migration_guide": {
                "steps": compatibility_contribution["content"]["migration_steps"],
                "estimated_time": "2-3 hours",
                "difficulty": "intermediate"
            },
            "test_results": {
                "success_rate": 0.9,
                "total_tests": 20,
                "failed_tests": 2
            },
            "source_contribution_id": contribution_id
        }
        
        compat_response = await async_client.post("/api/version-compatibility/entries/", json=compatibility_entry)
        assert compat_response.status_code == 201
        compat_id = compat_response.json()["id"]
        
        # Step 5: Verify compatibility matrix includes the new entry
        matrix_response = await async_client.get("/api/version-compatibility/compatibility/1.18.2/1.19.2")
        assert matrix_response.status_code == 200
        
        matrix_data = matrix_response.json()
        assert matrix_data["source_version"] == "1.18.2"
        assert matrix_data["target_version"] == "1.19.2"
        assert matrix_data["compatibility_score"] == 0.85

    @pytest.mark.asyncio
    async def test_conversion_inference_with_community_data(self, async_client: AsyncClient):
        """Test conversion inference using community-sourced data"""
        
        # Step 1: Set up multiple version compatibility entries
        compatibility_entries = [
            {
                "source_version": "1.17.1",
                "target_version": "1.18.2",
                "compatibility_score": 0.9,
                "conversion_complexity": "low"
            },
            {
                "source_version": "1.18.2",
                "target_version": "1.19.2",
                "compatibility_score": 0.8,
                "conversion_complexity": "medium"
            },
            {
                "source_version": "1.16.5",
                "target_version": "1.17.1",
                "compatibility_score": 0.85,
                "conversion_complexity": "low"
            }
        ]
        
        for entry in compatibility_entries:
            response = await async_client.post("/api/version-compatibility/entries/", json=entry)
            assert response.status_code == 201
        
        # Step 2: Submit a mod for conversion inference
        mod_data = {
            "mod_id": "test_mod",
            "version": "1.16.5",
            "loader": "forge",
            "features": ["custom_blocks", "entities", "networking"],
            "complexity_indicators": {
                "code_size": 8000,
                "custom_content_count": 75,
                "dependency_count": 12
            }
        }
        
        inference_request = {
            "source_mod": mod_data,
            "target_version": "1.19.2",
            "target_loader": "forge",
            "optimization_goals": ["minimal_breaking_changes", "maintain_performance"],
            "constraints": {
                "max_conversion_time": "4h",
                "preserve_world_data": True
            }
        }
        
        # Step 3: Get conversion path inference
        inference_response = await async_client.post("/api/conversion-inference/infer-path/", json=inference_request)
        assert inference_response.status_code == 200
        
        inference_result = inference_response.json()
        assert "recommended_path" in inference_result
        assert "confidence_score" in inference_result
        assert inference_result["confidence_score"] > 0.7
        
        # Step 4: Verify the recommended path uses known compatible versions
        path = inference_result["recommended_path"]["steps"]
        version_sequence = [mod_data["version"]]
        for step in path:
            if "target_version" in step:
                version_sequence.append(step["target_version"])
        
        # Should go 1.16.5 -> 1.17.1 -> 1.18.2 -> 1.19.2
        assert version_sequence[0] == "1.16.5"
        assert version_sequence[-1] == "1.19.2"
        assert len(version_sequence) >= 3  # Should include intermediate steps
        
        # Step 5: Verify each step in the path has good compatibility
        for i in range(len(version_sequence) - 1):
            source = version_sequence[i]
            target = version_sequence[i + 1]
            
            compat_response = await async_client.get(f"/api/version-compatibility/compatibility/{source}/{target}")
            assert compat_response.status_code == 200
            
            compat_data = compat_response.json()
            assert compat_data["compatibility_score"] > 0.7  # Should only use high-compatibility paths

    @pytest.mark.asyncio
    async def test_community_quality_assurance_workflow(self, async_client: AsyncClient):
        """Test the complete quality assurance workflow from submission to approval"""
        
        # Step 1: User submits a contribution
        user_contribution = {
            "contributor_id": str(uuid4()),
            "contribution_type": "performance_tip",
            "title": "Optimize Entity Ticking",
            "description": "Tips for reducing entity tick overhead",
            "content": {
                "tip": "Use canUpdate() to skip unnecessary ticking",
                "code_example": """
                    @Override
                    public boolean canUpdate() {
                        return this.ticksExisted % 10 == 0; // Only update every 10 ticks
                    }
                """,
                "performance_gain": "90% reduction in tick overhead",
                "side_effects": "Reduced responsiveness for slow entities"
            },
            "tags": ["performance", "entities", "optimization", "ticking"]
        }
        
        contribution_response = await async_client.post("/api/expert-knowledge/contributions/", json=user_contribution)
        assert contribution_response.status_code == 201
        contribution_id = contribution_response.json()["id"]
        
        # Step 2: Automatic validation
        validation_response = await async_client.post("/api/expert-knowledge/validate/", json={
            "knowledge_item": user_contribution["content"],
            "validation_rules": [
                {"name": "code_syntax_check", "check": "java_syntax"},
                {"name": "safety_check", "check": "no_dangerous_code"},
                {"name": "accuracy_check", "check": "verify_claims"}
            ]
        })
        assert validation_response.status_code == 200
        
        validation_result = validation_response.json()
        assert validation_result["is_valid"] == True
        
        # Step 3: Create peer review assignment
        assignment_response = await async_client.post("/api/peer-review/assign/", json={
            "submission_id": contribution_id,
            "required_reviews": 2,
            "expertise_required": ["performance", "entities"],
            "deadline": (datetime.now() + timedelta(days=7)).isoformat()
        })
        assert assignment_response.status_code == 200
        assignment_id = assignment_response.json()["assignment_id"]
        
        # Step 4: Submit multiple reviews
        review_data_1 = {
            "submission_id": contribution_id,
            "reviewer_id": str(uuid4()),
            "content_analysis": {"score": 9.0, "clarity": "excellent"},
            "technical_review": {"score": 8.5, "code_working": True},
            "recommendation": "approve"
        }
        
        review_data_2 = {
            "submission_id": contribution_id,
            "reviewer_id": str(uuid4()),
            "content_analysis": {"score": 8.0, "clarity": "good"},
            "technical_review": {"score": 9.5, "performance_claim_verified": True},
            "recommendation": "approve"
        }
        
        for review_data in [review_data_1, review_data_2]:
            review_response = await async_client.post("/api/peer-review/reviews/", json=review_data)
            assert review_response.status_code == 201
        
        # Step 5: Check if contribution is ready for final approval
        status_response = await async_client.get(f"/api/expert-knowledge/contributions/{contribution_id}/status")
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        assert status_data["reviews_completed"] == 2
        assert status_data["average_review_score"] > 8.0
        assert status_data["approval_ready"] == True
        
        # Step 6: Final approval and publishing
        approval_response = await async_client.post(f"/api/expert-knowledge/contributions/{contribution_id}/approve", json={
            "approved_by": "moderator",
            "approval_type": "published"
        })
        assert approval_response.status_code == 200
        
        # Step 7: Verify contribution appears in search results
        search_response = await async_client.get("/api/expert-knowledge/contributions/search", params={
            "query": "entity ticking",
            "limit": 10
        })
        assert search_response.status_code == 200
        
        search_results = search_response.json()["results"]
        found_contribution = next((r for r in search_results if r["id"] == contribution_id), None)
        assert found_contribution is not None
        assert found_contribution["status"] == "published"

    @pytest.mark.asyncio
    async def test_knowledge_graph_insights_from_community_data(self, async_client: AsyncClient):
        """Test extracting insights from knowledge graph populated with community data"""
        
        # Step 1: Submit multiple related contributions
        contributions = [
            {
                "title": "Custom Block Creation",
                "type": "tutorial",
                "content": {"focus": "block_registration", "difficulty": "beginner"},
                "tags": ["blocks", "tutorial", "beginner"]
            },
            {
                "title": "Advanced Block Properties",
                "type": "code_pattern",
                "content": {"focus": "block_states", "difficulty": "advanced"},
                "tags": ["blocks", "properties", "advanced"]
            },
            {
                "title": "Block Performance Optimization",
                "type": "performance_tip",
                "content": {"focus": "rendering_optimization", "difficulty": "intermediate"},
                "tags": ["blocks", "performance", "optimization"]
            }
        ]
        
        contribution_ids = []
        for contribution in contributions:
            contribution_data = {
                "contributor_id": str(uuid4()),
                "contribution_type": contribution["type"],
                "title": contribution["title"],
                "content": contribution["content"],
                "tags": contribution["tags"]
            }
            
            response = await async_client.post("/api/expert-knowledge/contributions/", json=contribution_data)
            assert response.status_code == 201
            contribution_ids.append(response.json()["id"])
        
        # Step 2: Extract and create knowledge graph entities
        for contribution_id in contribution_ids:
            extraction_response = await async_client.post("/api/expert-knowledge/extract/", json={
                "content_type": "contribution",
                "content": contribution_id,
                "context": {"domain": "minecraft_modding"}
            })
            assert extraction_response.status_code == 200
            
            extracted = extraction_response.json()
            # Create nodes and edges from extracted data
            for entity in extracted["extracted_entities"]:
                await async_client.post("/api/knowledge-graph/nodes/", json={
                    "node_type": entity["type"],
                    "properties": entity["properties"],
                    "metadata": {"source_contribution": contribution_id}
                })
        
        # Step 3: Get graph insights and patterns
        insights_response = await async_client.get("/api/knowledge-graph/insights/", params={
            "focus_domain": "blocks",
            "analysis_types": ["patterns", "gaps", "connections"]
        })
        assert insights_response.status_code == 200
        
        insights = insights_response.json()
        assert "patterns" in insights
        assert "knowledge_gaps" in insights
        assert "strong_connections" in insights
        
        # Step 4: Verify patterns are detected
        patterns = insights["patterns"]
        assert len(patterns) > 0
        
        block_patterns = [p for p in patterns if "block" in p["focus"].lower()]
        assert len(block_patterns) > 0
        
        # Step 5: Get recommendations based on graph analysis
        recommendations_response = await async_client.post("/api/expert-knowledge/graph/suggestions", json={
            "current_nodes": ["block", "performance", "optimization"],
            "mod_context": {"mod_type": "forge", "complexity": "intermediate"},
            "user_goals": ["learn_blocks", "optimize_performance"]
        })
        assert recommendations_response.status_code == 200
        
        recommendations = recommendations_response.json()
        assert "suggested_nodes" in recommendations
        assert "relevant_patterns" in recommendations
        assert len(recommendations["suggested_nodes"]) > 0

    @pytest.mark.asyncio
    async def test_batch_processing_and_analytics(self, async_client: AsyncClient):
        """Test batch processing capabilities and analytics generation"""
        
        # Step 1: Submit batch of contributions
        batch_contributions = []
        for i in range(10):
            contribution = {
                "contributor_id": str(uuid4()),
                "contribution_type": "code_pattern",
                "title": f"Pattern {i+1}",
                "content": {"example": f"code_example_{i+1}"},
                "tags": [f"tag_{i%3}", "pattern"]
            }
            batch_contributions.append(contribution)
        
        batch_request = {
            "contributions": batch_contributions,
            "processing_options": {
                "validate_knowledge": True,
                "extract_entities": True,
                "update_graph": True
            }
        }
        
        batch_response = await async_client.post("/api/expert-knowledge/contributions/batch", json=batch_request)
        assert batch_response.status_code == 202
        batch_id = batch_response.json()["batch_id"]
        
        # Step 2: Monitor batch processing
        processing_complete = False
        max_attempts = 30
        attempt = 0
        
        while not processing_complete and attempt < max_attempts:
            status_response = await async_client.get(f"/api/expert-knowledge/contributions/batch/{batch_id}/status")
            assert status_response.status_code == 200
            
            status_data = status_response.json()
            if status_data["status"] == "completed":
                processing_complete = True
                break
            
            await asyncio.sleep(1)
            attempt += 1
        
        assert processing_complete == True
        
        # Step 3: Generate analytics from processed data
        analytics_response = await async_client.get("/api/peer-review/analytics/", params={
            "time_period": "7d",
            "metrics": ["volume", "quality", "participation"]
        })
        assert analytics_response.status_code == 200
        
        analytics = analytics_response.json()
        assert "total_reviews" in analytics
        assert "average_completion_time" in analytics
        assert "approval_rate" in analytics
        
        # Step 4: Check knowledge graph statistics
        graph_stats_response = await async_client.get("/api/knowledge-graph/statistics/")
        assert graph_stats_response.status_code == 200
        
        graph_stats = graph_stats_response.json()
        assert graph_stats["node_count"] > 0
        assert graph_stats["edge_count"] > 0
        
        # Step 5: Verify version compatibility matrix is updated
        matrix_response = await async_client.get("/api/version-compatibility/statistics/")
        assert matrix_response.status_code == 200
        
        matrix_stats = matrix_response.json()
        assert "total_version_pairs" in matrix_stats
        assert "average_compatibility_score" in matrix_stats

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, async_client: AsyncClient):
        """Test error handling and recovery mechanisms"""
        
        # Step 1: Test validation errors
        invalid_contribution = {
            "contributor_id": "invalid-uuid",
            "contribution_type": "invalid_type",
            "title": "",  # Empty title
            "content": {},  # Empty content
            "tags": []  # No tags
        }
        
        response = await async_client.post("/api/expert-knowledge/contributions/", json=invalid_contribution)
        assert response.status_code == 422
        
        # Step 2: Test concurrent operations
        contribution_id = str(uuid4())
        
        # Simulate concurrent review submissions
        review_tasks = []
        for i in range(3):
            review_data = {
                "submission_id": contribution_id,
                "reviewer_id": str(uuid4()),
                "content_analysis": {"score": 8.0},
                "recommendation": "approve"
            }
            
            task = async_client.post("/api/peer-review/reviews/", json=review_data)
            review_tasks.append(task)
        
        # Wait for all tasks to complete
        review_results = await asyncio.gather(*review_tasks, return_exceptions=True)
        
        # At least one should succeed (first one), others might fail due to constraints
        successful_reviews = [r for r in review_results if hasattr(r, 'status_code') and r.status_code == 201]
        assert len(successful_reviews) >= 1
        
        # Step 3: Test knowledge graph transaction rollback on errors
        invalid_node = {
            "node_type": "invalid_type",
            "properties": {"invalid_field": "value"}
        }
        
        node_response = await async_client.post("/api/knowledge-graph/nodes/", json=invalid_node)
        assert node_response.status_code == 422  # Should fail validation
        
        # Verify graph is not corrupted
        graph_health_response = await async_client.get("/api/knowledge-graph/health/")
        assert graph_health_response.status_code == 200
        
        health_data = graph_health_response.json()
        assert health_data["status"] == "healthy"
        
        # Step 4: Test inference engine fallback
        incomplete_mod_data = {
            "source_mod": {
                "mod_id": "incomplete_mod",
                "version": "1.18.2"
                # Missing required fields
            },
            "target_version": "1.19.2"
        }
        
        inference_response = await async_client.post("/api/conversion-inference/infer-path/", json=incomplete_mod_data)
        assert inference_response.status_code == 422
        
        # Should provide helpful error message
        error_data = inference_response.json()
        assert "detail" in error_data
        assert "missing" in error_data["detail"].lower()
