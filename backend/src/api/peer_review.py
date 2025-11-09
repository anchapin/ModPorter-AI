"""
Peer Review System API Endpoints

This module provides REST API endpoints for the peer review system,
including reviews, workflows, reviewer expertise, templates, and analytics.
"""

from typing import Dict, List, Optional, Any
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from db.base import get_db
from db.peer_review_crud import (
    PeerReviewCRUD, ReviewWorkflowCRUD, ReviewerExpertiseCRUD,
    ReviewTemplateCRUD, ReviewAnalyticsCRUD
)
from db.models import (
    PeerReview as PeerReviewModel,
    ReviewWorkflow as ReviewWorkflowModel,
    ReviewerExpertise as ReviewerExpertiseModel,
    ReviewTemplate as ReviewTemplateModel,
    ReviewAnalytics as ReviewAnalyticsModel,
    CommunityContribution as CommunityContributionModel
)

router = APIRouter()


# Peer Review Endpoints

@router.post("/reviews", response_model=PeerReviewModel)
async def create_peer_review(
    review_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Create a new peer review."""
    try:
        # Validate contribution exists
        contribution_query = select(CommunityContributionModel).where(
            CommunityContributionModel.id == review_data.get("contribution_id")
        )
        contribution_result = await db.execute(contribution_query)
        contribution = contribution_result.scalar_one_or_none()
        
        if not contribution:
            raise HTTPException(status_code=404, detail="Contribution not found")
        
        # Validate reviewer capacity
        reviewer = await ReviewerExpertiseCRUD.get_by_id(db, review_data.get("reviewer_id"))
        if reviewer and reviewer.current_reviews >= reviewer.max_concurrent_reviews:
            raise HTTPException(status_code=400, detail="Reviewer has reached maximum concurrent reviews")
        
        # Create review
        review = await PeerReviewCRUD.create(db, review_data)
        if not review:
            raise HTTPException(status_code=400, detail="Failed to create peer review")
        
        # Increment reviewer's current reviews
        if reviewer:
            await ReviewerExpertiseCRUD.increment_current_reviews(db, review.reviewer_id)
        
        # Update workflow if exists
        workflow = await ReviewWorkflowCRUD.get_by_contribution(db, review.contribution_id)
        if workflow:
            await ReviewWorkflowCRUD.increment_completed_reviews(db, workflow.id)
        
        # Add background task to process review completion
        background_tasks.add_task(process_review_completion, review.id)
        
        return review
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating peer review: {str(e)}")


@router.get("/reviews/{review_id}", response_model=PeerReviewModel)
async def get_peer_review(
    review_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get peer review by ID."""
    try:
        review = await PeerReviewCRUD.get_by_id(db, review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Peer review not found")
        return review
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting peer review: {str(e)}")


@router.get("/reviews/contribution/{contribution_id}", response_model=List[PeerReviewModel])
async def get_contribution_reviews(
    contribution_id: str,
    status: Optional[str] = Query(None, description="Filter by review status"),
    db: AsyncSession = Depends(get_db)
):
    """Get all reviews for a contribution."""
    try:
        reviews = await PeerReviewCRUD.get_by_contribution(db, contribution_id)
        if status:
            reviews = [r for r in reviews if r.status == status]
        return reviews
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting contribution reviews: {str(e)}")


@router.get("/reviews/reviewer/{reviewer_id}", response_model=List[PeerReviewModel])
async def get_reviewer_reviews(
    reviewer_id: str,
    status: Optional[str] = Query(None, description="Filter by review status"),
    db: AsyncSession = Depends(get_db)
):
    """Get reviews by reviewer."""
    try:
        return await PeerReviewCRUD.get_by_reviewer(db, reviewer_id, status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting reviewer reviews: {str(e)}")


@router.put("/reviews/{review_id}/status")
async def update_review_status(
    review_id: str,
    update_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Update review status and metrics."""
    try:
        status = update_data.get("status")
        review_data = {k: v for k, v in update_data.items() if k != "status"}
        
        success = await PeerReviewCRUD.update_status(db, review_id, status, review_data)
        
        if not success:
            raise HTTPException(status_code=404, detail="Peer review not found or update failed")
        
        # Decrement reviewer's current reviews if review is completed
        if status in ["approved", "rejected", "needs_revision"]:
            review = await PeerReviewCRUD.get_by_id(db, review_id)
            if review:
                await ReviewerExpertiseCRUD.decrement_current_reviews(db, review.reviewer_id)
                
                # Update reviewer metrics
                metrics = {
                    "review_count": ReviewerExpertiseModel.review_count + 1
                }
                if review.overall_score:
                    # Update average review score
                    current_avg = review.reviewer_expertise.average_review_score or 0
                    count = review.reviewer_expertise.review_count or 1
                    new_avg = ((current_avg * (count - 1)) + review.overall_score) / count
                    metrics["average_review_score"] = new_avg
                
                await ReviewerExpertiseCRUD.update_review_metrics(db, review.reviewer_id, metrics)
        
        # Add background task to update contribution status based on reviews
        background_tasks.add_task(update_contribution_review_status, review_id)
        
        return {"message": "Review status updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating review status: {str(e)}")


@router.get("/reviews/pending", response_model=List[PeerReviewModel])
async def get_pending_reviews(
    limit: int = Query(50, le=200, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db)
):
    """Get pending reviews."""
    try:
        return await PeerReviewCRUD.get_pending_reviews(db, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting pending reviews: {str(e)}")


# Review Workflow Endpoints

@router.post("/workflows", response_model=ReviewWorkflowModel)
async def create_review_workflow(
    workflow_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Create a new review workflow."""
    try:
        workflow = await ReviewWorkflowCRUD.create(db, workflow_data)
        if not workflow:
            raise HTTPException(status_code=400, detail="Failed to create review workflow")
        
        # Add background task to start the workflow
        background_tasks.add_task(start_review_workflow, workflow.id)
        
        return workflow
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating review workflow: {str(e)}")


@router.get("/workflows/contribution/{contribution_id}", response_model=ReviewWorkflowModel)
async def get_contribution_workflow(
    contribution_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get workflow for a contribution."""
    try:
        workflow = await ReviewWorkflowCRUD.get_by_contribution(db, contribution_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Review workflow not found")
        return workflow
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting contribution workflow: {str(e)}")


@router.put("/workflows/{workflow_id}/stage")
async def update_workflow_stage(
    workflow_id: str,
    stage_update: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Update workflow stage."""
    try:
        stage = stage_update.get("current_stage")
        history_entry = stage_update.get("history_entry", {})
        
        success = await ReviewWorkflowCRUD.update_stage(db, workflow_id, stage, history_entry)
        
        if not success:
            raise HTTPException(status_code=404, detail="Review workflow not found or update failed")
        
        return {"message": "Workflow stage updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating workflow stage: {str(e)}")


@router.get("/workflows/active", response_model=List[ReviewWorkflowModel])
async def get_active_workflows(
    limit: int = Query(100, le=500, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db)
):
    """Get active review workflows."""
    try:
        return await ReviewWorkflowCRUD.get_active_workflows(db, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting active workflows: {str(e)}")


@router.get("/workflows/overdue", response_model=List[ReviewWorkflowModel])
async def get_overdue_workflows(
    db: AsyncSession = Depends(get_db)
):
    """Get overdue workflows."""
    try:
        return await ReviewWorkflowCRUD.get_overdue_workflows(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting overdue workflows: {str(e)}")


# Reviewer Expertise Endpoints

@router.post("/reviewers/expertise")
async def create_or_update_reviewer_expertise(
    reviewer_id: str,
    expertise_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Create or update reviewer expertise."""
    try:
        reviewer = await ReviewerExpertiseCRUD.create_or_update(db, reviewer_id, expertise_data)
        if not reviewer:
            raise HTTPException(status_code=400, detail="Failed to create/update reviewer expertise")
        return reviewer
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating/updating reviewer expertise: {str(e)}")


@router.get("/reviewers/expertise/{reviewer_id}", response_model=ReviewerExpertiseModel)
async def get_reviewer_expertise(
    reviewer_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get reviewer expertise by ID."""
    try:
        reviewer = await ReviewerExpertiseCRUD.get_by_id(db, reviewer_id)
        if not reviewer:
            raise HTTPException(status_code=404, detail="Reviewer expertise not found")
        return reviewer
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting reviewer expertise: {str(e)}")


@router.get("/reviewers/available", response_model=List[ReviewerExpertiseModel])
async def find_available_reviewers(
    expertise_area: str = Query(..., description="Required expertise area"),
    version: str = Query("latest", description="Minecraft version"),
    limit: int = Query(10, le=50, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db)
):
    """Find available reviewers with specific expertise."""
    try:
        return await ReviewerExpertiseCRUD.find_available_reviewers(db, expertise_area, version, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding available reviewers: {str(e)}")


@router.put("/reviewers/{reviewer_id}/metrics")
async def update_reviewer_metrics(
    reviewer_id: str,
    metrics: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Update reviewer performance metrics."""
    try:
        success = await ReviewerExpertiseCRUD.update_review_metrics(db, reviewer_id, metrics)
        
        if not success:
            raise HTTPException(status_code=404, detail="Reviewer not found or update failed")
        
        return {"message": "Reviewer metrics updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating reviewer metrics: {str(e)}")


# Review Template Endpoints

@router.post("/templates", response_model=ReviewTemplateModel)
async def create_review_template(
    template_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Create a new review template."""
    try:
        template = await ReviewTemplateCRUD.create(db, template_data)
        if not template:
            raise HTTPException(status_code=400, detail="Failed to create review template")
        return template
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating review template: {str(e)}")


@router.get("/templates", response_model=List[ReviewTemplateModel])
async def get_review_templates(
    template_type: Optional[str] = Query(None, description="Filter by template type"),
    contribution_type: Optional[str] = Query(None, description="Filter by contribution type"),
    db: AsyncSession = Depends(get_db)
):
    """Get review templates with optional filtering."""
    try:
        if template_type:
            return await ReviewTemplateCRUD.get_by_type(db, template_type, contribution_type)
        else:
            # Get all active templates
            query = select(ReviewTemplateModel).where(
                ReviewTemplateModel.is_active
            ).order_by(desc(ReviewTemplateModel.usage_count))
            result = await db.execute(query)
            return result.scalars().all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting review templates: {str(e)}")


@router.get("/templates/{template_id}", response_model=ReviewTemplateModel)
async def get_review_template(
    template_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get review template by ID."""
    try:
        template = await ReviewTemplateCRUD.get_by_id(db, template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Review template not found")
        return template
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting review template: {str(e)}")


@router.post("/templates/{template_id}/use")
async def use_review_template(
    template_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Increment template usage count."""
    try:
        success = await ReviewTemplateCRUD.increment_usage(db, template_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Review template not found")
        
        return {"message": "Template usage recorded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recording template usage: {str(e)}")


# Review Analytics Endpoints

@router.get("/analytics/daily/{analytics_date}", response_model=ReviewAnalyticsModel)
async def get_daily_analytics(
    analytics_date: date,
    db: AsyncSession = Depends(get_db)
):
    """Get daily analytics for specific date."""
    try:
        analytics = await ReviewAnalyticsCRUD.get_or_create_daily(db, analytics_date)
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting daily analytics: {str(e)}")


@router.put("/analytics/daily/{analytics_date}")
async def update_daily_analytics(
    analytics_date: date,
    metrics: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Update daily analytics metrics."""
    try:
        success = await ReviewAnalyticsCRUD.update_daily_metrics(db, analytics_date, metrics)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to update daily analytics")
        
        return {"message": "Daily analytics updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating daily analytics: {str(e)}")


@router.get("/analytics/summary")
async def get_review_summary(
    days: int = Query(30, le=365, description="Number of days to summarize"),
    db: AsyncSession = Depends(get_db)
):
    """Get review summary for last N days."""
    try:
        return await ReviewAnalyticsCRUD.get_review_summary(db, days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting review summary: {str(e)}")


@router.get("/analytics/trends")
async def get_review_trends(
    start_date: date = Query(..., description="Start date for trends"),
    end_date: date = Query(..., description="End date for trends"),
    db: AsyncSession = Depends(get_db)
):
    """Get review trends for date range."""
    try:
        if end_date < start_date:
            raise HTTPException(status_code=400, detail="End date must be after start date")
        
        analytics_list = await ReviewAnalyticsCRUD.get_date_range(db, start_date, end_date)
        
        # Process trend data
        trend_data = []
        for analytics in analytics_list:
            trend_data.append({
                "date": analytics.date.isoformat(),
                "submitted": analytics.contributions_submitted,
                "approved": analytics.contributions_approved,
                "rejected": analytics.contributions_rejected,
                "needing_revision": analytics.contributions_needing_revision,
                "approval_rate": (analytics.contributions_approved / analytics.contributions_submitted * 100) if analytics.contributions_submitted > 0 else 0,
                "avg_review_time": analytics.avg_review_time_hours,
                "avg_review_score": analytics.avg_review_score,
                "active_reviewers": analytics.active_reviewers
            })
        
        return {
            "trends": trend_data,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": (end_date - start_date).days + 1
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting review trends: {str(e)}")


@router.get("/analytics/performance")
async def get_reviewer_performance(
    db: AsyncSession = Depends(get_db)
):
    """Get reviewer performance metrics."""
    try:
        # Get top reviewers by various metrics
        query = select(ReviewerExpertiseModel).where(
            ReviewerExpertiseModel.is_active_reviewer
        ).order_by(desc(ReviewerExpertiseModel.review_count)).limit(20)
        
        result = await db.execute(query)
        reviewers = result.scalars().all()
        
        performance_data = []
        for reviewer in reviewers:
            performance_data.append({
                "reviewer_id": reviewer.reviewer_id,
                "review_count": reviewer.review_count,
                "average_review_score": reviewer.average_review_score,
                "approval_rate": reviewer.approval_rate,
                "response_time_avg": reviewer.response_time_avg,
                "expertise_score": reviewer.expertise_score,
                "reputation_score": reviewer.reputation_score,
                "current_reviews": reviewer.current_reviews,
                "max_concurrent_reviews": reviewer.max_concurrent_reviews,
                "utilization": (reviewer.current_reviews / reviewer.max_concurrent_reviews * 100) if reviewer.max_concurrent_reviews > 0 else 0
            })
        
        return {"reviewers": performance_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting reviewer performance: {str(e)}")


# Background Tasks

async def process_review_completion(review_id: str):
    """Process review completion and update related data."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Processing review completion: {review_id}")
    
    # TODO: Implement review completion processing
    # - Update contribution status
    # - Check if all required reviews are complete
    # - Apply auto-approval/rejection logic
    # - Update analytics


async def update_contribution_review_status(review_id: str):
    """Update contribution review status based on reviews."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Updating contribution review status for review: {review_id}")
    
    # TODO: Implement contribution status updates
    # - Calculate average review scores
    # - Determine if contribution should be approved/rejected
    # - Update contribution review_status field
    # - Notify contributor


async def start_review_workflow(workflow_id: str):
    """Start the review workflow process."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Starting review workflow: {workflow_id}")
    
    # TODO: Implement workflow start process
    # - Assign reviewers based on expertise
    # - Send review requests
    # - Set deadlines and reminders
    # - Initialize workflow stages
