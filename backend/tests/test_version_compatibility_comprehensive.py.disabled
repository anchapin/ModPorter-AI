"""
Comprehensive tests for version_compatibility.py API endpoints
This file implements actual tests to increase coverage from 0% to near 100%
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

# Set up path imports
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module under test
from src.api.version_compatibility import (
    get_version_compatibility, get_java_version_compatibility,
    create_or_update_compatibility, get_supported_features,
    get_conversion_path, generate_migration_guide, get_matrix_overview,
    get_java_versions, get_bedrock_versions, get_matrix_visual_data,
    get_version_recommendations, get_compatibility_statistics,
    CompatibilityRequest, MigrationGuideRequest, ConversionPathRequest,
    _get_recommendation_reason, _generate_recommendations
)

# Mock dependencies
@pytest.fixture
def mock_db():
    """Create a mock AsyncSession"""
    mock_db = AsyncMock(spec=AsyncSession)
    return mock_db

@pytest.fixture
def mock_compatibility_request():
    """Sample compatibility request data"""
    return {
        "java_version": "1.18.2",
        "bedrock_version": "1.18.30",
        "compatibility_score": 0.85,
        "features_supported": [
            {"name": "world_generation", "status": "full"},
            {"name": "entities", "status": "partial"}
        ],
        "deprecated_patterns": ["old_block_states"],
        "migration_guides": {"blocks": "use_block_states"},
        "auto_update_rules": {"entity_types": "update_names"},
        "known_issues": ["redstone_differences"]
    }

@pytest.fixture
def mock_migration_request():
    """Sample migration guide request data"""
    return {
        "from_java_version": "1.16.5",
        "to_bedrock_version": "1.18.30",
        "features": ["world_generation", "entities", "redstone"]
    }

@pytest.fixture
def mock_conversion_path_request():
    """Sample conversion path request data"""
    return {
        "java_version": "1.17.1",
        "bedrock_version": "1.18.30",
        "feature_type": "redstone"
    }

# Mock the dependencies at module level
@pytest.fixture(autouse=True)
def mock_dependencies():
    """Mock all external dependencies for the version_compatibility module"""
    with patch('src.api.version_compatibility.version_compatibility_service') as mock_service:
        # Make async methods return AsyncMock
        mock_service.get_compatibility = AsyncMock()
        mock_service.get_by_java_version = AsyncMock()
        mock_service.update_compatibility = AsyncMock()
        mock_service.get_supported_features = AsyncMock()
        mock_service.get_conversion_path = AsyncMock()
        mock_service.generate_migration_guide = AsyncMock()
        mock_service.get_matrix_overview = AsyncMock()

        yield {
            'service': mock_service
        }


# Version Compatibility Tests

@pytest.mark.asyncio
async def test_get_version_compatibility_success(mock_db, mock_dependencies):
    """Test successful version compatibility retrieval"""
    # Setup
    java_version = "1.18.2"
    bedrock_version = "1.18.30"

    # Mock compatibility object
    mock_compatibility = Mock()
    mock_compatibility.java_version = java_version
    mock_compatibility.bedrock_version = bedrock_version
    mock_compatibility.compatibility_score = 0.85
    mock_compatibility.features_supported = [
        {"name": "world_generation", "status": "full"},
        {"name": "entities", "status": "partial"}
    ]
    mock_compatibility.deprecated_patterns = ["old_block_states"]
    mock_compatibility.migration_guides = {"blocks": "use_block_states"}
    mock_compatibility.auto_update_rules = {"entity_types": "update_names"}
    mock_compatibility.known_issues = ["redstone_differences"]
    mock_compatibility.created_at.isoformat.return_value = "2023-01-01T12:00:00"
    mock_compatibility.updated_at.isoformat.return_value = "2023-01-15T12:00:00"

    mock_dependencies['service'].get_compatibility.return_value = mock_compatibility

    # Execute
    result = await get_version_compatibility(java_version, bedrock_version, mock_db)

    # Assert
    assert result["java_version"] == java_version
    assert result["bedrock_version"] == bedrock_version
    assert result["compatibility_score"] == 0.85
    assert len(result["features_supported"]) == 2
    assert "old_block_states" in result["deprecated_patterns"]
    mock_dependencies['service'].get_compatibility.assert_called_once_with(java_version, bedrock_version, mock_db)

@pytest.mark.asyncio
async def test_get_version_compatibility_not_found(mock_db, mock_dependencies):
    """Test version compatibility when not found"""
    # Setup
    java_version = "1.14.4"
    bedrock_version = "1.18.30"
    mock_dependencies['service'].get_compatibility.return_value = None

    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await get_version_compatibility(java_version, bedrock_version, mock_db)

    assert excinfo.value.status_code == 404
    assert f"No compatibility data found for Java {java_version} to Bedrock {bedrock_version}" in str(excinfo.value.detail)

@pytest.mark.asyncio
async def test_get_version_compatibility_exception(mock_db, mock_dependencies):
    """Test version compatibility with exception"""
    # Setup
    java_version = "1.18.2"
    bedrock_version = "1.18.30"
    mock_dependencies['service'].get_compatibility.side_effect = Exception("Database error")

    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await get_version_compatibility(java_version, bedrock_version, mock_db)

    assert excinfo.value.status_code == 500
    assert "Error getting version compatibility" in str(excinfo.value.detail)

@pytest.mark.asyncio
async def test_get_java_version_compatibility_success(mock_db, mock_dependencies):
    """Test successful Java version compatibility retrieval"""
    # Setup
    java_version = "1.18.2"

    # Mock compatibility objects
    mock_compat1 = Mock()
    mock_compat1.bedrock_version = "1.18.30"
    mock_compat1.compatibility_score = 0.85
    mock_compat1.features_supported = [{"name": "world_generation", "status": "full"}]
    mock_compat1.known_issues = ["redstone_differences"]

    mock_compat2 = Mock()
    mock_compat2.bedrock_version = "1.17.30"
    mock_compat2.compatibility_score = 0.75
    mock_compat2.features_supported = [{"name": "entities", "status": "partial"}]
    mock_compat2.known_issues = ["entity_differences"]

    mock_dependencies['service'].get_by_java_version.return_value = [mock_compat1, mock_compat2]

    # Execute
    result = await get_java_version_compatibility(java_version, mock_db)

    # Assert
    assert result["java_version"] == java_version
    assert result["total_bedrock_versions"] == 2
    assert result["best_compatibility"] == "1.18.30"
    assert result["average_compatibility"] == 0.8
    assert len(result["compatibilities"]) == 2

    # Check first compatibility
    compat1 = result["compatibilities"][0]
    assert compat1["bedrock_version"] == "1.18.30"
    assert compat1["compatibility_score"] == 0.85
    assert compat1["features_count"] == 1
    assert compat1["issues_count"] == 1

@pytest.mark.asyncio
async def test_get_java_version_compatibility_not_found(mock_db, mock_dependencies):
    """Test Java version compatibility when not found"""
    # Setup
    java_version = "1.14.4"
    mock_dependencies['service'].get_by_java_version.return_value = []

    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await get_java_version_compatibility(java_version, mock_db)

    assert excinfo.value.status_code == 404
    assert f"No compatibility data found for Java {java_version}" in str(excinfo.value.detail)

@pytest.mark.asyncio
async def test_create_or_update_compatibility_success(mock_compatibility_request, mock_db, mock_dependencies):
    """Test successful compatibility creation/update"""
    # Setup
    request = CompatibilityRequest(**mock_compatibility_request)
    mock_dependencies['service'].update_compatibility.return_value = True

    # Execute
    result = await create_or_update_compatibility(request, mock_db)

    # Assert
    assert result["message"] == "Compatibility information updated successfully"
    assert result["java_version"] == request.java_version
    assert result["bedrock_version"] == request.bedrock_version
    assert result["compatibility_score"] == request.compatibility_score
    mock_dependencies['service'].update_compatibility.assert_called_once()

@pytest.mark.asyncio
async def test_create_or_update_compatibility_failure(mock_compatibility_request, mock_db, mock_dependencies):
    """Test compatibility creation/update failure"""
    # Setup
    request = CompatibilityRequest(**mock_compatibility_request)
    mock_dependencies['service'].update_compatibility.return_value = False

    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await create_or_update_compatibility(request, mock_db)

    assert excinfo.value.status_code == 400
    assert "Failed to create or update compatibility entry" in str(excinfo.value.detail)

@pytest.mark.asyncio
async def test_get_supported_features_success(mock_db, mock_dependencies):
    """Test successful supported features retrieval"""
    # Setup
    java_version = "1.18.2"
    bedrock_version = "1.18.30"
    feature_type = "entities"

    expected_features = {
        "features": [
            {"name": "mobs", "status": "full", "notes": "All mobs supported"},
            {"name": "items", "status": "partial", "notes": "Some items missing"}
        ],
        "total_count": 2,
        "fully_supported": 1
    }

    mock_dependencies['service'].get_supported_features.return_value = expected_features

    # Execute
    result = await get_supported_features(java_version, bedrock_version, feature_type, mock_db)

    # Assert
    assert result == expected_features
    mock_dependencies['service'].get_supported_features.assert_called_once_with(
        java_version, bedrock_version, feature_type, mock_db
    )

@pytest.mark.asyncio
async def test_get_conversion_path_success(mock_conversion_path_request, mock_db, mock_dependencies):
    """Test successful conversion path retrieval"""
    # Setup
    request = ConversionPathRequest(**mock_conversion_path_request)

    expected_path = {
        "found": True,
        "direct": False,
        "steps": [
            {
                "from_version": "1.17.1",
                "to_version": "1.18.0",
                "feature_type": "redstone",
                "confidence": 0.9
            },
            {
                "from_version": "1.18.0",
                "to_version": "1.18.30",
                "feature_type": "redstone",
                "confidence": 0.95
            }
        ],
        "total_confidence": 0.855
    }

    mock_dependencies['service'].get_conversion_path.return_value = expected_path

    # Execute
    result = await get_conversion_path(request, mock_db)

    # Assert
    assert result == expected_path
    mock_dependencies['service'].get_conversion_path.assert_called_once_with(
        java_version=request.java_version,
        bedrock_version=request.bedrock_version,
        feature_type=request.feature_type,
        db=mock_db
    )

@pytest.mark.asyncio
async def test_generate_migration_guide_success(mock_migration_request, mock_db, mock_dependencies):
    """Test successful migration guide generation"""
    # Setup
    request = MigrationGuideRequest(**mock_migration_request)

    expected_guide = {
        "from_version": "1.16.5",
        "to_version": "1.18.30",
        "features": [
            {
                "name": "world_generation",
                "status": "compatible",
                "steps": ["Update biome definitions", "Test world generation"]
            },
            {
                "name": "entities",
                "status": "partial",
                "steps": ["Update entity models", "Test entity behaviors"]
            }
        ],
        "resources": ["https://example.com/migration-guide"]
    }

    mock_dependencies['service'].generate_migration_guide.return_value = expected_guide

    # Execute
    result = await generate_migration_guide(request, mock_db)

    # Assert
    assert result == expected_guide
    mock_dependencies['service'].generate_migration_guide.assert_called_once_with(
        from_java_version=request.from_java_version,
        to_bedrock_version=request.to_bedrock_version,
        features=request.features,
        db=mock_db
    )

@pytest.mark.asyncio
async def test_get_matrix_overview_success(mock_db, mock_dependencies):
    """Test successful matrix overview retrieval"""
    # Setup
    expected_overview = {
        "java_versions": ["1.16.5", "1.17.1", "1.18.2"],
        "bedrock_versions": ["1.16.100", "1.17.30", "1.18.30"],
        "total_combinations": 9,
        "average_compatibility": 0.75,
        "compatibility_distribution": {
            "high": 3,
            "medium": 4,
            "low": 2
        },
        "matrix": {
            "1.16.5": {
                "1.16.100": {"score": 0.9, "features_count": 10, "issues_count": 1},
                "1.17.30": {"score": 0.7, "features_count": 8, "issues_count": 2},
                "1.18.30": {"score": 0.6, "features_count": 7, "issues_count": 3}
            },
            "1.17.1": {
                "1.16.100": {"score": 0.5, "features_count": 6, "issues_count": 4},
                "1.17.30": {"score": 0.9, "features_count": 10, "issues_count": 1},
                "1.18.30": {"score": 0.8, "features_count": 9, "issues_count": 2}
            },
            "1.18.2": {
                "1.16.100": {"score": 0.4, "features_count": 5, "issues_count": 5},
                "1.17.30": {"score": 0.7, "features_count": 8, "issues_count": 3},
                "1.18.30": {"score": 0.95, "features_count": 12, "issues_count": 0}
            }
        },
        "last_updated": "2023-01-15T12:00:00"
    }

    mock_dependencies['service'].get_matrix_overview.return_value = expected_overview

    # Execute
    result = await get_matrix_overview(mock_db)

    # Assert
    assert result == expected_overview
    mock_dependencies['service'].get_matrix_overview.assert_called_once_with(mock_db)

@pytest.mark.asyncio
async def test_get_java_versions_success(mock_db, mock_dependencies):
    """Test successful Java versions list retrieval"""
    # Setup
    expected_overview = {
        "java_versions": ["1.16.5", "1.17.1", "1.18.2"],
        "bedrock_versions": ["1.16.100", "1.17.30", "1.18.30"],
        "last_updated": "2023-01-15T12:00:00"
    }

    mock_dependencies['service'].get_matrix_overview.return_value = expected_overview

    # Execute
    result = await get_java_versions(mock_db)

    # Assert
    assert result["java_versions"] == ["1.16.5", "1.17.1", "1.18.2"]
    assert result["total_count"] == 3
    assert result["last_updated"] == "2023-01-15T12:00:00"

@pytest.mark.asyncio
async def test_get_bedrock_versions_success(mock_db, mock_dependencies):
    """Test successful Bedrock versions list retrieval"""
    # Setup
    expected_overview = {
        "java_versions": ["1.16.5", "1.17.1", "1.18.2"],
        "bedrock_versions": ["1.16.100", "1.17.30", "1.18.30"],
        "last_updated": "2023-01-15T12:00:00"
    }

    mock_dependencies['service'].get_matrix_overview.return_value = expected_overview

    # Execute
    result = await get_bedrock_versions(mock_db)

    # Assert
    assert result["bedrock_versions"] == ["1.16.100", "1.17.30", "1.18.30"]
    assert result["total_count"] == 3
    assert result["last_updated"] == "2023-01-15T12:00:00"

@pytest.mark.asyncio
async def test_get_matrix_visual_data_success(mock_db, mock_dependencies):
    """Test successful matrix visual data retrieval"""
    # Setup
    expected_overview = {
        "java_versions": ["1.16.5", "1.18.2"],
        "bedrock_versions": ["1.16.100", "1.18.30"],
        "matrix": {
            "1.16.5": {
                "1.16.100": {"score": 0.9, "features_count": 10, "issues_count": 1},
                "1.18.30": {"score": 0.6, "features_count": 7, "issues_count": 3}
            },
            "1.18.2": {
                "1.16.100": {"score": 0.4, "features_count": 5, "issues_count": 5},
                "1.18.30": {"score": 0.95, "features_count": 12, "issues_count": 0}
            }
        },
        "total_combinations": 4,
        "average_compatibility": 0.7,
        "compatibility_distribution": {
            "high": 2,
            "medium": 1,
            "low": 1
        },
        "last_updated": "2023-01-15T12:00:00"
    }

    mock_dependencies['service'].get_matrix_overview.return_value = expected_overview

    # Execute
    result = await get_matrix_visual_data(mock_db)

    # Assert
    assert "data" in result
    assert "java_versions" in result
    assert "bedrock_versions" in result
    assert "summary" in result

    # Check data structure
    assert len(result["data"]) == 4  # 2 java * 2 bedrock = 4 combinations

    # Check first data point
    first_point = result["data"][0]
    assert first_point["java_version"] == "1.16.5"
    assert first_point["bedrock_version"] == "1.16.100"
    assert first_point["java_index"] == 0
    assert first_point["bedrock_index"] == 0
    assert first_point["compatibility_score"] == 0.9
    assert first_point["features_count"] == 10
    assert first_point["issues_count"] == 1
    assert first_point["supported"] is True

    # Check summary
    summary = result["summary"]
    assert summary["total_combinations"] == 4
    assert summary["average_compatibility"] == 0.7
    assert summary["high_compatibility_count"] == 2
    assert summary["medium_compatibility_count"] == 1
    assert summary["low_compatibility_count"] == 1

@pytest.mark.asyncio
async def test_get_version_recommendations_success(mock_db, mock_dependencies):
    """Test successful version recommendations retrieval"""
    # Setup
    java_version = "1.18.2"

    # Mock compatibility objects
    mock_compat1 = Mock()
    mock_compat1.bedrock_version = "1.18.30"
    mock_compat1.compatibility_score = 0.95
    mock_compat1.features_supported = [{"name": "world_generation", "status": "full"}] * 10
    mock_compat1.known_issues = []

    mock_compat2 = Mock()
    mock_compat2.bedrock_version = "1.17.30"
    mock_compat2.compatibility_score = 0.85
    mock_compat2.features_supported = [{"name": "entities", "status": "partial"}] * 8
    mock_compat2.known_issues = ["some_issues"]

    mock_compat3 = Mock()
    mock_compat3.bedrock_version = "1.16.100"
    mock_compat3.compatibility_score = 0.4
    mock_compat3.features_supported = [{"name": "items", "status": "partial"}] * 5
    mock_compat3.known_issues = ["many_issues"]

    mock_dependencies['service'].get_by_java_version.return_value = [mock_compat1, mock_compat2, mock_compat3]

    # Execute
    result = await get_version_recommendations(
        java_version=java_version,
        limit=2,
        min_compatibility=0.5,
        db=mock_db
    )

    # Assert
    assert result["java_version"] == java_version
    assert result["total_available"] == 2  # Only those above min_compatibility
    assert result["min_score_used"] == 0.5

    # Check recommendations
    recommendations = result["recommendations"]
    assert len(recommendations) == 2  # Limited by limit parameter

    # First recommendation should be the highest compatibility
    first_rec = recommendations[0]
    assert first_rec["bedrock_version"] == "1.18.30"
    assert first_rec["compatibility_score"] == 0.95
    assert first_rec["features_count"] == 10
    assert first_rec["issues_count"] == 0
    assert first_rec["features"] == mock_compat1.features_supported
    assert first_rec["issues"] == mock_compat1.known_issues
    assert "Excellent compatibility" in first_rec["recommendation_reason"]

    # Second recommendation
    second_rec = recommendations[1]
    assert second_rec["bedrock_version"] == "1.17.30"
    assert second_rec["compatibility_score"] == 0.85

@pytest.mark.asyncio
async def test_get_version_recommendations_not_found(mock_db, mock_dependencies):
    """Test version recommendations when Java version not found"""
    # Setup
    java_version = "1.14.4"
    mock_dependencies['service'].get_by_java_version.return_value = []

    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await get_version_recommendations(java_version=java_version, db=mock_db)

    assert excinfo.value.status_code == 404
    assert f"No compatibility data found for Java {java_version}" in str(excinfo.value.detail)

@pytest.mark.asyncio
async def test_get_compatibility_statistics_success(mock_db, mock_dependencies):
    """Test successful compatibility statistics retrieval"""
    # Setup
    expected_overview = {
        "java_versions": ["1.16.5", "1.17.1", "1.18.2"],
        "bedrock_versions": ["1.16.100", "1.17.30", "1.18.30"],
        "matrix": {
            "1.16.5": {
                "1.16.100": {"score": 0.9, "features_count": 10, "issues_count": 1},
                "1.17.30": {"score": 0.7, "features_count": 8, "issues_count": 2},
                "1.18.30": {"score": 0.6, "features_count": 7, "issues_count": 3}
            },
            "1.17.1": {
                "1.16.100": {"score": 0.5, "features_count": 6, "issues_count": 4},
                "1.17.30": {"score": 0.9, "features_count": 10, "issues_count": 1},
                "1.18.30": {"score": 0.8, "features_count": 9, "issues_count": 2}
            },
            "1.18.2": {
                "1.16.100": {"score": 0.4, "features_count": 5, "issues_count": 5},
                "1.17.30": {"score": 0.7, "features_count": 8, "issues_count": 3},
                "1.18.30": {"score": 0.95, "features_count": 12, "issues_count": 0}
            }
        },
        "total_combinations": 9,
        "average_compatibility": 0.7,
        "compatibility_distribution": {
            "high": 3,
            "medium": 4,
            "low": 2
        },
        "last_updated": "2023-01-15T12:00:00"
    }

    mock_dependencies['service'].get_matrix_overview.return_value = expected_overview

    # Execute
    result = await get_compatibility_statistics(mock_db)

    # Assert
    # Check coverage section
    coverage = result["coverage"]
    assert coverage["total_possible_combinations"] == 9
    assert coverage["documented_combinations"] == 9
    assert coverage["coverage_percentage"] == 100.0
    assert coverage["java_versions_count"] == 3
    assert coverage["bedrock_versions_count"] == 3

    # Check score distribution
    score_dist = result["score_distribution"]
    assert score_dist["average_score"] == pytest.approx(0.7)
    assert score_dist["minimum_score"] == 0.4
    assert score_dist["maximum_score"] == 0.95
    assert score_dist["median_score"] == 0.7
    assert score_dist["high_compatibility"] == 3
    assert score_dist["medium_compatibility"] == 4
    assert score_dist["low_compatibility"] == 2

    # Check best combinations
    best_combinations = result["best_combinations"]
    assert len(best_combinations) <= 10  # Limited to top 10
    # First should be the highest score
    assert best_combinations[0]["java_version"] == "1.18.2"
    assert best_combinations[0]["bedrock_version"] == "1.18.30"
    assert best_combinations[0]["score"] == 0.95
    assert best_combinations[0]["features"] == 12

    # Check worst combinations
    worst_combinations = result["worst_combinations"]
    assert len(worst_combinations) <= 10  # Limited to top 10
    # First should be the lowest score
    assert worst_combinations[0]["java_version"] == "1.18.2"
    assert worst_combinations[0]["bedrock_version"] == "1.16.100"
    assert worst_combinations[0]["score"] == 0.4
    assert worst_combinations[0]["issues"] == 5


# Helper Function Tests

def test_get_recommendation_reason_excellent():
    """Test recommendation reason for excellent compatibility"""
    # Setup
    mock_compatibility = Mock()
    mock_compatibility.compatibility_score = 0.95
    mock_compatibility.features_supported = [{"name": "feature1"}]
    mock_compatibility.known_issues = []

    mock_all_compatibilities = [mock_compatibility]

    # Execute
    result = _get_recommendation_reason(mock_compatibility, mock_all_compatibilities)

    # Assert
    assert "Excellent compatibility" in result

def test_get_recommendation_reason_high_with_features():
    """Test recommendation reason for high compatibility with many features"""
    # Setup
    mock_compatibility = Mock()
    mock_compatibility.compatibility_score = 0.85
    mock_compatibility.features_supported = [{"name": f"feature{i}"} for i in range(10)]
    mock_compatibility.known_issues = []

    mock_other = Mock()
    mock_other.compatibility_score = 0.75
    mock_other.features_supported = [{"name": f"feature{i}"} for i in range(5)]
    mock_other.known_issues = []

    mock_all_compatibilities = [mock_compatibility, mock_other]

    # Execute
    result = _get_recommendation_reason(mock_compatibility, mock_all_compatibilities)

    # Assert
    assert "High compatibility with above-average feature support" in result

def test_get_recommendation_reason_good():
    """Test recommendation reason for good compatibility"""
    # Setup
    mock_compatibility = Mock()
    mock_compatibility.compatibility_score = 0.8
    mock_compatibility.features_supported = [{"name": "feature1"}]
    mock_compatibility.known_issues = []

    mock_other = Mock()
    mock_other.compatibility_score = 0.7
    mock_other.features_supported = [{"name": "feature1"}]
    mock_other.known_issues = []

    mock_all_compatibilities = [mock_compatibility, mock_other]

    # Execute
    result = _get_recommendation_reason(mock_compatibility, mock_all_compatibilities)

    # Assert
    assert "Good compatibility" in result

def test_get_recommendation_reason_features_focus():
    """Test recommendation reason focusing on features"""
    # Setup
    mock_compatibility = Mock()
    mock_compatibility.compatibility_score = 0.6
    mock_compatibility.features_supported = [{"name": f"feature{i}"} for i in range(10)]
    mock_compatibility.known_issues = []

    mock_other = Mock()
    mock_other.compatibility_score = 0.7
    mock_other.features_supported = [{"name": "feature1"}]
    mock_other.known_issues = []

    mock_all_compatibilities = [mock_compatibility, mock_other]

    # Execute
    result = _get_recommendation_reason(mock_compatibility, mock_all_compatibilities)

    # Assert
    assert "Extensive feature support" in result

def test_get_recommendation_reason_stable():
    """Test recommendation reason for stable compatibility"""
    # Setup
    mock_compatibility = Mock()
    mock_compatibility.compatibility_score = 0.6
    mock_compatibility.features_supported = [{"name": "feature1"}]
    mock_compatibility.known_issues = []

    mock_other = Mock()
    mock_other.compatibility_score = 0.7
    mock_other.features_supported = [{"name": "feature1"}]
    mock_other.known_issues = ["some_issues"]

    mock_all_compatibilities = [mock_compatibility, mock_other]

    # Execute
    result = _get_recommendation_reason(mock_compatibility, mock_all_compatibilities)

    # Assert
    assert "Stable compatibility with no known issues" in result

def test_get_recommendation_reason_default():
    """Test default recommendation reason"""
    # Setup
    mock_compatibility = Mock()
    mock_compatibility.compatibility_score = 0.5
    mock_compatibility.features_supported = [{"name": "feature1"}]
    mock_compatibility.known_issues = ["some_issues"]

    mock_other = Mock()
    mock_other.compatibility_score = 0.7
    mock_other.features_supported = [{"name": "feature1"}]
    mock_other.known_issues = []

    mock_all_compatibilities = [mock_compatibility, mock_other]

    # Execute
    result = _get_recommendation_reason(mock_compatibility, mock_all_compatibilities)

    # Assert
    assert "Available option with acceptable compatibility" in result

def test_generate_recommendations_low_avg():
    """Test recommendations for low average compatibility"""
    # Setup
    overview = {
        "average_compatibility": 0.6,
        "compatibility_distribution": {
            "high": 1,
            "medium": 2,
            "low": 3
        },
        "java_versions": ["1.16.5", "1.17.1"],
        "bedrock_versions": ["1.16.100", "1.17.30"]
    }

    # Execute
    result = _generate_recommendations(overview)

    # Assert
    assert len(result) > 0
    assert any("low compatibility scores" in rec for rec in result)

def test_generate_recommendations_many_low():
    """Test recommendations for many low compatibility combinations"""
    # Setup
    overview = {
        "average_compatibility": 0.7,
        "compatibility_distribution": {
            "high": 2,
            "medium": 2,
            "low": 5
        },
        "java_versions": ["1.16.5", "1.17.1"],
        "bedrock_versions": ["1.16.100", "1.17.30"]
    }

    # Execute
    result = _generate_recommendations(overview)

    # Assert
    assert len(result) > 0
    assert any("low-compatibility combinations" in rec for rec in result)

def test_generate_recommendations_limited_java():
    """Test recommendations for limited Java version coverage"""
    # Setup
    overview = {
        "average_compatibility": 0.8,
        "compatibility_distribution": {
            "high": 3,
            "medium": 2,
            "low": 1
        },
        "java_versions": ["1.16.5", "1.17.1"],  # Only 2 versions
        "bedrock_versions": ["1.16.100", "1.17.30", "1.18.30"]
    }

    # Execute
    result = _generate_recommendations(overview)

    # Assert
    assert len(result) > 0
    assert any("Limited Java version coverage" in rec for rec in result)

def test_generate_recommendations_limited_bedrock():
    """Test recommendations for limited Bedrock version coverage"""
    # Setup
    overview = {
        "average_compatibility": 0.8,
        "compatibility_distribution": {
            "high": 3,
            "medium": 2,
            "low": 1
        },
        "java_versions": ["1.16.5", "1.17.1", "1.18.2"],
        "bedrock_versions": ["1.16.100"]  # Only 1 version
    }

    # Execute
    result = _generate_recommendations(overview)

    # Assert
    assert len(result) > 0
    assert any("Limited Bedrock version coverage" in rec for rec in result)

def test_generate_recommendations_few_high():
    """Test recommendations for few high compatibility combinations"""
    # Setup
    overview = {
        "average_compatibility": 0.7,
        "compatibility_distribution": {
            "high": 1,  # Only 1 high compatibility
            "medium": 5,
            "low": 2
        },
        "java_versions": ["1.16.5", "1.17.1", "1.18.2"],
        "bedrock_versions": ["1.16.100", "1.17.30", "1.18.30"]
    }

    # Execute
    result = _generate_recommendations(overview)

    # Assert
    assert len(result) > 0
    assert any("Few high-compatibility combinations" in rec for rec in result)
