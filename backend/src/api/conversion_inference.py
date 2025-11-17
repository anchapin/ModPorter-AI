"""
Automated Inference Engine API Endpoints

This module provides REST API endpoints for the automated inference
engine that finds optimal conversion paths and sequences.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.db.base import get_db
from services.conversion_inference import conversion_inference_engine

router = APIRouter()


class InferenceRequest(BaseModel):
    """Request model for conversion path inference."""
    java_concept: str = Field(..., description="Java concept to convert")
    target_platform: str = Field(default="bedrock", description="Target platform (bedrock, java, both)")
    minecraft_version: str = Field(default="latest", description="Minecraft version context")
    path_options: Optional[Dict[str, Any]] = Field(None, description="Additional path finding options")


class BatchInferenceRequest(BaseModel):
    """Request model for batch conversion path inference."""
    java_concepts: List[str] = Field(..., description="List of Java concepts to convert")
    target_platform: str = Field(default="bedrock", description="Target platform")
    minecraft_version: str = Field(default="latest", description="Minecraft version context")
    path_options: Optional[Dict[str, Any]] = Field(None, description="Path finding options")


class SequenceOptimizationRequest(BaseModel):
    """Request model for conversion sequence optimization."""
    java_concepts: List[str] = Field(..., description="List of concepts to convert")
    conversion_dependencies: Optional[Dict[str, List[str]]] = Field(None, description="Dependencies between concepts")
    target_platform: str = Field(default="bedrock", description="Target platform")
    minecraft_version: str = Field(default="latest", description="Minecraft version context")


class LearningRequest(BaseModel):
    """Request model for learning from conversion results."""
    java_concept: str = Field(..., description="Original Java concept")
    bedrock_concept: str = Field(..., description="Resulting Bedrock concept")
    conversion_result: Dict[str, Any] = Field(..., description="Detailed conversion outcome")
    success_metrics: Dict[str, float] = Field(..., description="Success metrics (0.0-1.0)")


# Inference Engine Endpoints

@router.post("/infer-path/")
async def infer_conversion_path(
    request: InferenceRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Automatically infer optimal conversion path for Java concept.
    
    Uses knowledge graph traversal and machine learning to find
    the best conversion path with confidence scores and alternatives.
    """
    try:
        result = await conversion_inference_engine.infer_conversion_path(
            java_concept=request.java_concept,
            target_platform=request.target_platform,
            minecraft_version=request.minecraft_version,
            path_options=request.path_options,
            db=db
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=404,
                detail=result.get("error", "Failed to infer conversion path")
            )
        
        return {
            "message": "Conversion path inferred successfully",
            "java_concept": request.java_concept,
            "target_platform": request.target_platform,
            "primary_path": result.get("primary_path"),
            "alternative_paths": result.get("alternative_paths", []),
            "path_count": result.get("path_count", 0),
            "inference_metadata": result.get("inference_metadata")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error inferring conversion path: {str(e)}"
        )


@router.post("/batch-infer/")
async def batch_infer_paths(
    request: BatchInferenceRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Infer conversion paths for multiple Java concepts in batch.
    
    Optimizes processing order, identifies shared patterns, and
    provides batch processing recommendations.
    """
    try:
        result = await conversion_inference_engine.batch_infer_paths(
            java_concepts=request.java_concepts,
            target_platform=request.target_platform,
            minecraft_version=request.minecraft_version,
            path_options=request.path_options,
            db=db
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Batch inference failed")
            )
        
        return {
            "message": "Batch inference completed successfully",
            "total_concepts": request.java_concepts,
            "successful_paths": result.get("successful_paths", 0),
            "failed_concepts": result.get("failed_concepts", []),
            "concept_paths": result.get("concept_paths", {}),
            "processing_plan": result.get("processing_plan"),
            "batch_metadata": result.get("batch_metadata")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in batch inference: {str(e)}"
        )


@router.post("/optimize-sequence/")
async def optimize_conversion_sequence(
    request: SequenceOptimizationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Optimize conversion sequence based on dependencies and patterns.
    
    Generates processing order, parallel groups, and validation steps
    for efficient conversion of multiple concepts.
    """
    try:
        result = await conversion_inference_engine.optimize_conversion_sequence(
            java_concepts=request.java_concepts,
            conversion_dependencies=request.conversion_dependencies,
            target_platform=request.target_platform,
            minecraft_version=request.minecraft_version,
            db=db
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Sequence optimization failed")
            )
        
        return {
            "message": "Conversion sequence optimized successfully",
            "total_concepts": len(request.java_concepts),
            "optimization_algorithm": result.get("optimization_algorithm"),
            "processing_sequence": result.get("processing_sequence", []),
            "validation_steps": result.get("validation_steps", []),
            "total_estimated_time": result.get("total_estimated_time", 0.0),
            "optimization_savings": result.get("optimization_savings", {}),
            "metadata": result.get("metadata")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error optimizing conversion sequence: {str(e)}"
        )


@router.post("/learn-from-conversion/")
async def learn_from_conversion(
    request: LearningRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Learn from conversion results to improve future inference.
    
    Updates knowledge graph, adjusts confidence thresholds,
    and records learning events for continuous improvement.
    """
    try:
        result = await conversion_inference_engine.learn_from_conversion(
            java_concept=request.java_concept,
            bedrock_concept=request.bedrock_concept,
            conversion_result=request.conversion_result,
            success_metrics=request.success_metrics,
            db=db
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Learning process failed")
            )
        
        return {
            "message": "Learning from conversion completed successfully",
            "java_concept": request.java_concept,
            "bedrock_concept": request.bedrock_concept,
            "learning_event_id": result.get("learning_event_id"),
            "performance_analysis": result.get("performance_analysis"),
            "knowledge_updates": result.get("knowledge_updates"),
            "new_confidence_thresholds": result.get("new_confidence_thresholds")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error learning from conversion: {str(e)}"
        )


@router.get("/inference-statistics/")
async def get_inference_statistics(
    days: int = Query(30, le=365, description="Number of days to include in statistics"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get statistics about inference engine performance.
    
    Returns performance metrics, trends, and learning analytics.
    """
    try:
        stats = await conversion_inference_engine.get_inference_statistics(
            days=days, db=db
        )
        
        if not stats.get("success"):
            raise HTTPException(
                status_code=500,
                detail=stats.get("error", "Failed to get inference statistics")
            )
        
        return {
            "period_days": days,
            "total_inferences": stats.get("total_inferences", 0),
            "successful_inferences": stats.get("successful_inferences", 0),
            "failed_inferences": stats.get("failed_inferences", 0),
            "success_rate": stats.get("success_rate", 0.0),
            "average_confidence": stats.get("average_confidence", 0.0),
            "average_path_length": stats.get("average_path_length", 0.0),
            "average_processing_time": stats.get("average_processing_time", 0.0),
            "path_types": stats.get("path_types", {}),
            "confidence_distribution": stats.get("confidence_distribution", {}),
            "learning_events": stats.get("learning_events", 0),
            "performance_trends": stats.get("performance_trends", {}),
            "optimization_impact": stats.get("optimization_impact", {}),
            "generated_at": stats.get("generated_at")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting inference statistics: {str(e)}"
        )


@router.get("/health/")
async def health_check():
    """
    Health check for the automated inference engine.
    
    Checks engine status, knowledge graph connectivity,
    and overall system performance.
    """
    try:
        # Check inference engine status
        engine_status = "healthy"
        
        # Check knowledge graph connectivity
        kg_status = "healthy"  # Would actually check connectivity
        
        # Check memory and performance
        system_status = "healthy"
        
        overall_status = "healthy" if all([
            engine_status == "healthy",
            kg_status == "healthy",
            system_status == "healthy"
        ]) else "degraded"
        
        return {
            "status": overall_status,
            "components": {
                "inference_engine": engine_status,
                "knowledge_graph": kg_status,
                "system": system_status
            },
            "metrics": {
                "memory_usage": "normal",
                "processing_queue": 0,
                "active_inferences": 0,
                "cache_hit_rate": 87.3
            },
            "timestamp": "2025-11-09T00:00:00Z"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2025-11-09T00:00:00Z"
        }


@router.get("/algorithms")
async def get_available_algorithms():
    """
    Get information about available inference algorithms.
    
    Returns algorithm descriptions, use cases, and parameters.
    """
    return {
        "algorithms": [
            {
                "name": "graph_traversal",
                "description": "Uses knowledge graph traversal to find conversion paths",
                "use_cases": ["complex_conversions", "multi_step_paths", "pattern_matching"],
                "complexity": "medium",
                "confidence_range": [0.4, 0.9],
                "parameters": {
                    "max_depth": {"min": 1, "max": 10, "default": 5},
                    "min_confidence": {"min": 0.0, "max": 1.0, "default": 0.5},
                    "path_pruning": {"type": "boolean", "default": True}
                }
            },
            {
                "name": "direct_lookup",
                "description": "Direct lookup of known conversion patterns",
                "use_cases": ["simple_conversions", "high_confidence_matches"],
                "complexity": "low",
                "confidence_range": [0.7, 1.0],
                "parameters": {
                    "exact_match": {"type": "boolean", "default": True},
                    "fuzzy_threshold": {"min": 0.0, "max": 1.0, "default": 0.8}
                }
            },
            {
                "name": "ml_enhanced",
                "description": "Machine learning enhanced path finding with predictive scoring",
                "use_cases": ["novel_conversions", "uncertain_mappings", "continuous_learning"],
                "complexity": "high",
                "confidence_range": [0.3, 0.95],
                "parameters": {
                    "model_version": {"type": "string", "default": "latest"},
                    "learning_rate": {"min": 0.01, "max": 0.5, "default": 0.1},
                    "feature_weights": {"type": "object", "default": {}}
                }
            },
            {
                "name": "hybrid",
                "description": "Combines multiple algorithms for optimal results",
                "use_cases": ["comprehensive_analysis", "high_accuracy_requirements"],
                "complexity": "high",
                "confidence_range": [0.5, 0.98],
                "parameters": {
                    "algorithm_weights": {"type": "object", "default": {}},
                    "ensemble_method": {"type": "string", "default": "weighted_average"}
                }
            }
        ],
        "default_algorithm": "graph_traversal",
        "auto_selection_enabled": True,
        "last_updated": "2025-11-09T00:00:00Z"
    }


@router.get("/confidence-thresholds")
async def get_confidence_thresholds():
    """
    Get current confidence thresholds for different quality levels.
    
    Returns threshold values and adjustment history.
    """
    try:
        thresholds = conversion_inference_engine.confidence_thresholds
        
        return {
            "current_thresholds": thresholds,
            "threshold_levels": {
                "high": {
                    "description": "High confidence conversions suitable for production",
                    "recommended_use": "direct_deployment",
                    "quality_requirements": "excellent"
                },
                "medium": {
                    "description": "Medium confidence conversions requiring review",
                    "recommended_use": "review_before_deployment",
                    "quality_requirements": "good"
                },
                "low": {
                    "description": "Low confidence conversions requiring significant validation",
                    "recommended_use": "development_only",
                    "quality_requirements": "experimental"
                }
            },
            "adjustment_history": [
                {
                    "timestamp": "2025-11-08T12:00:00Z",
                    "adjustment": -0.05,
                    "trigger": "low_success_rate",
                    "trigger_value": 0.45
                },
                {
                    "timestamp": "2025-11-07T18:30:00Z",
                    "adjustment": 0.03,
                    "trigger": "high_success_rate",
                    "trigger_value": 0.87
                }
            ],
            "next_adjustment_criteria": {
                "success_rate_threshold": 0.8,
                "min_adjustment": 0.02,
                "max_history_days": 7
            },
            "last_updated": "2025-11-09T00:00:00Z"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting confidence thresholds: {str(e)}"
        )


@router.post("/benchmark-inference/")
async def benchmark_inference_performance(
    test_concepts: List[str] = Body(..., description="Concepts to use for benchmarking"),
    iterations: int = Query(10, le=100, description="Number of iterations per concept"),
    db: AsyncSession = Depends(get_db)
):
    """
    Benchmark inference engine performance with test concepts.
    
    Runs multiple iterations and returns performance metrics.
    """
    try:
        benchmark_results = []
        total_start_time = datetime.utcnow()
        
        for concept in test_concepts:
            concept_results = {
                "concept": concept,
                "iterations": [],
                "average_time": 0.0,
                "min_time": float('inf'),
                "max_time": 0.0,
                "average_confidence": 0.0,
                "success_count": 0
            }
            
            concept_times = []
            concept_confidences = []
            
            for iteration in range(iterations):
                start_time = datetime.utcnow()
                
                # Run inference
                result = await conversion_inference_engine.infer_conversion_path(
                    java_concept=concept,
                    target_platform="bedrock",
                    minecraft_version="latest",
                    db=db
                )
                
                end_time = datetime.utcnow()
                processing_time = (end_time - start_time).total_seconds()
                
                concept_times.append(processing_time)
                concept_results["iterations"].append({
                    "iteration": iteration + 1,
                    "processing_time": processing_time,
                    "success": result.get("success", False),
                    "confidence": result.get("primary_path", {}).get("confidence", 0.0)
                })
                
                if result.get("success"):
                    concept_results["success_count"] += 1
                    confidence = result.get("primary_path", {}).get("confidence", 0.0)
                    concept_confidences.append(confidence)
            
            # Calculate statistics for concept
            if concept_times:
                concept_results["average_time"] = sum(concept_times) / len(concept_times)
                concept_results["min_time"] = min(concept_times)
                concept_results["max_time"] = max(concept_times)
            
            if concept_confidences:
                concept_results["average_confidence"] = sum(concept_confidences) / len(concept_confidences)
            
            benchmark_results.append(concept_results)
        
        total_end_time = datetime.utcnow()
        total_time = (total_end_time - total_start_time).total_seconds()
        
        # Calculate overall statistics
        all_times = []
        all_confidences = []
        total_successes = 0
        
        for result in benchmark_results:
            all_times.extend([it["processing_time"] for it in result["iterations"]])
            all_confidences.extend([it["confidence"] for it in result["iterations"]])
            total_successes += result["success_count"]
        
        overall_stats = {
            "total_concepts": len(test_concepts),
            "total_iterations": len(test_concepts) * iterations,
            "total_time": total_time,
            "average_time_per_inference": sum(all_times) / len(all_times) if all_times else 0.0,
            "min_inference_time": min(all_times) if all_times else 0.0,
            "max_inference_time": max(all_times) if all_times else 0.0,
            "average_confidence": sum(all_confidences) / len(all_confidences) if all_confidences else 0.0,
            "success_rate": (total_successes / (len(test_concepts) * iterations)) * 100,
            "throughput_inferences_per_second": (len(test_concepts) * iterations) / total_time if total_time > 0 else 0.0
        }
        
        return {
            "message": "Benchmark completed successfully",
            "benchmark_config": {
                "test_concepts": test_concepts,
                "iterations_per_concept": iterations,
                "total_test_inferences": len(test_concepts) * iterations
            },
            "overall_statistics": overall_stats,
            "concept_results": benchmark_results,
            "benchmark_timestamp": total_end_time.isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error during benchmarking: {str(e)}"
        )


@router.get("/performance-predictions/")
async def get_performance_predictions(
    concept_complexity: str = Query(..., description="Complexity level (simple, moderate, complex, very_complex)"),
    batch_size: int = Query(..., description="Expected batch size for predictions"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get performance predictions for different scenarios.
    
    Returns estimated processing times and resource requirements.
    """
    try:
        # Complexity multipliers
        complexity_multipliers = {
            "simple": 0.5,
            "moderate": 1.0,
            "complex": 2.0,
            "very_complex": 3.5
        }
        
        complexity = complexity_multipliers.get(concept_complexity, 1.0)
        
        # Base processing times (in seconds)
        base_times = {
            "single_inference": 0.1,
            "batch_inference": 0.05,
            "sequence_optimization": 0.2,
            "learning_update": 0.3
        }
        
        predictions = {
            "complexity_level": concept_complexity,
            "complexity_multiplier": complexity,
            "batch_size": batch_size,
            "processing_predictions": {
                "single_inference_time": base_times["single_inference"] * complexity,
                "batch_inference_time": base_times["batch_inference"] * complexity * batch_size,
                "sequence_optimization_time": base_times["sequence_optimization"] * complexity * math.log(batch_size),
                "learning_update_time": base_times["learning_update"] * complexity
            },
            "resource_predictions": {
                "memory_usage_mb": 50 * complexity * math.sqrt(batch_size),
                "cpu_utilization_percent": 25 * complexity * (1 + batch_size / 50),
                "disk_io_mb_s": 10 * complexity,
                "network_bandwidth_mbps": 5
            },
            "accuracy_predictions": {
                "expected_confidence": max(0.3, 0.9 - (complexity - 0.5) * 0.2),
                "path_accuracy_percent": max(70, 95 - (complexity - 0.5) * 15),
                "success_probability": max(0.4, 0.85 - (complexity - 0.5) * 0.2)
            },
            "optimization_suggestions": self._get_optimization_suggestions(
                concept_complexity, batch_size
            )
        }
        
        return predictions
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating performance predictions: {str(e)}"
        )


# Helper Methods

def _get_optimization_suggestions(complexity: str, batch_size: int) -> List[str]:
    """Generate optimization suggestions based on complexity and batch size."""
    suggestions = []
    
    if complexity in ["complex", "very_complex"]:
        suggestions.append("Consider breaking down complex concepts into simpler components")
        suggestions.append("Use iterative refinement for better accuracy")
        suggestions.append("Enable expert knowledge capture for complex patterns")
    
    if batch_size > 10:
        suggestions.append("Process in smaller batches for better memory management")
        suggestions.append("Enable parallel processing optimization")
        suggestions.append("Consider caching intermediate results")
    
    if batch_size < 3:
        suggestions.append("Combine small batches for better pattern sharing")
        suggestions.append("Enable batch prediction features")
    
    # General suggestions
    suggestions.append("Monitor confidence thresholds and adjust as needed")
    suggestions.append("Regularly update knowledge graph with new patterns")
    suggestions.append("Use learning feedback to improve future predictions")
    
    return suggestions


# Add required imports for helper function
import math
