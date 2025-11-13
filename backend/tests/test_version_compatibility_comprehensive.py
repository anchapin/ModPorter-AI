"""
Comprehensive tests for version_compatibility.py
Focus on improving coverage for complex methods and uncovered areas
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add source to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestVersionCompatibilityServiceAdvanced:
    """Advanced test suite for uncovered complex methods"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        return AsyncMock()
    
    @pytest.fixture
    def service(self):
        """Create service instance for testing"""
        with patch.dict('sys.modules', {
            'db': Mock(),
            'db.knowledge_graph_crud': Mock(),
            'db.models': Mock()
        }):
            from src.services.version_compatibility import VersionCompatibilityService
            return VersionCompatibilityService()
    
    @pytest.fixture
    def mock_compatibility_data(self):
        """Mock version compatibility data"""
        class MockCompatibility:
            def __init__(self, java_version, bedrock_version, score=0.8):
                self.java_version = java_version
                self.bedrock_version = bedrock_version
                self.compatibility_score = score
                self.features_supported = ["blocks", "entities"]
                self.known_issues = []
                self.updated_at = AsyncMock()
                self.updated_at.isoformat.return_value = "2024-01-01T00:00:00"
        
        return [
            MockCompatibility("1.19.4", "1.19.0", 0.9),
            MockCompatibility("1.20.1", "1.20.0", 0.85),
            MockCompatibility("1.20.6", "1.20.60", 0.95)
        ]
    
    @pytest.mark.asyncio
    async def test_get_compatibility_with_exact_match(self, service, mock_db):
        """Test get_compatibility with exact database match"""
        # Mock database response
        mock_compatibility = Mock()
        mock_compatibility.java_version = "1.20.1"
        mock_compatibility.bedrock_version = "1.20.0"
        mock_compatibility.compatibility_score = 0.85
        
        with patch('src.services.version_compatibility.VersionCompatibilityCRUD') as mock_crud:
            mock_crud.get_compatibility.return_value = mock_compatibility
            
            result = await service.get_compatibility("1.20.1", "1.20.0", mock_db)
            
            assert result is not None
            assert result.java_version == "1.20.1"
            assert result.bedrock_version == "1.20.0"
            mock_crud.get_compatibility.assert_called_once_with(mock_db, "1.20.1", "1.20.0")
    
    @pytest.mark.asyncio
    async def test_get_compatibility_with_closest_match(self, service, mock_db):
        """Test get_compatibility when falling back to closest versions"""
        with patch('src.services.version_compatibility.VersionCompatibilityCRUD') as mock_crud:
            # No exact match found
            mock_crud.get_compatibility.return_value = None
            
            # Mock closest compatibility finding
            with patch.object(service, '_find_closest_compatibility') as mock_closest:
                mock_closest.return_value = Mock(compatibility_score=0.7)
                
                result = await service.get_compatibility("1.20.1", "1.20.0", mock_db)
                
                assert result is not None
                mock_closest.assert_called_once_with(mock_db, "1.20.1", "1.20.0")
    
    @pytest.mark.asyncio
    async def test_get_compatibility_error_handling(self, service, mock_db):
        """Test get_compatibility error handling"""
        with patch('src.services.version_compatibility.VersionCompatibilityCRUD') as mock_crud:
            mock_crud.get_compatibility.side_effect = Exception("Database error")
            
            result = await service.get_compatibility("1.20.1", "1.20.0", mock_db)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_by_java_version_success(self, service, mock_db):
        """Test get_by_java_version with successful query"""
        mock_compatibilities = [
            Mock(java_version="1.20.1", bedrock_version="1.20.0"),
            Mock(java_version="1.20.1", bedrock_version="1.19.0")
        ]
        
        with patch('src.services.version_compatibility.VersionCompatibilityCRUD') as mock_crud:
            mock_crud.get_by_java_version.return_value = mock_compatibilities
            
            result = await service.get_by_java_version("1.20.1", mock_db)
            
            assert len(result) == 2
            mock_crud.get_by_java_version.assert_called_once_with(mock_db, "1.20.1")
    
    @pytest.mark.asyncio
    async def test_get_by_java_version_error_handling(self, service, mock_db):
        """Test get_by_java_version error handling"""
        with patch('src.services.version_compatibility.VersionCompatibilityCRUD') as mock_crud:
            mock_crud.get_by_java_version.side_effect = Exception("Database error")
            
            result = await service.get_by_java_version("1.20.1", mock_db)
            
            assert result == []
    
    @pytest.mark.asyncio
    async def test_get_supported_features_with_compatibility(self, service, mock_db):
        """Test get_supported_features with valid compatibility"""
        mock_compatibility = Mock()
        mock_compatibility.features_supported = {
            "blocks": {"supported": True, "coverage": 0.9},
            "entities": {"supported": True, "coverage": 0.8},
            "items": {"supported": False, "coverage": 0.0}
        }
        mock_compatibility.known_issues = ["Some blocks may not convert correctly"]
        
        with patch.object(service, 'get_compatibility') as mock_get_compat:
            mock_get_compat.return_value = mock_compatibility
            
            result = await service.get_supported_features(
                "1.20.1", mock_db, "1.20.0", "blocks"
            )
            
            assert result["java_version"] == "1.20.1"
            assert result["bedrock_version"] == "1.20.0"
            assert "blocks" in result["features"]
            assert result["features"]["blocks"]["supported"] is True
            assert len(result["known_issues"]) == 1
    
    @pytest.mark.asyncio
    async def test_get_supported_features_no_compatibility(self, service, mock_db):
        """Test get_supported_features when no compatibility found"""
        with patch.object(service, 'get_compatibility') as mock_get_compat:
            mock_get_compat.return_value = None
            
            result = await service.get_supported_features(
                "1.20.1", mock_db, "1.20.0", "blocks"
            )
            
            assert result["error"] == "No compatibility data found"
            assert "No compatibility data available" in result["message"]
    
    @pytest.mark.asyncio
    async def test_get_matrix_overview_with_data(self, service, mock_db, mock_compatibility_data):
        """Test get_matrix_overview with compatibility data"""
        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = mock_compatibility_data
        mock_db.execute.return_value = mock_result
        
        result = await service.get_matrix_overview(mock_db)
        
        assert result["total_combinations"] == 3
        assert len(result["java_versions"]) == 3
        assert len(result["bedrock_versions"]) == 3
        assert result["average_compatibility"] == 0.9  # (0.9 + 0.85 + 0.95) / 3
        assert "compatibility_distribution" in result
        assert "matrix" in result
    
    @pytest.mark.asyncio
    async def test_get_matrix_overview_no_data(self, service, mock_db):
        """Test get_matrix_overview with no compatibility data"""
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        result = await service.get_matrix_overview(mock_db)
        
        assert result["total_combinations"] == 0
        assert result["java_versions"] == []
        assert result["bedrock_versions"] == []
        assert result["average_compatibility"] == 0.0
        assert result["matrix"] == {}
    
    @pytest.mark.asyncio
    async def test_get_matrix_overview_error_handling(self, service, mock_db):
        """Test get_matrix_overview error handling"""
        mock_db.execute.side_effect = Exception("Database error")
        
        result = await service.get_matrix_overview(mock_db)
        
        assert "error" in result
        assert result["error"] == "Database error"
    
    @pytest.mark.asyncio
    async def test_generate_migration_guide_success(self, service, mock_db):
        """Test generate_migration_guide with valid data"""
        mock_compatibility = Mock()
        mock_compatibility.compatibility_score = 0.85
        mock_compatibility.features_supported = {
            "blocks": {"supported": True, "coverage": 0.9},
            "entities": {"supported": True, "coverage": 0.8}
        }
        mock_compatibility.known_issues = []
        mock_compatibility.java_version = "1.20.1"
        mock_compatibility.bedrock_version = "1.20.0"
        
        with patch.object(service, 'get_compatibility') as mock_get_compat:
            mock_get_compat.return_value = mock_compatibility
            
            with patch.object(service, '_generate_direct_migration_steps') as mock_direct:
                mock_direct.return_value = [
                    {"step": "convert_blocks", "description": "Convert all blocks"}
                ]
                
                result = await service.generate_migration_guide(
                    "1.20.1", "1.20.0", ["blocks", "entities"], mock_db
                )
                
                assert result["source_version"] == "1.20.1"
                assert result["target_version"] == "1.20.0"
                assert result["compatibility_score"] == 0.85
                assert "migration_steps" in result
                assert len(result["migration_steps"]) == 1
    
    @pytest.mark.asyncio
    async def test_generate_migration_guide_no_compatibility(self, service, mock_db):
        """Test generate_migration_guide when no compatibility found"""
        with patch.object(service, 'get_compatibility') as mock_get_compat:
            mock_get_compat.return_value = None
            
            result = await service.generate_migration_guide(
                "1.20.1", "1.20.0", ["blocks"], mock_db
            )
            
            assert result["error"] == "No compatibility data found"
            assert "No migration data available" in result["message"]
    
    @pytest.mark.asyncio
    async def test_find_optimal_conversion_path_direct(self, service, mock_db):
        """Test _find_optimal_conversion_path with direct compatibility"""
        mock_compatibility = Mock()
        mock_compatibility.compatibility_score = 0.9
        
        with patch.object(service, 'get_compatibility') as mock_get_compat:
            mock_get_compat.return_value = mock_compatibility
            
            result = await service._find_optimal_conversion_path(
                "1.20.1", "1.20.0", mock_db, "blocks"
            )
            
            assert result["path_type"] == "direct"
            assert result["compatibility_score"] == 0.9
            assert "patterns" in result
    
    @pytest.mark.asyncio
    async def test_find_optimal_conversion_path_intermediate(self, service, mock_db):
        """Test _find_optimal_conversion_path with intermediate steps"""
        mock_compatibility_low = Mock()
        mock_compatibility_low.compatibility_score = 0.3  # Low score - need intermediate
        
        mock_compatibility_intermediate = Mock()
        mock_compatibility_intermediate.compatibility_score = 0.7
        
        mock_compatibility_final = Mock()
        mock_compatibility_final.compatibility_score = 0.8
        
        with patch.object(service, 'get_compatibility') as mock_get_compat:
            # First call returns low compatibility
            mock_get_compat.return_value = mock_compatibility_low
            
            with patch.object(service, '_get_sorted_java_versions') as mock_java_versions:
                mock_java_versions.return_value = ["1.19.4", "1.20.1", "1.20.6"]
                
                with patch.object(service, '_get_sorted_bedrock_versions') as mock_bedrock_versions:
                    mock_bedrock_versions.return_value = ["1.19.0", "1.20.0", "1.20.60"]
                    
                    with patch.object(service, '_find_best_bedrock_match') as mock_best_match:
                        mock_best_match.return_value = "1.20.0"
                        
                        # Configure subsequent calls
                        def side_effect(*args):
                            if args[0] == "1.20.1" and args[1] == "1.20.0":
                                return mock_compatibility_intermediate
                            elif args[0] == "1.20.0" and args[1] == "1.20.0":
                                return mock_compatibility_final
                            return None
                        
                        mock_get_compat.side_effect = side_effect
                        
                        with patch.object(service, '_get_relevant_patterns') as mock_patterns:
                            mock_patterns.return_value = []
                            
                            result = await service._find_optimal_conversion_path(
                                "1.20.1", "1.20.0", mock_db, "blocks"
                            )
                            
                            assert result["path_type"] == "intermediate"
                            assert "steps" in result
                            assert len(result["steps"]) == 2
    
    @pytest.mark.asyncio
    async def test_find_optimal_conversion_path_version_not_found(self, service, mock_db):
        """Test _find_optimal_conversion_path with unknown versions"""
        with patch.object(service, 'get_compatibility') as mock_get_compat:
            mock_get_compat.return_value = None  # No compatibility found
            
            with patch.object(service, '_get_sorted_java_versions') as mock_java_versions:
                mock_java_versions.return_value = ["1.19.4", "1.20.1", "1.20.6"]
                
                result = await service._find_optimal_conversion_path(
                    "1.21.0", "1.20.0", mock_db, "blocks"
                )
                
                assert result["path_type"] == "failed"
                assert "Source Java version 1.21.0 not found" in result["message"]
    
    @pytest.mark.asyncio
    async def test_get_relevant_patterns_success(self, service, mock_db):
        """Test _get_relevant_patterns with matching patterns"""
        mock_pattern = Mock()
        mock_pattern.id = "pattern_1"
        mock_pattern.name = "Block Conversion Pattern"
        mock_pattern.description = "Converts blocks between versions"
        mock_pattern.success_rate = 0.85
        mock_pattern.tags = ["blocks", "conversion"]
        
        with patch('src.services.version_compatibility.ConversionPatternCRUD') as mock_crud:
            mock_crud.get_by_version.return_value = [mock_pattern]
            
            result = await service._get_relevant_patterns(
                mock_db, "1.20.1", "blocks"
            )
            
            assert len(result) == 1
            assert result[0]["id"] == "pattern_1"
            assert result[0]["name"] == "Block Conversion Pattern"
            assert result[0]["success_rate"] == 0.85
            mock_crud.get_by_version.assert_called_once_with(
                mock_db, minecraft_version="1.20.1", validation_status="validated"
            )
    
    @pytest.mark.asyncio
    async def test_get_relevant_patterns_no_match(self, service, mock_db):
        """Test _get_relevant_patterns with no matching patterns"""
        mock_pattern = Mock()
        mock_pattern.id = "pattern_1"
        mock_pattern.name = "Entity Conversion Pattern"
        mock_pattern.description = "Converts entities between versions"
        mock_pattern.success_rate = 0.75
        mock_pattern.tags = ["entities", "conversion"]
        # Mock the contains method to return False
        mock_pattern.name.lower.return_value.contains.return_value = False
        
        with patch('src.services.version_compatibility.ConversionPatternCRUD') as mock_crud:
            mock_crud.get_by_version.return_value = [mock_pattern]
            
            result = await service._get_relevant_patterns(
                mock_db, "1.20.1", "blocks"
            )
            
            assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_get_relevant_patterns_error_handling(self, service, mock_db):
        """Test _get_relevant_patterns error handling"""
        with patch('src.services.version_compatibility.ConversionPatternCRUD') as mock_crud:
            mock_crud.get_by_version.side_effect = Exception("Database error")
            
            result = await service._get_relevant_patterns(
                mock_db, "1.20.1", "blocks"
            )
            
            assert result == []
    
    @pytest.mark.asyncio
    async def test_get_sorted_java_versions(self, service, mock_db):
        """Test _get_sorted_java_versions returns predefined list"""
        result = await service._get_sorted_java_versions(mock_db)
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert "1.14.4" in result
        assert "1.21.0" in result
        # Check that versions are in expected order
        assert result == sorted(result, key=lambda x: tuple(map(int, x.split('.'))))
    
    @pytest.mark.asyncio
    async def test_get_sorted_bedrock_versions(self, service, mock_db):
        """Test _get_sorted_bedrock_versions returns predefined list"""
        result = await service._get_sorted_bedrock_versions(mock_db)
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert "1.14.0" in result
        assert "1.21.0" in result
        # Check that versions are in expected order
        assert result == sorted(result, key=lambda x: tuple(map(int, x.split('.'))))
    
    @pytest.mark.asyncio
    async def test_find_best_bedrock_match_success(self, service, mock_db):
        """Test _find_best_bedrock_match with successful finding"""
        mock_compatibility = Mock()
        mock_compatibility.bedrock_version = "1.20.0"
        mock_compatibility.compatibility_score = 0.85
        
        with patch.object(service, 'get_by_java_version') as mock_get_by_java:
            mock_get_by_java.return_value = [mock_compatibility]
            
            result = await service._find_best_bedrock_match(
                mock_db, "1.20.1", "blocks"
            )
            
            assert result == "1.20.0"
            mock_get_by_java.assert_called_once_with(mock_db, "1.20.1")
    
    @pytest.mark.asyncio
    async def test_find_best_bedrock_match_no_match(self, service, mock_db):
        """Test _find_best_bedrock_match with no suitable match"""
        with patch.object(service, 'get_by_java_version') as mock_get_by_java:
            mock_get_by_java.return_value = []
            
            result = await service._find_best_bedrock_match(
                mock_db, "1.20.1", "blocks"
            )
            
            assert result is None


class TestVersionCompatibilityServiceUpdate:
    """Test suite for update compatibility functionality"""
    
    @pytest.fixture
    def service(self):
        """Create service instance for testing"""
        with patch.dict('sys.modules', {
            'db': Mock(),
            'db.knowledge_graph_crud': Mock(),
            'db.models': Mock()
        }):
            from src.services.version_compatibility import VersionCompatibilityService
            return VersionCompatibilityService()
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_update_compatibility_create_new(self, service, mock_db):
        """Test update_compatibility creates new entry when none exists"""
        with patch('src.services.version_compatibility.VersionCompatibilityCRUD') as mock_crud:
            mock_crud.get_compatibility.return_value = None
            mock_crud.create_compatibility.return_value = Mock(
                java_version="1.20.1",
                bedrock_version="1.20.0",
                compatibility_score=0.85
            )
            
            result = await service.update_compatibility(
                "1.20.1", "1.20.0", 0.85,
                ["blocks", "entities"], ["issue1"], mock_db
            )
            
            assert result is not None
            assert result.java_version == "1.20.1"
            assert result.bedrock_version == "1.20.0"
            assert result.compatibility_score == 0.85
            mock_crud.create_compatibility.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_compatibility_update_existing(self, service, mock_db):
        """Test update_compatibility updates existing entry"""
        existing_compat = Mock()
        existing_compat.id = "existing_id"
        
        with patch('src.services.version_compatibility.VersionCompatibilityCRUD') as mock_crud:
            mock_crud.get_compatibility.return_value = existing_compat
            mock_crud.update_compatibility.return_value = Mock(
                java_version="1.20.1",
                bedrock_version="1.20.0",
                compatibility_score=0.9
            )
            
            result = await service.update_compatibility(
                "1.20.1", "1.20.0", 0.9,
                ["blocks"], [], mock_db
            )
            
            assert result is not None
            assert result.java_version == "1.20.1"
            assert result.bedrock_version == "1.20.0"
            assert result.compatibility_score == 0.9
            mock_crud.update_compatibility.assert_called_once()


class TestVersionCompatibilityServiceEdgeCases:
    """Test suite for edge cases and internal utility methods"""
    
    @pytest.fixture
    def service(self):
        """Create service instance for testing"""
        with patch.dict('sys.modules', {
            'db': Mock(),
            'db.knowledge_graph_crud': Mock(),
            'db.models': Mock()
        }):
            from src.services.version_compatibility import VersionCompatibilityService
            return VersionCompatibilityService()
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_find_closest_compatibility_fallback(self, service, mock_db):
        """Test _find_closest_compatibility fallback behavior"""
        with patch.object(service, 'get_by_java_version') as mock_get_by_java:
            mock_get_by_java.return_value = []
            
            result = await service._find_closest_compatibility(
                mock_db, "1.20.1", "1.20.0"
            )
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_find_closest_compatibility_partial_match(self, service, mock_db):
        """Test _find_closest_compatibility with partial version matches"""
        mock_compat = Mock()
        mock_compat.java_version = "1.20.0"  # Close match to 1.20.1
        mock_compat.bedrock_version = "1.20.0"
        mock_compat.compatibility_score = 0.7
        
        with patch.object(service, 'get_by_java_version') as mock_get_by_java:
            mock_get_by_java.return_value = [mock_compat]
            
            result = await service._find_closest_compatibility(
                mock_db, "1.20.1", "1.20.0"
            )
            
            assert result is not None
            assert result.java_version == "1.20.0"
    
    def test_load_default_compatibility(self, service):
        """Test _load_default_compatibility returns data"""
        result = service._load_default_compatibility()
        
        # Should return some default compatibility data
        assert isinstance(result, dict)
        # The method should not raise exceptions
    
    @pytest.mark.asyncio
    async def test_generate_direct_migration_steps(self, service, mock_db):
        """Test _generate_direct_migration_steps creates valid steps"""
        mock_compatibility = Mock()
        mock_compatibility.features_supported = {
            "blocks": {"supported": True, "coverage": 0.9},
            "entities": {"supported": True, "coverage": 0.8}
        }
        
        steps = service._generate_direct_migration_steps(
            mock_compatibility, ["blocks", "entities"]
        )
        
        assert isinstance(steps, list)
        # Should have steps for each supported feature
        assert len(steps) >= 1
        
        # Check step structure
        for step in steps:
            assert "step" in step
            assert "description" in step
            assert "priority" in step
    
    @pytest.mark.asyncio
    async def test_generate_gradual_migration_steps(self, service, mock_db):
        """Test _generate_gradual_migration_steps creates phased approach"""
        mock_compatibility = Mock()
        mock_compatibility.features_supported = {
            "blocks": {"supported": True, "coverage": 0.9},
            "entities": {"supported": True, "coverage": 0.8},
            "items": {"supported": True, "coverage": 0.6}
        }
        
        steps = service._generate_gradual_migration_steps(
            mock_compatibility, ["blocks", "entities", "items"]
        )
        
        assert isinstance(steps, list)
        # Should have phases for gradual migration
        assert len(steps) >= 1
        
        # Check for phase structure
        for step in steps:
            assert "phase" in step or "step" in step
            assert "description" in step
            assert "features" in step or "priority" in step


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
