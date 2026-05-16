"""
Conversion Quality Metrics API Endpoint

Provides aggregate conversion quality metrics and accuracy data.

Issue: #1547 - DX: Publish conversion quality metrics and accuracy data
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from services.conversion_quality_metrics import (
    ConversionQualityMetricsService,
    ConversionQualityMetrics,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class ConversionQualityResponse(BaseModel):
    """Response model for conversion quality metrics."""

    total_conversions: int
    successful_conversions: int
    failed_conversions: int
    cancelled_conversions: int
    success_rate: float
    failure_rate: float
    average_processing_time_seconds: Optional[float]
    conversions_by_target_version: dict
    conversions_by_status: dict
    feedback_score: Optional[float]
    total_feedback_count: int
    period_days: int

    model_config = ConfigDict(from_attributes=True)


class ConversionMetricsSummaryResponse(BaseModel):
    """Response model for complete metrics summary."""

    generated_at: str
    period_days: int
    summary: dict
    conversions_by_status: dict
    conversions_by_target_version: dict
    user_feedback: dict
    metadata: dict


class AccuracyMetricsResponse(BaseModel):
    """Response model for accuracy metrics."""

    total_features_attempted: int
    features_converted_successfully: int
    accuracy_percentage: float
    by_feature_category: dict

    model_config = ConfigDict(from_attributes=True)


@router.get(
    "/quality",
    response_model=ConversionQualityResponse,
    summary="Get conversion quality metrics",
    description="Returns aggregate statistics about conversion success/failure rates, "
    "conversions by status, and user feedback scores for a specified time period.",
)
async def get_conversion_quality_metrics(
    days: int = Query(
        default=30,
        ge=1,
        le=365,
        description="Number of days to look back for metrics (1-365)",
    ),
    target_version: Optional[str] = Query(
        default=None,
        description="Filter metrics by target Minecraft version (e.g., '1.20.0')",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get aggregate conversion quality metrics.

    Provides a comprehensive view of conversion quality including:
    - Total conversions and breakdown by status
    - Success and failure rates
    - Conversions grouped by target version
    - User feedback statistics
    """
    try:
        service = ConversionQualityMetricsService(db)
        metrics = await service.get_quality_metrics(days=days, target_version=target_version)

        return ConversionQualityResponse(
            total_conversions=metrics.total_conversions,
            successful_conversions=metrics.successful_conversions,
            failed_conversions=metrics.failed_conversions,
            cancelled_conversions=metrics.cancelled_conversions,
            success_rate=round(metrics.success_rate, 2),
            failure_rate=round(metrics.failure_rate, 2),
            average_processing_time_seconds=metrics.average_processing_time_seconds,
            conversions_by_target_version=metrics.conversions_by_target_version,
            conversions_by_status=metrics.conversions_by_status,
            feedback_score=metrics.feedback_score,
            total_feedback_count=metrics.total_feedback_count,
            period_days=metrics.period_days,
        )

    except Exception as e:
        logger.error(f"Failed to get conversion quality metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve conversion quality metrics. Please try again.",
        )


@router.get(
    "/summary",
    response_model=ConversionMetricsSummaryResponse,
    summary="Get complete metrics summary",
    description="Returns a comprehensive summary of conversion quality metrics including "
    "all aggregate statistics in a single response.",
)
async def get_metrics_summary(
    days: int = Query(
        default=30,
        ge=1,
        le=365,
        description="Number of days to look back for metrics (1-365)",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a complete metrics summary.

    Returns all quality metrics in a single response with:
    - Summary statistics (totals, rates)
    - Breakdown by status and target version
    - User feedback data
    - Metadata about the metrics
    """
    try:
        service = ConversionQualityMetricsService(db)
        summary = await service.get_metrics_summary(days=days)

        return ConversionMetricsSummaryResponse(**summary)

    except Exception as e:
        logger.error(f"Failed to get metrics summary: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve metrics summary. Please try again.",
        )


@router.get(
    "/accuracy",
    response_model=AccuracyMetricsResponse,
    summary="Get conversion accuracy metrics",
    description="Returns feature-level accuracy data showing what percentage "
    "of features convert correctly.",
)
async def get_accuracy_metrics(
    days: int = Query(
        default=30,
        ge=1,
        le=365,
        description="Number of days to look back for metrics (1-365)",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get feature-level accuracy metrics.

    Returns accuracy data showing conversion precision:
    - Total features attempted
    - Features converted successfully
    - Accuracy percentage
    - Breakdown by feature category
    """
    try:
        service = ConversionQualityMetricsService(db)
        accuracy = service.get_accuracy_metrics(days=days)

        return AccuracyMetricsResponse(
            total_features_attempted=accuracy.total_features_attempted,
            features_converted_successfully=accuracy.features_converted_successfully,
            accuracy_percentage=round(accuracy.accuracy_percentage, 2),
            by_feature_category=accuracy.by_feature_category,
        )

    except Exception as e:
        logger.error(f"Failed to get accuracy metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve accuracy metrics. Please try again.",
        )
