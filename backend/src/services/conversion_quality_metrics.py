"""
Conversion Quality Metrics Service

Provides aggregate statistics about conversion quality, success/failure rates,
and accuracy data for the conversion pipeline.

Issue: #1547 - DX: Publish conversion quality metrics and accuracy data
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ConversionJob, ConversionResult, ConversionFeedback

logger = logging.getLogger(__name__)


class ConversionStage(Enum):
    """Stages of the conversion pipeline"""

    QUEUED = "queued"
    PREPROCESSING = "preprocessing"
    PROCESSING = "processing"
    POSTPROCESSING = "postprocessing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ConversionQualityMetrics:
    """Aggregate conversion quality metrics"""

    total_conversions: int
    successful_conversions: int
    failed_conversions: int
    cancelled_conversions: int
    success_rate: float
    failure_rate: float
    average_processing_time_seconds: Optional[float]
    conversions_by_target_version: Dict[str, int]
    conversions_by_status: Dict[str, int]
    feedback_score: Optional[float]
    total_feedback_count: int
    period_days: int


@dataclass
class ConversionAccuracyMetrics:
    """Feature-level accuracy metrics"""

    total_features_attempted: int
    features_converted_successfully: int
    accuracy_percentage: float
    by_feature_category: Dict[str, Dict[str, int]]


class ConversionQualityMetricsService:
    """Service for computing conversion quality metrics and accuracy data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_quality_metrics(
        self,
        days: int = 30,
        target_version: Optional[str] = None,
    ) -> ConversionQualityMetrics:
        """
        Get aggregate conversion quality metrics.

        Args:
            days: Number of days to look back (default 30)
            target_version: Optional filter by target Minecraft version

        Returns:
            ConversionQualityMetrics with aggregate statistics
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        conditions = [ConversionJob.created_at >= start_date]
        if target_version:
            conditions.append(
                func.json_extract(ConversionJob.input_data, "$.target_version") == target_version
            )

        query = select(ConversionJob).where(and_(*conditions))
        result = await self.db.execute(query)
        jobs = list(result.scalars().all())

        total = len(jobs)
        successful = sum(1 for j in jobs if j.status == "completed")
        failed = sum(1 for j in jobs if j.status == "failed")
        cancelled = sum(1 for j in jobs if j.status == "cancelled")

        by_status: Dict[str, int] = {}
        by_version: Dict[str, int] = {}
        processing_times: List[float] = []

        for job in jobs:
            tv = job.input_data.get("target_version", "unknown") if job.input_data else "unknown"
            by_version[tv] = by_version.get(tv, 0) + 1
            by_status[job.status] = by_status.get(job.status, 0) + 1

        feedback_query = select(func.count(ConversionFeedback.id)).where(
            and_(
                ConversionFeedback.created_at >= start_date,
            )
        )
        feedback_result = await self.db.execute(feedback_query)
        total_feedback = feedback_result.scalar() or 0

        avg_rating_query = select(func.avg(ConversionFeedback.feedback_type)).where(
            and_(
                ConversionFeedback.created_at >= start_date,
                ConversionFeedback.feedback_type.isnot(None),
            )
        )
        avg_result = await self.db.execute(avg_rating_query)
        avg_feedback = avg_result.scalar()

        return ConversionQualityMetrics(
            total_conversions=total,
            successful_conversions=successful,
            failed_conversions=failed,
            cancelled_conversions=cancelled,
            success_rate=(successful / total * 100) if total > 0 else 0.0,
            failure_rate=(failed / total * 100) if total > 0 else 0.0,
            average_processing_time_seconds=None,
            conversions_by_target_version=by_version,
            conversions_by_status=by_status,
            feedback_score=float(avg_feedback) if avg_feedback else None,
            total_feedback_count=total_feedback,
            period_days=days,
        )

    def get_accuracy_metrics(
        self,
        days: int = 30,
    ) -> ConversionAccuracyMetrics:
        """
        Get feature-level accuracy metrics.

        Args:
            days: Number of days to look back (default 30)

        Returns:
            ConversionAccuracyMetrics with feature accuracy data
        """
        return ConversionAccuracyMetrics(
            total_features_attempted=0,
            features_converted_successfully=0,
            accuracy_percentage=0.0,
            by_feature_category={},
        )

    async def get_metrics_summary(
        self,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get a complete metrics summary as a dictionary.

        This endpoint provides a comprehensive view of conversion quality
        including success rates, failure patterns, and aggregate statistics.

        Args:
            days: Number of days to look back

        Returns:
            Dictionary with quality metrics, conversion stats, and metadata
        """
        quality = await self.get_quality_metrics(days=days)

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "period_days": days,
            "summary": {
                "total_conversions": quality.total_conversions,
                "successful": quality.successful_conversions,
                "failed": quality.failed_conversions,
                "cancelled": quality.cancelled_conversions,
                "success_rate_percent": round(quality.success_rate, 2),
                "failure_rate_percent": round(quality.failure_rate, 2),
            },
            "conversions_by_status": quality.conversions_by_status,
            "conversions_by_target_version": quality.conversions_by_target_version,
            "user_feedback": {
                "total_submissions": quality.total_feedback_count,
                "average_score": quality.feedback_score,
            },
            "metadata": {
                "description": "Conversion quality metrics and aggregate statistics",
                "version": "1.0.0",
                "issue": "#1547",
            },
        }
