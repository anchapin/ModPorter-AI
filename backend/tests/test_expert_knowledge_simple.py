"""
Working tests for expert_knowledge_simple.py API
Implementing comprehensive tests for coverage improvement
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.expert_knowledge_simple import capture_expert_contribution, health_check


class TestExpertKnowledgeCapture:
    """Test expert knowledge capture endpoint"""

    @pytest.mark.asyncio
    async def test_capture_expert_contribution_success(self):
        """Test successful expert contribution capture"""
        request_data = {
            "expert_id": "expert-123",
            "knowledge_type": "pattern",
            "content": "This is a known conversion pattern",
            "domain": "bedrock_edition",
            "confidence": 0.95,
        }

        result = await capture_expert_contribution(request_data)

        assert result["status"] == "success"
        assert result["contribution_id"].startswith("contrib_")
        assert result["message"] == "Expert contribution captured successfully"

    @pytest.mark.asyncio
    async def test_capture_expert_contribution_minimal_data(self):
        """Test contribution capture with minimal data"""
        request_data = {"expert_id": "expert-456"}

        result = await capture_expert_contribution(request_data)

        assert result["status"] == "success"
        assert result["contribution_id"].startswith("contrib_")

    @pytest.mark.asyncio
    async def test_capture_expert_contribution_complex_data(self):
        """Test contribution capture with complex structured data"""
        request_data = {
            "expert_id": "expert-789",
            "knowledge_type": "complex_rule",
            "content": {
                "condition": "if block_type == 'chest'",
                "action": "apply_vanilla_logic",
                "parameters": ["preserve_items", "update_logic"],
            },
            "metadata": {
                "source": "community_expert",
                "verified": True,
                "usage_count": 15,
            },
        }

        result = await capture_expert_contribution(request_data)

        assert result["status"] == "success"
        assert result["contribution_id"].startswith("contrib_")


class TestExpertKnowledgeHealth:
    """Test expert knowledge service health endpoint"""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check"""
        result = await health_check()

        assert result["status"] == "healthy"
        assert result["service"] == "expert_knowledge"


class TestExpertKnowledgeIntegration:
    """Test expert knowledge integration scenarios"""

    @pytest.mark.asyncio
    async def test_full_contribution_workflow(self):
        """Test full expert contribution workflow"""
        # Step 1: Capture contribution
        contribution_data = {
            "expert_id": "workflow-expert",
            "knowledge_type": "conversion_optimization",
            "content": {
                "before": "complex_chain_logic",
                "after": "simplified_mapping",
                "improvement": "30% faster execution",
            },
        }

        contribution_result = await capture_expert_contribution(contribution_data)
        assert contribution_result["status"] == "success"

        # Step 2: Verify service health
        health_result = await health_check()
        assert health_result["status"] == "healthy"

        # Verify integration
        assert isinstance(contribution_result["contribution_id"], str)
        assert len(contribution_result["contribution_id"]) > 10

    @pytest.mark.asyncio
    async def test_multiple_contributions_batch(self):
        """Test handling multiple expert contributions"""
        contributions = [
            {
                "expert_id": f"expert-{i}",
                "knowledge_type": "batch_pattern",
                "content": f"Pattern contribution {i}",
            }
            for i in range(5)
        ]

        results = []
        for contribution in contributions:
            result = await capture_expert_contribution(contribution)
            results.append(result)

        # Verify all contributions were captured
        assert len(results) == 5
        for result in results:
            assert result["status"] == "success"
            assert result["contribution_id"].startswith("contrib_")

        # Verify all contribution IDs are unique
        contribution_ids = [result["contribution_id"] for result in results]
        assert len(set(contribution_ids)) == 5
