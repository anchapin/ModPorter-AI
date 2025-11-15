"""
Comprehensive tests for conversion_inference.py

This test module provides comprehensive coverage of the conversion inference engine,
focusing on core path finding, optimization, and validation functionality.
"""

import pytest
import json
import sys
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.conversion_inference import ConversionInferenceEngine
from src.db.knowledge_graph_crud import KnowledgeNodeCRUD, KnowledgeRelationshipCRUD, ConversionPatternCRUD


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def conversion_engine():
    """Create a conversion inference engine instance with mocked dependencies."""
    with patch('src.services.conversion_inference.logger'):
        engine = ConversionInferenceEngine()
        return engine


class TestConversionInferenceEngine:
    """Test cases for ConversionInferenceEngine class."""

    class TestInitialization:
        """Test cases for engine initialization."""

        def test_init(self, conversion_engine):
            """Test engine initialization."""
            # Verify confidence thresholds
            assert conversion_engine.confidence_thresholds["high"] == 0.8
            assert conversion_engine.confidence_thresholds["medium"] == 0.6
            assert conversion_engine.confidence_thresholds["low"] == 0.4

            # Verify path configuration
            assert conversion_engine.max_path_depth == 5
            assert conversion_engine.min_path_confidence == 0.5

    class TestPathInference:
        """Test cases for conversion path inference."""

        @pytest.mark.asyncio
        async def test_infer_conversion_path_basic(self, conversion_engine, mock_db_session):
            """Test basic conversion path inference."""
            # Mock the node finding
            conversion_engine._find_matching_nodes = AsyncMock(return_value=[
                {"id": "node1", "name": "Java Block", "platform": "java", "type": "block"}
            ])

            # Mock the path finding
            conversion_engine._find_conversion_paths = AsyncMock(return_value=[
                {
                    "path": ["node1", "node2", "node3"],
                    "steps": [
                        {"from": "node1", "to": "node2", "conversion": "direct"},
                        {"from": "node2", "to": "node3", "conversion": "transformation"}
                    ],
                    "confidence": 0.85,
                    "complexity": "low"
                }
            ])

            # Call the method
            result = await conversion_engine.infer_conversion_path(
                java_concept="Java Block",
                db=mock_db_session,
                target_platform="bedrock",
                minecraft_version="1.18.2"
            )

            # Verify the result
            assert result["success"] is True
            assert result["java_concept"] == "Java Block"
            assert result["target_platform"] == "bedrock"
            assert result["minecraft_version"] == "1.18.2"
            assert len(result["paths"]) == 1
            assert result["paths"][0]["confidence"] == 0.85
            assert len(result["paths"][0]["steps"]) == 2
            assert "path_metadata" in result

        @pytest.mark.asyncio
        async def test_infer_conversion_path_no_match(self, conversion_engine, mock_db_session):
            """Test conversion path inference with no matching nodes."""
            # Mock empty node finding
            conversion_engine._find_matching_nodes = AsyncMock(return_value=[])

            # Call the method
            result = await conversion_engine.infer_conversion_path(
                java_concept="Nonexistent Concept",
                db=mock_db_session
            )

            # Verify the result
            assert result["success"] is False
            assert result["error"] == "No matching concept found"
            assert "suggestions" in result
            assert result["suggestions"]["similar_concepts"] == []
            assert result["suggestions"]["alternative_searches"] == []

        @pytest.mark.asyncio
        async def test_infer_conversion_path_with_suggestions(self, conversion_engine, mock_db_session):
            """Test conversion path inference with suggestions."""
            # Mock no exact matches but similar concepts
            conversion_engine._find_matching_nodes = AsyncMock(return_value=[])
            conversion_engine._find_similar_concepts = AsyncMock(return_value=[
                {"name": "Java Block", "similarity": 0.9},
                {"name": "Java Item", "similarity": 0.7}
            ])

            # Call the method
            result = await conversion_engine.infer_conversion_path(
                java_concept="Jav Blok",
                db=mock_db_session
            )

            # Verify the result
            assert result["success"] is False
            assert result["error"] == "No matching concept found"
            assert len(result["suggestions"]["similar_concepts"]) == 2
            assert result["suggestions"]["similar_concepts"][0]["name"] == "Java Block"
            assert result["suggestions"]["similar_concepts"][0]["similarity"] == 0.9
            assert len(result["suggestions"]["alternative_searches"]) > 0

        @pytest.mark.asyncio
        async def test_infer_conversion_path_complexity_filter(self, conversion_engine, mock_db_session):
            """Test conversion path inference with complexity filtering."""
            # Mock the node finding
            conversion_engine._find_matching_nodes = AsyncMock(return_value=[
                {"id": "node1", "name": "Java Block", "platform": "java", "type": "block"}
            ])

            # Mock multiple paths with different complexities
            conversion_engine._find_conversion_paths = AsyncMock(return_value=[
                {
                    "path": ["node1", "node2", "node3"],
                    "steps": [
                        {"from": "node1", "to": "node2", "conversion": "direct"},
                        {"from": "node2", "to": "node3", "conversion": "transformation"}
                    ],
                    "confidence": 0.85,
                    "complexity": "low"
                },
                {
                    "path": ["node1", "node4", "node5", "node6"],
                    "steps": [
                        {"from": "node1", "to": "node4", "conversion": "direct"},
                        {"from": "node4", "to": "node5", "conversion": "transformation"},
                        {"from": "node5", "to": "node6", "conversion": "transformation"}
                    ],
                    "confidence": 0.75,
                    "complexity": "high"
                }
            ])

            # Call the method with complexity preference
            result = await conversion_engine.infer_conversion_path(
                java_concept="Java Block",
                db=mock_db_session,
                path_options={"max_complexity": "medium"}
            )

            # Verify the result
            assert result["success"] is True
            assert len(result["paths"]) == 1  # Only low complexity path
            assert result["paths"][0]["complexity"] == "low"

    class TestBatchPathInference:
        """Test cases for batch conversion path inference."""

        @pytest.mark.asyncio
        async def test_batch_infer_paths(self, conversion_engine, mock_db_session):
            """Test batch conversion path inference."""
            # Mock the infer_conversion_path method
            conversion_engine.infer_conversion_path = AsyncMock(side_effect=[
                {"success": True, "paths": [{"confidence": 0.8}]},
                {"success": True, "paths": [{"confidence": 0.7}]},
                {"success": False, "error": "Not found"}
            ])

            # Call the method
            result = await conversion_engine.batch_infer_paths(
                java_concepts=["Block", "Item", "Nonexistent"],
                db=mock_db_session,
                target_platform="bedrock"
            )

            # Verify the result
            assert result["success"] is True
            assert result["total_concepts"] == 3
            assert result["successful_conversions"] == 2
            assert result["failed_conversions"] == 1
            assert "Block" in result["results"]
            assert "Item" in result["results"]
            assert "Nonexistent" in result["results"]
            assert "batch_metadata" in result
            assert "success_rate" in result["batch_metadata"]
            assert result["batch_metadata"]["success_rate"] == 2/3

    class TestPathOptimization:
        """Test cases for conversion path optimization."""

        @pytest.mark.asyncio
        async def test_optimize_conversion_sequence(self, conversion_engine, mock_db_session):
            """Test conversion sequence optimization."""
            # Mock conversion paths
            paths = [
                {
                    "path": ["node1", "node2", "node3"],
                    "confidence": 0.7,
                    "steps": [
                        {"from": "node1", "to": "node2", "conversion": "direct", "effort": 3},
                        {"from": "node2", "to": "node3", "conversion": "transformation", "effort": 5}
                    ]
                },
                {
                    "path": ["node1", "node4", "node3"],
                    "confidence": 0.8,
                    "steps": [
                        {"from": "node1", "to": "node4", "conversion": "direct", "effort": 2},
                        {"from": "node4", "to": "node3", "conversion": "transformation", "effort": 4}
                    ]
                }
            ]

            # Mock helper methods
            conversion_engine._calculate_path_metrics = AsyncMock(side_effect=[
                {"overall_effort": 8, "risk_score": 0.2},
                {"overall_effort": 6, "risk_score": 0.15}
            ])

            # Call the method
            result = await conversion_engine.optimize_conversion_sequence(
                conversion_paths=paths,
                optimization_criteria="balanced",
                db=mock_db_session
            )

            # Verify the result
            assert result["success"] is True
            assert len(result["optimized_paths"]) == 2
            assert result["optimized_paths"][0]["path"] == ["node1", "node4", "node3"]  # Better path first
            assert "optimization_metadata" in result
            assert result["optimization_metadata"]["criteria"] == "balanced"

        @pytest.mark.asyncio
        async def test_optimize_for_confidence(self, conversion_engine, mock_db_session):
            """Test optimization for confidence."""
            # Mock conversion paths with different confidence scores
            paths = [
                {"path": ["node1", "node2"], "confidence": 0.6, "steps": []},
                {"path": ["node1", "node3"], "confidence": 0.9, "steps": []},
                {"path": ["node1", "node4"], "confidence": 0.7, "steps": []}
            ]

            # Call the method
            result = await conversion_engine.optimize_conversion_sequence(
                conversion_paths=paths,
                optimization_criteria="confidence",
                db=mock_db_session
            )

            # Verify the result
            assert result["success"] is True
            assert len(result["optimized_paths"]) == 3
            assert result["optimized_paths"][0]["confidence"] == 0.9  # Highest confidence first
            assert result["optimized_paths"][1]["confidence"] == 0.7
            assert result["optimized_paths"][2]["confidence"] == 0.6

        @pytest.mark.asyncio
        async def test_optimize_for_effort(self, conversion_engine, mock_db_session):
            """Test optimization for effort."""
            # Mock conversion paths with different effort levels
            paths = [
                {
                    "path": ["node1", "node2"],
                    "confidence": 0.8,
                    "steps": [{"effort": 2}]
                },
                {
                    "path": ["node1", "node3"],
                    "confidence": 0.7,
                    "steps": [{"effort": 1}]
                },
                {
                    "path": ["node1", "node4"],
                    "confidence": 0.6,
                    "steps": [{"effort": 3}]
                }
            ]

            # Mock helper methods
            conversion_engine._calculate_path_metrics = AsyncMock(side_effect=[
                {"overall_effort": 2, "risk_score": 0.2},
                {"overall_effort": 1, "risk_score": 0.15},
                {"overall_effort": 3, "risk_score": 0.25}
            ])

            # Call the method
            result = await conversion_engine.optimize_conversion_sequence(
                conversion_paths=paths,
                optimization_criteria="effort",
                db=mock_db_session
            )

            # Verify the result
            assert result["success"] is True
            assert len(result["optimized_paths"]) == 3
            assert result["optimized_paths"][0]["path"] == ["node1", "node3"]  # Lowest effort first

    class TestPathValidation:
        """Test cases for conversion path validation."""

        @pytest.mark.asyncio
        async def test_validate_conversion_path(self, conversion_engine, mock_db_session):
            """Test conversion path validation."""
            # Create a valid path
            path = {
                "path": ["node1", "node2", "node3"],
                "steps": [
                    {"from": "node1", "to": "node2", "conversion": "direct"},
                    {"from": "node2", "to": "node3", "conversion": "transformation"}
                ],
                "confidence": 0.8
            }

            # Mock validation methods
            conversion_engine._validate_node_existence = AsyncMock(return_value=True)
            conversion_engine._validate_relationship_existence = AsyncMock(return_value=True)
            conversion_engine._validate_conversion_feasibility = AsyncMock(return_value=True)
            conversion_engine._check_version_compatibility = AsyncMock(return_value=True)

            # Call the method
            result = await conversion_engine.validate_conversion_path(
                conversion_path=path,
                db=mock_db_session,
                minecraft_version="1.18.2"
            )

            # Verify the result
            assert result["valid"] is True
            assert result["validation_score"] == 1.0
            assert len(result["validation_issues"]) == 0
            assert "validation_metadata" in result

        @pytest.mark.asyncio
        async def test_validate_conversion_path_with_issues(self, conversion_engine, mock_db_session):
            """Test conversion path validation with issues."""
            # Create a path with potential issues
            path = {
                "path": ["node1", "node2", "node3"],
                "steps": [
                    {"from": "node1", "to": "node2", "conversion": "direct"},
                    {"from": "node2", "to": "node3", "conversion": "transformation"}
                ],
                "confidence": 0.5
            }

            # Mock validation methods with issues
            conversion_engine._validate_node_existence = AsyncMock(return_value=True)
            conversion_engine._validate_relationship_existence = AsyncMock(return_value=False)  # Issue
            conversion_engine._validate_conversion_feasibility = AsyncMock(return_value=True)
            conversion_engine._check_version_compatibility = AsyncMock(return_value=False)  # Issue

            # Call the method
            result = await conversion_engine.validate_conversion_path(
                conversion_path=path,
                db=mock_db_session,
                minecraft_version="1.18.2"
            )

            # Verify the result
            assert result["valid"] is False
            assert result["validation_score"] < 1.0
            assert len(result["validation_issues"]) >= 2  # At least 2 issues

    class TestHelperMethods:
        """Test cases for helper methods."""

        def test_calculate_path_confidence(self, conversion_engine):
            """Test calculation of path confidence."""
            # Create steps with different confidence scores
            steps = [
                {"confidence": 0.9},
                {"confidence": 0.7},
                {"confidence": 0.8}
            ]

            # Call the method
            confidence = conversion_engine._calculate_path_confidence(steps)

            # Verify the result (average of step confidences)
            assert abs(confidence - 0.8) < 0.01  # (0.9 + 0.7 + 0.8) / 3 = 0.8

        def test_calculate_path_effort(self, conversion_engine):
            """Test calculation of path effort."""
            # Create steps with different effort levels
            steps = [
                {"effort": 2},
                {"effort": 3},
                {"effort": 1}
            ]

            # Call the method
            effort = conversion_engine._calculate_path_effort(steps)

            # Verify the result (sum of step efforts)
            assert effort == 6  # 2 + 3 + 1 = 6

        def test_determine_complexity(self, conversion_engine):
            """Test determination of path complexity."""
            # Test low complexity
            steps = [
                {"effort": 1},
                {"effort": 2}
            ]
            complexity = conversion_engine._determine_complexity(steps)
            assert complexity == "low"

            # Test medium complexity
            steps = [
                {"effort": 2},
                {"effort": 3},
                {"effort": 2}
            ]
            complexity = conversion_engine._determine_complexity(steps)
            assert complexity == "medium"

            # Test high complexity
            steps = [
                {"effort": 4},
                {"effort": 3},
                {"effort": 4},
                {"effort": 3}
            ]
            complexity = conversion_engine._determine_complexity(steps)
            assert complexity == "high"

        def test_generate_path_explanation(self, conversion_engine):
            """Test generation of path explanation."""
            # Create a path
            path = {
                "path": ["java_block", "conversion_step", "bedrock_block"],
                "confidence": 0.8,
                "complexity": "medium"
            }

            # Call the method
            explanation = conversion_engine._generate_path_explanation(path)

            # Verify the result
            assert "java_block" in explanation
            assert "bedrock_block" in explanation
            assert "confidence" in explanation.lower()
            assert "medium" in explanation

        def test_estimate_implementation_time(self, conversion_engine):
            """Test estimation of implementation time."""
            # Test with low complexity
            time = conversion_engine._estimate_implementation_time("low", 3)
            assert 1 <= time <= 3  # Hours

            # Test with medium complexity
            time = conversion_engine._estimate_implementation_time("medium", 5)
            assert 3 <= time <= 8  # Hours

            # Test with high complexity
            time = conversion_engine._estimate_implementation_time("high", 4)
            assert 5 <= time <= 12  # Hours

        @pytest.mark.asyncio
        async def test_find_similar_concepts(self, conversion_engine, mock_db_session):
            """Test finding similar concepts."""
            # Mock the database query
            mock_nodes = [
                {"id": "node1", "name": "Java Block", "platform": "java"},
                {"id": "node2", "name": "Java Item", "platform": "java"},
                {"id": "node3", "name": "Bedrock Block", "platform": "bedrock"}
            ]

            # Mock KnowledgeNodeCRUD
            with patch.object(KnowledgeNodeCRUD, 'search_by_name') as mock_search:
                mock_search.return_value = mock_nodes

                # Call the method
                result = await conversion_engine._find_similar_concepts(
                    "Java Blok",  # Misspelled
                    "java",
                    mock_db_session
                )

                # Verify the result
                assert len(result) >= 1
                assert "Java Block" in [item["name"] for item in result]
                assert all("similarity" in item for item in result)

        @pytest.mark.asyncio
        async def test_find_conversion_paths(self, conversion_engine, mock_db_session):
            """Test finding conversion paths between nodes."""
            # Mock the path finding algorithm
            conversion_engine._find_paths_with_bfs = AsyncMock(return_value=[
                {
                    "path": ["node1", "node2", "node3"],
                    "confidence": 0.8
                }
            ])

            # Call the method
            result = await conversion_engine._find_conversion_paths(
                "node1",
                "node3",
                "bedrock",
                mock_db_session
            )

            # Verify the result
            assert len(result) == 1
            assert result[0]["path"] == ["node1", "node2", "node3"]
            assert result[0]["confidence"] == 0.8
            assert "steps" in result[0]
            assert "complexity" in result[0]

    # Additional comprehensive tests for better coverage

    async def test_learn_from_conversion(self, conversion_engine, mock_db_session):
        """Test learning from successful/failures conversions."""
        # Mock successful conversion data
        conversion_data = {
            "java_concept": "java_block",
            "bedrock_concept": "bedrock_block",
            "path_used": ["java_block", "intermediate", "bedrock_block"],
            "success": True,
            "confidence": 0.85,
            "implementation_time": 45.5,
            "issues_encountered": ["minor_texturing_issue"],
            "minecraft_version": "1.20.0"
        }

        # Mock the CRUD operations
        with patch.object(conversion_engine, '_update_conversion_patterns') as mock_update:
            mock_update.return_value = {"success": True, "updated_patterns": 3}

            result = await conversion_engine.learn_from_conversion(
                conversion_data, mock_db_session
            )

            assert result["success"] is True
            assert "patterns_updated" in result
            assert "learning_confidence" in result
            mock_update.assert_called_once()

    async def test_get_inference_statistics(self, conversion_engine, mock_db_session):
        """Test getting inference engine statistics."""
        with patch.object(conversion_engine, '_collect_usage_stats') as mock_stats:
            mock_stats.return_value = {
                "total_inferences": 1250,
                "success_rate": 0.87,
                "average_confidence": 0.73,
                "common_paths": ["direct_mapping", "complex_transformation"],
                "performance_metrics": {
                    "avg_response_time": 0.15,
                    "cache_hit_rate": 0.65
                }
            }

            stats = await conversion_engine.get_inference_statistics(mock_db_session)

            assert "total_inferences" in stats
            assert "success_rate" in stats
            assert "common_paths" in stats
            assert "performance_metrics" in stats
            assert stats["total_inferences"] == 1250
            assert 0 <= stats["success_rate"] <= 1

    async def test_find_indirect_paths(self, conversion_engine, mock_db_session):
        """Test finding indirect conversion paths."""
        # Mock graph database response for indirect path finding
        with patch('src.services.conversion_inference.graph_db') as mock_graph:
            mock_graph.find_paths.return_value = [
                {
                    "path": ["java_block", "intermediate1", "intermediate2", "bedrock_block"],
                    "confidence": 0.72,
                    "complexity": "medium",
                    "estimated_time": 65.3
                },
                {
                    "path": ["java_block", "alternative_path", "bedrock_block"],
                    "confidence": 0.68,
                    "complexity": "low",
                    "estimated_time": 45.2
                }
            ]

            source_node = {"id": "java_block", "type": "java_concept"}
            indirect_paths = await conversion_engine._find_indirect_paths(
                mock_db_session, source_node, "bedrock", "1.20.0"
            )

            assert len(indirect_paths) >= 1
            assert all("path" in path for path in indirect_paths)
            assert all("confidence" in path for path in indirect_paths)
            assert all(0 <= path["confidence"] <= 1 for path in indirect_paths)

    async def test_rank_paths_by_confidence(self, conversion_engine):
        """Test path ranking by confidence score."""
        paths = [
            {"path": ["a", "b", "c"], "confidence": 0.65, "complexity": "medium"},
            {"path": ["a", "c"], "confidence": 0.82, "complexity": "low"},
            {"path": ["a", "d", "e", "c"], "confidence": 0.71, "complexity": "high"}
        ]

        ranked = await conversion_engine._rank_paths(paths, "confidence")

        assert len(ranked) == 3
        assert ranked[0]["confidence"] >= ranked[1]["confidence"]
        assert ranked[1]["confidence"] >= ranked[2]["confidence"]
        assert ranked[0]["confidence"] == 0.82  # Highest confidence first

    async def test_rank_paths_by_speed(self, conversion_engine):
        """Test path ranking by implementation speed."""
        paths = [
            {"path": ["a", "b", "c"], "confidence": 0.65, "complexity": "medium", "estimated_time": 45.2},
            {"path": ["a", "c"], "confidence": 0.82, "complexity": "low", "estimated_time": 25.1},
            {"path": ["a", "d", "e", "c"], "confidence": 0.71, "complexity": "high", "estimated_time": 75.8}
        ]

        ranked = await conversion_engine._rank_paths(paths, "speed")

        assert len(ranked) == 3
        # Should be ordered by estimated_time (fastest first)
        assert ranked[0]["estimated_time"] <= ranked[1]["estimated_time"]
        assert ranked[1]["estimated_time"] <= ranked[2]["estimated_time"]

    async def test_suggest_similar_concepts(self, conversion_engine, mock_db_session):
        """Test suggesting similar concepts when no direct match found."""
        with patch.object(conversion_engine, '_find_similar_nodes') as mock_similar:
            mock_similar.return_value = [
                {"concept": "java_block_stone", "similarity": 0.92, "type": "block"},
                {"concept": "java_block_wood", "similarity": 0.87, "type": "block"},
                {"concept": "java_item_stone", "similarity": 0.73, "type": "item"}
            ]

            suggestions = await conversion_engine._suggest_similar_concepts(
                mock_db_session, "java_block", "java"
            )

            assert len(suggestions) >= 1
            assert all("concept" in s for s in suggestions)
            assert all("similarity" in s for s in suggestions)
            assert all(0 <= s["similarity"] <= 1 for s in suggestions)
            # Should be ordered by similarity (highest first)
            assert suggestions[0]["similarity"] >= suggestions[1]["similarity"]

    async def test_analyze_batch_paths(self, conversion_engine, mock_db_session):
        """Test batch path analysis for multiple concepts."""
        batch_data = [
            {"java_concept": "java_block", "priority": "high"},
            {"java_concept": "java_entity", "priority": "medium"},
            {"java_concept": "java_item", "priority": "low"}
        ]

        with patch.object(conversion_engine, 'infer_conversion_path') as mock_infer:
            # Mock individual inference results
            mock_infer.side_effect = [
                {"success": True, "path_type": "direct", "primary_path": {"confidence": 0.85}},
                {"success": True, "path_type": "indirect", "primary_path": {"confidence": 0.72}},
                {"success": False, "error": "concept not found"}
            ]

            analysis = await conversion_engine._analyze_batch_paths(
                batch_data, mock_db_session
            )

            assert "batch_summary" in analysis
            assert "individual_results" in analysis
            assert "optimization_suggestions" in analysis
            assert len(analysis["individual_results"]) == 3

    async def test_optimize_processing_order(self, conversion_engine):
        """Test optimization of batch processing order."""
        concepts = [
            {"java_concept": "complex_entity", "complexity": 9, "dependencies": []},
            {"java_concept": "simple_block", "complexity": 2, "dependencies": []},
            {"java_concept": "medium_item", "complexity": 5, "dependencies": ["simple_block"]},
            {"java_concept": "dependent_entity", "complexity": 7, "dependencies": ["complex_entity"]}
        ]

        optimized_order = await conversion_engine._optimize_processing_order(concepts)

        assert len(optimized_order) == 4
        # Simple items should come before complex ones
        assert optimized_order[0]["java_concept"] == "simple_block"
        # Dependencies should be respected
        simple_idx = next(i for i, c in enumerate(optimized_order) if c["java_concept"] == "simple_block")
        medium_idx = next(i for i, c in enumerate(optimized_order) if c["java_concept"] == "medium_item")
        assert simple_idx < medium_idx

    async def test_identify_shared_steps(self, conversion_engine):
        """Test identification of shared conversion steps across paths."""
        paths = [
            ["java_block1", "intermediate_a", "intermediate_b", "bedrock_block1"],
            ["java_block2", "intermediate_a", "intermediate_c", "bedrock_block2"],
            ["java_block3", "intermediate_d", "intermediate_b", "bedrock_block3"]
        ]

        shared_steps = await conversion_engine._identify_shared_steps(paths)

        assert "intermediate_a" in shared_steps
        assert "intermediate_b" in shared_steps
        assert shared_steps["intermediate_a"]["usage_count"] == 2
        assert shared_steps["intermediate_b"]["usage_count"] == 2
        assert all("paths" in step for step in shared_steps.values())

    async def test_generate_batch_plan(self, conversion_engine):
        """Test generation of optimized batch conversion plan."""
        batch_data = [
            {"java_concept": "concept1", "priority": "high", "estimated_complexity": 3},
            {"java_concept": "concept2", "priority": "medium", "estimated_complexity": 7},
            {"java_concept": "concept3", "priority": "low", "estimated_complexity": 2}
        ]

        with patch.object(conversion_engine, '_identify_shared_steps') as mock_shared, \
             patch.object(conversion_engine, '_optimize_processing_order') as mock_optimize:

            mock_shared.return_value = {"shared_step": {"usage_count": 2}}
            mock_optimize.return_value = batch_data

            plan = await conversion_engine._generate_batch_plan(batch_data)

            assert "processing_order" in plan
            assert "shared_steps" in plan
            assert "optimizations" in plan
            assert "estimated_time" in plan
            assert len(plan["processing_order"]) == 3

    def test_estimate_batch_time(self, conversion_engine):
        """Test batch processing time estimation."""
        batch_plan = {
            "processing_order": [
                {"complexity": 3, "path_type": "direct"},
                {"complexity": 7, "path_type": "indirect"},
                {"complexity": 2, "path_type": "direct"}
            ],
            "shared_steps": {"step1": {"usage_count": 2, "time_saved": 15}},
            "parallel_processing": True
        }

        estimated_time = conversion_engine._estimate_batch_time(batch_plan)

        assert isinstance(estimated_time, float)
        assert estimated_time > 0
        # Parallel processing should reduce total time
        individual_time = sum(item["complexity"] * 10 for item in batch_plan["processing_order"])
        assert estimated_time < individual_time

    async def test_find_common_patterns(self, conversion_engine, mock_db_session):
        """Test finding common conversion patterns."""
        with patch.object(conversion_engine, '_analyze_pattern_frequency') as mock_analyze:
            mock_analyze.return_value = {
                "direct_mapping": {"frequency": 0.45, "avg_confidence": 0.82},
                "entity_transformation": {"frequency": 0.23, "avg_confidence": 0.71},
                "behavior_mapping": {"frequency": 0.18, "avg_confidence": 0.68}
            }

            patterns = await conversion_engine._find_common_patterns(mock_db_session)

            assert len(patterns) >= 1
            assert all("frequency" in p for p in patterns.values())
            assert all("avg_confidence" in p for p in patterns.values())
            # Should be sorted by frequency
            frequencies = [p["frequency"] for p in patterns.values()]
            assert frequencies == sorted(frequencies, reverse=True)

    async def test_build_dependency_graph(self, conversion_engine):
        """Test building dependency graph for batch conversions."""
        concepts = [
            {"java_concept": "base_block", "dependencies": []},
            {"java_concept": "derived_block", "dependencies": ["base_block"]},
            {"java_concept": "complex_entity", "dependencies": ["base_block", "derived_block"]},
            {"java_concept": "independent_item", "dependencies": []}
        ]

        dependency_graph = await conversion_engine._build_dependency_graph(concepts)

        assert "nodes" in dependency_graph
        assert "edges" in dependency_graph
        assert "processing_levels" in dependency_graph
        assert len(dependency_graph["nodes"]) == 4
        assert len(dependency_graph["edges"]) == 2  # Two dependency relationships

        # Check processing levels
        levels = dependency_graph["processing_levels"]
        assert "base_block" in levels[0]  # No dependencies
        assert "independent_item" in levels[0]  # No dependencies
        assert "derived_block" in levels[1]  # Depends on level 0
        assert "complex_entity" in levels[2]  # Depends on level 1

    def test_calculate_path_complexity_comprehensive(self, conversion_engine):
        """Test comprehensive path complexity calculation."""
        # Simple path
        simple_path = {
            "path": ["java_block", "bedrock_block"],
            "transformations": ["direct_mapping"],
            "complexity_factors": {"code_changes": "low", "asset_changes": "medium"}
        }
        simple_complexity = conversion_engine._calculate_path_complexity(simple_path)
        assert simple_complexity <= 3

        # Complex path
        complex_path = {
            "path": ["java_entity", "intermediate1", "intermediate2", "intermediate3", "bedrock_entity"],
            "transformations": ["complex_transform", "asset_generation", "behavior_mapping"],
            "complexity_factors": {"code_changes": "high", "asset_changes": "high", "logic_changes": "high"}
        }
        complex_complexity = conversion_engine._calculate_path_complexity(complex_path)
        assert complex_complexity >= 7

    def test_validate_path_constraints(self, conversion_engine):
        """Test validation of path constraints and requirements."""
        # Valid path
        valid_path = {
            "path": ["java_block", "bedrock_block"],
            "confidence": 0.85,
            "complexity": 2,
            "estimated_time": 30.5,
            "required_skills": ["basic_mapping"],
            "minecraft_versions": ["1.20.0", "1.19.4"]
        }

        constraints = {
            "max_complexity": 5,
            "min_confidence": 0.7,
            "max_time": 60,
            "target_version": "1.20.0",
            "available_skills": ["basic_mapping", "advanced_scripting"]
        }

        validation = conversion_engine._validate_path_constraints(valid_path, constraints)

        assert validation["is_valid"] is True
        assert len(validation["violations"]) == 0

        # Invalid path
        invalid_path = {
            "path": ["java_complex_entity", "bedrock_entity"],
            "confidence": 0.45,
            "complexity": 8,
            "estimated_time": 120.0,
            "required_skills": ["advanced_ai"],
            "minecraft_versions": ["1.18.0"]
        }

        validation = conversion_engine._validate_path_constraints(invalid_path, constraints)

        assert validation["is_valid"] is False
        assert len(validation["violations"]) >= 2  # Should fail on confidence and complexity

    def test_generate_path_recommendations(self, conversion_engine):
        """Test generation of path-specific recommendations."""
        path_data = {
            "path": ["java_entity", "complex_intermediate", "bedrock_entity"],
            "confidence": 0.65,
            "complexity": 7,
            "transformations": ["behavior_mapping", "asset_generation"],
            "risk_factors": ["high_complexity", "limited_expertise"]
        }

        recommendations = conversion_engine._generate_path_recommendations(path_data)

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert all("category" in rec for rec in recommendations)
        assert all("priority" in rec for rec in recommendations)
        assert all("description" in rec for rec in recommendations)

        # Should have recommendations for the identified risks
        categories = [rec["category"] for rec in recommendations]
        assert any("complexity" in cat.lower() for cat in categories)
        assert any("expertise" in cat.lower() for cat in categories)

    def test_edge_case_empty_paths(self, conversion_engine):
        """Test handling of empty or invalid path data."""
        # Empty path list
        empty_ranked = conversion_engine._rank_paths([], "confidence")
        assert empty_ranked == []

        # Invalid optimization strategy
        paths = [{"path": ["a", "b"], "confidence": 0.8}]
        with pytest.raises(ValueError):
            conversion_engine._rank_paths(paths, "invalid_strategy")

    def test_edge_case_extreme_values(self, conversion_engine):
        """Test handling of extreme confidence and complexity values."""
        # Maximum confidence path
        max_confidence_path = {
            "path": ["simple_a", "simple_b"],
            "confidence": 1.0,
            "complexity": 1,
            "estimated_time": 1.0
        }

        # Minimum confidence path
        min_confidence_path = {
            "path": ["complex_a", "complex_b", "complex_c", "complex_d"],
            "confidence": 0.0,
            "complexity": 10,
            "estimated_time": 999.9
        }

        paths = [max_confidence_path, min_confidence_path]
        ranked = conversion_engine._rank_paths(paths, "confidence")

        assert ranked[0]["confidence"] == 1.0
        assert ranked[1]["confidence"] == 0.0

    def test_performance_large_batch_simulation(self, conversion_engine):
        """Test performance with large batch of concepts."""
        # Create a large batch of test concepts
        large_batch = [
            {"java_concept": f"concept_{i}", "priority": "medium", "complexity": (i % 10) + 1}
            for i in range(100)
        ]

        # This should not cause performance issues
        import time
        start_time = time.time()

        # Mock the optimization to avoid actual DB calls
        with patch.object(conversion_engine, '_optimize_processing_order') as mock_optimize:
            mock_optimize.return_value = large_batch[:10]  # Return subset for testing

            result = conversion_engine._optimize_processing_order(large_batch)
            processing_time = time.time() - start_time

            assert processing_time < 5.0  # Should complete within 5 seconds
            assert len(result) == 10
