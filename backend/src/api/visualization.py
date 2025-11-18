"""
Advanced Visualization API Endpoints

This module provides REST API endpoints for knowledge graph visualization,
including filtering, layout, clustering, and export capabilities.
"""

import logging
from typing import Dict, List, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import get_db
from src.services.advanced_visualization import (
    AdvancedVisualizationService, VisualizationType, FilterType, 
    LayoutAlgorithm
)

logger = logging.getLogger(__name__)

# Create service instance
advanced_visualization_service = AdvancedVisualizationService()

router = APIRouter()


# Visualization Creation Endpoints

@router.post("/visualizations")
async def create_visualization(
    viz_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Create a new graph visualization."""
    try:
        graph_id = viz_data.get("graph_id")
        viz_type_str = viz_data.get("visualization_type", "force_directed")
        filters = viz_data.get("filters", [])
        layout_str = viz_data.get("layout", "spring")
        
        if not graph_id:
            raise HTTPException(
                status_code=400,
                detail="graph_id is required"
            )
        
        # Parse visualization type
        try:
            viz_type = VisualizationType(viz_type_str)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid visualization_type: {viz_type_str}"
            )
        
        # Parse layout algorithm
        try:
            layout = LayoutAlgorithm(layout_str)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid layout: {layout_str}"
            )
        
        result = await advanced_visualization_service.create_visualization(
            graph_id, viz_type, filters, layout, db
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating visualization: {e}")
        raise HTTPException(status_code=500, detail=f"Visualization creation failed: {str(e)}")


@router.get("/visualizations/{visualization_id}")
async def get_visualization(visualization_id: str):
    """Get details of a specific visualization."""
    try:
        if visualization_id not in advanced_visualization_service.visualization_cache:
            raise HTTPException(
                status_code=404,
                detail="Visualization not found"
            )
        
        viz_state = advanced_visualization_service.visualization_cache[visualization_id]
        
        return {
            "success": True,
            "visualization_id": visualization_id,
            "state": {
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
                        "visibility": node.visibility,
                        "properties": node.properties,
                        "metadata": node.metadata
                    }
                    for node in viz_state.nodes
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
                        "visibility": edge.visibility,
                        "properties": edge.properties,
                        "metadata": edge.metadata
                    }
                    for edge in viz_state.edges
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
                    for cluster in viz_state.clusters
                ],
                "filters": [
                    {
                        "filter_id": f.filter.filter_id,
                        "filter_type": f.filter.filter_type.value,
                        "field": f.filter.field,
                        "operator": f.filter.operator,
                        "value": f.filter.value,
                        "description": f.filter.description,
                        "metadata": f.filter.metadata
                    }
                    for f in viz_state.filters
                ],
                "layout": viz_state.layout.value,
                "viewport": viz_state.viewport,
                "metadata": viz_state.metadata,
                "created_at": viz_state.created_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting visualization: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get visualization: {str(e)}")


@router.post("/visualizations/{visualization_id}/filters")
async def update_visualization_filters(
    visualization_id: str,
    filter_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Update filters for an existing visualization."""
    try:
        filters = filter_data.get("filters", [])
        
        result = await advanced_visualization_service.update_visualization_filters(
            visualization_id, filters, db
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating visualization filters: {e}")
        raise HTTPException(status_code=500, detail=f"Filter update failed: {str(e)}")


@router.post("/visualizations/{visualization_id}/layout")
async def change_visualization_layout(
    visualization_id: str,
    layout_data: Dict[str, Any]
):
    """Change layout algorithm for a visualization."""
    try:
        layout_str = layout_data.get("layout", "spring")
        animate = layout_data.get("animate", True)
        
        # Parse layout algorithm
        try:
            layout = LayoutAlgorithm(layout_str)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid layout: {layout_str}"
            )
        
        result = await advanced_visualization_service.change_layout(
            visualization_id, layout, animate
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing layout: {e}")
        raise HTTPException(status_code=500, detail=f"Layout change failed: {str(e)}")


@router.post("/visualizations/{visualization_id}/focus")
async def focus_on_node(
    visualization_id: str,
    focus_data: Dict[str, Any]
):
    """Focus visualization on a specific node."""
    try:
        node_id = focus_data.get("node_id")
        radius = focus_data.get("radius", 2)
        animate = focus_data.get("animate", True)
        
        if not node_id:
            raise HTTPException(
                status_code=400,
                detail="node_id is required"
            )
        
        result = await advanced_visualization_service.focus_on_node(
            visualization_id, node_id, radius, animate
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error focusing on node: {e}")
        raise HTTPException(status_code=500, detail=f"Focus operation failed: {str(e)}")


# Filter Preset Endpoints

@router.post("/filter-presets")
async def create_filter_preset(preset_data: Dict[str, Any]):
    """Create a reusable filter preset."""
    try:
        preset_name = preset_data.get("preset_name")
        filters = preset_data.get("filters", [])
        description = preset_data.get("description", "")
        
        if not all([preset_name, filters]):
            raise HTTPException(
                status_code=400,
                detail="preset_name and filters are required"
            )
        
        result = await advanced_visualization_service.create_filter_preset(
            preset_name, filters, description
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating filter preset: {e}")
        raise HTTPException(status_code=500, detail=f"Preset creation failed: {str(e)}")


@router.get("/filter-presets")
async def get_filter_presets():
    """Get all available filter presets."""
    try:
        presets = []
        
        for preset_name, filters in advanced_visualization_service.filter_presets.items():
            presets.append({
                "name": preset_name,
                "filters_count": len(filters),
                "filters": [
                    {
                        "filter_id": f.filter.filter_id,
                        "filter_type": f.filter.filter_type.value,
                        "field": f.filter.field,
                        "operator": f.filter.operator,
                        "value": f.filter.value,
                        "description": f.filter.description
                    }
                    for f in filters
                ]
            })
        
        return {
            "success": True,
            "presets": presets,
            "total_presets": len(presets)
        }
        
    except Exception as e:
        logger.error(f"Error getting filter presets: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get presets: {str(e)}")


@router.get("/filter-presets/{preset_name}")
async def get_filter_preset(preset_name: str):
    """Get details of a specific filter preset."""
    try:
        if preset_name not in advanced_visualization_service.filter_presets:
            raise HTTPException(
                status_code=404,
                detail="Filter preset not found"
            )
        
        filters = advanced_visualization_service.filter_presets[preset_name]
        
        return {
            "success": True,
            "preset_name": preset_name,
            "filters": [
                {
                    "filter_id": f.filter.filter_id,
                    "filter_type": f.filter.filter_type.value,
                    "field": f.filter.field,
                    "operator": f.filter.operator,
                    "value": f.filter.value,
                    "description": f.filter.description,
                    "metadata": f.filter.metadata
                }
                for f in filters
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting filter preset: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get preset: {str(e)}")


# Export Endpoints

@router.post("/visualizations/{visualization_id}/export")
async def export_visualization(
    visualization_id: str,
    export_data: Dict[str, Any]
):
    """Export visualization data in specified format."""
    try:
        format_type = export_data.get("format", "json")
        include_metadata = export_data.get("include_metadata", True)
        
        result = await advanced_visualization_service.export_visualization(
            visualization_id, format_type, include_metadata
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting visualization: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


# Metrics Endpoints

@router.get("/visualizations/{visualization_id}/metrics")
async def get_visualization_metrics(visualization_id: str):
    """Get detailed metrics for a visualization."""
    try:
        result = await advanced_visualization_service.get_visualization_metrics(visualization_id)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting visualization metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Metrics calculation failed: {str(e)}")


# Utility Endpoints

@router.get("/visualization-types")
async def get_visualization_types():
    """Get available visualization types."""
    try:
        types = []
        
        for viz_type in VisualizationType:
            types.append({
                "value": viz_type.value,
                "name": viz_type.value.replace("_", " ").title(),
                "description": f"{viz_type.value.replace('_', ' ').title()} visualization layout"
            })
        
        return {
            "success": True,
            "visualization_types": types,
            "total_types": len(types)
        }
        
    except Exception as e:
        logger.error(f"Error getting visualization types: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get types: {str(e)}")


@router.get("/layout-algorithms")
async def get_layout_algorithms():
    """Get available layout algorithms."""
    try:
        algorithms = []
        
        for layout in LayoutAlgorithm:
            algorithms.append({
                "value": layout.value,
                "name": layout.value.replace("_", " ").title(),
                "description": f"{layout.value.replace('_', ' ').title()} layout algorithm",
                "suitable_for": self._get_layout_suitability(layout)
            })
        
        return {
            "success": True,
            "layout_algorithms": algorithms,
            "total_algorithms": len(algorithms)
        }
        
    except Exception as e:
        logger.error(f"Error getting layout algorithms: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get algorithms: {str(e)}")


@router.get("/filter-types")
async def get_filter_types():
    """Get available filter types."""
    try:
        types = []
        
        for filter_type in FilterType:
            types.append({
                "value": filter_type.value,
                "name": filter_type.value.replace("_", " ").title(),
                "description": f"{filter_type.value.replace('_', ' ').title()} filter",
                "operators": self._get_filter_operators(filter_type),
                "fields": self._get_filter_fields(filter_type)
            })
        
        return {
            "success": True,
            "filter_types": types,
            "total_types": len(types)
        }
        
    except Exception as e:
        logger.error(f"Error getting filter types: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get filter types: {str(e)}")


@router.get("/visualizations/active")
async def get_active_visualizations():
    """Get list of active visualizations."""
    try:
        visualizations = []
        
        for viz_id, viz_state in advanced_visualization_service.visualization_cache.items():
            visualizations.append({
                "visualization_id": viz_id,
                "graph_id": viz_state.metadata.get("graph_id"),
                "visualization_type": viz_state.metadata.get("visualization_type"),
                "layout": viz_state.layout.value,
                "nodes_count": len(viz_state.nodes),
                "edges_count": len(viz_state.edges),
                "clusters_count": len(viz_state.clusters),
                "filters_applied": len(viz_state.filters),
                "created_at": viz_state.created_at.isoformat(),
                "last_updated": viz_state.metadata.get("last_updated", viz_state.created_at.isoformat())
            })
        
        # Sort by creation date (newest first)
        visualizations.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "success": True,
            "visualizations": visualizations,
            "total_visualizations": len(visualizations)
        }
        
    except Exception as e:
        logger.error(f"Error getting active visualizations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get visualizations: {str(e)}")


@router.delete("/visualizations/{visualization_id}")
async def delete_visualization(visualization_id: str):
    """Delete a visualization and clean up resources."""
    try:
        if visualization_id not in advanced_visualization_service.visualization_cache:
            raise HTTPException(
                status_code=404,
                detail="Visualization not found"
            )
        
        # Remove from cache
        del advanced_visualization_service.visualization_cache[visualization_id]
        
        # Clean up any related caches
        if visualization_id in advanced_visualization_service.layout_cache:
            del advanced_visualization_service.layout_cache[visualization_id]
        
        if visualization_id in advanced_visualization_service.cluster_cache:
            del advanced_visualization_service.cluster_cache[visualization_id]
        
        return {
            "success": True,
            "visualization_id": visualization_id,
            "message": "Visualization deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting visualization: {e}")
        raise HTTPException(status_code=500, detail=f"Visualization deletion failed: {str(e)}")


@router.get("/performance-stats")
async def get_performance_stats():
    """Get performance statistics for the visualization service."""
    try:
        active_viz_count = len(advanced_visualization_service.visualization_cache)
        cached_layouts = len(advanced_visualization_service.layout_cache)
        cached_clusters = len(advanced_visualization_service.cluster_cache)
        filter_presets = len(advanced_visualization_service.filter_presets)
        
        # Calculate average nodes and edges
        total_nodes = sum(
            len(viz.nodes) 
            for viz in advanced_visualization_service.visualization_cache.values()
        )
        total_edges = sum(
            len(viz.edges) 
            for viz in advanced_visualization_service.visualization_cache.values()
        )
        
        avg_nodes = total_nodes / active_viz_count if active_viz_count > 0 else 0
        avg_edges = total_edges / active_viz_count if active_viz_count > 0 else 0
        
        return {
            "success": True,
            "stats": {
                "active_visualizations": active_viz_count,
                "cached_layouts": cached_layouts,
                "cached_clusters": cached_clusters,
                "filter_presets": filter_presets,
                "total_nodes": total_nodes,
                "total_edges": total_edges,
                "average_nodes_per_visualization": avg_nodes,
                "average_edges_per_visualization": avg_edges,
                "memory_usage_mb": self._estimate_memory_usage(),
                "cache_hit_ratio": self._calculate_cache_hit_ratio()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting performance stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


# Private Helper Methods

def _get_layout_suitability(layout: LayoutAlgorithm) -> List[str]:
    """Get suitable use cases for a layout algorithm."""
    suitability = {
        LayoutAlgorithm.SPRING: ["General purpose", "Moderate size graphs", "Force-directed layout"],
        LayoutAlgorithm.FRUCHTERMAN: ["Large graphs", "Physics simulation", "Energy minimization"],
        LayoutAlgorithm.CIRCULAR: ["Social networks", "Cyclical relationships", "Community visualization"],
        LayoutAlgorithm.HIERARCHICAL: ["Organizational charts", "Dependency graphs", "Process flows"],
        LayoutAlgorithm.GRID: ["Regular structures", "Matrix-style data", "Tabular relationships"]
    }
    return suitability.get(layout, ["General use"])
