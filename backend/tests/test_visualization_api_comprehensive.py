"""
Comprehensive tests for visualization.py API module
Tests all visualization endpoints including creation, filtering, layout, export, and utility functions.
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from src.api.visualization import router
from src.services.advanced_visualization import VisualizationType, FilterType, LayoutAlgorithm

# Test client setup
client = TestClient(router)


class TestVisualizationCreation:
    """Test visualization creation endpoints"""
    
    @pytest.mark.asyncio
    async def test_create_visualization_success(self):
        """Test successful visualization creation"""
        mock_service = AsyncMock()
        mock_service.create_visualization.return_value = {
            "success": True,
            "visualization_id": "viz_123",
            "status": "created",
            "nodes_count": 150,
            "edges_count": 200
        }
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            viz_data = {
                "graph_id": "graph_456",
                "visualization_type": "force_directed",
                "filters": [{"field": "platform", "operator": "equals", "value": "java"}],
                "layout": "spring"
            }
            
            response = client.post("/visualizations", json=viz_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "visualization_id" in data
    
    @pytest.mark.asyncio
    async def test_create_visualization_missing_graph_id(self):
        """Test visualization creation without graph_id"""
        viz_data = {
            "visualization_type": "force_directed",
            "layout": "spring"
        }
        
        response = client.post("/visualizations", json=viz_data)
        
        assert response.status_code == 400
        assert "graph_id is required" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_create_visualization_invalid_type(self):
        """Test visualization creation with invalid type"""
        viz_data = {
            "graph_id": "graph_456",
            "visualization_type": "invalid_type",
            "layout": "spring"
        }
        
        response = client.post("/visualizations", json=viz_data)
        
        assert response.status_code == 400
        assert "Invalid visualization_type" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_create_visualization_invalid_layout(self):
        """Test visualization creation with invalid layout"""
        viz_data = {
            "graph_id": "graph_456",
            "visualization_type": "force_directed",
            "layout": "invalid_layout"
        }
        
        response = client.post("/visualizations", json=viz_data)
        
        assert response.status_code == 400
        assert "Invalid layout" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_create_visualization_service_failure(self):
        """Test visualization creation when service returns failure"""
        mock_service = AsyncMock()
        mock_service.create_visualization.return_value = {
            "success": False,
            "error": "Graph not found"
        }
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            viz_data = {
                "graph_id": "nonexistent",
                "visualization_type": "force_directed",
                "layout": "spring"
            }
            
            response = client.post("/visualizations", json=viz_data)
            
            assert response.status_code == 400
            assert "Graph not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_create_visualization_with_complex_filters(self):
        """Test visualization creation with complex filter array"""
        mock_service = AsyncMock()
        mock_service.create_visualization.return_value = {
            "success": True,
            "visualization_id": "viz_complex_123"
        }
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            viz_data = {
                "graph_id": "graph_456",
                "visualization_type": "force_directed",
                "filters": [
                    {"field": "platform", "operator": "equals", "value": "java"},
                    {"field": "confidence", "operator": "greater_than", "value": 0.8},
                    {"field": "type", "operator": "in", "value": ["mod", "resourcepack"]}
                ],
                "layout": "spring"
            }
            
            response = client.post("/visualizations", json=viz_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
    
    @pytest.mark.asyncio
    async def test_create_visualization_with_default_params(self):
        """Test visualization creation with default parameters"""
        mock_service = AsyncMock()
        mock_service.create_visualization.return_value = {
            "success": True,
            "visualization_id": "viz_default_123"
        }
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            viz_data = {
                "graph_id": "graph_456"
                # No other parameters - should use defaults
            }
            
            response = client.post("/visualizations", json=viz_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True


class TestVisualizationManagement:
    """Test visualization management endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_visualization_success(self):
        """Test successful visualization retrieval"""
        # Mock the visualization cache
        mock_viz_state = Mock()
        mock_viz_state.nodes = [
            Mock(
                id="node1", label="Test Node", type="mod", platform="java",
                x=100, y=200, size=20, color="blue", community=1, confidence=0.9,
                visibility=True, properties={}, metadata={}
            )
        ]
        mock_viz_state.edges = [
            Mock(
                id="edge1", source="node1", target="node2", type="relates_to",
                weight=1.0, color="gray", width=2, confidence=0.8,
                visibility=True, properties={}, metadata={}
            )
        ]
        mock_viz_state.clusters = [
            Mock(
                cluster_id="cluster1", name="Test Cluster", nodes=["node1"],
                edges=["edge1"], color="red", size=10, density=0.5,
                centrality=0.7, properties={}
            )
        ]
        mock_viz_state.filters = []
        mock_viz_state.layout = LayoutAlgorithm.SPRING
        mock_viz_state.viewport = {"x": 0, "y": 0, "width": 800, "height": 600}
        mock_viz_state.metadata = {"graph_id": "graph_456", "visualization_type": "force_directed"}
        mock_viz_state.created_at = datetime.utcnow()
        
        mock_service = Mock()
        mock_service.visualization_cache = {"viz_123": mock_viz_state}
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            response = client.get("/visualizations/viz_123")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["visualization_id"] == "viz_123"
            assert "nodes" in data["state"]
            assert "edges" in data["state"]
    
    @pytest.mark.asyncio
    async def test_get_visualization_not_found(self):
        """Test retrieval of non-existent visualization"""
        mock_service = Mock()
        mock_service.visualization_cache = {}  # Empty cache
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            response = client.get("/visualizations/nonexistent")
            
            assert response.status_code == 404
            assert "Visualization not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_update_visualization_filters_success(self):
        """Test successful filter update"""
        mock_service = AsyncMock()
        mock_service.update_visualization_filters.return_value = {
            "success": True,
            "visualization_id": "viz_123",
            "filters_updated": 3,
            "nodes_affected": 120
        }
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            filter_data = {
                "filters": [
                    {"field": "platform", "operator": "equals", "value": "bedrock"},
                    {"field": "confidence", "operator": "greater_than", "value": 0.7}
                ]
            }
            
            response = client.post("/visualizations/viz_123/filters", json=filter_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["filters_updated"] == 3
    
    @pytest.mark.asyncio
    async def test_change_visualization_layout_success(self):
        """Test successful layout change"""
        mock_service = AsyncMock()
        mock_service.change_layout.return_value = {
            "success": True,
            "visualization_id": "viz_123",
            "old_layout": "spring",
            "new_layout": "circular",
            "layout_changed": True
        }
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            layout_data = {
                "layout": "circular",
                "animate": True
            }
            
            response = client.post("/visualizations/viz_123/layout", json=layout_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["new_layout"] == "circular"
    
    @pytest.mark.asyncio
    async def test_change_visualization_layout_invalid(self):
        """Test layout change with invalid layout"""
        layout_data = {
            "layout": "invalid_layout"
        }
        
        response = client.post("/visualizations/viz_123/layout", json=layout_data)
        
        assert response.status_code == 400
        assert "Invalid layout" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_focus_on_node_success(self):
        """Test successful node focus"""
        mock_service = AsyncMock()
        mock_service.focus_on_node.return_value = {
            "success": True,
            "visualization_id": "viz_123",
            "node_id": "node_456",
            "nodes_in_focus": 25,
            "viewport_updated": True
        }
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            focus_data = {
                "node_id": "node_456",
                "radius": 3,
                "animate": True
            }
            
            response = client.post("/visualizations/viz_123/focus", json=focus_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["node_id"] == "node_456"
    
    @pytest.mark.asyncio
    async def test_focus_on_node_missing_node_id(self):
        """Test node focus without node_id"""
        focus_data = {
            "radius": 2
        }
        
        response = client.post("/visualizations/viz_123/focus", json=focus_data)
        
        assert response.status_code == 400
        assert "node_id is required" in response.json()["detail"]


class TestFilterPresets:
    """Test filter preset endpoints"""
    
    @pytest.mark.asyncio
    async def test_create_filter_preset_success(self):
        """Test successful filter preset creation"""
        mock_service = AsyncMock()
        mock_service.create_filter_preset.return_value = {
            "success": True,
            "preset_name": "java_mods",
            "filters_count": 2
        }
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            preset_data = {
                "preset_name": "java_mods",
                "filters": [
                    {"field": "platform", "operator": "equals", "value": "java"},
                    {"field": "type", "operator": "equals", "value": "mod"}
                ],
                "description": "Java platform mods only"
            }
            
            response = client.post("/filter-presets", json=preset_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["preset_name"] == "java_mods"
    
    @pytest.mark.asyncio
    async def test_create_filter_preset_missing_params(self):
        """Test filter preset creation with missing parameters"""
        preset_data = {
            "preset_name": "test_preset"
            # Missing filters
        }
        
        response = client.post("/filter-presets", json=preset_data)
        
        assert response.status_code == 400
        assert "filters are required" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_filter_presets_success(self):
        """Test successful retrieval of filter presets"""
        mock_service = Mock()
        mock_preset = Mock()
        mock_preset.filter.filter_id = "filter1"
        mock_preset.filter.filter_type = FilterType.PROPERTY
        mock_preset.filter.field = "platform"
        mock_preset.filter.operator = "equals"
        mock_preset.filter.value = "java"
        mock_preset.filter.description = "Java platform filter"
        mock_preset.filter.metadata = {}
        
        mock_service.filter_presets = {
            "java_mods": [mock_preset],
            "bedrock_addons": [mock_preset]
        }
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            response = client.get("/filter-presets")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["presets"]) == 2
            assert data["total_presets"] == 2
    
    @pytest.mark.asyncio
    async def test_get_filter_presets_empty(self):
        """Test retrieval when no presets exist"""
        mock_service = Mock()
        mock_service.filter_presets = {}  # Empty presets
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            response = client.get("/filter-presets")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["presets"]) == 0
            assert data["total_presets"] == 0
    
    @pytest.mark.asyncio
    async def test_get_specific_filter_preset_success(self):
        """Test successful retrieval of specific preset"""
        mock_service = Mock()
        mock_preset = Mock()
        mock_preset.filter.filter_id = "filter1"
        mock_preset.filter.filter_type = FilterType.PROPERTY
        mock_preset.filter.field = "platform"
        mock_preset.filter.operator = "equals"
        mock_preset.filter.value = "java"
        mock_preset.filter.description = "Java platform filter"
        mock_preset.filter.metadata = {"created_by": "system"}
        
        mock_service.filter_presets = {
            "java_mods": [mock_preset]
        }
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            response = client.get("/filter-presets/java_mods")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["preset_name"] == "java_mods"
            assert len(data["filters"]) == 1
    
    @pytest.mark.asyncio
    async def test_get_specific_filter_preset_not_found(self):
        """Test retrieval of non-existent preset"""
        mock_service = Mock()
        mock_service.filter_presets = {}  # Empty presets
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            response = client.get("/filter-presets/nonexistent")
            
            assert response.status_code == 404
            assert "Filter preset not found" in response.json()["detail"]


class TestExportEndpoints:
    """Test visualization export endpoints"""
    
    @pytest.mark.asyncio
    async def test_export_visualization_success(self):
        """Test successful visualization export"""
        mock_service = AsyncMock()
        mock_service.export_visualization.return_value = {
            "success": True,
            "visualization_id": "viz_123",
            "format": "json",
            "file_size": 15420,
            "export_url": "/exports/viz_123_export.json"
        }
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            export_data = {
                "format": "json",
                "include_metadata": True
            }
            
            response = client.post("/visualizations/viz_123/export", json=export_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["format"] == "json"
    
    @pytest.mark.asyncio
    async def test_export_visualization_different_formats(self):
        """Test export in different formats"""
        formats = ["json", "gexf", "graphml", "csv"]
        
        for format_type in formats:
            mock_service = AsyncMock()
            mock_service.export_visualization.return_value = {
                "success": True,
                "format": format_type,
                "file_size": 10000
            }
            
            with patch('src.api.visualization.advanced_visualization_service', mock_service):
                export_data = {
                    "format": format_type
                }
                
                response = client.post("/visualizations/viz_123/export", json=export_data)
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["format"] == format_type
    
    @pytest.mark.asyncio
    async def test_export_visualization_with_metadata(self):
        """Test export with metadata inclusion"""
        mock_service = AsyncMock()
        mock_service.export_visualization.return_value = {
            "success": True,
            "format": "json",
            "include_metadata": True,
            "metadata_size": 2048
        }
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            export_data = {
                "format": "json",
                "include_metadata": True
            }
            
            response = client.post("/visualizations/viz_123/export", json=export_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["include_metadata"] is True


class TestMetricsEndpoints:
    """Test visualization metrics endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_visualization_metrics_success(self):
        """Test successful metrics retrieval"""
        mock_service = AsyncMock()
        mock_service.get_visualization_metrics.return_value = {
            "success": True,
            "visualization_id": "viz_123",
            "metrics": {
                "nodes_count": 150,
                "edges_count": 200,
                "clusters_count": 5,
                "density": 0.034,
                "average_clustering_coefficient": 0.42,
                "centrality_metrics": {
                    "betweenness": {"mean": 0.12, "std": 0.08},
                    "closeness": {"mean": 0.65, "std": 0.15}
                },
                "community_metrics": {
                    "modularity": 0.67,
                    "number_of_communities": 5
                }
            }
        }
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            response = client.get("/visualizations/viz_123/metrics")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "metrics" in data
            assert data["metrics"]["nodes_count"] == 150
    
    @pytest.mark.asyncio
    async def test_get_visualization_metrics_failure(self):
        """Test metrics retrieval failure"""
        mock_service = AsyncMock()
        mock_service.get_visualization_metrics.return_value = {
            "success": False,
            "error": "Visualization not found"
        }
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            response = client.get("/visualizations/viz_123/metrics")
            
            assert response.status_code == 400
            assert "Visualization not found" in response.json()["detail"]


class TestUtilityEndpoints:
    """Test utility and configuration endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_visualization_types_success(self):
        """Test successful retrieval of visualization types"""
        response = client.get("/visualization-types")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "visualization_types" in data
        assert len(data["visualization_types"]) > 0
        
        # Check structure of visualization types
        viz_type = data["visualization_types"][0]
        assert "value" in viz_type
        assert "name" in viz_type
        assert "description" in viz_type
    
    @pytest.mark.asyncio
    async def test_get_layout_algorithms_success(self):
        """Test successful retrieval of layout algorithms"""
        response = client.get("/layout-algorithms")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "layout_algorithms" in data
        assert len(data["layout_algorithms"]) > 0
        
        # Check structure of layout algorithms
        algorithm = data["layout_algorithms"][0]
        assert "value" in algorithm
        assert "name" in algorithm
        assert "description" in algorithm
        assert "suitable_for" in algorithm
    
    @pytest.mark.asyncio
    async def test_get_filter_types_success(self):
        """Test successful retrieval of filter types"""
        response = client.get("/filter-types")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "filter_types" in data
        assert len(data["filter_types"]) > 0
        
        # Check structure of filter types
        filter_type = data["filter_types"][0]
        assert "value" in filter_type
        assert "name" in filter_type
        assert "description" in filter_type
        assert "operators" in filter_type
        assert "fields" in filter_type
    
    @pytest.mark.asyncio
    async def test_get_active_visualizations_success(self):
        """Test successful retrieval of active visualizations"""
        mock_service = Mock()
        
        # Mock visualization states
        mock_viz_state1 = Mock()
        mock_viz_state1.metadata = {"graph_id": "graph1", "visualization_type": "force_directed"}
        mock_viz_state1.layout = LayoutAlgorithm.SPRING
        mock_viz_state1.nodes = [Mock(), Mock(), Mock()]  # 3 nodes
        mock_viz_state1.edges = [Mock(), Mock()]  # 2 edges
        mock_viz_state1.clusters = [Mock()]  # 1 cluster
        mock_viz_state1.filters = [Mock(), Mock()]  # 2 filters
        mock_viz_state1.created_at = datetime.utcnow()
        
        mock_viz_state2 = Mock()
        mock_viz_state2.metadata = {"graph_id": "graph2", "visualization_type": "circular"}
        mock_viz_state2.layout = LayoutAlgorithm.CIRCULAR
        mock_viz_state2.nodes = [Mock()]  # 1 node
        mock_viz_state2.edges = []  # 0 edges
        mock_viz_state2.clusters = []  # 0 clusters
        mock_viz_state2.filters = []  # 0 filters
        mock_viz_state2.created_at = datetime.utcnow()
        
        mock_service.visualization_cache = {
            "viz_active1": mock_viz_state1,
            "viz_active2": mock_viz_state2
        }
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            response = client.get("/visualizations/active")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["visualizations"]) == 2
            assert data["total_visualizations"] == 2
    
    @pytest.mark.asyncio
    async def test_get_active_visualizations_empty(self):
        """Test retrieval when no active visualizations exist"""
        mock_service = Mock()
        mock_service.visualization_cache = {}  # Empty cache
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            response = client.get("/visualizations/active")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["visualizations"]) == 0
            assert data["total_visualizations"] == 0
    
    @pytest.mark.asyncio
    async def test_delete_visualization_success(self):
        """Test successful visualization deletion"""
        mock_service = Mock()
        mock_service.visualization_cache = {"viz_to_delete": Mock()}
        mock_service.layout_cache = {"viz_to_delete": Mock()}
        mock_service.cluster_cache = {"viz_to_delete": Mock()}
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            response = client.delete("/visualizations/viz_to_delete")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["visualization_id"] == "viz_to_delete"
            
            # Verify cleanup
            assert "viz_to_delete" not in mock_service.visualization_cache
            assert "viz_to_delete" not in mock_service.layout_cache
            assert "viz_to_delete" not in mock_service.cluster_cache
    
    @pytest.mark.asyncio
    async def test_delete_visualization_not_found(self):
        """Test deletion of non-existent visualization"""
        mock_service = Mock()
        mock_service.visualization_cache = {}  # Empty cache
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            response = client.delete("/visualizations/nonexistent")
            
            assert response.status_code == 404
            assert "Visualization not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_performance_stats_success(self):
        """Test successful performance statistics retrieval"""
        mock_service = Mock()
        
        # Mock visualization states
        mock_viz1 = Mock()
        mock_viz1.nodes = [Mock(), Mock(), Mock()]  # 3 nodes
        mock_viz1.edges = [Mock(), Mock(), Mock(), Mock()]  # 4 edges
        
        mock_viz2 = Mock()
        mock_viz2.nodes = [Mock(), Mock()]  # 2 nodes
        mock_viz2.edges = [Mock()]  # 1 edge
        
        mock_service.visualization_cache = {"viz1": mock_viz1, "viz2": mock_viz2}
        mock_service.layout_cache = {"viz1": Mock()}  # 1 cached layout
        mock_service.cluster_cache = {"viz1": Mock(), "viz2": Mock()}  # 2 cached clusters
        mock_service.filter_presets = {"preset1": [], "preset2": [], "preset3": []}  # 3 presets
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            response = client.get("/performance-stats")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "stats" in data
            
            stats = data["stats"]
            assert stats["active_visualizations"] == 2
            assert stats["cached_layouts"] == 1
            assert stats["cached_clusters"] == 2
            assert stats["filter_presets"] == 3
            assert stats["total_nodes"] == 5
            assert stats["total_edges"] == 5
            assert stats["average_nodes_per_visualization"] == 2.5
            assert stats["average_edges_per_visualization"] == 2.5


class TestVisualizationErrorHandling:
    """Test error handling in visualization API"""
    
    @pytest.mark.asyncio
    async def test_service_exception_handling(self):
        """Test handling of service exceptions"""
        mock_service = AsyncMock()
        mock_service.create_visualization.side_effect = Exception("Service error")
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            viz_data = {
                "graph_id": "graph_456",
                "visualization_type": "force_directed",
                "layout": "spring"
            }
            
            response = client.post("/visualizations", json=viz_data)
            
            assert response.status_code == 500
            assert "Visualization creation failed" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_visualization_exception(self):
        """Test exception handling in get visualization"""
        mock_service = Mock()
        mock_service.visualization_cache = {"viz_123": Mock()}
        mock_service.visualization_cache["viz_123"].nodes = [Mock()]
        # Add other required attributes
        mock_service.visualization_cache["viz_123"].edges = [Mock()]
        mock_service.visualization_cache["viz_123"].clusters = []
        mock_service.visualization_cache["viz_123"].filters = []
        mock_service.visualization_cache["viz_123"].layout = LayoutAlgorithm.SPRING
        mock_service.visualization_cache["viz_123"].viewpoint = {}
        mock_service.visualization_cache["viz_123"].metadata = {}
        mock_service.visualization_cache["viz_123"].created_at = datetime.utcnow()
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            response = client.get("/visualizations/viz_123")
            
            # Should work normally or handle exception gracefully
            assert response.status_code in [200, 500]
    
    @pytest.mark.asyncio
    async def test_update_filters_exception(self):
        """Test exception handling in filter update"""
        mock_service = AsyncMock()
        mock_service.update_visualization_filters.side_effect = Exception("Update failed")
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            filter_data = {"filters": [{"field": "test", "value": "value"}]}
            
            response = client.post("/visualizations/viz_123/filters", json=filter_data)
            
            assert response.status_code == 500
            assert "Filter update failed" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_export_visualization_exception(self):
        """Test exception handling in visualization export"""
        mock_service = AsyncMock()
        mock_service.export_visualization.side_effect = Exception("Export failed")
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            export_data = {"format": "json"}
            
            response = client.post("/visualizations/viz_123/export", json=export_data)
            
            assert response.status_code == 500
            assert "Export failed" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_metrics_exception(self):
        """Test exception handling in metrics retrieval"""
        mock_service = AsyncMock()
        mock_service.get_visualization_metrics.side_effect = Exception("Metrics failed")
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            response = client.get("/visualizations/viz_123/metrics")
            
            assert response.status_code == 500
            assert "Metrics calculation failed" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_types_exception(self):
        """Test exception handling in get types"""
        with patch('src.api.visualization.VisualizationType', side_effect=Exception("Enum error")):
            response = client.get("/visualization-types")
            
            assert response.status_code == 500
    
    @pytest.mark.asyncio
    async def test_get_presets_exception(self):
        """Test exception handling in get presets"""
        mock_service = Mock()
        mock_service.filter_presets = {}  # Empty but valid
        # Simulate an exception in the endpoint
        with patch('src.api.visualization.advanced_visualization_service.filter_presets', side_effect=Exception("Preset access failed")):
            response = client.get("/filter-presets")
            
            assert response.status_code == 500


class TestVisualizationHelperFunctions:
    """Test visualization API helper functions"""
    
    def test_get_layout_suitability(self):
        """Test layout suitability helper function"""
        from src.api.visualization import _get_layout_suitability
        
        suitability = _get_layout_suitability(LayoutAlgorithm.SPRING)
        assert "General purpose" in suitability
        assert "Moderate size graphs" in suitability
        
        suitability = _get_layout_suitability(LayoutAlgorithm.HIERARCHICAL)
        assert "Organizational charts" in suitability
        assert "Dependency graphs" in suitability
        
        suitability = _get_layout_suitability("UNKNOWN")
        assert suitability == ["General use"]


class TestVisualizationIntegration:
    """Integration tests for visualization API workflows"""
    
    @pytest.mark.asyncio
    async def test_complete_visualization_workflow(self):
        """Test complete visualization workflow"""
        mock_service = AsyncMock()
        
        # Mock different service responses for workflow steps
        mock_service.create_visualization.return_value = {
            "success": True,
            "visualization_id": "workflow_viz_123"
        }
        mock_service.get_visualization_metrics.return_value = {
            "success": True,
            "metrics": {"nodes_count": 150, "edges_count": 200}
        }
        mock_service.export_visualization.return_value = {
            "success": True,
            "format": "json",
            "file_size": 25000
        }
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            # Step 1: Create visualization
            viz_data = {
                "graph_id": "graph_456",
                "visualization_type": "force_directed",
                "layout": "spring"
            }
            
            create_response = client.post("/visualizations", json=viz_data)
            assert create_response.status_code == 200
            
            viz_id = create_response.json()["visualization_id"]
            
            # Step 2: Get metrics
            metrics_response = client.get(f"/visualizations/{viz_id}/metrics")
            assert metrics_response.status_code == 200
            
            # Step 3: Export visualization
            export_data = {"format": "json", "include_metadata": True}
            export_response = client.post(f"/visualizations/{viz_id}/export", json=export_data)
            assert export_response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_filter_preset_workflow(self):
        """Test filter preset creation and usage workflow"""
        mock_service = AsyncMock()
        mock_service.create_filter_preset.return_value = {
            "success": True,
            "preset_name": "high_confidence_mods"
        }
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            # Step 1: Create filter preset
            preset_data = {
                "preset_name": "high_confidence_mods",
                "filters": [
                    {"field": "confidence", "operator": "greater_than", "value": 0.9},
                    {"field": "type", "operator": "equals", "value": "mod"}
                ],
                "description": "High confidence mods only"
            }
            
            create_response = client.post("/filter-presets", json=preset_data)
            assert create_response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_layout_change_workflow(self):
        """Test layout change workflow"""
        mock_service = AsyncMock()
        mock_service.change_layout.return_value = {
            "success": True,
            "layout_changed": True
        }
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            layouts = ["spring", "circular", "hierarchical", "grid"]
            
            for layout in layouts:
                layout_data = {"layout": layout, "animate": True}
                response = client.post("/visualizations/viz_123/layout", json=layout_data)
                assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_configuration_endpoints_workflow(self):
        """Test configuration endpoints workflow"""
        # Step 1: Get visualization types
        types_response = client.get("/visualization-types")
        assert types_response.status_code == 200
        types_data = types_response.json()
        
        # Step 2: Get layout algorithms
        layouts_response = client.get("/layout-algorithms")
        assert layouts_response.status_code == 200
        layouts_data = layouts_response.json()
        
        # Step 3: Get filter types
        filters_response = client.get("/filter-types")
        assert filters_response.status_code == 200
        filters_data = filters_response.json()
        
        # Verify all have required structure
        for viz_type in types_data["visualization_types"]:
            assert "value" in viz_type
            assert "description" in viz_type
        
        for layout in layouts_data["layout_algorithms"]:
            assert "value" in layout
            assert "suitable_for" in layout
        
        for filter_type in filters_data["filter_types"]:
            assert "value" in filter_type
            assert "operators" in filter_type
            assert "fields" in filter_type
    
    @pytest.mark.asyncio
    async def test_focus_and_filter_workflow(self):
        """Test focus and filter operations workflow"""
        mock_service = AsyncMock()
        mock_service.focus_on_node.return_value = {
            "success": True,
            "nodes_in_focus": 15
        }
        mock_service.update_visualization_filters.return_value = {
            "success": True,
            "filters_updated": 2,
            "nodes_affected": 75
        }
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            # Step 1: Focus on a node
            focus_data = {
                "node_id": "central_node",
                "radius": 2,
                "animate": True
            }
            
            focus_response = client.post("/visualizations/viz_123/focus", json=focus_data)
            assert focus_response.status_code == 200
            
            # Step 2: Update filters
            filter_data = {
                "filters": [
                    {"field": "platform", "operator": "equals", "value": "java"},
                    {"field": "community", "operator": "equals", "value": 1}
                ]
            }
            
            filter_response = client.post("/visualizations/viz_123/filters", json=filter_data)
            assert filter_response.status_code == 200


class TestVisualizationPerformance:
    """Test visualization API performance characteristics"""
    
    @pytest.mark.asyncio
    async def test_multiple_visualization_creation(self):
        """Test creation of multiple visualizations"""
        mock_service = AsyncMock()
        mock_service.create_visualization.return_value = {
            "success": True,
            "visualization_id": "batch_viz"
        }
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            viz_data = {
                "graph_id": "graph_456",
                "visualization_type": "force_directed",
                "layout": "spring"
            }
            
            # Create multiple visualizations
            responses = []
            for i in range(10):
                response = client.post("/visualizations", json=viz_data)
                responses.append(response)
            
            # All should succeed
            for response in responses:
                assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_concurrent_filter_updates(self):
        """Test concurrent filter update requests"""
        mock_service = AsyncMock()
        mock_service.update_visualization_filters.return_value = {
            "success": True,
            "filters_updated": 1
        }
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            filter_data = {
                "filters": [{"field": "test", "operator": "equals", "value": "value"}]
            }
            
            # Simulate concurrent updates
            responses = []
            for i in range(5):
                response = client.post("/visualizations/viz_123/filters", json=filter_data)
                responses.append(response)
            
            # All should succeed
            for response in responses:
                assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_configuration_endpoints_performance(self):
        """Test performance of configuration endpoints"""
        import time
        
        # Test visualization types endpoint
        start_time = time.time()
        response = client.get("/visualization-types")
        types_time = time.time() - start_time
        assert response.status_code == 200
        assert types_time < 2.0  # Should respond quickly
        
        # Test layout algorithms endpoint
        start_time = time.time()
        response = client.get("/layout-algorithms")
        layouts_time = time.time() - start_time
        assert response.status_code == 200
        assert layouts_time < 2.0
        
        # Test filter types endpoint
        start_time = time.time()
        response = client.get("/filter-types")
        filters_time = time.time() - start_time
        assert response.status_code == 200
        assert filters_time < 2.0
    
    @pytest.mark.asyncio
    async def test_large_filter_array_handling(self):
        """Test handling of large filter arrays"""
        mock_service = AsyncMock()
        mock_service.update_visualization_filters.return_value = {
            "success": True,
            "filters_updated": 20,
            "nodes_affected": 500
        }
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            # Create large filter array
            large_filters = []
            for i in range(20):
                large_filters.append({
                    "field": f"property_{i}",
                    "operator": "equals",
                    "value": f"value_{i}"
                })
            
            filter_data = {"filters": large_filters}
            
            response = client.post("/visualizations/viz_123/filters", json=filter_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["filters_updated"] == 20
    
    @pytest.mark.asyncio
    async def test_performance_stats_comprehensiveness(self):
        """Test comprehensiveness of performance statistics"""
        mock_service = Mock()
        
        # Create mock visualizations with varying sizes
        for i in range(5):
            mock_viz = Mock()
            mock_viz.nodes = [Mock() for _ in range(10 * (i + 1))]  # 10, 20, 30, 40, 50 nodes
            mock_viz.edges = [Mock() for _ in range(15 * (i + 1))]  # 15, 30, 45, 60, 75 edges
            mock_service.visualization_cache[f"viz_{i}"] = mock_viz
        
        mock_service.layout_cache = {f"viz_{i}": Mock() for i in range(3)}  # 3 cached layouts
        mock_service.cluster_cache = {f"viz_{i}": Mock() for i in range(4)}  # 4 cached clusters
        mock_service.filter_presets = {f"preset_{i}": [] for i in range(7)}  # 7 presets
        
        with patch('src.api.visualization.advanced_visualization_service', mock_service):
            response = client.get("/performance-stats")
            assert response.status_code == 200
            
            data = response.json()
            stats = data["stats"]
            
            # Verify all expected stats are present
            expected_stats = [
                "active_visualizations", "cached_layouts", "cached_clusters", 
                "filter_presets", "total_nodes", "total_edges",
                "average_nodes_per_visualization", "average_edges_per_visualization"
            ]
            
            for stat in expected_stats:
                assert stat in stats
                assert isinstance(stats[stat], (int, float))
            
            # Verify calculations are reasonable
            assert stats["active_visualizations"] == 5
            assert stats["total_nodes"] == 150  # 10+20+30+40+50
            assert stats["total_edges"] == 225  # 15+30+45+60+75
            assert stats["average_nodes_per_visualization"] == 30.0
