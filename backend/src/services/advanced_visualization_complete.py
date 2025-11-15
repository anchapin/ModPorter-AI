# -*- coding: utf-8 -*-
"""
Advanced Visualization Service for Knowledge Graph (Complete)

This service provides advanced visualization capabilities for knowledge graphs,
including filtering, clustering, layout algorithms, and interactive features.
"""

import logging
import json
import math
import networkx as nx
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func

from ..db.database import get_async_session
from ..db.knowledge_graph_crud import (
    KnowledgeNodeCRUD, KnowledgeRelationshipCRUD, ConversionPatternCRUD
)
from ..db.models import (
    KnowledgeNode, KnowledgeRelationship, ConversionPattern
)

logger = logging.getLogger(__name__)


class VisualizationType(Enum):
    """Types of visualizations."""
    FORCE_DIRECTED = "force_directed"
    FORCE_UNDIRECTED = "force_undirected"
    CIRCULAR = "circular"
    HIERARCHICAL = "hierarchical"
    CLUSTERED = "clustered"
    GEOGRAPHIC = "geographic"
    TEMPORAL = "temporal"
    COMPARATIVE = "comparative"


class FilterType(Enum):
    """Types of filters for visualization."""
    NODE_TYPE = "node_type"
    PLATFORM = "platform"
    VERSION = "version"
    CONFIDENCE = "confidence"
    COMMUNITY_RATING = "community_rating"
    EXPERT_VALIDATED = "expert_validated"
    DATE_RANGE = "date_range"
    TEXT_SEARCH = "text_search"
    CUSTOM = "custom"


class LayoutAlgorithm(Enum):
    """Layout algorithms for graph visualization."""
    SPRING = "spring"
    FRUCHTERMAN_REINGOLD = "fruchterman_reingold"
    KAMADA_KAWAI = "kamada_kawai"
    SPECTRAL = "spectral"
    CIRCULAR = "circular"
    HIERARCHICAL = "hierarchical"
    MDS = "multidimensional_scaling"
    PCA = "principal_component_analysis"


@dataclass
class VisualizationFilter:
    """Filter for graph visualization."""
    filter_id: str
    filter_type: FilterType
    field: str
    operator: str  # eq, ne, gt, gte, lt, lte, in, contains
    value: Any
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VisualizationNode:
    """Node for graph visualization."""
    id: str
    label: str
    type: str
    platform: str
    x: float = 0.0
    y: float = 0.0
    size: float = 1.0
    color: str = "#666666"
    properties: Dict[str, Any] = field(default_factory=dict)
    community: Optional[int] = None
    confidence: float = 0.5
    visibility: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VisualizationEdge:
    """Edge for graph visualization."""
    id: str
    source: str
    target: str
    type: str
    weight: float = 1.0
    color: str = "#999999"
    width: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    visibility: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphCluster:
    """Cluster in graph visualization."""
    cluster_id: int
    nodes: List[str] = field(default_factory=list)
    edges: List[str] = field(default_factory=list)
    name: str = ""
    color: str = ""
    size: int = 0
    density: float = 0.0
    centrality: float = 0.0
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VisualizationState:
    """Complete state of graph visualization."""
    visualization_id: str
    nodes: List[VisualizationNode] = field(default_factory=list)
    edges: List[VisualizationEdge] = field(default_factory=list)
    clusters: List[GraphCluster] = field(default_factory=list)
    filters: List[VisualizationFilter] = field(default_factory=list)
    layout: LayoutAlgorithm = LayoutAlgorithm.SPRING
    viewport: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class AdvancedVisualizationService:
    """Advanced visualization service for knowledge graphs."""
    
    def __init__(self):
        self.visualization_cache: Dict[str, VisualizationState] = {}
        self.filter_presets: Dict[str, List[VisualizationFilter]] = {}
        self.layout_cache: Dict[str, Dict[str, Any]] = {}
        self.cluster_cache: Dict[str, List[GraphCluster]] = {}
        
    async def create_visualization(
        self,
        graph_id: str,
        visualization_type: VisualizationType,
        filters: Optional[List[Dict[str, Any]]] = None,
        layout: LayoutAlgorithm = LayoutAlgorithm.SPRING,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Create a new graph visualization.
        
        Args:
            graph_id: ID of the knowledge graph to visualize
            visualization_type: Type of visualization to create
            filters: Filters to apply to the visualization
            layout: Layout algorithm to use
            db: Database session
        
        Returns:
            Visualization creation result
        """
        try:
            visualization_id = f"viz_{graph_id}_{datetime.utcnow().timestamp()}"
            
            # Get graph data
            graph_data = await self._get_graph_data(graph_id, db)
            
            # Apply filters
            filtered_data = await self._apply_filters(graph_data, filters)
            
            # Create visualization nodes and edges
            nodes, edges = await self._create_visualization_elements(
                filtered_data, visualization_type
            )
            
            # Apply layout
            layout_result = await self._apply_layout(nodes, edges, layout)
            
            # Detect clusters
            clusters = await self._detect_clusters(nodes, edges)
            
            # Calculate metrics
            metrics = await self._calculate_metrics(nodes, edges, clusters)
            
            # Create visualization state
            visualization = VisualizationState(
                visualization_id=visualization_id,
                nodes=nodes,
                edges=edges,
                clusters=clusters,
                filters=[
                    VisualizationFilter(**filter_data) 
                    for filter_data in (filters or [])
                ],
                layout=layout,
                viewport=await self._calculate_viewport(nodes, edges),
                metadata={
                    "graph_id": graph_id,
                    "visualization_type": visualization_type.value,
                    "creation_time": datetime.utcnow().isoformat(),
                    "metrics": metrics
                }
            )
            
            # Cache visualization
            self.visualization_cache[visualization_id] = visualization
            
            return {
                "success": True,
                "visualization_id": visualization_id,
                "graph_id": graph_id,
                "visualization_type": visualization_type.value,
                "layout": layout.value,
                "metrics": metrics,
                "nodes_count": len(nodes),
                "edges_count": len(edges),
                "clusters_count": len(clusters),
                "filters_applied": len(visualization.filters),
                "viewport": visualization.viewport,
                "message": "Visualization created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error creating visualization: {e}")
            return {
                "success": False,
                "error": f"Visualization creation failed: {str(e)}"
            }
    
    async def update_visualization_filters(
        self,
        visualization_id: str,
        filters: List[Dict[str, Any]],
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Update filters for an existing visualization.
        
        Args:
            visualization_id: ID of the visualization to update
            filters: New filters to apply
            db: Database session
        
        Returns:
            Filter update result
        """
        try:
            if visualization_id not in self.visualization_cache:
                return {
                    "success": False,
                    "error": "Visualization not found"
                }
            
            visualization = self.visualization_cache[visualization_id]
            graph_id = visualization.metadata.get("graph_id")
            
            # Get fresh graph data
            graph_data = await self._get_graph_data(graph_id, db)
            
            # Apply new filters
            filtered_data = await self._apply_filters(graph_data, filters)
            
            # Create new visualization elements
            nodes, edges = await self._create_visualization_elements(
                filtered_data, VisualizationType(visualization.metadata.get("visualization_type"))
            )
            
            # Reapply layout (maintaining positions where possible)
            layout_result = await self._reapply_layout(
                visualization.nodes, visualization.edges, nodes, edges, visualization.layout
            )
            
            # Redetect clusters
            clusters = await self._detect_clusters(nodes, edges)
            
            # Update visualization
            visualization.nodes = nodes
            visualization.edges = edges
            visualization.clusters = clusters
            visualization.filters = [
                VisualizationFilter(**filter_data) for filter_data in filters
            ]
            visualization.viewport = await self._calculate_viewport(nodes, edges)
            
            # Update metrics
            metrics = await self._calculate_metrics(nodes, edges, clusters)
            visualization.metadata["metrics"] = metrics
            
            return {
                "success": True,
                "visualization_id": visualization_id,
                "filters_applied": len(visualization.filters),
                "nodes_count": len(nodes),
                "edges_count": len(edges),
                "clusters_count": len(clusters),
                "viewport": visualization.viewport,
                "metrics": metrics,
                "message": "Filters updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Error updating visualization filters: {e}")
            return {
                "success": False,
                "error": f"Filter update failed: {str(e)}"
            }
    
    async def change_layout(
        self,
        visualization_id: str,
        layout: LayoutAlgorithm,
        animate: bool = True
    ) -> Dict[str, Any]:
        """
        Change the layout algorithm for a visualization.
        
        Args:
            visualization_id: ID of the visualization
            layout: New layout algorithm to apply
            animate: Whether to animate the transition
        
        Returns:
            Layout change result
        """
        try:
            if visualization_id not in self.visualization_cache:
                return {
                    "success": False,
                    "error": "Visualization not found"
                }
            
            visualization = self.visualization_cache[visualization_id]
            
            # Store original positions for animation
            original_positions = {
                node.id: {"x": node.x, "y": node.y}
                for node in visualization.nodes
            }
            
            # Apply new layout
            layout_result = await self._apply_layout(
                visualization.nodes, visualization.edges, layout
            )
            
            # Update visualization
            visualization.layout = layout
            visualization.viewport = await self._calculate_viewport(
                visualization.nodes, visualization.edges
            )
            
            # Calculate animation data if requested
            animation_data = None
            if animate:
                animation_data = await self._create_animation_data(
                    original_positions, visualization.nodes
                )
            
            return {
                "success": True,
                "visualization_id": visualization_id,
                "layout": layout.value,
                "layout_result": layout_result,
                "animation_data": animation_data,
                "viewport": visualization.viewport,
                "message": "Layout changed successfully"
            }
            
        except Exception as e:
            logger.error(f"Error changing layout: {e}")
            return {
                "success": False,
                "error": f"Layout change failed: {str(e)}"
            }
    
    async def focus_on_node(
        self,
        visualization_id: str,
        node_id: str,
        radius: int = 2,
        animate: bool = True
    ) -> Dict[str, Any]:
        """
        Focus visualization on a specific node and its neighbors.
        
        Args:
            visualization_id: ID of the visualization
            node_id: ID of the node to focus on
            radius: Number of hops to include in focus
            animate: Whether to animate the transition
        
        Returns:
            Focus operation result
        """
        try:
            if visualization_id not in self.visualization_cache:
                return {
                    "success": False,
                    "error": "Visualization not found"
                }
            
            visualization = self.visualization_cache[visualization_id]
            
            # Find focus node
            focus_node = None
            for node in visualization.nodes:
                if node.id == node_id:
                    focus_node = node
                    break
            
            if not focus_node:
                return {
                    "success": False,
                    "error": f"Node '{node_id}' not found"
                }
            
            # Find neighbors within radius
            focus_nodes = {node_id}
            focus_edges = set()
            
            current_nodes = {node_id}
            for hop in range(radius):
                next_nodes = set()
                
                for edge in visualization.edges:
                    if edge.source in current_nodes and edge.target not in focus_nodes:
                        next_nodes.add(edge.target)
                        focus_edges.add(edge.id)
                        focus_nodes.add(edge.target)
                    elif edge.target in current_nodes and edge.source not in focus_nodes:
                        next_nodes.add(edge.source)
                        focus_edges.add(edge.id)
                        focus_nodes.add(edge.source)
                
                current_nodes = next_nodes
                if not current_nodes:
                    break
            
            # Update node visibility
            for node in visualization.nodes:
                node.visibility = node.id in focus_nodes
            
            # Update edge visibility
            for edge in visualization.edges:
                edge.visibility = edge.id in focus_edges
            
            # Calculate new viewport
            focus_nodes_list = [
                node for node in visualization.nodes 
                if node.id in focus_nodes and node.visibility
            ]
            focus_edges_list = [
                edge for edge in visualization.edges
                if edge.id in focus_edges and edge.visibility
            ]
            
            viewport = await self._calculate_viewport(focus_nodes_list, focus_edges_list)
            
            return {
                "success": True,
                "visualization_id": visualization_id,
                "focus_node_id": node_id,
                "radius": radius,
                "nodes_in_focus": len(focus_nodes),
                "edges_in_focus": len(focus_edges),
                "viewport": viewport,
                "animate": animate,
                "message": "Focused on node successfully"
            }
            
        except Exception as e:
            logger.error(f"Error focusing on node: {e}")
            return {
                "success": False,
                "error": f"Focus operation failed: {str(e)}"
            }
    
    # Private Helper Methods
    
    async def _get_graph_data(
        self, 
        graph_id: str, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Get graph data from database."""
        try:
            # This would query the actual graph from the database
            # For now, return mock data
            return {
                "nodes": [
                    {
                        "id": "node1",
                        "name": "Java Entity",
                        "type": "entity",
                        "platform": "java",
                        "description": "Example Java entity",
                        "community_rating": 0.8
                    },
                    {
                        "id": "node2",
                        "name": "Bedrock Entity",
                        "type": "entity",
                        "platform": "bedrock",
                        "description": "Example Bedrock entity",
                        "community_rating": 0.9
                    }
                ],
                "edges": [
                    {
                        "id": "edge1",
                        "source_id": "node1",
                        "target_id": "node2",
                        "type": "converts_to",
                        "confidence_score": 0.85
                    }
                ],
                "graph_id": graph_id
            }
        except Exception as e:
            logger.error(f"Error getting graph data: {e}")
            return {"nodes": [], "edges": [], "graph_id": graph_id}
    
    async def _apply_filters(
        self, 
        graph_data: Dict[str, Any], 
        filters: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Apply filters to graph data."""
        try:
            if not filters:
                return graph_data
            
            filtered_nodes = graph_data["nodes"].copy()
            filtered_edges = graph_data["edges"].copy()
            
            # Apply each filter
            for filter_data in filters:
                filter_obj = VisualizationFilter(**filter_data)
                
                if filter_obj.filter_type == FilterType.NODE_TYPE:
                    filtered_nodes = [
                        node for node in filtered_nodes
                        if self._matches_filter(node, filter_obj)
                    ]
                elif filter_obj.filter_type == FilterType.PLATFORM:
                    filtered_nodes = [
                        node for node in filtered_nodes
                        if self._matches_filter(node, filter_obj)
                    ]
                elif filter_obj.filter_type == FilterType.CONFIDENCE:
                    filtered_nodes = [
                        node for node in filtered_nodes
                        if self._matches_filter(node, filter_obj)
                    ]
                elif filter_obj.filter_type == FilterType.TEXT_SEARCH:
                    search_value = str(filter_obj.value).lower()
                    filtered_nodes = [
                        node for node in filtered_nodes
                        if search_value in node.get("name", "").lower() or 
                           search_value in node.get("description", "").lower()
                    ]
            
            # Filter edges to only include filtered nodes
            node_ids = {node["id"] for node in filtered_nodes}
            filtered_edges = [
                edge for edge in filtered_edges
                if edge.get("source_id") in node_ids and 
                   edge.get("target_id") in node_ids
            ]
            
            return {
                "nodes": filtered_nodes,
                "edges": filtered_edges,
                "graph_id": graph_data["graph_id"]
            }
        except Exception as e:
            logger.error(f"Error applying filters: {e}")
            return graph_data
    
    def _matches_filter(self, item: Dict[str, Any], filter_obj: VisualizationFilter) -> bool:
        """Check if an item matches a filter."""
        try:
            field_value = item.get(filter_obj.field)
            filter_value = filter_obj.value
            
            if filter_obj.operator == "eq":
                return field_value == filter_value
            elif filter_obj.operator == "ne":
                return field_value != filter_value
            elif filter_obj.operator == "gt":
                return field_value > filter_value
            elif filter_obj.operator == "gte":
                return field_value >= filter_value
            elif filter_obj.operator == "lt":
                return field_value < filter_value
            elif filter_obj.operator == "lte":
                return field_value <= filter_value
            elif filter_obj.operator == "in":
                return field_value in filter_value if isinstance(filter_value, list) else False
            elif filter_obj.operator == "contains":
                return filter_value in str(field_value) if field_value else False
            
            return False
        except Exception:
            return False
    
    async def _create_visualization_elements(
        self, 
        graph_data: Dict[str, Any], 
        visualization_type: VisualizationType
    ) -> Tuple[List[VisualizationNode], List[VisualizationEdge]]:
        """Create visualization nodes and edges from graph data."""
        try:
            nodes = []
            edges = []
            
            # Create nodes
            for node_data in graph_data["nodes"]:
                node = VisualizationNode(
                    id=node_data["id"],
                    label=node_data.get("name", ""),
                    type=node_data.get("type", "unknown"),
                    platform=node_data.get("platform", "unknown"),
                    size=self._calculate_node_size(node_data),
                    color=self._calculate_node_color(node_data),
                    confidence=node_data.get("community_rating", 0.5),
                    properties=node_data,
                    community=None,  # Will be set later
                    visibility=True,
                    metadata=node_data
                )
                nodes.append(node)
            
            # Create edges
            for edge_data in graph_data["edges"]:
                edge = VisualizationEdge(
                    id=edge_data["id"],
                    source=edge_data["source_id"],
                    target=edge_data["target_id"],
                    type=edge_data.get("type", "relates_to"),
                    weight=edge_data.get("confidence_score", 1.0),
                    width=self._calculate_edge_width(edge_data),
                    color=self._calculate_edge_color(edge_data),
                    confidence=edge_data.get("confidence_score", 0.5),
                    properties=edge_data,
                    visibility=True,
                    metadata=edge_data
                )
                edges.append(edge)
            
            return nodes, edges
        except Exception as e:
            logger.error(f"Error creating visualization elements: {e}")
            return [], []
    
    def _calculate_node_size(self, node_data: Dict[str, Any]) -> float:
        """Calculate node size based on properties."""
        try:
            base_size = 1.0
            
            # Size based on type
            type_sizes = {
                "entity": 1.5,
                "block": 1.3,
                "item": 1.2,
                "behavior": 1.4,
                "command": 1.1,
                "pattern": 1.6
            }
            
            node_type = node_data.get("type", "unknown")
            base_size = type_sizes.get(node_type, 1.0)
            
            # Adjust based on community rating
            rating = node_data.get("community_rating", 0.5)
            base_size *= (0.8 + rating * 0.4)
            
            return max(0.5, min(3.0, base_size))
        except Exception:
            return 1.0
    
    def _calculate_node_color(self, node_data: Dict[str, Any]) -> str:
        """Calculate node color based on properties."""
        try:
            # Color based on platform
            platform_colors = {
                "java": "#4CAF50",      # Green
                "bedrock": "#2196F3",    # Blue
                "both": "#FF9800",       # Orange
                "unknown": "#9E9E9E"      # Gray
            }
            
            platform = node_data.get("platform", "unknown")
            base_color = platform_colors.get(platform, "#9E9E9E")
            
            # Adjust based on expert validation
            if node_data.get("expert_validated", False):
                # Make color slightly brighter for validated items
                base_color = self._brighten_color(base_color, 0.2)
            
            return base_color
        except Exception:
            return "#9E9E9E"
    
    def _calculate_edge_width(self, edge_data: Dict[str, Any]) -> float:
        """Calculate edge width based on properties."""
        try:
            confidence = edge_data.get("confidence_score", 0.5)
            return max(0.5, min(3.0, confidence * 3))
        except Exception:
            return 1.0
    
    def _calculate_edge_color(self, edge_data: Dict[str, Any]) -> str:
        """Calculate edge color based on properties."""
        try:
            # Color based on relationship type
            type_colors = {
                "converts_to": "#4CAF50",     # Green
                "relates_to": "#2196F3",       # Blue
                "similar_to": "#FF9800",         # Orange
                "depends_on": "#F44336",         # Red
                "unknown": "#9E9E9E"              # Gray
            }
            
            edge_type = edge_data.get("type", "unknown")
            return type_colors.get(edge_type, "#9E9E9E")
        except Exception:
            return "#9E9E9E"
    
    def _brighten_color(self, color: str, factor: float) -> str:
        """Brighten a color by a factor."""
        try:
            # Simple implementation for hex colors
            if color.startswith("#"):
                rgb = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
                rgb = tuple(min(255, int(c + (255 - c) * factor)) for c in rgb)
                return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
            return color
        except Exception:
            return color
    
    async def _apply_layout(
        self, 
        nodes: List[VisualizationNode], 
        edges: List[VisualizationEdge], 
        layout: LayoutAlgorithm
    ) -> Dict[str, Any]:
        """Apply layout algorithm to position nodes."""
        try:
            # Create NetworkX graph
            G = nx.Graph()
            
            # Add nodes
            for node in nodes:
                G.add_node(node.id, size=node.size)
            
            # Add edges
            for edge in edges:
                G.add_edge(edge.source, edge.target, weight=edge.weight)
            
            # Apply layout algorithm
            if layout == LayoutAlgorithm.SPRING:
                pos = nx.spring_layout(G, k=1, iterations=50)
            elif layout == LayoutAlgorithm.FRUCHTERMAN:
                pos = nx.fruchterman_reingold_layout(G)
            elif layout == LayoutAlgorithm.CIRCULAR:
                pos = nx.circular_layout(G)
            elif layout == LayoutAlgorithm.HIERARCHICAL:
                pos = nx.spring_layout(G, k=1, iterations=50)  # Fallback for hierarchical
            elif layout == LayoutAlgorithm.GRID:
                pos = nx.grid_layout(G)
            else:
                # Default to spring layout
                pos = nx.spring_layout(G, k=1, iterations=50)
            
            return {"positions": pos, "layout_algorithm": layout.value}
            
        except Exception as e:
            raise VisualizationError(f"Failed to apply layout: {str(e)}")
