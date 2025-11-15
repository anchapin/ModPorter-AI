"""
Tests for version compatibility service.
Tests the core service logic directly.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from services.version_compatibility import version_compatibility_service
from db.models import VersionCompatibility


class TestVersionCompatibilityService:
    """Test version compatibility service core logic."""
    
    @pytest.mark.asyncio
    async def test_get_compatibility_existing_entry(self):
        """Test getting compatibility for existing entry."""
        # Mock database and CRUD operations
        mock_db = AsyncMock()
        mock_compatibility = MagicMock()
        mock_compatibility.java_version = "1.19.4"
        mock_compatibility.bedrock_version = "1.19.50"
        mock_compatibility.compatibility_score = 0.85
        mock_compatibility.features_supported = []
        mock_compatibility.deprecated_patterns = []
        mock_compatibility.migration_guides = {}
        mock_compatibility.auto_update_rules = {}
        mock_compatibility.known_issues = []
        
        with patch('services.version_compatibility.VersionCompatibilityCRUD') as mock_crud:
            mock_crud.get_compatibility = AsyncMock(return_value=mock_compatibility)
            
            result = await version_compatibility_service.get_compatibility(
                "1.19.4", "1.19.50", mock_db
            )
            
            assert result == mock_compatibility
            mock_crud.get_compatibility.assert_called_once_with(
                mock_db, "1.19.4", "1.19.50"
            )
    
    @pytest.mark.asyncio
    async def test_get_compatibility_no_entry(self):
        """Test getting compatibility when no exact match exists."""
        mock_db = AsyncMock()
        
        with patch('services.version_compatibility.VersionCompatibilityCRUD') as mock_crud, \
             patch.object(version_compatibility_service, '_find_closest_compatibility') as mock_find:
            
            # No exact match found
            mock_crud.get_compatibility = AsyncMock(return_value=None)
            
            # Mock closest version found
            mock_closest = MagicMock()
            mock_closest.java_version = "1.19.4"
            mock_closest.bedrock_version = "1.19.50"
            mock_closest.compatibility_score = 0.8
            mock_find.return_value = mock_closest
            
            result = await version_compatibility_service.get_compatibility(
                "1.19.3", "1.19.45", mock_db
            )
            
            assert result == mock_closest
            mock_find.assert_called_once_with(mock_db, "1.19.3", "1.19.45")
    
    @pytest.mark.asyncio
    async def test_get_by_java_version(self):
        """Test getting all compatibilities for a Java version."""
        mock_db = AsyncMock()
        
        with patch('services.version_compatibility.VersionCompatibilityCRUD') as mock_crud:
            # Mock compatibilities
            compat1 = MagicMock()
            compat1.bedrock_version = "1.19.50"
            compat1.compatibility_score = 0.85
            
            compat2 = MagicMock()
            compat2.bedrock_version = "1.20.0"
            compat2.compatibility_score = 0.75
            
            compat3 = MagicMock()
            compat3.bedrock_version = "1.20.60"
            compat3.compatibility_score = 0.80
            
            # Should be sorted by score descending
            mock_crud.get_by_java_version = AsyncMock(return_value=[compat1, compat3, compat2])
            
            result = await version_compatibility_service.get_by_java_version(
                "1.19.4", mock_db
            )
            
            assert result == [compat1, compat3, compat2]
            mock_crud.get_by_java_version.assert_called_once_with(mock_db, "1.19.4")
    
    @pytest.mark.asyncio
    async def test_update_compatibility_create_new(self):
        """Test creating new compatibility entry."""
        mock_db = AsyncMock()
        
        with patch('services.version_compatibility.VersionCompatibilityCRUD') as mock_crud:
            # No existing entry
            mock_crud.get_compatibility = AsyncMock(return_value=None)
            
            # Mock successful creation
            mock_new = MagicMock()
            mock_new.id = "test-id"
            mock_crud.create = AsyncMock(return_value=mock_new)
            
            compatibility_data = {
                "compatibility_score": 0.9,
                "features_supported": [],
                "deprecated_patterns": [],
                "migration_guides": {},
                "auto_update_rules": {},
                "known_issues": []
            }
            
            result = await version_compatibility_service.update_compatibility(
                "1.20.1", "1.20.60", compatibility_data, mock_db
            )
            
            assert result is True
            mock_crud.create.assert_called_once_with(mock_db, {
                "java_version": "1.20.1",
                "bedrock_version": "1.20.60",
                **compatibility_data
            })
    
    @pytest.mark.asyncio
    async def test_update_compatibility_update_existing(self):
        """Test updating existing compatibility entry."""
        mock_db = AsyncMock()
        
        with patch('services.version_compatibility.VersionCompatibilityCRUD') as mock_crud:
            # Existing entry found
            mock_existing = MagicMock()
            mock_existing.id = "existing-id"
            mock_crud.get_compatibility = AsyncMock(return_value=mock_existing)
            
            # Mock successful update
            mock_crud.update = AsyncMock(return_value=True)
            
            compatibility_data = {
                "compatibility_score": 0.95,
                "features_supported": [{"type": "blocks"}],
                "deprecated_patterns": [],
                "migration_guides": {"steps": []},
                "auto_update_rules": {},
                "known_issues": []
            }
            
            result = await version_compatibility_service.update_compatibility(
                "1.20.1", "1.20.60", compatibility_data, mock_db
            )
            
            assert result is True
            mock_crud.update.assert_called_once_with(
                mock_db, "existing-id", compatibility_data
            )
    
    def test_find_closest_version_exact_match(self):
        """Test finding closest version when exact match exists."""
        available = ["1.19.4", "1.20.0", "1.20.60"]
        target = "1.20.0"
        
        result = version_compatibility_service._find_closest_version(target, available)
        
        assert result == "1.20.0"
    
    def test_find_closest_version_no_exact_match(self):
        """Test finding closest version when no exact match exists."""
        available = ["1.19.4", "1.20.0", "1.20.60"]
        target = "1.19.5"
        
        result = version_compatibility_service._find_closest_version(target, available)
        
        # Should find 1.19.4 as closest
        assert result == "1.19.4"
    
    def test_find_closest_version_version_number_parsing(self):
        """Test version number parsing in closest version finder."""
        available = ["1.14.4", "1.15.2", "1.16.5"]
        target = "1.15.1"
        
        result = version_compatibility_service._find_closest_version(target, available)
        
        # Should find 1.15.2 as closest
        assert result == "1.15.2"
    
    @pytest.mark.asyncio
    async def test_get_matrix_overview_empty(self):
        """Test getting matrix overview when no entries exist."""
        mock_db = AsyncMock()
        
        with patch('services.version_compatibility.select') as mock_select:
            # Empty result
            # Create nested mock structure for result.scalars().all()
            mock_result = MagicMock()
            mock_scalars = MagicMock()
            mock_scalars.all.return_value = []
            
            # result.scalars() returns mock_scalars
            mock_result.scalars.return_value = mock_scalars
            
            # Mock db.execute(query) returns result
            mock_db.execute = AsyncMock(return_value=mock_result)
            
            result = await version_compatibility_service.get_matrix_overview(mock_db)
            
            assert result["total_combinations"] == 0
            assert result["java_versions"] == []
            assert result["bedrock_versions"] == []
            assert result["average_compatibility"] == 0.0
            assert result["matrix"] == {}
    
    @pytest.mark.asyncio
    async def test_get_matrix_overview_with_entries(self):
        """Test getting matrix overview with entries."""
        mock_db = AsyncMock()
        
        with patch('services.version_compatibility.select') as mock_select, \
             patch('services.version_compatibility.max') as mock_max:
            
            # Mock entries
            compat1 = MagicMock()
            compat1.java_version = "1.19.4"
            compat1.bedrock_version = "1.19.50"
            compat1.compatibility_score = 0.85
            compat1.features_supported = []
            compat1.known_issues = []
            compat1.updated_at = datetime.now()
            
            compat2 = MagicMock()
            compat2.java_version = "1.19.4"
            compat2.bedrock_version = "1.20.0"
            compat2.compatibility_score = 0.75
            compat2.features_supported = []
            compat2.known_issues = []
            compat2.updated_at = datetime.now()
            
            # Create nested mock structure for result.scalars().all()
            mock_result = MagicMock()
            mock_scalars = MagicMock()
            mock_scalars.all.return_value = [compat1, compat2]
            
            # result.scalars() returns mock_scalars
            mock_result.scalars.return_value = mock_scalars
            
            # Mock db.execute(query) returns result
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_max.return_value.isoformat.return_value = "2024-01-01T00:00:00"
            
            result = await version_compatibility_service.get_matrix_overview(mock_db)
            
            assert result["total_combinations"] == 2
            assert "1.19.4" in result["java_versions"]
            assert "1.19.50" in result["bedrock_versions"]
            assert "1.20.0" in result["bedrock_versions"]
            assert result["average_compatibility"] == 0.8
            assert result["last_updated"] == "2024-01-01T00:00:00"
            
            # Check matrix structure
            matrix = result["matrix"]
            assert matrix["1.19.4"]["1.19.50"]["score"] == 0.85
            assert matrix["1.19.4"]["1.20.0"]["score"] == 0.75
    
    @pytest.mark.asyncio
    async def test_get_supported_features(self):
        """Test getting supported features between versions."""
        mock_db = AsyncMock()
        
        with patch.object(version_compatibility_service, 'get_compatibility') as mock_get_compat, \
             patch('services.version_compatibility.ConversionPatternCRUD') as mock_patterns:
            
            # Mock compatibility
            mock_compat = MagicMock()
            mock_compat.compatibility_score = 0.8
            mock_compat.features_supported = [
                {"type": "entities", "name": "Mobs"},
                {"type": "blocks", "name": "Building blocks"}
            ]
            mock_compat.deprecated_patterns = ["old_entity_system"]
            mock_compat.migration_guides = {"steps": []}
            mock_compat.auto_update_rules = {}
            mock_compat.known_issues = []
            mock_get_compat.return_value = mock_compat
            
            # Mock patterns
            mock_pattern = MagicMock()
            mock_pattern.id = "pattern-1"
            mock_pattern.name = "Entity Conversion"
            mock_pattern.description = "Convert Java entities to Bedrock"
            mock_pattern.success_rate = 0.9
            mock_pattern.tags = ["entities", "mobs"]
            mock_pattern.get = MagicMock(side_effect=lambda key, default=None: {"tags": ["entities", "mobs"]}.get(key, default))
            mock_patterns.get_by_version = AsyncMock(return_value=[mock_pattern])
            
            result = await version_compatibility_service.get_supported_features(
                "1.19.4", mock_db, "1.19.50", "entities"
            )
            
            assert result["supported"] is True
            assert result["compatibility_score"] == 0.8
            # Filter entities by feature_type if provided
            assert len(result["features"]) == 1  # Only entities after filtering
            assert len(result["patterns"]) == 1
            assert result["patterns"][0]["name"] == "Entity Conversion"
    
    @pytest.mark.asyncio
    async def test_get_supported_features_no_compatibility(self):
        """Test getting supported features when no compatibility exists."""
        mock_db = AsyncMock()
        
        with patch.object(version_compatibility_service, 'get_compatibility') as mock_get_compat:
            # No compatibility found
            mock_get_compat.return_value = None
            
            result = await version_compatibility_service.get_supported_features(
                "1.17.1", mock_db, "1.17.0", None
            )
            
            assert result["supported"] is False
            assert "message" in result
            assert "1.17.1" in result["message"]
            assert "Java 1.17.1" in result["message"]
    
    def test_load_default_compatibility(self):
        """Test loading of default compatibility data."""
        # Test that service initializes with default data
        service = version_compatibility_service
        
        # Should have default compatibility loaded
        assert hasattr(service, 'default_compatibility')
        assert "1.19.4" in service.default_compatibility
        assert "1.20.1" in service.default_compatibility
        
        # Check structure of default data
        java_1_19 = service.default_compatibility["1.19.4"]
        assert "1.19.50" in java_1_19
        assert "score" in java_1_19["1.19.50"]
        assert "features" in java_1_19["1.19.50"]
        assert "issues" in java_1_19["1.19.50"]
