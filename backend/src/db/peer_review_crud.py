"""
Peer Review System CRUD Operations

This module provides CRUD operations for the peer review system,
including reviews, workflows, reviewer expertise, templates, and analytics.
"""

from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from db.models import (
    PeerReview as PeerReviewModel,
    ReviewWorkflow as ReviewWorkflowModel,
    ReviewerExpertise as ReviewerExpertiseModel,
    ReviewTemplate as ReviewTemplateModel,
    ReviewAnalytics as ReviewAnalyticsModel,
    CommunityContribution as CommunityContributionModel
)


class PeerReviewCRUD:
    """CRUD operations for peer reviews."""
    
    @staticmethod
    async def create(db: AsyncSession, review_data: Dict[str, Any]) -> Optional[PeerReviewModel]:
        """Create a new peer review."""
        try:
            db_review = PeerReviewModel(**review_data)
            db.add(db_review)
            await db.commit()
            await db.refresh(db_review)
            return db_review
        except Exception as e:
            await db.rollback()
            print(f"Error creating peer review: {e}")
            return None
    
    @staticmethod
    async def get_by_id(db: AsyncSession, review_id: str) -> Optional[PeerReviewModel]:
        """Get peer review by ID."""
        try:
            query = select(PeerReviewModel).where(PeerReviewModel.id == review_id)
            result = await db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"Error getting peer review: {e}")
            return None
    
    @staticmethod
    async def get_by_contribution(db: AsyncSession, contribution_id: str) -> List[PeerReviewModel]:
        """Get all reviews for a contribution."""
        try:
            query = select(PeerReviewModel).where(
                PeerReviewModel.contribution_id == contribution_id
            ).order_by(desc(PeerReviewModel.created_at))
            result = await db.execute(query)
            return result.scalars().all()
        except Exception as e:
            print(f"Error getting reviews by contribution: {e}")
            return []
    
    @staticmethod
    async def get_by_reviewer(db: AsyncSession, reviewer_id: str, status: Optional[str] = None) -> List[PeerReviewModel]:
        """Get reviews by reviewer."""
        try:
            query = select(PeerReviewModel).where(PeerReviewModel.reviewer_id == reviewer_id)
            if status:
                query = query.where(PeerReviewModel.status == status)
            query = query.order_by(desc(PeerReviewModel.created_at))
            result = await db.execute(query)
            return result.scalars().all()
        except Exception as e:
            print(f"Error getting reviews by reviewer: {e}")
            return []
    
    @staticmethod
    async def update_status(db: AsyncSession, review_id: str, status: str, review_data: Dict[str, Any]) -> bool:
        """Update review status and data."""
        try:
            query = update(PeerReviewModel).where(
                PeerReviewModel.id == review_id
            ).values(
                status=status,
                **review_data,
                updated_at=datetime.utcnow()
            )
            await db.execute(query)
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            print(f"Error updating review status: {e}")
            return False
    
    @staticmethod
    async def get_pending_reviews(db: AsyncSession, limit: int = 50) -> List[PeerReviewModel]:
        """Get pending reviews."""
        try:
            query = select(PeerReviewModel).where(
                PeerReviewModel.status == "pending"
            ).order_by(PeerReviewModel.created_at).limit(limit)
            result = await db.execute(query)
            return result.scalars().all()
        except Exception as e:
            print(f"Error getting pending reviews: {e}")
            return []
    
    @staticmethod
    async def calculate_average_score(db: AsyncSession, contribution_id: str) -> Optional[float]:
        """Calculate average review score for a contribution."""
        try:
            query = select(func.avg(PeerReviewModel.overall_score)).where(
                and_(
                    PeerReviewModel.contribution_id == contribution_id,
                    PeerReviewModel.status == "approved",
                    PeerReviewModel.overall_score.isnot(None)
                )
            )
            result = await db.execute(query)
            avg_score = result.scalar()
            return float(avg_score) if avg_score else None
        except Exception as e:
            print(f"Error calculating average score: {e}")
            return None


class ReviewWorkflowCRUD:
    """CRUD operations for review workflows."""
    
    @staticmethod
    async def create(db: AsyncSession, workflow_data: Dict[str, Any]) -> Optional[ReviewWorkflowModel]:
        """Create a new review workflow."""
        try:
            db_workflow = ReviewWorkflowModel(**workflow_data)
            db.add(db_workflow)
            await db.commit()
            await db.refresh(db_workflow)
            return db_workflow
        except Exception as e:
            await db.rollback()
            print(f"Error creating review workflow: {e}")
            return None
    
    @staticmethod
    async def get_by_contribution(db: AsyncSession, contribution_id: str) -> Optional[ReviewWorkflowModel]:
        """Get workflow for a contribution."""
        try:
            query = select(ReviewWorkflowModel).where(
                ReviewWorkflowModel.contribution_id == contribution_id
            )
            result = await db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"Error getting workflow: {e}")
            return None
    
    @staticmethod
    async def update_stage(db: AsyncSession, workflow_id: str, stage: str, history_entry: Dict[str, Any]) -> bool:
        """Update workflow stage."""
        try:
            # First get current workflow to update stage history
            current_query = select(ReviewWorkflowModel).where(ReviewWorkflowModel.id == workflow_id)
            current_result = await db.execute(current_query)
            workflow = current_result.scalar_one_or_none()
            
            if not workflow:
                return False
            
            # Update stage history
            new_history = workflow.stage_history.copy()
            new_history.append({
                "stage": workflow.current_stage,
                "timestamp": datetime.utcnow().isoformat(),
                "entry": history_entry
            })
            
            # Update workflow
            query = update(ReviewWorkflowModel).where(
                ReviewWorkflowModel.id == workflow_id
            ).values(
                current_stage=stage,
                stage_history=new_history,
                updated_at=datetime.utcnow()
            )
            await db.execute(query)
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            print(f"Error updating workflow stage: {e}")
            return False
    
    @staticmethod
    async def increment_completed_reviews(db: AsyncSession, workflow_id: str) -> bool:
        """Increment completed reviews count."""
        try:
            query = update(ReviewWorkflowModel).where(
                ReviewWorkflowModel.id == workflow_id
            ).values(
                completed_reviews=ReviewWorkflowModel.completed_reviews + 1,
                updated_at=datetime.utcnow()
            )
            await db.execute(query)
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            print(f"Error incrementing completed reviews: {e}")
            return False
    
    @staticmethod
    async def get_active_workflows(db: AsyncSession, limit: int = 100) -> List[ReviewWorkflowModel]:
        """Get active review workflows."""
        try:
            query = select(ReviewWorkflowModel).where(
                ReviewWorkflowModel.status == "active"
            ).order_by(ReviewWorkflowModel.created_at).limit(limit)
            result = await db.execute(query)
            return result.scalars().all()
        except Exception as e:
            print(f"Error getting active workflows: {e}")
            return []
    
    @staticmethod
    async def get_overdue_workflows(db: AsyncSession) -> List[ReviewWorkflowModel]:
        """Get overdue workflows."""
        try:
            deadline_time = datetime.utcnow() - timedelta(hours=48)  # 48 hours ago
            query = select(ReviewWorkflowModel).where(
                and_(
                    ReviewWorkflowModel.status == "active",
                    ReviewWorkflowModel.created_at < deadline_time
                )
            )
            result = await db.execute(query)
            return result.scalars().all()
        except Exception as e:
            print(f"Error getting overdue workflows: {e}")
            return []


class ReviewerExpertiseCRUD:
    """CRUD operations for reviewer expertise."""
    
    @staticmethod
    async def create_or_update(db: AsyncSession, reviewer_id: str, expertise_data: Dict[str, Any]) -> Optional[ReviewerExpertiseModel]:
        """Create or update reviewer expertise."""
        try:
            # Check if reviewer exists
            query = select(ReviewerExpertiseModel).where(
                ReviewerExpertiseModel.reviewer_id == reviewer_id
            )
            result = await db.execute(query)
            reviewer = result.scalar_one_or_none()
            
            if reviewer:
                # Update existing
                for key, value in expertise_data.items():
                    if hasattr(reviewer, key):
                        setattr(reviewer, key, value)
                reviewer.updated_at = datetime.utcnow()
            else:
                # Create new
                reviewer = ReviewerExpertiseModel(
                    reviewer_id=reviewer_id,
                    **expertise_data
                )
                db.add(reviewer)
            
            await db.commit()
            await db.refresh(reviewer)
            return reviewer
        except Exception as e:
            await db.rollback()
            print(f"Error creating/updating reviewer expertise: {e}")
            return None
    
    @staticmethod
    async def get_by_id(db: AsyncSession, reviewer_id: str) -> Optional[ReviewerExpertiseModel]:
        """Get reviewer expertise by ID."""
        try:
            query = select(ReviewerExpertiseModel).where(
                ReviewerExpertiseModel.reviewer_id == reviewer_id
            )
            result = await db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"Error getting reviewer expertise: {e}")
            return None
    
    @staticmethod
    async def find_available_reviewers(db: AsyncSession, expertise_area: str, version: str, limit: int = 10) -> List[ReviewerExpertiseModel]:
        """Find available reviewers with specific expertise."""
        try:
            query = select(ReviewerExpertiseModel).where(
                and_(
                    ReviewerExpertiseModel.is_active_reviewer == True,
                    ReviewerExpertiseModel.current_reviews < ReviewerExpertiseModel.max_concurrent_reviews,
                    ReviewerExpertiseModel.expertise_areas.contains([expertise_area]),
                    ReviewerExpertiseModel.minecraft_versions.contains([version])
                )
            ).order_by(
                desc(ReviewerExpertiseModel.expertise_score),
                desc(ReviewerExpertiseModel.approval_rate)
            ).limit(limit)
            
            result = await db.execute(query)
            return result.scalars().all()
        except Exception as e:
            print(f"Error finding available reviewers: {e}")
            return []
    
    @staticmethod
    async def update_review_metrics(db: AsyncSession, reviewer_id: str, metrics: Dict[str, Any]) -> bool:
        """Update reviewer performance metrics."""
        try:
            query = update(ReviewerExpertiseModel).where(
                ReviewerExpertiseModel.reviewer_id == reviewer_id
            ).values(
                **metrics,
                updated_at=datetime.utcnow(),
                last_active_date=datetime.utcnow()
            )
            await db.execute(query)
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            print(f"Error updating reviewer metrics: {e}")
            return False
    
    @staticmethod
    async def increment_current_reviews(db: AsyncSession, reviewer_id: str) -> bool:
        """Increment current reviews count for reviewer."""
        try:
            query = update(ReviewerExpertiseModel).where(
                ReviewerExpertiseModel.reviewer_id == reviewer_id
            ).values(
                current_reviews=ReviewerExpertiseModel.current_reviews + 1,
                updated_at=datetime.utcnow()
            )
            await db.execute(query)
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            print(f"Error incrementing current reviews: {e}")
            return False
    
    @staticmethod
    async def decrement_current_reviews(db: AsyncSession, reviewer_id: str) -> bool:
        """Decrement current reviews count for reviewer."""
        try:
            query = update(ReviewerExpertiseModel).where(
                ReviewerExpertiseModel.reviewer_id == reviewer_id
            ).values(
                current_reviews=func.greatest(ReviewerExpertiseModel.current_reviews - 1, 0),
                updated_at=datetime.utcnow()
            )
            await db.execute(query)
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            print(f"Error decrementing current reviews: {e}")
            return False


class ReviewTemplateCRUD:
    """CRUD operations for review templates."""
    
    @staticmethod
    async def create(db: AsyncSession, template_data: Dict[str, Any]) -> Optional[ReviewTemplateModel]:
        """Create a new review template."""
        try:
            db_template = ReviewTemplateModel(**template_data)
            db.add(db_template)
            await db.commit()
            await db.refresh(db_template)
            return db_template
        except Exception as e:
            await db.rollback()
            print(f"Error creating review template: {e}")
            return None
    
    @staticmethod
    async def get_by_type(db: AsyncSession, template_type: str, contribution_type: Optional[str] = None) -> List[ReviewTemplateModel]:
        """Get templates by type."""
        try:
            query = select(ReviewTemplateModel).where(
                and_(
                    ReviewTemplateModel.template_type == template_type,
                    ReviewTemplateModel.is_active == True
                )
            )
            
            if contribution_type:
                query = query.where(
                    ReviewTemplateModel.contribution_types.contains([contribution_type])
                )
            
            query = query.order_by(desc(ReviewTemplateModel.usage_count))
            result = await db.execute(query)
            return result.scalars().all()
        except Exception as e:
            print(f"Error getting templates by type: {e}")
            return []
    
    @staticmethod
    async def get_by_id(db: AsyncSession, template_id: str) -> Optional[ReviewTemplateModel]:
        """Get template by ID."""
        try:
            query = select(ReviewTemplateModel).where(ReviewTemplateModel.id == template_id)
            result = await db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"Error getting template: {e}")
            return None
    
    @staticmethod
    async def increment_usage(db: AsyncSession, template_id: str) -> bool:
        """Increment template usage count."""
        try:
            query = update(ReviewTemplateModel).where(
                ReviewTemplateModel.id == template_id
            ).values(
                usage_count=ReviewTemplateModel.usage_count + 1,
                updated_at=datetime.utcnow()
            )
            await db.execute(query)
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            print(f"Error incrementing template usage: {e}")
            return False


class ReviewAnalyticsCRUD:
    """CRUD operations for review analytics."""
    
    @staticmethod
    async def create_daily_analytics(db: AsyncSession, analytics_date: date, data: Dict[str, Any]) -> Optional[ReviewAnalyticsModel]:
        """Create daily analytics entry."""
        try:
            db_analytics = ReviewAnalyticsModel(
                date=analytics_date,
                **data
            )
            db.add(db_analytics)
            await db.commit()
            await db.refresh(db_analytics)
            return db_analytics
        except Exception as e:
            await db.rollback()
            print(f"Error creating daily analytics: {e}")
            return None
    
    @staticmethod
    async def get_or_create_daily(db: AsyncSession, analytics_date: date) -> ReviewAnalyticsModel:
        """Get or create daily analytics."""
        try:
            # Try to get existing
            query = select(ReviewAnalyticsModel).where(
                ReviewAnalyticsModel.date == analytics_date
            )
            result = await db.execute(query)
            analytics = result.scalar_one_or_none()
            
            if not analytics:
                # Create new with defaults
                analytics = ReviewAnalyticsModel(
                    date=analytics_date,
                    contributions_submitted=0,
                    contributions_approved=0,
                    contributions_rejected=0,
                    contributions_needing_revision=0,
                    active_reviewers=0,
                    auto_approvals=0,
                    auto_rejections=0,
                    manual_reviews=0,
                    escalation_events=0,
                    quality_score_distribution={},
                    reviewer_performance={},
                    bottlenecks=[]
                )
                db.add(analytics)
                await db.commit()
                await db.refresh(analytics)
            
            return analytics
        except Exception as e:
            print(f"Error getting/creating daily analytics: {e}")
            raise
    
    @staticmethod
    async def update_daily_metrics(db: AsyncSession, analytics_date: date, metrics: Dict[str, Any]) -> bool:
        """Update daily analytics metrics."""
        try:
            # Get or create
            analytics = await ReviewAnalyticsCRUD.get_or_create_daily(db, analytics_date)
            
            # Update with new metrics
            for key, value in metrics.items():
                if hasattr(analytics, key):
                    setattr(analytics, key, value)
            
            analytics.updated_at = datetime.utcnow()
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            print(f"Error updating daily metrics: {e}")
            return False
    
    @staticmethod
    async def get_date_range(db: AsyncSession, start_date: date, end_date: date) -> List[ReviewAnalyticsModel]:
        """Get analytics for date range."""
        try:
            query = select(ReviewAnalyticsModel).where(
                ReviewAnalyticsModel.date.between(start_date, end_date)
            ).order_by(desc(ReviewAnalyticsModel.date))
            result = await db.execute(query)
            return result.scalars().all()
        except Exception as e:
            print(f"Error getting date range analytics: {e}")
            return []
    
    @staticmethod
    async def get_review_summary(db: AsyncSession, days: int = 30) -> Dict[str, Any]:
        """Get review summary for last N days."""
        try:
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days)
            
            analytics_list = await ReviewAnalyticsCRUD.get_date_range(db, start_date, end_date)
            
            if not analytics_list:
                return {
                    "total_submitted": 0,
                    "total_approved": 0,
                    "total_rejected": 0,
                    "total_needing_revision": 0,
                    "approval_rate": 0.0,
                    "rejection_rate": 0.0,
                    "avg_review_time": 0.0,
                    "avg_review_score": 0.0,
                    "active_reviewers": 0
                }
            
            # Aggregate metrics
            total_submitted = sum(a.contributions_submitted for a in analytics_list)
            total_approved = sum(a.contributions_approved for a in analytics_list)
            total_rejected = sum(a.contributions_rejected for a in analytics_list)
            total_needing_revision = sum(a.contributions_needing_revision for a in analytics_list)
            
            avg_review_times = [a.avg_review_time_hours for a in analytics_list if a.avg_review_time_hours]
            avg_review_scores = [a.avg_review_score for a in analytics_list if a.avg_review_score]
            
            return {
                "total_submitted": total_submitted,
                "total_approved": total_approved,
                "total_rejected": total_rejected,
                "total_needing_revision": total_needing_revision,
                "approval_rate": (total_approved / total_submitted * 100) if total_submitted > 0 else 0.0,
                "rejection_rate": (total_rejected / total_submitted * 100) if total_submitted > 0 else 0.0,
                "avg_review_time": sum(avg_review_times) / len(avg_review_times) if avg_review_times else 0.0,
                "avg_review_score": sum(avg_review_scores) / len(avg_review_scores) if avg_review_scores else 0.0,
                "active_reviewers": sum(a.active_reviewers for a in analytics_list) // len(analytics_list) if analytics_list else 0
            }
        except Exception as e:
            print(f"Error getting review summary: {e}")
            return {}
