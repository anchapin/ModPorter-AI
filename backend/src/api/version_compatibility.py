"""
Version Compatibility Matrix API Endpoints

This module provides REST API endpoints for the version compatibility matrix
system that manages Java and Bedrock edition version relationships.
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from unittest.mock import Mock

try:
    from db.base import get_db
    from services.version_compatibility import version_compatibility_service
except ImportError:
    # Mock imports if they fail
    get_db = Mock()
    version_compatibility_service = Mock()

router = APIRouter()


class CompatibilityRequest(BaseModel):
    """Request model for creating/updating compatibility data."""
    java_version: str = Field(..., description="Minecraft Java edition version")
    bedrock_version: str = Field(..., description="Minecraft Bedrock edition version")
    compatibility_score: float = Field(..., ge=0.0, le=1.0, description="Compatibility score (0.0-1.0)")
    features_supported: List[Dict[str, Any]] = Field(default_factory=list, description="List of supported features")
    deprecated_patterns: List[str] = Field(default_factory=list, description="Deprecated patterns between versions")
    migration_guides: Dict[str, Any] = Field(default_factory=dict, description="Migration guide information")
    auto_update_rules: Dict[str, Any] = Field(default_factory=dict, description="Rules for automatic updates")
    known_issues: List[str] = Field(default_factory=list, description="Known issues between versions")


class MigrationGuideRequest(BaseModel):
    """Request model for generating migration guide."""
    from_java_version: str = Field(..., description="Source Java edition version")
    to_bedrock_version: str = Field(..., description="Target Bedrock edition version")
    features: List[str] = Field(..., description="List of features to migrate")


class ConversionPathRequest(BaseModel):
    """Request model for finding conversion path."""
    java_version: str = Field(..., description="Source Java edition version")
    bedrock_version: str = Field(..., description="Target Bedrock edition version")
    feature_type: str = Field(..., description="Type of feature to convert")


# Version Compatibility Endpoints

@router.get("/compatibility/{java_version}/{bedrock_version}")
async def get_version_compatibility(
    java_version: str = Path(..., description="Minecraft Java edition version"),
    bedrock_version: str = Path(..., description="Minecraft Bedrock edition version"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get compatibility information between specific Java and Bedrock versions.

    Returns detailed compatibility data including supported features, patterns, and known issues.
    """
    try:
        compatibility = await version_compatibility_service.get_compatibility(
            java_version, bedrock_version, db
        )

        if not compatibility:
            raise HTTPException(
                status_code=404,
                detail=f"No compatibility data found for Java {java_version} to Bedrock {bedrock_version}"
            )

        return {
            "java_version": compatibility.java_version,
            "bedrock_version": compatibility.bedrock_version,
            "compatibility_score": compatibility.compatibility_score,
            "features_supported": compatibility.features_supported,
            "deprecated_patterns": compatibility.deprecated_patterns,
            "migration_guides": compatibility.migration_guides,
            "auto_update_rules": compatibility.auto_update_rules,
            "known_issues": compatibility.known_issues,
            "created_at": compatibility.created_at.isoformat(),
            "updated_at": compatibility.updated_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting version compatibility: {str(e)}"
        )


@router.get("/compatibility/java/{java_version}")
async def get_java_version_compatibility(
    java_version: str = Path(..., description="Minecraft Java edition version"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all compatibility entries for a specific Java version.

    Returns compatibility with all available Bedrock versions.
    """
    try:
        compatibilities = await version_compatibility_service.get_by_java_version(
            java_version, db
        )

        if not compatibilities:
            raise HTTPException(
                status_code=404,
                detail=f"No compatibility data found for Java {java_version}"
            )

        return {
            "java_version": java_version,
            "total_bedrock_versions": len(compatibilities),
            "compatibilities": [
                {
                    "bedrock_version": c.bedrock_version,
                    "compatibility_score": c.compatibility_score,
                    "features_count": len(c.features_supported),
                    "issues_count": len(c.known_issues)
                }
                for c in compatibilities
            ],
            "best_compatibility": max(compatibilities, key=lambda x: x.compatibility_score).bedrock_version if compatibilities else None,
            "average_compatibility": sum(c.compatibility_score for c in compatibilities) / len(compatibilities) if compatibilities else 0.0
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting Java version compatibility: {str(e)}"
        )


@router.post("/compatibility")
async def create_or_update_compatibility(
    request: CompatibilityRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create or update compatibility information between versions.

    Allows adding new compatibility data or updating existing entries.
    """
    try:
        success = await version_compatibility_service.update_compatibility(
            java_version=request.java_version,
            bedrock_version=request.bedrock_version,
            compatibility_data={
                "compatibility_score": request.compatibility_score,
                "features_supported": request.features_supported,
                "deprecated_patterns": request.deprecated_patterns,
                "migration_guides": request.migration_guides,
                "auto_update_rules": request.auto_update_rules,
                "known_issues": request.known_issues
            },
            db=db
        )

        if not success:
            raise HTTPException(
                status_code=400,
                detail="Failed to create or update compatibility entry"
            )

        return {
            "message": "Compatibility information updated successfully",
            "java_version": request.java_version,
            "bedrock_version": request.bedrock_version,
            "compatibility_score": request.compatibility_score
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating compatibility: {str(e)}"
        )


@router.get("/features/{java_version}/{bedrock_version}")
async def get_supported_features(
    java_version: str = Path(..., description="Minecraft Java edition version"),
    bedrock_version: str = Path(..., description="Minecraft Bedrock edition version"),
    feature_type: Optional[str] = Query(None, description="Filter by specific feature type"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get features supported between specific Java and Bedrock versions.

    Returns detailed feature information with conversion patterns and best practices.
    """
    try:
        features_data = await version_compatibility_service.get_supported_features(
            java_version, bedrock_version, feature_type, db
        )

        return features_data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting supported features: {str(e)}"
        )


@router.post("/conversion-path")
async def get_conversion_path(
    request: ConversionPathRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Find optimal conversion path between versions for specific feature type.

    Returns direct or intermediate-step conversion paths with compatibility scores.
    """
    try:
        path_data = await version_compatibility_service.get_conversion_path(
            java_version=request.java_version,
            bedrock_version=request.bedrock_version,
            feature_type=request.feature_type,
            db=db
        )

        return path_data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error finding conversion path: {str(e)}"
        )


@router.post("/migration-guide")
async def generate_migration_guide(
    request: MigrationGuideRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate detailed migration guide for specific versions and features.

    Provides step-by-step instructions, best practices, and resource links.
    """
    try:
        guide = await version_compatibility_service.generate_migration_guide(
            from_java_version=request.from_java_version,
            to_bedrock_version=request.to_bedrock_version,
            features=request.features,
            db=db
        )

        return guide
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating migration guide: {str(e)}"
        )


@router.get("/matrix/overview")
async def get_matrix_overview(
    db: AsyncSession = Depends(get_db)
):
    """
    Get overview of the complete version compatibility matrix.

    Returns statistics, version lists, and compatibility scores matrix.
    """
    try:
        overview = await version_compatibility_service.get_matrix_overview(db)
        return overview
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting matrix overview: {str(e)}"
        )


@router.get("/java-versions")
async def get_java_versions(
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of all Java versions in the compatibility matrix.

    Returns sorted list with release information if available.
    """
    try:
        overview = await version_compatibility_service.get_matrix_overview(db)
        return {
            "java_versions": overview.get("java_versions", []),
            "total_count": len(overview.get("java_versions", [])),
            "last_updated": overview.get("last_updated")
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting Java versions: {str(e)}"
        )


@router.get("/bedrock-versions")
async def get_bedrock_versions(
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of all Bedrock versions in the compatibility matrix.

    Returns sorted list with release information if available.
    """
    try:
        overview = await version_compatibility_service.get_matrix_overview(db)
        return {
            "bedrock_versions": overview.get("bedrock_versions", []),
            "total_count": len(overview.get("bedrock_versions", [])),
            "last_updated": overview.get("last_updated")
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting Bedrock versions: {str(e)}"
        )


@router.get("/matrix/visual")
async def get_matrix_visual_data(
    db: AsyncSession = Depends(get_db)
):
    """
    Get compatibility matrix data formatted for visualization.

    Returns data ready for heatmap or network visualization.
    """
    try:
        overview = await version_compatibility_service.get_matrix_overview(db)
        matrix = overview.get("matrix", {})
        java_versions = overview.get("java_versions", [])
        bedrock_versions = overview.get("bedrock_versions", [])

        # Convert to visualization format
        visual_data = []
        for jv_idx, java_version in enumerate(java_versions):
            for bv_idx, bedrock_version in enumerate(bedrock_versions):
                compatibility = matrix.get(java_version, {}).get(bedrock_version)

                visual_data.append({
                    "java_version": java_version,
                    "bedrock_version": bedrock_version,
                    "java_index": jv_idx,
                    "bedrock_index": bv_idx,
                    "compatibility_score": compatibility.get("score") if compatibility else None,
                    "features_count": compatibility.get("features_count") if compatibility else None,
                    "issues_count": compatibility.get("issues_count") if compatibility else None,
                    "supported": compatibility is not None
                })

        return {
            "data": visual_data,
            "java_versions": java_versions,
            "bedrock_versions": bedrock_versions,
            "summary": {
                "total_combinations": overview.get("total_combinations", 0),
                "average_compatibility": overview.get("average_compatibility", 0.0),
                "high_compatibility_count": overview.get("compatibility_distribution", {}).get("high", 0),
                "medium_compatibility_count": overview.get("compatibility_distribution", {}).get("medium", 0),
                "low_compatibility_count": overview.get("compatibility_distribution", {}).get("low", 0)
            },
            "last_updated": overview.get("last_updated")
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting matrix visual data: {str(e)}"
        )


@router.get("/recommendations/{java_version}")
async def get_version_recommendations(
    java_version: str = Path(..., description="Minecraft Java edition version"),
    limit: int = Query(5, le=10, description="Maximum number of recommendations"),
    min_compatibility: float = Query(0.5, ge=0.0, le=1.0, description="Minimum compatibility score"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recommended Bedrock versions for a specific Java version.

    Returns sorted recommendations with compatibility scores and feature support.
    """
    try:
        compatibilities = await version_compatibility_service.get_by_java_version(
            java_version, db
        )

        if not compatibilities:
            raise HTTPException(
                status_code=404,
                detail=f"No compatibility data found for Java {java_version}"
            )

        # Filter and sort by compatibility score
        filtered_compatibilities = [
            c for c in compatibilities
            if c.compatibility_score >= min_compatibility
        ]

        # Sort by compatibility score (descending), then by feature count
        sorted_compatibilities = sorted(
            filtered_compatibilities,
            key=lambda x: (x.compatibility_score, len(x.features_supported)),
            reverse=True
        )

        # Take top recommendations
        recommendations = sorted_compatibilities[:limit]

        return {
            "java_version": java_version,
            "recommendations": [
                {
                    "bedrock_version": c.bedrock_version,
                    "compatibility_score": c.compatibility_score,
                    "features_count": len(c.features_supported),
                    "issues_count": len(c.known_issues),
                    "features": c.features_supported,
                    "issues": c.known_issues,
                    "recommendation_reason": _get_recommendation_reason(c, compatibilities)
                }
                for c in recommendations
            ],
            "total_available": len(filtered_compatibilities),
            "min_score_used": min_compatibility
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting version recommendations: {str(e)}"
        )


@router.get("/statistics")
async def get_compatibility_statistics(
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive statistics for the compatibility matrix.

    Returns detailed metrics, trends, and analysis data.
    """
    try:
        overview = await version_compatibility_service.get_matrix_overview(db)

        # Calculate additional statistics
        java_versions = overview.get("java_versions", [])
        bedrock_versions = overview.get("bedrock_versions", [])
        matrix = overview.get("matrix", {})

        # Version statistics
        total_combinations = len(java_versions) * len(bedrock_versions)
        documented_combinations = overview.get("total_combinations", 0)
        coverage_percentage = (documented_combinations / total_combinations * 100) if total_combinations > 0 else 0.0

        # Score distribution
        scores = []
        for java_v in java_versions:
            for bedrock_v in bedrock_versions:
                compat = matrix.get(java_v, {}).get(bedrock_v)
                if compat and compat.get("score") is not None:
                    scores.append(compat["score"])

        score_stats = {
            "average": sum(scores) / len(scores) if scores else 0.0,
            "minimum": min(scores) if scores else 0.0,
            "maximum": max(scores) if scores else 0.0,
            "median": sorted(scores)[len(scores) // 2] if scores else 0.0
        }

        # Best and worst combinations
        best_combinations = []
        worst_combinations = []

        for java_v in java_versions:
            for bedrock_v in bedrock_versions:
                compat = matrix.get(java_v, {}).get(bedrock_v)
                if compat and compat.get("score") is not None:
                    score = compat["score"]
                    if score >= 0.8:
                        best_combinations.append({
                            "java_version": java_v,
                            "bedrock_version": bedrock_v,
                            "score": score,
                            "features": compat.get("features_count", 0)
                        })
                    elif score < 0.5:
                        worst_combinations.append({
                            "java_version": java_v,
                            "bedrock_version": bedrock_v,
                            "score": score,
                            "issues": compat.get("issues_count", 0)
                        })

        # Sort best/worst combinations
        best_combinations.sort(key=lambda x: (x["score"], x["features"]), reverse=True)
        worst_combinations.sort(key=lambda x: x["score"])

        return {
            "coverage": {
                "total_possible_combinations": total_combinations,
                "documented_combinations": documented_combinations,
                "coverage_percentage": coverage_percentage,
                "java_versions_count": len(java_versions),
                "bedrock_versions_count": len(bedrock_versions)
            },
            "score_distribution": {
                "average_score": score_stats["average"],
                "minimum_score": score_stats["minimum"],
                "maximum_score": score_stats["maximum"],
                "median_score": score_stats["median"],
                "high_compatibility": overview.get("compatibility_distribution", {}).get("high", 0),
                "medium_compatibility": overview.get("compatibility_distribution", {}).get("medium", 0),
                "low_compatibility": overview.get("compatibility_distribution", {}).get("low", 0)
            },
            "best_combinations": best_combinations[:10],  # Top 10 best
            "worst_combinations": worst_combinations[:10],  # Top 10 worst
            "recommendations": _generate_recommendations(overview),
            "last_updated": overview.get("last_updated")
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting compatibility statistics: {str(e)}"
        )


# Helper Methods

def _get_recommendation_reason(
    compatibility,
    all_compatibilities
) -> str:
    """Generate recommendation reason for compatibility entry."""
    score = compatibility.compatibility_score
    features_count = len(compatibility.features_supported)
    issues_count = len(compatibility.known_issues)

    # Compare with average
    avg_score = sum(c.compatibility_score for c in all_compatibilities) / len(all_compatibilities)
    avg_features = sum(len(c.features_supported) for c in all_compatibilities) / len(all_compatibilities)

    if score >= 0.9:
        return "Excellent compatibility with full feature support"
    elif score >= 0.8 and features_count >= avg_features:
        return "High compatibility with above-average feature support"
    elif score >= avg_score:
        return "Good compatibility, meets average standards"
    elif features_count > avg_features * 1.2:
        return "Extensive feature support despite moderate compatibility"
    elif issues_count == 0:
        return "Stable compatibility with no known issues"
    else:
        return "Available option with acceptable compatibility"


def _generate_recommendations(overview: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on matrix overview."""
    recommendations = []

    avg_score = overview.get("average_compatibility", 0.0)
    distribution = overview.get("compatibility_distribution", {})
    java_versions = overview.get("java_versions", [])
    bedrock_versions = overview.get("bedrock_versions", [])

    if avg_score < 0.7:
        recommendations.append("Overall compatibility scores are low. Consider focusing on improving conversion patterns.")

    if distribution.get("low", 0) > distribution.get("high", 0):
        recommendations.append("Many low-compatibility combinations. Prioritize improving problematic conversions.")

    if len(java_versions) < 5:
        recommendations.append("Limited Java version coverage. Add more recent Java versions to the matrix.")

    if len(bedrock_versions) < 5:
        recommendations.append("Limited Bedrock version coverage. Add more recent Bedrock versions to the matrix.")

    high_compat = distribution.get("high", 0)
    total = high_compat + distribution.get("medium", 0) + distribution.get("low", 0)
    if total > 0 and (high_compat / total) < 0.3:
        recommendations.append("Few high-compatibility combinations. Focus on proven conversion patterns.")

    return recommendations


# Add helper methods to module namespace
version_compatibility_api = {
    "_get_recommendation_reason": _get_recommendation_reason,
    "_generate_recommendations": _generate_recommendations
}
