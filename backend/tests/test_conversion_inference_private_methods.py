"""
Fixed and enhanced tests for conversion_inference.py private methods
Target: Achieve 100% coverage for 0% coverage private methods
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import sys
import os

# Add source to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConversionInferencePrivateMethods:
    """Comprehensive test suite for private methods with 0% coverage"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return AsyncMock()

    @pytest.fixture
    def engine(self):
        """Create inference engine instance for testing"""
        # Mock imports that cause issues
        with patch.dict('sys.modules', {
            'db': Mock(),
            'db.models': Mock(),
            'db.knowledge_graph_crud': Mock(),
            'db.graph_db': Mock(),
            'services.version_compatibility': Mock()
        }):
            from src.services.conversion_inference import (
                ConversionInferenceEngine
            )
            return ConversionInferenceEngine()

    @pytest.fixture
    def mock_source_node(self):
        """Create mock source knowledge node"""
        from src.db.models import KnowledgeNode
        node = Mock(spec=KnowledgeNode)
        node.id = "source_123"
        node.name = "java_block"
        node.node_type = "block"
        node.platform = "java"
        node.minecraft_version = "1.19.3"
        node.neo4j_id = "neo4j_123"
        node.properties = {"category": "building", "material": "wood"}
        return node

    @pytest.mark.asyncio
    async def test_find_direct_paths_with_results(self, engine, mock_db, mock_source_node):
        """Test _find_direct_paths method with successful results"""
        # Mock graph database properly
        mock_graph_db = Mock()
        mock_graph_db.find_conversion_paths = Mock(return_value=[
            {
                "path_length": 1,
                "confidence": 0.85,
                "end_node": {
                    "name": "bedrock_block",
                    "platform": "bedrock",
                    "minecraft_version": "1.19.3"
                },
                "relationships": [{"type": "CONVERTS_TO", "confidence": 0.9}],
                "supported_features": ["textures", "behaviors"],
                "success_rate": 0.9,
                "usage_count": 150
            }
        ])

        with patch('src.services.conversion_inference.graph_db', mock_graph_db):
            result = await engine._find_direct_paths(
                mock_db, mock_source_node, "bedrock", "1.19.3"
            )

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["path_type"] == "direct"
            assert result[0]["confidence"] == 0.85
            assert result[0]["path_length"] == 1
            assert len(result[0]["steps"]) == 1
            assert result[0]["supports_features"] == ["textures", "behaviors"]
            assert result[0]["success_rate"] == 0.9
            assert result[0]["usage_count"] == 150

            # Verify step details
            step = result[0]["steps"][0]
            assert step["source_concept"] == "java_block"
            assert step["target_concept"] == "bedrock_block"
            assert step["relationship"] == "CONVERTS_TO"
            assert step["platform"] == "bedrock"
            assert step["version"] == "1.19.3"

    @pytest.mark.asyncio
    async def test_find_direct_paths_no_results(self, engine, mock_db, mock_source_node):
        """Test _find_direct_paths method with no results"""
        # Mock graph database returning no paths
        mock_graph_db = Mock()
        mock_graph_db.find_conversion_paths = Mock(return_value=[])

        with patch('src.services.conversion_inference.graph_db', mock_graph_db):
            result = await engine._find_direct_paths(
                mock_db, mock_source_node, "bedrock", "1.19.3"
            )

            assert isinstance(result, list)
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_find_direct_paths_filter_by_platform(self, engine, mock_db, mock_source_node):
        """Test _find_direct_paths filters results by target platform"""
        # Mock graph database with mixed platforms
        mock_graph_db = Mock()
        mock_graph_db.find_conversion_paths = Mock(return_value=[
            {
                "path_length": 1,
                "confidence": 0.85,
                "end_node": {
                    "name": "bedrock_block",
                    "platform": "bedrock",  # Matches target
                    "minecraft_version": "1.19.3"
                },
                "relationships": [{"type": "CONVERTS_TO", "confidence": 0.9}],
                "success_rate": 0.9,
                "usage_count": 150
            },
            {
                "path_length": 1,
                "confidence": 0.75,
                "end_node": {
                    "name": "java_block_v2",
                    "platform": "java",  # Doesn't match target
                    "minecraft_version": "1.19.3"
                },
                "relationships": [{"type": "UPGRADES_TO"}],
                "success_rate": 0.8,
                "usage_count": 80
            },
            {
                "path_length": 1,
                "confidence": 0.90,
                "end_node": {
                    "name": "universal_block",
                    "platform": "both",  # Matches all platforms
                    "minecraft_version": "1.19.3"
                },
                "relationships": [{"type": "CONVERTS_TO", "confidence": 0.9}],
                "success_rate": 0.95,
                "usage_count": 200
            }
        ])

        with patch('src.services.conversion_inference.graph_db', mock_graph_db):
            result = await engine._find_direct_paths(
                mock_db, mock_source_node, "bedrock", "1.19.3"
            )

            assert isinstance(result, list)
            assert len(result) == 2  # Only bedrock and "both" platforms

            # Should be sorted by confidence (descending)
            assert result[0]["confidence"] == 0.90  # universal_block
            assert result[1]["confidence"] == 0.85  # bedrock_block

            # Verify platform filtering
            platform_names = [path["steps"][0]["target_concept"] for path in result]
            assert "bedrock_block" in platform_names
            assert "universal_block" in platform_names
            assert "java_block_v2" not in platform_names

    @pytest.mark.asyncio
    async def test_find_direct_paths_error_handling(self, engine, mock_db, mock_source_node):
        """Test _find_direct_paths error handling"""
        # Mock graph database to raise exception
        mock_graph_db = Mock()
        mock_graph_db.find_conversion_paths = Mock(side_effect=Exception("Database error"))

        with patch('src.services.conversion_inference.graph_db', mock_graph_db):
            result = await engine._find_direct_paths(
                mock_db, mock_source_node, "bedrock", "1.19.3"
            )

            # Should return empty list on error
            assert isinstance(result, list)
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_find_indirect_paths_basic(self, engine, mock_db, mock_source_node):
        """Test _find_indirect_paths method basic functionality"""
        # Mock graph database with indirect paths
        mock_graph_db = Mock()
        mock_graph_db.find_conversion_paths = Mock(return_value=[
            {
                "path_length": 2,
                "confidence": 0.75,
                "end_node": {
                    "name": "bedrock_block",
                    "platform": "bedrock",
                    "minecraft_version": "1.19.3"
                },
                "relationships": [
                    {"type": "CONVERTS_TO", "confidence": 0.85},
                    {"type": "TRANSFORMS", "confidence": 0.90}
                ],
                "nodes": [
                    {"name": "java_block"},
                    {"name": "intermediate_block"},
                    {"name": "bedrock_block"}
                ],
                "supported_features": ["textures"],
                "success_rate": 0.7,
                "usage_count": 100
            }
        ])

        with patch('src.services.conversion_inference.graph_db', mock_graph_db):
            result = await engine._find_indirect_paths(
                mock_db, mock_source_node, "bedrock", "1.19.3", max_depth=3, min_confidence=0.6
            )

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["path_type"] == "indirect"
            assert result[0]["confidence"] == 0.75
            assert result[0]["path_length"] == 2

            # Check steps
            assert len(result[0]["steps"]) == 2
            step1 = result[0]["steps"][0]
            step2 = result[0]["steps"][1]
            assert step1["source_concept"] == "java_block"
            assert step1["target_concept"] == "intermediate_block"
            assert step2["source_concept"] == "intermediate_block"
            assert step2["target_concept"] == "bedrock_block"

            # Check intermediate concepts
            assert result[0]["intermediate_concepts"] == ["intermediate_block"]

    @pytest.mark.asyncio
    async def test_find_indirect_paths_max_depth_limit(self, engine, mock_db, mock_source_node):
        """Test _find_indirect_paths respects max depth limit"""
        # Mock graph database with deep path
        mock_graph_db = Mock()
        mock_graph_db.find_conversion_paths = Mock(return_value=[
            {
                "path_length": 7,  # Exceeds max depth
                "confidence": 0.40,
                "end_node": {
                    "name": "deep_bedrock_block",
                    "platform": "bedrock"
                }
            }
        ])

        with patch('src.services.conversion_inference.graph_db', mock_graph_db):
            result = await engine._find_indirect_paths(
                mock_db, mock_source_node, "bedrock", "1.19.3", max_depth=5, min_confidence=0.6
            )

            assert isinstance(result, list)
            assert len(result) == 0  # Should filter out paths exceeding max depth

    @pytest.mark.asyncio
    async def test_find_indirect_paths_min_confidence_filter(self, engine, mock_db, mock_source_node):
        """Test _find_indirect_paths filters by minimum confidence"""
        # Mock graph database with low confidence path
        mock_graph_db = Mock()
        mock_graph_db.find_conversion_paths = Mock(return_value=[
            {
                "path_length": 2,
                "confidence": 0.45,  # Below min confidence
                "end_node": {
                    "name": "low_confidence_block",
                    "platform": "bedrock"
                }
            }
        ])

        with patch('src.services.conversion_inference.graph_db', mock_graph_db):
            result = await engine._find_indirect_paths(
                mock_db, mock_source_node, "bedrock", "1.19.3", max_depth=3, min_confidence=0.6
            )

            assert isinstance(result, list)
            assert len(result) == 0  # Should filter out low confidence paths

    @pytest.mark.asyncio
    async def test_find_indirect_paths_platform_filtering(self, engine, mock_db, mock_source_node):
        """Test _find_indirect_paths filters by platform compatibility"""
        # Mock graph database with mixed platforms
        mock_graph_db = Mock()
        mock_graph_db.find_conversion_paths = Mock(return_value=[
            {
                "path_length": 2,
                "confidence": 0.75,
                "end_node": {
                    "name": "bedrock_block",
                    "platform": "bedrock"  # Matches target
                }
            },
            {
                "path_length": 2,
                "confidence": 0.80,
                "end_node": {
                    "name": "java_block_v2",
                    "platform": "java"  # Doesn't match target
                }
            }
        ])

        with patch('src.services.conversion_inference.graph_db', mock_graph_db):
            result = await engine._find_indirect_paths(
                mock_db, mock_source_node, "bedrock", "1.19.3", max_depth=3, min_confidence=0.6
            )

            assert isinstance(result, list)
            assert len(result) == 1  # Only bedrock platform
            assert result[0]["steps"][-1]["target_concept"] == "bedrock_block"

    @pytest.mark.asyncio
    async def test_enhance_conversion_accuracy_success(self, engine):
        """Test enhance_conversion_accuracy method with successful enhancement"""
        conversion_paths = [
            {
                "path_type": "direct",
                "confidence": 0.75,
                "steps": [{"step": "direct_conversion"}],
                "pattern_type": "simple_conversion"
            },
            {
                "path_type": "indirect",
                "confidence": 0.60,
                "steps": [{"step": "step1"}, {"step": "step2"}],
                "pattern_type": "complex_conversion"
            }
        ]

        # Mock the various enhancement methods
        engine._validate_conversion_pattern = Mock(return_value=True)
        engine._check_platform_compatibility = Mock(return_value={"compatible": True, "issues": []})
        engine._refine_with_ml_predictions = Mock(return_value={"enhanced_confidence": 0.82})
        engine._integrate_community_wisdom = Mock(return_value={"community_boost": 0.05})
        engine._optimize_for_performance = Mock(return_value={"performance_score": 0.90})
        engine._generate_accuracy_suggestions = Mock(return_value=["suggestion1", "suggestion2"])

        result = await engine.enhance_conversion_accuracy(conversion_paths)

        assert isinstance(result, dict)
        assert "enhanced_paths" in result
        assert "improvement_summary" in result
        assert "suggestions" in result

        assert len(result["enhanced_paths"]) == 2
        assert result["improvement_summary"]["original_avg_confidence"] == 0.675
        assert "enhanced_avg_confidence" in result["improvement_summary"]
        assert result["suggestions"] == ["suggestion1", "suggestion2"]

    @pytest.mark.asyncio
    async def test_enhance_conversion_accuracy_error_handling(self, engine):
        """Test enhance_conversion_accuracy method error handling"""
        # Test with empty paths
        result = await engine.enhance_conversion_accuracy([])

        assert isinstance(result, dict)
        assert "error" in result
        assert result["enhanced_paths"] == []

        # Test with invalid path data
        invalid_paths = [{"invalid": "data"}]
        result = await engine.enhance_conversion_accuracy(invalid_paths)

        assert isinstance(result, dict)
        assert "error" in result

    def test_validate_conversion_pattern_valid(self, engine):
        """Test _validate_conversion_pattern with valid patterns"""
        valid_pattern = {
            "path_type": "direct",
            "confidence": 0.85,
            "steps": [
                {"source_concept": "java_block", "target_concept": "bedrock_block"}
            ]
        }

        result = engine._validate_conversion_pattern(valid_pattern)

        assert isinstance(result, dict)
        assert result["valid"] is True
        assert "issues" in result
        assert len(result["issues"]) == 0

    def test_validate_conversion_pattern_invalid(self, engine):
        """Test _validate_conversion_pattern with invalid patterns"""
        invalid_pattern = {
            "path_type": "direct",
            "confidence": 1.5,  # Invalid confidence > 1.0
            "steps": []  # Empty steps
        }

        result = engine._validate_conversion_pattern(invalid_pattern)

        assert isinstance(result, dict)
        assert result["valid"] is False
        assert "issues" in result
        assert len(result["issues"]) > 0
        assert any("confidence" in issue.lower() for issue in result["issues"])
        assert any("steps" in issue.lower() for issue in result["issues"])

    def test_check_platform_compatibility_compatible(self, engine):
        """Test _check_platform_compatibility with compatible platforms"""
        path = {
            "steps": [
                {"platform": "java"},
                {"platform": "both"}
            ],
            "target_platform": "bedrock"
        }

        result = engine._check_platform_compatibility(path, "bedrock")

        assert isinstance(result, dict)
        assert result["compatible"] is True
        assert len(result["issues"]) == 0

    def test_check_platform_compatibility_incompatible(self, engine):
        """Test _check_platform_compatibility with incompatible platforms"""
        path = {
            "steps": [
                {"platform": "java"},
                {"platform": "java"}  # No bedrock compatibility
            ],
            "target_platform": "bedrock"
        }

        result = engine._check_platform_compatibility(path, "bedrock")

        assert isinstance(result, dict)
        assert result["compatible"] is False
        assert len(result["issues"]) > 0

    def test_calculate_improvement_percentage(self, engine):
        """Test _calculate_improvement_percentage calculation"""
        original = 0.60
        enhanced = 0.75

        result = engine._calculate_improvement_percentage(original, enhanced)

        assert isinstance(result, float)
        assert abs(result - 25.0) < 0.01  # 25% improvement

    def test_calculate_improvement_percentage_edge_cases(self, engine):
        """Test _calculate_improvement_percentage edge cases"""
        # No improvement
        result = engine._calculate_improvement_percentage(0.80, 0.80)
        assert result == 0.0

        # Decrease (should return 0)
        result = engine._calculate_improvement_percentage(0.80, 0.75)
        assert result == 0.0

        # Original is 0 (avoid division by zero)
        result = engine._calculate_improvement_percentage(0.0, 0.50)
        assert result == 0.0


class TestConversionInferenceOptimizationMethods:
    """Test optimization methods that need coverage improvement"""

    @pytest.fixture
    def engine(self):
        """Create inference engine instance"""
        with patch.dict('sys.modules', {
            'db': Mock(),
            'db.models': Mock(),
            'db.knowledge_graph_crud': Mock(),
            'db.graph_db': Mock(),
            'services.version_compatibility': Mock()
        }):
            from src.services.conversion_inference import ConversionInferenceEngine
            return ConversionInferenceEngine()

    @pytest.mark.asyncio
    async def test_optimize_conversion_sequence_complete(self, engine):
        """Test complete optimization sequence"""
        conversion_sequence = [
            {"concept": "concept1", "confidence": 0.8, "estimated_time": 5},
            {"concept": "concept2", "confidence": 0.9, "estimated_time": 3},
            {"concept": "concept3", "confidence": 0.7, "estimated_time": 8}
        ]

        # Mock optimization methods
        engine._identify_shared_steps = Mock(return_value=["shared_step1", "shared_step2"])
        engine._estimate_batch_time = Mock(return_value=12.5)
        engine._get_batch_optimizations = Mock(return_value=["parallel_processing", "caching"])
        engine._generate_validation_steps = Mock(return_value=["validate_step1", "validate_step2"])
        engine._calculate_savings = Mock(return_value=3.2)

        result = await engine.optimize_conversion_sequence(conversion_sequence)

        assert isinstance(result, dict)
        assert "optimized_sequence" in result
        assert "optimization_applied" in result
        assert "time_savings" in result
        assert "shared_steps" in result
        assert "validation_steps" in result

        assert result["optimization_applied"] is True
        assert result["shared_steps"] == ["shared_step1", "shared_step2"]
        assert result["time_savings"] == 3.2

    @pytest.mark.asyncio
    async def test_optimize_conversion_sequence_empty(self, engine):
        """Test optimization with empty sequence"""
        result = await engine.optimize_conversion_sequence([])

        assert isinstance(result, dict)
        assert "optimized_sequence" in result
        assert len(result["optimized_sequence"]) == 0
        assert result["optimization_applied"] is False

    def test_identify_shared_steps_found(self, engine):
        """Test _identify_shared_steps with shared patterns"""
        conversion_sequence = [
            {
                "steps": [
                    {"action": "parse_java", "concept": "java_block"},
                    {"action": "convert_texture", "concept": "bedrock_texture"},
                    {"action": "apply_properties", "concept": "final_block"}
                ]
            },
            {
                "steps": [
                    {"action": "parse_java", "concept": "java_item"},
                    {"action": "convert_texture", "concept": "bedrock_texture"},
                    {"action": "apply_properties", "concept": "final_item"}
                ]
            }
        ]

        result = engine._identify_shared_steps(conversion_sequence)

        assert isinstance(result, list)
        assert len(result) >= 2  # Should find parse_java and convert_texture as shared
        assert any(step["action"] == "parse_java" for step in result)
        assert any(step["action"] == "convert_texture" for step in result)

    def test_identify_shared_steps_none_found(self, engine):
        """Test _identify_shared_steps with no shared patterns"""
        conversion_sequence = [
            {
                "steps": [
                    {"action": "parse_java", "concept": "java_block"},
                    {"action": "convert_texture", "concept": "bedrock_texture"}
                ]
            },
            {
                "steps": [
                    {"action": "parse_bedrock", "concept": "bedrock_item"},
                    {"action": "convert_behavior", "concept": "java_behavior"}
                ]
            }
        ]

        result = engine._identify_shared_steps(conversion_sequence)

        assert isinstance(result, list)
        assert len(result) == 0

    def test_estimate_batch_time_simple(self, engine):
        """Test _estimate_batch_time with simple sequence"""
        conversion_sequence = [
            {"estimated_time": 5.0},
            {"estimated_time": 3.0},
            {"estimated_time": 7.0}
        ]

        result = engine._estimate_batch_time(conversion_sequence)

        assert isinstance(result, float)
        assert result == 15.0  # Simple sum

    def test_estimate_batch_time_with_optimizations(self, engine):
        """Test _estimate_batch_time with optimizations"""
        conversion_sequence = [
            {"estimated_time": 5.0},
            {"estimated_time": 3.0},
            {"estimated_time": 7.0}
        ]

        # Mock optimizations to reduce time
        with patch.object(engine, '_get_batch_optimizations', return_value=['parallel_processing']):
            result = engine._estimate_batch_time(conversion_sequence)

            assert isinstance(result, float)
            # Should be less than simple sum due to optimizations
            assert result < 15.0

    def test_get_batch_optimizations_available(self, engine):
        """Test _get_batch_optimizations returns available optimizations"""
        conversion_sequence = [
            {"concept": "concept1", "steps": [{"action": "parse"}]},
            {"concept": "concept2", "steps": [{"action": "parse"}]}  # Same action
        ]

        result = engine._get_batch_optimizations(conversion_sequence)

        assert isinstance(result, list)
        assert len(result) > 0
        # Should include parallel processing for same actions
        assert "parallel_processing" in result

    def test_calculate_savings_with_shared_steps(self, engine):
        """Test _calculate_savings with shared steps"""
        original_time = 20.0
        optimized_time = 15.0
        shared_steps = ["parse_java", "convert_texture"]

        result = engine._calculate_savings(original_time, optimized_time, shared_steps)

        assert isinstance(result, dict)
        assert "time_saved" in result
        assert "percentage_saved" in result
        assert "shared_step_count" in result

        assert result["time_saved"] == 5.0
        assert abs(result["percentage_saved"] - 25.0) < 0.01
        assert result["shared_step_count"] == 2


class TestConversionInferenceEdgeCases:
    """Test edge cases and error conditions for private methods"""

    @pytest.fixture
    def engine(self):
        """Create inference engine instance"""
        with patch.dict('sys.modules', {
            'db': Mock(),
            'db.models': Mock(),
            'db.knowledge_graph_crud': Mock(),
            'db.graph_db': Mock(),
            'services.version_compatibility': Mock()
        }):
            from src.services.conversion_inference import ConversionInferenceEngine
            return ConversionInferenceEngine()

    @pytest.mark.asyncio
    async def test_find_direct_paths_malformed_data(self, engine, mock_db):
        """Test _find_direct_paths with malformed graph data"""
        # Create a mock source node
        mock_source_node = Mock()
        mock_source_node.neo4j_id = "test_id"
        mock_source_node.name = "test_node"

        # Mock graph database with malformed data
        mock_graph_db = Mock()
        mock_graph_db.find_conversion_paths = Mock(return_value=[
            {
                "path_length": 1,
                "confidence": 0.85,
                "end_node": None,  # Missing end_node
                "relationships": [{"type": "CONVERTS_TO"}]
            },
            {
                "path_length": 1,
                "confidence": "invalid",  # Invalid confidence type
                "end_node": {"name": "valid_node", "platform": "bedrock"},
                "relationships": []
            }
        ])

        with patch('src.services.conversion_inference.graph_db', mock_graph_db):
            result = await engine._find_direct_paths(
                mock_db, mock_source_node, "bedrock", "1.19.3"
            )

            # Should handle malformed data gracefully
            assert isinstance(result, list)
            # Should not crash, but may return fewer results due to filtering

    @pytest.mark.asyncio
    async def test_find_indirect_paths_circular_reference(self, engine, mock_db):
        """Test _find_indirect_paths with potential circular references"""
        mock_source_node = Mock()
        mock_source_node.neo4j_id = "test_id"
        mock_source_node.name = "test_node"

        # Mock graph database with circular path
        mock_graph_db = Mock()
        mock_graph_db.find_conversion_paths = Mock(return_value=[
            {
                "path_length": 3,
                "confidence": 0.75,
                "end_node": {
                    "name": "target_node",
                    "platform": "bedrock"
                },
                "nodes": [
                    {"name": "test_node"},      # Start
                    {"name": "middle_node"},    # Middle
                    {"name": "test_node"},      # Back to start (circular)
                    {"name": "target_node"}     # End
                ],
                "relationships": [
                    {"type": "CONVERTS_TO"},
                    {"type": "REFERENCES"},
                    {"type": "CONVERTS_TO"}
                ]
            }
        ])

        with patch('src.services.conversion_inference.graph_db', mock_graph_db):
            result = await engine._find_indirect_paths(
                mock_db, mock_source_node, "bedrock", "1.19.3", max_depth=5, min_confidence=0.6
            )

            assert isinstance(result, list)
            # Should handle circular references without infinite loops

    @pytest.mark.asyncio
    async def test_enhance_conversion_accuracy_partial_failure(self, engine):
        """Test enhance_conversion_accuracy with partial enhancement failures"""
        conversion_paths = [
            {
                "path_type": "direct",
                "confidence": 0.75,
                "steps": [{"step": "direct_conversion"}]
            }
        ]

        # Mock some methods to fail
        engine._validate_conversion_pattern = Mock(return_value=True)
        engine._check_platform_compatibility = Mock(side_effect=Exception("Platform check failed"))
        engine._refine_with_ml_predictions = Mock(return_value={"enhanced_confidence": 0.82})
        engine._integrate_community_wisdom = Mock(return_value={"community_boost": 0.05})

        result = await engine.enhance_conversion_accuracy(conversion_paths)

        # Should handle partial failures gracefully
        assert isinstance(result, dict)
        assert "enhanced_paths" in result
        # May include partial results even with some failures

    def test_validate_conversion_pattern_edge_cases(self, engine):
        """Test _validate_conversion_pattern edge cases"""
        # Test with None
        result = engine._validate_conversion_pattern(None)
        assert result["valid"] is False
        assert len(result["issues"]) > 0

        # Test with missing required fields
        incomplete_pattern = {"path_type": "direct"}  # Missing confidence and steps
        result = engine._validate_conversion_pattern(incomplete_pattern)
        assert result["valid"] is False
        assert len(result["issues"]) >= 2

        # Test with negative confidence
        negative_pattern = {
            "path_type": "direct",
            "confidence": -0.5,
            "steps": [{"step": "test"}]
        }
        result = engine._validate_conversion_pattern(negative_pattern)
        assert result["valid"] is False
        assert any("negative" in issue.lower() for issue in result["issues"])


class TestConversionInferenceRemainingPrivateMethods:
    """Test remaining private methods that need coverage"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return AsyncMock()

    @pytest.fixture
    def engine(self):
        """Create inference engine instance for testing"""
        with patch.dict('sys.modules', {
            'db': Mock(),
            'db.models': Mock(),
            'db.knowledge_graph_crud': Mock(),
            'db.graph_db': Mock(),
            'services.version_compatibility': Mock()
        }):
            from src.services.conversion_inference import ConversionInferenceEngine
            return ConversionInferenceEngine()

    @pytest.mark.asyncio
    async def test_refine_with_ml_predictions(self, engine):
        """Test _refine_with_ml_predictions method"""
        path = {
            "confidence": 0.75,
            "steps": [{"step": "test1"}, {"step": "test2"}, {"step": "test3"}],
            "pattern_type": "entity_conversion",
            "target_platform": "bedrock",
            "complexity": "low"
        }
        context_data = {"version": "1.19.3"}

        result = await engine._refine_with_ml_predictions(path, context_data)

        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0
        # Should be higher than base confidence for good features
        assert result > path["confidence"]

    @pytest.mark.asyncio
    async def test_integrate_community_wisdom(self, engine, mock_db):
        """Test _integrate_community_wisdom method"""
        path = {
            "pattern_type": "entity_conversion",
            "confidence": 0.75
        }

        result = await engine._integrate_community_wisdom(path, mock_db)

        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0
        # Should return popularity score for known pattern type
        assert result == 0.85  # entity_conversion popularity score

    @pytest.mark.asyncio
    async def test_integrate_community_wisdom_unknown_pattern(self, engine, mock_db):
        """Test _integrate_community_wisdom with unknown pattern"""
        path = {
            "pattern_type": "unknown_pattern",
            "confidence": 0.75
        }

        result = await engine._integrate_community_wisdom(path, mock_db)

        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0
        # Should return default score for unknown pattern
        assert result == 0.60

    @pytest.mark.asyncio
    async def test_integrate_community_wisdom_no_db(self, engine):
        """Test _integrate_community_wisdom without database"""
        path = {
            "pattern_type": "entity_conversion",
            "confidence": 0.75
        }

        result = await engine._integrate_community_wisdom(path, None)

        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0
        # Should return default score when no DB available
        assert result == 0.7

    @pytest.mark.asyncio
    async def test_optimize_for_performance(self, engine):
        """Test _optimize_for_performance method"""
        path = {
            "confidence": 0.75,
            "steps": [{"step": "test1"}, {"step": "test2"}],
            "resource_usage": {"memory": "low", "cpu": "medium"}
        }
        context_data = {"optimization_level": "standard"}

        result = await engine._optimize_for_performance(path, context_data)

        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0
        # Should return a reasonable performance score
        assert 0.5 <= result <= 1.0

    @pytest.mark.asyncio
    async def test_optimize_for_performance_high_intensity(self, engine):
        """Test _optimize_for_performance with high resource intensity"""
        path = {
            "confidence": 0.75,
            "steps": [{"step": "test1"}, {"step": "test2"}],
            "resource_intensity": "high"  # High intensity - matches implementation
        }
        context_data = {"optimization_level": "standard"}

        result = await engine._optimize_for_performance(path, context_data)

        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0
        # Should be lower due to high resource intensity
        # Base score 0.8 - 0.1 penalty = 0.7
        assert result <= 0.71  # Allow for floating-point precision

    @pytest.mark.asyncio
    async def test_generate_accuracy_suggestions(self, engine):
        """Test _generate_accuracy_suggestions method"""
        path = {
            "accuracy_components": {
                "pattern_validation": 0.6,
                "platform_compatibility": 0.7,
                "ml_prediction": 0.5
            }
        }
        accuracy_score = 0.6

        result = await engine._generate_accuracy_suggestions(path, accuracy_score)

        assert isinstance(result, list)
        # Should have suggestions for low accuracy
        assert len(result) > 0
        # Should suggest improvements for low score components
        assert any("pattern validation" in suggestion.lower() for suggestion in result)
        assert any("training data" in suggestion.lower() for suggestion in result)

    @pytest.mark.asyncio
    async def test_generate_accuracy_suggestions_high_accuracy(self, engine):
        """Test _generate_accuracy_suggestions with high accuracy score"""
        path = {
            "accuracy_components": {
                "pattern_validation": 0.9,
                "platform_compatibility": 0.9,
                "ml_prediction": 0.9
            }
        }
        accuracy_score = 0.9

        result = await engine._generate_accuracy_suggestions(path, accuracy_score)

        assert isinstance(result, list)
        # Should have fewer suggestions for high accuracy
        assert len(result) <= 2

    @pytest.mark.asyncio
    async def test_topological_sort(self, engine):
        """Test _topological_sort method"""
        # Simple DAG (Directed Acyclic Graph)
        graph = {
            "A": ["B", "C"],
            "B": ["D"],
            "C": ["D"],
            "D": []
        }

        result = await engine._topological_sort(graph)

        assert isinstance(result, list)
        assert len(result) == 4
        # A should come before B and C
        assert result.index("A") < result.index("B")
        assert result.index("A") < result.index("C")
        # B and C should come before D
        assert result.index("B") < result.index("D")
        assert result.index("C") < result.index("D")

    @pytest.mark.asyncio
    async def test_topological_sort_complex(self, engine):
        """Test _topological_sort with more complex graph"""
        graph = {
            "concept1": ["concept2", "concept3"],
            "concept2": ["concept4"],
            "concept3": ["concept4", "concept5"],
            "concept4": ["concept6"],
            "concept5": ["concept6"],
            "concept6": []
        }

        result = await engine._topological_sort(graph)

        assert isinstance(result, list)
        assert len(result) == 6
        # Check dependencies are satisfied
        for node in result:
            for dependency in graph[node]:
                assert result.index(node) < result.index(dependency)

    @pytest.mark.asyncio
    async def test_topological_sort_empty(self, engine):
        """Test _topological_sort with empty graph"""
        graph = {}

        result = await engine._topological_sort(graph)

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_simulate_ml_scoring(self, engine):
        """Test _simulate_ml_scoring method"""
        features = {
            "base_confidence": 0.8,
            "path_length": 2,
            "complexity": "low"
        }

        result = engine._simulate_ml_scoring(features)

        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0
        # Should be higher for good features
        assert result >= 0.8

    @pytest.mark.asyncio
    async def test_simulate_ml_scoring_low_confidence(self, engine):
        """Test _simulate_ml_scoring with low confidence"""
        features = {
            "base_confidence": 0.4,
            "path_length": 5,
            "complexity": "high"
        }

        result = engine._simulate_ml_scoring(features)

        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0
        # Should be lower for poor features but still reasonable
        assert result >= 0.7  # Base score is 0.7

    @pytest.mark.asyncio
    async def test_store_learning_event(self, engine, mock_db):
        """Test _store_learning_event method"""
        event = {
            "type": "conversion_completed",
            "success": True,
            "confidence": 0.85
        }

        # Method should not raise errors
        await engine._store_learning_event(event, mock_db)

        # Should have added an ID to the event
        assert "id" in event
        assert event["id"].startswith("learning_")

    @pytest.mark.asyncio
    async def test_calculate_complexity(self, engine):
        """Test _calculate_complexity method"""
        conversion_result = {
            "step_count": 3,
            "pattern_count": 2,
            "custom_code": ["line1", "line2", "line3", "line4"],
            "file_count": 2
        }

        result = engine._calculate_complexity(conversion_result)

        assert isinstance(result, float)
        assert result > 0.0
        # Verify calculation: 3*0.2 + 2*0.3 + 4*0.4 + 2*0.1 = 0.6 + 0.6 + 1.6 + 0.2 = 3.0
        assert abs(result - 3.0) < 0.01

    @pytest.mark.asyncio
    async def test_calculate_complexity_defaults(self, engine):
        """Test _calculate_complexity with missing fields"""
        conversion_result = {}  # Empty result

        result = engine._calculate_complexity(conversion_result)

        assert isinstance(result, float)
        # Should use defaults: 1*0.2 + 1*0.3 + 0*0.4 + 1*0.1 = 0.2 + 0.3 + 0 + 0.1 = 0.6
        assert abs(result - 0.6) < 0.01
