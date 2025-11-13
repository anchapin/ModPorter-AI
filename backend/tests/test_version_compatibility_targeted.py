"""
Targeted tests for version_compatibility.py to cover missing lines and reach 80%+ coverage
Focus on lines: 46-62, 79-83, 104-157, 182-224, 245-275, 294-355, 379-437, 449-475, 479-511, 521-602, 615-637, 643, 652, 664-690, 700, 755
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add source to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestVersionCompatibilityTargeted:
    """Targeted tests for missing coverage lines"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return AsyncMock()
    
    @pytest.fixture
    def service(self):
        """Create service instance for testing"""
        from src.services.version_compatibility import VersionCompatibilityService
        return VersionCompatibilityService()
    
    @pytest.mark.asyncio
    async def test_get_compatibility_with_result(self, service, mock_db):
        """Test get_compatibility with compatibility found (covers lines 46-62)"""
        mock_compatibility = Mock()
        mock_compatibility.compatibility_score = 0.8
        mock_compatibility.features_supported = ["entities", "blocks"]
        mock_compatibility.deprecated_patterns = ["old_pattern"]
        mock_compatibility.auto_update_rules = {"update": "auto"}
        
        with patch('src.services.version_compatibility.VersionCompatibilityCRUD.get_compatibility') as mock_get:
            mock_get.return_value = mock_compatibility
            
            result = await service.get_compatibility("1.19.0", "1.18.0", mock_db)
            
            assert result is not None
            assert result.compatibility_score == 0.8
            assert "entities" in result.features_supported
            assert "old_pattern" in result.deprecated_patterns
            assert result.auto_update_rules["update"] == "auto"
    
    @pytest.mark.asyncio
    async def test_get_by_java_version_with_results(self, service, mock_db):
        """Test get_by_java_version with compatibility results (covers lines 79-83)"""
        mock_compatibility1 = Mock()
        mock_compatibility1.java_version = "1.19.0"
        mock_compatibility1.bedrock_version = "1.18.0"
        mock_compatibility1.compatibility_score = 0.9
        
        mock_compatibility2 = Mock()
        mock_compatibility2.java_version = "1.19.0"
        mock_compatibility2.bedrock_version = "1.17.0"
        mock_compatibility2.compatibility_score = 0.7
        
        with patch('src.services.version_compatibility.VersionCompatibilityCRUD.get_by_java_version') as mock_get_by_java:
            mock_get_by_java.return_value = [mock_compatibility1, mock_compatibility2]
            
            result = await service.get_by_java_version("1.19.0", mock_db)
            
            assert len(result) == 2
            assert result[0].compatibility_score == 0.9  # Should be sorted by score
            assert result[1].compatibility_score == 0.7
    
    @pytest.mark.asyncio
    async def test_get_supported_features_with_patterns(self, service, mock_db):
        """Test get_supported_features with deprecated patterns and auto-update rules (covers lines 104-157)"""
        mock_compatibility = Mock()
        mock_compatibility.compatibility_score = 0.8
        mock_compatibility.features_supported = [
            {"type": "entities", "name": "Mobs"},
            {"type": "blocks", "name": "Blocks"}
        ]
        mock_compatibility.deprecated_patterns = [
            {"pattern": "old_entity_id", "replacement": "new_entity_id"},
            {"pattern": "removed_block", "replacement": None}
        ]
        mock_compatibility.auto_update_rules = {
            "entity_conversion": "automatic",
            "block_mapping": "manual_review"
        }
        
        with patch('src.services.version_compatibility.VersionCompatibilityCRUD.get_compatibility') as mock_get:
            mock_get.return_value = mock_compatibility
            
            result = await service.get_supported_features("1.19.0", "1.18.0", mock_db)
            
            assert result["supported"] is True
            assert result["compatibility_score"] == 0.8
            assert len(result["features"]) == 2
            assert any(f["type"] == "entities" for f in result["features"])
            assert any(f["type"] == "blocks" for f in result["features"])
            assert len(result["deprecated_patterns"]) == 2
            assert result["auto_update_rules"]["entity_conversion"] == "automatic"
            assert result["auto_update_rules"]["block_mapping"] == "manual_review"
    
    @pytest.mark.asyncio
    async def test_update_compatibility_existing_entry(self, service, mock_db):
        """Test updating compatibility for existing entry (covers lines 182-224)"""
        mock_existing = Mock()
        mock_existing.id = 1
        
        with patch('src.services.version_compatibility.VersionCompatibilityCRUD.get_compatibility') as mock_get, \
             patch('src.services.version_compatibility.db.knowledge_graph_crud.VersionCompatibilityCRUD.update') as mock_update:
            
            mock_get.return_value = mock_existing
            mock_update.return_value = True
            
            compatibility_data = {
                "compatibility_score": 0.85,
                "features_supported": [{"type": "entities", "name": "Mobs"}],
                "deprecated_patterns": [{"pattern": "old_pattern", "replacement": "new_pattern"}],
                "migration_guides": {"entities": {"steps": ["step1", "step2"]}},
                "auto_update_rules": {"conversion": "automatic"},
                "known_issues": [{"issue": "data_loss", "severity": "medium"}]
            }
            
            result = await service.update_compatibility(
                "1.19.0", "1.18.0", compatibility_data, mock_db
            )
            
            assert result is True
            mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_compatibility_new_entry(self, service, mock_db):
        """Test updating compatibility for new entry (covers lines 208-220)"""
        with patch('src.services.version_compatibility.VersionCompatibilityCRUD.get_compatibility') as mock_get, \
             patch('src.services.version_compatibility.VersionCompatibilityCRUD.create') as mock_create:
            
            mock_get.return_value = None
            mock_new_entry = Mock()
            mock_create.return_value = mock_new_entry
            
            compatibility_data = {
                "compatibility_score": 0.75,
                "features_supported": [{"type": "blocks", "name": "Blocks"}],
                "deprecated_patterns": [],
                "migration_guides": {},
                "auto_update_rules": {},
                "known_issues": []
            }
            
            result = await service.update_compatibility(
                "1.18.0", "1.17.0", compatibility_data, mock_db
            )
            
            assert result is True
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_compatibility_error_handling(self, service, mock_db):
        """Test error handling in update_compatibility (covers line 220)"""
        with patch('src.services.version_compatibility.VersionCompatibilityCRUD.get_compatibility') as mock_get:
            mock_get.side_effect = Exception("Database error")
            
            result = await service.update_compatibility(
                "1.19.0", "1.18.0", {}, mock_db
            )
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_get_conversion_path_with_result(self, service, mock_db):
        """Test get_conversion_path with valid result (covers lines 245-275)"""
        mock_compatibility = Mock()
        mock_compatibility.compatibility_score = 0.8
        mock_compatibility.conversion_steps = [
            {"step": "parse_entities", "complexity": "low"},
            {"step": "map_blocks", "complexity": "medium"},
            {"step": "validate_output", "complexity": "high"}
        ]
        mock_compatibility.estimated_time = "45 minutes"
        mock_compatibility.required_tools = ["converter_v2", "validator"]
        
        with patch('src.services.version_compatibility.VersionCompatibilityCRUD.get_compatibility') as mock_get:
            mock_get.return_value = mock_compatibility
            
            result = await service.get_conversion_path("1.19.0", "1.18.0", "entities", mock_db)
            
            assert result is not None
            assert result["feasible"] is True
            assert result["compatibility_score"] == 0.8
            assert len(result["conversion_steps"]) == 3
            assert result["estimated_time"] == "45 minutes"
            assert "converter_v2" in result["required_tools"]
    
    @pytest.mark.asyncio
    async def test_get_matrix_overview_with_data(self, service, mock_db):
        """Test get_matrix_overview with compatibility data (covers lines 294-355)"""
        mock_entries = [
            Mock(java_version="1.19.0", bedrock_version="1.18.0", compatibility_score=0.9),
            Mock(java_version="1.19.0", bedrock_version="1.17.0", compatibility_score=0.7),
            Mock(java_version="1.18.0", bedrock_version="1.17.0", compatibility_score=0.8),
            Mock(java_version="1.20.0", bedrock_version="1.19.0", compatibility_score=0.95)
        ]
        
        with patch('src.services.version_compatibility.db.knowledge_graph_crud.VersionCompatibilityCRUD.get_all') as mock_get_all:
            mock_get_all.return_value = mock_entries
            
            result = await service.get_matrix_overview(mock_db)
            
            assert "matrix" in result
            assert "java_versions" in result
            assert "bedrock_versions" in result
            assert "statistics" in result
            
            # Check matrix structure
            matrix = result["matrix"]
            assert "1.19.0" in matrix
            assert matrix["1.19.0"]["1.18.0"] == 0.9
            assert matrix["1.19.0"]["1.17.0"] == 0.7
            
            # Check statistics
            stats = result["statistics"]
            assert stats["total_combinations"] == 4
            assert 0.7 <= stats["average_compatibility"] <= 0.9
            assert stats["best_combination"]["java_version"] == "1.20.0"
            assert stats["best_combination"]["score"] == 0.95
            assert "worst_combination" in stats
    
    @pytest.mark.asyncio
    async def test_generate_migration_guide_with_data(self, service, mock_db):
        """Test generate_migration_guide with migration data (covers lines 379-437)"""
        mock_compatibility = Mock()
        mock_compatibility.compatibility_score = 0.6
        mock_compatibility.features_supported = [{"type": "entities", "name": "Mobs"}]
        mock_compatibility.migration_guides = {
            "entities": {
                "steps": [
                    {"action": "extract_entity_data", "tool": "parser"},
                    {"action": "transform_entity_ids", "tool": "mapper"},
                    {"action": "validate_entities", "tool": "validator"}
                ],
                "complexity": "medium",
                "estimated_time": "30 minutes"
            }
        }
        mock_compatibility.known_issues = [
            {"issue": "entity_id_conflicts", "severity": "medium", "solution": "manual_review"},
            {"issue": "data_loss_risk", "severity": "low", "solution": "backup_first"}
        ]
        
        with patch('src.services.version_compatibility.VersionCompatibilityCRUD.get_compatibility') as mock_get, \
             patch.object(service, '_find_closest_compatibility') as mock_closest, \
             patch.object(service, '_find_optimal_conversion_path') as mock_path:
            
            mock_get.return_value = mock_compatibility
            mock_closest.return_value = mock_compatibility
            mock_path.return_value = {
                "path": ["1.19.0", "1.18.5", "1.18.0"],
                "steps": ["conversion1", "conversion2"],
                "confidence": 0.8
            }
            
            result = await service.generate_migration_guide(
                "1.19.0", "1.18.0", "entities", mock_db
            )
            
            assert result["feasible"] is True
            assert result["confidence"] == 0.6
            assert "steps" in result
            assert len(result["known_issues"]) == 2
            assert any(step["action"] == "extract_entity_data" for step in result["steps"])
    
    def test_find_closest_compatibility_with_entries(self, service):
        """Test _find_closest_compatibility with entries (covers lines 449-475)"""
        mock_entries = [
            Mock(java_version="1.19.0", bedrock_version="1.18.0", compatibility_score=0.9),
            Mock(java_version="1.19.1", bedrock_version="1.18.0", compatibility_score=0.85),
            Mock(java_version="1.18.0", bedrock_version="1.18.0", compatibility_score=0.95)
        ]
        
        result = service._find_closest_compatibility("1.19.2", "1.18.0", mock_entries)
        
        assert result is not None
        assert result.java_version in ["1.19.0", "1.19.1"]  # Closest versions
    
    def test_find_closest_version_operations(self, service):
        """Test _find_closest_version different scenarios (covers lines 479-511)"""
        versions = ["1.16.0", "1.16.1", "1.16.2", "1.17.0", "1.18.0"]
        
        # Test exact match
        result = service._find_closest_version("1.17.0", versions)
        assert result == "1.17.0"
        
        # Test closest lower version
        result = service._find_closest_version("1.16.5", versions)
        assert result == "1.16.2"
        
        # Test version higher than all available
        result = service._find_closest_version("1.19.0", versions)
        assert result == "1.18.0"
        
        # Test version lower than all available
        result = service._find_closest_version("1.15.0", versions)
        assert result == "1.16.0"
        
        # Test empty list
        result = service._find_closest_version("1.19.0", [])
        assert result == "1.19.0"  # Default behavior
    
    @pytest.mark.asyncio
    async def test_find_optimal_conversion_path_with_data(self, service):
        """Test _find_optimal_conversion_path with compatibility data (covers lines 521-602)"""
        mock_entries = [
            Mock(java_version="1.19.0", bedrock_version="1.18.0", compatibility_score=0.9),
            Mock(java_version="1.19.0", bedrock_version="1.17.0", compatibility_score=0.6),
            Mock(java_version="1.18.0", bedrock_version="1.17.0", compatibility_score=0.8),
            Mock(java_version="1.20.0", bedrock_version="1.18.0", compatibility_score=0.95)
        ]
        
        result = service._find_optimal_conversion_path("1.19.0", "1.17.0", mock_entries)
        
        assert "path" in result
        assert "steps" in result
        assert "confidence" in result
        
        # Should find path through 1.18.0 for better compatibility
        path = result["path"]
        assert "1.19.0" in path
        assert "1.17.0" in path
    
    def test_get_relevant_patterns_with_matches(self, service):
        """Test _get_relevant_patterns with matching patterns (covers lines 615-637)"""
        patterns = [
            {
                "feature_type": "entities", 
                "pattern": "entity_id", 
                "applicable_versions": ["1.18.*"],
                "complexity": "low"
            },
            {
                "feature_type": "blocks", 
                "pattern": "block_state", 
                "applicable_versions": ["1.19.*"],
                "complexity": "medium"
            },
            {
                "feature_type": "entities", 
                "pattern": "entity_data", 
                "applicable_versions": ["1.*"],
                "complexity": "high"
            }
        ]
        
        result = service._get_relevant_patterns("entities", "1.18.0", patterns)
        
        assert len(result) >= 2  # Should match entity_id and entity_data patterns
        assert any(p["pattern"] == "entity_id" for p in result)
        assert any(p["pattern"] == "entity_data" for p in result)
    
    def test_get_sorted_java_versions_with_entries(self, service):
        """Test _get_sorted_java_versions with entries (covers line 643)"""
        mock_entries = [
            Mock(java_version="1.19.0"),
            Mock(java_version="1.16.5"),
            Mock(java_version="1.18.0"),
            Mock(java_version="1.17.1")
        ]
        
        result = service._get_sorted_java_versions(mock_entries)
        
        assert result == ["1.16.5", "1.17.1", "1.18.0", "1.19.0"]
    
    def test_get_sorted_bedrock_versions_with_entries(self, service):
        """Test _get_sorted_bedrock_versions with entries (covers line 652)"""
        mock_entries = [
            Mock(bedrock_version="1.19.0"),
            Mock(bedrock_version="1.16.5"),
            Mock(bedrock_version="1.18.0"),
            Mock(bedrock_version="1.17.1")
        ]
        
        result = service._get_sorted_bedrock_versions(mock_entries)
        
        assert result == ["1.16.5", "1.17.1", "1.18.0", "1.19.0"]
    
    @pytest.mark.asyncio
    async def test_find_best_bedrock_match_with_entries(self, service, mock_db):
        """Test _find_best_bedrock_match with entries (covers lines 664-690)"""
        entries = [
            Mock(bedrock_version="1.18.0", compatibility_score=0.9),
            Mock(bedrock_version="1.18.1", compatibility_score=0.85),
            Mock(bedrock_version="1.17.0", compatibility_score=0.7)
        ]
        
        result = await service._find_best_bedrock_match(mock_db, "1.19.0", "entities")
        
        assert result is not None
        assert result.bedrock_version in ["1.18.0", "1.18.1"]
    
    def test_generate_direct_migration_steps_with_data(self, service):
        """Test _generate_direct_migration_steps with migration data (covers line 700)"""
        mock_compatibility = Mock()
        mock_compatibility.migration_guides = {
            "entities": {
                "steps": [
                    {"action": "convert_entity_ids", "tool": "mapper"},
                    {"action": "update_entity_data", "tool": "transformer"}
                ],
                "complexity": "medium",
                "estimated_time": "20 minutes"
            }
        }
        
        result = service._generate_direct_migration_steps(mock_compatibility, "entities", [], mock_db)
        
        assert "steps" in result
        assert "complexity" in result
        assert len(result["steps"]) == 2
        assert any(step["action"] == "convert_entity_ids" for step in result["steps"])
        assert result["complexity"] == "medium"
    
    def test_generate_gradual_migration_steps_with_path(self, service):
        """Test _generate_gradual_migration_steps with conversion path (covers line 755)"""
        path = ["1.19.0", "1.18.0", "1.17.0"]
        
        result = service._generate_gradual_migration_steps(path, "entities", [], mock_db)
        
        assert "phases" in result
        assert len(result["phases"]) >= 1  # Should have at least one phase


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
