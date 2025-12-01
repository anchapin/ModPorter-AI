"""
Analytics and reporting API endpoints.

This module provides endpoints for:
- Feedback analytics and metrics
- User engagement analytics
- Quality metrics and trend analysis
- Community health indicators
- Automated report generation
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from db import get_async_session
from services.feedback_analytics_service import (
    FeedbackAnalyticsService,
    AnalyticsTimeRange,
    ReportType,
)
from security.auth import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models for request/response
class TimeRangeRequest(BaseModel):
    time_range: str = Field(
        ...,
        description="Time range: today, 7d, 30d, 90d, this_month, last_month, this_quarter, this_year",
    )


class TrendAnalysisRequest(BaseModel):
    metric: str = Field(
        ...,
        description="Metric to analyze: feedback_volume, quality_score, user_engagement",
    )
    time_range: str = Field(
        ...,
        description="Time range: today, 7d, 30d, 90d, this_month, last_month, this_quarter, this_year",
    )


class TopContributorsRequest(BaseModel):
    time_range: str = Field("30d", description="Time range for analysis")
    limit: int = Field(20, ge=1, le=100, description="Number of contributors to return")
    metric: str = Field(
        "reputation",
        description="Sorting metric: reputation, feedback_volume, helpfulness",
    )


class ReportGenerationRequest(BaseModel):
    report_type: str = Field(
        ...,
        description="Report type: community_health, feedback_analysis, user_engagement, quality_metrics, reputation_analysis, trend_analysis, performance_summary",
    )
    time_range: str = Field("30d", description="Time range for the report")
    format_type: str = Field("json", description="Output format: json, csv, pdf")
    filters: Optional[Dict[str, Any]] = Field(
        None, description="Optional filters for the report"
    )


class FeedbackOverviewResponse(BaseModel):
    time_range: str
    period: Dict[str, str]
    summary: Dict[str, Any]
    feedback_by_type: Dict[str, int]
    feedback_by_status: Dict[str, int]
    engagement_rate: float


class UserEngagementResponse(BaseModel):
    time_range: str
    period: Dict[str, str]
    submission_metrics: Dict[str, Any]
    voting_metrics: Dict[str, Any]
    user_activity: Dict[str, Any]
    retention_metrics: Dict[str, Any]


class QualityAnalysisResponse(BaseModel):
    time_range: str
    period: Dict[str, str]
    summary: Dict[str, Any]
    grade_distribution: Dict[str, int]
    common_issues: Dict[str, int]
    automation_metrics: Dict[str, Any]


class TrendAnalysisResponse(BaseModel):
    metric: str
    time_range: str
    period: Dict[str, str]
    daily_data: List[Dict[str, Any]]
    trend_analysis: Dict[str, Any]
    insights: List[str]


class ContributorEntry(BaseModel):
    user_id: str
    username: str
    score: Optional[float] = None
    feedback_count: Optional[int] = None
    metric_type: str
    # Additional fields based on metric type
    level: Optional[str] = None
    average_quality: Optional[float] = None
    total_helpful: Optional[int] = None
    helpfulness_ratio: Optional[float] = None


class ReportResponse(BaseModel):
    report_type: str
    time_range: str
    generated_at: str
    filters: Dict[str, Any]
    data: Dict[str, Any]


def parse_time_range(time_range_str: str) -> AnalyticsTimeRange:
    """Parse time range string to enum."""
    try:
        return AnalyticsTimeRange(time_range_str)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid time range: {time_range_str}. Valid options: {[range.value for range in AnalyticsTimeRange]}",
        )


def parse_report_type(report_type_str: str) -> ReportType:
    """Parse report type string to enum."""
    try:
        return ReportType(report_type_str)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid report type: {report_type_str}. Valid options: {[rt.value for rt in ReportType]}",
        )


@router.get("/analytics/feedback-overview", response_model=FeedbackOverviewResponse)
async def get_feedback_overview(
    time_range: str = Query("7d", description="Time range for analysis"),
    current_user=Depends(get_current_user),
    db=Depends(get_async_session),
):
    """Get high-level feedback overview metrics."""
    try:
        analytics_service = FeedbackAnalyticsService(db)
        time_range_enum = parse_time_range(time_range)

        overview = await analytics_service.get_feedback_overview(time_range_enum)

        return FeedbackOverviewResponse(**overview)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting feedback overview: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve feedback overview"
        )


@router.get("/analytics/user-engagement", response_model=UserEngagementResponse)
async def get_user_engagement(
    time_range: str = Query("30d", description="Time range for analysis"),
    current_user=Depends(get_current_user),
    db=Depends(get_async_session),
):
    """Get detailed user engagement metrics."""
    try:
        analytics_service = FeedbackAnalyticsService(db)
        time_range_enum = parse_time_range(time_range)

        engagement = await analytics_service.get_user_engagement_metrics(
            time_range_enum
        )

        return UserEngagementResponse(**engagement)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user engagement metrics: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve user engagement metrics"
        )


@router.get("/analytics/quality-analysis", response_model=QualityAnalysisResponse)
async def get_quality_analysis(
    time_range: str = Query("30d", description="Time range for analysis"),
    current_user=Depends(get_current_user),
    db=Depends(get_async_session),
):
    """Get comprehensive quality analysis metrics."""
    try:
        analytics_service = FeedbackAnalyticsService(db)
        time_range_enum = parse_time_range(time_range)

        quality = await analytics_service.get_quality_analysis(time_range_enum)

        return QualityAnalysisResponse(**quality)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting quality analysis: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve quality analysis"
        )


@router.post("/analytics/trend-analysis", response_model=TrendAnalysisResponse)
async def get_trend_analysis(
    request: TrendAnalysisRequest,
    current_user=Depends(get_current_user),
    db=Depends(get_async_session),
):
    """Get trend analysis for specific metrics."""
    try:
        if request.metric not in [
            "feedback_volume",
            "quality_score",
            "user_engagement",
        ]:
            raise HTTPException(
                status_code=400,
                detail="Invalid metric. Valid options: feedback_volume, quality_score, user_engagement",
            )

        analytics_service = FeedbackAnalyticsService(db)
        time_range_enum = parse_time_range(request.time_range)

        trend_data = await analytics_service.get_trend_analysis(
            request.metric, time_range_enum
        )

        return TrendAnalysisResponse(**trend_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trend analysis: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve trend analysis")


@router.post("/analytics/top-contributors", response_model=List[ContributorEntry])
async def get_top_contributors(
    request: TopContributorsRequest,
    current_user=Depends(get_current_user),
    db=Depends(get_async_session),
):
    """Get top contributors based on various metrics."""
    try:
        if request.metric not in ["reputation", "feedback_volume", "helpfulness"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid metric. Valid options: reputation, feedback_volume, helpfulness",
            )

        analytics_service = FeedbackAnalyticsService(db)
        time_range_enum = parse_time_range(request.time_range)

        contributors = await analytics_service.get_top_contributors(
            time_range_enum, request.limit, request.metric
        )

        return [ContributorEntry(**contributor) for contributor in contributors]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting top contributors: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve top contributors"
        )


@router.post("/analytics/reports/generate", response_model=ReportResponse)
async def generate_report(
    request: ReportGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db=Depends(get_async_session),
):
    """Generate comprehensive reports."""
    try:
        if request.format_type not in ["json", "csv", "pdf"]:
            raise HTTPException(
                status_code=400, detail="Invalid format. Valid options: json, csv, pdf"
            )

        analytics_service = FeedbackAnalyticsService(db)
        time_range_enum = parse_time_range(request.time_range)
        report_type_enum = parse_report_type(request.report_type)

        # Generate report data
        report_data = await analytics_service.generate_report(
            report_type_enum, time_range_enum, request.format_type, request.filters
        )

        # If non-JSON format is requested, add background task to convert
        if request.format_type != "json":
            background_tasks.add_task(
                _convert_report_format,
                report_data,
                request.format_type,
                current_user.id,
            )
            report_data["conversion_status"] = "processing"

        return ReportResponse(
            report_type=report_data["report_type"],
            time_range=report_data["time_range"],
            generated_at=report_data["generated_at"],
            filters=report_data.get("filters", {}),
            data=report_data,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate report")


@router.get("/analytics/dashboard")
async def get_dashboard_data(
    time_range: str = Query("7d", description="Time range for dashboard data"),
    current_user=Depends(get_current_user),
    db=Depends(get_async_session),
):
    """Get comprehensive dashboard data with multiple metrics."""
    try:
        analytics_service = FeedbackAnalyticsService(db)
        time_range_enum = parse_time_range(time_range)

        # Run multiple analytics queries in parallel
        dashboard_tasks = [
            analytics_service.get_feedback_overview(time_range_enum),
            analytics_service.get_user_engagement_metrics(time_range_enum),
            analytics_service.get_quality_analysis(time_range_enum),
            analytics_service.get_trend_analysis("feedback_volume", time_range_enum),
            analytics_service.get_top_contributors(time_range_enum, 10, "reputation"),
        ]

        results = await asyncio.gather(*dashboard_tasks, return_exceptions=True)

        dashboard_data = {
            "time_range": time_range,
            "generated_at": datetime.utcnow().isoformat(),
            "overview": results[0] if not isinstance(results[0], Exception) else None,
            "engagement": results[1] if not isinstance(results[1], Exception) else None,
            "quality": results[2] if not isinstance(results[2], Exception) else None,
            "trends": results[3] if not isinstance(results[3], Exception) else None,
            "top_contributors": results[4]
            if not isinstance(results[4], Exception)
            else None,
        }

        # Calculate health score if we have the necessary data
        if dashboard_data["overview"] and dashboard_data["engagement"]:
            health_score = analytics_service._calculate_health_score(
                dashboard_data["overview"], dashboard_data["engagement"]
            )
            dashboard_data["health_score"] = health_score

        return dashboard_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dashboard data: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard data")


@router.get("/analytics/insights")
async def get_analytics_insights(
    time_range: str = Query("7d", description="Time range for insights"),
    current_user=Depends(get_current_user),
    db=Depends(get_async_session),
):
    """Get AI-powered insights and recommendations."""
    try:
        analytics_service = FeedbackAnalyticsService(db)
        time_range_enum = parse_time_range(time_range)

        insights = {
            "time_range": time_range,
            "generated_at": datetime.utcnow().isoformat(),
            "insights": [],
            "recommendations": [],
            "alerts": [],
        }

        # Get trend data for analysis
        feedback_trends = await analytics_service.get_trend_analysis(
            "feedback_volume", time_range_enum
        )
        quality_trends = await analytics_service.get_trend_analysis(
            "quality_score", time_range_enum
        )
        engagement_trends = await analytics_service.get_trend_analysis(
            "user_engagement", time_range_enum
        )

        # Generate insights from trends
        for trend_data in [feedback_trends, quality_trends, engagement_trends]:
            if trend_data.get("insights"):
                insights["insights"].extend(trend_data["insights"])

        # Generate recommendations based on data
        overview = await analytics_service.get_feedback_overview(time_range_enum)
        engagement = await analytics_service.get_user_engagement_metrics(
            time_range_enum
        )

        # Engagement recommendations
        if overview.get("engagement_rate", 0) < 10:
            insights["recommendations"].append(
                "Low engagement rate detected. Consider implementing gamification features or improving feedback visibility."
            )

        # Quality recommendations
        if (
            quality_trends.get("trend_analysis", {}).get("trend_direction")
            == "decreasing"
        ):
            insights["recommendations"].append(
                "Quality scores are declining. Review quality control measures and provide better feedback guidelines."
            )

        # Retention alerts
        retention_rate = engagement.get("retention_metrics", {}).get(
            "retention_rate", 0
        )
        if retention_rate < 25:
            insights["alerts"].append(
                f"Low user retention rate ({retention_rate:.1f}%). Focus on improving user experience and follow-up engagement."
            )

        # Volume alerts
        if (
            feedback_trends.get("trend_analysis", {}).get("trend_direction")
            == "decreasing"
        ):
            insights["alerts"].append(
                "Feedback volume is decreasing. Investigate potential causes and consider outreach campaigns."
            )

        return insights

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analytics insights: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve analytics insights"
        )


async def _convert_report_format(
    report_data: Dict[str, Any], format_type: str, user_id: str
) -> None:
    """
    Background task to convert report data to different formats.

    This would typically involve generating CSV files or PDF reports.
    For now, it's a placeholder that logs the conversion request.
    """
    try:
        logger.info(
            f"Converting report {report_data.get('report_type')} "
            f"to {format_type} format for user {user_id}"
        )

        # In a real implementation, this would:
        # - Generate CSV files using pandas or csv module
        # - Generate PDF reports using libraries like ReportLab or WeasyPrint
        # - Save files to storage and update the database with file paths

    except Exception as e:
        logger.error(f"Error converting report format: {str(e)}")


# Import asyncio for parallel execution
import asyncio
