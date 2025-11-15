"""
Working Test Suite for Progressive Loading API

Tests for src/api/progressive.py - 259 statements, targeting 60%+ coverage
Focus on testing functions directly as they are defined
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json
from datetime import datetime

from src.api.progressive import (
    start_progressive_load, get_loading_progress, update_loading_level,
    preload_adjacent_areas, get_loading_statistics, get_loading_strategies,
    get_detail_levels, get_loading_priorities, estimate_load_time,
    optimize_loading_settings, get_progressive_loading_health
)
from src.services.progressive_loading import (
    LoadingStrategy, DetailLevel, LoadingPriority
)
from fastapi import HTTPException


class TestProgressiveLoading:
    """Test progressive loading endpoints."""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()
    
    @pytest.fixture
    def sample_load_data(self):
        return {
            "visualization_id": "viz_123",
            "loading_strategy": "lod_based",
            "detail_level": "low",
            "priority": "medium",
            "viewport": {
                "x": 0, "y": 0, "width": 800, "height": 600
            },
            "parameters": {
                "batch_size": 100,
                "timeout": 30
            }
        }
    
    @pytest.mark.asyncio
    async def test_start_progressive_load_success(self, mock_db, sample_load_data):
        """Test successful progressive load start."""
        with patch('src.api.progressive.progressive_loading_service') as mock_service:
            mock_service.start_progressive_load.return_value = {
                "success": True,
                "task_id": "task_123",
                "visualization_id": "viz_123",
                "loading_strategy": "lod_based",
                "detail_level": "low",
                "priority": "medium"
            }
            
            result = await start_progressive_load(sample_load_data, mock_db)
            
            assert result["success"] is True
            assert result["task_id"] == "task_123"
            assert result["visualization_id"] == "viz_123"
            mock_service.start_progressive_load.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_progressive_load_missing_visualization_id(self, mock_db):
        """Test progressive load start with missing visualization_id."""
        load_data = {
            "loading_strategy": "lod_based",
            "detail_level": "low",
            "priority": "medium"
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await start_progressive_load(load_data, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "visualization_id is required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_start_progressive_load_invalid_strategy(self, mock_db):
        """Test progressive load start with invalid strategy."""
        load_data = {
            "visualization_id": "viz_123",
            "loading_strategy": "invalid_strategy",
            "detail_level": "low",
            "priority": "medium"
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await start_progressive_load(load_data, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "Invalid loading_strategy" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_start_progressive_load_invalid_detail_level(self, mock_db):
        """Test progressive load start with invalid detail level."""
        load_data = {
            "visualization_id": "viz_123",
            "loading_strategy": "lod_based",
            "detail_level": "invalid_level",
            "priority": "medium"
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await start_progressive_load(load_data, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "Invalid detail_level" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_start_progressive_load_invalid_priority(self, mock_db):
        """Test progressive load start with invalid priority."""
        load_data = {
            "visualization_id": "viz_123",
            "loading_strategy": "lod_based",
            "detail_level": "low",
            "priority": "invalid_priority"
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await start_progressive_load(load_data, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "Invalid priority" in str(exc_info.value.detail)


class TestLoadingProgress:
    """Test loading progress endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_loading_progress_success(self):
        """Test successful loading progress retrieval."""
        with patch('src.api.progressive.progressive_loading_service') as mock_service:
            mock_service.get_loading_progress.return_value = {
                "success": True,
                "task_id": "task_123",
                "progress": {
                    "loaded_nodes": 50,
                    "total_nodes": 200,
                    "loaded_edges": 75,
                    "total_edges": 300,
                    "percentage": 25.0,
                    "current_stage": "loading_nodes",
                    "estimated_time_remaining": 45.2
                }
            }
            
            result = await get_loading_progress("task_123")
            
            assert result["success"] is True
            assert result["task_id"] == "task_123"
            assert result["progress"]["percentage"] == 25.0
            assert result["progress"]["current_stage"] == "loading_nodes"
            mock_service.get_loading_progress.assert_called_once_with("task_123")
    
    @pytest.mark.asyncio
    async def test_get_loading_progress_not_found(self):
        """Test loading progress retrieval for non-existent task."""
        with patch('src.api.progressive.progressive_loading_service') as mock_service:
            mock_service.get_loading_progress.return_value = {
                "success": False,
                "error": "Task not found"
            }
            
            with pytest.raises(HTTPException) as exc_info:
                await get_loading_progress("nonexistent_task")
            
            assert exc_info.value.status_code == 404
            assert "Task not found" in str(exc_info.value.detail)


class TestLoadingLevel:
    """Test loading level endpoints."""
    
    @pytest.mark.asyncio
    async def test_update_loading_level_success(self):
        """Test successful loading level update."""
        with patch('src.api.progressive.progressive_loading_service') as mock_service:
            mock_service.update_detail_level.return_value = {
                "success": True,
                "task_id": "task_123",
                "new_level": "high",
                "reloaded": True
            }
            
            level_data = {
                "detail_level": "high",
                "reload": True,
                "viewport": {"x": 0, "y": 0, "width": 800, "height": 600}
            }
            
            result = await update_loading_level("task_123", level_data)
            
            assert result["success"] is True
            assert result["new_level"] == "high"
            assert result["reloaded"] is True
            mock_service.update_detail_level.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_loading_level_invalid_level(self):
        """Test loading level update with invalid level."""
        level_data = {
            "detail_level": "invalid_level",
            "reload": True
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await update_loading_level("task_123", level_data)
        
        assert exc_info.value.status_code == 400
        assert "Invalid detail_level" in str(exc_info.value.detail)


class TestPreloading:
    """Test preloading endpoints."""
    
    @pytest.mark.asyncio
    async def test_preload_adjacent_areas_success(self):
        """Test successful adjacent areas preloading."""
        with patch('src.api.progressive.progressive_loading_service') as mock_service:
            mock_service.preload_adjacent_areas.return_value = {
                "success": True,
                "task_id": "task_123",
                "preloaded_areas": [
                    {"area_id": "area_1", "nodes": 25, "edges": 40},
                    {"area_id": "area_2", "nodes": 30, "edges": 55}
                ],
                "total_nodes_preloaded": 55,
                "total_edges_preloaded": 95
            }
            
            preload_data = {
                "viewport": {"x": 100, "y": 200, "width": 800, "height": 600},
                "radius": 2.0,
                "priority": "high"
            }
            
            result = await preload_adjacent_areas(preload_data)
            
            assert result["success"] is True
            assert result["total_nodes_preloaded"] == 55
            assert result["total_edges_preloaded"] == 95
            assert len(result["preloaded_areas"]) == 2
            mock_service.preload_adjacent_areas.assert_called_once()


class TestLoadingStatistics:
    """Test loading statistics endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_loading_statistics_success(self):
        """Test successful loading statistics retrieval."""
        with patch('src.api.progressive.progressive_loading_service') as mock_service:
            mock_service.get_loading_statistics.return_value = {
                "success": True,
                "statistics": {
                    "active_tasks": 3,
                    "completed_tasks": 15,
                    "failed_tasks": 2,
                    "total_nodes_loaded": 2500,
                    "total_edges_loaded": 4200,
                    "average_load_time": 125.5,
                    "memory_usage_mb": 256.3
                }
            }
            
            result = await get_loading_statistics()
            
            assert result["success"] is True
            assert result["statistics"]["active_tasks"] == 3
            assert result["statistics"]["completed_tasks"] == 15
            assert result["statistics"]["total_nodes_loaded"] == 2500
            mock_service.get_loading_statistics.assert_called_once()


class TestUtilityEndpoints:
    """Test utility endpoints for progressive loading."""
    
    @pytest.mark.asyncio
    async def test_get_loading_strategies_success(self):
        """Test successful loading strategies retrieval."""
        result = await get_loading_strategies()
        
        assert result["success"] is True
        assert result["total_strategies"] > 0
        assert len(result["strategies"]) > 0
        
        # Check if all strategies have required fields
        for strategy in result["strategies"]:
            assert "value" in strategy
            assert "name" in strategy
            assert "description" in strategy
            assert "suitable_for" in strategy
    
    @pytest.mark.asyncio
    async def test_get_detail_levels_success(self):
        """Test successful detail levels retrieval."""
        result = await get_detail_levels()
        
        assert result["success"] is True
        assert result["total_levels"] > 0
        assert len(result["detail_levels"]) > 0
        
        # Check if all levels have required fields
        for level in result["detail_levels"]:
            assert "value" in level
            assert "name" in level
            assert "description" in level
            assert "node_limit" in level
            assert "edge_limit" in level
    
    @pytest.mark.asyncio
    async def test_get_loading_priorities_success(self):
        """Test successful loading priorities retrieval."""
        result = await get_loading_priorities()
        
        assert result["success"] is True
        assert result["total_priorities"] > 0
        assert len(result["priorities"]) > 0
        
        # Check if all priorities have required fields
        for priority in result["priorities"]:
            assert "value" in priority
            assert "name" in priority
            assert "description" in priority
            assert "weight" in priority
    
    @pytest.mark.asyncio
    async def test_estimate_load_time_success(self):
        """Test successful load time estimation."""
        with patch('src.api.progressive.progressive_loading_service') as mock_service:
            mock_service.estimate_load_time.return_value = {
                "success": True,
                "estimates": {
                    "graph_size_nodes": 500,
                    "graph_size_edges": 800,
                    "strategy": "lod_based",
                    "detail_level": "medium",
                    "estimated_time_seconds": 45.2,
                    "confidence_interval": [38.5, 51.9],
                    "factors": {
                        "network_speed": "fast",
                        "device_performance": "medium",
                        "data_complexity": "medium"
                    }
                }
            }
            
            estimate_data = {
                "graph_id": "viz_123",
                "strategy": "lod_based",
                "detail_level": "medium",
                "viewport_size": {"width": 800, "height": 600}
            }
            
            result = await estimate_load_time(estimate_data)
            
            assert result["success"] is True
            assert result["estimates"]["estimated_time_seconds"] == 45.2
            assert result["estimates"]["graph_size_nodes"] == 500
            mock_service.estimate_load_time.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_optimize_loading_settings_success(self):
        """Test successful loading settings optimization."""
        with patch('src.api.progressive.progressive_loading_service') as mock_service:
            mock_service.optimize_settings.return_value = {
                "success": True,
                "optimization_results": {
                    "recommended_strategy": "hybrid",
                    "recommended_detail_level": "medium",
                    "recommended_batch_size": 150,
                    "recommended_viewport_size": {"width": 1024, "height": 768},
                    "expected_performance_improvement": 35.2,
                    "optimization_reasons": [
                        "Large graph detected",
                        "Network conditions moderate",
                        "Device performance high"
                    ]
                }
            }
            
            optimization_data = {
                "graph_id": "viz_123",
                "current_settings": {
                    "strategy": "lod_based",
                    "detail_level": "low",
                    "batch_size": 100
                },
                "constraints": {
                    "max_memory_mb": 512,
                    "max_load_time_seconds": 60,
                    "target_framerate": 30
                }
            }
            
            result = await optimize_loading_settings(optimization_data)
            
            assert result["success"] is True
            assert result["optimization_results"]["recommended_strategy"] == "hybrid"
            assert result["optimization_results"]["expected_performance_improvement"] == 35.2
            mock_service.optimize_settings.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_progressive_loading_health_success(self):
        """Test successful progressive loading health check."""
        with patch('src.api.progressive.progressive_loading_service') as mock_service:
            mock_service.get_health_status.return_value = {
                "success": True,
                "health": {
                    "status": "healthy",
                    "active_tasks": 3,
                    "service_uptime_seconds": 86400,
                    "memory_usage_mb": 256.3,
                    "cpu_usage_percent": 15.2,
                    "cache_hit_ratio": 0.85,
                    "average_response_time_ms": 125.5,
                    "error_rate_percent": 0.1,
                    "last_health_check": datetime.now().isoformat()
                }
            }
            
            result = await get_progressive_loading_health()
            
            assert result["success"] is True
            assert result["health"]["status"] == "healthy"
            assert result["health"]["active_tasks"] == 3
            assert result["health"]["memory_usage_mb"] == 256.3
            mock_service.get_health_status.assert_called_once()


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_start_progressive_load_default_values(self, mock_db):
        """Test progressive load start with default values."""
        load_data = {
            "visualization_id": "viz_123"
            # No other fields - should use defaults
        }
        
        with patch('src.api.progressive.progressive_loading_service') as mock_service:
            mock_service.start_progressive_load.return_value = {
                "success": True,
                "task_id": "task_123"
            }
            
            result = await start_progressive_load(load_data, mock_db)
            
            assert result["success"] is True
            # Verify service was called
            mock_service.start_progressive_load.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_loading_level_service_error(self):
        """Test loading level update when service returns error."""
        with patch('src.api.progressive.progressive_loading_service') as mock_service:
            mock_service.update_detail_level.return_value = {
                "success": False,
                "error": "Task not found"
            }
            
            level_data = {"detail_level": "high", "reload": True}
            
            with pytest.raises(HTTPException) as exc_info:
                await update_loading_level("nonexistent_task", level_data)
            
            assert exc_info.value.status_code == 404
            assert "Task not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_estimate_load_time_validation_error(self):
        """Test load time estimation with validation error."""
        estimate_data = {
            # Missing required graph_id
            "strategy": "lod_based",
            "detail_level": "medium"
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await estimate_load_time(estimate_data)
        
        assert exc_info.value.status_code == 400
        assert "graph_id is required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_optimize_loading_settings_validation_error(self):
        """Test settings optimization with validation error."""
        optimization_data = {
            # Missing required current_settings
            "graph_id": "viz_123",
            "constraints": {"max_memory_mb": 512}
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await optimize_loading_settings(optimization_data)
        
        assert exc_info.value.status_code == 400
        assert "current_settings are required" in str(exc_info.value.detail)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
