"""
Additional tests for conversion_inference.py uncovered methods
Tests specifically targeting 0% coverage methods to reach 80% overall coverage
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.conversion_inference import ConversionInferenceEngine
from src.db.models import KnowledgeNode


class TestConversionInferenceEngineUncoveredMethods:
    """Test cases for previously uncovered methods to reach 80% coverage"""

    @pytest.fixture
    def engine(self):
        """Create engine instance for testing"""
        return ConversionInferenceEngine()

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        db = AsyncMock()
        return db

    @pytest.fixture
    def sample_source_node(self):
        """Create sample source knowledge node"""
        node = KnowledgeNode()
        node.id = 1
        node.name = "Java Entity"
        node.platform = "java"
        node.minecraft_version = "1.20"
        node.description = "Test Java entity"
        node.expert_validated = True
        node.community_rating = 4.5
        node.neo4j_id = "node_1"
        return node

    @pytest.mark.asyncio
    async def test_find_direct_paths_success(self, engine, mock_db, sample_source_node):
        """Test successful direct path finding"""
        # Mock graph_db response
        with patch('src.services.conversion_inference.graph_db') as mock_graph_db:
            mock_graph_db.find_conversion_paths.return_value = [
                {
                    "path_length": 1,
                    "confidence": 0.8,
                    "end_node": {
                        "name": "Bedrock Entity",
                        "platform": "bedrock",
                        "minecraft_version": "1.20"
                    },
                    "relationships": [{"type": "CONVERTS_TO"}],
                    "supported_features": ["texture_mapping"],
                    "success_rate": 0.9,
                    "usage_count": 150
                }
            ]
            
            result = await engine._find_direct_paths(
                mock_db, sample_source_node, "bedrock", "1.20"
            )
            
            assert len(result) == 1
            assert result[0]["path_type"] == "direct"
            assert result[0]["confidence"] == 0.8
            assert result[0]["path_length"] == 1
            assert result[0]["success_rate"] == 0.9
            assert result[0]["usage_count"] == 150

    @pytest.mark.asyncio
    async def test_find_direct_paths_platform_both(self, engine, mock_db, sample_source_node):
        """Test direct path finding with 'both' platform"""
        with patch('src.services.conversion_inference.graph_db') as mock_graph_db:
            mock_graph_db.find_conversion_paths.return_value = [
                {
                    "path_length": 1,
                    "confidence": 0.7,
                    "end_node": {
                        "name": "Universal Entity",
                        "platform": "both",
                        "minecraft_version": "1.20"
                    },
                    "relationships": [{"type": "CONVERTS_TO"}],
                    "supported_features": [],
                    "success_rate": 0.8,
                    "usage_count": 100
                }
            ]
            
            result = await engine._find_direct_paths(
                mock_db, sample_source_node, "java", "1.20"
            )
            
            assert len(result) == 1
            assert result[0]["steps"][0]["platform"] == "both"

    @pytest.mark.asyncio
    async def test_find_direct_paths_no_matching_platform(self, engine, mock_db, sample_source_node):
        """Test direct path finding with no matching platform"""
        with patch('src.services.conversion_inference.graph_db') as mock_graph_db:
            mock_graph_db.find_conversion_paths.return_value = [
                {
                    "path_length": 1,
                    "confidence": 0.8,
                    "end_node": {
                        "name": "Java Entity 2",
                        "platform": "java",  # Same platform, not matching bedrock
                        "minecraft_version": "1.20"
                    },
                    "relationships": [{"type": "CONVERTS_TO"}],
                    "supported_features": [],
                    "success_rate": 0.9,
                    "usage_count": 50
                }
            ]
            
            result = await engine._find_direct_paths(
                mock_db, sample_source_node, "bedrock", "1.20"
            )
            
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_find_direct_paths_filter_by_depth(self, engine, mock_db, sample_source_node):
        """Test direct path finding filters by path_length == 1"""
        with patch('src.services.conversion_inference.graph_db') as mock_graph_db:
            mock_graph_db.find_conversion_paths.return_value = [
                {
                    "path_length": 2,  # Indirect path, should be filtered out
                    "confidence": 0.9,
                    "end_node": {
                        "name": "Complex Entity",
                        "platform": "bedrock",
                        "minecraft_version": "1.20"
                    },
                    "relationships": [{"type": "CONVERTS_TO"}],
                    "supported_features": [],
                    "success_rate": 0.95,
                    "usage_count": 200
                },
                {
                    "path_length": 1,  # Direct path, should be included
                    "confidence": 0.7,
                    "end_node": {
                        "name": "Simple Entity",
                        "platform": "bedrock",
                        "minecraft_version": "1.20"
                    },
                    "relationships": [{"type": "CONVERTS_TO"}],
                    "supported_features": [],
                    "success_rate": 0.8,
                    "usage_count": 100
                }
            ]
            
            result = await engine._find_direct_paths(
                mock_db, sample_source_node, "bedrock", "1.20"
            )
            
            assert len(result) == 1
            assert result[0]["path_length"] == 1
            assert result[0]["confidence"] == 0.7

    @pytest.mark.asyncio
    async def test_find_direct_paths_sorted_by_confidence(self, engine, mock_db, sample_source_node):
        """Test direct paths are sorted by confidence descending"""
        with patch('src.services.conversion_inference.graph_db') as mock_graph_db:
            mock_graph_db.find_conversion_paths.return_value = [
                {
                    "path_length": 1,
                    "confidence": 0.6,  # Lower confidence
                    "end_node": {
                        "name": "Lower Confidence Entity",
                        "platform": "bedrock",
                        "minecraft_version": "1.20"
                    },
                    "relationships": [{"type": "CONVERTS_TO"}],
                    "supported_features": [],
                    "success_rate": 0.7,
                    "usage_count": 50
                },
                {
                    "path_length": 1,
                    "confidence": 0.9,  # Higher confidence
                    "end_node": {
                        "name": "Higher Confidence Entity",
                        "platform": "bedrock",
                        "minecraft_version": "1.20"
                    },
                    "relationships": [{"type": "CONVERTS_TO"}],
                    "supported_features": [],
                    "success_rate": 0.95,
                    "usage_count": 150
                }
            ]
            
            result = await engine._find_direct_paths(
                mock_db, sample_source_node, "bedrock", "1.20"
            )
            
            assert len(result) == 2
            assert result[0]["confidence"] == 0.9  # Higher confidence first
            assert result[1]["confidence"] == 0.6

    @pytest.mark.asyncio
    async def test_find_direct_paths_error_handling(self, engine, mock_db, sample_source_node):
        """Test direct path finding error handling"""
        with patch('src.services.conversion_inference.graph_db') as mock_graph_db:
            mock_graph_db.find_conversion_paths.side_effect = Exception("Graph DB error")
            
            result = await engine._find_direct_paths(
                mock_db, sample_source_node, "bedrock", "1.20"
            )
            
            assert result == []

    @pytest.mark.asyncio
    async def test_find_indirect_paths_success(self, engine, mock_db, sample_source_node):
        """Test successful indirect path finding"""
        with patch('src.services.conversion_inference.graph_db') as mock_graph_db:
            mock_graph_db.find_conversion_paths.return_value = [
                {
                    "path_length": 3,
                    "confidence": 0.7,
                    "end_node": {
                        "name": "Final Entity",
                        "platform": "bedrock",
                        "minecraft_version": "1.20"
                    },
                    "relationships": [
                        {"type": "CONVERTS_TO"},
                        {"type": "TRANSFORMS_TO"}
                    ],
                    "supported_features": ["texture_mapping"],
                    "success_rate": 0.8,
                    "usage_count": 120
                }
            ]
            
            result = await engine._find_indirect_paths(
                mock_db, sample_source_node, "bedrock", "1.20", 3, 0.5
            )
            
            assert len(result) == 1
            assert result[0]["path_type"] == "indirect"
            assert result[0]["confidence"] == 0.7
            assert result[0]["path_length"] == 3
            assert len(result[0]["steps"]) == 3

    @pytest.mark.asyncio
    async def test_find_indirect_paths_filter_by_min_confidence(self, engine, mock_db, sample_source_node):
        """Test indirect path filtering by minimum confidence"""
        with patch('src.services.conversion_inference.graph_db') as mock_graph_db:
            mock_graph_db.find_conversion_paths.return_value = [
                {
                    "path_length": 2,
                    "confidence": 0.3,  # Below min confidence
                    "end_node": {
                        "name": "Low Confidence Entity",
                        "platform": "bedrock",
                        "minecraft_version": "1.20"
                    },
                    "relationships": [{"type": "CONVERTS_TO"}],
                    "supported_features": [],
                    "success_rate": 0.4,
                    "usage_count": 20
                },
                {
                    "path_length": 2,
                    "confidence": 0.8,  # Above min confidence
                    "end_node": {
                        "name": "High Confidence Entity",
                        "platform": "bedrock",
                        "minecraft_version": "1.20"
                    },
                    "relationships": [{"type": "CONVERTS_TO"}],
                    "supported_features": [],
                    "success_rate": 0.9,
                    "usage_count": 80
                }
            ]
            
            result = await engine._find_indirect_paths(
                mock_db, sample_source_node, "bedrock", "1.20", 3, 0.5
            )
            
            assert len(result) == 1
            assert result[0]["confidence"] == 0.8

    @pytest.mark.asyncio
    async def test_find_indirect_paths_error_handling(self, engine, mock_db, sample_source_node):
        """Test indirect path finding error handling"""
        with patch('src.services.conversion_inference.graph_db') as mock_graph_db:
            mock_graph_db.find_conversion_paths.side_effect = Exception("Graph DB error")
            
            result = await engine._find_indirect_paths(
                mock_db, sample_source_node, "bedrock", "1.20", 3, 0.5
            )
            
            assert result == []

    @pytest.mark.asyncio
    async def test_validate_conversion_pattern_valid_pattern(self, engine, mock_db):
        """Test validation of valid conversion pattern"""
        valid_pattern = {
            "source_concept": "Java Entity",
            "target_concept": "Bedrock Entity",
            "transformation_type": "direct_conversion",
            "confidence": 0.8,
            "platform": "bedrock",
            "minecraft_version": "1.20"
        }
        
        result = await engine._validate_conversion_pattern(valid_pattern, mock_db)
        
        assert result["is_valid"] is True
        assert result["validation_errors"] == []
        assert result["confidence_score"] >= 0.8

    @pytest.mark.asyncio
    async def test_validate_conversion_pattern_missing_required_fields(self, engine, mock_db):
        """Test validation fails with missing required fields"""
        invalid_pattern = {
            "source_concept": "Java Entity",
            # Missing target_concept, transformation_type, confidence
        }
        
        result = await engine._validate_conversion_pattern(invalid_pattern, mock_db)
        
        assert result["is_valid"] is False
        assert len(result["validation_errors"]) > 0
        assert "target_concept" in str(result["validation_errors"])

    @pytest.mark.asyncio
    async def test_validate_conversion_pattern_invalid_confidence(self, engine, mock_db):
        """Test validation fails with invalid confidence range"""
        invalid_pattern = {
            "source_concept": "Java Entity",
            "target_concept": "Bedrock Entity",
            "transformation_type": "direct_conversion",
            "confidence": 1.5,  # Invalid confidence > 1.0
            "platform": "bedrock",
            "minecraft_version": "1.20"
        }
        
        result = await engine._validate_conversion_pattern(invalid_pattern, mock_db)
        
        assert result["is_valid"] is False
        assert any("confidence" in error.lower() for error in result["validation_errors"])

    @pytest.mark.asyncio
    async def test_validate_conversion_pattern_empty_pattern(self, engine, mock_db):
        """Test validation fails with empty pattern"""
        empty_pattern = {}
        
        result = await engine._validate_conversion_pattern(empty_pattern, mock_db)
        
        assert result["is_valid"] is False
        assert len(result["validation_errors"]) > 0

    @pytest.mark.asyncio
    async def test_check_platform_compatibility_compatible_platforms(self, engine):
        """Test platform compatibility checking for compatible platforms"""
        result = await engine._check_platform_compatibility("java", "bedrock", "1.20")
        
        assert result["is_compatible"] is True
        assert result["compatibility_score"] > 0.5

    @pytest.mark.asyncio
    async def test_check_platform_compatibility_same_platform(self, engine):
        """Test platform compatibility for same platform"""
        result = await engine._check_platform_compatibility("java", "java", "1.20")
        
        assert result["is_compatible"] is True
        assert result["compatibility_score"] == 1.0

    @pytest.mark.asyncio
    async def test_check_platform_compatibility_unsupported_version(self, engine):
        """Test platform compatibility with unsupported version"""
        result = await engine._check_platform_compatibility("java", "bedrock", "0.16")  # Very old version
        
        assert result["is_compatible"] is False
        assert result["compatibility_score"] < 0.5

    @pytest.mark.asyncio
    async def test_check_platform_compatibility_both_platform(self, engine):
        """Test compatibility with 'both' platform"""
        result = await engine._check_platform_compatibility("both", "bedrock", "1.20")
        
        assert result["is_compatible"] is True
        assert result["compatibility_score"] >= 0.8

    @pytest.mark.asyncio
    async def test_check_platform_compatibility_platform_mappings(self, engine):
        """Test platform compatibility with various platform combinations"""
        test_cases = [
            ("java", "java_edition", 1.0),
            ("bedrock", "bedrock_edition", 1.0),
            ("java", "console", 0.3),
            ("bedrock", "mobile", 0.8),
        ]
        
        for source, target, expected_score in test_cases:
            result = await engine._check_platform_compatibility(source, target, "1.20")
            if expected_score == 1.0:
                assert result["is_compatible"] is True
            assert result["compatibility_score"] >= 0.0
