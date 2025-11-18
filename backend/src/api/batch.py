"""
Batch Processing API Endpoints

This module provides REST API endpoints for large graph batch operations,
including job submission, progress tracking, and job management.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import get_db
from src.services.batch_processing import (
    batch_processing_service, BatchOperationType, ProcessingMode
)

logger = logging.getLogger(__name__)

router = APIRouter()


# Job Management Endpoints

@router.post("/batch/jobs")
async def submit_batch_job(
    job_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Submit a new batch job."""
    try:
        operation_type_str = job_data.get("operation_type")
        parameters = job_data.get("parameters", {})
        processing_mode_str = job_data.get("processing_mode", "sequential")
        chunk_size = job_data.get("chunk_size", 100)
        parallel_workers = job_data.get("parallel_workers", 4)

        if not operation_type_str:
            raise HTTPException(
                status_code=400,
                detail="operation_type is required"
            )

        # Parse operation type
        try:
            operation_type = BatchOperationType(operation_type_str)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid operation_type: {operation_type_str}"
            )

        # Parse processing mode
        try:
            processing_mode = ProcessingMode(processing_mode_str)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid processing_mode: {processing_mode_str}"
            )

        result = await batch_processing_service.submit_batch_job(
            operation_type, parameters, processing_mode, chunk_size, parallel_workers, db
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting batch job: {e}")
        raise HTTPException(status_code=500, detail=f"Job submission failed: {str(e)}")


@router.get("/batch/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get status and progress of a batch job."""
    try:
        result = await batch_processing_service.get_job_status(job_id)

        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")


@router.post("/batch/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    cancel_data: Dict[str, Any] = None
):
    """Cancel a running batch job."""
    try:
        reason = cancel_data.get("reason", "User requested cancellation") if cancel_data else "User requested cancellation"

        result = await batch_processing_service.cancel_job(job_id, reason)

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job: {e}")
        raise HTTPException(status_code=500, detail=f"Job cancellation failed: {str(e)}")


@router.post("/batch/jobs/{job_id}/pause")
async def pause_job(
    job_id: str,
    pause_data: Dict[str, Any] = None
):
    """Pause a running batch job."""
    try:
        reason = pause_data.get("reason", "User requested pause") if pause_data else "User requested pause"

        result = await batch_processing_service.pause_job(job_id, reason)

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing job: {e}")
        raise HTTPException(status_code=500, detail=f"Job pause failed: {str(e)}")


@router.post("/batch/jobs/{job_id}/resume")
async def resume_job(job_id: str):
    """Resume a paused batch job."""
    try:
        result = await batch_processing_service.resume_job(job_id)

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming job: {e}")
        raise HTTPException(status_code=500, detail=f"Job resume failed: {str(e)}")


@router.get("/batch/jobs")
async def get_active_jobs():
    """Get list of all active batch jobs."""
    try:
        result = await batch_processing_service.get_active_jobs()

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting active jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get active jobs: {str(e)}")


@router.get("/batch/jobs/history")
async def get_job_history(
    limit: int = Query(50, le=1000, description="Maximum number of jobs to return"),
    operation_type: Optional[str] = Query(None, description="Filter by operation type")
):
    """Get history of completed batch jobs."""
    try:
        # Parse operation type filter
        op_type = None
        if operation_type:
            try:
                op_type = BatchOperationType(operation_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid operation_type: {operation_type}"
                )

        result = await batch_processing_service.get_job_history(limit, op_type)

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get job history: {str(e)}")


# Import/Export Endpoints

@router.post("/batch/import/nodes")
async def import_nodes(
    file: UploadFile = File(...),
    processing_mode: str = Query("sequential", description="Processing mode"),
    chunk_size: int = Query(100, le=1000, description="Chunk size"),
    parallel_workers: int = Query(4, le=10, description="Parallel workers"),
    db: AsyncSession = Depends(get_db)
):
    """Import nodes from uploaded file."""
    try:
        # Parse processing mode
        try:
            mode = ProcessingMode(processing_mode)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid processing_mode: {processing_mode}"
            )

        # Read and parse file content
        content = await file.read()

        try:
            if file.filename.endswith('.json'):
                nodes_data = json.loads(content.decode())
            elif file.filename.endswith('.csv'):
                # Parse CSV
                nodes_data = await _parse_csv_nodes(content.decode())
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Unsupported file format. Use JSON or CSV."
                )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to parse file: {str(e)}"
            )

        # Submit batch job
        parameters = {
            "nodes": nodes_data,
            "source_file": file.filename,
            "file_size": len(content)
        }

        result = await batch_processing_service.submit_batch_job(
            BatchOperationType.IMPORT_NODES, parameters, mode,
            chunk_size, parallel_workers, db
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "success": True,
            "message": f"Import job submitted for {file.filename}",
            "job_id": result["job_id"],
            "estimated_total_items": result["estimated_total_items"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing nodes: {e}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/batch/import/relationships")
async def import_relationships(
    file: UploadFile = File(...),
    processing_mode: str = Query("sequential", description="Processing mode"),
    chunk_size: int = Query(100, le=1000, description="Chunk size"),
    parallel_workers: int = Query(4, le=10, description="Parallel workers"),
    db: AsyncSession = Depends(get_db)
):
    """Import relationships from uploaded file."""
    try:
        # Parse processing mode
        try:
            mode = ProcessingMode(processing_mode)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid processing_mode: {processing_mode}"
            )

        # Read and parse file content
        content = await file.read()

        try:
            if file.filename.endswith('.json'):
                relationships_data = json.loads(content.decode())
            elif file.filename.endswith('.csv'):
                # Parse CSV
                relationships_data = await _parse_csv_relationships(content.decode())
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Unsupported file format. Use JSON or CSV."
                )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to parse file: {str(e)}"
            )

        # Submit batch job
        parameters = {
            "relationships": relationships_data,
            "source_file": file.filename,
            "file_size": len(content)
        }

        result = await batch_processing_service.submit_batch_job(
            BatchOperationType.IMPORT_RELATIONSHIPS, parameters, mode,
            chunk_size, parallel_workers, db
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "success": True,
            "message": f"Import job submitted for {file.filename}",
            "job_id": result["job_id"],
            "estimated_total_items": result["estimated_total_items"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing relationships: {e}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/batch/export/graph")
async def export_graph(
    export_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Export knowledge graph to specified format."""
    try:
        format_type = export_data.get("format", "json")
        filters = export_data.get("filters", {})
        include_relationships = export_data.get("include_relationships", True)
        include_patterns = export_data.get("include_patterns", True)
        processing_mode = export_data.get("processing_mode", "sequential")
        chunk_size = export_data.get("chunk_size", 100)
        parallel_workers = export_data.get("parallel_workers", 4)

        # Validate format
        if format_type not in ["json", "csv", "gexf", "graphml"]:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format: {format_type}"
            )

        # Parse processing mode
        try:
            mode = ProcessingMode(processing_mode)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid processing_mode: {processing_mode}"
            )

        # Submit batch job
        parameters = {
            "format": format_type,
            "filters": filters,
            "include_relationships": include_relationships,
            "include_patterns": include_patterns,
            "output_file": f"graph_export_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d_%H%M%S')}.{format_type}"
        }

        result = await batch_processing_service.submit_batch_job(
            BatchOperationType.EXPORT_GRAPH, parameters, mode,
            chunk_size, parallel_workers, db
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "success": True,
            "message": f"Export job submitted in {format_type} format",
            "job_id": result["job_id"],
            "estimated_total_items": result["estimated_total_items"],
            "output_format": format_type
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting graph: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


# Batch Operation Endpoints

@router.post("/batch/delete/nodes")
async def batch_delete_nodes(
    delete_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Batch delete nodes matching criteria."""
    try:
        filters = delete_data.get("filters", {})
        dry_run = delete_data.get("dry_run", False)
        processing_mode = delete_data.get("processing_mode", "sequential")
        chunk_size = delete_data.get("chunk_size", 100)
        parallel_workers = delete_data.get("parallel_workers", 4)

        # Validate filters
        if not filters:
            raise HTTPException(
                status_code=400,
                detail="filters are required for deletion"
            )

        # Parse processing mode
        try:
            mode = ProcessingMode(processing_mode)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid processing_mode: {processing_mode}"
            )

        # Submit batch job
        parameters = {
            "filters": filters,
            "dry_run": dry_run,
            "operation": "batch_delete_nodes"
        }

        result = await batch_processing_service.submit_batch_job(
            BatchOperationType.DELETE_NODES, parameters, mode,
            chunk_size, parallel_workers, db
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "success": True,
            "message": f"Batch delete job submitted (dry_run={dry_run})",
            "job_id": result["job_id"],
            "estimated_total_items": result["estimated_total_items"],
            "dry_run": dry_run
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch delete nodes: {e}")
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.post("/batch/validate/graph")
async def batch_validate_graph(
    validation_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Batch validate knowledge graph integrity."""
    try:
        validation_rules = validation_data.get("rules", ["all"])
        scope = validation_data.get("scope", "full")
        processing_mode = validation_data.get("processing_mode", "parallel")
        chunk_size = validation_data.get("chunk_size", 200)
        parallel_workers = validation_data.get("parallel_workers", 6)

        # Validate rules
        valid_rules = ["nodes", "relationships", "patterns", "consistency", "all"]
        for rule in validation_rules:
            if rule not in valid_rules:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid validation rule: {rule}"
                )

        # Parse processing mode
        try:
            mode = ProcessingMode(processing_mode)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid processing_mode: {processing_mode}"
            )

        # Submit batch job
        parameters = {
            "rules": validation_rules,
            "scope": scope,
            "validation_options": validation_data.get("options", {})
        }

        result = await batch_processing_service.submit_batch_job(
            BatchOperationType.VALIDATE_GRAPH, parameters, mode,
            chunk_size, parallel_workers, db
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "success": True,
            "message": f"Graph validation job submitted with rules: {validation_rules}",
            "job_id": result["job_id"],
            "estimated_total_items": result["estimated_total_items"],
            "validation_rules": validation_rules,
            "scope": scope
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch graph validation: {e}")
        raise HTTPException(status_code=500, detail=f"Validation job failed: {str(e)}")


# Utility Endpoints

@router.get("/batch/operation-types")
async def get_operation_types():
    """Get available batch operation types."""
    try:
        operation_types = []

        for op_type in BatchOperationType:
            operation_types.append({
                "value": op_type.value,
                "name": op_type.value.replace("_", " ").title(),
                "description": _get_operation_description(op_type),
                "requires_file": _operation_requires_file(op_type),
                "estimated_duration": _get_operation_duration(op_type)
            })

        return {
            "success": True,
            "operation_types": operation_types,
            "total_types": len(operation_types)
        }

    except Exception as e:
        logger.error(f"Error getting operation types: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get operation types: {str(e)}")


@router.get("/batch/processing-modes")
async def get_processing_modes():
    """Get available processing modes."""
    try:
        modes = []

        for mode in ProcessingMode:
            modes.append({
                "value": mode.value,
                "name": mode.value.title(),
                "description": _get_processing_mode_description(mode),
                "use_cases": _get_processing_mode_use_cases(mode),
                "recommended_for": _get_processing_mode_recommendations(mode)
            })

        return {
            "success": True,
            "processing_modes": modes,
            "total_modes": len(modes)
        }

    except Exception as e:
        logger.error(f"Error getting processing modes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get processing modes: {str(e)}")


@router.get("/batch/status-summary")
async def get_status_summary():
    """Get summary of all batch job statuses."""
    try:
        # Get active jobs
        active_result = await batch_processing_service.get_active_jobs()

        # Get recent history
        history_result = await batch_processing_service.get_job_history(limit=100)

        # Calculate statistics
        status_counts = {
            "pending": 0,
            "running": 0,
            "paused": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0
        }

        operation_type_counts = {}

        if active_result["success"]:
            for job in active_result["active_jobs"]:
                status = job["status"]
                if status in status_counts:
                    status_counts[status] += 1

                op_type = job["operation_type"]
                operation_type_counts[op_type] = operation_type_counts.get(op_type, 0) + 1

        if history_result["success"]:
            for job in history_result["job_history"]:
                status = job["status"]
                if status in status_counts:
                    status_counts[status] += 1

                op_type = job["operation_type"]
                operation_type_counts[op_type] = operation_type_counts.get(op_type, 0) + 1

        return {
            "success": True,
            "summary": {
                "status_counts": status_counts,
                "operation_type_counts": operation_type_counts,
                "total_active": active_result["total_active"] if active_result["success"] else 0,
                "queue_size": active_result["queue_size"] if active_result["success"] else 0,
                "max_concurrent": active_result["max_concurrent_jobs"] if active_result["success"] else 0,
                "recent_history": len(history_result.get("job_history", [])) if history_result["success"] else 0
            },
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting status summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status summary: {str(e)}")


@router.get("/batch/performance-stats")
async def get_performance_stats():
    """Get batch processing performance statistics."""
    try:
        # This would get statistics from the batch processing service
        # For now, return mock data

        return {
            "success": True,
            "performance_stats": {
                "total_jobs_processed": 150,
                "total_items_processed": 50000,
                "average_processing_time_seconds": 120.5,
                "jobs_per_hour": 8.5,
                "items_per_hour": 2800.0,
                "success_rate": 94.5,
                "failure_rate": 5.5,
                "average_chunk_size": 150,
                "parallel_jobs_processed": 45,
                "sequential_jobs_processed": 105,
                "operation_type_performance": {
                    "import_nodes": {
                        "total_jobs": 50,
                        "success_rate": 96.0,
                        "avg_time_per_1000_items": 45.2
                    },
                    "import_relationships": {
                        "total_jobs": 30,
                        "success_rate": 93.3,
                        "avg_time_per_1000_items": 32.8
                    },
                    "export_graph": {
                        "total_jobs": 25,
                        "success_rate": 100.0,
                        "avg_time_per_1000_items": 28.5
                    },
                    "validate_graph": {
                        "total_jobs": 20,
                        "success_rate": 95.0,
                        "avg_time_per_1000_items": 65.3
                    }
                }
            },
            "calculated_at": dt.datetime.now(dt.timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting performance stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance stats: {str(e)}")


# Private Helper Methods

async def _parse_csv_nodes(content: str) -> List[Dict[str, Any]]:
    """Parse CSV content for nodes."""
    import csv
    import io

    try:
        reader = csv.DictReader(io.StringIO(content))
        nodes = []

        for row in reader:
            node = {
                "name": row.get("name", ""),
                "node_type": row.get("node_type", "unknown"),
                "platform": row.get("platform", "unknown"),
                "description": row.get("description", ""),
                "minecraft_version": row.get("minecraft_version", "latest"),
                "expert_validated": row.get("expert_validated", "").lower() == "true",
                "community_rating": float(row.get("community_rating", 0.0)),
                "properties": json.loads(row.get("properties", "{}"))
            }
            nodes.append(node)

        return nodes

    except Exception as e:
        raise ValueError(f"Failed to parse CSV nodes: {str(e)}")


async def _parse_csv_relationships(content: str) -> List[Dict[str, Any]]:
    """Parse CSV content for relationships."""
    import csv
    import io

    try:
        reader = csv.DictReader(io.StringIO(content))
        relationships = []

        for row in reader:
            relationship = {
                "source_node_id": row.get("source_node_id", ""),
                "target_node_id": row.get("target_node_id", ""),
                "relationship_type": row.get("relationship_type", "relates_to"),
                "confidence_score": float(row.get("confidence_score", 0.5)),
                "properties": json.loads(row.get("properties", "{}"))
            }
            relationships.append(relationship)

        return relationships

    except Exception as e:
        raise ValueError(f"Failed to parse CSV relationships: {str(e)}")


def _get_operation_description(op_type) -> str:
    """Get description for batch operation type."""
    descriptions = {
        BatchOperationType.IMPORT_NODES: "Import knowledge nodes from file",
        BatchOperationType.IMPORT_RELATIONSHIPS: "Import knowledge relationships from file",
        BatchOperationType.IMPORT_PATTERNS: "Import conversion patterns from file",
        BatchOperationType.EXPORT_GRAPH: "Export entire knowledge graph to file",
        BatchOperationType.DELETE_NODES: "Batch delete nodes matching criteria",
        BatchOperationType.DELETE_RELATIONSHIPS: "Batch delete relationships matching criteria",
        BatchOperationType.UPDATE_NODES: "Batch update nodes with new data",
        BatchOperationType.VALIDATE_GRAPH: "Validate knowledge graph integrity",
        BatchOperationType.CALCULATE_METRICS: "Calculate graph metrics and statistics"
    }
    return descriptions.get(op_type, "Unknown operation")


def _operation_requires_file(op_type) -> bool:
    """Check if operation requires file upload."""
    file_operations = [
        BatchOperationType.IMPORT_NODES,
        BatchOperationType.IMPORT_RELATIONSHIPS,
        BatchOperationType.IMPORT_PATTERNS
    ]
    return op_type in file_operations


def _get_operation_duration(op_type) -> str:
    """Get estimated duration for operation type."""
    durations = {
        BatchOperationType.IMPORT_NODES: "Medium (2-5 min per 1000 items)",
        BatchOperationType.IMPORT_RELATIONSHIPS: "Fast (1-3 min per 1000 items)",
        BatchOperationType.IMPORT_PATTERNS: "Slow (3-8 min per 1000 items)",
        BatchOperationType.EXPORT_GRAPH: "Medium (2-4 min per 1000 items)",
        BatchOperationType.DELETE_NODES: "Very Fast (30 sec per 1000 items)",
        BatchOperationType.DELETE_RELATIONSHIPS: "Very Fast (20 sec per 1000 items)",
        BatchOperationType.VALIDATE_GRAPH: "Slow (5-10 min per 1000 items)"
    }
    return durations.get(op_type, "Unknown duration")


def _get_processing_mode_description(mode) -> str:
    """Get description for processing mode."""
    descriptions = {
        ProcessingMode.SEQUENTIAL: "Process items one by one in sequence",
        ProcessingMode.PARALLEL: "Process multiple items simultaneously",
        ProcessingMode.CHUNKED: "Process items in chunks for memory efficiency",
        ProcessingMode.STREAMING: "Process items as a continuous stream"
    }
    return descriptions.get(mode, "Unknown processing mode")


def _get_processing_mode_use_cases(mode) -> List[str]:
    """Get use cases for processing mode."""
    use_cases = {
        ProcessingMode.SEQUENTIAL: ["Simple operations", "Low memory systems", "Debugging"],
        ProcessingMode.PARALLEL: ["CPU-intensive operations", "Large datasets", "Performance optimization"],
        ProcessingMode.CHUNKED: ["Memory-constrained environments", "Large files", "Batch processing"],
        ProcessingMode.STREAMING: ["Real-time data", "Very large datasets", "Continuous processing"]
    }
    return use_cases.get(mode, ["General use"])


def _get_processing_mode_recommendations(mode) -> List[str]:
    """Get recommendations for processing mode."""
    recommendations = {
        ProcessingMode.SEQUENTIAL: "Best for small datasets (< 1000 items)",
        ProcessingMode.PARALLEL: "Best for CPU-bound operations with multi-core systems",
        ProcessingMode.CHUNKED: "Best for memory-intensive operations",
        ProcessingMode.STREAMING: "Best for real-time or continuous data processing"
    }
    return recommendations.get(mode, ["General purpose"])


# Add missing imports
import datetime as dt
