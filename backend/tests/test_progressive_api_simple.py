"""
Simple Test Suite for Progressive Loading API

Tests for src/api/progressive.py - 259 statements, targeting 60%+ coverage
Focus on testing the functions directly as they are defined
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.api.progressive import (
    start_progressive_load,
    get_loading_progress,
    get_loading_statistics,
    get_detail_levels,
)
from src.services.progressive_loading import (
    LoadingStrategy,
    DetailLevel,
    LoadingPriority,
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
            "viewport": {"x": 0, "y": 0, "width": 800, "height": 600},
            "parameters": {"batch_size": 100, "timeout": 30},
        }

    @pytest.mark.asyncio
    async def test_start_progressive_load_success(self, mock_db, sample_load_data):
        """Test successful progressive load start."""
        with patch("src.api.progressive.progressive_loading_service") as mock_service:
            mock_service.start_progressive_load.return_value = {
                "success": True,
                "task_id": "task_123",
                "visualization_id": "viz_123",
                "loading_strategy": "lod_based",
                "detail_level": "low",
                "priority": "medium",
            }

            result = await start_progressive_load(sample_load_data, mock_db)

            assert result["success"] is True
            assert result["task_id"] == "task_123"
            assert result["visualization_id"] == "viz_123"
            mock_service.start_progressive_load.assert_called_once_with(
                "viz_123",
                LoadingStrategy.LOD_BASED,
                DetailLevel.LOW,
                sample_load_data["viewport"],
                LoadingPriority.MEDIUM,
                sample_load_data["parameters"],
                mock_db,
            )

    @pytest.mark.asyncio
    async def test_start_progressive_load_missing_visualization_id(self, mock_db):
        """Test progressive load start with missing visualization_id."""
        load_data = {
            "loading_strategy": "lod_based",
            "detail_level": "low",
            "priority": "medium",
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
            "priority": "medium",
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
            "priority": "medium",
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
            "priority": "invalid_priority",
        }

        with pytest.raises(HTTPException) as exc_info:
            await start_progressive_load(load_data, mock_db)

        assert exc_info.value.status_code == 400
        assert "Invalid priority" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_start_progressive_load_service_error(self, mock_db):
        """Test progressive load start when service returns error."""
        load_data = {
            "visualization_id": "viz_123",
            "loading_strategy": "lod_based",
            "detail_level": "low",
            "priority": "medium",
        }

        with patch("src.api.progressive.progressive_loading_service") as mock_service:
            mock_service.start_progressive_load.return_value = {
                "success": False,
                "error": "Visualization not found",
            }

            with pytest.raises(HTTPException) as exc_info:
                await start_progressive_load(load_data, mock_db)

            assert exc_info.value.status_code == 400
            assert "Visualization not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_start_progressive_load_exception_handling(self, mock_db):
        """Test progressive load start with unexpected exception."""
        load_data = {
            "visualization_id": "viz_123",
            "loading_strategy": "lod_based",
            "detail_level": "low",
            "priority": "medium",
        }

        with patch("src.api.progressive.progressive_loading_service") as mock_service:
            mock_service.start_progressive_load.side_effect = Exception(
                "Database error"
            )

            with pytest.raises(HTTPException) as exc_info:
                await start_progressive_load(load_data, mock_db)

            assert exc_info.value.status_code == 500
            assert "Progressive load failed" in str(exc_info.value.detail)


class TestLoadingProgress:
    """Test loading progress endpoints."""

    @pytest.mark.asyncio
    async def test_get_loading_progress_success(self):
        """Test successful loading progress retrieval."""
        with patch("src.api.progressive.progressive_loading_service") as mock_service:
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
                    "estimated_time_remaining": 45.2,
                },
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
        with patch("src.api.progressive.progressive_loading_service") as mock_service:
            mock_service.get_loading_progress.return_value = {
                "success": False,
                "error": "Task not found",
            }

            with pytest.raises(HTTPException) as exc_info:
                await get_loading_progress("nonexistent_task")

            assert exc_info.value.status_code == 404
            assert "Task not found" in str(exc_info.value.detail)


class TestLoadingControl:
    """Test loading control endpoints."""

    @pytest.mark.asyncio
    async def test_pause_loading_task_success(self):
        """Test successful loading task pause."""
        with patch("src.api.progressive.progressive_loading_service") as mock_service:
            mock_service.pause_loading_task.return_value = {
                "success": True,
                "task_id": "task_123",
                "status": "paused",
            }

            result = await pause_loading_task("task_123")

            assert result["success"] is True
            assert result["status"] == "paused"
            mock_service.pause_loading_task.assert_called_once_with("task_123")

    @pytest.mark.asyncio
    async def test_pause_loading_task_not_found(self):
        """Test pause for non-existent loading task."""
        with patch("src.api.progressive.progressive_loading_service") as mock_service:
            mock_service.pause_loading_task.return_value = {
                "success": False,
                "error": "Task not found",
            }

            with pytest.raises(HTTPException) as exc_info:
                await pause_loading_task("nonexistent_task")

            assert exc_info.value.status_code == 404
            assert "Task not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_resume_loading_task_success(self):
        """Test successful loading task resume."""
        with patch("src.api.progressive.progressive_loading_service") as mock_service:
            mock_service.resume_loading_task.return_value = {
                "success": True,
                "task_id": "task_123",
                "status": "resumed",
            }

            result = await resume_loading_task("task_123")

            assert result["success"] is True
            assert result["status"] == "resumed"
            mock_service.resume_loading_task.assert_called_once_with("task_123")

    @pytest.mark.asyncio
    async def test_cancel_loading_task_success(self):
        """Test successful loading task cancellation."""
        with patch("src.api.progressive.progressive_loading_service") as mock_service:
            mock_service.cancel_loading_task.return_value = {
                "success": True,
                "task_id": "task_123",
                "status": "cancelled",
                "reason": "User requested cancellation",
            }

            result = await cancel_loading_task("task_123")

            assert result["success"] is True
            assert result["status"] == "cancelled"
            mock_service.cancel_loading_task.assert_called_once_with("task_123")


class TestLoadingStatistics:
    """Test loading statistics endpoints."""

    @pytest.mark.asyncio
    async def test_get_loading_statistics_success(self):
        """Test successful loading statistics retrieval."""
        with patch("src.api.progressive.progressive_loading_service") as mock_service:
            mock_service.get_loading_statistics.return_value = {
                "success": True,
                "statistics": {
                    "active_tasks": 3,
                    "completed_tasks": 15,
                    "failed_tasks": 2,
                    "total_nodes_loaded": 2500,
                    "total_edges_loaded": 4200,
                    "average_load_time": 125.5,
                    "memory_usage_mb": 256.3,
                },
            }

            result = await get_loading_statistics()

            assert result["success"] is True
            assert result["statistics"]["active_tasks"] == 3
            assert result["statistics"]["completed_tasks"] == 15
            assert result["statistics"]["total_nodes_loaded"] == 2500
            mock_service.get_loading_statistics.assert_called_once()


class TestViewportAndDetailLevel:
    """Test viewport and detail level endpoints."""

    @pytest.mark.asyncio
    async def test_update_viewport_success(self):
        """Test successful viewport update."""
        with patch("src.api.progressive.progressive_loading_service") as mock_service:
            mock_service.update_viewport.return_value = {
                "success": True,
                "task_id": "task_123",
                "viewport": {"x": 100, "y": 200, "width": 800, "height": 600},
                "reloaded": True,
            }

            viewport_data = {"x": 100, "y": 200, "width": 800, "height": 600}

            result = await update_viewport("task_123", viewport_data)

            assert result["success"] is True
            assert result["reloaded"] is True
            assert result["viewport"]["x"] == 100
            mock_service.update_viewport.assert_called_once_with(
                "task_123", viewport_data
            )

    @pytest.mark.asyncio
    async def test_set_detail_level_success(self):
        """Test successful detail level setting."""
        with patch("src.api.progressive.progressive_loading_service") as mock_service:
            mock_service.set_detail_level.return_value = {
                "success": True,
                "task_id": "task_123",
                "detail_level": "high",
                "reloaded": True,
            }

            detail_data = {"detail_level": "high", "reload": True}

            result = await set_detail_level("task_123", detail_data)

            assert result["success"] is True
            assert result["detail_level"] == "high"
            assert result["reloaded"] is True
            mock_service.set_detail_level.assert_called_once_with(
                "task_123", DetailLevel.HIGH, True
            )


class TestUtilityEndpoints:
    """Test utility endpoints for progressive loading."""

    @pytest.mark.asyncio
    async def test_get_available_strategies_success(self):
        """Test successful loading strategies retrieval."""
        result = await get_available_strategies()

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
    async def test_get_priorities_success(self):
        """Test successful priorities retrieval."""
        result = await get_priorities()

        assert result["success"] is True
        assert result["total_priorities"] > 0
        assert len(result["priorities"]) > 0

        # Check if all priorities have required fields
        for priority in result["priorities"]:
            assert "value" in priority
            assert "name" in priority
            assert "description" in priority
            assert "weight" in priority


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_start_progressive_load_default_values(self, mock_db):
        """Test progressive load start with default values."""
        load_data = {
            "visualization_id": "viz_123"
            # No other fields - should use defaults
        }

        with patch("src.api.progressive.progressive_loading_service") as mock_service:
            mock_service.start_progressive_load.return_value = {
                "success": True,
                "task_id": "task_123",
            }

            result = await start_progressive_load(load_data, mock_db)

            assert result["success"] is True
            # Verify default parameters were used
            mock_service.start_progressive_load.assert_called_once()
            call_args = mock_service.start_progressive_load.call_args[0]
            assert call_args[1] == LoadingStrategy.LOD_BASED  # default strategy
            assert call_args[2] == DetailLevel.LOW  # default detail level
            assert call_args[4] == LoadingPriority.MEDIUM  # default priority

    @pytest.mark.asyncio
    async def test_update_viewport_invalid_task(self):
        """Test viewport update for non-existent task."""
        with patch("src.api.progressive.progressive_loading_service") as mock_service:
            mock_service.update_viewport.return_value = {
                "success": False,
                "error": "Task not found",
            }

            viewport_data = {"x": 0, "y": 0, "width": 800, "height": 600}

            with pytest.raises(HTTPException) as exc_info:
                await update_viewport("nonexistent_task", viewport_data)

            assert exc_info.value.status_code == 404
            assert "Task not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_set_detail_level_invalid_level(self):
        """Test detail level setting with invalid level."""
        detail_data = {"detail_level": "invalid_level", "reload": True}

        with pytest.raises(HTTPException) as exc_info:
            await set_detail_level("task_123", detail_data)

        assert exc_info.value.status_code == 400
        assert "Invalid detail_level" in str(exc_info.value.detail)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
