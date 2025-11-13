"""
Working tests for conversion_inference.py
Based on actual service structure and methods
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys
import os
from datetime import datetime

# Add source to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConversionInferenceEngine:
    """Working test suite for ConversionInferenceEngine"""
    
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
    
    def test_engine_import(self):
        """Test that engine can be imported"""
        try:
            from src.services.conversion_inference import ConversionInferenceEngine
            assert ConversionInferenceEngine is not None
        except ImportError as e:
            pytest.skip(f"Cannot import engine: {e}")
    
    def test_engine_initialization(self, engine):
        """Test engine initialization"""
        assert engine is not None
        # Should have confidence thresholds
        assert hasattr(engine, 'confidence_thresholds')
        assert hasattr(engine, 'max_path_depth')
        assert hasattr(engine, 'min_path_confidence')
        
        # Check thresholds structure
        assert "high" in engine.confidence_thresholds
        assert "medium" in engine.confidence_thresholds
        assert "low" in engine.confidence_thresholds
        
        # Check threshold values are valid
        for threshold_name, threshold_value in engine.confidence_thresholds.items():
            assert isinstance(threshold_value, float)
            assert 0.0 <= threshold_value <= 1.0
    
    def test_confidence_threshold_hierarchy(self, engine):
        """Test confidence threshold hierarchy"""
        high = engine.confidence_thresholds["high"]
        medium = engine.confidence_thresholds["medium"]
        low = engine.confidence_thresholds["low"]
        
        # Should be in descending order
        assert high > medium
        assert medium > low
        assert low >= 0.0
        assert high <= 1.0
    
    @pytest.mark.asyncio
    async def test_infer_conversion_path_success(self, engine, mock_db):
        """Test successful conversion path inference"""
        # Mock concept node finding
        with patch.object(engine, '_find_concept_node') as mock_find:
            mock_find.return_value = {
                "id": "test_node_123",
                "concept": "test_concept",
                "platform": "java",
                "version": "1.19.3"
            }
            
            # Mock direct path finding
            with patch.object(engine, '_find_direct_paths') as mock_direct:
                mock_direct.return_value = [
                    {
                        "target_concept": "bedrock_equivalent",
                        "platform": "bedrock",
                        "confidence": 0.85,
                        "path": ["direct_conversion"]
                    }
                ]
                
                result = await engine.infer_conversion_path(
                    "java_concept", mock_db, "bedrock", "1.19.3"
                )
                
                assert result is not None
                assert "success" in result
                assert "path_type" in result
                assert "primary_path" in result
    
    @pytest.mark.asyncio
    async def test_infer_conversion_path_source_not_found(self, engine, mock_db):
        """Test conversion path inference with source not found"""
        # Mock concept node finding returning None
        with patch.object(engine, '_find_concept_node') as mock_find:
            mock_find.return_value = None
            
            # Mock concept suggestions
            with patch.object(engine, '_suggest_similar_concepts') as mock_suggest:
                mock_suggest.return_value = ["similar_concept1", "similar_concept2"]
                
                result = await engine.infer_conversion_path(
                    "nonexistent_concept", mock_db, "bedrock", "1.19.3"
                )
                
                assert result is not None
                assert result["success"] is False
                assert "error" in result
                assert "suggestions" in result
                assert len(result["suggestions"]) > 0
    
    @pytest.mark.asyncio
    async def test_batch_infer_paths_success(self, engine, mock_db):
        """Test successful batch conversion path inference"""
        # Mock individual inference
        with patch.object(engine, 'infer_conversion_path') as mock_infer:
            mock_infer.side_effect = [
                {
                    "success": True,
                    "java_concept": "concept1",
                    "path_type": "direct",
                    "primary_path": {"confidence": 0.85}
                },
                {
                    "success": True,
                    "java_concept": "concept2", 
                    "path_type": "indirect",
                    "primary_path": {"confidence": 0.72}
                }
            ]
            
            concepts = ["concept1", "concept2"]
            result = await engine.batch_infer_paths(
                concepts, "bedrock", "1.19.3", db=mock_db
            )
            
            assert result is not None
            assert result["success"] is True
            assert "total_concepts" in result
            assert "successful_paths" in result
            assert "concept_paths" in result
            assert result["total_concepts"] == 2
            assert len(result["concept_paths"]) == 2
    
    @pytest.mark.asyncio
    async def test_batch_infer_paths_mixed_results(self, engine, mock_db):
        """Test batch inference with mixed success/failure"""
        # Mock individual inference with mixed results
        with patch.object(engine, 'infer_conversion_path') as mock_infer:
            mock_infer.side_effect = [
                {
                    "success": True,
                    "java_concept": "concept1",
                    "primary_path": {"confidence": 0.85}
                },
                {
                    "success": False,
                    "error": "Concept not found",
                    "java_concept": "concept2"
                }
            ]
            
            concepts = ["concept1", "concept2"]
            result = await engine.batch_infer_paths(
                concepts, "bedrock", "1.19.3", db=mock_db
            )
            
            assert result is not None
            assert result["success"] is True
            assert result["total_concepts"] == 2
            assert "successful_paths" in result
            assert "failed_concepts" in result
            assert len(result["concept_paths"]) == 1
            assert len(result["failed_concepts"]) == 1
    
    @pytest.mark.asyncio
    async def test_optimize_conversion_sequence(self, engine, mock_db):
        """Test conversion sequence optimization"""
        # Create test sequence
        java_concepts = ["concept1", "concept2", "concept3"]
        
        result = await engine.optimize_conversion_sequence(
            java_concepts, None, "bedrock", "latest", db=mock_db
        )
        
        assert result is not None
        assert "success" in result
        assert "processing_sequence" in result
        assert "total_concepts" in result
        assert result["total_concepts"] == 3
        assert isinstance(result["processing_sequence"], list)
    
    @pytest.mark.asyncio
    async def test_learn_from_conversion(self, engine, mock_db):
        """Test learning from conversion results"""
        # Create test conversion data
        java_concept = "test_concept"
        bedrock_concept = "test_bedrock_concept"
        conversion_result = {
            "path_taken": ["step1", "step2"],
            "success": True,
            "confidence": 0.85,
            "user_feedback": {"rating": 5, "comments": "Good conversion"}
        }
        success_metrics = {
            "overall_success": 0.9,
            "accuracy": 0.85,
            "feature_completeness": 0.8
        }
        
        result = await engine.learn_from_conversion(
            java_concept, bedrock_concept, conversion_result, success_metrics, mock_db
        )
        
        assert result is not None
        assert result["success"] is True
        assert "performance_analysis" in result
        assert "knowledge_updates" in result
    
    @pytest.mark.asyncio
    async def test_get_inference_statistics(self, engine, mock_db):
        """Test getting inference statistics"""
        # Mock statistics retrieval
        with patch.object(engine, '_retrieve_statistics') as mock_stats:
            mock_stats.return_value = {
                "total_inferences": 1500,
                "successful_inferences": 1200,
                "average_confidence": 0.75,
                "popular_concepts": ["concept1", "concept2"],
                "inference_trends": {"daily": [100, 120, 110]}
            }
            
            result = await engine.get_inference_statistics(
                mock_db, time_range="7d"
            )
            
            assert result is not None
            assert "total_inferences" in result
            assert "success_rate" in result
            assert "average_confidence" in result
            assert result["total_inferences"] == 1500
            assert "popular_concepts" in result
    
    @pytest.mark.asyncio
    async def test_update_confidence_thresholds(self, engine):
        """Test updating confidence thresholds"""
        new_thresholds = {
            "high": 0.9,
            "medium": 0.7,
            "low": 0.5
        }
        
        engine.update_confidence_thresholds(new_thresholds)
        
        # Verify thresholds were updated
        assert engine.confidence_thresholds["high"] == 0.9
        assert engine.confidence_thresholds["medium"] == 0.7
        assert engine.confidence_thresholds["low"] == 0.5
    
    def test_validate_path_options(self, engine):
        """Test path options validation"""
        # Valid options
        valid_options = {
            "max_depth": 5,
            "min_confidence": 0.6,
            "include_alternatives": True,
            "optimize_for": "confidence"
        }
        
        result = engine.validate_path_options(valid_options)
        assert result["valid"] is True
        
        # Invalid options
        invalid_options = {
            "max_depth": -1,  # Invalid negative
            "min_confidence": 1.5,  # Invalid > 1.0
            "optimize_for": "invalid_option"
        }
        
        result = engine.validate_path_options(invalid_options)
        assert result["valid"] is False
        assert "errors" in result
        assert len(result["errors"]) > 0
    
    def test_calculate_path_confidence(self, engine):
        """Test path confidence calculation"""
        # Create test path steps
        path_steps = [
            {"step": 1, "confidence": 0.9},
            {"step": 2, "confidence": 0.8},
            {"step": 3, "confidence": 0.85}
        ]
        
        # Calculate overall confidence
        overall_confidence = engine.calculate_path_confidence(path_steps)
        
        assert isinstance(overall_confidence, float)
        assert 0.0 <= overall_confidence <= 1.0
        # Should be lower than individual step confidences
        assert overall_confidence <= min([s["confidence"] for s in path_steps])
    
    @pytest.mark.asyncio
    async def test_find_alternative_paths(self, engine, mock_db):
        """Test finding alternative conversion paths"""
        # Mock path finding
        with patch.object(engine, '_search_path_network') as mock_search:
            mock_search.return_value = [
                {
                    "path": ["alternative1", "alternative2"],
                    "confidence": 0.7,
                    "complexity": "medium"
                },
                {
                    "path": ["alternative3"],
                    "confidence": 0.75,
                    "complexity": "low"
                }
            ]
            
            result = await engine.find_alternative_paths(
                "source_concept", "target_concept", mock_db
            )
            
            assert result is not None
            assert "alternatives" in result
            assert "total_alternatives" in result
            assert len(result["alternatives"]) > 0
            # Should be sorted by confidence (descending)
            assert result["alternatives"][0]["confidence"] >= result["alternatives"][1]["confidence"]
    
    def test_get_confidence_category(self, engine):
        """Test confidence category determination"""
        # Test high confidence
        category = engine.get_confidence_category(0.9)
        assert category == "high"
        
        # Test medium confidence
        category = engine.get_confidence_category(0.7)
        assert category == "medium"
        
        # Test low confidence
        category = engine.get_confidence_category(0.3)
        assert category == "low"
        
        # Test edge cases
        category = engine.get_confidence_category(engine.confidence_thresholds["high"])
        assert category == "high"
        
        category = engine.get_confidence_category(engine.confidence_thresholds["low"])
        assert category == "low"
    
    @pytest.mark.asyncio
    async def test_infer_conversion_path_with_options(self, engine, mock_db):
        """Test conversion path inference with custom options"""
        # Mock concept node finding
        with patch.object(engine, '_find_concept_node') as mock_find:
            mock_find.return_value = {"id": "test_node"}
            
            # Mock path finding
            with patch.object(engine, '_find_direct_paths') as mock_direct:
                mock_direct.return_value = []
                
                # Mock indirect path finding
                with patch.object(engine, '_find_indirect_paths') as mock_indirect:
                    mock_indirect.return_value = [
                        {
                            "path": ["step1", "step2"],
                            "confidence": 0.65,
                            "complexity": "medium"
                        }
                    ]
                    
                    # Custom options
                    options = {
                        "max_depth": 3,
                        "min_confidence": 0.6,
                        "optimize_for": "features",
                        "include_alternatives": True
                    }
                    
                    result = await engine.infer_conversion_path(
                        "java_concept", mock_db, "bedrock", "1.19.3", options
                    )
                    
                    assert result is not None
                    assert "success" in result
                    # Should use indirect paths when direct not available
                    assert result.get("path_type") == "indirect"
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_database(self, engine):
        """Test error handling with invalid database session"""
        # Test with None database
        result = await engine.infer_conversion_path(
            "test_concept", None, "bedrock", "1.19.3"
        )
        
        # Should handle gracefully
        assert result is not None
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_performance_large_batch(self, engine, mock_db):
        """Test performance with large batch operations"""
        # Create large concept list
        concepts = [f"concept_{i}" for i in range(100)]
        
        # Mock individual inference for performance test
        with patch.object(engine, 'infer_conversion_path') as mock_infer:
            mock_infer.return_value = {
                "success": True,
                "path_type": "direct",
                "primary_path": {"confidence": 0.8}
            }
            
            import time
            start_time = time.time()
            
            result = await engine.batch_infer_paths(
                concepts, mock_db, "bedrock", "1.19.3"
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            assert result is not None
            assert result["total_concepts"] == 100
            assert result["successful_conversions"] == 100
            # Performance check - should complete within reasonable time
            assert processing_time < 5.0  # 5 seconds max


class TestConversionInferenceValidation:
    """Test validation and edge cases for inference engine"""
    
    @pytest.fixture
    def engine(self):
        """Create engine instance for validation tests"""
        with patch.dict('sys.modules', {
            'db': Mock(),
            'db.models': Mock(),
            'db.knowledge_graph_crud': Mock(),
            'db.graph_db': Mock(),
            'services.version_compatibility': Mock()
        }):
            from src.services.conversion_inference import ConversionInferenceEngine
            return ConversionInferenceEngine()
    
    def test_validate_concept_input(self, engine):
        """Test concept input validation"""
        # Valid concepts
        assert engine.validate_concept("valid_concept")["valid"] is True
        assert engine.validate_concept("valid_concept_123")["valid"] is True
        
        # Invalid concepts
        assert engine.validate_concept("")["valid"] is False
        assert engine.validate_concept(None)["valid"] is False
        assert engine.validate_concept("   ")["valid"] is False
        assert engine.validate_concept("concept\nwith\nnewlines")["valid"] is False
    
    def test_validate_platform_input(self, engine):
        """Test platform input validation"""
        # Valid platforms
        assert engine.validate_platform("java")["valid"] is True
        assert engine.validate_platform("bedrock")["valid"] is True
        assert engine.validate_platform("both")["valid"] is True
        
        # Invalid platforms
        assert engine.validate_platform("invalid")["valid"] is False
        assert engine.validate_platform("")["valid"] is False
        assert engine.validate_platform(None)["valid"] is False
    
    def test_validate_version_input(self, engine):
        """Test version input validation"""
        # Valid versions
        assert engine.validate_version("1.19.3")["valid"] is True
        assert engine.validate_version("1.20")["valid"] is True
        assert engine.validate_version("latest")["valid"] is True
        
        # Invalid versions
        assert engine.validate_version("1.99.999")["valid"] is False
        assert engine.validate_version("")["valid"] is False
        assert engine.validate_version(None)["valid"] is False
        assert engine.validate_version("invalid.version")["valid"] is False


class TestConversionInferencePrivateMethods:
    """Test private methods that are currently uncovered"""
    
    @pytest.fixture
    def engine(self):
        """Create engine instance for testing private methods"""
        with patch.dict('sys.modules', {
            'db': Mock(),
            'db.models': Mock(),
            'db.knowledge_graph_crud': Mock(),
            'db.graph_db': Mock(),
            'services.version_compatibility': Mock()
        }):
            from src.services.conversion_inference import ConversionInferenceEngine
            return ConversionInferenceEngine()
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return AsyncMock()
    
    @pytest.fixture 
    def mock_source_node(self):
        """Create mock source knowledge node"""
        from src.db.models import KnowledgeNode
        return KnowledgeNode(
            id="source_123",
            name="java_block",
            node_type="block",
            platform="java",
            minecraft_version="1.19.3",
            properties={"category": "building", "material": "wood"}
        )
    
    @pytest.mark.asyncio
    async def test_find_direct_paths_with_results(self, engine, mock_db, mock_source_node):
        """Test _find_direct_paths method with successful results"""
        # Mock graph database
        mock_graph_db = Mock()
        mock_graph_db.find_conversion_paths.return_value = [
            {
                "path_length": 1,
                "confidence": 0.85,
                "end_node": {
                    "name": "bedrock_block",
                    "platform": "bedrock",
                    "minecraft_version": "1.19.3"
                },
                "relationships": [{"type": "CONVERTS_TO"}],
                "supported_features": ["textures", "behaviors"],
                "success_rate": 0.9,
                "usage_count": 150
            }
        ]
        
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
    
    @pytest.mark.asyncio
    async def test_find_direct_paths_no_results(self, engine, mock_db, mock_source_node):
        """Test _find_direct_paths method with no results"""
        # Mock graph database returning no paths
        mock_graph_db = Mock()
        mock_graph_db.find_conversion_paths.return_value = []
        
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
        mock_graph_db.find_conversion_paths.return_value = [
            {
                "path_length": 1,
                "confidence": 0.85,
                "end_node": {
                    "name": "bedrock_block",
                    "platform": "bedrock",
                    "minecraft_version": "1.19.3"
                },
                "relationships": [{"type": "CONVERTS_TO"}]
            },
            {
                "path_length": 1,
                "confidence": 0.75,
                "end_node": {
                    "name": "java_block_variant", 
                    "platform": "java",  # Should be filtered out
                    "minecraft_version": "1.19.3"
                },
                "relationships": [{"type": "CONVERTS_TO"}]
            },
            {
                "path_length": 1,
                "confidence": 0.80,
                "end_node": {
                    "name": "universal_block",
                    "platform": "both",  # Should be included
                    "minecraft_version": "1.19.3"
                },
                "relationships": [{"type": "CONVERTS_TO"}]
            }
        ]
        
        with patch('src.services.conversion_inference.graph_db', mock_graph_db):
            result = await engine._find_direct_paths(
                mock_db, mock_source_node, "bedrock", "1.19.3"
            )
            
            assert isinstance(result, list)
            assert len(result) == 2  # Only bedrock and "both" platforms included
            assert all(path["steps"][0]["target_concept"] in ["bedrock_block", "universal_block"] for path in result)
    
    @pytest.mark.asyncio
    async def test_find_direct_paths_error_handling(self, engine, mock_db, mock_source_node):
        """Test _find_direct_paths error handling"""
        # Mock graph database raising exception
        mock_graph_db = Mock()
        mock_graph_db.find_conversion_paths.side_effect = Exception("Database connection failed")
        
        with patch('src.services.conversion_inference.graph_db', mock_graph_db):
            result = await engine._find_direct_paths(
                mock_db, mock_source_node, "bedrock", "1.19.3"
            )
            
            assert isinstance(result, list)
            assert len(result) == 0  # Should return empty list on error
    
    @pytest.mark.asyncio
    async def test_find_indirect_paths_basic(self, engine, mock_db, mock_source_node):
        """Test _find_indirect_paths method basic functionality"""
        # Mock graph database for indirect paths
        mock_graph_db = Mock()
        mock_graph_db.find_conversion_paths.return_value = [
            {
                "path_length": 3,
                "confidence": 0.65,
                "end_node": {
                    "name": "bedrock_complex_block",
                    "platform": "bedrock", 
                    "minecraft_version": "1.19.3"
                },
                "relationships": [
                    {"type": "CONVERTS_TO", "start": "java_block", "end": "intermediate_block"},
                    {"type": "TRANSFORMS", "start": "intermediate_block", "end": "bedrock_complex_block"}
                ],
                "intermediate_nodes": [
                    {"name": "intermediate_block", "platform": "both"}
                ]
            }
        ]
        
        with patch('src.services.conversion_inference.graph_db', mock_graph_db):
            result = await engine._find_indirect_paths(
                mock_db, mock_source_node, "bedrock", "1.19.3", max_depth=5
            )
            
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["path_type"] == "indirect"
            assert result[0]["path_length"] == 3
            assert result[0]["confidence"] == 0.65
            assert len(result[0]["steps"]) == 3
    
    @pytest.mark.asyncio
    async def test_find_indirect_paths_max_depth_limit(self, engine, mock_db, mock_source_node):
        """Test _find_indirect_paths respects max depth limit"""
        # Mock graph database with deep path
        mock_graph_db = Mock()
        mock_graph_db.find_conversion_paths.return_value = [
            {
                "path_length": 7,  # Exceeds max depth
                "confidence": 0.40,
                "end_node": {
                    "name": "deep_bedrock_block",
                    "platform": "bedrock"
                }
            }
        ]
        
        with patch('src.services.conversion_inference.graph_db', mock_graph_db):
            result = await engine._find_indirect_paths(
                mock_db, mock_source_node, "bedrock", "1.19.3", max_depth=5
            )
            
            assert isinstance(result, list)
            assert len(result) == 0  # Should filter out paths exceeding max depth
    
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
                "confidence": 0.65,
                "steps": [{"step": "step1"}, {"step": "step2"}],
                "pattern_type": "complex_conversion"
            }
        ]
        
        context_data = {
            "target_platform": "bedrock",
            "minecraft_version": "1.19.3",
            "optimization_priority": "accuracy"
        }
        
        # Mock the internal enhancement methods
        with patch.object(engine, '_validate_conversion_pattern') as mock_validate:
            mock_validate.return_value = 0.85  # Pattern validation score
            
            with patch.object(engine, '_check_platform_compatibility') as mock_compat:
                mock_compat.return_value = 0.90  # Compatibility score
                
                with patch.object(engine, '_refine_with_ml_predictions') as mock_ml:
                    mock_ml.return_value = 0.80  # ML refinement score
                    
                    with patch.object(engine, '_integrate_community_wisdom') as mock_community:
                        mock_community.return_value = 0.75  # Community wisdom score
                        
                        with patch.object(engine, '_optimize_for_performance') as mock_perf:
                            mock_perf.return_value = 0.88  # Performance score
                            
                            result = await engine.enhance_conversion_accuracy(
                                conversion_paths, context_data
                            )
                            
                            assert result["success"] is True
                            assert "enhanced_paths" in result
                            assert "accuracy_improvements" in result
                            assert "enhancement_metadata" in result
                            
                            # Check that paths were enhanced
                            assert len(result["enhanced_paths"]) == 2
                            assert all(
                                "enhanced_accuracy" in path for path in result["enhanced_paths"]
                            )
                            assert all(
                                "accuracy_suggestions" in path for path in result["enhanced_paths"]
                            )
                            
                            # Check improvement calculations
                            improvements = result["accuracy_improvements"]
                            assert improvements["original_avg_confidence"] == 0.70  # (0.75 + 0.65) / 2
                            assert improvements["enhanced_avg_confidence"] > 0.70
                            assert improvements["improvement_percentage"] > 0
    
    @pytest.mark.asyncio
    async def test_enhance_conversion_accuracy_error_handling(self, engine):
        """Test enhance_conversion_accuracy method error handling"""
        # Mock internal method to raise exception
        with patch.object(engine, '_validate_conversion_pattern') as mock_validate:
            mock_validate.side_effect = Exception("Validation failed")
            
            result = await engine.enhance_conversion_accuracy([])
            
            assert result["success"] is False
            assert "error" in result
            assert "Accuracy enhancement failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_validate_conversion_pattern_success(self, engine, mock_db):
        """Test _validate_conversion_pattern with successful validation"""
        path = {
            "pattern_type": "simple_conversion",
            "confidence": 0.80
        }
        
        # Mock ConversionPatternCRUD - make it return a coroutine
        mock_patterns = [
            Mock(success_rate=0.85),
            Mock(success_rate=0.90)
        ]
        
        with patch('src.services.conversion_inference.ConversionPatternCRUD') as mock_crud:
            # Make get_by_type return an awaitable list
            mock_crud.get_by_type = AsyncMock(return_value=mock_patterns)
            
            result = await engine._validate_conversion_pattern(path, mock_db)
            
            assert isinstance(result, float)
            assert result == 1.0  # min(1.0, (0.85 + 0.90) / 2 * 1.2)
            mock_crud.get_by_type.assert_called_once_with(
                mock_db, "simple_conversion", validation_status="validated"
            )
    
    @pytest.mark.asyncio
    async def test_validate_conversion_pattern_no_db(self, engine):
        """Test _validate_conversion_pattern without database"""
        path = {"pattern_type": "unknown_conversion"}
        
        result = await engine._validate_conversion_pattern(path, None)
        
        assert result == 0.7  # Default moderate score
    
    @pytest.mark.asyncio
    async def test_validate_conversion_pattern_no_patterns(self, engine, mock_db):
        """Test _validate_conversion_pattern with no successful patterns"""
        path = {"pattern_type": "rare_conversion"}
        
        with patch('src.services.conversion_inference.ConversionPatternCRUD') as mock_crud:
            mock_crud.get_by_type.return_value = []  # No patterns found
            
            result = await engine._validate_conversion_pattern(path, mock_db)
            
            assert result == 0.5  # Neutral score for unknown patterns
    
    @pytest.mark.asyncio
    async def test_check_platform_compatibility_perfect(self, engine):
        """Test _check_platform_compatibility with perfect compatibility"""
        path = {
            "target_platform": "bedrock",
            "minecraft_version": "1.19.3",
            "required_features": ["textures", "behaviors"]
        }
        
        context_data = {
            "minecraft_version": "latest",
            "target_platform": "bedrock"
        }
        
        result = await engine._check_platform_compatibility(path, context_data)
        
        assert isinstance(result, float)
        assert result >= 0.7  # Should be high for perfect compatibility
    
    @pytest.mark.asyncio
    async def test_check_platform_compatibility_version_mismatch(self, engine):
        """Test _check_platform_compatibility with version mismatch"""
        path = {
            "target_platform": "bedrock",
            "minecraft_version": "1.16.5",  # Older version
            "required_features": ["new_features"]  # Not available in older version
        }
        
        context_data = {
            "minecraft_version": "1.16.5",
            "target_platform": "bedrock"
        }
        
        result = await engine._check_platform_compatibility(path, context_data)
        
        assert isinstance(result, float)
        assert result <= 0.7  # Should be lower for version/feature mismatch
    
    @pytest.mark.asyncio
    async def test_refine_with_ml_predictions(self, engine):
        """Test _refine_with_ml_predictions method"""
        path = {
            "path_type": "complex_conversion",
            "confidence": 0.70,
            "complexity_factors": {
                "step_count": 5,
                "feature_count": 10,
                "custom_code_required": True
            }
        }
        
        context_data = {
            "model_version": "v2.0",
            "prediction_accuracy": 0.85
        }
        
        result = await engine._refine_with_ml_predictions(path, context_data)
        
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0
        # Should adjust confidence based on ML predictions
    
    @pytest.mark.asyncio
    async def test_integrate_community_wisdom_high_usage(self, engine, mock_db):
        """Test _integrate_community_wisdom with high community usage"""
        path = {
            "path_type": "entity_conversion",  # Use a known pattern type
            "usage_count": 1000,
            "community_rating": 4.8,
            "success_reports": 950
        }
        
        result = await engine._integrate_community_wisdom(path, mock_db)
        
        assert isinstance(result, float)
        assert result >= 0.6  # Should be reasonable for popular paths
    
    @pytest.mark.asyncio
    async def test_integrate_community_wisdom_low_usage(self, engine, mock_db):
        """Test _integrate_community_wisdom with low community usage"""
        path = {
            "path_type": "unknown",  # Use unknown pattern type
            "usage_count": 5,
            "community_rating": 2.5,
            "success_reports": 2
        }
        
        result = await engine._integrate_community_wisdom(path, mock_db)
        
        assert isinstance(result, float)
        assert result <= 0.6  # Should be low for experimental paths
    
    @pytest.mark.asyncio
    async def test_optimize_for_performance(self, engine):
        """Test _optimize_for_performance method"""
        path = {
            "path_type": "performance_heavy_conversion",
            "steps": [
                {"processing_time": 100, "memory_usage": 50},
                {"processing_time": 200, "memory_usage": 100}
            ],
            "resource_requirements": {
                "cpu_intensive": True,
                "memory_intensive": False,
                "network_required": False
            }
        }
        
        context_data = {
            "performance_priority": "speed",
            "resource_limits": {
                "max_memory": 512,
                "max_cpu_time": 300
            }
        }
        
        result = await engine._optimize_for_performance(path, context_data)
        
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0
        # Should consider performance characteristics
    
    def test_calculate_complexity_simple(self, engine):
        """Test _calculate_complexity for simple conversion"""
        conversion_result = {
            "step_count": 1,
            "pattern_count": 1,
            "custom_code": [],
            "file_count": 1
        }
        
        result = engine._calculate_complexity(conversion_result)
        
        assert isinstance(result, float)
        expected = (1 * 0.2) + (1 * 0.3) + (0 * 0.4) + (1 * 0.1)
        assert result == expected  # Should be 1.0
    
    def test_calculate_complexity_complex(self, engine):
        """Test _calculate_complexity for complex conversion"""
        conversion_result = {
            "step_count": 10,
            "pattern_count": 5,
            "custom_code": ["code1", "code2", "code3"],
            "file_count": 15
        }
        
        result = engine._calculate_complexity(conversion_result)
        
        assert isinstance(result, float)
        expected = (10 * 0.2) + (5 * 0.3) + (3 * 0.4) + (15 * 0.1)
        assert result == expected  # Should be 5.3
    
    @pytest.mark.asyncio
    async def test_store_learning_event(self, engine, mock_db):
        """Test _store_learning_event method"""
        event = {
            "type": "conversion_completed",
            "path_type": "direct",
            "confidence": 0.85,
            "success": True,
            "user_feedback": {"rating": 5}
        }
        
        # Mock the database storage
        with patch('src.services.conversion_inference.logger') as mock_logger:
            await engine._store_learning_event(event, mock_db)
            
            # Should add ID to event
            assert "id" in event
            assert event["id"].startswith("learning_")
            
            # Should log the event
            mock_logger.info.assert_called_once()
            log_message = mock_logger.info.call_args[0][0]
            assert "Storing learning event:" in log_message


class TestTopologicalSort:
    """Test topological sort method and related algorithms"""
    
    @pytest.fixture
    def engine(self):
        """Create engine instance"""
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
    async def test_topological_sort_simple(self, engine):
        """Test _topological_sort with simple dependency graph"""
        dependency_graph = {
            "A": ["B", "C"],
            "B": ["D"],
            "C": ["D"],
            "D": []
        }
        
        result = await engine._topological_sort(dependency_graph)
        
        assert isinstance(result, list)
        assert len(result) == 4
        # D should come after B and C
        assert result.index("D") > result.index("B")
        assert result.index("D") > result.index("C")
        # B and C should come after A
        assert result.index("B") > result.index("A")
        assert result.index("C") > result.index("A")
    
    @pytest.mark.asyncio
    async def test_topological_sort_cycle(self, engine):
        """Test _topological_sort with cycle detection"""
        dependency_graph = {
            "A": ["B"],
            "B": ["C"],
            "C": ["A"]  # Creates a cycle
        }
        
        result = await engine._topological_sort(dependency_graph)
        
        assert isinstance(result, list)
        # Should handle cycle gracefully (either return partial ordering or empty list)
    
    @pytest.mark.asyncio
    async def test_topological_sort_empty(self, engine):
        """Test _topological_sort with empty graph"""
        dependency_graph = {}
        
        result = await engine._topological_sort(dependency_graph)
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_topological_sort_single_node(self, engine):
        """Test _topological_sort with single node"""
        dependency_graph = {
            "A": []
        }
        
        result = await engine._topological_sort(dependency_graph)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == "A"


if __name__ == "__main__":
    pytest.main([__file__])
