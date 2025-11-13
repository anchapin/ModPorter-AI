"""
Comprehensive Test Suite for Visualization API

Tests for src/api/visualization.py - 234 statements, targeting 70%+ coverage
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import HTTPException
import json
from datetime import datetime

from src.api.visualization import router, advanced_visualization_service
from src.services.advanced_visualization import (
    VisualizationType, FilterType, LayoutAlgorithm,
    VisualizationState, VisualizationNode, VisualizationEdge, GraphCluster
)


class TestVisualizationCreation:
    """Test visualization creation endpoints."""
    
    @pytest.fixture
    def client(self):
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router, prefix="/api")
        return TestClient(app)
    
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
                    "value": "class"
                }
            ],
            "layout": "spring"
        }
    
    @pytest.mark.asyncio
    async def test_create_visualization_success(self, mock_db):
        """Test successful visualization creation."""
        # Mock the service response
        with patch.object(advanced_visualization_service, 'create_visualization') as mock_create:
            mock_create.return_value = {
                "success": True,
                "visualization_id": "viz_123",
                "graph_id": "test_graph_123",
                "visualization_type": "force_directed",
                "layout": "spring"
            }
            
            # Create a mock request
            viz_data = {
                "graph_id": "test_graph_123",
                "visualization_type": "force_directed",
                "filters": [],
                "layout": "spring"
            }
            
            result = await router.create_visualization(viz_data, mock_db)
            
            assert result["success"] is True
            assert result["visualization_id"] == "viz_123"
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_visualization_missing_graph_id(self, mock_db):
        """Test visualization creation with missing graph_id."""
        viz_data = {
            "visualization_type": "force_directed",
            "filters": [],
            "layout": "spring"
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await router.create_visualization(viz_data, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "graph_id is required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_create_visualization_invalid_type(self, mock_db):
        """Test visualization creation with invalid visualization type."""
        viz_data = {
            "graph_id": "test_graph_123",
            "visualization_type": "invalid_type",
            "filters": [],
            "layout": "spring"
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await router.create_visualization(viz_data, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "Invalid visualization_type" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_create_visualization_invalid_layout(self, mock_db):
        """Test visualization creation with invalid layout."""
        viz_data = {
            "graph_id": "test_graph_123",
            "visualization_type": "force_directed",
            "filters": [],
            "layout": "invalid_layout"
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await router.create_visualization(viz_data, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "Invalid layout" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_create_visualization_service_error(self, mock_db):
        """Test visualization creation when service returns error."""
        with patch.object(advanced_visualization_service, 'create_visualization') as mock_create:
            mock_create.return_value = {
                "success": False,
                "error": "Graph not found"
            }
            
            viz_data = {
                "graph_id": "nonexistent_graph",
                "visualization_type": "force_directed",
                "filters": [],
                "layout": "spring"
            }
            
            with pytest.raises(HTTPException) as exc_info:
                await router.create_visualization(viz_data, mock_db)
            
            assert exc_info.value.status_code == 400
            assert "Graph not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_create_visualization_exception_handling(self, mock_db):
        """Test visualization creation with unexpected exception."""
        with patch.object(advanced_visualization_service, 'create_visualization') as mock_create:
            mock_create.side_effect = Exception("Database error")
            
            viz_data = {
                "graph_id": "test_graph_123",
                "visualization_type": "force_directed",
                "filters": [],
                "layout": "spring"
            }
            
            with pytest.raises(HTTPException) as exc_info:
                await router.create_visualization(viz_data, mock_db)
            
            assert exc_info.value.status_code == 500
            assert "Visualization creation failed" in str(exc_info.value.detail)


class TestVisualizationRetrieval:
    """Test visualization retrieval endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_visualization_success(self):
        """Test successful visualization retrieval."""
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
        
        # Add to cache
        advanced_visualization_service.visualization_cache["viz_123"] = mock_viz_state
        
        result = await router.get_visualization("viz_123")
        
        assert result["success"] is True
        assert result["visualization_id"] == "viz_123"
        assert len(result["state"]["nodes"]) == 1
        assert len(result["state"]["edges"]) == 1
        assert len(result["state"]["clusters"]) == 1
        assert len(result["state"]["filters"]) == 1
        assert result["state"]["layout"] == "spring"
        
        # Clean up
        del advanced_visualization_service.visualization_cache["viz_123"]
    
    @pytest.mark.asyncio
    async def test_get_visualization_not_found(self):
        """Test visualization retrieval for non-existent visualization."""
        with pytest.raises(HTTPException) as exc_info:
            await router.get_visualization("nonexistent_viz")
        
        assert exc_info.value.status_code == 404
        assert "Visualization not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_visualization_exception_handling(self):
        """Test visualization retrieval with unexpected exception."""
        # Add corrupted data to cache
        advanced_visualization_service.visualization_cache["corrupted_viz"] = None
        
        with pytest.raises(HTTPException) as exc_info:
            await router.get_visualization("corrupted_viz")
        
        assert exc_info.value.status_code == 500
        assert "Failed to get visualization" in str(exc_info.value.detail)
        
        # Clean up
        del advanced_visualization_service.visualization_cache["corrupted_viz"]


class TestVisualizationFilters:
    """Test visualization filter endpoints."""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_update_visualization_filters_success(self, mock_db):
        """Test successful filter update."""
        with patch.object(advanced_visualization_service, 'update_visualization_filters') as mock_update:
            mock_update.return_value = {
                "success": True,
                "visualization_id": "viz_123",
                "filters_applied": 2
            }
            
            filter_data = {
                "filters": [
                    {
                        "filter_type": "node_type",
                        "field": "type",
                        "operator": "equals",
                        "value": "class"
                    }
                ]
            }
            
            result = await router.update_visualization_filters("viz_123", filter_data, mock_db)
            
            assert result["success"] is True
            assert result["filters_applied"] == 2
            mock_update.assert_called_once_with("viz_123", filter_data["filters"], mock_db)
    
    @pytest.mark.asyncio
    async def test_update_visualization_filters_service_error(self, mock_db):
        """Test filter update when service returns error."""
        with patch.object(advanced_visualization_service, 'update_visualization_filters') as mock_update:
            mock_update.return_value = {
                "success": False,
                "error": "Invalid filter configuration"
            }
            
            filter_data = {"filters": []}
            
            with pytest.raises(HTTPException) as exc_info:
                await router.update_visualization_filters("viz_123", filter_data, mock_db)
            
            assert exc_info.value.status_code == 400
            assert "Invalid filter configuration" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_update_visualization_filters_exception(self, mock_db):
        """Test filter update with unexpected exception."""
        with patch.object(advanced_visualization_service, 'update_visualization_filters') as mock_update:
            mock_update.side_effect = Exception("Database connection error")
            
            filter_data = {"filters": []}
            
            with pytest.raises(HTTPException) as exc_info:
                await router.update_visualization_filters("viz_123", filter_data, mock_db)
            
            assert exc_info.value.status_code == 500
            assert "Filter update failed" in str(exc_info.value.detail)


class TestVisualizationLayout:
    """Test visualization layout endpoints."""
    
    @pytest.mark.asyncio
    async def test_change_visualization_layout_success(self):
        """Test successful layout change."""
        with patch.object(advanced_visualization_service, 'change_layout') as mock_change:
            mock_change.return_value = {
                "success": True,
                "visualization_id": "viz_123",
                "layout": "hierarchical",
                "animated": True
            }
            
            layout_data = {
                "layout": "hierarchical",
                "animate": True
            }
            
            result = await router.change_visualization_layout("viz_123", layout_data)
            
            assert result["success"] is True
            assert result["layout"] == "hierarchical"
            assert result["animated"] is True
            mock_change.assert_called_once_with("viz_123", LayoutAlgorithm.HIERARCHICAL, True)
    
    @pytest.mark.asyncio
    async def test_change_visualization_layout_invalid_layout(self):
        """Test layout change with invalid layout."""
        layout_data = {
            "layout": "invalid_layout",
            "animate": True
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await router.change_visualization_layout("viz_123", layout_data)
        
        assert exc_info.value.status_code == 400
        assert "Invalid layout" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_change_visualization_layout_default_values(self):
        """Test layout change with default values."""
        with patch.object(advanced_visualization_service, 'change_layout') as mock_change:
            mock_change.return_value = {
                "success": True,
                "visualization_id": "viz_123",
                "layout": "spring",
                "animated": True
            }
            
            layout_data = {}  # No layout specified, should default to "spring"
            
            result = await router.change_visualization_layout("viz_123", layout_data)
            
            assert result["success"] is True
            mock_change.assert_called_once_with("viz_123", LayoutAlgorithm.SPRING, True)
    
    @pytest.mark.asyncio
    async def test_change_visualization_layout_service_error(self):
        """Test layout change when service returns error."""
        with patch.object(advanced_visualization_service, 'change_layout') as mock_change:
            mock_change.return_value = {
                "success": False,
                "error": "Visualization not found"
            }
            
            layout_data = {"layout": "circular"}
            
            with pytest.raises(HTTPException) as exc_info:
                await router.change_visualization_layout("nonexistent_viz", layout_data)
            
            assert exc_info.value.status_code == 400
            assert "Visualization not found" in str(exc_info.value.detail)


class TestVisualizationFocus:
    """Test visualization focus endpoints."""
    
    @pytest.mark.asyncio
    async def test_focus_on_node_success(self):
        """Test successful node focus."""
        with patch.object(advanced_visualization_service, 'focus_on_node') as mock_focus:
            mock_focus.return_value = {
                "success": True,
                "visualization_id": "viz_123",
                "focused_node": "node_123",
                "radius": 3
            }
            
            focus_data = {
                "node_id": "node_123",
                "radius": 3,
                "animate": True
            }
            
            result = await router.focus_on_node("viz_123", focus_data)
            
            assert result["success"] is True
            assert result["focused_node"] == "node_123"
            assert result["radius"] == 3
            mock_focus.assert_called_once_with("viz_123", "node_123", 3, True)
    
    @pytest.mark.asyncio
    async def test_focus_on_node_missing_node_id(self):
        """Test node focus with missing node_id."""
        focus_data = {
            "radius": 2,
            "animate": True
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await router.focus_on_node("viz_123", focus_data)
        
        assert exc_info.value.status_code == 400
        assert "node_id is required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_focus_on_node_default_values(self):
        """Test node focus with default values."""
        with patch.object(advanced_visualization_service, 'focus_on_node') as mock_focus:
            mock_focus.return_value = {
                "success": True,
                "visualization_id": "viz_123",
                "focused_node": "node_123",
                "radius": 2
            }
            
            focus_data = {"node_id": "node_123"}  # No radius specified
            
            result = await router.focus_on_node("viz_123", focus_data)
            
            assert result["success"] is True
            mock_focus.assert_called_once_with("viz_123", "node_123", 2, True)
    
    @pytest.mark.asyncio
    async def test_focus_on_node_service_error(self):
        """Test node focus when service returns error."""
        with patch.object(advanced_visualization_service, 'focus_on_node') as mock_focus:
            mock_focus.return_value = {
                "success": False,
                "error": "Node not found in visualization"
            }
            
            focus_data = {"node_id": "nonexistent_node"}
            
            with pytest.raises(HTTPException) as exc_info:
                await router.focus_on_node("viz_123", focus_data)
            
            assert exc_info.value.status_code == 400
            assert "Node not found in visualization" in str(exc_info.value.detail)


class TestFilterPresets:
    """Test filter preset endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_filter_preset_success(self):
        """Test successful filter preset creation."""
        with patch.object(advanced_visualization_service, 'create_filter_preset') as mock_create:
            mock_create.return_value = {
                "success": True,
                "preset_name": "java_classes",
                "filters_count": 3
            }
            
            preset_data = {
                "preset_name": "java_classes",
                "filters": [
                    {
                        "filter_type": "node_type",
                        "field": "type",
                        "operator": "equals",
                        "value": "class"
                    }
                ],
                "description": "Filter for Java classes only"
            }
            
            result = await router.create_filter_preset(preset_data)
            
            assert result["success"] is True
            assert result["preset_name"] == "java_classes"
            assert result["filters_count"] == 3
            mock_create.assert_called_once_with("java_classes", preset_data["filters"], "Filter for Java classes only")
    
    @pytest.mark.asyncio
    async def test_create_filter_preset_missing_name(self):
        """Test filter preset creation with missing preset_name."""
        preset_data = {
            "filters": [],
            "description": "Test preset"
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await router.create_filter_preset(preset_data)
        
        assert exc_info.value.status_code == 400
        assert "preset_name and filters are required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_create_filter_preset_missing_filters(self):
        """Test filter preset creation with missing filters."""
        preset_data = {
            "preset_name": "test_preset",
            "description": "Test preset"
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await router.create_filter_preset(preset_data)
        
        assert exc_info.value.status_code == 400
        assert "preset_name and filters are required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_filter_presets_success(self):
        """Test successful filter presets retrieval."""
        # Mock filter presets in service
        mock_filter = Mock()
        mock_filter.filter.filter_id = "filter_1"
        mock_filter.filter.filter_type = FilterType.NODE_TYPE
        mock_filter.filter.field = "type"
        mock_filter.filter.operator = "equals"
        mock_filter.filter.value = "class"
        mock_filter.filter.description = "Class filter"
        
        advanced_visualization_service.filter_presets = {
            "java_classes": [mock_filter],
            "python_modules": [mock_filter]
        }
        
        result = await router.get_filter_presets()
        
        assert result["success"] is True
        assert result["total_presets"] == 2
        assert len(result["presets"]) == 2
        assert result["presets"][0]["name"] == "java_classes"
        assert result["presets"][0]["filters_count"] == 1
        
        # Clean up
        advanced_visualization_service.filter_presets.clear()
    
    @pytest.mark.asyncio
    async def test_get_filter_presets_empty(self):
        """Test filter presets retrieval when no presets exist."""
        advanced_visualization_service.filter_presets.clear()
        
        result = await router.get_filter_presets()
        
        assert result["success"] is True
        assert result["total_presets"] == 0
        assert len(result["presets"]) == 0
    
    @pytest.mark.asyncio
    async def test_get_filter_preset_success(self):
        """Test successful specific filter preset retrieval."""
        mock_filter = Mock()
        mock_filter.filter.filter_id = "filter_1"
        mock_filter.filter.filter_type = FilterType.NODE_TYPE
        mock_filter.filter.field = "type"
        mock_filter.filter.operator = "equals"
        mock_filter.filter.value = "class"
        mock_filter.filter.description = "Class filter"
        mock_filter.filter.metadata = {"priority": "high"}
        
        advanced_visualization_service.filter_presets = {
            "java_classes": [mock_filter]
        }
        
        result = await router.get_filter_preset("java_classes")
        
        assert result["success"] is True
        assert result["preset_name"] == "java_classes"
        assert len(result["filters"]) == 1
        assert result["filters"][0]["filter_type"] == "node_type"
        assert result["filters"][0]["metadata"]["priority"] == "high"
        
        # Clean up
        advanced_visualization_service.filter_presets.clear()
    
    @pytest.mark.asyncio
    async def test_get_filter_preset_not_found(self):
        """Test filter preset retrieval for non-existent preset."""
        advanced_visualization_service.filter_presets.clear()
        
        with pytest.raises(HTTPException) as exc_info:
            await router.get_filter_preset("nonexistent_preset")
        
        assert exc_info.value.status_code == 404
        assert "Filter preset not found" in str(exc_info.value.detail)


class TestVisualizationExport:
    """Test visualization export endpoints."""
    
    @pytest.mark.asyncio
    async def test_export_visualization_success(self):
        """Test successful visualization export."""
        with patch.object(advanced_visualization_service, 'export_visualization') as mock_export:
            mock_export.return_value = {
                "success": True,
                "visualization_id": "viz_123",
                "format": "json",
                "data": {"nodes": [], "edges": []},
                "download_url": "/downloads/viz_123.json"
            }
            
            export_data = {
                "format": "json",
                "include_metadata": True
            }
            
            result = await router.export_visualization("viz_123", export_data)
            
            assert result["success"] is True
            assert result["format"] == "json"
            assert result["download_url"] == "/downloads/viz_123.json"
            mock_export.assert_called_once_with("viz_123", "json", True)
    
    @pytest.mark.asyncio
    async def test_export_visualization_default_values(self):
        """Test visualization export with default values."""
        with patch.object(advanced_visualization_service, 'export_visualization') as mock_export:
            mock_export.return_value = {
                "success": True,
                "visualization_id": "viz_123",
                "format": "json",
                "data": {}
            }
            
            export_data = {}  # No format specified
            
            result = await router.export_visualization("viz_123", export_data)
            
            assert result["success"] is True
            assert result["format"] == "json"
            mock_export.assert_called_once_with("viz_123", "json", True)
    
    @pytest.mark.asyncio
    async def test_export_visualization_service_error(self):
        """Test visualization export when service returns error."""
        with patch.object(advanced_visualization_service, 'export_visualization') as mock_export:
            mock_export.return_value = {
                "success": False,
                "error": "Unsupported export format"
            }
            
            export_data = {"format": "unsupported"}
            
            with pytest.raises(HTTPException) as exc_info:
                await router.export_visualization("viz_123", export_data)
            
            assert exc_info.value.status_code == 400
            assert "Unsupported export format" in str(exc_info.value.detail)


class TestVisualizationMetrics:
    """Test visualization metrics endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_visualization_metrics_success(self):
        """Test successful visualization metrics retrieval."""
        with patch.object(advanced_visualization_service, 'get_visualization_metrics') as mock_metrics:
            mock_metrics.return_value = {
                "success": True,
                "visualization_id": "viz_123",
                "metrics": {
                    "nodes_count": 150,
                    "edges_count": 300,
                    "clusters_count": 5,
                    "density": 0.027,
                    "clustering_coefficient": 0.45,
                    "average_path_length": 3.2
                }
            }
            
            result = await router.get_visualization_metrics("viz_123")
            
            assert result["success"] is True
            assert result["metrics"]["nodes_count"] == 150
            assert result["metrics"]["edges_count"] == 300
            assert result["metrics"]["density"] == 0.027
            mock_metrics.assert_called_once_with("viz_123")
    
    @pytest.mark.asyncio
    async def test_get_visualization_metrics_service_error(self):
        """Test visualization metrics when service returns error."""
        with patch.object(advanced_visualization_service, 'get_visualization_metrics') as mock_metrics:
            mock_metrics.return_value = {
                "success": False,
                "error": "Visualization not found"
            }
            
            with pytest.raises(HTTPException) as exc_info:
                await router.get_visualization_metrics("nonexistent_viz")
            
            assert exc_info.value.status_code == 400
            assert "Visualization not found" in str(exc_info.value.detail)


class TestUtilityEndpoints:
    """Test utility endpoints for visualization."""
    
    @pytest.mark.asyncio
    async def test_get_visualization_types_success(self):
        """Test successful visualization types retrieval."""
        result = await router.get_visualization_types()
        
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
        result = await router.get_layout_algorithms()
        
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
        result = await router.get_filter_types()
        
        assert result["success"] is True
        assert result["total_types"] > 0
        assert len(result["filter_types"]) > 0
        
        # Check if all filter types have required fields
        for filter_type in result["filter_types"]:
            assert "value" in filter_type
            assert "name" in filter_type
            assert "description" in filter_type
            assert "operators" in filter_type
            assert "fields" in filter_type
    
    @pytest.mark.asyncio
    async def test_get_active_visualizations_success(self):
        """Test successful active visualizations retrieval."""
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
            "last_updated": datetime.now().isoformat()
        }
        
        advanced_visualization_service.visualization_cache = {
            "viz_1": mock_viz_state,
            "viz_2": mock_viz_state
        }
        
        result = await router.get_active_visualizations()
        
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
        
        # Clean up
        advanced_visualization_service.visualization_cache.clear()
    
    @pytest.mark.asyncio
    async def test_get_active_visualizations_empty(self):
        """Test active visualizations retrieval when no visualizations exist."""
        advanced_visualization_service.visualization_cache.clear()
        
        result = await router.get_active_visualizations()
        
        assert result["success"] is True
        assert result["total_visualizations"] == 0
        assert len(result["visualizations"]) == 0
    
    @pytest.mark.asyncio
    async def test_delete_visualization_success(self):
        """Test successful visualization deletion."""
        # Add a mock visualization to cache
        advanced_visualization_service.visualization_cache["viz_123"] = Mock()
        advanced_visualization_service.layout_cache["viz_123"] = Mock()
        advanced_visualization_service.cluster_cache["viz_123"] = Mock()
        
        result = await router.delete_visualization("viz_123")
        
        assert result["success"] is True
        assert result["visualization_id"] == "viz_123"
        assert "deleted successfully" in result["message"]
        
        # Verify cleanup
        assert "viz_123" not in advanced_visualization_service.visualization_cache
        assert "viz_123" not in advanced_visualization_service.layout_cache
        assert "viz_123" not in advanced_visualization_service.cluster_cache
    
    @pytest.mark.asyncio
    async def test_delete_visualization_not_found(self):
        """Test visualization deletion for non-existent visualization."""
        with pytest.raises(HTTPException) as exc_info:
            await router.delete_visualization("nonexistent_viz")
        
        assert exc_info.value.status_code == 404
        assert "Visualization not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_performance_stats_success(self):
        """Test successful performance stats retrieval."""
        # Mock visualization states
        mock_viz_state1 = Mock()
        mock_viz_state1.nodes = [Mock(), Mock(), Mock()]  # 3 nodes
        mock_viz_state1.edges = [Mock(), Mock()]  # 2 edges
        
        mock_viz_state2 = Mock()
        mock_viz_state2.nodes = [Mock(), Mock()]  # 2 nodes
        mock_viz_state2.edges = [Mock()]  # 1 edge
        
        advanced_visualization_service.visualization_cache = {
            "viz_1": mock_viz_state1,
            "viz_2": mock_viz_state2
        }
        advanced_visualization_service.layout_cache = {"viz_1": Mock()}
        advanced_visualization_service.cluster_cache = {"viz_1": Mock()}
        advanced_visualization_service.filter_presets = {"preset1": Mock(), "preset2": Mock()}
        
        result = await router.get_performance_stats()
        
        assert result["success"] is True
        stats = result["stats"]
        
        assert stats["active_visualizations"] == 2
        assert stats["cached_layouts"] == 1
        assert stats["cached_clusters"] == 1
        assert stats["filter_presets"] == 2
        assert stats["total_nodes"] == 5  # 3 + 2
        assert stats["total_edges"] == 3  # 2 + 1
        assert stats["average_nodes_per_visualization"] == 2.5
        assert stats["average_edges_per_visualization"] == 1.5
        
        # Clean up
        advanced_visualization_service.visualization_cache.clear()
        advanced_visualization_service.layout_cache.clear()
        advanced_visualization_service.cluster_cache.clear()
        advanced_visualization_service.filter_presets.clear()


class TestHelperMethods:
    """Test helper methods."""
    
    def test_get_layout_suitability(self):
        """Test layout suitability helper method."""
        from src.api.visualization import _get_layout_suitability
        
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
        """Test layout algorithms endpoint with self reference error."""
        # This tests the bug where 'self' is used in a non-method context
        with patch('src.api.visualization.LayoutAlgorithm') as mock_layout:
            mock_layout.SPRING.value = 'spring'
            
            # The actual function should work despite the self reference in the source
            result = await router.get_layout_algorithms()
            
            assert result["success"] is True
            assert result["total_algorithms"] > 0
    
    @pytest.mark.asyncio
    async def test_get_filter_types_with_self_reference_error(self):
        """Test filter types endpoint with self reference error."""
        # This tests the bug where 'self' is used in a non-method context
        with patch('src.api.visualization.FilterType') as mock_filter_type:
            mock_filter_type.NODE_TYPE.value = 'node_type'
            
            # The actual function should work despite the self reference in the source
            result = await router.get_filter_types()
            
            assert result["success"] is True
            assert result["total_types"] > 0
    
    @pytest.mark.asyncio
    async def test_get_performance_stats_with_empty_cache(self):
        """Test performance stats with empty caches."""
        advanced_visualization_service.visualization_cache.clear()
        advanced_visualization_service.layout_cache.clear()
        advanced_visualization_service.cluster_cache.clear()
        advanced_visualization_service.filter_presets.clear()
        
        result = await router.get_performance_stats()
        
        assert result["success"] is True
        stats = result["stats"]
        
        assert stats["active_visualizations"] == 0
        assert stats["cached_layouts"] == 0
        assert stats["cached_clusters"] == 0
        assert stats["filter_presets"] == 0
        assert stats["total_nodes"] == 0
        assert stats["total_edges"] == 0
        assert stats["average_nodes_per_visualization"] == 0
        assert stats["average_edges_per_visualization"] == 0


class TestConcurrentOperations:
    """Test concurrent visualization operations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_visualization_creation(self):
        """Test creating multiple visualizations concurrently."""
        with patch.object(advanced_visualization_service, 'create_visualization') as mock_create:
            mock_create.return_value = {
                "success": True,
                "visualization_id": "viz_123",
                "graph_id": "test_graph"
            }
            
            viz_data = {
                "graph_id": "test_graph",
                "visualization_type": "force_directed",
                "filters": [],
                "layout": "spring"
            }
            
            mock_db = AsyncMock()
            
            # Create multiple visualizations concurrently
            tasks = [
                router.create_visualization(viz_data, mock_db)
                for _ in range(5)
            ]
            
            results = await asyncio.gather(*tasks)
            
            assert all(result["success"] is True for result in results)
            assert mock_create.call_count == 5
    
    @pytest.mark.asyncio
    async def test_concurrent_filter_updates(self):
        """Test updating filters on multiple visualizations concurrently."""
        with patch.object(advanced_visualization_service, 'update_visualization_filters') as mock_update:
            mock_update.return_value = {
                "success": True,
                "visualization_id": "viz_123",
                "filters_applied": 1
            }
            
            filter_data = {"filters": []}
            mock_db = AsyncMock()
            
            # Update filters on multiple visualizations concurrently
            tasks = [
                router.update_visualization_filters(f"viz_{i}", filter_data, mock_db)
                for i in range(3)
            ]
            
            results = await asyncio.gather(*tasks)
            
            assert all(result["success"] is True for result in results)
            assert mock_update.call_count == 3


# Integration Tests
class TestVisualizationAPIIntegration:
    """Integration tests for visualization API endpoints."""
    
    @pytest.mark.asyncio
    async def test_complete_visualization_workflow(self):
        """Test complete visualization workflow: create -> filter -> layout -> export."""
        mock_db = AsyncMock()
        
        with patch.object(advanced_visualization_service, 'create_visualization') as mock_create, \
             patch.object(advanced_visualization_service, 'update_visualization_filters') as mock_update, \
             patch.object(advanced_visualization_service, 'change_layout') as mock_layout, \
             patch.object(advanced_visualization_service, 'export_visualization') as mock_export:
            
            # Setup mocks
            mock_create.return_value = {
                "success": True,
                "visualization_id": "viz_workflow",
                "graph_id": "test_graph"
            }
            
            mock_update.return_value = {
                "success": True,
                "visualization_id": "viz_workflow",
                "filters_applied": 2
            }
            
            mock_layout.return_value = {
                "success": True,
                "visualization_id": "viz_workflow",
                "layout": "circular"
            }
            
            mock_export.return_value = {
                "success": True,
                "visualization_id": "viz_workflow",
                "format": "json",
                "download_url": "/downloads/viz_workflow.json"
            }
            
            # Step 1: Create visualization
            viz_data = {
                "graph_id": "test_graph",
                "visualization_type": "force_directed",
                "filters": [],
                "layout": "spring"
            }
            
            create_result = await router.create_visualization(viz_data, mock_db)
            assert create_result["success"] is True
            viz_id = create_result["visualization_id"]
            
            # Step 2: Update filters
            filter_data = {
                "filters": [
                    {
                        "filter_type": "node_type",
                        "field": "type",
                        "operator": "equals",
                        "value": "class"
                    }
                ]
            }
            
            filter_result = await router.update_visualization_filters(viz_id, filter_data, mock_db)
            assert filter_result["success"] is True
            
            # Step 3: Change layout
            layout_data = {"layout": "circular", "animate": True}
            
            layout_result = await router.change_visualization_layout(viz_id, layout_data)
            assert layout_result["success"] is True
            
            # Step 4: Export visualization
            export_data = {"format": "json", "include_metadata": True}
            
            export_result = await router.export_visualization(viz_id, export_data)
            assert export_result["success"] is True
            
            # Verify all service calls were made
            mock_create.assert_called_once()
            mock_update.assert_called_once()
            mock_layout.assert_called_once()
            mock_export.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_visualization_lifecycle_management(self):
        """Test complete visualization lifecycle: create -> get -> delete."""
        mock_db = AsyncMock()
        
        with patch.object(advanced_visualization_service, 'create_visualization') as mock_create:
            mock_create.return_value = {
                "success": True,
                "visualization_id": "viz_lifecycle",
                "graph_id": "test_graph"
            }
            
            # Step 1: Create visualization
            viz_data = {
                "graph_id": "test_graph",
                "visualization_type": "force_directed",
                "filters": [],
                "layout": "spring"
            }
            
            create_result = await router.create_visualization(viz_data, mock_db)
            assert create_result["success"] is True
            viz_id = create_result["visualization_id"]
            
            # Step 2: Add to active visualizations cache for testing
            mock_viz_state = Mock()
            mock_viz_state.nodes = []
            mock_viz_state.edges = []
            mock_viz_state.clusters = []
            mock_viz_state.filters = []
            mock_viz_state.layout = LayoutAlgorithm.SPRING
            mock_viz_state.created_at = datetime.now()
            mock_viz_state.metadata = {"graph_id": "test_graph"}
            
            advanced_visualization_service.visualization_cache[viz_id] = mock_viz_state
            
            # Step 3: Get active visualizations
            active_result = await router.get_active_visualizations()
            assert active_result["success"] is True
            assert active_result["total_visualizations"] == 1
            
            # Step 4: Get specific visualization
            get_result = await router.get_visualization(viz_id)
            assert get_result["success"] is True
            assert get_result["visualization_id"] == viz_id
            
            # Step 5: Delete visualization
            delete_result = await router.delete_visualization(viz_id)
            assert delete_result["success"] is True
            
            # Step 6: Verify deletion
            active_result_after = await router.get_active_visualizations()
            assert active_result_after["success"] is True
            assert active_result_after["total_visualizations"] == 0


# Performance and Load Tests
class TestVisualizationAPIPerformance:
    """Performance tests for visualization API."""
    
    @pytest.mark.asyncio
    async def test_large_filter_preset_handling(self):
        """Test handling of large numbers of filter presets."""
        # Create many mock filter presets
        mock_filter = Mock()
        mock_filter.filter.filter_id = "filter_1"
        mock_filter.filter.filter_type = FilterType.NODE_TYPE
        mock_filter.filter.field = "type"
        mock_filter.filter.operator = "equals"
        mock_filter.filter.value = "class"
        mock_filter.filter.description = "Class filter"
        
        large_presets = {
            f"preset_{i}": [mock_filter] * 10  # 10 filters per preset
            for i in range(100)  # 100 presets
        }
        
        advanced_visualization_service.filter_presets = large_presets
        
        result = await router.get_filter_presets()
        
        assert result["success"] is True
        assert result["total_presets"] == 100
        assert len(result["presets"]) == 100
        
        # Test specific preset retrieval with large preset
        specific_result = await router.get_filter_preset("preset_50")
        assert specific_result["success"] is True
        assert len(specific_result["filters"]) == 10
        
        # Clean up
        advanced_visualization_service.filter_presets.clear()
    
    @pytest.mark.asyncio
    async def test_performance_stats_with_large_visualization_cache(self):
        """Test performance stats with large visualization cache."""
        # Create many mock visualizations
        large_cache = {}
        for i in range(50):
            mock_viz_state = Mock()
            mock_viz_state.nodes = [Mock() for _ in range(20)]  # 20 nodes each
            mock_viz_state.edges = [Mock() for _ in range(40)]  # 40 edges each
            large_cache[f"viz_{i}"] = mock_viz_state
        
        advanced_visualization_service.visualization_cache = large_cache
        advanced_visualization_service.layout_cache = {f"viz_{i}": Mock() for i in range(25)}
        advanced_visualization_service.cluster_cache = {f"viz_{i}": Mock() for i in range(25)}
        
        result = await router.get_performance_stats()
        
        assert result["success"] is True
        stats = result["stats"]
        
        assert stats["active_visualizations"] == 50
        assert stats["total_nodes"] == 1000  # 50 * 20
        assert stats["total_edges"] == 2000  # 50 * 40
        assert stats["average_nodes_per_visualization"] == 20
        assert stats["average_edges_per_visualization"] == 40
        
        # Clean up
        advanced_visualization_service.visualization_cache.clear()
        advanced_visualization_service.layout_cache.clear()
        advanced_visualization_service.cluster_cache.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
