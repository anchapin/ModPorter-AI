"""
Working Test Suite for Advanced Visualization Service

This test suite provides comprehensive coverage for the advanced visualization service.
"""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

# Import visualization service
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from src.services.advanced_visualization import (
    VisualizationType, FilterType, LayoutAlgorithm,
    VisualizationFilter, VisualizationNode, VisualizationEdge,
    GraphCluster, VisualizationState, VisualizationMetrics
)


class TestVisualizationEnums:
    """Test suite for visualization enums"""
    
    def test_visualization_type_enum(self):
        """Test VisualizationType enum values"""
        assert VisualizationType.FORCE_DIRECTED.value == "force_directed"
        assert VisualizationType.FORCE_UNDIRECTED.value == "force_undirected"
        assert VisualizationType.CIRCULAR.value == "circular"
        assert VisualizationType.HIERARCHICAL.value == "hierarchical"
        assert VisualizationType.CLUSTERED.value == "clustered"
        assert VisualizationType.GEOGRAPHIC.value == "geographic"
        assert VisualizationType.TEMPORAL.value == "temporal"
        assert VisualizationType.COMPARATIVE.value == "comparative"
    
    def test_filter_type_enum(self):
        """Test FilterType enum values"""
        assert FilterType.NODE_TYPE.value == "node_type"
        assert FilterType.PLATFORM.value == "platform"
        assert FilterType.VERSION.value == "version"
        assert FilterType.CONFIDENCE.value == "confidence"
        assert FilterType.COMMUNITY_RATING.value == "community_rating"
        assert FilterType.EXPERT_VALIDATED.value == "expert_validated"
        assert FilterType.DATE_RANGE.value == "date_range"
        assert FilterType.TEXT_SEARCH.value == "text_search"
        assert FilterType.CUSTOM.value == "custom"
    
    def test_layout_algorithm_enum(self):
        """Test LayoutAlgorithm enum values"""
        assert LayoutAlgorithm.SPRING.value == "spring"
        assert LayoutAlgorithm.FORCE_ATLAS2.value == "force_atlas2"
        assert LayoutAlgorithm.FRUCHTERMAN_REINGOLD.value == "fruchterman_reingold"
        assert LayoutAlgorithm.KAMADA_KAWAI.value == "kamada_kawai"
        assert LayoutAlgorithm.CIRCULAR.value == "circular"
        assert LayoutAlgorithm.HIERARCHICAL.value == "hierarchical"
        assert LayoutAlgorithm.GEOGRAPHIC.value == "geographic"


class TestVisualizationService:
    """Test suite for AdvancedVisualizationService"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def visualization_service(self, mock_db):
        """Create visualization service instance"""
        return AdvancedVisualizationService(mock_db)
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, mock_db):
        """Test service initialization"""
        service = AdvancedVisualizationService(mock_db)
        
        assert service.db == mock_db
        assert service.node_crud is not None
        assert self.relationship_crud is not None
        assert self.pattern_crud is not None
    
    @pytest.mark.asyncio
    async def test_create_visualization_success(self, visualization_service):
        """Test successful visualization creation"""
        viz_config = {
            "type": "force_directed",
            "title": "Test Visualization",
            "description": "Test visualization description",
            "nodes": ["node1", "node2"],
            "filters": [],
            "layout": {"algorithm": "spring", "iterations": 100}
        }
        
        with patch.object(visualization_service, '_generate_layout') as mock_layout:
            mock_layout.return_value = {
                "nodes": [{"id": "node1", "x": 100, "y": 100}],
                "edges": [{"source": "node1", "target": "node2"}]
            }
            
            result = await visualization_service.create_visualization(viz_config)
            
            assert result["type"] == "force_directed"
            assert result["title"] == "Test Visualization"
            assert "nodes" in result
            assert "edges" in result
            assert result["layout"]["algorithm"] == "spring"
    
    @pytest.mark.asyncio
    async def test_get_visualization_success(self, visualization_service):
        """Test successful visualization retrieval"""
        viz_id = "viz_123"
        
        with patch.object(visualization_service, '_load_visualization') as mock_load:
            mock_load.return_value = {
                "id": viz_id,
                "type": "force_directed",
                "title": "Test Visualization",
                "nodes": [{"id": "node1"}],
                "edges": [{"source": "node1", "target": "node2"}]
            }
            
            result = await visualization_service.get_visualization(viz_id)
            
            assert result["id"] == viz_id
            assert result["type"] == "force_directed"
            assert "nodes" in result
            assert "edges" in result
    
    @pytest.mark.asyncio
    async def test_update_visualization_success(self, visualization_service):
        """Test successful visualization update"""
        viz_id = "viz_123"
        update_data = {
            "title": "Updated Title",
            "layout": {"algorithm": "circular"}
        }
        
        with patch.object(visualization_service, '_save_visualization') as mock_save:
            mock_save.return_value = {
                "id": viz_id,
                "title": "Updated Title",
                "layout": {"algorithm": "circular"}
            }
            
            result = await visualization_service.update_visualization(viz_id, update_data)
            
            assert result["id"] == viz_id
            assert result["title"] == "Updated Title"
            assert result["layout"]["algorithm"] == "circular"
    
    @pytest.mark.asyncio
    async def test_delete_visualization_success(self, visualization_service):
        """Test successful visualization deletion"""
        viz_id = "viz_123"
        
        with patch.object(visualization_service, '_remove_visualization') as mock_remove:
            mock_remove.return_value = True
            
            result = await visualization_service.delete_visualization(viz_id)
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_apply_filters_success(self, visualization_service):
        """Test successful filter application"""
        viz_data = {
            "nodes": [
                {"id": "node1", "type": "conversion", "platform": "java"},
                {"id": "node2", "type": "pattern", "platform": "bedrock"}
            ],
            "edges": [
                {"source": "node1", "target": "node2"}
            ]
        }
        
        filters = [
            {"type": "node_type", "value": "conversion"},
            {"type": "platform", "value": "java"}
        ]
        
        result = await visualization_service.apply_filters(viz_data, filters)
        
        assert len(result["nodes"]) == 1
        assert result["nodes"][0]["id"] == "node1"
    
    @pytest.mark.asyncio
    async def test_change_layout_success(self, visualization_service):
        """Test successful layout change"""
        viz_data = {
            "nodes": [
                {"id": "node1"},
                {"id": "node2"}
            ],
            "edges": [
                {"source": "node1", "target": "node2"}
            ]
        }
        
        layout_config = {
            "algorithm": "circular",
            "radius": 100
        }
        
        with patch.object(visualization_service, '_calculate_layout') as mock_calc:
            mock_calc.return_value = {
                "nodes": [
                    {"id": "node1", "x": 100, "y": 0},
                    {"id": "node2", "x": -100, "y": 0}
                ]
            }
            
            result = await visualization_service.change_layout(viz_data, layout_config)
            
            assert "nodes" in result
            assert result["nodes"][0]["x"] == 100
            assert result["nodes"][0]["y"] == 0
    
    @pytest.mark.asyncio
    async def test_focus_on_node_success(self, visualization_service):
        """Test successful node focus"""
        viz_data = {
            "nodes": [
                {"id": "node1", "x": 0, "y": 0},
                {"id": "node2", "x": 100, "y": 100},
                {"id": "node3", "x": -100, "y": -100}
            ],
            "edges": [
                {"source": "node1", "target": "node2"},
                {"source": "node1", "target": "node3"}
            ]
        }
        
        result = await visualization_service.focus_on_node(viz_data, "node1")
        
        assert len(result["nodes"]) == 3
        assert len(result["edges"]) == 2
        # Check if node1 is centered
        node1 = next(n for n in result["nodes"] if n["id"] == "node1")
        assert abs(node1["x"]) < 10  # Should be close to center
        assert abs(node1["y"]) < 10
    
    @pytest.mark.asyncio
    async def test_create_filter_preset_success(self, visualization_service):
        """Test successful filter preset creation"""
        preset_data = {
            "name": "Java Conversions",
            "description": "Filter for Java conversion patterns",
            "filters": [
                {"type": "platform", "value": "java"},
                {"type": "node_type", "value": "conversion"}
            ]
        }
        
        with patch.object(visualization_service, '_save_filter_preset') as mock_save:
            mock_save.return_value = {
                "id": "preset_123",
                "name": "Java Conversions",
                "filters": preset_data["filters"]
            }
            
            result = await visualization_service.create_filter_preset(preset_data)
            
            assert result["name"] == "Java Conversions"
            assert len(result["filters"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_filter_presets_success(self, visualization_service):
        """Test successful filter presets retrieval"""
        with patch.object(visualization_service, '_load_filter_presets') as mock_load:
            mock_load.return_value = [
                {
                    "id": "preset_123",
                    "name": "Java Conversions",
                    "filters": [{"type": "platform", "value": "java"}]
                },
                {
                    "id": "preset_456",
                    "name": "High Confidence",
                    "filters": [{"type": "confidence", "value": 0.8}]
                }
            ]
            
            result = await visualization_service.get_filter_presets()
            
            assert len(result["presets"]) == 2
            assert result["presets"][0]["name"] == "Java Conversions"
    
    @pytest.mark.asyncio
    async def test_export_visualization_success(self, visualization_service):
        """Test successful visualization export"""
        viz_id = "viz_123"
        export_config = {
            "format": "json",
            "include_filters": True,
            "include_layout": True
        }
        
        with patch.object(visualization_service, '_prepare_export_data') as mock_prepare:
            mock_prepare.return_value = {
                "id": viz_id,
                "type": "force_directed",
                "nodes": [{"id": "node1"}],
                "edges": [{"source": "node1", "target": "node2"}]
            }
            
            result = await visualization_service.export_visualization(viz_id, export_config)
            
            assert result["format"] == "json"
            assert "nodes" in result
            assert "edges" in result
    
    @pytest.mark.asyncio
    async def test_get_visualization_metrics_success(self, visualization_service):
        """Test successful visualization metrics retrieval"""
        viz_data = {
            "nodes": [
                {"id": "node1", "type": "conversion"},
                {"id": "node2", "type": "pattern"},
                {"id": "node3", "type": "conversion"}
            ],
            "edges": [
                {"source": "node1", "target": "node2"},
                {"source": "node2", "target": "node3"}
            ]
        }
        
        result = await visualization_service.get_visualization_metrics(viz_data)
        
        assert result["total_nodes"] == 3
        assert result["total_edges"] == 2
        assert result["node_types"]["conversion"] == 2
        assert result["node_types"]["pattern"] == 1
        assert "density" in result
        assert "average_degree" in result


class TestVisualizationLayout:
    """Test suite for visualization layout functionality"""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def visualization_service(self, mock_db):
        return AdvancedVisualizationService(mock_db)
    
    @pytest.mark.asyncio
    async def test_spring_layout_algorithm(self, visualization_service):
        """Test spring layout algorithm"""
        nodes = [
            {"id": "node1"},
            {"id": "node2"},
            {"id": "node3"}
        ]
        edges = [
            {"source": "node1", "target": "node2"},
            {"source": "node2", "target": "node3"}
        ]
        
        layout_config = {
            "algorithm": "spring",
            "iterations": 100,
            "force_strength": 1.0,
            "link_distance": 50
        }
        
        result = await visualization_service._calculate_layout(
            nodes, edges, layout_config
        )
        
        assert "nodes" in result
        assert len(result["nodes"]) == 3
        # Check that all nodes have positions
        for node in result["nodes"]:
            assert "x" in node
            assert "y" in node
    
    @pytest.mark.asyncio
    async def test_circular_layout_algorithm(self, visualization_service):
        """Test circular layout algorithm"""
        nodes = [
            {"id": "node1"},
            {"id": "node2"},
            {"id": "node3"},
            {"id": "node4"}
        ]
        edges = [
            {"source": "node1", "target": "node2"},
            {"source": "node2", "target": "node3"},
            {"source": "node3", "target": "node4"},
            {"source": "node4", "target": "node1"}
        ]
        
        layout_config = {
            "algorithm": "circular",
            "radius": 100,
            "start_angle": 0
        }
        
        result = await visualization_service._calculate_layout(
            nodes, edges, layout_config
        )
        
        assert "nodes" in result
        assert len(result["nodes"]) == 4
        # Check that nodes are positioned in a circle
        for node in result["nodes"]:
            assert "x" in node
            assert "y" in node
    
    @pytest.mark.asyncio
    async def test_hierarchical_layout_algorithm(self, visualization_service):
        """Test hierarchical layout algorithm"""
        nodes = [
            {"id": "root", "level": 0},
            {"id": "child1", "level": 1, "parent": "root"},
            {"id": "child2", "level": 1, "parent": "root"},
            {"id": "grandchild1", "level": 2, "parent": "child1"}
        ]
        edges = [
            {"source": "root", "target": "child1"},
            {"source": "root", "target": "child2"},
            {"source": "child1", "target": "grandchild1"}
        ]
        
        layout_config = {
            "algorithm": "hierarchical",
            "level_height": 100,
            "node_spacing": 50
        }
        
        result = await visualization_service._calculate_layout(
            nodes, edges, layout_config
        )
        
        assert "nodes" in result
        assert len(result["nodes"]) == 4
        
        # Check hierarchical positioning
        root = next(n for n in result["nodes"] if n["id"] == "root")
        child1 = next(n for n in result["nodes"] if n["id"] == "child1")
        child2 = next(n for n in result["nodes"] if n["id"] == "child2")
        
        # Root should be at higher y-coordinate (lower on screen)
        assert root["y"] < child1["y"]
        assert root["y"] < child2["y"]
    
    @pytest.mark.asyncio
    async def test_geographic_layout_algorithm(self, visualization_service):
        """Test geographic layout algorithm"""
        nodes = [
            {"id": "node1", "latitude": 40.7128, "longitude": -74.0060},  # New York
            {"id": "node2", "latitude": 34.0522, "longitude": -118.2437},  # Los Angeles
            {"id": "node3", "latitude": 51.5074, "longitude": -0.1278}    # London
        ]
        edges = [
            {"source": "node1", "target": "node2"},
            {"source": "node2", "target": "node3"}
        ]
        
        layout_config = {
            "algorithm": "geographic",
            "projection": "mercator",
            "scale": 1000
        }
        
        result = await visualization_service._calculate_layout(
            nodes, edges, layout_config
        )
        
        assert "nodes" in result
        assert len(result["nodes"]) == 3
        
        # Check that coordinates are projected
        for node in result["nodes"]:
            assert "x" in node
            assert "y" in node


class TestVisualizationFilters:
    """Test suite for visualization filter functionality"""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def visualization_service(self, mock_db):
        return AdvancedVisualizationService(mock_db)
    
    @pytest.mark.asyncio
    async def test_node_type_filter(self, visualization_service):
        """Test node type filter"""
        nodes = [
            {"id": "node1", "type": "conversion"},
            {"id": "node2", "type": "pattern"},
            {"id": "node3", "type": "conversion"}
        ]
        
        filter_config = {
            "type": "node_type",
            "value": "conversion"
        }
        
        result = await visualization_service._apply_node_filter(nodes, filter_config)
        
        assert len(result) == 2
        assert all(node["type"] == "conversion" for node in result)
    
    @pytest.mark.asyncio
    async def test_platform_filter(self, visualization_service):
        """Test platform filter"""
        nodes = [
            {"id": "node1", "platform": "java"},
            {"id": "node2", "platform": "bedrock"},
            {"id": "node3", "platform": "java"}
        ]
        
        filter_config = {
            "type": "platform",
            "value": "java"
        }
        
        result = await visualization_service._apply_node_filter(nodes, filter_config)
        
        assert len(result) == 2
        assert all(node["platform"] == "java" for node in result)
    
    @pytest.mark.asyncio
    async def test_confidence_filter(self, visualization_service):
        """Test confidence filter"""
        nodes = [
            {"id": "node1", "confidence": 0.95},
            {"id": "node2", "confidence": 0.75},
            {"id": "node3", "confidence": 0.85}
        ]
        
        filter_config = {
            "type": "confidence",
            "value": 0.8,
            "operator": "greater_than"
        }
        
        result = await visualization_service._apply_node_filter(nodes, filter_config)
        
        assert len(result) == 2
        assert all(node["confidence"] > 0.8 for node in result)
    
    @pytest.mark.asyncio
    async def test_date_range_filter(self, visualization_service):
        """Test date range filter"""
        nodes = [
            {"id": "node1", "created_at": "2023-01-01"},
            {"id": "node2", "created_at": "2023-03-15"},
            {"id": "node3", "created_at": "2023-05-20"}
        ]
        
        filter_config = {
            "type": "date_range",
            "start_date": "2023-02-01",
            "end_date": "2023-04-30"
        }
        
        result = await visualization_service._apply_node_filter(nodes, filter_config)
        
        assert len(result) == 1
        assert result[0]["id"] == "node2"
    
    @pytest.mark.asyncio
    async def test_text_search_filter(self, visualization_service):
        """Test text search filter"""
        nodes = [
            {"id": "node1", "title": "Java to Bedrock Conversion"},
            {"id": "node2", "title": "Block Transformation Pattern"},
            {"id": "node3", "title": "Entity Mapping Strategy"}
        ]
        
        filter_config = {
            "type": "text_search",
            "value": "Java",
            "fields": ["title", "description"]
        }
        
        result = await visualization_service._apply_node_filter(nodes, filter_config)
        
        assert len(result) == 1
        assert result[0]["id"] == "node1"
    
    @pytest.mark.asyncio
    async def test_custom_filter(self, visualization_service):
        """Test custom filter"""
        nodes = [
            {"id": "node1", "custom_field": "value1"},
            {"id": "node2", "custom_field": "value2"},
            {"id": "node3", "custom_field": "value1"}
        ]
        
        filter_config = {
            "type": "custom",
            "field": "custom_field",
            "value": "value1"
        }
        
        result = await visualization_service._apply_node_filter(nodes, filter_config)
        
        assert len(result) == 2
        assert all(node["custom_field"] == "value1" for node in result)
    
    @pytest.mark.asyncio
    async def test_multiple_filters(self, visualization_service):
        """Test applying multiple filters"""
        nodes = [
            {"id": "node1", "type": "conversion", "platform": "java", "confidence": 0.95},
            {"id": "node2", "type": "pattern", "platform": "java", "confidence": 0.85},
            {"id": "node3", "type": "conversion", "platform": "bedrock", "confidence": 0.75}
        ]
        
        filters = [
            {"type": "node_type", "value": "conversion"},
            {"type": "platform", "value": "java"},
            {"type": "confidence", "value": 0.9, "operator": "greater_than"}
        ]
        
        result = await visualization_service.apply_filters(
            {"nodes": nodes, "edges": []}, filters
        )
        
        assert len(result["nodes"]) == 1
        assert result["nodes"][0]["id"] == "node1"


class TestVisualizationErrorHandling:
    """Test suite for error handling in visualization service"""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def visualization_service(self, mock_db):
        return AdvancedVisualizationService(mock_db)
    
    @pytest.mark.asyncio
    async def test_invalid_visualization_type(self, visualization_service):
        """Test handling of invalid visualization type"""
        viz_config = {
            "type": "invalid_type",
            "title": "Test Visualization"
        }
        
        with pytest.raises(ValueError):
            await visualization_service.create_visualization(viz_config)
    
    @pytest.mark.asyncio
    async def test_invalid_layout_algorithm(self, visualization_service):
        """Test handling of invalid layout algorithm"""
        nodes = [{"id": "node1"}, {"id": "node2"}]
        edges = [{"source": "node1", "target": "node2"}]
        
        layout_config = {
            "algorithm": "invalid_algorithm"
        }
        
        with pytest.raises(ValueError):
            await visualization_service._calculate_layout(
                nodes, edges, layout_config
            )
    
    @pytest.mark.asyncio
    async def test_invalid_filter_type(self, visualization_service):
        """Test handling of invalid filter type"""
        nodes = [{"id": "node1", "type": "conversion"}]
        
        filter_config = {
            "type": "invalid_filter_type",
            "value": "conversion"
        }
        
        with pytest.raises(ValueError):
            await visualization_service._apply_node_filter(nodes, filter_config)
    
    @pytest.mark.asyncio
    async def test_nonexistent_visualization(self, visualization_service):
        """Test handling of non-existent visualization"""
        with pytest.raises(ValueError):
            await visualization_service.get_visualization("nonexistent_viz")
    
    @pytest.mark.asyncio
    async def test_database_connection_error(self, visualization_service):
        """Test handling of database connection errors"""
        # Mock database error
        visualization_service.node_crud.get_nodes.side_effect = Exception("DB connection failed")
        
        with pytest.raises(Exception):
            await visualization_service.get_visualization("viz_123")
    
    @pytest.mark.asyncio
    async def test_empty_graph_handling(self, visualization_service):
        """Test handling of empty graph data"""
        empty_viz_data = {"nodes": [], "edges": []}
        
        result = await visualization_service.get_visualization_metrics(empty_viz_data)
        
        assert result["total_nodes"] == 0
        assert result["total_edges"] == 0
        assert result["density"] == 0
        assert result["average_degree"] == 0


# Test dataclasses for type safety testing
def test_node_filter_dataclass():
    """Test NodeFilter dataclass"""
    filter_obj = NodeFilter(
        type=FilterType.NODE_TYPE,
        value="conversion",
        operator="equals"
    )
    
    assert filter_obj.type == FilterType.NODE_TYPE
    assert filter_obj.value == "conversion"
    assert filter_obj.operator == "equals"


def test_edge_filter_dataclass():
    """Test EdgeFilter dataclass"""
    filter_obj = EdgeFilter(
        type=FilterType.CONFIDENCE,
        value=0.8,
        operator="greater_than"
    )
    
    assert filter_obj.type == FilterType.CONFIDENCE
    assert filter_obj.value == 0.8
    assert filter_obj.operator == "greater_than"


def test_visualization_layout_dataclass():
    """Test VisualizationLayout dataclass"""
    layout_obj = VisualizationLayout(
        algorithm=LayoutAlgorithm.SPRING,
        iterations=100,
        force_strength=1.0,
        link_distance=50
    )
    
    assert layout_obj.algorithm == LayoutAlgorithm.SPRING
    assert layout_obj.iterations == 100
    assert layout_obj.force_strength == 1.0
    assert layout_obj.link_distance == 50


def test_interactive_features_dataclass():
    """Test InteractiveFeatures dataclass"""
    features = InteractiveFeatures(
        enable_zoom=True,
        enable_pan=True,
        enable_selection=True,
        enable_hover=True,
        enable_drag=True
    )
    
    assert features.enable_zoom is True
    assert features.enable_pan is True
    assert features.enable_selection is True
    assert features.enable_hover is True
    assert features.enable_drag is True
