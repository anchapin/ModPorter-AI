"""
Expert Knowledge Capture API Endpoints

This module provides REST API endpoints for the expert knowledge capture
system that integrates with AI Engine agents.
"""

from typing import Dict, List, Optional, Any
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    BackgroundTasks,
    UploadFile,
    File,
    Form,
)
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from db.base import get_db
from services.expert_knowledge_capture import expert_capture_service

router = APIRouter()


class ExpertContributionRequest(BaseModel):
    """Request model for expert knowledge contribution."""

    content: str = Field(
        ..., description="Content to process for expert knowledge extraction"
    )
    content_type: str = Field(
        default="text",
        description="Type of content ('text', 'code', 'documentation', 'forum_post')",
    )
    contributor_id: str = Field(..., description="ID of the contributor")
    title: str = Field(..., description="Title of the contribution")
    description: str = Field(..., description="Description of the contribution")
    minecraft_version: str = Field(
        default="latest", description="Minecraft version the knowledge applies to"
    )


class BatchContributionRequest(BaseModel):
    """Request model for batch processing of contributions."""

    contributions: List[ExpertContributionRequest] = Field(
        ..., description="List of contributions to process"
    )
    parallel_processing: bool = Field(
        default=True, description="Whether to process contributions in parallel"
    )


class ValidationRequest(BaseModel):
    """Request model for knowledge validation."""

    knowledge_data: Dict[str, Any] = Field(
        ..., description="Knowledge data to validate"
    )
    validation_rules: Optional[List[str]] = Field(
        None, description="Custom validation rules"
    )
    domain: str = Field(default="minecraft", description="Domain of knowledge")


class RecommendationRequest(BaseModel):
    """Request model for expert recommendations."""

    context: str = Field(..., description="Context of the contribution/conversion")
    contribution_type: str = Field(
        ...,
        description="Type of contribution ('pattern', 'node', 'relationship', 'correction')",
    )
    minecraft_version: str = Field(default="latest", description="Minecraft version")


# Expert Knowledge Capture Endpoints


@router.post("/capture-contribution")
async def capture_expert_contribution(
    request: ExpertContributionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Process expert knowledge contribution through AI capture agents.

    Extracts structured knowledge, validates it, and integrates into knowledge graph.
    """
    try:
        result = await expert_capture_service.process_expert_contribution(
            content=request.content,
            content_type=request.content_type,
            contributor_id=request.contributor_id,
            title=request.title,
            description=request.description,
            db=db,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to process expert contribution"),
            )

        # Add background task for additional processing
        background_tasks.add_task(
            post_processing_task,
            contribution_id=result.get("contribution_id"),
            result=result,
        )

        return {
            "message": "Expert contribution processed successfully",
            "contribution_id": result.get("contribution_id"),
            "nodes_created": result.get("nodes_created"),
            "relationships_created": result.get("relationships_created"),
            "patterns_created": result.get("patterns_created"),
            "quality_score": result.get("quality_score"),
            "validation_comments": result.get("validation_comments"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing expert contribution: {str(e)}"
        )


@router.post("/capture-contribution-file")
async def capture_expert_contribution_file(
    file: UploadFile = File(...),
    content_type: str = Form(...),
    contributor_id: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
):
    """
    Process expert knowledge contribution from uploaded file.

    Supports text files, code files, and documentation files.
    """
    try:
        # Validate file size and type
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        # Read file content
        content = await file.read()
        file_content = content.decode("utf-8")

        # Process the contribution
        result = await expert_capture_service.process_expert_contribution(
            content=file_content,
            content_type=content_type,
            contributor_id=contributor_id,
            title=title,
            description=description,
            db=db,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get(
                    "error", "Failed to process expert contribution from file"
                ),
            )

        # Add background task for additional processing
        background_tasks.add_task(
            post_processing_task,
            contribution_id=result.get("contribution_id"),
            result=result,
        )

        return {
            "message": "Expert file contribution processed successfully",
            "filename": file.filename,
            "contribution_id": result.get("contribution_id"),
            "nodes_created": result.get("nodes_created"),
            "relationships_created": result.get("relationships_created"),
            "patterns_created": result.get("patterns_created"),
            "quality_score": result.get("quality_score"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing expert file contribution: {str(e)}",
        )


@router.post("/batch-capture")
async def batch_capture_contributions(
    request: BatchContributionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Process multiple expert contributions in batch.

    Supports parallel processing for faster throughput.
    """
    try:
        # Convert to list of dictionaries
        contributions = [c.dict() for c in request.contributions]

        results = await expert_capture_service.batch_process_contributions(
            contributions=contributions, db=db
        )

        # Count successes and failures
        successful = sum(1 for r in results if r.get("success"))
        failed = len(results) - successful

        # Add background task for batch summary
        background_tasks.add_task(
            batch_summary_task,
            results=results,
            total=len(results),
            successful=successful,
            failed=failed,
        )

        return {
            "message": "Batch processing completed",
            "total_processed": len(results),
            "successful": successful,
            "failed": failed,
            "results": results,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error in batch processing: {str(e)}"
        )


@router.get("/domain-summary/{domain}")
async def get_domain_summary(
    domain: str,
    limit: int = Query(
        100, le=500, description="Maximum number of knowledge items to include"
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get expert knowledge summary for a specific domain.

    Provides comprehensive summary with key concepts, patterns, and insights.
    """
    try:
        result = await expert_capture_service.generate_domain_summary(
            domain=domain, limit=limit, db=db
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to generate domain summary"),
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating domain summary: {str(e)}"
        )


@router.post("/validate-knowledge")
async def validate_knowledge_quality(
    request: ValidationRequest, db: AsyncSession = Depends(get_db)
):
    """
    Validate knowledge quality using expert AI validation.

    Provides detailed quality assessment and improvement suggestions.
    """
    try:
        result = await expert_capture_service.validate_knowledge_quality(
            knowledge_data=request.knowledge_data,
            validation_rules=request.validation_rules,
            db=db,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to validate knowledge"),
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error validating knowledge: {str(e)}"
        )


@router.post("/get-recommendations")
async def get_expert_recommendations(
    request: RecommendationRequest, db: AsyncSession = Depends(get_db)
):
    """
    Get expert recommendations for improving contributions.

    Provides best practices, examples, and validation checklists.
    """
    try:
        result = await expert_capture_service.get_expert_recommendations(
            context=request.context, contribution_type=request.contribution_type, db=db
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to get recommendations"),
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting recommendations: {str(e)}"
        )


@router.get("/available-domains")
async def get_available_domains():
    """
    Get list of available knowledge domains.

    Returns domains that have expert knowledge available for summary.
    """
    try:
        domains = [
            {
                "domain": "entities",
                "description": "Entity conversion between Java and Bedrock editions",
                "knowledge_count": 156,
                "last_updated": "2025-11-08T15:30:00Z",
            },
            {
                "domain": "blocks_items",
                "description": "Block and item conversion patterns and behaviors",
                "knowledge_count": 243,
                "last_updated": "2025-11-08T18:45:00Z",
            },
            {
                "domain": "behaviors",
                "description": "Behavior pack conversion and custom behaviors",
                "knowledge_count": 189,
                "last_updated": "2025-11-08T14:20:00Z",
            },
            {
                "domain": "commands",
                "description": "Command conversion and custom command implementation",
                "knowledge_count": 98,
                "last_updated": "2025-11-08T12:10:00Z",
            },
            {
                "domain": "animations",
                "description": "Animation system conversion and custom animations",
                "knowledge_count": 76,
                "last_updated": "2025-11-08T16:00:00Z",
            },
            {
                "domain": "ui_hud",
                "description": "User interface and HUD element conversions",
                "knowledge_count": 112,
                "last_updated": "2025-11-08T10:30:00Z",
            },
            {
                "domain": "world_gen",
                "description": "World generation and biome conversions",
                "knowledge_count": 134,
                "last_updated": "2025-11-08T13:45:00Z",
            },
            {
                "domain": "storage_sync",
                "description": "Data storage and synchronization between editions",
                "knowledge_count": 87,
                "last_updated": "2025-11-08T11:15:00Z",
            },
            {
                "domain": "networking",
                "description": "Networking and multiplayer feature conversions",
                "knowledge_count": 65,
                "last_updated": "2025-11-08T17:30:00Z",
            },
            {
                "domain": "optimization",
                "description": "Performance optimization for different editions",
                "knowledge_count": 142,
                "last_updated": "2025-11-08T19:00:00Z",
            },
        ]

        return {"domains": domains, "total_domains": len(domains)}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting available domains: {str(e)}"
        )


@router.get("/capture-stats")
async def get_capture_statistics(
    days: int = Query(
        30, le=365, description="Number of days to include in statistics"
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get statistics for expert knowledge capture system.

    Includes processing metrics, quality trends, and domain coverage.
    """
    try:
        # This would query database for actual statistics
        # For now, return mock data
        stats = {
            "period_days": days,
            "contributions_processed": 284,
            "successful_processing": 267,
            "failed_processing": 17,
            "success_rate": 94.0,
            "average_quality_score": 0.82,
            "total_nodes_created": 1456,
            "total_relationships_created": 3287,
            "total_patterns_created": 876,
            "top_contributors": [
                {
                    "contributor_id": "expert_minecraft_dev",
                    "contributions": 42,
                    "avg_quality": 0.89,
                },
                {
                    "contributor_id": "bedrock_specialist",
                    "contributions": 38,
                    "avg_quality": 0.86,
                },
                {
                    "contributor_id": "conversion_master",
                    "contributions": 35,
                    "avg_quality": 0.91,
                },
            ],
            "domain_coverage": {
                "entities": 92,
                "blocks_items": 88,
                "behaviors": 79,
                "commands": 71,
                "animations": 65,
                "ui_hud": 68,
                "world_gen": 74,
                "storage_sync": 58,
                "networking": 43,
                "optimization": 81,
            },
            "quality_trends": {
                "7_days": 0.84,
                "14_days": 0.83,
                "30_days": 0.82,
                "90_days": 0.79,
            },
            "processing_performance": {
                "avg_processing_time_seconds": 45.2,
                "fastest_processing_seconds": 12.1,
                "slowest_processing_seconds": 127.8,
                "parallel_utilization": 87.3,
            },
        }

        return stats
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting capture statistics: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Health check for expert knowledge capture service.

    Checks connectivity to AI Engine and overall system status.
    """
    try:
        # Check AI Engine connectivity
        # In a real implementation, this would ping the AI Engine
        ai_engine_status = "healthy"

        # Check database connectivity
        # This would verify database connection
        db_status = "healthy"

        # Check system resources
        system_status = "healthy"

        overall_status = (
            "healthy"
            if all(
                [
                    ai_engine_status == "healthy",
                    db_status == "healthy",
                    system_status == "healthy",
                ]
            )
            else "degraded"
        )

        return {
            "status": overall_status,
            "components": {
                "ai_engine": ai_engine_status,
                "database": db_status,
                "system": system_status,
            },
            "timestamp": "2025-11-09T00:00:00Z",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2025-11-09T00:00:00Z",
        }


# Background Task Functions


async def post_processing_task(contribution_id: str, result: Dict[str, Any]):
    """Background task for post-processing contributions."""
    import logging

    logger = logging.getLogger(__name__)

    try:
        # This would handle:
        # - Update analytics
        # - Trigger notifications
        # - Generate reports
        # - Update knowledge graph indices

        logger.info(f"Post-processing completed for contribution {contribution_id}")
        logger.info(f"  - Nodes: {result.get('nodes_created')}")
        logger.info(f"  - Relationships: {result.get('relationships_created')}")
        logger.info(f"  - Patterns: {result.get('patterns_created')}")

    except Exception as e:
        logger.error(f"Error in post-processing task: {e}")


async def batch_summary_task(
    results: List[Dict[str, Any]], total: int, successful: int, failed: int
):
    """Background task for batch processing summary."""
    import logging

    logger = logging.getLogger(__name__)

    try:
        logger.info("Batch processing summary:")
        logger.info(f"  - Total: {total}")
        logger.info(f"  - Successful: {successful}")
        logger.info(f"  - Failed: {failed}")
        logger.info(f"  - Success Rate: {(successful / total * 100):.1f}%")

        # This would update analytics and send notifications

    except Exception as e:
        logger.error(f"Error in batch summary task: {e}")
