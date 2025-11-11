"""
Comprehensive tests for version_compatibility.py API module.
Tests all version compatibility matrix endpoints and business logic.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Dict, Any

from backend.src.api.version_compatibility import (
    router,
    CompatibilityRequest,
    MigrationGuideRequest,
    ConversionPathRequest,
    get_version_compatibility,
    get_java_version_compatibility,
    create_or_update_compatibility,
    get_supported_features,
    get_conversion_path,
    generate_migration_guide,
    get_matrix_overview,
    get_java_versions,
    get_bedrock_versions,
    get_matrix_visual_data,
    get_version_recommendations,
    get_compatibility_statistics,
    _get_recommendation_reason,
    _generate_recommendations,
    version_compatibility_api
)


class TestCompatibilityRequest:
    """Test CompatibilityRequest Pydantic model."""
    
    def test_minimal_request(self):
        """Test CompatibilityRequest with minimal required fields."""
        request = CompatibilityRequest(
            java_version="1.19.0",
            bedrock_version="1.19.50",
            compatibility_score=0.85
        )
        
        assert request.java_version == "1.19.0"
        assert request.bedrock_version == "1.19.50"
        assert request.compatibility_score == 0.85
        assert request.features_supported == []
        assert request.deprecated_patterns == []
        assert request.migration_guides == {}
        assert request.auto_update_rules == {}
        assert request.known_issues == []
    
    def test_full_request(self):
        """Test CompatibilityRequest with all fields."""
        request = CompatibilityRequest(
            java_version="1.18.2",
            bedrock_version="1.18.30",
            compatibility_score=0.75,
            features_supported=[{"name": "blocks", "supported": True}],
            deprecated_patterns=["old_redstone"],
            migration_guides={"overview": "guide"},
            auto_update_rules={"pattern": "auto"},
            known_issues=["issue1", "issue2"]
        )
        
        assert request.features_supported == [{"name": "blocks", "supported": True}]
        assert request.deprecated_patterns == ["old_redstone"]
        assert request.migration_guides == {"overview": "guide"}
        assert request.auto_update_rules == {"pattern": "auto"}
        assert request.known_issues == ["issue1", "issue2"]
    
    def test_compatibility_score_validation(self):
        """Test compatibility_score field validation."""
        # Valid scores
        valid_scores = [0.0, 0.5, 1.0]
        for score in valid_scores:
            request = CompatibilityRequest(
                java_version="1.19.0",
                bedrock_version="1.19.50",
                compatibility_score=score
            )
            assert request.compatibility_score == score
        
        # Invalid scores
        invalid_scores = [-0.1, 1.1]
        for score in invalid_scores:
            with pytest.raises(ValueError):
                CompatibilityRequest(
                    java_version="1.19.0",
                    bedrock_version="1.19.50",
                    compatibility_score=score
                )


class TestMigrationGuideRequest:
    """Test MigrationGuideRequest Pydantic model."""
    
    def test_request_creation(self):
        """Test MigrationGuideRequest creation."""
        request = MigrationGuideRequest(
            from_java_version="1.18.2",
            to_bedrock_version="1.18.30",
            features=["blocks", "entities", "redstone"]
        )
        
        assert request.from_java_version == "1.18.2"
        assert request.to_bedrock_version == "1.18.30"
        assert request.features == ["blocks", "entities", "redstone"]


class TestConversionPathRequest:
    """Test ConversionPathRequest Pydantic model."""
    
    def test_request_creation(self):
        """Test ConversionPathRequest creation."""
        request = ConversionPathRequest(
            java_version="1.19.0",
            bedrock_version="1.19.50",
            feature_type="blocks"
        )
        
        assert request.java_version == "1.19.0"
        assert request.bedrock_version == "1.19.50"
        assert request.feature_type == "blocks"


class TestVersionCompatibilityEndpoints:
    """Test version compatibility API endpoints."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def mock_compatibility_service(self):
        """Create mock version compatibility service."""
        service = AsyncMock()
        return service
    
    @pytest.fixture
    def sample_compatibility(self):
        """Create sample compatibility data."""
        compatibility = MagicMock()
        compatibility.java_version = "1.19.0"
        compatibility.bedrock_version = "1.19.50"
        compatibility.compatibility_score = 0.85
        compatibility.features_supported = [{"name": "blocks", "supported": True}]
        compatibility.deprecated_patterns = ["old_pattern"]
        compatibility.migration_guides = {"overview": "test guide"}
        compatibility.auto_update_rules = {"auto": True}
        compatibility.known_issues = ["minor issue"]
        compatibility.created_at = datetime.now()
        compatibility.updated_at = datetime.now()
        return compatibility
    
    @pytest.mark.asyncio
    async def test_get_version_compatibility_success(
        self, mock_db, mock_compatibility_service, sample_compatibility
    ):
        """Test successful version compatibility retrieval."""
        with patch('backend.src.api.version_compatibility.version_compatibility_service', mock_compatibility_service):
            mock_compatibility_service.get_compatibility.return_value = sample_compatibility
            
            response = await get_version_compatibility(
                java_version="1.19.0",
                bedrock_version="1.19.50",
                db=mock_db
            )
            
            assert response["java_version"] == "1.19.0"
            assert response["bedrock_version"] == "1.19.50"
            assert response["compatibility_score"] == 0.85
            assert "created_at" in response
            assert "updated_at" in response
            
            mock_compatibility_service.get_compatibility.assert_called_once_with(
                "1.19.0", "1.19.50", mock_db
            )
    
    @pytest.mark.asyncio
    async def test_get_version_compatibility_not_found(
        self, mock_db, mock_compatibility_service
    ):
        """Test version compatibility retrieval when not found."""
        with patch('backend.src.api.version_compatibility.version_compatibility_service', mock_compatibility_service):
            mock_compatibility_service.get_compatibility.return_value = None
            
            with pytest.raises(HTTPException) as exc_info:
                await get_version_compatibility(
                    java_version="1.19.0",
                    bedrock_version="1.19.50",
                    db=mock_db
                )
            
            assert exc_info.value.status_code == 404
            assert "No compatibility data found" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_version_compatibility_error(
        self, mock_db, mock_compatibility_service
    ):
        """Test version compatibility retrieval with error."""
        with patch('backend.src.api.version_compatibility.version_compatibility_service', mock_compatibility_service):
            mock_compatibility_service.get_compatibility.side_effect = Exception("Database error")
            
            with pytest.raises(HTTPException) as exc_info:
                await get_version_compatibility(
                    java_version="1.19.0",
                    bedrock_version="1.19.50",
                    db=mock_db
                )
            
            assert exc_info.value.status_code == 500
            assert "Error getting version compatibility" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_java_version_compatibility_success(
        self, mock_db, mock_compatibility_service, sample_compatibility
    ):
        """Test successful Java version compatibility retrieval."""
        with patch('backend.src.api.version_compatibility.version_compatibility_service', mock_compatibility_service):
            mock_compatibility_service.get_by_java_version.return_value = [sample_compatibility]
            
            response = await get_java_version_compatibility(
                java_version="1.19.0",
                db=mock_db
            )
            
            assert response["java_version"] == "1.19.0"
            assert response["total_bedrock_versions"] == 1
            assert len(response["compatibilities"]) == 1
            assert response["best_compatibility"] == "1.19.50"
            assert response["average_compatibility"] == 0.85
            
            mock_compatibility_service.get_by_java_version.assert_called_once_with(
                "1.19.0", mock_db
            )
    
    @pytest.mark.asyncio
    async def test_get_java_version_compatibility_empty(
        self, mock_db, mock_compatibility_service
    ):
        """Test Java version compatibility retrieval with no data."""
        with patch('backend.src.api.version_compatibility.version_compatibility_service', mock_compatibility_service):
            mock_compatibility_service.get_by_java_version.return_value = []
            
            with pytest.raises(HTTPException) as exc_info:
                await get_java_version_compatibility(
                    java_version="1.19.0",
                    db=mock_db
                )
            
            assert exc_info.value.status_code == 404
            assert "No compatibility data found" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_create_or_update_compatibility_success(
        self, mock_db, mock_compatibility_service
    ):
        """Test successful compatibility creation/update."""
        with patch('backend.src.api.version_compatibility.version_compatibility_service', mock_compatibility_service):
            mock_compatibility_service.update_compatibility.return_value = True
            
            request = CompatibilityRequest(
                java_version="1.19.0",
                bedrock_version="1.19.50",
                compatibility_score=0.85
            )
            
            response = await create_or_update_compatibility(
                request=request,
                db=mock_db
            )
            
            assert response["message"] == "Compatibility information updated successfully"
            assert response["java_version"] == "1.19.0"
            assert response["bedrock_version"] == "1.19.50"
            assert response["compatibility_score"] == 0.85
            
            mock_compatibility_service.update_compatibility.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_or_update_compatibility_failure(
        self, mock_db, mock_compatibility_service
    ):
        """Test compatibility creation/update failure."""
        with patch('backend.src.api.version_compatibility.version_compatibility_service', mock_compatibility_service):
            mock_compatibility_service.update_compatibility.return_value = False
            
            request = CompatibilityRequest(
                java_version="1.19.0",
                bedrock_version="1.19.50",
                compatibility_score=0.85
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await create_or_update_compatibility(
                    request=request,
                    db=mock_db
                )
            
            assert exc_info.value.status_code == 400
            assert "Failed to create or update compatibility" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_supported_features_success(
        self, mock_db, mock_compatibility_service
    ):
        """Test successful supported features retrieval."""
        with patch('backend.src.api.version_compatibility.version_compatibility_service', mock_compatibility_service):
            expected_features = {
                "features": [
                    {"name": "blocks", "supported": True},
                    {"name": "entities", "supported": False}
                ],
                "total_count": 10,
                "supported_count": 8
            }
            mock_compatibility_service.get_supported_features.return_value = expected_features
            
            response = await get_supported_features(
                java_version="1.19.0",
                bedrock_version="1.19.50",
                feature_type="blocks",
                db=mock_db
            )
            
            assert response == expected_features
            mock_compatibility_service.get_supported_features.assert_called_once_with(
                "1.19.0", "1.19.50", "blocks", mock_db
            )
    
    @pytest.mark.asyncio
    async def test_get_conversion_path_success(
        self, mock_db, mock_compatibility_service
    ):
        """Test successful conversion path retrieval."""
        with patch('backend.src.api.version_compatibility.version_compatibility_service', mock_compatibility_service):
            expected_path = {
                "path": ["1.19.0", "1.19.50"],
                "compatibility_scores": [0.85],
                "recommendations": ["Direct conversion recommended"]
            }
            mock_compatibility_service.get_conversion_path.return_value = expected_path
            
            request = ConversionPathRequest(
                java_version="1.19.0",
                bedrock_version="1.19.50",
                feature_type="blocks"
            )
            
            response = await get_conversion_path(
                request=request,
                db=mock_db
            )
            
            assert response == expected_path
            mock_compatibility_service.get_conversion_path.assert_called_once_with(
                java_version="1.19.0",
                bedrock_version="1.19.50",
                feature_type="blocks",
                db=mock_db
            )
    
    @pytest.mark.asyncio
    async def test_generate_migration_guide_success(
        self, mock_db, mock_compatibility_service
    ):
        """Test successful migration guide generation."""
        with patch('backend.src.api.version_compatibility.version_compatibility_service', mock_compatibility_service):
            expected_guide = {
                "steps": [
                    {"step": 1, "description": "Backup world"},
                    {"step": 2, "description": "Convert blocks"}
                ],
                "resources": ["https://example.com/guide"],
                "estimated_time": "2 hours"
            }
            mock_compatibility_service.generate_migration_guide.return_value = expected_guide
            
            request = MigrationGuideRequest(
                from_java_version="1.18.2",
                to_bedrock_version="1.18.30",
                features=["blocks", "entities"]
            )
            
            response = await generate_migration_guide(
                request=request,
                db=mock_db
            )
            
            assert response == expected_guide
            mock_compatibility_service.generate_migration_guide.assert_called_once_with(
                from_java_version="1.18.2",
                to_bedrock_version="1.18.30",
                features=["blocks", "entities"],
                db=mock_db
            )
    
    @pytest.mark.asyncio
    async def test_get_matrix_overview_success(
        self, mock_db, mock_compatibility_service
    ):
        """Test successful matrix overview retrieval."""
        with patch('backend.src.api.version_compatibility.version_compatibility_service', mock_compatibility_service):
            expected_overview = {
                "java_versions": ["1.18.2", "1.19.0"],
                "bedrock_versions": ["1.18.30", "1.19.50"],
                "total_combinations": 4,
                "average_compatibility": 0.80
            }
            mock_compatibility_service.get_matrix_overview.return_value = expected_overview
            
            response = await get_matrix_overview(db=mock_db)
            
            assert response == expected_overview
            mock_compatibility_service.get_matrix_overview.assert_called_once_with(mock_db)
    
    @pytest.mark.asyncio
    async def test_get_java_versions_success(
        self, mock_db, mock_compatibility_service
    ):
        """Test successful Java versions list retrieval."""
        with patch('backend.src.api.version_compatibility.version_compatibility_service', mock_compatibility_service):
            expected_overview = {
                "java_versions": ["1.18.2", "1.19.0", "1.20.0"],
                "last_updated": "2023-12-01T12:00:00"
            }
            mock_compatibility_service.get_matrix_overview.return_value = expected_overview
            
            response = await get_java_versions(db=mock_db)
            
            assert response["java_versions"] == ["1.18.2", "1.19.0", "1.20.0"]
            assert response["total_count"] == 3
            assert response["last_updated"] == "2023-12-01T12:00:00"
    
    @pytest.mark.asyncio
    async def test_get_bedrock_versions_success(
        self, mock_db, mock_compatibility_service
    ):
        """Test successful Bedrock versions list retrieval."""
        with patch('backend.src.api.version_compatibility.version_compatibility_service', mock_compatibility_service):
            expected_overview = {
                "bedrock_versions": ["1.18.30", "1.19.50", "1.20.60"],
                "last_updated": "2023-12-01T12:00:00"
            }
            mock_compatibility_service.get_matrix_overview.return_value = expected_overview
            
            response = await get_bedrock_versions(db=mock_db)
            
            assert response["bedrock_versions"] == ["1.18.30", "1.19.50", "1.20.60"]
            assert response["total_count"] == 3
            assert response["last_updated"] == "2023-12-01T12:00:00"
    
    @pytest.mark.asyncio
    async def test_get_matrix_visual_data_success(
        self, mock_db, mock_compatibility_service
    ):
        """Test successful matrix visual data retrieval."""
        with patch('backend.src.api.version_compatibility.version_compatibility_service', mock_compatibility_service):
            expected_overview = {
                "java_versions": ["1.18.2", "1.19.0"],
                "bedrock_versions": ["1.18.30", "1.19.50"],
                "matrix": {
                    "1.18.2": {
                        "1.18.30": {"score": 0.9, "features_count": 100, "issues_count": 2},
                        "1.19.50": {"score": 0.7, "features_count": 80, "issues_count": 5}
                    },
                    "1.19.0": {
                        "1.18.30": {"score": None, "features_count": None, "issues_count": None},
                        "1.19.50": {"score": 0.95, "features_count": 110, "issues_count": 1}
                    }
                },
                "total_combinations": 4,
                "average_compatibility": 0.85,
                "compatibility_distribution": {"high": 2, "medium": 1, "low": 0}
            }
            mock_compatibility_service.get_matrix_overview.return_value = expected_overview
            
            response = await get_matrix_visual_data(db=mock_db)
            
            # Check structure
            assert "data" in response
            assert "java_versions" in response
            assert "bedrock_versions" in response
            assert "summary" in response
            
            # Check data points
            data_points = response["data"]
            assert len(data_points) == 4  # 2 Java versions × 2 Bedrock versions
            
            # Check specific data point
            first_point = data_points[0]
            assert "java_version" in first_point
            assert "bedrock_version" in first_point
            assert "java_index" in first_point
            assert "bedrock_index" in first_point
            assert "compatibility_score" in first_point
            assert "features_count" in first_point
            assert "issues_count" in first_point
            assert "supported" in first_point
            
            # Check summary
            summary = response["summary"]
            assert summary["total_combinations"] == 4
            assert summary["average_compatibility"] == 0.85
            assert summary["high_compatibility_count"] == 2
            assert summary["medium_compatibility_count"] == 1
            assert summary["low_compatibility_count"] == 0
    
    @pytest.mark.asyncio
    async def test_get_version_recommendations_success(
        self, mock_db, mock_compatibility_service, sample_compatibility
    ):
        """Test successful version recommendations retrieval."""
        with patch('backend.src.api.version_compatibility.version_compatibility_service', mock_compatibility_service):
            mock_compatibility_service.get_by_java_version.return_value = [sample_compatibility]
            
            response = await get_version_recommendations(
                java_version="1.19.0",
                limit=5,
                min_compatibility=0.5,
                db=mock_db
            )
            
            assert response["java_version"] == "1.19.0"
            assert len(response["recommendations"]) == 1
            assert response["total_available"] == 1
            assert response["min_score_used"] == 0.5
            
            recommendation = response["recommendations"][0]
            assert recommendation["bedrock_version"] == "1.19.50"
            assert recommendation["compatibility_score"] == 0.85
            assert "recommendation_reason" in recommendation
    
    @pytest.mark.asyncio
    async def test_get_version_recommendations_no_data(
        self, mock_db, mock_compatibility_service
    ):
        """Test version recommendations with no data."""
        with patch('backend.src.api.version_compatibility.version_compatibility_service', mock_compatibility_service):
            mock_compatibility_service.get_by_java_version.return_value = []
            
            with pytest.raises(HTTPException) as exc_info:
                await get_version_recommendations(
                    java_version="1.19.0",
                    db=mock_db
                )
            
            assert exc_info.value.status_code == 404
            assert "No compatibility data found" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_version_recommendations_filtering(
        self, mock_db, mock_compatibility_service
    ):
        """Test version recommendations with filtering."""
        with patch('backend.src.api.version_compatibility.version_compatibility_service', mock_compatibility_service):
            # Create compatibilities with different scores
            low_compat = MagicMock()
            low_compat.bedrock_version = "1.18.30"
            low_compat.compatibility_score = 0.4
            low_compat.features_supported = []
            low_compat.known_issues = []
            
            high_compat = MagicMock()
            high_compat.bedrock_version = "1.19.50"
            high_compat.compatibility_score = 0.9
            high_compat.features_supported = []
            high_compat.known_issues = []
            
            mock_compatibility_service.get_by_java_version.return_value = [low_compat, high_compat]
            
            response = await get_version_recommendations(
                java_version="1.19.0",
                limit=5,  # Need to pass the actual integer value, not Query object
                min_compatibility=0.7,  # Should filter out low_compat
                db=mock_db
            )
            
            assert len(response["recommendations"]) == 1
            assert response["recommendations"][0]["bedrock_version"] == "1.19.50"
            assert response["total_available"] == 1
    
    @pytest.mark.asyncio
    async def test_get_compatibility_statistics_success(
        self, mock_db, mock_compatibility_service
    ):
        """Test successful compatibility statistics retrieval."""
        with patch('backend.src.api.version_compatibility.version_compatibility_service', mock_compatibility_service):
            expected_overview = {
                "java_versions": ["1.18.2", "1.19.0"],
                "bedrock_versions": ["1.18.30", "1.19.50"],
                "matrix": {
                    "1.18.2": {
                        "1.18.30": {"score": 0.9, "features_count": 100, "issues_count": 2},
                        "1.19.50": {"score": 0.7, "features_count": 80, "issues_count": 5}
                    },
                    "1.19.0": {
                        "1.18.30": {"score": 0.8, "features_count": 90, "issues_count": 3},
                        "1.19.50": {"score": 0.95, "features_count": 110, "issues_count": 1}
                    }
                },
                "total_combinations": 4,
                "average_compatibility": 0.8375,
                "compatibility_distribution": {"high": 2, "medium": 2, "low": 0}
            }
            mock_compatibility_service.get_matrix_overview.return_value = expected_overview
            
            response = await get_compatibility_statistics(db=mock_db)
            
            # Check coverage section
            coverage = response["coverage"]
            assert coverage["total_possible_combinations"] == 4  # 2×2
            assert coverage["documented_combinations"] == 4
            assert coverage["coverage_percentage"] == 100.0
            assert coverage["java_versions_count"] == 2
            assert coverage["bedrock_versions_count"] == 2
            
            # Check score distribution
            score_dist = response["score_distribution"]
            assert score_dist["average_score"] == 0.8375
            assert score_dist["minimum_score"] == 0.7
            assert score_dist["maximum_score"] == 0.95
            assert "median_score" in score_dist
            assert score_dist["high_compatibility"] == 2
            assert score_dist["medium_compatibility"] == 2
            assert score_dist["low_compatibility"] == 0
            
            # Check best combinations
            best_combinations = response["best_combinations"]
            assert len(best_combinations) == 3  # Scores >= 0.8: 0.95, 0.9, 0.8 (not 0.7)
            best_combinations.sort(key=lambda x: x["score"], reverse=True)
            assert best_combinations[0]["score"] == 0.95
            assert best_combinations[0]["java_version"] == "1.19.0"
            assert best_combinations[0]["bedrock_version"] == "1.19.50"
            
            # Check worst combinations
            worst_combinations = response["worst_combinations"]
            # All scores >= 0.5, so should be empty or contain the lowest scores
            assert isinstance(worst_combinations, list)
            
            # Check recommendations
            recommendations = response["recommendations"]
            assert isinstance(recommendations, list)


class TestHelperFunctions:
    """Test helper functions for version compatibility API."""
    
    def test_get_recommendation_reason_excellent(self):
        """Test recommendation reason for excellent compatibility."""
        compatibility = MagicMock()
        compatibility.compatibility_score = 0.95
        compatibility.features_supported = [{"name": "blocks"}]
        compatibility.known_issues = []
        
        all_compatibilities = [compatibility]
        
        reason = _get_recommendation_reason(compatibility, all_compatibilities)
        assert "Excellent compatibility" in reason
    
    def test_get_recommendation_reason_high_features(self):
        """Test recommendation reason for high feature support."""
        compatibility = MagicMock()
        compatibility.compatibility_score = 0.8
        compatibility.features_supported = [{"name": "blocks"}, {"name": "entities"}]  # Above average
        compatibility.known_issues = []
        
        other_compat = MagicMock()
        other_compat.compatibility_score = 0.7
        other_compat.features_supported = [{"name": "blocks"}]  # Below average
        
        all_compatibilities = [compatibility, other_compat]
        
        reason = _get_recommendation_reason(compatibility, all_compatibilities)
        assert "above-average feature support" in reason
    
    def test_get_recommendation_reason_no_issues(self):
        """Test recommendation reason for stable compatibility."""
        compatibility = MagicMock()
        compatibility.compatibility_score = 0.6
        compatibility.features_supported = [{"name": "blocks"}]
        compatibility.known_issues = []  # No issues
        
        other_compat = MagicMock()
        other_compat.compatibility_score = 0.7
        other_compat.features_supported = [{"name": "blocks"}]
        other_compat.known_issues = ["some issue"]
        
        all_compatibilities = [compatibility, other_compat]
        
        reason = _get_recommendation_reason(compatibility, all_compatibilities)
        assert "no known issues" in reason
    
    def test_get_recommendation_reason_fallback(self):
        """Test recommendation reason fallback case."""
        compatibility = MagicMock()
        compatibility.compatibility_score = 0.6
        compatibility.features_supported = [{"name": "blocks"}]
        compatibility.known_issues = ["some issue"]
        
        other_compat = MagicMock()
        other_compat.compatibility_score = 0.7
        other_compat.features_supported = [{"name": "blocks"}]
        other_compat.known_issues = []
        
        all_compatibilities = [compatibility, other_compat]
        
        reason = _get_recommendation_reason(compatibility, all_compatibilities)
        assert "acceptable compatibility" in reason
    
    def test_generate_recommendations_low_average(self):
        """Test recommendations generation for low average scores."""
        overview = {
            "average_compatibility": 0.6,  # Low average
            "compatibility_distribution": {"high": 1, "medium": 2, "low": 3},
            "java_versions": ["1.18.2", "1.19.0"],
            "bedrock_versions": ["1.18.30", "1.19.50"]
        }
        
        recommendations = _generate_recommendations(overview)
        assert len(recommendations) > 0
        assert any("compatibility scores are low" in r for r in recommendations)
    
    def test_generate_recommendations_many_low(self):
        """Test recommendations generation for many low-compatibility combos."""
        overview = {
            "average_compatibility": 0.7,
            "compatibility_distribution": {"high": 1, "medium": 1, "low": 5},  # Many low
            "java_versions": ["1.18.2", "1.19.0"],
            "bedrock_versions": ["1.18.30", "1.19.50"]
        }
        
        recommendations = _generate_recommendations(overview)
        assert len(recommendations) > 0
        assert any("low-compatibility combinations" in r for r in recommendations)
    
    def test_generate_recommendations_limited_java(self):
        """Test recommendations generation for limited Java versions."""
        overview = {
            "average_compatibility": 0.8,
            "compatibility_distribution": {"high": 3, "medium": 2, "low": 1},
            "java_versions": ["1.18.2"],  # Only one version
            "bedrock_versions": ["1.18.30", "1.19.50", "1.20.60"]
        }
        
        recommendations = _generate_recommendations(overview)
        assert len(recommendations) > 0
        assert any("Limited Java version coverage" in r for r in recommendations)
    
    def test_generate_recommendations_limited_bedrock(self):
        """Test recommendations generation for limited Bedrock versions."""
        overview = {
            "average_compatibility": 0.8,
            "compatibility_distribution": {"high": 3, "medium": 2, "low": 1},
            "java_versions": ["1.18.2", "1.19.0", "1.20.0"],
            "bedrock_versions": ["1.18.30"]  # Only one version
        }
        
        recommendations = _generate_recommendations(overview)
        assert len(recommendations) > 0
        assert any("Limited Bedrock version coverage" in r for r in recommendations)
    
    def test_generate_recommendations_few_high(self):
        """Test recommendations generation for few high-compatibility combos."""
        overview = {
            "average_compatibility": 0.6,
            "compatibility_distribution": {"high": 1, "medium": 2, "low": 7},  # Low ratio of high
            "java_versions": ["1.18.2", "1.19.0", "1.20.0"],
            "bedrock_versions": ["1.18.30", "1.19.50", "1.20.60"]
        }
        
        recommendations = _generate_recommendations(overview)
        assert len(recommendations) > 0
        assert any("Few high-compatibility combinations" in r for r in recommendations)
    
    def test_generate_recommendations_no_issues(self):
        """Test recommendations generation when no specific issues."""
        overview = {
            "average_compatibility": 0.8,
            "compatibility_distribution": {"high": 5, "medium": 3, "low": 1},  # Good ratio
            "java_versions": ["1.18.2", "1.19.0", "1.20.0", "1.21.0"],  # Good coverage
            "bedrock_versions": ["1.18.30", "1.19.50", "1.20.60", "1.21.80"]  # Good coverage
        }
        
        recommendations = _generate_recommendations(overview)
        # Should return empty or minimal recommendations
        assert isinstance(recommendations, list)


class TestVersionCompatibilityApiModule:
    """Test version compatibility API module structure."""
    
    def test_module_exports(self):
        """Test that all expected functions are exported."""
        from backend.src.api import version_compatibility
        
        # Check that helper functions are in the API module namespace
        assert hasattr(version_compatibility, "_get_recommendation_reason")
        assert hasattr(version_compatibility, "_generate_recommendations")
        assert hasattr(version_compatibility, "router")
    
    def test_version_compatibility_api_dict(self):
        """Test the version_compatibility_api dictionary."""
        assert "_get_recommendation_reason" in version_compatibility_api
        assert "_generate_recommendations" in version_compatibility_api
        assert callable(version_compatibility_api["_get_recommendation_reason"])
        assert callable(version_compatibility_api["_generate_recommendations"])
