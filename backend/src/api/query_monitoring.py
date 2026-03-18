"""
Query Monitoring API Endpoints

Provides HTTP endpoints to access and manage query performance monitoring.
Useful for debugging and performance optimization.

Endpoints:
- GET /api/query-monitor/report - Get query performance report
- GET /api/query-monitor/n-plus-one - Get N+1 candidates
- POST /api/query-monitor/reset - Reset monitoring data
- GET /api/query-monitor/slowest - Get slowest queries
- GET /api/query-monitor/frequent - Get most executed queries
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from db.query_monitor import (
    get_query_report,
    reset_query_monitor,
    enable_query_monitoring,
    disable_query_monitoring,
)

router = APIRouter(prefix="/api/query-monitor", tags=["query-monitoring"])


@router.get("/report", summary="Get Query Performance Report")
async def get_report() -> Dict[str, Any]:
    """
    Get comprehensive query performance report.
    
    Returns:
        - summary: Overall statistics
        - n_plus_one_candidates: Detected N+1 queries
        - slowest_queries: Top 10 slowest queries
        - most_executed_queries: Top 10 most executed queries
    """
    try:
        return get_query_report()
    except Exception as e:
        logger.error(f"Failed to generate report: {str(e)}", exc_info=True)

        raise HTTPException(status_code=500, detail="Failed to generate report: Please try again.")


@router.get("/n-plus-one", summary="Get N+1 Query Candidates")
async def get_n_plus_one_candidates() -> Dict[str, Any]:
    """
    Get queries that appear to have N+1 problems.
    
    Returns a list of queries executed multiple times with different parameters.
    """
    try:
        report = get_query_report()
        return {
            "count": len(report["n_plus_one_candidates"]),
            "candidates": report["n_plus_one_candidates"],
        }
    except Exception as e:
        logger.error(f"Failed to fetch N+1 candidates: {str(e)}", exc_info=True)

        raise HTTPException(status_code=500, detail="Failed to fetch N+1 candidates: Please try again.")


@router.get("/slowest", summary="Get Slowest Queries")
async def get_slowest_queries() -> Dict[str, Any]:
    """
    Get the 10 slowest queries by total execution time.
    """
    try:
        report = get_query_report()
        return {
            "count": len(report["slowest_queries"]),
            "queries": report["slowest_queries"],
        }
    except Exception as e:
        logger.error(f"Failed to fetch slowest queries: {str(e)}", exc_info=True)

        raise HTTPException(status_code=500, detail="Failed to fetch slowest queries: Please try again.")


@router.get("/frequent", summary="Get Most Executed Queries")
async def get_most_executed() -> Dict[str, Any]:
    """
    Get the 10 most frequently executed queries.
    """
    try:
        report = get_query_report()
        return {
            "count": len(report["most_executed_queries"]),
            "queries": report["most_executed_queries"],
        }
    except Exception as e:
        logger.error(f"Failed to fetch most executed queries: {str(e)}", exc_info=True)

        raise HTTPException(status_code=500, detail="Failed to fetch most executed queries: Please try again.")


@router.post("/reset", summary="Reset Monitoring Data")
async def reset_monitor() -> Dict[str, str]:
    """
    Clear all accumulated query monitoring data.
    
    This is useful when starting a new monitoring session.
    """
    try:
        reset_query_monitor()
        return {"status": "success", "message": "Query monitor reset"}
    except Exception as e:
        logger.error(f"Failed to reset monitor: {str(e)}", exc_info=True)

        raise HTTPException(status_code=500, detail="Failed to reset monitor: Please try again.")


@router.post("/enable", summary="Enable Query Monitoring")
async def enable_monitor() -> Dict[str, str]:
    """Enable query performance monitoring."""
    try:
        enable_query_monitoring()
        return {"status": "success", "message": "Query monitoring enabled"}
    except Exception as e:
        logger.error(f"Failed to enable monitor: {str(e)}", exc_info=True)

        raise HTTPException(status_code=500, detail="Failed to enable monitor: Please try again.")


@router.post("/disable", summary="Disable Query Monitoring")
async def disable_monitor() -> Dict[str, str]:
    """Disable query performance monitoring."""
    try:
        disable_query_monitoring()
        return {"status": "success", "message": "Query monitoring disabled"}
    except Exception as e:
        logger.error(f"Failed to disable monitor: {str(e)}", exc_info=True)

        raise HTTPException(status_code=500, detail="Failed to disable monitor: Please try again.")


@router.get("/summary", summary="Get Summary Statistics")
async def get_summary() -> Dict[str, Any]:
    """Get summary statistics about query performance."""
    try:
        report = get_query_report()
        return report["summary"]
    except Exception as e:
        logger.error(f"Failed to fetch summary: {str(e)}", exc_info=True)

        raise HTTPException(status_code=500, detail="Failed to fetch summary: Please try again.")
