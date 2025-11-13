"""
Simple Working Test Suite for Advanced Visualization Service

This test suite provides basic coverage for advanced visualization service components.
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
        assert LayoutAlgorithm.SPECTRAL.value == "spectral"
        assert LayoutAlgorithm.CIRCULAR.value == "circular"
        assert LayoutAlgorithm.HIERARCHICAL.value == "hierarchical"
        assert LayoutAlgorithm.MDS.value == "multidimensional_scaling"
        assert LayoutAlgorithm.PCA.value == "principal_component_analysis"
    
    def test_enum_iteration(self):
        """Test that all enums can be iterated"""
        viz_types = list(VisualizationType)
        filter_types = list(FilterType)
        layout_algos = list(LayoutAlgorithm)
        
        assert len(viz_types) > 0
        assert len(filter_types) > 0
        assert len(layout_algos) > 0
        
        # Test that all enum values are strings
        for viz_type in viz_types:
            assert isinstance(viz_type.value, str)
        
        for filter_type in filter_types:
            assert isinstance(filter_type.value, str)
        
        for layout_algo in layout_algos:
            assert isinstance(layout_algo.value, str)


class TestVisualizationDataclasses:
    """Test suite for visualization dataclasses"""
    
    def test_visualization_filter_dataclass(self):
        """Test VisualizationFilter dataclass"""
        filter_obj = VisualizationFilter(
            filter_id="filter_123",
            filter_type=FilterType.NODE_TYPE,
            field="type",
            operator="equals",
            value="conversion",
            description="Filter for conversion nodes"
        )
        
        assert filter_obj.filter_id == "filter_123"
        assert filter_obj.filter_type == FilterType.NODE_TYPE
        assert filter_obj.field == "type"
        assert filter_obj.operator == "equals"
        assert filter_obj.value == "conversion"
        assert filter_obj.description == "Filter for conversion nodes"
        assert filter_obj.metadata == {}
    
    def test_visualization_node_dataclass(self):
        """Test VisualizationNode dataclass"""
        node_obj = VisualizationNode(
            id="node_123",
            label="Test Node",
            type="conversion",
            platform="java",
            x=100.5,
            y=200.5,
            size=2.0,
            color="#ff0000",
            properties={"confidence": 0.95},
            community=1,
            confidence=0.95,
            visibility=True
        )
        
        assert node_obj.id == "node_123"
        assert node_obj.label == "Test Node"
        assert node_obj.type == "conversion"
        assert node_obj.platform == "java"
        assert node_obj.x == 100.5
        assert node_obj.y == 200.5
        assert node_obj.size == 2.0
        assert node_obj.color == "#ff0000"
        assert node_obj.properties["confidence"] == 0.95
        assert node_obj.community == 1
        assert node_obj.confidence == 0.95
        assert node_obj.visibility is True
    
    def test_visualization_edge_dataclass(self):
        """Test VisualizationEdge dataclass"""
        edge_obj = VisualizationEdge(
            id="edge_123",
            source="node_1",
            target="node_2",
            type="transforms_to",
            weight=2.5,
            color="#00ff00",
            width=3.0,
            properties={"confidence": 0.85},
            confidence=0.85,
            visibility=True
        )
        
        assert edge_obj.id == "edge_123"
        assert edge_obj.source == "node_1"
        assert edge_obj.target == "node_2"
        assert edge_obj.type == "transforms_to"
        assert edge_obj.weight == 2.5
        assert edge_obj.color == "#00ff00"
        assert edge_obj.width == 3.0
        assert edge_obj.properties["confidence"] == 0.85
        assert edge_obj.confidence == 0.85
        assert edge_obj.visibility is True
    
    def test_graph_cluster_dataclass(self):
        """Test GraphCluster dataclass"""
        cluster_obj = GraphCluster(
            cluster_id=1,
            nodes=["node_1", "node_2", "node_3"],
            edges=["edge_1", "edge_2"],
            name="Conversion Cluster",
            color="#ff0000",
            size=3,
            density=0.75,
            centrality=0.85,
            properties={"type": "conversion"}
        )
        
        assert cluster_obj.cluster_id == 1
        assert len(cluster_obj.nodes) == 3
        assert "node_1" in cluster_obj.nodes
        assert "node_2" in cluster_obj.nodes
        assert "node_3" in cluster_obj.nodes
        assert len(cluster_obj.edges) == 2
        assert cluster_obj.name == "Conversion Cluster"
        assert cluster_obj.color == "#ff0000"
        assert cluster_obj.size == 3
        assert cluster_obj.density == 0.75
        assert cluster_obj.centrality == 0.85
        assert cluster_obj.properties["type"] == "conversion"
    
    def test_visualization_state_dataclass(self):
        """Test VisualizationState dataclass"""
        state_obj = VisualizationState(
            visualization_id="viz_123",
            nodes=[
                VisualizationNode(id="node_1", label="Node 1", type="test", platform="java")
            ],
            edges=[
                VisualizationEdge(id="edge_1", source="node_1", target="node_2", type="test")
            ],
            clusters=[
                GraphCluster(cluster_id=1, name="Cluster 1")
            ],
            filters=[
                VisualizationFilter(filter_id="filter_1", filter_type=FilterType.NODE_TYPE, field="type", operator="equals", value="test")
            ],
            layout=LayoutAlgorithm.SPRING,
            viewport={"x": 0, "y": 0, "zoom": 1.0},
            metadata={"title": "Test Visualization"}
        )
        
        assert state_obj.visualization_id == "viz_123"
        assert len(state_obj.nodes) == 1
        assert state_obj.nodes[0].id == "node_1"
        assert len(state_obj.edges) == 1
        assert state_obj.edges[0].id == "edge_1"
        assert len(state_obj.clusters) == 1
        assert state_obj.clusters[0].cluster_id == 1
        assert len(state_obj.filters) == 1
        assert state_obj.filters[0].filter_id == "filter_1"
        assert state_obj.layout == LayoutAlgorithm.SPRING
        assert state_obj.viewport["x"] == 0
        assert state_obj.metadata["title"] == "Test Visualization"
    
    def test_visualization_metrics_dataclass(self):
        """Test VisualizationMetrics dataclass"""
        metrics_obj = VisualizationMetrics(
            total_nodes=100,
            total_edges=150,
            total_clusters=5,
            filtered_nodes=25,
            filtered_edges=30,
            density=0.75,
            average_degree=3.0,
            clustering_coefficient=0.85,
            path_length=2.5,
            centrality={"node_1": 0.9, "node_2": 0.7},
            rendering_time=50.5,
            memory_usage=2048.0
        )
        
        assert metrics_obj.total_nodes == 100
        assert metrics_obj.total_edges == 150
        assert metrics_obj.total_clusters == 5
        assert metrics_obj.filtered_nodes == 25
        assert metrics_obj.filtered_edges == 30
        assert metrics_obj.density == 0.75
        assert metrics_obj.average_degree == 3.0
        assert metrics_obj.clustering_coefficient == 0.85
        assert metrics_obj.path_length == 2.5
        assert metrics_obj.centrality["node_1"] == 0.9
        assert metrics_obj.centrality["node_2"] == 0.7
        assert metrics_obj.rendering_time == 50.5
        assert metrics_obj.memory_usage == 2048.0


class TestVisualizationDataclassDefaults:
    """Test suite for dataclass default values"""
    
    def test_visualization_node_defaults(self):
        """Test VisualizationNode default values"""
        node_obj = VisualizationNode(
            id="node_123",
            label="Test Node",
            type="conversion",
            platform="java"
        )
        
        assert node_obj.x == 0.0
        assert node_obj.y == 0.0
        assert node_obj.size == 1.0
        assert node_obj.color == "#666666"
        assert node_obj.properties == {}
        assert node_obj.community is None
        assert node_obj.confidence == 0.5
        assert node_obj.visibility is True
        assert node_obj.metadata == {}
    
    def test_visualization_edge_defaults(self):
        """Test VisualizationEdge default values"""
        edge_obj = VisualizationEdge(
            id="edge_123",
            source="node_1",
            target="node_2",
            type="transforms_to"
        )
        
        assert edge_obj.weight == 1.0
        assert edge_obj.color == "#999999"
        assert edge_obj.width == 1.0
        assert edge_obj.properties == {}
        assert edge_obj.confidence == 0.5
        assert edge_obj.visibility is True
        assert edge_obj.metadata == {}
    
    def test_graph_cluster_defaults(self):
        """Test GraphCluster default values"""
        cluster_obj = GraphCluster(cluster_id=1)
        
        assert cluster_obj.nodes == []
        assert cluster_obj.edges == []
        assert cluster_obj.name == ""
        assert cluster_obj.color == ""
        assert cluster_obj.size == 0
        assert cluster_obj.density == 0.0
        assert cluster_obj.centrality == 0.0
        assert cluster_obj.properties == {}
    
    def test_visualization_state_defaults(self):
        """Test VisualizationState default values"""
        state_obj = VisualizationState(visualization_id="viz_123")
        
        assert state_obj.nodes == []
        assert state_obj.edges == []
        assert state_obj.clusters == []
        assert state_obj.filters == []
        assert state_obj.layout == LayoutAlgorithm.SPRING
        assert state_obj.viewport == {}
        assert state_obj.metadata == {}
    
    def test_visualization_metrics_defaults(self):
        """Test VisualizationMetrics default values"""
        metrics_obj = VisualizationMetrics()
        
        assert metrics_obj.total_nodes == 0
        assert metrics_obj.total_edges == 0
        assert metrics_obj.total_clusters == 0
        assert metrics_obj.filtered_nodes == 0
        assert metrics_obj.filtered_edges == 0
        assert metrics_obj.density == 0.0
        assert metrics_obj.average_degree == 0.0
        assert metrics_obj.clustering_coefficient == 0.0
        assert metrics_obj.path_length == 0.0
        assert metrics_obj.centrality == {}
        assert metrics_obj.rendering_time == 0.0
        assert metrics_obj.memory_usage == 0.0


class TestVisualizationTypeValidation:
    """Test suite for type validation and conversion"""
    
    def test_visualization_type_from_string(self):
        """Test creating VisualizationType from string"""
        viz_type = VisualizationType("force_directed")
        assert viz_type == VisualizationType.FORCE_DIRECTED
        assert viz_type.value == "force_directed"
        
        viz_type = VisualizationType("circular")
        assert viz_type == VisualizationType.CIRCULAR
        assert viz_type.value == "circular"
    
    def test_filter_type_from_string(self):
        """Test creating FilterType from string"""
        filter_type = FilterType("node_type")
        assert filter_type == FilterType.NODE_TYPE
        assert filter_type.value == "node_type"
        
        filter_type = FilterType("confidence")
        assert filter_type == FilterType.CONFIDENCE
        assert filter_type.value == "confidence"
    
    def test_layout_algorithm_from_string(self):
        """Test creating LayoutAlgorithm from string"""
        layout_algo = LayoutAlgorithm("spring")
        assert layout_algo == LayoutAlgorithm.SPRING
        assert layout_algo.value == "spring"
        
        layout_algo = LayoutAlgorithm("circular")
        assert layout_algo == LayoutAlgorithm.CIRCULAR
        assert layout_algo.value == "circular"
    
    def test_invalid_enum_values(self):
        """Test handling of invalid enum values"""
        with pytest.raises(ValueError):
            VisualizationType("invalid_type")
        
        with pytest.raises(ValueError):
            FilterType("invalid_filter")
        
        with pytest.raises(ValueError):
            LayoutAlgorithm("invalid_algorithm")


class TestVisualizationSerialization:
    """Test suite for dataclass serialization"""
    
    def test_visualization_filter_serialization(self):
        """Test VisualizationFilter serialization"""
        filter_obj = VisualizationFilter(
            filter_id="filter_123",
            filter_type=FilterType.NODE_TYPE,
            field="type",
            operator="equals",
            value="conversion"
        )
        
        # Test that the object can be serialized to JSON
        filter_dict = {
            "filter_id": filter_obj.filter_id,
            "filter_type": filter_obj.filter_type.value,
            "field": filter_obj.field,
            "operator": filter_obj.operator,
            "value": filter_obj.value,
            "description": filter_obj.description,
            "metadata": filter_obj.metadata
        }
        
        json_str = json.dumps(filter_dict, default=str)
        assert json_str is not None
        
        # Test that it can be deserialized
        loaded_dict = json.loads(json_str)
        assert loaded_dict["filter_id"] == "filter_123"
        assert loaded_dict["filter_type"] == "node_type"
        assert loaded_dict["field"] == "type"
        assert loaded_dict["operator"] == "equals"
        assert loaded_dict["value"] == "conversion"
    
    def test_visualization_node_serialization(self):
        """Test VisualizationNode serialization"""
        node_obj = VisualizationNode(
            id="node_123",
            label="Test Node",
            type="conversion",
            platform="java",
            properties={"confidence": 0.95}
        )
        
        node_dict = {
            "id": node_obj.id,
            "label": node_obj.label,
            "type": node_obj.type,
            "platform": node_obj.platform,
            "x": node_obj.x,
            "y": node_obj.y,
            "size": node_obj.size,
            "color": node_obj.color,
            "properties": node_obj.properties,
            "community": node_obj.community,
            "confidence": node_obj.confidence,
            "visibility": node_obj.visibility,
            "metadata": node_obj.metadata
        }
        
        json_str = json.dumps(node_dict, default=str)
        assert json_str is not None
        
        loaded_dict = json.loads(json_str)
        assert loaded_dict["id"] == "node_123"
        assert loaded_dict["label"] == "Test Node"
        assert loaded_dict["type"] == "conversion"
        assert loaded_dict["platform"] == "java"
    
    def test_complex_state_serialization(self):
        """Test complex VisualizationState serialization"""
        complex_state = VisualizationState(
            visualization_id="viz_complex",
            nodes=[
                VisualizationNode(id="n1", label="Node 1", type="type1", platform="java"),
                VisualizationNode(id="n2", label="Node 2", type="type2", platform="bedrock")
            ],
            edges=[
                VisualizationEdge(id="e1", source="n1", target="n2", type="transforms")
            ],
            clusters=[
                GraphCluster(cluster_id=1, name="Cluster 1", nodes=["n1", "n2"])
            ],
            filters=[
                VisualizationFilter(filter_id="f1", filter_type=FilterType.NODE_TYPE, field="type", operator="equals", value="type1")
            ]
        )
        
        state_dict = {
            "visualization_id": complex_state.visualization_id,
            "nodes": [
                {
                    "id": n.id, "label": n.label, "type": n.type, "platform": n.platform,
                    "x": n.x, "y": n.y, "size": n.size, "color": n.color,
                    "properties": n.properties, "community": n.community,
                    "confidence": n.confidence, "visibility": n.visibility,
                    "metadata": n.metadata
                }
                for n in complex_state.nodes
            ],
            "edges": [
                {
                    "id": e.id, "source": e.source, "target": e.target, "type": e.type,
                    "weight": e.weight, "color": e.color, "width": e.width,
                    "properties": e.properties, "confidence": e.confidence,
                    "visibility": e.visibility, "metadata": e.metadata
                }
                for e in complex_state.edges
            ],
            "clusters": [
                {
                    "cluster_id": c.cluster_id, "nodes": c.nodes, "edges": c.edges,
                    "name": c.name, "color": c.color, "size": c.size,
                    "density": c.density, "centrality": c.centrality,
                    "properties": c.properties
                }
                for c in complex_state.clusters
            ],
            "filters": [
                {
                    "filter_id": f.filter_id, "filter_type": f.filter_type.value,
                    "field": f.field, "operator": f.operator, "value": f.value,
                    "description": f.description, "metadata": f.metadata
                }
                for f in complex_state.filters
            ],
            "layout": complex_state.layout.value,
            "viewport": complex_state.viewport,
            "metadata": complex_state.metadata,
            "created_at": complex_state.created_at.isoformat()
        }
        
        json_str = json.dumps(state_dict, default=str)
        assert json_str is not None
        assert len(json_str) > 0
        
        loaded_dict = json.loads(json_str)
        assert loaded_dict["visualization_id"] == "viz_complex"
        assert len(loaded_dict["nodes"]) == 2
        assert len(loaded_dict["edges"]) == 1
        assert len(loaded_dict["clusters"]) == 1
        assert len(loaded_dict["filters"]) == 1


class TestVisualizationPerformanceMetrics:
    """Test suite for visualization performance metrics"""
    
    def test_metrics_calculation(self):
        """Test metrics calculation from graph data"""
        # Create sample graph data
        nodes = [
            VisualizationNode(id="n1", label="Node 1", type="type1", platform="java"),
            VisualizationNode(id="n2", label="Node 2", type="type1", platform="java"),
            VisualizationNode(id="n3", label="Node 3", type="type2", platform="bedrock")
        ]
        
        edges = [
            VisualizationEdge(id="e1", source="n1", target="n2", type="connects"),
            VisualizationEdge(id="e2", source="n2", target="n3", type="connects"),
            VisualizationEdge(id="e3", source="n1", target="n3", type="connects")
        ]
        
        # Calculate metrics manually
        total_nodes = len(nodes)
        total_edges = len(edges)
        max_possible_edges = total_nodes * (total_nodes - 1) / 2
        density = total_edges / max_possible_edges if max_possible_edges > 0 else 0
        average_degree = (2 * total_edges) / total_nodes if total_nodes > 0 else 0
        
        # Create metrics object
        metrics = VisualizationMetrics(
            total_nodes=total_nodes,
            total_edges=total_edges,
            density=density,
            average_degree=average_degree
        )
        
        assert metrics.total_nodes == 3
        assert metrics.total_edges == 3
        assert metrics.density == density
        assert metrics.average_degree == average_degree
    
    def test_metrics_serialization(self):
        """Test metrics serialization"""
        metrics = VisualizationMetrics(
            total_nodes=100,
            total_edges=150,
            total_clusters=5,
            density=0.75,
            average_degree=3.0,
            centrality={"n1": 0.9, "n2": 0.7},
            rendering_time=50.5,
            memory_usage=2048.0
        )
        
        metrics_dict = {
            "total_nodes": metrics.total_nodes,
            "total_edges": metrics.total_edges,
            "total_clusters": metrics.total_clusters,
            "filtered_nodes": metrics.filtered_nodes,
            "filtered_edges": metrics.filtered_edges,
            "density": metrics.density,
            "average_degree": metrics.average_degree,
            "clustering_coefficient": metrics.clustering_coefficient,
            "path_length": metrics.path_length,
            "centrality": metrics.centrality,
            "rendering_time": metrics.rendering_time,
            "memory_usage": metrics.memory_usage
        }
        
        json_str = json.dumps(metrics_dict, default=str)
        assert json_str is not None
        
        loaded_dict = json.loads(json_str)
        assert loaded_dict["total_nodes"] == 100
        assert loaded_dict["total_edges"] == 150
        assert loaded_dict["density"] == 0.75
        assert loaded_dict["average_degree"] == 3.0
        assert loaded_dict["centrality"]["n1"] == 0.9
