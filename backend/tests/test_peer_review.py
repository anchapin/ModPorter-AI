"""
Comprehensive tests for Peer Review System API
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestPeerReviewAPI:
    """Test suite for Peer Review System endpoints"""

    @pytest.mark.asyncio
    async def test_create_peer_review(self, async_client: AsyncClient):
        """Test creating a new peer review"""
        review_data = {
            "submission_id": str(uuid4()),
            "reviewer_id": str(uuid4()),
            "content_analysis": {"score": 85, "comments": "Good quality content"},
            "technical_review": {"score": 90, "issues_found": []},
            "recommendation": "approve"
        }
        
        response = await async_client.post("/api/v1/peer-review/reviews/", json=review_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["submission_id"] == review_data["submission_id"]
        assert data["reviewer_id"] == review_data["reviewer_id"]
        assert data["recommendation"] == "approve"

    @pytest.mark.asyncio
    async def test_get_peer_review(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test retrieving a specific peer review"""
        # First create a review
        review_data = {
            "submission_id": str(uuid4()),
            "reviewer_id": str(uuid4()),
            "content_analysis": {"score": 80},
            "recommendation": "request_changes"
        }
        
        create_response = await async_client.post("/api/v1/peer-review/reviews/", json=review_data)
        review_id = create_response.json()["id"]
        
        # Retrieve the review
        response = await async_client.get(f"/api/v1/peer-review/reviews/{review_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == review_id
        assert data["recommendation"] == "request_changes"

    @pytest.mark.asyncio
    async def test_list_peer_reviews(self, async_client: AsyncClient):
        """Test listing peer reviews with filters"""
        # Create multiple reviews
        for i in range(3):
            review_data = {
                "submission_id": str(uuid4()),
                "reviewer_id": str(uuid4()),
                "content_analysis": {"score": 70 + i * 5},
                "recommendation": "approve" if i > 0 else "request_changes"
            }
            await async_client.post("/api/v1/peer-review/reviews/", json=review_data)
        
        # List all reviews
        response = await async_client.get("/api/v1/peer-review/reviews/")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["items"]) >= 3
        assert "total" in data
        assert "page" in data

    @pytest.mark.asyncio
    async def test_create_review_workflow(self, async_client: AsyncClient):
        """Test creating a review workflow"""
        workflow_data = {
            "submission_id": str(uuid4()),
            "workflow_type": "technical_review",
            "stages": [
                {"name": "initial_review", "required": True},
                {"name": "expert_review", "required": False}
            ],
            "auto_assign": True
        }
        
        response = await async_client.post("/api/v1/peer-review/workflows/", json=workflow_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["submission_id"] == workflow_data["submission_id"]
        assert data["workflow_type"] == "technical_review"
        assert len(data["stages"]) == 2

    @pytest.mark.asyncio
    async def test_advance_workflow_stage(self, async_client: AsyncClient):
        """Test advancing a workflow to the next stage"""
        # Create workflow first
        workflow_data = {
            "submission_id": str(uuid4()),
            "workflow_type": "content_review",
            "stages": [
                {"name": "initial_review", "required": True},
                {"name": "final_review", "required": True}
            ]
        }
        
        create_response = await async_client.post("/api/v1/peer-review/workflows/", json=workflow_data)
        workflow_id = create_response.json()["id"]
        
        # Advance to next stage
        advance_data = {
            "stage_name": "final_review",
            "notes": "Initial review completed successfully"
        }
        
        response = await async_client.post(
            f"/api/v1/peer-review/workflows/{workflow_id}/advance", 
            json=advance_data
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["current_stage"] == "final_review"

    @pytest.mark.asyncio
    async def test_add_reviewer_expertise(self, async_client: AsyncClient):
        """Test adding reviewer expertise"""
        expertise_data = {
            "reviewer_id": str(uuid4()),
            "domain": "java_modding",
            "expertise_level": "expert",
            "years_experience": 5,
            "specializations": ["fabric", "forge"],
            "verified": True
        }
        
        response = await async_client.post("/api/v1/peer-review/expertise/", json=expertise_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["reviewer_id"] == expertise_data["reviewer_id"]
        assert data["domain"] == "java_modding"
        assert data["expertise_level"] == "expert"

    @pytest.mark.asyncio
    async def test_create_review_template(self, async_client: AsyncClient):
        """Test creating a review template"""
        template_data = {
            "name": "Technical Review Template",
            "description": "Template for technical reviews",
            "template_type": "technical",
            "criteria": [
                {"name": "code_quality", "weight": 0.3, "required": True},
                {"name": "performance", "weight": 0.2, "required": True},
                {"name": "security", "weight": 0.25, "required": True}
            ],
            "default_settings": {
                "auto_assign": False,
                "min_reviewers": 2,
                "deadline_days": 7
            }
        }
        
        response = await async_client.post("/api/v1/peer-review/templates/", json=template_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["name"] == template_data["name"]
        assert data["template_type"] == "technical"
        assert len(data["criteria"]) == 3

    @pytest.mark.asyncio
    async def test_get_review_analytics(self, async_client: AsyncClient):
        """Test retrieving review analytics"""
        response = await async_client.get("/api/v1/peer-review/analytics/")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_reviews" in data
        assert "average_completion_time" in data
        assert "approval_rate" in data
        assert "reviewer_workload" in data

    @pytest.mark.asyncio
    async def test_assign_reviewers_automatically(self, async_client: AsyncClient):
        """Test automatic reviewer assignment"""
        assignment_data = {
            "submission_id": str(uuid4()),
            "required_reviews": 2,
            "expertise_required": ["java_modding", "fabric"],
            "exclude_reviewers": [str(uuid4())],
            "deadline": (datetime.now() + timedelta(days=7)).isoformat()
        }
        
        response = await async_client.post("/api/v1/peer-review/assign/", json=assignment_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "assigned_reviewers" in data
        assert "assignment_id" in data

    @pytest.mark.asyncio
    async def test_get_reviewer_workload(self, async_client: AsyncClient):
        """Test getting reviewer workload information"""
        reviewer_id = str(uuid4())
        response = await async_client.get(f"/api/v1/peer-review/reviewers/{reviewer_id}/workload")
        assert response.status_code == 200
        
        data = response.json()
        assert "active_reviews" in data
        assert "completed_reviews" in data
        assert "average_review_time" in data

    @pytest.mark.asyncio
    async def test_submit_review_feedback(self, async_client: AsyncClient):
        """Test submitting feedback on a review"""
        # First create a review
        review_data = {
            "submission_id": str(uuid4()),
            "reviewer_id": str(uuid4()),
            "content_analysis": {"score": 85},
            "recommendation": "approve"
        }
        
        create_response = await async_client.post("/api/v1/peer-review/reviews/", json=review_data)
        review_id = create_response.json()["id"]
        
        # Submit feedback
        feedback_data = {
            "review_id": review_id,
            "feedback_type": "helpful",
            "rating": 5,
            "comments": "Very thorough review",
            "anonymous": False
        }
        
        response = await async_client.post("/api/v1/peer-review/feedback/", json=feedback_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["review_id"] == review_id
        assert data["rating"] == 5

    @pytest.mark.asyncio
    async def test_review_search(self, async_client: AsyncClient):
        """Test searching reviews with filters"""
        # Create reviews with different data
        reviewer_id = str(uuid4())
        for i in range(3):
            review_data = {
                "submission_id": str(uuid4()),
                "reviewer_id": reviewer_id,
                "content_analysis": {"score": 80 + i * 5},
                "recommendation": "approve" if i > 0 else "request_changes",
                "tags": [f"tag{i}", "common"]
            }
            await async_client.post("/api/v1/peer-review/reviews/", json=review_data)
        
        # Search for reviews
        search_params = {
            "reviewer_id": reviewer_id,
            "recommendation": "approve",
            "limit": 10
        }
        
        response = await async_client.get("/api/v1/peer-review/search/", params=search_params)
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert all(review["reviewer_id"] == reviewer_id for review in data["results"])

    @pytest.mark.asyncio
    async def test_invalid_review_data(self, async_client: AsyncClient):
        """Test validation of invalid review data"""
        invalid_data = {
            "submission_id": "invalid-uuid",
            "reviewer_id": str(uuid4()),
            "content_analysis": {"score": 150},  # Invalid score > 100
            "recommendation": "invalid_status"
        }
        
        response = await async_client.post("/api/v1/peer-review/reviews/", json=invalid_data)
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_workflow_state_transitions(self, async_client: AsyncClient):
        """Test workflow state transitions are valid"""
        # Create workflow
        workflow_data = {
            "submission_id": str(uuid4()),
            "workflow_type": "simple_review",
            "stages": [
                {"name": "pending", "required": True},
                {"name": "in_review", "required": True},
                {"name": "completed", "required": True}
            ]
        }
        
        create_response = await async_client.post("/api/v1/peer-review/workflows/", json=workflow_data)
        workflow_id = create_response.json()["id"]
        
        # Try to advance beyond next stage (should fail)
        invalid_advance = {
            "stage_name": "completed",
            "notes": "Skipping in_review"
        }
        
        response = await async_client.post(
            f"/api/v1/peer-review/workflows/{workflow_id}/advance",
            json=invalid_advance
        )
        assert response.status_code == 400  # Bad request

    @pytest.mark.asyncio
    async def test_export_review_data(self, async_client: AsyncClient):
        """Test exporting review data in different formats"""
        # Create a review first
        review_data = {
            "submission_id": str(uuid4()),
            "reviewer_id": str(uuid4()),
            "content_analysis": {"score": 85, "comments": "Good review"},
            "recommendation": "approve"
        }
        
        await async_client.post("/api/v1/peer-review/reviews/", json=review_data)
        
        # Export as JSON
        response = await async_client.get("/api/v1/peer-review/export/?format=json")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        # Export as CSV
        response = await async_client.get("/api/v1/peer-review/export/?format=csv")
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
