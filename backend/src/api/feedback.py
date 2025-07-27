"""
Feedback API endpoints for conversion job feedback and AI training data.
"""

import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from db.base import get_db
from db import crud

router = APIRouter()


class FeedbackRequest(BaseModel):
    job_id: str
    feedback_type: str  # 'thumbs_up', 'thumbs_down', 'detailed'
    user_id: Optional[str] = None
    comment: Optional[str] = None
    # Enhanced feedback fields for RL training
    quality_rating: Optional[int] = None  # 1-5 scale
    specific_issues: Optional[List[str]] = None  # List of specific problems
    suggested_improvements: Optional[str] = None
    conversion_accuracy: Optional[int] = None  # 1-5 scale
    visual_quality: Optional[int] = None  # 1-5 scale
    performance_rating: Optional[int] = None  # 1-5 scale
    ease_of_use: Optional[int] = None  # 1-5 scale
    agent_specific_feedback: Optional[Dict[str, Any]] = None  # Agent-specific ratings


class FeedbackResponse(BaseModel):
    id: str
    job_id: str
    feedback_type: str
    user_id: Optional[str] = None
    comment: Optional[str] = None
    quality_rating: Optional[int] = None
    specific_issues: Optional[List[str]] = None
    suggested_improvements: Optional[str] = None
    conversion_accuracy: Optional[int] = None
    visual_quality: Optional[int] = None
    performance_rating: Optional[int] = None
    ease_of_use: Optional[int] = None
    agent_specific_feedback: Optional[Dict[str, Any]] = None
    created_at: str


class TrainingDataResponse(BaseModel):
    """Enhanced training data response with quality metrics"""
    job_id: str
    input_file_path: str
    output_file_path: str
    feedback: Dict[str, Any]
    quality_metrics: Optional[Dict[str, Any]] = None
    conversion_metadata: Optional[Dict[str, Any]] = None
    agent_performance_data: Optional[Dict[str, Any]] = None


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackRequest,
    db: AsyncSession = Depends(get_db)
):
    """Submit feedback for a conversion job."""
    try:
        job_uuid = uuid.UUID(feedback.job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    # Check if job exists
    job = await crud.get_job(db, feedback.job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Conversion job with ID '{feedback.job_id}' not found"
        )
    
    # Create enhanced feedback with RL training data
    db_feedback = await crud.create_enhanced_feedback(
        db,
        job_id=job_uuid,
        feedback_type=feedback.feedback_type,
        user_id=feedback.user_id,
        comment=feedback.comment,
        quality_rating=feedback.quality_rating,
        specific_issues=feedback.specific_issues,
        suggested_improvements=feedback.suggested_improvements,
        conversion_accuracy=feedback.conversion_accuracy,
        visual_quality=feedback.visual_quality,
        performance_rating=feedback.performance_rating,
        ease_of_use=feedback.ease_of_use,
        agent_specific_feedback=feedback.agent_specific_feedback
    )
    
    return FeedbackResponse(
        id=str(db_feedback.id),
        job_id=str(db_feedback.job_id),
        feedback_type=db_feedback.feedback_type,
        user_id=db_feedback.user_id,
        comment=db_feedback.comment,
        quality_rating=db_feedback.quality_rating,
        specific_issues=db_feedback.specific_issues,
        suggested_improvements=db_feedback.suggested_improvements,
        conversion_accuracy=db_feedback.conversion_accuracy,
        visual_quality=db_feedback.visual_quality,
        performance_rating=db_feedback.performance_rating,
        ease_of_use=db_feedback.ease_of_use,
        agent_specific_feedback=db_feedback.agent_specific_feedback,
        created_at=db_feedback.created_at.isoformat()
    )


@router.get("/ai/training_data")
async def get_training_data(
    skip: int = 0,
    limit: int = 100,
    include_quality_metrics: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Get enhanced feedback data for RL training."""
    feedback_list = await crud.list_all_feedback(db, skip=skip, limit=limit)
    
    training_data = []
    for feedback in feedback_list:
        # Get job details for file paths
        job = await crud.get_job(db, str(feedback.job_id))
        
        feedback_dict = {
            "id": str(feedback.id),
            "job_id": str(feedback.job_id),
            "input_file_path": job.input_data.get("file_path", "") if job else "",
            "output_file_path": f"conversion_outputs/{feedback.job_id}_converted.mcaddon" if job else "",
            "feedback": {
                "feedback_type": feedback.feedback_type,
                "user_id": feedback.user_id,
                "comment": feedback.comment,
                "quality_rating": getattr(feedback, 'quality_rating', None),
                "specific_issues": getattr(feedback, 'specific_issues', None),
                "suggested_improvements": getattr(feedback, 'suggested_improvements', None),
                "conversion_accuracy": getattr(feedback, 'conversion_accuracy', None),
                "visual_quality": getattr(feedback, 'visual_quality', None),
                "performance_rating": getattr(feedback, 'performance_rating', None),
                "ease_of_use": getattr(feedback, 'ease_of_use', None),
                "agent_specific_feedback": getattr(feedback, 'agent_specific_feedback', None),
                "created_at": feedback.created_at.isoformat()
            }
        }
        
        # Add conversion metadata if available
        if job:
            feedback_dict["conversion_metadata"] = {
                "job_id": str(job.id),
                "status": job.status,
                "processing_time_seconds": 30.0,  # Could be calculated from timestamps
                "target_version": job.input_data.get("target_version", "1.20.0"),
                "created_at": job.created_at.isoformat(),
                "updated_at": job.updated_at.isoformat()
            }
        
        training_data.append(feedback_dict)
    
    return {
        "data": training_data,
        "total": len(training_data),
        "skip": skip,
        "limit": limit
    }


@router.post("/ai/training/trigger")
async def trigger_rl_training():
    """Manually trigger RL training cycle."""
    try:
        # Import and run training manager
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ai-engine', 'src'))
        
        from training_manager import fetch_training_data_from_backend, train_model_with_feedback
        
        # Fetch training data
        backend_url = os.getenv("MODPORTER_BACKEND_URL", "http://localhost:8000")
        training_data = await fetch_training_data_from_backend(backend_url, skip=0, limit=50)
        
        if training_data:
            # Run RL training
            result = await train_model_with_feedback(training_data)
            return {
                "status": "success",
                "message": "RL training completed successfully",
                "training_result": result
            }
        else:
            return {
                "status": "warning",
                "message": "No training data available for RL training"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"RL training failed: {str(e)}"
        }


@router.get("/ai/performance/agents")
async def get_agent_performance():
    """Get performance metrics for all AI agents."""
    try:
        # Import RL components
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ai-engine', 'src'))
        
        from rl.agent_optimizer import create_agent_optimizer
        
        optimizer = create_agent_optimizer()
        system_metrics = optimizer.get_system_wide_metrics()
        
        return {
            "status": "success",
            "metrics": system_metrics
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get agent performance: {str(e)}"
        }


@router.get("/ai/performance/agents/{agent_type}")
async def get_specific_agent_performance(agent_type: str):
    """Get detailed performance metrics for a specific agent type."""
    try:
        # Import RL components
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ai-engine', 'src'))
        
        from rl.agent_optimizer import create_agent_optimizer
        
        optimizer = create_agent_optimizer()
        
        # Check if we have performance history for this agent
        if agent_type in optimizer.performance_history and optimizer.performance_history[agent_type]:
            latest_metrics = optimizer.performance_history[agent_type][-1]
            return {
                "status": "success",
                "agent_type": agent_type,
                "metrics": latest_metrics.__dict__
            }
        else:
            return {
                "status": "warning",
                "message": f"No performance data available for agent type: {agent_type}"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get agent performance: {str(e)}"
        }


@router.post("/ai/performance/compare")
async def compare_agent_performance(agent_types: List[str]):
    """Compare performance between multiple agent types."""
    try:
        # Import RL components
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ai-engine', 'src'))
        
        from rl.agent_optimizer import create_agent_optimizer
        
        optimizer = create_agent_optimizer()
        comparison_report = optimizer.compare_agents(agent_types)
        
        return {
            "status": "success",
            "comparison_report": comparison_report.__dict__
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to compare agents: {str(e)}"
        }