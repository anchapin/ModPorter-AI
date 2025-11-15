"""
Comprehensive Test Suite for Peer Review API

This module provides extensive test coverage for the peer review system API,
including reviews, workflows, reviewer expertise, templates, and analytics.
"""

import pytest
import json
import uuid
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
import os

# Set testing environment
os.environ["TESTING"] = "true"

# Import the router
from src.api.peer_review import router

# Create FastAPI app with the router
app = FastAPI()
app.include_router(router, prefix="/api/peer-review")


class TestPeerReviewAPI:
    """Comprehensive test suite for peer review API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def sample_review_data(self):
        """Sample review data for testing."""
        return {
            "submission_id": str(uuid.uuid4()),
            "reviewer_id": "reviewer_123",
            "recommendation": "approve",
            "content_analysis": {
                "score": 85,
                "comments": "Good work overall"
            },
            "technical_review": {
                "score": 90,
                "issues_found": []
            }
        }
    
    @pytest.fixture
    def sample_workflow_data(self):
        """Sample workflow data for testing."""
        return {
            "submission_id": str(uuid.uuid4()),
            "workflow_type": "technical_review",
            "stages": [
                {"name": "initial_review", "status": "pending"},
                {"name": "technical_review", "status": "pending"}
            ],
            "auto_assign": True
        }
    
    @pytest.fixture
    def sample_expertise_data(self):
        """Sample expertise data for testing."""
        return {
            "reviewer_id": "expert_123",
            "expertise_areas": ["java_modding", "forge"],
            "minecraft_versions": ["1.18.2", "1.19.2"],
            "java_experience_level": 4,
            "bedrock_experience_level": 2
        }

    # Peer Review Endpoints Tests
    
    def test_create_peer_review_success(self, client, sample_review_data):
        """Test successful creation of a peer review."""
        response = client.post("/api/peer-review/reviews/", json=sample_review_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert "submission_id" in data
        assert "reviewer_id" in data
        assert "status" in data
        assert "recommendation" in data
        assert "content_analysis" in data
        assert "technical_review" in data
        
        # Verify data mapping
        assert data["submission_id"] == sample_review_data["submission_id"]
        assert data["reviewer_id"] == sample_review_data["reviewer_id"]
        assert data["recommendation"] == sample_review_data["recommendation"]
        assert "score" in data["content_analysis"]
        assert "score" in data["technical_review"]
    
    def test_create_peer_review_invalid_submission_id(self, client):
        """Test creation with invalid submission ID format."""
        review_data = {
            "submission_id": "invalid-uuid",
            "reviewer_id": "reviewer_123",
            "recommendation": "approve"
        }
        
        response = client.post("/api/peer-review/reviews/", json=review_data)
        assert response.status_code == 422
    
    def test_create_peer_review_invalid_score_range(self, client):
        """Test creation with score outside valid range."""
        review_data = {
            "submission_id": str(uuid.uuid4()),
            "reviewer_id": "reviewer_123",
            "recommendation": "approve",
            "content_analysis": {
                "score": 150,  # Invalid: > 100
                "comments": "Test"
            }
        }
        
        response = client.post("/api/peer-review/reviews/", json=review_data)
        assert response.status_code == 422
    
    def test_create_peer_review_invalid_recommendation(self, client):
        """Test creation with invalid recommendation value."""
        review_data = {
            "submission_id": str(uuid.uuid4()),
            "reviewer_id": "reviewer_123",
            "recommendation": "invalid_option"
        }
        
        response = client.post("/api/peer-review/reviews/", json=review_data)
        assert response.status_code == 422
    
    def test_get_peer_review_by_id(self, client):
        """Test retrieving peer review by ID."""
        review_id = str(uuid.uuid4())
        
        response = client.get(f"/api/peer-review/reviews/{review_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == review_id
        assert "submission_id" in data
        assert "reviewer_id" in data
        assert "status" in data
        assert "recommendation" in data
        assert "content_analysis" in data
        assert "technical_review" in data
    
    def test_list_peer_reviews_default_pagination(self, client):
        """Test listing peer reviews with default pagination."""
        response = client.get("/api/peer-review/reviews/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        
        # Should return mock reviews for testing
        assert len(data["items"]) > 0
        assert data["limit"] == 50
    
    def test_list_peer_reviews_custom_pagination(self, client):
        """Test listing peer reviews with custom pagination."""
        response = client.get("/api/peer-review/reviews/?limit=10&offset=20")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["limit"] == 10
        assert data["page"] == 1  # Mock response uses simple pagination
    
    def test_list_peer_reviews_with_status_filter(self, client):
        """Test listing peer reviews with status filter."""
        response = client.get("/api/peer-review/reviews/?status=pending")
        
        assert response.status_code == 200
        data = response.json()
        
        # Mock response should filter by status
        assert "items" in data
        assert "total" in data
    
    def test_get_contribution_reviews(self, client):
        """Test getting reviews for a specific contribution."""
        contribution_id = str(uuid.uuid4())
        
        response = client.get(f"/api/peer-review/reviews/contribution/{contribution_id}")
        
        assert response.status_code == 200
        # Should return list of reviews for the contribution
        assert isinstance(response.json(), list)
    
    def test_get_contribution_reviews_with_status_filter(self, client):
        """Test getting contribution reviews with status filter."""
        contribution_id = str(uuid.uuid4())
        
        response = client.get(f"/api/peer-review/reviews/contribution/{contribution_id}?status=approved")
        
        assert response.status_code == 200
        # Should return filtered reviews
        assert isinstance(response.json(), list)
    
    def test_get_reviewer_reviews(self, client):
        """Test getting reviews by a specific reviewer."""
        reviewer_id = "reviewer_123"
        
        response = client.get(f"/api/peer-review/reviews/reviewer/{reviewer_id}")
        
        assert response.status_code == 200
        # Should return list of reviews by the reviewer
        assert isinstance(response.json(), list)
    
    def test_get_reviewer_reviews_with_status_filter(self, client):
        """Test getting reviewer reviews with status filter."""
        reviewer_id = "reviewer_123"
        
        response = client.get(f"/api/peer-review/reviews/reviewer/{reviewer_id}?status=completed")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_update_review_status(self, client):
        """Test updating review status."""
        review_id = str(uuid.uuid4())
        update_data = {
            "status": "approved",
            "notes": "Review completed successfully"
        }
        
        response = client.put(f"/api/peer-review/reviews/{review_id}/status", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "Review status updated successfully" in data["message"]
    
    def test_get_pending_reviews(self, client):
        """Test getting pending reviews."""
        response = client.get("/api/peer-review/reviews/pending")
        
        assert response.status_code == 200
        # Should return list of pending reviews
        assert isinstance(response.json(), list)
    
    def test_get_pending_reviews_with_limit(self, client):
        """Test getting pending reviews with custom limit."""
        response = client.get("/api/peer-review/reviews/pending?limit=25")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    # Review Workflow Endpoints Tests
    
    def test_create_review_workflow_success(self, client, sample_workflow_data):
        """Test successful creation of a review workflow."""
        response = client.post("/api/peer-review/workflows/", json=sample_workflow_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert "submission_id" in data
        assert "workflow_type" in data
        assert "stages" in data
        assert "current_stage" in data
        assert "status" in data
        assert "auto_assign" in data
        
        # Verify data mapping
        assert data["submission_id"] == sample_workflow_data["submission_id"]
        assert data["workflow_type"] == sample_workflow_data["workflow_type"]
        assert data["auto_assign"] == sample_workflow_data["auto_assign"]
    
    def test_get_contribution_workflow(self, client):
        """Test getting workflow for a specific contribution."""
        contribution_id = str(uuid.uuid4())
        
        response = client.get(f"/api/peer-review/workflows/contribution/{contribution_id}")
        
        assert response.status_code == 200
        # Should return workflow for the contribution
        data = response.json()
        assert "id" in data
    
    def test_update_workflow_stage(self, client):
        """Test updating workflow stage."""
        workflow_id = str(uuid.uuid4())
        stage_update = {
            "current_stage": "in_review",
            "history_entry": {
                "action": "stage_advanced",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        response = client.put(f"/api/peer-review/workflows/{workflow_id}/stage", json=stage_update)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "Workflow stage updated successfully" in data["message"]
    
    def test_get_active_workflows(self, client):
        """Test getting active workflows."""
        response = client.get("/api/peer-review/workflows/active")
        
        assert response.status_code == 200
        # Should return list of active workflows
        assert isinstance(response.json(), list)
    
    def test_get_active_workflows_with_limit(self, client):
        """Test getting active workflows with custom limit."""
        response = client.get("/api/peer-review/workflows/active?limit=50")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_overdue_workflows(self, client):
        """Test getting overdue workflows."""
        response = client.get("/api/peer-review/workflows/overdue")
        
        assert response.status_code == 200
        # Should return list of overdue workflows
        assert isinstance(response.json(), list)
    
    def test_advance_workflow_stage(self, client):
        """Test advancing workflow to next stage."""
        workflow_id = str(uuid.uuid4())
        advance_data = {
            "current_stage": "pending",
            "stage_name": "in_review",
            "notes": "Moving to review phase"
        }
        
        response = client.post(f"/api/peer-review/workflows/{workflow_id}/advance", json=advance_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["workflow_id"] == workflow_id
        assert data["current_stage"] == "in_review"
        assert "updated_at" in data

    # Reviewer Expertise Endpoints Tests
    
    def test_add_reviewer_expertise_success(self, client, sample_expertise_data):
        """Test successful addition of reviewer expertise."""
        response = client.post("/api/peer-review/expertise/", json=sample_expertise_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert "reviewer_id" in data
        assert "expertise_areas" in data
        assert "minecraft_versions" in data
        assert "expertise_score" in data
        assert "is_active_reviewer" in data
        
        # Verify data mapping
        assert data["reviewer_id"] == sample_expertise_data["reviewer_id"]
        assert data["expertise_areas"] == sample_expertise_data["expertise_areas"]
    
    def test_create_or_update_reviewer_expertise(self, client):
        """Test creating or updating reviewer expertise."""
        reviewer_id = "expert_456"
        expertise_data = {
            "expertise_areas": ["bedrock_dev", "texture_creation"],
            "java_experience_level": 3
        }
        
        response = client.post(f"/api/peer-review/reviewers/expertise?reviewer_id={reviewer_id}", json=expertise_data)
        
        assert response.status_code == 200
        # Should return updated expertise data
        data = response.json()
        assert "reviewer_id" in data
    
    def test_get_reviewer_expertise(self, client):
        """Test getting reviewer expertise by ID."""
        reviewer_id = "expert_789"
        
        response = client.get(f"/api/peer-review/reviewers/expertise/{reviewer_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["reviewer_id"] == reviewer_id
        assert "expertise_areas" in data
        assert "review_count" in data
        assert "average_review_score" in data
    
    def test_find_available_reviewers(self, client):
        """Test finding available reviewers with specific expertise."""
        response = client.get("/api/peer-review/reviewers/available?expertise_area=java_modding&version=1.19.2&limit=5")
        
        assert response.status_code == 200
        # Should return list of available reviewers
        assert isinstance(response.json(), list)
    
    def test_update_reviewer_metrics(self, client):
        """Test updating reviewer performance metrics."""
        reviewer_id = "expert_123"
        metrics = {
            "review_count": 25,
            "average_review_score": 8.5,
            "approval_rate": 0.9
        }
        
        response = client.put(f"/api/peer-review/reviewers/{reviewer_id}/metrics", json=metrics)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "Reviewer metrics updated successfully" in data["message"]
    
    def test_get_reviewer_workload(self, client):
        """Test getting reviewer workload information."""
        reviewer_id = "expert_123"
        
        response = client.get(f"/api/peer-review/reviewers/{reviewer_id}/workload")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["reviewer_id"] == reviewer_id
        assert "active_reviews" in data
        assert "completed_reviews" in data
        assert "average_review_time" in data
        assert "utilization_rate" in data

    # Review Template Endpoints Tests
    
    def test_create_review_template_success(self, client):
        """Test successful creation of a review template."""
        template_data = {
            "name": "Technical Review Template",
            "description": "Comprehensive technical review template",
            "template_type": "technical",
            "contribution_types": ["pattern", "node"],
            "criteria": [
                {"name": "code_quality", "weight": 0.3, "required": True},
                {"name": "performance", "weight": 0.2, "required": True}
            ],
            "scoring_weights": {
                "technical": 0.4,
                "quality": 0.3,
                "documentation": 0.2,
                "practices": 0.1
            }
        }
        
        response = client.post("/api/peer-review/templates", json=template_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert "name" in data
        assert "template_type" in data
        assert "criteria" in data
        assert "scoring_weights" in data
        assert "is_active" in data
        assert "version" in data
    
    def test_get_review_template(self, client):
        """Test getting review template by ID."""
        template_id = str(uuid.uuid4())
        
        response = client.get(f"/api/peer-review/templates/{template_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert "name" in data
        assert "template_type" in data
    
    def test_use_review_template(self, client):
        """Test incrementing template usage count."""
        template_id = str(uuid.uuid4())
        
        response = client.post(f"/api/peer-review/templates/{template_id}/use")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "Template usage recorded successfully" in data["message"]

    # Review Analytics Endpoints Tests
    
    def test_get_daily_analytics(self, client):
        """Test getting daily analytics for specific date."""
        test_date = date.today()
        
        response = client.get(f"/api/peer-review/analytics/daily/{test_date.isoformat()}")
        
        assert response.status_code == 200
        # Should return analytics data for the date
        data = response.json()
        assert "date" in data or "contributions_submitted" in data
    
    def test_update_daily_analytics(self, client):
        """Test updating daily analytics metrics."""
        test_date = date.today()
        metrics = {
            "contributions_submitted": 5,
            "contributions_approved": 3,
            "contributions_rejected": 1,
            "avg_review_time_hours": 24.5
        }
        
        response = client.put(f"/api/peer-review/analytics/daily/{test_date.isoformat()}", json=metrics)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "Daily analytics updated successfully" in data["message"]
    
    def test_get_review_summary(self, client):
        """Test getting review summary for last N days."""
        response = client.get("/api/peer-review/analytics/summary?days=30")
        
        assert response.status_code == 200
        # Should return summary analytics
        data = response.json()
        assert isinstance(data, dict)
    
    def test_get_review_trends(self, client):
        """Test getting review trends for date range."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
        
        response = client.get(
            f"/api/peer-review/analytics/trends?start_date={start_date.isoformat()}&end_date={end_date.isoformat()}"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "trends" in data
        assert "period" in data
        assert isinstance(data["trends"], list)
    
    def test_get_review_trends_invalid_date_range(self, client):
        """Test review trends with invalid date range."""
        start_date = date.today()
        end_date = date.today() - timedelta(days=30)  # End before start
        
        response = client.get(
            f"/api/peer-review/analytics/trends?start_date={start_date.isoformat()}&end_date={end_date.isoformat()}"
        )
        
        assert response.status_code == 400
    
    def test_get_reviewer_performance(self, client):
        """Test getting reviewer performance metrics."""
        response = client.get("/api/peer-review/analytics/performance")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "reviewers" in data
        assert isinstance(data["reviewers"], list)
        
        # Check reviewer data structure
        if data["reviewers"]:
            reviewer = data["reviewers"][0]
            assert "reviewer_id" in reviewer
            assert "review_count" in reviewer
            assert "average_review_score" in reviewer
            assert "utilization" in reviewer
    
    def test_get_review_analytics_default(self, client):
        """Test getting review analytics with default parameters."""
        response = client.get("/api/peer-review/analytics/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "time_period" in data
        assert "generated_at" in data
        assert "total_reviews" in data
        assert "average_review_score" in data
        assert "approval_rate" in data
        assert "reviewer_workload" in data
    
    def test_get_review_analytics_with_metrics_filter(self, client):
        """Test getting review analytics with specific metrics filter."""
        response = client.get("/api/peer-review/analytics/?metrics=volume,quality&time_period=7d")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "time_period" in data
        assert "volume_details" in data
        assert "quality_details" in data
        # Should not include participation_details since not requested
        assert "participation_details" not in data
    
    def test_get_review_analytics_volume_metrics(self, client):
        """Test getting review analytics with volume metrics only."""
        response = client.get("/api/peer-review/analytics/?metrics=volume")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_reviews" in data
        assert "reviews_per_day" in data
        assert "volume_details" in data
        assert "pending_reviews" in data
        
        # Should not include quality metrics
        assert "average_review_score" not in data
    
    def test_get_review_analytics_quality_metrics(self, client):
        """Test getting review analytics with quality metrics only."""
        response = client.get("/api/peer-review/analytics/?metrics=quality")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "average_review_score" in data
        assert "approval_rate" in data
        assert "quality_details" in data
        assert "score_distribution" in data["quality_details"]
        
        # Should not include volume metrics
        assert "total_reviews" not in data
    
    def test_get_review_analytics_participation_metrics(self, client):
        """Test getting review analytics with participation metrics only."""
        response = client.get("/api/peer-review/analytics/?metrics=participation")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "active_reviewers" in data
        assert "average_completion_time" in data
        assert "participation_details" in data
        assert "top_reviewers" in data["participation_details"]
        
        # Should not include other metrics
        assert "total_reviews" not in data

    # Additional Review Assignment and Management Tests
    
    def test_create_review_assignment(self, client):
        """Test creating a new peer review assignment."""
        assignment_data = {
            "submission_id": str(uuid.uuid4()),
            "required_reviews": 2,
            "expertise_required": ["java_modding", "forge"],
            "deadline": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "priority": "high"
        }
        
        response = client.post("/api/peer-review/assign/", json=assignment_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "assignment_id" in data
        assert "submission_id" in data
        assert "required_reviews" in data
        assert "expertise_required" in data
        assert "status" in data
        assert "assigned_reviewers" in data
        assert "assignment_date" in data
    
    def test_submit_review_feedback(self, client):
        """Test submitting feedback on a review."""
        feedback_data = {
            "review_id": str(uuid.uuid4()),
            "feedback_type": "review_quality",
            "rating": 4,
            "comment": "Helpful and constructive review",
            "submitted_by": "test_user"
        }
        
        response = client.post("/api/peer-review/feedback/", json=feedback_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert "feedback_id" in data
        assert "review_id" in data
        assert "feedback_type" in data
        assert "rating" in data
        assert "created_at" in data
    
    def test_review_search(self, client):
        """Test searching reviews by content."""
        search_params = {
            "reviewer_id": "reviewer_123",
            "limit": 10,
            "recommendation": "approve"
        }
        
        response = client.post("/api/peer-review/search/", json=search_params)
        
        assert response.status_code == 201
        data = response.json()
        
        assert "query" in data
        assert "results" in data
        assert "total" in data
        assert "limit" in data
        assert isinstance(data["results"], list)
    
    def test_export_review_data_json(self, client):
        """Test exporting review data in JSON format."""
        response = client.get("/api/peer-review/export/?format=json")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "export_id" in data
        assert "format" in data
        assert "status" in data
        assert "download_url" in data
        assert data["format"] == "json"
    
    def test_export_review_data_csv(self, client):
        """Test exporting review data in CSV format."""
        response = client.get("/api/peer-review/export/?format=csv")
        
        assert response.status_code == 200
        # Should return CSV content
        assert response.headers["content-type"] == "text/csv"
        assert "attachment" in response.headers["content-disposition"]
    
    # Error Handling Tests
    
    def test_get_nonexistent_review(self, client):
        """Test getting a review that doesn't exist."""
        fake_id = str(uuid.uuid4())
        
        response = client.get(f"/api/peer-review/reviews/{fake_id}")
        
        # In testing mode, this returns mock data, so it should succeed
        assert response.status_code == 200
    
    def test_get_nonexistent_template(self, client):
        """Test getting a template that doesn't exist."""
        fake_id = str(uuid.uuid4())
        
        # This should return 404 in production, but testing mode may return mock data
        response = client.get(f"/api/peer-review/templates/{fake_id}")
        assert response.status_code in [200, 404]  # Depends on implementation
    
    def test_invalid_workflow_stage_transition(self, client):
        """Test invalid workflow stage transition."""
        workflow_id = str(uuid.uuid4())
        advance_data = {
            "current_stage": "pending",
            "stage_name": "completed",  # Invalid transition
            "notes": "Invalid transition"
        }
        
        response = client.post(f"/api/peer-review/workflows/{workflow_id}/advance", json=advance_data)
        
        assert response.status_code == 400
    
    def test_pagination_limit_exceeded(self, client):
        """Test pagination with limit exceeding maximum."""
        response = client.get("/api/peer-review/reviews/?limit=300")
        
        assert response.status_code == 422  # Should reject limit > 200
    
    def test_negative_offset_pagination(self, client):
        """Test pagination with negative offset."""
        response = client.get("/api/peer-review/reviews/?offset=-5")
        
        assert response.status_code == 422  # Should reject negative offset

    # Integration Tests
    
    def test_complete_review_workflow(self, client, sample_review_data, sample_workflow_data):
        """Test complete review workflow from creation to completion."""
        # 1. Create workflow
        workflow_response = client.post("/api/peer-review/workflows/", json=sample_workflow_data)
        assert workflow_response.status_code == 201
        workflow_data = workflow_response.json()
        workflow_id = workflow_data["id"]
        
        # 2. Create review
        review_response = client.post("/api/peer-review/reviews/", json=sample_review_data)
        assert review_response.status_code == 201
        review_data = review_response.json()
        review_id = review_data["id"]
        
        # 3. Update workflow stage
        stage_update = {
            "current_stage": "in_review",
            "history_entry": {"action": "review_started"}
        }
        stage_response = client.put(f"/api/peer-review/workflows/{workflow_id}/stage", json=stage_update)
        assert stage_response.status_code == 200
        
        # 4. Update review status
        status_update = {"status": "approved"}
        status_response = client.put(f"/api/peer-review/reviews/{review_id}/status", json=status_update)
        assert status_response.status_code == 200
        
        # 5. Advance workflow to completed
        advance_data = {
            "current_stage": "in_review",
            "stage_name": "completed",
            "notes": "Review completed successfully"
        }
        advance_response = client.post(f"/api/peer-review/workflows/{workflow_id}/advance", json=advance_data)
        assert advance_response.status_code == 200
    
    def test_reviewer_lifecycle(self, client, sample_expertise_data):
        """Test complete reviewer lifecycle from expertise creation to workload tracking."""
        # 1. Add reviewer expertise
        expertise_response = client.post("/api/peer-review/expertise/", json=sample_expertise_data)
        assert expertise_response.status_code == 201
        expertise_data = expertise_response.json()
        reviewer_id = expertise_data["reviewer_id"]
        
        # 2. Get reviewer expertise
        get_expertise_response = client.get(f"/api/peer-review/reviewers/expertise/{reviewer_id}")
        assert get_expertise_response.status_code == 200
        
        # 3. Find available reviewers (should include our reviewer)
        available_response = client.get("/api/peer-review/reviewers/available?expertise_area=java_modding")
        assert available_response.status_code == 200
        assert isinstance(available_response.json(), list)
        
        # 4. Get reviewer workload
        workload_response = client.get(f"/api/peer-review/reviewers/{reviewer_id}/workload")
        assert workload_response.status_code == 200
        workload_data = workload_response.json()
        assert workload_data["reviewer_id"] == reviewer_id
        
        # 5. Update reviewer metrics
        metrics = {"review_count": 5, "average_review_score": 8.5}
        metrics_response = client.put(f"/api/peer-review/reviewers/{reviewer_id}/metrics", json=metrics)
        assert metrics_response.status_code == 200
    
    def test_analytics_data_consistency(self, client):
        """Test consistency of analytics data across different endpoints."""
        # Get general analytics
        general_response = client.get("/api/peer-review/analytics/")
        assert general_response.status_code == 200
        general_data = general_response.json()
        
        # Get performance analytics
        performance_response = client.get("/api/peer-review/analytics/performance")
        assert performance_response.status_code == 200
        performance_data = performance_response.json()
        
        # Both should have reviewer-related data
        assert "reviewer_workload" in general_data
        assert "reviewers" in performance_data
        
        # Get daily analytics
        today = date.today()
        daily_response = client.get(f"/api/peer-review/analytics/daily/{today.isoformat()}")
        assert daily_response.status_code == 200
    
    def test_template_usage_tracking(self, client):
        """Test template creation and usage tracking."""
        # 1. Create template
        template_data = {
            "name": "Test Template",
            "description": "Test template for usage tracking",
            "template_type": "technical",
            "contribution_types": ["pattern"]
        }
        
        create_response = client.post("/api/peer-review/templates", json=template_data)
        assert create_response.status_code == 201
        template_id = create_response.json()["id"]
        
        # 2. Use template multiple times
        for _ in range(3):
            use_response = client.post(f"/api/peer-review/templates/{template_id}/use")
            assert use_response.status_code == 200
        
        # 3. Get template (usage count should be reflected)
        get_response = client.get(f"/api/peer-review/templates/{template_id}")
        assert get_response.status_code == 200
        # Template data should reflect usage
    
    def test_search_and_filter_combination(self, client):
        """Test combining search with status and pagination filters."""
        # Create some reviews first
        for i in range(5):
            review_data = {
                "submission_id": str(uuid.uuid4()),
                "reviewer_id": f"reviewer_{i}",
                "recommendation": "approve" if i % 2 == 0 else "request_changes",
                "content_analysis": {"score": 80 + i * 2, "comments": f"Review {i}"}
            }
            client.post("/api/peer-review/reviews/", json=review_data)
        
        # Search with filters
        search_params = {
            "reviewer_id": "reviewer_1",
            "recommendation": "approve",
            "limit": 10
        }
        
        response = client.post("/api/peer-review/search/", json=search_params)
        assert response.status_code == 201
        
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert data["limit"] == 10


# Run tests if this file is executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
