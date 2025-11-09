"""
Advanced Visualization Service for Knowledge Graph

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

from ..db.crud import get_async_session
from ..db.knowledge_graph_crud import (
    KnowledgeNodeCRUD, KnowledgeRelationshipCRUD, ConversionPatternCRUD
)
from ..models import (
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


@dataclass
class VisualizationMetrics:
    """Metrics for visualization performance."""
    total_nodes: int = 0
    total_edges: int = 0
    total_clusters: int = 0
    filtered_nodes: int = 0
    filtered_edges: int = 0
    density: float = 0.0
    average_degree: float = 0.0
    clustering_coefficient: float = 0.0
    path_length: float = 0.0
    centrality: Dict[str, float] = field(default_factory=dict)
    rendering_time: float = 0.0
    memory_usage: float = 0.0


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
            visualization_type: Type of visualization
            filters: List of filters to apply
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
            visualization_id: ID of the visualization
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
            layout: New layout algorithm
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
            node_id: ID of node to focus on
            radius: Number of hops to include
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
    
    async def create_filter_preset(
        self,
        preset_name: str,
        filters: List[Dict[str, Any]],
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Create a reusable filter preset.
        
        Args:
            preset_name: Name of the preset
            filters: Filters to include in preset
            description: Description of the preset
        
        Returns:
            Preset creation result
        """
        try:
            # Validate filters
            visualization_filters = []
            for filter_data in filters:
                try:
                    viz_filter = VisualizationFilter(**filter_data)
                    visualization_filters.append(viz_filter)
                except Exception as e:
                    logger.warning(f"Invalid filter data: {e}")
                    continue
            
            if not visualization_filters:
                return {
                    "success": False,
                    "error": "No valid filters provided"
                }
            
            # Store preset
            self.filter_presets[preset_name] = visualization_filters
            
            return {
                "success": True,
                "preset_name": preset_name,
                "filters_count": len(visualization_filters),
                "description": description,
                "filters": [
                    {
                        "filter_id": f.filter.filter_id,
                        "filter_type": f.filter.filter_type.value,
                        "field": f.filter.field,
                        "operator": f.filter.operator,
                        "value": f.filter.value,
                        "description": f.filter.description
                    }
                    for f in visualization_filters
                ],
                "message": "Filter preset created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error creating filter preset: {e}")
            return {
                "success": False,
                "error": f"Preset creation failed: {str(e)}"
            }
    
    async def export_visualization(
        self,
        visualization_id: str,
        format: str = "json",
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Export visualization data in specified format.
        
        Args:
            visualization_id: ID of the visualization
            format: Export format (json, gexf, graphml, csv)
            include_metadata: Whether to include metadata
        
        Returns:
            Export result
        """
        try:
            if visualization_id not in self.visualization_cache:
                return {
                    "success": False,
                    "error": "Visualization not found"
                }
            
            visualization = self.visualization_cache[visualization_id]
            
            # Prepare export data
            export_data = {
                "visualization_id": visualization_id,
                "nodes": [
                    {
                        "id": node.id,
                        "label": node.label,
                        "type": node.type,
                        "platform": node.platform,
                        "x": node.x,
                        "y": node.y,
                        "size": node.size,
                        "color": node.color,
                        "community": node.community,
                        "confidence": node.confidence,
                        "properties": node.properties,
                        "metadata": node.metadata
                    }
                    for node in visualization.nodes
                ],
                "edges": [
                    {
                        "id": edge.id,
                        "source": edge.source,
                        "target": edge.target,
                        "type": edge.type,
                        "weight": edge.weight,
                        "color": edge.color,
                        "width": edge.width,
                        "confidence": edge.confidence,
                        "properties": edge.properties,
                        "metadata": edge.metadata
                    }
                    for edge in visualization.edges
                ],
                "clusters": [
                    {
                        "cluster_id": cluster.cluster_id,
                        "name": cluster.name,
                        "nodes": cluster.nodes,
                        "edges": cluster.edges,
                        "color": cluster.color,
                        "size": cluster.size,
                        "density": cluster.density,
                        "centrality": cluster.centrality,
                        "properties": cluster.properties
                    }
                    for cluster in visualization.clusters
                ]
            }
            
            # Add metadata if requested
            if include_metadata:
                export_data.update({
                    "metadata": visualization.metadata,
                    "filters": [
                        {
                            "filter_id": f.filter.filter_id,
                            "filter_type": f.filter.filter_type.value,
                            "field": f.filter.field,
                            "operator": f.filter.operator,
                            "value": f.filter.value,
                            "description": f.filter.description
                        }
                        for f in visualization.filters
                    ],
                    "layout": visualization.layout.value,
                    "viewport": visualization.viewport,
                    "exported_at": datetime.utcnow().isoformat()
                })
            
            # Convert to requested format
            if format.lower() == "json":
                export_content = json.dumps(export_data, indent=2)
                content_type = "application/json"
            elif format.lower() == "csv":
                export_content = await self._convert_to_csv(export_data)
                content_type = "text/csv"
            elif format.lower() == "gexf":
                export_content = await self._convert_to_gexf(export_data)
                content_type = "application/gexf+xml"
            elif format.lower() == "graphml":
                export_content = await self._convert_to_graphml(export_data)
                content_type = "application/xml"
            else:
                return {
                    "success": False,
                    "error": f"Unsupported export format: {format}"
                }
            
            return {
                "success": True,
                "format": format,
                "content_type": content_type,
                "content": export_content,
                "nodes_count": len(visualization.nodes),
                "edges_count": len(visualization.edges),
                "file_size": len(export_content),
                "message": f"Visualization exported as {format}"
            }
            
        except Exception as e:
            logger.error(f"Error exporting visualization: {e}")
            return {
                "success": False,
                "error": f"Export failed: {str(e)}"
            }
    
    async def get_visualization_metrics(
        self,
        visualization_id: str
    ) -> Dict[str, Any]:
        """
        Get detailed metrics for a visualization.
        
        Args:
            visualization_id: ID of the visualization
        
        Returns:
            Visualization metrics
        """
        try:
            if visualization_id not in self.visualization_cache:
                return {
                    "success": False,
                    "error": "Visualization not found"
                }
            
            visualization = self.visualization_cache[visualization_id]
            
            # Calculate comprehensive metrics
            metrics = await self._calculate_comprehensive_metrics(
                visualization.nodes, visualization.edges, visualization.clusters
            )
            
            # Get performance metrics
            performance_metrics = await self._get_performance_metrics(visualization_id)
            
            return {
                "success": True,
                "visualization_id": visualization_id,
                "basic_metrics": {
                    "total_nodes": len(visualization.nodes),
                    "total_edges": len(visualization.edges),
                    "total_clusters": len(visualization.clusters),
                    "visible_nodes": sum(1 for node in visualization.nodes if node.visibility),
                    "visible_edges": sum(1 for edge in visualization.edges if edge.visibility)
                },
                "graph_metrics": metrics,
                "performance_metrics": performance_metrics,
                "visualization_metadata": visualization.metadata,
                "calculated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting visualization metrics: {e}")
            return {
                "success": False,
                "error": f"Metrics calculation failed: {str(e)}"
            }
    
    # Private Helper Methods
    
    async def _get_graph_data(
        self, 
        graph_id: str, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Get graph data from database."""
        try:
            # This would query the actual graph from database
            # For now, return mock data
            
            nodes = []
            edges = []
            patterns = []
            
            if db:
                # Get nodes
                db_nodes = await KnowledgeNodeCRUD.get_all(db, limit=1000)
                for node in db_nodes:
                    nodes.append({
                        "id": str(node.id),
                        "name": node.name,
                        "type": node.node_type,
                        "platform": node.platform,
                        "description": node.description,
                        "minecraft_version": node.minecraft_version,
                        "expert_validated": node.expert_validated,
                        "community_rating": node.community_rating,
                        "properties": json.loads(node.properties or "{}")
                    })
                
                # Get relationships
                db_relationships = await KnowledgeRelationshipCRUD.get_all(db, limit=2000)
                for rel in db_relationships:
                    edges.append({
                        "id": str(rel.id),
                        "source_id": rel.source_node_id,
                        "target_id": rel.target_node_id,
                        "type": rel.relationship_type,
                        "confidence_score": rel.confidence_score,
                        "properties": json.loads(rel.properties or "{}")
                    })
                
                # Get patterns
                db_patterns = await ConversionPatternCRUD.get_all(db, limit=500)
                for pattern in db_patterns:
                    patterns.append({
                        "id": str(pattern.id),
                        "java_concept": pattern.java_concept,
                        "bedrock_concept": pattern.bedrock_concept,
                        "pattern_type": pattern.pattern_type,
                        "success_rate": pattern.success_rate,
                        "minecraft_version": pattern.minecraft_version,
                        "conversion_features": json.loads(pattern.conversion_features or "{}")
                    })
            
            return {
                "nodes": nodes,
                "edges": edges,
                "patterns": patterns,
                "graph_id": graph_id
            }
            
        except Exception as e:
            logger.error(f"Error getting graph data: {e}")
            return {"nodes": [], "edges": [], "patterns": []}
    
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
                    filtered_edges = [
                        edge for edge in filtered_edges
                        if self._matches_filter(edge, filter_obj)
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
                "patterns": graph_data["patterns"],
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
                    properties=node_data.get("properties", {}),
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
                    properties=edge_data.get("properties", {}),
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
            
            # Adjust based on connections (would need edge data)
            # For now, use community rating
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
                "relates_to": "#2196F3",     # Blue
                "similar_to": "#FF9800",       # Orange
                "depends_on": "#F44336",       # Red
                "unknown": "#9E9E9E"          # Gray
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
            if layout == LayoutAlgorithm.SPRING:
                return await self._spring_layout(nodes, edges)
            elif layout == LayoutAlgorithm.FRUchte
