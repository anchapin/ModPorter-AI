"""
Comprehensive tests for VersionCompatibilityService.

This module tests the core functionality of the VersionCompatibilityService,
including compatibility checks, matrix management, and version mapping.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from src.services.version_compatibility import VersionCompatibilityService
from src.db.models import VersionCompatibility


class TestVersionCompatibilityService:
    """Test cases for VersionCompatibilityService class."""

    @pytest.fixture
    def service(self):
        """Create a VersionCompatibilityService instance for testing."""
        return VersionCompatibilityService()

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session for testing."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def sample_version_compatibility(self):
        """Sample version compatibility for testing."""
        return VersionCompatibility(
            id="compat_1",
            java_version="1.18.2",
            bedrock_version="1.18.0",
            compatibility_score=0.9,
            issues=[
                {
                    "category": "block_properties",
                    "description": "Some block properties differ between Java and Bedrock",
                    "severity": "medium",
                    "workaround": "Use alternative properties"
                }
            ],
            features_supported=[
                "basic_blocks",
                "custom_items",
                "simple_entities"
            ],
            features_unsupported=[
                "advanced_redstone",
                "complex_entity_ai"
            ],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

    @pytest.fixture
    def sample_version_matrix(self):
        """Sample version compatibility matrix for testing."""
        return [
            {
                "java_version": "1.18.2",
                "bedrock_version": "1.18.0",
                "compatibility_score": 0.9,
                "features_supported": ["basic_blocks", "custom_items"],
                "features_unsupported": ["advanced_redstone"]
            },
            {
                "java_version": "1.19.0",
                "bedrock_version": "1.19.0",
                "compatibility_score": 0.85,
                "features_supported": ["basic_blocks", "custom_items", "advanced_redstone"],
                "features_unsupported": ["complex_entity_ai"]
            },
            {
                "java_version": "1.20.0",
                "bedrock_version": "1.20.0",
                "compatibility_score": 0.8,
                "features_supported": ["basic_blocks", "custom_items", "advanced_redstone", "simple_entities"],
                "features_unsupported": ["complex_entity_ai", "custom_dimensions"]
            }
        ]

    @pytest.mark.asyncio
    async def test_init(self, service):
        """Test VersionCompatibilityService initialization."""
        assert service.default_compatibility is not None
        assert isinstance(service.default_compatibility, dict)
        assert len(service.default_compatibility) > 0

    @pytest.mark.asyncio
    async def test_get_compatibility_exact_match(
        self, service, mock_db_session, sample_version_compatibility
    ):
        """Test getting compatibility with exact match in database."""
        # Mock VersionCompatibilityCRUD.get_compatibility to return our sample
        with patch('src.services.version_compatibility.VersionCompatibilityCRUD.get_compatibility',
                  return_value=sample_version_compatibility):
            # Call the method
            result = await service.get_compatibility("1.18.2", "1.18.0", mock_db_session)

            # Verify the result
            assert result is not None
            assert result.java_version == "1.18.2"
            assert result.bedrock_version == "1.18.0"
            assert result.compatibility_score == 0.9
            assert len(result.issues) == 1
            assert result.issues[0]["category"] == "block_properties"
            assert "basic_blocks" in result.features_supported
            assert "advanced_redstone" in result.features_unsupported

    @pytest.mark.asyncio
    async def test_get_compatibility_no_match_fallback(
        self, service, mock_db_session, sample_version_matrix
    ):
        """Test getting compatibility with no match, falling back to defaults."""
        # Mock VersionCompatibilityCRUD.get_compatibility to return None (no match)
        with patch('src.services.version_compatibility.VersionCompatibilityCRUD.get_compatibility',
                  return_value=None):
            # Mock _get_closest_version_match to return a fallback
            with patch.object(service, '_get_closest_version_match',
                             return_value=sample_version_matrix[0]):
                # Call the method
                result = await service.get_compatibility("1.21.0", "1.21.0", mock_db_session)

                # Verify the result uses fallback data
                assert result is not None
                assert result.java_version == "1.18.2"  # From fallback
                assert result.bedrock_version == "1.18.0"  # From fallback
                assert result.compatibility_score == 0.9

    @pytest.mark.asyncio
    async def test_get_compatibility_no_fallback(self, service, mock_db_session):
        """Test getting compatibility with no match and no fallback."""
        # Mock VersionCompatibilityCRUD.get_compatibility to return None
        with patch('src.services.version_compatibility.VersionCompatibilityCRUD.get_compatibility',
                  return_value=None):
            # Mock _get_closest_version_match to return None (no fallback)
            with patch.object(service, '_get_closest_version_match', return_value=None):
                # Call the method
                result = await service.get_compatibility("1.21.0", "1.21.0", mock_db_session)

                # Verify no result is returned
                assert result is None

    @pytest.mark.asyncio
    async def test_get_java_version_compatibility(
        self, service, mock_db_session, sample_version_matrix
    ):
        """Test getting all compatibility data for a Java version."""
        # Mock database query to return compatibility data for Java version
        with patch('src.services.version_compatibility.execute_query',
                  return_value=sample_version_matrix):
            # Call the method
            result = await service.get_java_version_compatibility("1.19.0", mock_db_session)

            # Verify the result
            assert result is not None
            assert len(result) == 1  # One entry for Java 1.19.0
            assert result[0]["java_version"] == "1.19.0"
            assert result[0]["bedrock_version"] == "1.19.0"
            assert result[0]["compatibility_score"] == 0.85

    @pytest.mark.asyncio
    async def test_get_bedrock_version_compatibility(
        self, service, mock_db_session, sample_version_matrix
    ):
        """Test getting all compatibility data for a Bedrock version."""
        # Mock database query to return compatibility data for Bedrock version
        with patch('src.services.version_compatibility.execute_query',
                  return_value=sample_version_matrix):
            # Call the method
            result = await service.get_bedrock_version_compatibility("1.18.0", mock_db_session)

            # Verify the result
            assert result is not None
            assert len(result) == 1  # One entry for Bedrock 1.18.0
            assert result[0]["java_version"] == "1.18.2"
            assert result[0]["bedrock_version"] == "1.18.0"
            assert result[0]["compatibility_score"] == 0.9

    @pytest.mark.asyncio
    async def test_get_compatibility_matrix(self, service, mock_db_session, sample_version_matrix):
        """Test getting the full compatibility matrix."""
        # Mock database query to return the full matrix
        with patch('src.services.version_compatibility.execute_query',
                  return_value=sample_version_matrix):
            # Call the method
            result = await service.get_compatibility_matrix(mock_db_session)

            # Verify the result
            assert result is not None
            assert len(result) == 3  # All entries in the matrix
            # Check that all Java versions are included
            java_versions = {entry["java_version"] for entry in result}
            assert java_versions == {"1.18.2", "1.19.0", "1.20.0"}
            # Check that all Bedrock versions are included
            bedrock_versions = {entry["bedrock_version"] for entry in result}
            assert bedrock_versions == {"1.18.0", "1.19.0", "1.20.0"}

    @pytest.mark.asyncio
    async def test_create_or_update_compatibility_create(
        self, service, mock_db_session, sample_version_compatibility
    ):
        """Test creating new compatibility data."""
        # Mock VersionCompatibilityCRUD.get_compatibility to return None (no existing entry)
        with patch('src.services.version_compatibility.VersionCompatibilityCRUD.get_compatibility',
                  return_value=None):
            # Mock VersionCompatibilityCRUD.create_compatibility to return created entry
            with patch('src.services.version_compatibility.VersionCompatibilityCRUD.create_compatibility',
                      return_value=sample_version_compatibility):
                # Call the method
                result = await service.create_or_update_compatibility(
                    "1.21.0", "1.21.0", 0.75,
                    ["issue1"], ["feature1"], ["feature2"],
                    mock_db_session
                )

                # Verify the result
                assert result is not None
                assert result.java_version == "1.18.2"  # From our sample

    @pytest.mark.asyncio
    async def test_create_or_update_compatibility_update(
        self, service, mock_db_session, sample_version_compatibility
    ):
        """Test updating existing compatibility data."""
        # Mock VersionCompatibilityCRUD.get_compatibility to return existing entry
        with patch('src.services.version_compatibility.VersionCompatibilityCRUD.get_compatibility',
                  return_value=sample_version_compatibility):
            # Mock VersionCompatibilityCRUD.update_compatibility to return updated entry
            updated_entry = VersionCompatibility(
                id=sample_version_compatibility.id,
                java_version="1.18.2",
                bedrock_version="1.18.0",
                compatibility_score=0.95,  # Updated score
                issues=[],
                features_supported=["basic_blocks", "custom_items", "advanced_redstone"],
                features_unsupported=["complex_entity_ai"],
                created_at=sample_version_compatibility.created_at,
                updated_at=datetime.utcnow()
            )

            with patch('src.services.version_compatibility.VersionCompatibilityCRUD.update_compatibility',
                      return_value=updated_entry):
                # Call the method
                result = await service.create_or_update_compatibility(
                    "1.18.2", "1.18.0", 0.95,  # Updated score
                    [],  # No issues
                    ["basic_blocks", "custom_items", "advanced_redstone"],  # Additional feature
                    ["complex_entity_ai"],  # Unsupported feature
                    mock_db_session
                )

                # Verify the result
                assert result is not None
                assert result.java_version == "1.18.2"
                assert result.bedrock_version == "1.18.0"
                assert result.compatibility_score == 0.95  # Updated score
                assert len(result.issues) == 0  # Updated issues
                assert "advanced_redstone" in result.features_supported  # Updated features

    @pytest.mark.asyncio
    async def test_check_feature_compatibility(
        self, service, mock_db_session, sample_version_compatibility
    ):
        """Test checking if a feature is compatible between versions."""
        # Mock VersionCompatibilityCRUD.get_compatibility to return our sample
        with patch('src.services.version_compatibility.VersionCompatibilityCRUD.get_compatibility',
                  return_value=sample_version_compatibility):
            # Test with a supported feature
            result_supported = await service.check_feature_compatibility(
                "basic_blocks", "1.18.2", "1.18.0", mock_db_session
            )
            assert result_supported is True

            # Test with an unsupported feature
            result_unsupported = await service.check_feature_compatibility(
                "advanced_redstone", "1.18.2", "1.18.0", mock_db_session
            )
            assert result_unsupported is False

            # Test with a feature not in either list (default to False)
            result_unknown = await service.check_feature_compatibility(
                "unknown_feature", "1.18.2", "1.18.0", mock_db_session
            )
            assert result_unknown is False

    @pytest.mark.asyncio
    async def test_get_compatible_versions_for_feature(
        self, service, mock_db_session, sample_version_matrix
    ):
        """Test getting all version pairs compatible with a feature."""
        # Mock database query to return the full matrix
        with patch('src.services.version_compatibility.execute_query',
                  return_value=sample_version_matrix):
            # Call the method for a feature that's supported in some versions
            result = await service.get_compatible_versions_for_feature(
                "basic_blocks", mock_db_session
            )

            # Verify the result
            assert result is not None
            assert len(result) == 3  # All three entries support basic_blocks
            assert all("basic_blocks" in entry["features_supported"] for entry in result)

            # Call the method for a feature that's only supported in some versions
            result_partial = await service.get_compatible_versions_for_feature(
                "advanced_redstone", mock_db_session
            )

            # Verify the result
            assert result_partial is not None
            assert len(result_partial) == 2  # Only 1.19.0 and 1.20.0 support advanced_redstone
            assert all("advanced_redstone" in entry["features_supported"] for entry in result_partial)

    @pytest.mark.asyncio
    async def test_get_version_compatibility_issues(
        self, service, mock_db_session, sample_version_compatibility
    ):
        """Test getting compatibility issues between versions."""
        # Mock VersionCompatibilityCRUD.get_compatibility to return our sample
        with patch('src.services.version_compatibility.VersionCompatibilityCRUD.get_compatibility',
                  return_value=sample_version_compatibility):
            # Call the method
            result = await service.get_version_compatibility_issues(
                "1.18.2", "1.18.0", mock_db_session
            )

            # Verify the result
            assert result is not None
            assert len(result) == 1
            assert result[0]["category"] == "block_properties"
            assert result[0]["severity"] == "medium"
            assert "workaround" in result[0]

    @pytest.mark.asyncio
    async def test_recommended_version_pairs(
        self, service, mock_db_session, sample_version_matrix
    ):
        """Test getting recommended version pairs for a feature."""
        # Mock database query to return the full matrix
        with patch('src.services.version_compatibility.execute_query',
                  return_value=sample_version_matrix):
            # Call the method for a feature
            result = await service.recommended_version_pairs(
                "basic_blocks", mock_db_session
            )

            # Verify the result
            assert result is not None
            assert len(result) == 3  # All three entries support basic_blocks
            # Results should be sorted by compatibility score (descending)
            assert result[0]["compatibility_score"] >= result[1]["compatibility_score"]
            assert result[1]["compatibility_score"] >= result[2]["compatibility_score"]

            # Verify structure of each entry
            for entry in result:
                assert "java_version" in entry
                assert "bedrock_version" in entry
                assert "compatibility_score" in entry
                assert "issues" in entry

    @pytest.mark.asyncio
    async def test_get_version_transition_path(
        self, service, mock_db_session, sample_version_matrix
    ):
        """Test getting a path for version transitions."""
        # Mock database query to return the full matrix
        with patch('src.services.version_compatibility.execute_query',
                  return_value=sample_version_matrix):
            # Test with compatible versions
            result = await service.get_version_transition_path(
                "1.18.2", "1.20.0", mock_db_session
            )

            # Verify the result
            assert result is not None
            assert "path" in result
            assert "steps" in result["path"]
            assert len(result["path"]["steps"]) >= 1

            # Verify structure of each step
            for step in result["path"]["steps"]:
                assert "java_version" in step
                assert "bedrock_version" in step
                assert "compatibility_score" in step
                assert "issues" in step

    def test_get_closest_version_match_exact(self, service, sample_version_matrix):
        """Test finding the closest version match with exact match."""
        # Call the method with exact match
        result = service._get_closest_version_match(
            "1.19.0", "1.19.0", sample_version_matrix
        )

        # Verify the result
        assert result is not None
        assert result["java_version"] == "1.19.0"
        assert result["bedrock_version"] == "1.19.0"
        assert result["compatibility_score"] == 0.85

    def test_get_closest_version_match_partial(self, service, sample_version_matrix):
        """Test finding the closest version match with partial match."""
        # Call the method with no exact match but close major version
        result = service._get_closest_version_match(
            "1.19.1", "1.19.1", sample_version_matrix
        )

        # Verify the result finds the closest match (1.19.0)
        assert result is not None
        assert result["java_version"] == "1.19.0"
        assert result["bedrock_version"] == "1.19.0"
        assert result["compatibility_score"] == 0.85

    def test_get_closest_version_match_none(self, service, sample_version_matrix):
        """Test finding the closest version match with no close match."""
        # Call the method with a version that's far from available versions
        result = service._get_closest_version_match(
            "2.0.0", "2.0.0", sample_version_matrix
        )

        # Verify the result finds the closest match (highest version)
        assert result is not None
        assert result["java_version"] == "1.20.0"
        assert result["bedrock_version"] == "1.20.0"

    def test_calculate_overall_compatibility(self, service, sample_version_matrix):
        """Test calculating overall compatibility between versions."""
        # Call the method with compatible versions
        result = service._calculate_overall_compatibility(
            "1.18.2", "1.18.0", sample_version_matrix
        )

        # Verify the result
        assert result is not None
        assert 0.0 <= result <= 1.0
        assert result == 0.9  # From our sample data

    @pytest.mark.asyncio
    async def test_sync_version_matrix(self, service, mock_db_session):
        """Test synchronizing version compatibility matrix."""
        # Mock external data source
        external_data = [
            {
                "java_version": "1.21.0",
                "bedrock_version": "1.21.0",
                "compatibility_score": 0.85,
                "features_supported": ["basic_blocks"],
                "features_unsupported": []
            }
        ]

        # Mock CRUD operations
        with patch('src.services.version_compatibility.VersionCompatibilityCRUD.get_compatibility',
                  return_value=None):
            with patch('src.services.version_compatibility.VersionCompatibilityCRUD.create_compatibility',
                      return_value=True):
                # Call the method
                result = await service.sync_version_matrix(external_data, mock_db_session)

                # Verify the result
                assert result is not None
                assert "success" in result
                assert "updated" in result
                assert "created" in result
                assert "errors" in result
                assert result["success"] is True
