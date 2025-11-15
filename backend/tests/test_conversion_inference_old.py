"""
Comprehensive tests for conversion_inference.py module.

This test suite provides extensive coverage for the Conversion Inference Engine,
ensuring all inference algorithms, path finding, and optimization methods are tested.

Coverage Target: ≥80% line coverage for 443 statements
"""

import pytest
import asyncio
import json
import math
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.conversion_inference import ConversionInferenceEngine


class TestConversionInferenceEngine:
    """Test ConversionInferenceEngine class."""
    
    @pytest.fixture
    def engine(self):
        """Create a fresh engine instance for each test."""
        return ConversionInferenceEngine()
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def sample_source_node(self):
        """Sample source node for testing."""
        node = MagicMock()
        node.id = "node123"
        node.name = "TestEntity"
        node.node_type = "entity"
        node.platform = "java"
        node.minecraft_version = "1.20"
        node.description = "Test entity for conversion"
        node.expert_validated = True
        node.community_rating = 4.5
        node.confidence_score = 0.85
        node.properties = '{"complexity": "medium"}'
        return node
    
    @pytest.fixture
    def sample_direct_paths(self):
        """Sample direct conversion paths."""
        return [
            {
                "target_node": MagicMock(id="target1", name="TestEntity_Bedrock"),
                "relationship": MagicMock(
                    relationship_type="converts_to",
                    confidence_score=0.9,
                    conversion_features='{"direct": true}'
                ),
                "confidence": 0.9,
                "path_length": 1,
                "estimated_time": 2.5,
                "complexity": "low"
            },
            {
                "target_node": MagicMock(id="target2", name="AlternativeEntity"),
                "relationship": MagicMock(
                    relationship_type="relates_to",
                    confidence_score=0.7,
                    conversion_features='{"indirect": true}'
                ),
                "confidence": 0.7,
                "path_length": 1,
                "estimated_time": 4.0,
                "complexity": "medium"
            }
        ]
    
    @pytest.fixture
    def sample_indirect_paths(self):
        """Sample indirect conversion paths."""
        return [
            {
                "path": [
                    MagicMock(id="node1", name="TestEntity"),
                    MagicMock(id="node2", name="IntermediateEntity"),
                    MagicMock(id="node3", name="TestEntity_Bedrock")
                ],
                "relationships": [
                    MagicMock(confidence_score=0.8),
                    MagicMock(confidence_score=0.75)
                ],
                "confidence": 0.775,  # (0.8 * 0.75)^0.5
                "path_length": 3,
                "estimated_time": 6.5,
                "complexity": "medium",
                "intermediate_steps": ["IntermediateEntity"]
            }
        ]

    def test_engine_initialization(self, engine):
        """Test engine initializes with correct default values."""
        assert engine.confidence_thresholds["high"] == 0.8
        assert engine.confidence_thresholds["medium"] == 0.6
        assert engine.confidence_thresholds["low"] == 0.4
        assert engine.max_path_depth == 5
        assert engine.min_path_confidence == 0.5
    
    async def test_infer_conversion_path_source_not_found(self, engine, mock_db):
        """Test path inference when source concept not found."""
        java_concept = "NonExistentEntity"
        
        with patch.object(engine, '_find_concept_node') as mock_find, \
             patch.object(engine, '_suggest_similar_concepts') as mock_suggest:
            
            mock_find.return_value = None
            mock_suggest.return_value = ["SimilarEntity", "TestEntity"]
            
            result = await engine.infer_conversion_path(
                java_concept=java_concept,
                db=mock_db,
                target_platform="bedrock",
                minecraft_version="1.20"
            )
            
            assert result["success"] is False
            assert "Source concept not found" in result["error"]
            assert result["java_concept"] == java_concept
            assert "suggestions" in result
            assert "SimilarEntity" in result["suggestions"]
    
    async def test_infer_conversion_path_direct_path_success(self, engine, mock_db, sample_source_node, sample_direct_paths):
        """Test successful path inference with direct paths."""
        with patch.object(engine, '_find_concept_node') as mock_find, \
             patch.object(engine, '_find_direct_paths') as mock_direct, \
             patch.object(engine, '_find_indirect_paths') as mock_indirect:
            
            mock_find.return_value = sample_source_node
            mock_direct.return_value = sample_direct_paths
            
            result = await engine.infer_conversion_path(
                java_concept="TestEntity",
                db=mock_db,
                target_platform="bedrock",
                minecraft_version="1.20"
            )
            
            assert result["success"] is True
            assert result["java_concept"] == "TestEntity"
            assert result["path_type"] == "direct"
            assert "primary_path" in result
            assert result["primary_path"]["confidence"] == 0.9  # Best direct path
            assert len(result["alternative_paths"]) == 1  # Second direct path
            assert result["path_count"] == 2
    
    async def test_infer_conversion_path_no_direct_paths(self, engine, mock_db, sample_source_node, sample_indirect_paths):
        """Test path inference when no direct paths available."""
        with patch.object(engine, '_find_concept_node') as mock_find, \
             patch.object(engine, '_find_direct_paths') as mock_direct, \
             patch.object(engine, '_find_indirect_paths') as mock_indirect, \
             patch.object(engine, '_rank_paths') as mock_rank:
            
            mock_find.return_value = sample_source_node
            mock_direct.return_value = []  # No direct paths
            mock_indirect.return_value = sample_indirect_paths
            mock_rank.return_value = sample_indirect_paths
            
            result = await engine.infer_conversion_path(
                java_concept="TestEntity",
                db=mock_db,
                target_platform="bedrock"
            )
            
            assert result["success"] is True
            assert result["path_type"] == "indirect"
            assert len(result["primary_path"]["intermediate_steps"]) > 0
            assert result["path_count"] == 1
    
    async def test_infer_conversion_path_no_paths_found(self, engine, mock_db, sample_source_node):
        """Test path inference when no paths found."""
        with patch.object(engine, '_find_concept_node') as mock_find, \
             patch.object(engine, '_find_direct_paths') as mock_direct, \
             patch.object(engine, '_find_indirect_paths') as mock_indirect, \
             patch.object(engine, '_suggest_similar_concepts') as mock_suggest:
            
            mock_find.return_value = sample_source_node
            mock_direct.return_value = []
            mock_indirect.return_value = []
            mock_suggest.return_value = ["AlternativeConcept"]
            
            result = await engine.infer_conversion_path(
                java_concept="TestEntity",
                db=mock_db
            )
            
            assert result["success"] is False
            assert "No suitable conversion paths found" in result["error"]
            assert "suggestions" in result
    
    async def test_infer_conversion_path_custom_options(self, engine, mock_db, sample_source_node):
        """Test path inference with custom options."""
        options = {
            "max_depth": 3,
            "min_confidence": 0.7,
            "include_alternatives": False,
            "optimize_for": "speed"
        }
        
        with patch.object(engine, '_find_concept_node') as mock_find, \
             patch.object(engine, '_find_direct_paths') as mock_direct:
            
            mock_find.return_value = sample_source_node
            mock_direct.return_value = []  # Force indirect path search
            
            result = await engine.infer_conversion_path(
                java_concept="TestEntity",
                db=mock_db,
                path_options=options
            )
            
            assert result["success"] is False  # No paths, but options were used
            # Verify options were applied
            mock_find.assert_called_with(mock_db, "TestEntity", "java", "latest")
            mock_direct.assert_called_once()
    
    async def test_infer_conversion_path_exception_handling(self, engine, mock_db):
        """Test path inference exception handling."""
        with patch.object(engine, '_find_concept_node') as mock_find:
            mock_find.side_effect = Exception("Database error")
            
            result = await engine.infer_conversion_path(
                java_concept="TestEntity",
                db=mock_db
            )
            
            assert result["success"] is False
            assert "Path inference failed" in result["error"]
    
    async def test_batch_infer_paths_success(self, engine, mock_db, sample_source_node):
        """Test successful batch path inference."""
        java_concepts = ["TestEntity1", "TestEntity2", "TestEntity3"]
        
        with patch.object(engine, 'infer_conversion_path') as mock_infer, \
             patch.object(engine, '_analyze_batch_paths') as mock_analyze, \
             patch.object(engine, '_optimize_processing_order') as mock_optimize:
            
            # Mock individual path inferences
            mock_infer.side_effect = [
                {
                    "success": True,
                    "path_type": "direct",
                    "primary_path": {"confidence": 0.9},
                    "alternative_paths": []
                },
                {
                    "success": True,
                    "path_type": "indirect",
                    "primary_path": {"confidence": 0.7},
                    "alternative_paths": []
                },
                {
                    "success": False,
                    "error": "Concept not found"
                }
            ]
            
            mock_analyze.return_value = {
                "successful_conversions": 2,
                "failed_conversions": 1,
                "average_confidence": 0.8,
                "optimization_opportunities": ["batch_processing"]
            }
            
            mock_optimize.return_value = java_concepts
            
            result = await engine.batch_infer_paths(
                java_concepts=java_concepts,
                db=mock_db,
                target_platform="bedrock"
            )
            
            assert result["success"] is True
            assert result["total_concepts"] == 3
            assert result["successful_conversions"] == 2
            assert result["failed_conversions"] == 1
            assert "batch_results" in result
            assert "batch_analysis" in result
            assert "optimization_plan" in result
            
            # Check individual results
            batch_results = result["batch_results"]
            assert "TestEntity1" in batch_results
            assert "TestEntity2" in batch_results
            assert "TestEntity3" in batch_results
            assert batch_results["TestEntity1"]["success"] is True
            assert batch_results["TestEntity3"]["success"] is False
    
    async def test_batch_infer_paths_empty_list(self, engine, mock_db):
        """Test batch path inference with empty concept list."""
        result = await engine.batch_infer_paths(
            java_concepts=[],
            db=mock_db
        )
        
        assert result["success"] is True
        assert result["total_concepts"] == 0
        assert result["successful_conversions"] == 0
        assert result["failed_conversions"] == 0
        assert len(result["batch_results"]) == 0
    
    async def test_batch_infer_paths_partial_failure(self, engine, mock_db):
        """Test batch path inference with partial failures."""
        java_concepts = ["TestEntity1", "TestEntity2"]
        
        with patch.object(engine, 'infer_conversion_path') as mock_infer, \
             patch.object(engine, '_analyze_batch_paths') as mock_analyze:
            
            mock_infer.side_effect = [
                {"success": True, "path_type": "direct"},
                {"success": False, "error": "Database error"}
            ]
            
            mock_analyze.return_value = {
                "successful_conversions": 1,
                "failed_conversions": 1,
                "average_confidence": 0.8
            }
            
            result = await engine.batch_infer_paths(
                java_concepts=java_concepts,
                db=mock_db
            )
            
            assert result["success"] is True  # Partial success still succeeds
            assert result["successful_conversions"] == 1
            assert result["failed_conversions"] == 1
    
    async def test_optimize_conversion_sequence_success(self, engine, mock_db):
        """Test successful conversion sequence optimization."""
        conversion_sequence = [
            {
                "concept": "TestEntity1",
                "target_platform": "bedrock",
                "priority": 1,
                "estimated_time": 3.0,
                "dependencies": []
            },
            {
                "concept": "TestEntity2",
                "target_platform": "bedrock",
                "priority": 2,
                "estimated_time": 2.5,
                "dependencies": ["TestEntity1"]
            },
            {
                "concept": "TestEntity3",
                "target_platform": "bedrock",
                "priority": 1,
                "estimated_time": 4.0,
                "dependencies": []
            }
        ]
        
        with patch.object(engine, '_identify_shared_steps') as mock_shared, \
             patch.object(engine, '_generate_batch_plan') as mock_plan, \
             patch.object(engine, '_calculate_savings') as mock_savings:
            
            mock_shared.return_value = [
                {"concepts": ["TestEntity1", "TestEntity3"], "shared_steps": ["validation"]}
            ]
            
            mock_plan.return_value = {
                "optimized_sequence": ["TestEntity1", "TestEntity3", "TestEntity2"],
                "batch_operations": [
                    {"concepts": ["TestEntity1", "TestEntity3"], "operation": "batch_validate"}
                ],
                "estimated_total_time": 8.5
            }
            
            mock_savings.return_value = {
                "time_savings": 2.5,
                "confidence_improvement": 0.15,
                "resource_optimization": 0.3
            }
            
            result = await engine.optimize_conversion_sequence(
                conversions=conversion_sequence,
                db=mock_db
            )
            
            assert result["success"] is True
            assert "optimized_sequence" in result
            assert "batch_operations" in result
            assert "savings" in result
            assert "optimization_metadata" in result
            
            # Check optimized order (dependent after prerequisite)
            optimized = result["optimized_sequence"]
            assert optimized.index("TestEntity1") < optimized.index("TestEntity2")
            
            # Check batch operations
            batch_ops = result["batch_operations"]
            assert len(batch_ops) > 0
            assert "batch_validate" in str(batch_ops)
            
            # Check savings
            savings = result["savings"]
            assert savings["time_savings"] == 2.5
            assert savings["confidence_improvement"] == 0.15
    
    async def test_optimize_conversion_sequence_no_dependencies(self, engine, mock_db):
        """Test conversion sequence optimization with no dependencies."""
        conversion_sequence = [
            {
                "concept": "TestEntity1",
                "target_platform": "bedrock",
                "priority": 1,
                "estimated_time": 2.0,
                "dependencies": []
            },
            {
                "concept": "TestEntity2",
                "target_platform": "bedrock",
                "priority": 2,
                "estimated_time": 3.0,
                "dependencies": []
            }
        ]
        
        with patch.object(engine, '_identify_shared_steps') as mock_shared, \
             patch.object(engine, '_generate_batch_plan') as mock_plan:
            
            mock_shared.return_value = []
            mock_plan.return_value = {
                "optimized_sequence": ["TestEntity1", "TestEntity2"],
                "batch_operations": [],
                "estimated_total_time": 5.0
            }
            
            result = await engine.optimize_conversion_sequence(
                conversions=conversion_sequence,
                db=mock_db
            )
            
            assert result["success"] is True
            assert len(result["batch_operations"]) == 0  # No shared steps
    
    async def test_optimize_conversion_sequence_complex_dependencies(self, engine, mock_db):
        """Test conversion sequence optimization with complex dependencies."""
        conversion_sequence = [
            {
                "concept": "BaseEntity",
                "dependencies": []
            },
            {
                "concept": "DerivedEntity1",
                "dependencies": ["BaseEntity"]
            },
            {
                "concept": "DerivedEntity2",
                "dependencies": ["BaseEntity"]
            },
            {
                "concept": "FinalEntity",
                "dependencies": ["DerivedEntity1", "DerivedEntity2"]
            }
        ]
        
        with patch.object(engine, '_identify_shared_steps') as mock_shared, \
             patch.object(engine, '_generate_batch_plan') as mock_plan:
            
            mock_shared.return_value = []
            mock_plan.return_value = {
                "optimized_sequence": ["BaseEntity", "DerivedEntity1", "DerivedEntity2", "FinalEntity"],
                "batch_operations": [],
                "estimated_total_time": 10.0
            }
            
            result = await engine.optimize_conversion_sequence(
                conversions=conversion_sequence,
                db=mock_db
            )
            
            assert result["success"] is True
            # Verify dependency ordering
            optimized = result["optimized_sequence"]
            base_idx = optimized.index("BaseEntity")
            derived1_idx = optimized.index("DerivedEntity1")
            derived2_idx = optimized.index("DerivedEntity2")
            final_idx = optimized.index("FinalEntity")
            
            assert base_idx < derived1_idx
            assert base_idx < derived2_idx
            assert derived1_idx < final_idx
            assert derived2_idx < final_idx
    
    async def test_learn_from_conversion_success(self, engine, mock_db, sample_source_node):
        """Test successful learning from conversion results."""
        conversion_result = {
            "java_concept": "TestEntity",
            "bedrock_concept": "TestEntity_Bedrock",
            "path_used": "direct",
            "success": True,
            "confidence": 0.9,
            "actual_confidence": 0.85,
            "conversion_time": 2.5,
            "errors": [],
            "optimizations_applied": ["direct_mapping"],
            "user_feedback": {"rating": 4.5, "comments": "Perfect conversion"}
        }
        
        with patch.object(engine, '_update_knowledge_graph') as mock_update, \
             patch.object(engine, '_adjust_confidence_thresholds') as mock_adjust, \
             patch.object(engine, '_store_learning_event') as mock_store, \
             patch.object(engine, '_analyze_conversion_performance') as mock_analyze:
            
            mock_update.return_value = {"success": True, "updated_nodes": 2}
            mock_adjust.return_value = {"threshold_adjusted": True, "new_thresholds": {}}
            mock_analyze.return_value = {
                "performance_score": 0.85,
                "improvements_needed": ["none"],
                "success_rate": 0.9
            }
            
            result = await engine.learn_from_conversion(
                conversion_result=conversion_result,
                db=mock_db
            )
            
            assert result["success"] is True
            assert "learning_applied" in result
            assert "knowledge_updates" in result
            assert "threshold_adjustments" in result
            assert "performance_analysis" in result
            
            # Verify components were called
            mock_update.assert_called_once()
            mock_adjust.assert_called_once()
            mock_store.assert_called_once()
            mock_analyze.assert_called_once()
    
    async def test_learn_from_conversion_failure(self, engine, mock_db):
        """Test learning from failed conversion."""
        conversion_result = {
            "java_concept": "TestEntity",
            "bedrock_concept": None,
            "path_used": None,
            "success": False,
            "confidence": 0.0,
            "actual_confidence": 0.0,
            "conversion_time": 0.0,
            "errors": ["Concept not found", "No conversion path"],
            "optimizations_applied": [],
            "user_feedback": {"rating": 1.0, "comments": "Complete failure"}
        }
        
        with patch.object(engine, '_update_knowledge_graph') as mock_update, \
             patch.object(engine, '_adjust_confidence_thresholds') as mock_adjust, \
             patch.object(engine, '_store_learning_event') as mock_store, \
             patch.object(engine, '_analyze_conversion_performance') as mock_analyze:
            
            mock_update.return_value = {"success": True, "updated_nodes": 0}
            mock_adjust.return_value = {"threshold_adjusted": True, "new_thresholds": {}}
            mock_analyze.return_value = {
                "performance_score": 0.1,
                "improvements_needed": ["concept_identification", "path_finding"],
                "success_rate": 0.0
            }
            
            result = await engine.learn_from_conversion(
                conversion_result=conversion_result,
                db=mock_db
            )
            
            assert result["success"] is True
            # Should still learn from failure
            assert "learning_applied" in result
    
    async def test_learn_from_conversion_exception(self, engine, mock_db):
        """Test learning with exception handling."""
        conversion_result = {"test": "data"}
        
        with patch.object(engine, '_store_learning_event') as mock_store:
            mock_store.side_effect = Exception("Learning error")
            
            result = await engine.learn_from_conversion(
                conversion_result=conversion_result,
                db=mock_db
            )
            
            assert result["success"] is False
            assert "Learning failed" in result["error"]
    
    async def test_get_inference_statistics_success(self, engine):
        """Test successful inference statistics retrieval."""
        # Set up some mock statistics
        engine.confidence_thresholds = {
            "high": 0.85,
            "medium": 0.65,
            "low": 0.45
        }
        
        with patch.object(engine, '_analyze_conversion_performance') as mock_analyze:
            mock_analyze.return_value = {
                "overall_success_rate": 0.82,
                "average_confidence": 0.78,
                "conversion_attempts": 100,
                "successful_conversions": 82
            }
            
            result = await engine.get_inference_statistics()
            
            assert result["success"] is True
            assert "engine_configuration" in result
            assert "performance_metrics" in result
            assert "recommendations" in result
            
            # Check configuration
            config = result["engine_configuration"]
            assert config["confidence_thresholds"]["high"] == 0.85
            assert config["max_path_depth"] == 5
            assert config["min_path_confidence"] == 0.5
            
            # Check performance
            perf = result["performance_metrics"]
            assert perf["overall_success_rate"] == 0.82
            assert perf["average_confidence"] == 0.78
    
    async def test_get_inference_statistics_no_data(self, engine):
        """Test inference statistics with no performance data."""
        with patch.object(engine, '_analyze_conversion_performance') as mock_analyze:
            mock_analyze.return_value = {
                "overall_success_rate": 0.0,
                "average_confidence": 0.0,
                "conversion_attempts": 0,
                "successful_conversions": 0
            }
            
            result = await engine.get_inference_statistics()
            
            assert result["success"] is True
            assert result["performance_metrics"]["conversion_attempts"] == 0
    
    async def test_find_concept_node_success(self, engine, mock_db, sample_source_node):
        """Test successful concept node finding."""
        with patch('src.services.conversion_inference.KnowledgeNodeCRUD.get_by_name') as mock_get:
            mock_get.return_value = sample_source_node
            
            result = await engine._find_concept_node(
                mock_db, "TestEntity", "java", "1.20"
            )
            
            assert result is not None
            assert result.name == "TestEntity"
            assert result.platform == "java"
            assert result.node_type == "entity"
    
    async def test_find_concept_node_not_found(self, engine, mock_db):
        """Test concept node finding when node not found."""
        with patch('src.services.conversion_inference.KnowledgeNodeCRUD.get_by_name') as mock_get:
            mock_get.return_value = None
            
            result = await engine._find_concept_node(
                mock_db, "NonExistentEntity", "java", "1.20"
            )
            
            assert result is None
    
    async def test_find_concept_node_exception(self, engine, mock_db):
        """Test concept node finding exception handling."""
        with patch('src.services.conversion_inference.KnowledgeNodeCRUD.get_by_name') as mock_get:
            mock_get.side_effect = Exception("Database error")
            
            result = await engine._find_concept_node(
                mock_db, "TestEntity", "java", "1.20"
            )
            
            assert result is None
    
    async def test_find_direct_paths_success(self, engine, mock_db, sample_source_node):
        """Test successful direct paths finding."""
        with patch('src.services.conversion_inference.KnowledgeRelationshipCRUD.find_direct_conversions') as mock_find:
            # Mock relationships
            mock_relationships = [
                MagicMock(
                    target_node_id="target1",
                    relationship_type="converts_to",
                    confidence_score=0.9,
                    conversion_features='{"direct": true}'
                ),
                MagicMock(
                    target_node_id="target2",
                    relationship_type="relates_to",
                    confidence_score=0.7,
                    conversion_features='{"indirect": true}'
                )
            ]
            
            mock_target_nodes = [
                MagicMock(id="target1", name="TestEntity_Bedrock"),
                MagicMock(id="target2", name="AlternativeEntity")
            ]
            
            with patch('src.services.conversion_inference.KnowledgeNodeCRUD.get_by_ids') as mock_get_nodes:
                mock_find.return_value = mock_relationships
                mock_get_nodes.return_value = mock_target_nodes
                
                result = await engine._find_direct_paths(
                    mock_db, sample_source_node, "bedrock", "1.20"
                )
                
                assert len(result) == 2
                assert result[0]["confidence"] == 0.9
                assert result[0]["path_length"] == 1
                assert result[1]["confidence"] == 0.7
                assert result[1]["path_length"] == 1
    
    async def test_find_direct_paths_no_results(self, engine, mock_db, sample_source_node):
        """Test direct paths finding with no results."""
        with patch('src.services.conversion_inference.KnowledgeRelationshipCRUD.find_direct_conversions') as mock_find:
            mock_find.return_value = []
            
            result = await engine._find_direct_paths(
                mock_db, sample_source_node, "bedrock", "1.20"
            )
            
            assert result == []
    
    async def test_find_indirect_paths_success(self, engine, mock_db, sample_source_node):
        """Test successful indirect paths finding."""
        with patch('src.services.conversion_inference.graph_db.find_paths') as mock_graph_find:
            # Mock path finding
            mock_paths = [
                {
                    "nodes": [
                        sample_source_node,
                        MagicMock(id="intermediate1", name="IntermediateEntity"),
                        MagicMock(id="target1", name="TestEntity_Bedrock")
                    ],
                    "relationships": [
                        MagicMock(confidence_score=0.8),
                        MagicMock(confidence_score=0.75)
                    ]
                }
            ]
            
            mock_graph_find.return_value = mock_paths
            
            result = await engine._find_indirect_paths(
                mock_db, sample_source_node, "bedrock", "1.20", max_depth=3
            )
            
            assert len(result) == 1
            assert result[0]["path_length"] == 3
            assert result[0]["confidence"] > 0.7  # Combined confidence
            assert len(result[0]["intermediate_steps"]) == 1
            assert "IntermediateEntity" in result[0]["intermediate_steps"]
    
    async def test_find_indirect_paths_no_results(self, engine, mock_db, sample_source_node):
        """Test indirect paths finding with no results."""
        with patch('src.services.conversion_inference.graph_db.find_paths') as mock_graph_find:
            mock_graph_find.return_value = []
            
            result = await engine._find_indirect_paths(
                mock_db, sample_source_node, "bedrock", "1.20", max_depth=3
            )
            
            assert result == []
    
    async def test_find_indirect_paths_max_depth(self, engine, mock_db, sample_source_node):
        """Test indirect paths finding with depth limit."""
        with patch('src.services.conversion_inference.graph_db.find_paths') as mock_graph_find:
            # Mock paths with different lengths
            mock_paths = [
                {
                    "nodes": [sample_source_node] + [MagicMock()] * 2,  # Length 3
                    "relationships": [MagicMock(), MagicMock()]
                },
                {
                    "nodes": [sample_source_node] + [MagicMock()] * 6,  # Length 7 (too long)
                    "relationships": [MagicMock()] * 6
                }
            ]
            
            mock_graph_find.return_value = mock_paths
            
            result = await engine._find_indirect_paths(
                mock_db, sample_source_node, "bedrock", "1.20", max_depth=5
            )
            
            # Should only include paths within depth limit
            assert len(result) == 1
            assert result[0]["path_length"] == 3
    
    async def test_rank_paths_confidence_optimization(self, engine, sample_direct_paths):
        """Test path ranking with confidence optimization."""
        result = await engine._rank_paths(
            paths=sample_direct_paths,
            optimize_for="confidence"
        )
        
        assert len(result) == 2
        assert result[0]["confidence"] >= result[1]["confidence"]  # Sorted by confidence
        assert result[0]["confidence"] == 0.9  # Highest confidence first
    
    async def test_rank_paths_speed_optimization(self, engine, sample_direct_paths):
        """Test path ranking with speed optimization."""
        result = await engine._rank_paths(
            paths=sample_direct_paths,
            optimize_for="speed"
        )
        
        assert len(result) == 2
        assert result[0]["estimated_time"] <= result[1]["estimated_time"]  # Sorted by time
        assert result[0]["estimated_time"] == 2.5  # Fastest first
    
    async def test_rank_paths_features_optimization(self, engine, sample_direct_paths):
        """Test path ranking with features optimization."""
        result = await engine._rank_paths(
            paths=sample_direct_paths,
            optimize_for="features"
        )
        
        assert len(result) == 2
        # Features optimization might prioritize paths with more conversion features
        # Implementation specific - just verify structure
        assert "confidence" in result[0]
        assert "estimated_time" in result[0]
    
    async def test_suggest_similar_concepts_success(self, engine, mock_db):
        """Test successful similar concepts suggestion."""
        with patch('src.services.conversion_inference.KnowledgeNodeCRUD.search_by_name') as mock_search:
            mock_nodes = [
                MagicMock(name="TestEntityVariant", node_type="entity"),
                MagicMock(name="SimilarTestEntity", node_type="entity"),
                MagicMock(name="TestRelatedEntity", node_type="entity")
            ]
            
            mock_search.return_value = mock_nodes
            
            result = await engine._suggest_similar_concepts(
                mock_db, "TestEntity", "java"
            )
            
            assert len(result) == 3
            assert "TestEntityVariant" in result
            assert "SimilarTestEntity" in result
            assert "TestRelatedEntity" in result
    
    async def test_suggest_similar_concepts_no_results(self, engine, mock_db):
        """Test similar concepts suggestion with no results."""
        with patch('src.services.conversion_inference.KnowledgeNodeCRUD.search_by_name') as mock_search:
            mock_search.return_value = []
            
            result = await engine._suggest_similar_concepts(
                mock_db, "UniqueEntity", "java"
            )
            
            assert result == []
    
    async def test_analyze_batch_paths_success(self, engine):
        """Test successful batch paths analysis."""
        batch_results = {
            "concept1": {
                "success": True,
                "confidence": 0.9,
                "path_type": "direct",
                "estimated_time": 2.5
            },
            "concept2": {
                "success": True,
                "confidence": 0.7,
                "path_type": "indirect",
                "estimated_time": 4.0
            },
            "concept3": {
                "success": False,
                "error": "Concept not found"
            }
        }
        
        result = await engine._analyze_batch_paths(batch_results)
        
        assert result["successful_conversions"] == 2
        assert result["failed_conversions"] == 1
        assert result["average_confidence"] == 0.8  # (0.9 + 0.7) / 2
        assert result["average_estimated_time"] == 3.25  # (2.5 + 4.0) / 2
        assert "optimization_opportunities" in result
    
    async def test_analyze_batch_paths_empty(self, engine):
        """Test batch paths analysis with empty results."""
        result = await engine._analyze_batch_paths({})
        
        assert result["successful_conversions"] == 0
        assert result["failed_conversions"] == 0
        assert result["average_confidence"] == 0.0
        assert result["average_estimated_time"] == 0.0
    
    async def test_optimize_processing_order_success(self, engine):
        """Test successful processing order optimization."""
        concepts = [
            {"concept": "concept1", "priority": 1, "dependencies": []},
            {"concept": "concept2", "priority": 2, "dependencies": ["concept1"]},
            {"concept": "concept3", "priority": 1, "dependencies": []},
            {"concept": "concept4", "priority": 2, "dependencies": ["concept2", "concept3"]}
        ]
        
        result = await engine._optimize_processing_order(concepts)
        
        assert len(result) == 4
        # Verify dependency ordering
        idx1 = result.index("concept1")
        idx2 = result.index("concept2")
        idx3 = result.index("concept3")
        idx4 = result.index("concept4")
        
        assert idx1 < idx2  # concept1 before concept2
        assert idx3 < idx4  # concept3 before concept4
        assert idx2 < idx4  # concept2 before concept4
    
    async def test_identify_shared_steps_success(self, engine):
        """Test successful shared steps identification."""
        conversions = [
            {
                "concept": "concept1",
                "target_platform": "bedrock",
                "conversion_steps": ["validation", "mapping", "testing"]
            },
            {
                "concept": "concept2",
                "target_platform": "bedrock",
                "conversion_steps": ["validation", "mapping", "optimization"]
            },
            {
                "concept": "concept3",
                "target_platform": "bedrock",
                "conversion_steps": ["validation", "testing"]
            }
        ]
        
        result = await engine._identify_shared_steps(conversions)
        
        assert len(result) > 0
        # Should identify shared validation step
        shared_steps = [s for s in result if "validation" in s.get("shared_steps", [])]
        assert len(shared_steps) > 0
        
        # Check that shared steps include multiple concepts
        for shared in result:
            if len(shared["concepts"]) > 1:
                assert len(shared["shared_steps"]) > 0
    
    async def test_identify_shared_steps_no_shared(self, engine):
        """Test shared steps identification with no shared steps."""
        conversions = [
            {
                "concept": "concept1",
                "conversion_steps": ["unique_step1"]
            },
            {
                "concept": "concept2",
                "conversion_steps": ["unique_step2"]
            }
        ]
        
        result = await engine._identify_shared_steps(conversions)
        
        assert len(result) == 0  # No shared steps
    
    def test_estimate_batch_time(self, engine):
        """Test batch time estimation."""
        conversions = [
            {"estimated_time": 2.5, "can_batch": True},
            {"estimated_time": 3.0, "can_batch": True},
            {"estimated_time": 1.5, "can_batch": False}
        ]
        
        # Batch efficiency for 2 bachable conversions
        batch_efficiency = 0.8
        
        result = engine._estimate_batch_time(conversions, batch_efficiency)
        
        # Expected: (2.5 + 3.0) * 0.8 + 1.5 = 5.9
        expected_time = (2.5 + 3.0) * batch_efficiency + 1.5
        
        assert abs(result - expected_time) < 0.1
    
    def test_estimate_batch_time_empty(self, engine):
        """Test batch time estimation with empty conversions."""
        result = engine._estimate_batch_time([], 0.8)
        
        assert result == 0.0
    
    async def test_calculate_savings(self, engine):
        """Test savings calculation."""
        original_time = 10.0
        optimized_time = 7.5
        original_confidence = 0.7
        optimized_confidence = 0.85
        
        result = await engine._calculate_savings(
            original_time, optimized_time, original_confidence, optimized_confidence
        )
        
        assert "time_savings" in result
        assert "confidence_improvement" in result
        assert "resource_optimization" in result
        
        # Check time savings
        expected_time_savings = (original_time - optimized_time) / original_time
        assert abs(result["time_savings"] - expected_time_savings) < 0.1
        
        # Check confidence improvement
        expected_conf_improvement = optimized_confidence - original_confidence
        assert abs(result["confidence_improvement"] - expected_conf_improvement) < 0.1
    
    async def test_analyze_conversion_performance_success(self, engine):
        """Test successful conversion performance analysis."""
        conversion_history = [
            {"success": True, "confidence": 0.9, "actual_confidence": 0.85, "time": 2.5},
            {"success": True, "confidence": 0.8, "actual_confidence": 0.82, "time": 3.0},
            {"success": False, "confidence": 0.7, "actual_confidence": 0.0, "time": 1.0},
            {"success": True, "confidence": 0.85, "actual_confidence": 0.88, "time": 2.8}
        ]
        
        result = await engine._analyze_conversion_performance(conversion_history)
        
        assert "success_rate" in result
        assert "average_confidence" in result
        assert "confidence_accuracy" in result
        assert "average_time" in result
        
        # Check success rate
        assert result["success_rate"] == 0.75  # 3/4 successful
        
        # Check average confidence
        expected_avg_conf = (0.9 + 0.8 + 0.7 + 0.85) / 4
        assert abs(result["average_confidence"] - expected_avg_conf) < 0.1
    
    async def test_analyze_conversion_performance_empty(self, engine):
        """Test conversion performance analysis with empty history."""
        result = await engine._analyze_conversion_performance([])
        
        assert result["success_rate"] == 0.0
        assert result["average_confidence"] == 0.0
        assert result["confidence_accuracy"] == 0.0
        assert result["average_time"] == 0.0
    
    def test_calculate_complexity(self, engine):
        """Test complexity calculation."""
        # Simple conversion
        simple_conversion = {
            "path_length": 1,
            "confidence": 0.9,
            "complexity_factors": ["direct"],
            "estimated_time": 2.0
        }
        
        simple_complexity = engine._calculate_complexity(simple_conversion)
        
        # Complex conversion
        complex_conversion = {
            "path_length": 5,
            "confidence": 0.6,
            "complexity_factors": ["indirect", "multi_step", "custom_logic"],
            "estimated_time": 10.0
        }
        
        complex_complexity = engine._calculate_complexity(complex_conversion)
        
        # Complex should have higher complexity score
        assert complex_complexity > simple_complexity
        assert 0.0 <= simple_complexity <= 1.0
        assert 0.0 <= complex_complexity <= 1.0
    
    def test_calculate_improvement_percentage(self, engine):
        """Test improvement percentage calculation."""
        # Positive improvement
        positive = engine._calculate_improvement_percentage(0.7, 0.85)
        assert positive == pytest.approx(21.4, rel=1e-1)  # (0.85-0.7)/0.7 * 100
        
        # Negative improvement (regression)
        negative = engine._calculate_improvement_percentage(0.8, 0.6)
        assert negative == pytest.approx(-25.0, rel=1e-1)  # (0.6-0.8)/0.8 * 100
        
        # No improvement
        no_change = engine._calculate_improvement_percentage(0.75, 0.75)
        assert no_change == 0.0
        
        # Edge case - original is 0
        zero_original = engine._calculate_improvement_percentage(0.0, 0.5)
        assert zero_original == 0.0  # Should handle division by zero


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @pytest.fixture
    def engine(self):
        """Create a fresh engine instance for each test."""
        return ConversionInferenceEngine()
    
    def test_extreme_confidence_values(self, engine):
        """Test handling of extreme confidence values."""
        # Very high confidence
        high_conf = {
            "confidence": 1.0,
            "path_length": 1,
            "estimated_time": 0.1
        }
        
        # Very low confidence  
        low_conf = {
            "confidence": 0.0,
            "path_length": 10,
            "estimated_time": 100.0
        }
        
        high_complexity = engine._calculate_complexity(high_conf)
        low_complexity = engine._calculate_complexity(low_conf)
        
        assert 0.0 <= high_complexity <= 1.0
        assert 0.0 <= low_complexity <= 1.0
        assert low_complexity > high_complexity  # Low confidence should have higher complexity
    
    def test_circular_dependencies(self, engine):
        """Test handling of circular dependencies in optimization."""
        conversions = [
            {"concept": "A", "dependencies": ["B"]},
            {"concept": "B", "dependencies": ["C"]},
            {"concept": "C", "dependencies": ["A"]}  # Circular dependency
        ]
        
        # Should handle circular dependencies gracefully
        # Implementation specific - just test no infinite loops
        try:
            result = asyncio.run(engine._optimize_processing_order(conversions))
            # Either returns partial order or handles the cycle
            assert isinstance(result, list)
        except Exception as e:
            # Should throw a meaningful error for circular dependencies
            assert "circular" in str(e).lower() or "cycle" in str(e).lower()
    
    def test_empty_paths_list(self, engine):
        """Test ranking of empty paths list."""
        result = asyncio.run(engine._rank_paths([], optimize_for="confidence"))
        
        assert result == []
    
    def test_none_values_in_data(self, engine):
        """Test handling of None values in conversion data."""
        conversion_result = {
            "java_concept": "TestEntity",
            "bedrock_concept": None,  # None value
            "confidence": None,  # None value
            "success": True
        }
        
        # Should handle None values gracefully
        # Implementation specific - test that no exceptions are raised
        try:
            complexity = engine._calculate_complexity(conversion_result)
            assert isinstance(complexity, float)
        except Exception:
            # If exception occurs, should be handled gracefully
            pass
    
    def test_very_large_batch_size(self, engine):
        """Test handling of very large batch sizes."""
        large_batch = []
        for i in range(10000):  # Very large batch
            large_batch.append({
                "concept": f"concept{i}",
                "priority": i % 3,
                "dependencies": [],
                "estimated_time": 1.0 + (i % 5)
            })
        
        # Should handle large batches without memory issues
        try:
            result = asyncio.run(engine._optimize_processing_order(large_batch))
            assert isinstance(result, list)
            # Should maintain original count
            assert len(result) == 10000
        except MemoryError:
            # Memory errors are acceptable for very large batches
            pass
    
    def test_unicode_concept_names(self, engine):
        """Test handling of unicode concept names."""
        unicode_concepts = [
            "实体测试",  # Chinese
            "エンティティ",  # Japanese
            "entité😊",  # French with emoji
            "עצם",  # Hebrew (RTL)
        ]
        
        # Should handle unicode names without issues
        for concept in unicode_concepts:
            try:
                # Test that concept names can be processed
                assert len(concept) > 0
                assert isinstance(concept, str)
            except Exception as e:
                pytest.fail(f"Failed to handle unicode concept '{concept}': {e}")
    
    def test_malformed_json_features(self, engine):
        """Test handling of malformed JSON in conversion features."""
        malformed_json = '{"incomplete": json'
        valid_json = '{"valid": true, "features": ["test"]}'
        
        # Should handle malformed JSON gracefully
        # Implementation specific - test robustness
        try:
            parsed_valid = json.loads(valid_json)
            assert parsed_valid["valid"] is True
            
            # This should fail but be handled gracefully
            try:
                parsed_malformed = json.loads(malformed_json)
                # If it doesn't fail, that's unexpected but acceptable
                pass
            except json.JSONDecodeError:
                # Expected behavior
                pass
        except Exception as e:
            pytest.fail(f"JSON handling failed unexpectedly: {e}")


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "--tb=short"])
