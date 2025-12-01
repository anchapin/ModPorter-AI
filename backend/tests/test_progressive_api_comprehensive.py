"""
Comprehensive tests for progressive.py API module
Tests all progressive loading endpoints including task management, strategy configuration, and utility functions.
"""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from src.api.progressive import router
from src.services.progressive_loading import (
    LoadingStrategy,
    DetailLevel,
    LoadingPriority,
)

# Test client setup
client = TestClient(router)


class TestProgressiveLoading:
    """Test progressive loading endpoints"""

    @pytest.mark.asyncio
    async def test_start_progressive_load_success(self):
        """Test successful progressive load start"""
        mock_service = AsyncMock()
        mock_service.start_progressive_load.return_value = {
            "success": True,
            "task_id": "task_123",
            "status": "started",
            "estimated_duration": 30,
        }

        with patch("src.api.progressive.progressive_loading_service", mock_service):
            load_data = {
                "visualization_id": "viz_123",
                "loading_strategy": "lod_based",
                "detail_level": "medium",
                "priority": "high",
                "viewport": {"x": 0, "y": 0, "width": 800, "height": 600},
            }

            response = client.post("/progressive/load", json=load_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "task_id" in data

    @pytest.mark.asyncio
    async def test_start_progressive_load_missing_visualization_id(self):
        """Test progressive load without visualization_id"""
        load_data = {"loading_strategy": "lod_based", "detail_level": "medium"}

        response = client.post("/progressive/load", json=load_data)

        assert response.status_code == 400
        assert "visualization_id is required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_start_progressive_load_invalid_strategy(self):
        """Test progressive load with invalid loading strategy"""
        load_data = {
            "visualization_id": "viz_123",
            "loading_strategy": "invalid_strategy",
            "detail_level": "medium",
        }

        response = client.post("/progressive/load", json=load_data)

        assert response.status_code == 400
        assert "Invalid loading_strategy" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_start_progressive_load_invalid_detail_level(self):
        """Test progressive load with invalid detail level"""
        load_data = {
            "visualization_id": "viz_123",
            "loading_strategy": "lod_based",
            "detail_level": "invalid_level",
        }

        response = client.post("/progressive/load", json=load_data)

        assert response.status_code == 400
        assert "Invalid detail_level" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_start_progressive_load_invalid_priority(self):
        """Test progressive load with invalid priority"""
        load_data = {
            "visualization_id": "viz_123",
            "loading_strategy": "lod_based",
            "detail_level": "medium",
            "priority": "invalid_priority",
        }

        response = client.post("/progressive/load", json=load_data)

        assert response.status_code == 400
        assert "Invalid priority" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_start_progressive_load_service_failure(self):
        """Test progressive load when service returns failure"""
        mock_service = AsyncMock()
        mock_service.start_progressive_load.return_value = {
            "success": False,
            "error": "Visualization not found",
        }

        with patch("src.api.progressive.progressive_loading_service", mock_service):
            load_data = {
                "visualization_id": "nonexistent",
                "loading_strategy": "lod_based",
                "detail_level": "medium",
            }

            response = client.post("/progressive/load", json=load_data)

            assert response.status_code == 400
            assert "Visualization not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_loading_progress_success(self):
        """Test successful loading progress retrieval"""
        mock_service = AsyncMock()
        mock_service.get_loading_progress.return_value = {
            "success": True,
            "task_id": "task_123",
            "status": "running",
            "progress_percentage": 45.5,
            "items_loaded": 455,
            "total_items": 1000,
            "elapsed_time": 12.3,
            "estimated_remaining": 15.7,
        }

        with patch("src.api.progressive.progressive_loading_service", mock_service):
            response = client.get("/progressive/tasks/task_123")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["progress_percentage"] == 45.5

    @pytest.mark.asyncio
    async def test_get_loading_progress_not_found(self):
        """Test loading progress for non-existent task"""
        mock_service = AsyncMock()
        mock_service.get_loading_progress.return_value = {
            "success": False,
            "error": "Task not found",
        }

        with patch("src.api.progressive.progressive_loading_service", mock_service):
            response = client.get("/progressive/tasks/nonexistent")

            assert response.status_code == 404
            assert "Task not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_loading_level_success(self):
        """Test successful loading level update"""
        mock_service = AsyncMock()
        mock_service.update_loading_level.return_value = {
            "success": True,
            "task_id": "task_123",
            "old_level": "medium",
            "new_level": "high",
            "reloaded_items": 250,
        }

        with patch("src.api.progressive.progressive_loading_service", mock_service):
            update_data = {
                "detail_level": "high",
                "viewport": {"x": 100, "y": 100, "width": 600, "height": 400},
            }

            response = client.post(
                "/progressive/tasks/task_123/update-level", json=update_data
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["new_level"] == "high"

    @pytest.mark.asyncio
    async def test_update_loading_level_missing_level(self):
        """Test loading level update without detail level"""
        update_data = {"viewport": {"x": 100, "y": 100}}

        response = client.post(
            "/progressive/tasks/task_123/update-level", json=update_data
        )

        assert response.status_code == 400
        assert "detail_level is required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_loading_level_invalid_level(self):
        """Test loading level update with invalid level"""
        update_data = {"detail_level": "invalid_level"}

        response = client.post(
            "/progressive/tasks/task_123/update-level", json=update_data
        )

        assert response.status_code == 400
        assert "Invalid detail_level" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_preload_adjacent_areas_success(self):
        """Test successful adjacent areas preload"""
        mock_service = AsyncMock()
        mock_service.preload_adjacent_areas.return_value = {
            "success": True,
            "visualization_id": "viz_123",
            "preloaded_areas": 4,
            "estimated_items": 200,
            "preload_distance": 2.0,
        }

        with patch("src.api.progressive.progressive_loading_service", mock_service):
            preload_data = {
                "visualization_id": "viz_123",
                "current_viewport": {"x": 0, "y": 0, "width": 800, "height": 600},
                "preload_distance": 2.0,
                "detail_level": "low",
            }

            response = client.post("/progressive/preload", json=preload_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["preloaded_areas"] == 4

    @pytest.mark.asyncio
    async def test_preload_adjacent_areas_missing_params(self):
        """Test preload with missing required parameters"""
        preload_data = {
            "visualization_id": "viz_123"
            # Missing current_viewport
        }

        response = client.post("/progressive/preload", json=preload_data)

        assert response.status_code == 400
        assert "current_viewport are required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_preload_adjacent_areas_invalid_detail_level(self):
        """Test preload with invalid detail level"""
        preload_data = {
            "visualization_id": "viz_123",
            "current_viewport": {"x": 0, "y": 0},
            "detail_level": "invalid_level",
        }

        response = client.post("/progressive/preload", json=preload_data)

        assert response.status_code == 400
        assert "Invalid detail_level" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_loading_statistics_success(self):
        """Test successful loading statistics retrieval"""
        mock_service = AsyncMock()
        mock_service.get_loading_statistics.return_value = {
            "success": True,
            "statistics": {
                "total_loads": 150,
                "average_load_time": 2.3,
                "success_rate": 95.5,
                "strategy_usage": {
                    "lod_based": 60,
                    "distance_based": 30,
                    "importance_based": 10,
                },
            },
        }

        with patch("src.api.progressive.progressive_loading_service", mock_service):
            response = client.get("/progressive/statistics")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "statistics" in data

    @pytest.mark.asyncio
    async def test_get_loading_statistics_with_filter(self):
        """Test loading statistics with visualization filter"""
        mock_service = AsyncMock()
        mock_service.get_loading_statistics.return_value = {
            "success": True,
            "statistics": {
                "total_loads": 25,
                "average_load_time": 1.8,
                "success_rate": 96.0,
            },
        }

        with patch("src.api.progressive.progressive_loading_service", mock_service):
            response = client.get("/progressive/statistics?visualization_id=viz_123")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_loading_statistics_failure(self):
        """Test loading statistics retrieval failure"""
        mock_service = AsyncMock()
        mock_service.get_loading_statistics.return_value = {
            "success": False,
            "error": "Statistics service unavailable",
        }

        with patch("src.api.progressive.progressive_loading_service", mock_service):
            response = client.get("/progressive/statistics")

            assert response.status_code == 500
            assert "Statistics service unavailable" in response.json()["detail"]


class TestProgressiveStrategyConfig:
    """Test strategy and configuration endpoints"""

    @pytest.mark.asyncio
    async def test_get_loading_strategies_success(self):
        """Test successful retrieval of loading strategies"""
        response = client.get("/progressive/loading-strategies")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "loading_strategies" in data
        assert len(data["loading_strategies"]) > 0

        # Check structure of strategies
        strategy = data["loading_strategies"][0]
        assert "value" in strategy
        assert "name" in strategy
        assert "description" in strategy
        assert "use_cases" in strategy
        assert "recommended_for" in strategy
        assert "performance_characteristics" in strategy

    @pytest.mark.asyncio
    async def test_get_detail_levels_success(self):
        """Test successful retrieval of detail levels"""
        response = client.get("/progressive/detail-levels")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "detail_levels" in data
        assert len(data["detail_levels"]) > 0

        # Check structure of detail levels
        level = data["detail_levels"][0]
        assert "value" in level
        assert "name" in level
        assert "description" in level
        assert "item_types" in level
        assert "performance_impact" in level
        assert "memory_usage" in level
        assert "recommended_conditions" in level

    @pytest.mark.asyncio
    async def test_get_loading_priorities_success(self):
        """Test successful retrieval of loading priorities"""
        response = client.get("/progressive/priorities")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "loading_priorities" in data
        assert len(data["loading_priorities"]) > 0

        # Check structure of priorities
        priority = data["loading_priorities"][0]
        assert "value" in priority
        assert "name" in priority
        assert "description" in priority
        assert "use_cases" in priority
        assert "expected_response_time" in priority
        assert "resource_allocation" in priority


class TestProgressiveUtilities:
    """Test progressive loading utility endpoints"""

    @pytest.mark.asyncio
    async def test_estimate_load_time_success(self):
        """Test successful load time estimation"""
        estimate_data = {
            "visualization_id": "viz_123",
            "loading_strategy": "lod_based",
            "detail_level": "medium",
            "viewport": {"x": 0, "y": 0, "width": 800, "height": 600},
            "estimated_total_items": 1000,
        }

        response = client.post("/progressive/estimate-load", json=estimate_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "estimation" in data

        estimation = data["estimation"]
        assert "total_items" in estimation
        assert "loading_strategy" in estimation
        assert "detail_level" in estimation
        assert "estimated_time_seconds" in estimation
        assert "estimated_memory_usage_mb" in estimation
        assert "chunk_recommendations" in estimation
        assert "performance_tips" in estimation

    @pytest.mark.asyncio
    async def test_estimate_load_time_missing_visualization_id(self):
        """Test load time estimation without visualization ID"""
        estimate_data = {"loading_strategy": "lod_based", "detail_level": "medium"}

        response = client.post("/progressive/estimate-load", json=estimate_data)

        assert response.status_code == 400
        assert "visualization_id is required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_estimate_load_time_invalid_strategy(self):
        """Test load time estimation with invalid strategy"""
        estimate_data = {
            "visualization_id": "viz_123",
            "loading_strategy": "invalid_strategy",
            "detail_level": "medium",
        }

        response = client.post("/progressive/estimate-load", json=estimate_data)

        assert response.status_code == 400
        assert "Invalid" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_estimate_load_time_with_historical_data(self):
        """Test load time estimation with total items estimation"""
        estimate_data = {
            "visualization_id": "viz_123",
            "loading_strategy": "distance_based",
            "detail_level": "high",
            # No total_items provided - should be estimated
        }

        response = client.post("/progressive/estimate-load", json=estimate_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        estimation = data["estimation"]
        assert estimation["total_items"] > 0  # Should have estimated value
        assert estimation["loading_strategy"] == "distance_based"

    @pytest.mark.asyncio
    async def test_optimize_loading_settings_success(self):
        """Test successful loading settings optimization"""
        optimization_data = {
            "current_performance": {
                "average_load_time_ms": 3000,
                "memory_usage_mb": 600,
                "network_usage_mbps": 80,
            },
            "system_capabilities": {
                "available_memory_mb": 4096,
                "cpu_cores": 8,
                "network_speed_mbps": 100,
            },
            "user_preferences": {
                "quality_preference": "balanced",
                "interactivity_preference": "high",
            },
        }

        response = client.post("/progressive/optimize-settings", json=optimization_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "optimized_settings" in data
        assert "analysis" in data
        assert "recommended_strategy" in data
        assert "expected_improvements" in data

        # Check optimized settings structure
        settings = data["optimized_settings"]
        assert isinstance(settings, dict)

        # Check analysis structure
        analysis = data["analysis"]
        assert "current_performance" in analysis
        assert "system_capabilities" in analysis
        assert "user_preferences" in analysis

    @pytest.mark.asyncio
    async def test_optimize_loading_settings_minimal_data(self):
        """Test optimization with minimal data"""
        optimization_data = {}

        response = client.post("/progressive/optimize-settings", json=optimization_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "optimized_settings" in data

    @pytest.mark.asyncio
    async def test_optimize_loading_settings_performance_focused(self):
        """Test optimization for performance-focused scenario"""
        optimization_data = {
            "current_performance": {
                "average_load_time_ms": 5000,  # Slow
                "memory_usage_mb": 3500,  # High usage
                "network_usage_mbps": 90,  # High usage
            },
            "system_capabilities": {
                "available_memory_mb": 4096,
                "cpu_cores": 4,
                "network_speed_mbps": 50,
            },
            "user_preferences": {
                "quality_preference": "performance",
                "interactivity_preference": "low",
            },
        }

        response = client.post("/progressive/optimize-settings", json=optimization_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        settings = data["optimized_settings"]
        # Should include performance optimizations
        if "performance" in settings:
            assert "recommended_loading_strategy" in settings["performance"]

    @pytest.mark.asyncio
    async def test_get_progressive_loading_health_success(self):
        """Test successful progressive loading health check"""
        mock_service = AsyncMock()
        mock_service.active_tasks = {"task1": {}, "task2": {}}
        mock_service.loading_caches = {"cache1": {}, "cache2": {}, "cache3": {}}
        mock_service.viewport_history = {"viz1": ["view1", "view2"], "viz2": ["view3"]}
        mock_service.average_load_time = 2000  # 2 seconds
        mock_service.total_loads = 150
        mock_service.background_thread = True

        with patch("src.api.progressive.progressive_loading_service", mock_service):
            response = client.get("/progressive/health")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "health_status" in data
            assert "issues" in data
            assert "metrics" in data
            assert "thresholds" in data

            # Check health status is valid
            assert data["health_status"] in ["healthy", "warning", "critical"]

            # Check metrics structure
            metrics = data["metrics"]
            assert "active_tasks" in metrics
            assert "total_caches" in metrics
            assert "average_load_time_ms" in metrics

    @pytest.mark.asyncio
    async def test_get_progressive_loading_health_warning_status(self):
        """Test health check with warning status due to high metrics"""
        mock_service = AsyncMock()
        # Simulate high metrics that should trigger warning
        mock_service.active_tasks = {
            f"task{i}": {} for i in range(25)
        }  # Over threshold
        mock_service.loading_caches = {
            f"cache{i}": {} for i in range(120)
        }  # Over threshold
        mock_service.average_load_time = 6000  # Over threshold
        mock_service.total_loads = 200
        mock_service.background_thread = True
        mock_service.viewport_history = {
            "viz1": ["view1", "view2", "view3", "view4", "view5"]
        }

        with patch("src.api.progressive.progressive_loading_service", mock_service):
            response = client.get("/progressive/health")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            # Should be warning due to high metrics
            assert data["health_status"] == "warning"
            assert len(data["issues"]) > 0


class TestProgressiveErrorHandling:
    """Test error handling in progressive API"""

    @pytest.mark.asyncio
    async def test_service_exception_handling(self):
        """Test handling of service exceptions"""
        mock_service = AsyncMock()
        mock_service.start_progressive_load.side_effect = Exception("Service error")

        with patch("src.api.progressive.progressive_loading_service", mock_service):
            load_data = {
                "visualization_id": "viz_123",
                "loading_strategy": "lod_based",
                "detail_level": "medium",
            }

            response = client.post("/progressive/load", json=load_data)

            assert response.status_code == 500
            assert "Progressive load failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_progress_exception(self):
        """Test exception handling in get progress"""
        mock_service = AsyncMock()
        mock_service.get_loading_progress.side_effect = Exception("Database error")

        with patch("src.api.progressive.progressive_loading_service", mock_service):
            response = client.get("/progressive/tasks/task_123")

            assert response.status_code == 500
            assert "Failed to get loading progress" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_level_exception(self):
        """Test exception handling in level update"""
        mock_service = AsyncMock()
        mock_service.update_loading_level.side_effect = Exception("Update failed")

        with patch("src.api.progressive.progressive_loading_service", mock_service):
            update_data = {"detail_level": "high"}

            response = client.post(
                "/progressive/tasks/task_123/update-level", json=update_data
            )

            assert response.status_code == 500
            assert "Loading level update failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_preload_exception(self):
        """Test exception handling in preload"""
        mock_service = AsyncMock()
        mock_service.preload_adjacent_areas.side_effect = Exception("Preload failed")

        with patch("src.api.progressive.progressive_loading_service", mock_service):
            preload_data = {
                "visualization_id": "viz_123",
                "current_viewport": {"x": 0, "y": 0},
            }

            response = client.post("/progressive/preload", json=preload_data)

            assert response.status_code == 500
            assert "Preloading failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_strategies_exception(self):
        """Test exception handling in get strategies"""
        with patch(
            "src.api.progressive.LoadingStrategy", side_effect=Exception("Enum error")
        ):
            response = client.get("/progressive/loading-strategies")

            assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_estimate_load_exception(self):
        """Test exception handling in load estimation"""
        estimate_data = {
            "visualization_id": "viz_123",
            "loading_strategy": "lod_based",
            "detail_level": "medium",
        }

        # Mock the estimation method to raise exception
        with patch(
            "src.api.progressive.progressive_loading_service.start_progressive_load",
            side_effect=Exception("Estimation failed"),
        ):
            response = client.post("/progressive/estimate-load", json=estimate_data)

            assert response.status_code == 500
            assert "Load time estimation failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_optimize_settings_exception(self):
        """Test exception handling in settings optimization"""
        optimization_data = {"current_performance": {"load_time": 2000}}

        response = client.post("/progressive/optimize-settings", json=optimization_data)

        assert response.status_code == 500
        assert "Settings optimization failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_health_check_exception(self):
        """Test exception handling in health check"""
        mock_service = AsyncMock()
        mock_service.active_tasks.side_effect = Exception("Health check failed")

        with patch("src.api.progressive.progressive_loading_service", mock_service):
            response = client.get("/progressive/health")

            assert response.status_code == 500
            assert "Health check failed" in response.json()["detail"]


class TestProgressiveHelperFunctions:
    """Test progressive API helper functions"""

    def test_get_strategy_description(self):
        """Test strategy description helper"""
        from src.api.progressive import _get_strategy_description

        desc = _get_strategy_description(LoadingStrategy.LOD_BASED)
        assert "level of detail" in desc

        desc = _get_strategy_description(LoadingStrategy.DISTANCE_BASED)
        assert "distance from viewport" in desc

        desc = _get_strategy_description("UNKNOWN")
        assert desc == "Unknown loading strategy"

    def test_get_strategy_use_cases(self):
        """Test strategy use cases helper"""
        from src.api.progressive import _get_strategy_use_cases

        use_cases = _get_strategy_use_cases(LoadingStrategy.LOD_BASED)
        assert "Large graphs" in use_cases
        assert "Memory-constrained environments" in use_cases

        use_cases = _get_strategy_use_cases("UNKNOWN")
        assert use_cases == ["General use"]

    def test_get_strategy_recommendations(self):
        """Test strategy recommendations helper"""
        from src.api.progressive import _get_strategy_recommendations

        rec = _get_strategy_recommendations(LoadingStrategy.LOD_BASED)
        assert "dynamic zoom" in rec

        rec = _get_strategy_recommendations("UNKNOWN")
        assert rec == "General purpose strategy"

    def test_get_strategy_performance(self):
        """Test strategy performance characteristics"""
        from src.api.progressive import _get_strategy_performance

        perf = _get_strategy_performance(LoadingStrategy.LOD_BASED)
        assert "speed" in perf
        assert "memory_efficiency" in perf
        assert "scalability" in perf

        perf = _get_strategy_performance("UNKNOWN")
        assert perf["speed"] == "medium"

    def test_get_detail_level_description(self):
        """Test detail level description helper"""
        from src.api.progressive import _get_detail_level_description

        desc = _get_detail_level_description(DetailLevel.MINIMAL)
        assert "essential" in desc

        desc = _get_detail_level_description(DetailLevel.FULL)
        assert "all available data" in desc

        desc = _get_detail_level_description("UNKNOWN")
        assert desc == "Unknown detail level"

    def test_get_detail_level_items(self):
        """Test detail level items helper"""
        from src.api.progressive import _get_detail_level_items

        items = _get_detail_level_items(DetailLevel.MINIMAL)
        assert "node_ids" in items
        assert "basic_positions" in items

        items = _get_detail_level_items(DetailLevel.FULL)
        assert "complete_data" in items
        assert "metadata" in items

    def test_get_detail_level_performance(self):
        """Test detail level performance helper"""
        from src.api.progressive import _get_detail_level_performance

        perf = _get_detail_level_performance(DetailLevel.MINIMAL)
        assert perf == "Very low"

        perf = _get_detail_level_performance(DetailLevel.FULL)
        assert perf == "Very high"

    def test_get_detail_level_memory(self):
        """Test detail level memory helper"""
        from src.api.progressive import _get_detail_level_memory

        memory = _get_detail_level_memory(DetailLevel.LOW)
        assert "Low" in memory
        assert "200-500 MB" in memory

        memory = _get_detail_level_memory(DetailLevel.FULL)
        assert "Very high" in memory
        assert "2-5GB" in memory

    def test_get_detail_level_conditions(self):
        """Test detail level conditions helper"""
        from src.api.progressive import _get_detail_level_conditions

        conditions = _get_detail_level_conditions(DetailLevel.MINIMAL)
        assert "Very large graphs" in conditions
        assert "Low memory devices" in conditions

        conditions = _get_detail_level_conditions(DetailLevel.FULL)
        assert "Very small graphs" in conditions
        assert "High-performance devices" in conditions

    def test_get_priority_description(self):
        """Test priority description helper"""
        from src.api.progressive import _get_priority_description

        desc = _get_priority_description(LoadingPriority.CRITICAL)
        assert "highest system priority" in desc

        desc = _get_priority_description(LoadingPriority.BACKGROUND)
        assert "background" in desc

        desc = _get_priority_description("UNKNOWN")
        assert desc == "Unknown priority"

    def test_get_priority_use_cases(self):
        """Test priority use cases helper"""
        from src.api.progressive import _get_priority_use_cases

        use_cases = _get_priority_use_cases(LoadingPriority.CRITICAL)
        assert "User-focused content" in use_cases
        assert "Current viewport" in use_cases

        use_cases = _get_priority_use_cases("UNKNOWN")
        assert use_cases == ["General use"]

    def test_get_priority_response_time(self):
        """Test priority response time helper"""
        from src.api.progressive import _get_priority_response_time

        response_time = _get_priority_response_time(LoadingPriority.CRITICAL)
        assert "< 100ms" in response_time

        response_time = _get_priority_response_time(LoadingPriority.BACKGROUND)
        assert "> 10s" in response_time

    def test_get_priority_resources(self):
        """Test priority resources helper"""
        from src.api.progressive import _get_priority_resources

        resources = _get_priority_resources(LoadingPriority.CRITICAL)
        assert "Maximum resources" in resources
        assert "80% CPU" in resources

        resources = _get_priority_resources(LoadingPriority.BACKGROUND)
        assert "Minimal resources" in resources
        assert "10% CPU" in resources


class TestProgressiveIntegration:
    """Integration tests for progressive API workflows"""

    @pytest.mark.asyncio
    async def test_complete_progressive_load_workflow(self):
        """Test complete progressive loading workflow"""
        mock_service = AsyncMock()

        # Mock different service responses for workflow steps
        mock_service.start_progressive_load.return_value = {
            "success": True,
            "task_id": "workflow_task_123",
            "status": "started",
        }
        mock_service.get_loading_progress.return_value = {
            "success": True,
            "task_id": "workflow_task_123",
            "status": "running",
            "progress_percentage": 100.0,
        }
        mock_service.update_loading_level.return_value = {
            "success": True,
            "task_id": "workflow_task_123",
            "new_level": "high",
        }

        with patch("src.api.progressive.progressive_loading_service", mock_service):
            # Step 1: Start progressive load
            load_data = {
                "visualization_id": "viz_123",
                "loading_strategy": "lod_based",
                "detail_level": "medium",
                "priority": "high",
            }

            load_response = client.post("/progressive/load", json=load_data)
            assert load_response.status_code == 200

            task_id = load_response.json()["task_id"]

            # Step 2: Check progress
            progress_response = client.get(f"/progressive/tasks/{task_id}")
            assert progress_response.status_code == 200

            # Step 3: Update loading level
            update_data = {"detail_level": "high"}
            update_response = client.post(
                f"/progressive/tasks/{task_id}/update-level", json=update_data
            )
            assert update_response.status_code == 200

    @pytest.mark.asyncio
    async def test_preload_workflow(self):
        """Test preload adjacent areas workflow"""
        mock_service = AsyncMock()
        mock_service.preload_adjacent_areas.return_value = {
            "success": True,
            "preloaded_areas": 6,
            "estimated_items": 300,
        }

        with patch("src.api.progressive.progressive_loading_service", mock_service):
            preload_data = {
                "visualization_id": "viz_123",
                "current_viewport": {"x": 0, "y": 0, "width": 800, "height": 600},
                "preload_distance": 3.0,
                "detail_level": "low",
            }

            response = client.post("/progressive/preload", json=preload_data)
            assert response.status_code == 200
            assert response.json()["preloaded_areas"] == 6

    @pytest.mark.asyncio
    async def test_configuration_workflow(self):
        """Test strategy configuration workflow"""
        # Step 1: Get available strategies
        strategies_response = client.get("/progressive/loading-strategies")
        assert strategies_response.status_code == 200
        strategies = strategies_response.json()["loading_strategies"]

        # Step 2: Get detail levels
        levels_response = client.get("/progressive/detail-levels")
        assert levels_response.status_code == 200
        levels = levels_response.json()["detail_levels"]

        # Step 3: Get priorities
        priorities_response = client.get("/progressive/priorities")
        assert priorities_response.status_code == 200
        priorities = priorities_response.json()["loading_priorities"]

        # Verify structure
        assert len(strategies) > 0
        assert len(levels) > 0
        assert len(priorities) > 0

        # Verify each has required fields
        for strategy in strategies:
            assert "value" in strategy
            assert "description" in strategy

        for level in levels:
            assert "value" in level
            assert "memory_usage" in level

        for priority in priorities:
            assert "value" in priority
            assert "expected_response_time" in priority

    @pytest.mark.asyncio
    async def test_estimation_and_optimization_workflow(self):
        """Test load estimation and optimization workflow"""
        # Step 1: Estimate load time
        estimate_data = {
            "visualization_id": "viz_123",
            "loading_strategy": "hybrid",
            "detail_level": "high",
            "estimated_total_items": 5000,
        }

        estimate_response = client.post(
            "/progressive/estimate-load", json=estimate_data
        )
        assert estimate_response.status_code == 200
        estimation = estimate_response.json()["estimation"]

        # Step 2: Optimize settings based on estimation
        optimization_data = {
            "current_performance": {
                "average_load_time_ms": estimation["estimated_time_seconds"] * 1000,
                "memory_usage_mb": estimation["estimated_memory_usage_mb"],
            },
            "system_capabilities": {"available_memory_mb": 8192, "cpu_cores": 8},
            "user_preferences": {"quality_preference": "balanced"},
        }

        optimize_response = client.post(
            "/progressive/optimize-settings", json=optimization_data
        )
        assert optimize_response.status_code == 200
        optimizations = optimize_response.json()["optimized_settings"]

        # Verify optimization results
        assert isinstance(optimizations, dict)

    @pytest.mark.asyncio
    async def test_mixed_strategies_workflow(self):
        """Test different loading strategies in workflow"""
        mock_service = AsyncMock()
        mock_service.start_progressive_load.return_value = {
            "success": True,
            "task_id": "strategy_test_123",
        }

        with patch("src.api.progressive.progressive_loading_service", mock_service):
            strategies = ["lod_based", "distance_based", "importance_based", "hybrid"]

            for strategy in strategies:
                load_data = {
                    "visualization_id": "viz_123",
                    "loading_strategy": strategy,
                    "detail_level": "medium",
                }

                response = client.post("/progressive/load", json=load_data)
                assert response.status_code == 200


class TestProgressivePerformance:
    """Test progressive API performance characteristics"""

    @pytest.mark.asyncio
    async def test_large_visualization_estimation(self):
        """Test estimation for very large visualization"""
        estimate_data = {
            "visualization_id": "large_viz",
            "loading_strategy": "lod_based",
            "detail_level": "minimal",
            "estimated_total_items": 100000,
        }

        response = client.post("/progressive/estimate-load", json=estimate_data)

        assert response.status_code == 200
        data = response.json()
        estimation = data["estimation"]

        # Verify estimates are reasonable for large dataset
        assert estimation["total_items"] == 100000
        assert estimation["estimated_time_seconds"] > 0
        assert estimation["estimated_memory_usage_mb"] > 0

    @pytest.mark.asyncio
    async def test_multiple_concurrent_loads(self):
        """Test handling multiple concurrent load requests"""
        mock_service = AsyncMock()
        mock_service.start_progressive_load.return_value = {
            "success": True,
            "task_id": "concurrent_task",
        }

        with patch("src.api.progressive.progressive_loading_service", mock_service):
            load_data = {
                "visualization_id": "viz_123",
                "loading_strategy": "lod_based",
                "detail_level": "medium",
            }

            # Simulate concurrent requests
            responses = []
            for i in range(10):
                response = client.post("/progressive/load", json=load_data)
                responses.append(response)

            # All should succeed
            for response in responses:
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_configuration_responses_performance(self):
        """Test performance of configuration endpoint responses"""
        import time

        # Test strategies endpoint performance
        start_time = time.time()
        response = client.get("/progressive/loading-strategies")
        strategies_time = time.time() - start_time
        assert response.status_code == 200
        assert strategies_time < 1.0  # Should respond quickly

        # Test detail levels endpoint performance
        start_time = time.time()
        response = client.get("/progressive/detail-levels")
        levels_time = time.time() - start_time
        assert response.status_code == 200
        assert levels_time < 1.0

        # Test priorities endpoint performance
        start_time = time.time()
        response = client.get("/progressive/priorities")
        priorities_time = time.time() - start_time
        assert response.status_code == 200
        assert priorities_time < 1.0

    @pytest.mark.asyncio
    async def test_health_check_monitoring(self):
        """Test health check with various system states"""
        # Test with different service states
        test_states = [
            {"active_tasks": 5, "caches": 10, "load_time": 1000, "healthy": True},
            {"active_tasks": 25, "caches": 50, "load_time": 3000, "healthy": False},
            {"active_tasks": 50, "caches": 150, "load_time": 8000, "healthy": False},
        ]

        for state in test_states:
            mock_service = AsyncMock()
            mock_service.active_tasks = {
                f"task{i}": {} for i in range(state["active_tasks"])
            }
            mock_service.loading_caches = {
                f"cache{i}": {} for i in range(state["caches"])
            }
            mock_service.average_load_time = state["load_time"]
            mock_service.total_loads = 100
            mock_service.background_thread = True
            mock_service.viewport_history = {"viz1": ["view1"]}

            with patch("src.api.progressive.progressive_loading_service", mock_service):
                response = client.get("/progressive/health")
                assert response.status_code == 200

                data = response.json()
                assert data["success"] is True
                assert "health_status" in data
                assert "metrics" in data

                # Verify metrics match expected values
                metrics = data["metrics"]
                assert metrics["active_tasks"] == state["active_tasks"]
                assert metrics["total_caches"] == state["caches"]
                assert metrics["average_load_time_ms"] == state["load_time"]
