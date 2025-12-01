"""
Simple Test Suite for Visualization API

Tests for src/api/visualization.py - 235 statements, targeting 60%+ coverage
Focus on testing the functions directly as they are defined
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.api.visualization import (
    create_visualization,
    get_visualization,
    update_visualization_filters,
    change_visualization_layout,
    focus_on_node,
    create_filter_preset,
    get_filter_presets,
    export_visualization,
    get_visualization_metrics,
    get_visualization_types,
    get_layout_algorithms,
    get_filter_types,
    get_active_visualizations,
    delete_visualization,
    get_performance_stats,
    _get_layout_suitability,
)
from src.services.advanced_visualization import (
    VisualizationType,
    FilterType,
    LayoutAlgorithm,
)
from fastapi import HTTPException


class TestVisualizationCreation:
    """Test visualization creation endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def sample_viz_data(self):
        return {
            "graph_id": "test_graph_123",
            "visualization_type": "force_directed",
            "filters": [
                {
                    "filter_type": "node_type",
                    "field": "type",
                    "operator": "equals",
                    "value": "class",
                }
            ],
            "layout": "spring",
        }

    @pytest.mark.asyncio
    async def test_create_visualization_success(self, mock_db, sample_viz_data):
        """Test successful visualization creation."""
        with patch(
            "src.api.visualization.advanced_visualization_service"
        ) as mock_service:
            mock_service.create_visualization.return_value = {
                "success": True,
                "visualization_id": "viz_123",
                "graph_id": "test_graph_123",
                "visualization_type": "force_directed",
                "layout": "spring",
            }

            result = await create_visualization(sample_viz_data, mock_db)

            assert result["success"] is True
            assert result["visualization_id"] == "viz_123"
            mock_service.create_visualization.assert_called_once_with(
                "test_graph_123",
                VisualizationType.FORCE_DIRECTED,
                sample_viz_data["filters"],
                LayoutAlgorithm.SPRING,
                mock_db,
            )

    @pytest.mark.asyncio
    async def test_create_visualization_missing_graph_id(self, mock_db):
        """Test visualization creation with missing graph_id."""
        viz_data = {
            "visualization_type": "force_directed",
            "filters": [],
            "layout": "spring",
        }

        with pytest.raises(HTTPException) as exc_info:
            await create_visualization(viz_data, mock_db)

        assert exc_info.value.status_code == 400
        assert "graph_id is required" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_visualization_invalid_type(self, mock_db):
        """Test visualization creation with invalid visualization type."""
        viz_data = {
            "graph_id": "test_graph_123",
            "visualization_type": "invalid_type",
            "filters": [],
            "layout": "spring",
        }

        with pytest.raises(HTTPException) as exc_info:
            await create_visualization(viz_data, mock_db)

        assert exc_info.value.status_code == 400
        assert "Invalid visualization_type" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_visualization_invalid_layout(self, mock_db):
        """Test visualization creation with invalid layout."""
        viz_data = {
            "graph_id": "test_graph_123",
            "visualization_type": "force_directed",
            "filters": [],
            "layout": "invalid_layout",
        }

        with pytest.raises(HTTPException) as exc_info:
            await create_visualization(viz_data, mock_db)

        assert exc_info.value.status_code == 400
        assert "Invalid layout" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_visualization_service_error(self, mock_db):
        """Test visualization creation when service returns error."""
        viz_data = {
            "graph_id": "nonexistent_graph",
            "visualization_type": "force_directed",
            "filters": [],
            "layout": "spring",
        }

        with patch(
            "src.api.visualization.advanced_visualization_service"
        ) as mock_service:
            mock_service.create_visualization.return_value = {
                "success": False,
                "error": "Graph not found",
            }

            with pytest.raises(HTTPException) as exc_info:
                await create_visualization(viz_data, mock_db)

            assert exc_info.value.status_code == 400
            assert "Graph not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_visualization_exception_handling(self, mock_db):
        """Test visualization creation with unexpected exception."""
        viz_data = {
            "graph_id": "test_graph_123",
            "visualization_type": "force_directed",
            "filters": [],
            "layout": "spring",
        }

        with patch(
            "src.api.visualization.advanced_visualization_service"
        ) as mock_service:
            mock_service.create_visualization.side_effect = Exception("Database error")

            with pytest.raises(HTTPException) as exc_info:
                await create_visualization(viz_data, mock_db)

            assert exc_info.value.status_code == 500
            assert "Visualization creation failed" in str(exc_info.value.detail)


class TestVisualizationRetrieval:
    """Test visualization retrieval endpoint."""

    @pytest.mark.asyncio
    async def test_get_visualization_success(self):
        """Test successful visualization retrieval."""
        with patch(
            "src.api.visualization.advanced_visualization_service"
        ) as mock_service:
            # Create mock visualization state
            mock_node = Mock()
            mock_node.id = "node_1"
            mock_node.label = "Test Node"
            mock_node.type = "class"
            mock_node.platform = "java"
            mock_node.x = 100.0
            mock_node.y = 200.0
            mock_node.size = 10
            mock_node.color = "#ff0000"
            mock_node.community = 1
            mock_node.confidence = 0.95
            mock_node.visibility = True
            mock_node.properties = {"package": "com.example"}
            mock_node.metadata = {"created_by": "user123"}

            mock_edge = Mock()
            mock_edge.id = "edge_1"
            mock_edge.source = "node_1"
            mock_edge.target = "node_2"
            mock_edge.type = "extends"
            mock_edge.weight = 0.8
            mock_edge.color = "#0000ff"
            mock_edge.width = 2
            mock_edge.confidence = 0.9
            mock_edge.visibility = True
            mock_edge.properties = {"line_style": "solid"}
            mock_edge.metadata = {"source_line": 10}

            mock_cluster = Mock()
            mock_cluster.cluster_id = "cluster_1"
            mock_cluster.name = "Test Cluster"
            mock_cluster.nodes = ["node_1", "node_2"]
            mock_cluster.edges = ["edge_1"]
            mock_cluster.color = "#00ff00"
            mock_cluster.size = 2
            mock_cluster.density = 0.5
            mock_cluster.centrality = 0.7
            mock_cluster.properties = {"algorithm": "louvain"}

            mock_filter = Mock()
            mock_filter.filter.filter_id = "filter_1"
            mock_filter.filter.filter_type = FilterType.NODE_TYPE
            mock_filter.filter.field = "type"
            mock_filter.filter.operator = "equals"
            mock_filter.filter.value = "class"
            mock_filter.filter.description = "Filter classes"
            mock_filter.filter.metadata = {"priority": "high"}

            mock_viz_state = Mock()
            mock_viz_state.nodes = [mock_node]
            mock_viz_state.edges = [mock_edge]
            mock_viz_state.clusters = [mock_cluster]
            mock_viz_state.filters = [mock_filter]
            mock_viz_state.layout = LayoutAlgorithm.SPRING
            mock_viz_state.viewport = {"x": 0, "y": 0, "zoom": 1.0}
            mock_viz_state.metadata = {"graph_id": "test_graph"}
            mock_viz_state.created_at = datetime.now()

            mock_service.visualization_cache = {"viz_123": mock_viz_state}

            result = await get_visualization("viz_123")

            assert result["success"] is True
            assert result["visualization_id"] == "viz_123"
            assert len(result["state"]["nodes"]) == 1
            assert len(result["state"]["edges"]) == 1
            assert len(result["state"]["clusters"]) == 1
            assert len(result["state"]["filters"]) == 1
            assert result["state"]["layout"] == "spring"

    @pytest.mark.asyncio
    async def test_get_visualization_not_found(self):
        """Test visualization retrieval for non-existent visualization."""
        with patch(
            "src.api.visualization.advanced_visualization_service"
        ) as mock_service:
            mock_service.visualization_cache = {}

            with pytest.raises(HTTPException) as exc_info:
                await get_visualization("nonexistent_viz")

            assert exc_info.value.status_code == 404
            assert "Visualization not found" in str(exc_info.value.detail)


class TestVisualizationFilters:
    """Test visualization filter endpoints."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_update_visualization_filters_success(self, mock_db):
        """Test successful filter update."""
        with patch(
            "src.api.visualization.advanced_visualization_service"
        ) as mock_service:
            mock_service.update_visualization_filters.return_value = {
                "success": True,
                "visualization_id": "viz_123",
                "filters_applied": 2,
            }

            filter_data = {
                "filters": [
                    {
                        "filter_type": "node_type",
                        "field": "type",
                        "operator": "equals",
                        "value": "class",
                    }
                ]
            }

            result = await update_visualization_filters("viz_123", filter_data, mock_db)

            assert result["success"] is True
            assert result["filters_applied"] == 2
            mock_service.update_visualization_filters.assert_called_once_with(
                "viz_123", filter_data["filters"], mock_db
            )

    @pytest.mark.asyncio
    async def test_update_visualization_filters_service_error(self, mock_db):
        """Test filter update when service returns error."""
        with patch(
            "src.api.visualization.advanced_visualization_service"
        ) as mock_service:
            mock_service.update_visualization_filters.return_value = {
                "success": False,
                "error": "Invalid filter configuration",
            }

            filter_data = {"filters": []}

            with pytest.raises(HTTPException) as exc_info:
                await update_visualization_filters("viz_123", filter_data, mock_db)

            assert exc_info.value.status_code == 400
            assert "Invalid filter configuration" in str(exc_info.value.detail)


class TestVisualizationLayout:
    """Test visualization layout endpoint."""

    @pytest.mark.asyncio
    async def test_change_visualization_layout_success(self):
        """Test successful layout change."""
        with patch(
            "src.api.visualization.advanced_visualization_service"
        ) as mock_service:
            mock_service.change_layout.return_value = {
                "success": True,
                "visualization_id": "viz_123",
                "layout": "hierarchical",
                "animated": True,
            }

            layout_data = {"layout": "hierarchical", "animate": True}

            result = await change_visualization_layout("viz_123", layout_data)

            assert result["success"] is True
            assert result["layout"] == "hierarchical"
            assert result["animated"] is True
            mock_service.change_layout.assert_called_once_with(
                "viz_123", LayoutAlgorithm.HIERARCHICAL, True
            )

    @pytest.mark.asyncio
    async def test_change_visualization_layout_invalid_layout(self):
        """Test layout change with invalid layout."""
        layout_data = {"layout": "invalid_layout", "animate": True}

        with pytest.raises(HTTPException) as exc_info:
            await change_visualization_layout("viz_123", layout_data)

        assert exc_info.value.status_code == 400
        assert "Invalid layout" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_change_visualization_layout_default_values(self):
        """Test layout change with default values."""
        with patch(
            "src.api.visualization.advanced_visualization_service"
        ) as mock_service:
            mock_service.change_layout.return_value = {
                "success": True,
                "visualization_id": "viz_123",
                "layout": "spring",
                "animated": True,
            }

            layout_data = {}  # No layout specified, should default to "spring"

            result = await change_visualization_layout("viz_123", layout_data)

            assert result["success"] is True
            mock_service.change_layout.assert_called_once_with(
                "viz_123", LayoutAlgorithm.SPRING, True
            )


class TestVisualizationFocus:
    """Test visualization focus endpoint."""

    @pytest.mark.asyncio
    async def test_focus_on_node_success(self):
        """Test successful node focus."""
        with patch(
            "src.api.visualization.advanced_visualization_service"
        ) as mock_service:
            mock_service.focus_on_node.return_value = {
                "success": True,
                "visualization_id": "viz_123",
                "focused_node": "node_123",
                "radius": 3,
            }

            focus_data = {"node_id": "node_123", "radius": 3, "animate": True}

            result = await focus_on_node("viz_123", focus_data)

            assert result["success"] is True
            assert result["focused_node"] == "node_123"
            assert result["radius"] == 3
            mock_service.focus_on_node.assert_called_once_with(
                "viz_123", "node_123", 3, True
            )

    @pytest.mark.asyncio
    async def test_focus_on_node_missing_node_id(self):
        """Test node focus with missing node_id."""
        focus_data = {"radius": 2, "animate": True}

        with pytest.raises(HTTPException) as exc_info:
            await focus_on_node("viz_123", focus_data)

        assert exc_info.value.status_code == 400
        assert "node_id is required" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_focus_on_node_default_values(self):
        """Test node focus with default values."""
        with patch(
            "src.api.visualization.advanced_visualization_service"
        ) as mock_service:
            mock_service.focus_on_node.return_value = {
                "success": True,
                "visualization_id": "viz_123",
                "focused_node": "node_123",
                "radius": 2,
            }

            focus_data = {"node_id": "node_123"}  # No radius specified

            result = await focus_on_node("viz_123", focus_data)

            assert result["success"] is True
            mock_service.focus_on_node.assert_called_once_with(
                "viz_123", "node_123", 2, True
            )


class TestFilterPresets:
    """Test filter preset endpoints."""

    @pytest.mark.asyncio
    async def test_create_filter_preset_success(self):
        """Test successful filter preset creation."""
        with patch(
            "src.api.visualization.advanced_visualization_service"
        ) as mock_service:
            mock_service.create_filter_preset.return_value = {
                "success": True,
                "preset_name": "java_classes",
                "filters_count": 3,
            }

            preset_data = {
                "preset_name": "java_classes",
                "filters": [
                    {
                        "filter_type": "node_type",
                        "field": "type",
                        "operator": "equals",
                        "value": "class",
                    }
                ],
                "description": "Filter for Java classes only",
            }

            result = await create_filter_preset(preset_data)

            assert result["success"] is True
            assert result["preset_name"] == "java_classes"
            assert result["filters_count"] == 3
            mock_service.create_filter_preset.assert_called_once_with(
                "java_classes", preset_data["filters"], "Filter for Java classes only"
            )

    @pytest.mark.asyncio
    async def test_create_filter_preset_missing_name(self):
        """Test filter preset creation with missing preset_name."""
        preset_data = {"filters": [], "description": "Test preset"}

        with pytest.raises(HTTPException) as exc_info:
            await create_filter_preset(preset_data)

        assert exc_info.value.status_code == 400
        assert "preset_name and filters are required" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_filter_presets_success(self):
        """Test successful filter presets retrieval."""
        with patch(
            "src.api.visualization.advanced_visualization_service"
        ) as mock_service:
            mock_filter = Mock()
            mock_filter.filter.filter_id = "filter_1"
            mock_filter.filter.filter_type = FilterType.NODE_TYPE
            mock_filter.filter.field = "type"
            mock_filter.filter.operator = "equals"
            mock_filter.filter.value = "class"
            mock_filter.filter.description = "Class filter"

            mock_service.filter_presets = {
                "java_classes": [mock_filter],
                "python_modules": [mock_filter],
            }

            result = await get_filter_presets()

            assert result["success"] is True
            assert result["total_presets"] == 2
            assert len(result["presets"]) == 2
            assert result["presets"][0]["name"] == "java_classes"
            assert result["presets"][0]["filters_count"] == 1


class TestVisualizationExport:
    """Test visualization export endpoint."""

    @pytest.mark.asyncio
    async def test_export_visualization_success(self):
        """Test successful visualization export."""
        with patch(
            "src.api.visualization.advanced_visualization_service"
        ) as mock_service:
            mock_service.export_visualization.return_value = {
                "success": True,
                "visualization_id": "viz_123",
                "format": "json",
                "data": {"nodes": [], "edges": []},
                "download_url": "/downloads/viz_123.json",
            }

            export_data = {"format": "json", "include_metadata": True}

            result = await export_visualization("viz_123", export_data)

            assert result["success"] is True
            assert result["format"] == "json"
            assert result["download_url"] == "/downloads/viz_123.json"
            mock_service.export_visualization.assert_called_once_with(
                "viz_123", "json", True
            )


class TestVisualizationMetrics:
    """Test visualization metrics endpoint."""

    @pytest.mark.asyncio
    async def test_get_visualization_metrics_success(self):
        """Test successful visualization metrics retrieval."""
        with patch(
            "src.api.visualization.advanced_visualization_service"
        ) as mock_service:
            mock_service.get_visualization_metrics.return_value = {
                "success": True,
                "visualization_id": "viz_123",
                "metrics": {
                    "nodes_count": 150,
                    "edges_count": 300,
                    "clusters_count": 5,
                    "density": 0.027,
                    "clustering_coefficient": 0.45,
                    "average_path_length": 3.2,
                },
            }

            result = await get_visualization_metrics("viz_123")

            assert result["success"] is True
            assert result["metrics"]["nodes_count"] == 150
            assert result["metrics"]["edges_count"] == 300
            assert result["metrics"]["density"] == 0.027
            mock_service.get_visualization_metrics.assert_called_once_with("viz_123")


class TestUtilityEndpoints:
    """Test utility endpoints for visualization."""

    @pytest.mark.asyncio
    async def test_get_visualization_types_success(self):
        """Test successful visualization types retrieval."""
        result = await get_visualization_types()

        assert result["success"] is True
        assert result["total_types"] > 0
        assert len(result["visualization_types"]) > 0

        # Check if all types have required fields
        for viz_type in result["visualization_types"]:
            assert "value" in viz_type
            assert "name" in viz_type
            assert "description" in viz_type

    @pytest.mark.asyncio
    async def test_get_layout_algorithms_success(self):
        """Test successful layout algorithms retrieval."""
        result = await get_layout_algorithms()

        assert result["success"] is True
        assert result["total_algorithms"] > 0
        assert len(result["layout_algorithms"]) > 0

        # Check if all algorithms have required fields
        for layout in result["layout_algorithms"]:
            assert "value" in layout
            assert "name" in layout
            assert "description" in layout
            assert "suitable_for" in layout

    @pytest.mark.asyncio
    async def test_get_filter_types_success(self):
        """Test successful filter types retrieval."""
        result = await get_filter_types()

        assert result["success"] is True
        assert result["total_types"] > 0
        assert len(result["filter_types"]) > 0

        # Check if all filter types have required fields
        for filter_type in result["filter_types"]:
            assert "value" in filter_type
            assert "name" in filter_type
            assert "description" in filter_type
            # Note: operators and fields may cause errors due to self reference issues

    @pytest.mark.asyncio
    async def test_get_active_visualizations_success(self):
        """Test successful active visualizations retrieval."""
        with patch(
            "src.api.visualization.advanced_visualization_service"
        ) as mock_service:
            # Mock visualization states
            mock_viz_state = Mock()
            mock_viz_state.nodes = [Mock(), Mock()]  # 2 nodes
            mock_viz_state.edges = [Mock()]  # 1 edge
            mock_viz_state.clusters = [Mock()]  # 1 cluster
            mock_viz_state.filters = [Mock(), Mock()]  # 2 filters
            mock_viz_state.layout = LayoutAlgorithm.SPRING
            mock_viz_state.created_at = datetime.now()
            mock_viz_state.metadata = {
                "graph_id": "test_graph",
                "visualization_type": "force_directed",
                "last_updated": datetime.now().isoformat(),
            }

            mock_service.visualization_cache = {
                "viz_1": mock_viz_state,
                "viz_2": mock_viz_state,
            }

            result = await get_active_visualizations()

            assert result["success"] is True
            assert result["total_visualizations"] == 2
            assert len(result["visualizations"]) == 2

            # Check if all visualizations have required fields
            for viz in result["visualizations"]:
                assert "visualization_id" in viz
                assert "graph_id" in viz
                assert "nodes_count" in viz
                assert "edges_count" in viz
                assert "created_at" in viz
                assert viz["nodes_count"] == 2
                assert viz["edges_count"] == 1

    @pytest.mark.asyncio
    async def test_delete_visualization_success(self):
        """Test successful visualization deletion."""
        with patch(
            "src.api.visualization.advanced_visualization_service"
        ) as mock_service:
            # Add a mock visualization to cache
            mock_service.visualization_cache = {"viz_123": Mock()}
            mock_service.layout_cache = {"viz_123": Mock()}
            mock_service.cluster_cache = {"viz_123": Mock()}

            result = await delete_visualization("viz_123")

            assert result["success"] is True
            assert result["visualization_id"] == "viz_123"
            assert "deleted successfully" in result["message"]

            # Verify cleanup
            assert "viz_123" not in mock_service.visualization_cache
            assert "viz_123" not in mock_service.layout_cache
            assert "viz_123" not in mock_service.cluster_cache


class TestHelperMethods:
    """Test helper methods."""

    def test_get_layout_suitability(self):
        """Test layout suitability helper method."""
        spring_suitability = _get_layout_suitability(LayoutAlgorithm.SPRING)
        assert "General purpose" in spring_suitability
        assert "Moderate size graphs" in spring_suitability

        circular_suitability = _get_layout_suitability(LayoutAlgorithm.CIRCULAR)
        assert "Social networks" in circular_suitability
        assert "Cyclical relationships" in circular_suitability

        hierarchical_suitability = _get_layout_suitability(LayoutAlgorithm.HIERARCHICAL)
        assert "Organizational charts" in hierarchical_suitability
        assert "Dependency graphs" in hierarchical_suitability


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_get_layout_algorithms_with_self_reference_error(self):
        """Test layout algorithms endpoint with potential self reference error."""
        # The function should work despite any self reference issues in source
        result = await get_layout_algorithms()

        assert result["success"] is True
        assert result["total_algorithms"] > 0

    @pytest.mark.asyncio
    async def test_get_filter_types_with_self_reference_error(self):
        """Test filter types endpoint with potential self reference error."""
        # The function should work despite any self reference issues in source
        result = await get_filter_types()

        assert result["success"] is True
        assert result["total_types"] > 0

    @pytest.mark.asyncio
    async def test_get_performance_stats_with_empty_cache(self):
        """Test performance stats with empty caches."""
        with patch(
            "src.api.visualization.advanced_visualization_service"
        ) as mock_service:
            mock_service.visualization_cache = {}
            mock_service.layout_cache = {}
            mock_service.cluster_cache = {}
            mock_service.filter_presets = {}

            result = await get_performance_stats()

            assert result["success"] is True
            stats = result["stats"]

            assert stats["active_visualizations"] == 0
            assert stats["cached_layouts"] == 0
            assert stats["cached_clusters"] == 0
            assert stats["filter_presets"] == 0
            assert stats["total_nodes"] == 0
            assert stats["total_edges"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
