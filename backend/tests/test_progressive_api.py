"""
Comprehensive tests for progressive.py API endpoints.

This test suite provides extensive coverage for the Progressive Loading API,
ensuring all loading strategy, viewport management, and optimization endpoints are tested.

Coverage Target: ≥80% line coverage for 259 statements
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call, mock_open
from fastapi.testclient import TestClient
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from io import BytesIO

from src.api.progressive import router
from src.services.progressive_loading import (
    progressive_loading_service, LoadingStrategy, DetailLevel, LoadingPriority
)


class TestProgressiveAPI:
    """Test Progressive Loading API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create a test client for progressive API."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def sample_load_data(self):
        """Sample progressive load data for testing."""
        return {
            "visualization_id": "viz123",
            "loading_strategy": "lod_based",
            "detail_level": "medium",
            "priority": "high",
            "viewport": {
                "x": 0, "y": 0, "width": 800, "height": 600,
                "zoom": 1.0
            },
            "parameters": {
                "max_nodes": 1000,
                "cache_size": "100MB",
                "stream_buffer": 50
            }
        }

    # Progressive Loading Endpoints Tests
    
    async def test_start_progressive_load_success(self, client, mock_db, sample_load_data):
        """Test successful progressive load start."""
        with patch('src.api.progressive.get_db') as mock_get_db, \
             patch.object(progressive_loading_service, 'start_progressive_load') as mock_load:
            
            mock_get_db.return_value = mock_db
            mock_load.return_value = {
                "success": True,
                "task_id": "task123",
                "status": "initializing",
                "estimated_completion": (
                    datetime.utcnow() + timedelta(minutes=5)
                ).isoformat()
            }
            
            response = client.post("/progressive/load", json=sample_load_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "task_id" in data
            assert data["status"] == "initializing"
    
    def test_start_progressive_load_missing_visualization_id(self, client, mock_db):
        """Test progressive load start with missing visualization_id."""
        with patch('src.api.progressive.get_db') as mock_get_db:
            mock_get_db.return_value = mock_db
            
            load_data = {
                "loading_strategy": "lod_based",
                "detail_level": "medium"
            }
            
            response = client.post("/progressive/load", json=load_data)
            
            assert response.status_code == 400
            assert "visualization_id is required" in response.json()["detail"]
    
    def test_start_progressive_load_invalid_strategy(self, client, mock_db):
        """Test progressive load start with invalid strategy."""
        with patch('src.api.progressive.get_db') as mock_get_db:
            mock_get_db.return_value = mock_db
            
            load_data = {
                "visualization_id": "viz123",
                "loading_strategy": "invalid_strategy"
            }
            
            response = client.post("/progressive/load", json=load_data)
            
            assert response.status_code == 400
            assert "Invalid loading_strategy" in response.json()["detail"]
    
    def test_start_progressive_load_invalid_detail_level(self, client, mock_db):
        """Test progressive load start with invalid detail level."""
        with patch('src.api.progressive.get_db') as mock_get_db:
            mock_get_db.return_value = mock_db
            
            load_data = {
                "visualization_id": "viz123",
                "detail_level": "invalid_level"
            }
            
            response = client.post("/progressive/load", json=load_data)
            
            assert response.status_code == 400
            assert "Invalid detail_level" in response.json()["detail"]
    
    def test_start_progressive_load_invalid_priority(self, client, mock_db):
        """Test progressive load start with invalid priority."""
        with patch('src.api.progressive.get_db') as mock_get_db:
            mock_get_db.return_value = mock_db
            
            load_data = {
                "visualization_id": "viz123",
                "priority": "invalid_priority"
            }
            
            response = client.post("/progressive/load", json=load_data)
            
            assert response.status_code == 400
            assert "Invalid priority" in response.json()["detail"]
    
    def test_start_progressive_load_service_error(self, client, mock_db, sample_load_data):
        """Test progressive load start when service raises an error."""
        with patch('src.api.progressive.get_db') as mock_get_db, \
             patch.object(progressive_loading_service, 'start_progressive_load') as mock_load:
            
            mock_get_db.return_value = mock_db
            mock_load.return_value = {
                "success": False,
                "error": "Service unavailable"
            }
            
            response = client.post("/progressive/load", json=sample_load_data)
            
            assert response.status_code == 400
            assert "Service unavailable" in response.json()["detail"]
    
    async def test_get_load_task_status_success(self, client):
        """Test successful load task status retrieval."""
        with patch.object(progressive_loading_service, 'get_task_status') as mock_status:
            
            mock_status.return_value = {
                "success": True,
                "task_id": "task123",
                "status": "loading",
                "progress": 45.5,
                "loaded_nodes": 455,
                "total_nodes": 1000,
                "current_detail_level": "medium",
                "memory_usage": "45MB"
            }
            
            response = client.get("/progressive/tasks/task123")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["task_id"] == "task123"
            assert data["status"] == "loading"
            assert data["progress"] == 45.5
    
    async def test_get_load_task_status_not_found(self, client):
        """Test load task status retrieval when task not found."""
        with patch.object(progressive_loading_service, 'get_task_status') as mock_status:
            
            mock_status.return_value = {
                "success": False,
                "error": "Task not found"
            }
            
            response = client.get("/progressive/tasks/nonexistent")
            
            assert response.status_code == 404
            assert "Task not found" in response.json()["detail"]
    
    def test_update_loading_level_success(self, client):
        """Test successful loading level update."""
        with patch.object(progressive_loading_service, 'update_loading_level') as mock_update:
            
            mock_update.return_value = {
                "success": True,
                "task_id": "task123",
                "previous_level": "medium",
                "new_level": "high",
                "updated_at": datetime.utcnow().isoformat()
            }
            
            update_data = {
                "detail_level": "high",
                "reason": "User requested higher detail"
            }
            
            response = client.post("/progressive/tasks/task123/update-level", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["previous_level"] == "medium"
            assert data["new_level"] == "high"
    
    def test_update_loading_level_invalid_level(self, client):
        """Test loading level update with invalid level."""
        with patch.object(progressive_loading_service, 'update_loading_level') as mock_update:
            
            mock_update.return_value = {
                "success": False,
                "error": "Invalid detail level"
            }
            
            update_data = {"detail_level": "invalid_level"}
            
            response = client.post("/progressive/tasks/task123/update-level", json=update_data)
            
            assert response.status_code == 400
            assert "Invalid detail level" in response.json()["detail"]
    
    def test_preload_data_success(self, client, mock_db):
        """Test successful data preloading."""
        with patch('src.api.progressive.get_db') as mock_get_db, \
             patch.object(progressive_loading_service, 'preload_data') as mock_preload:
            
            mock_get_db.return_value = mock_db
            mock_preload.return_value = {
                "success": True,
                "preload_id": "preload123",
                "status": "preloading",
                "items_queued": 500,
                "estimated_completion": (
                    datetime.utcnow() + timedelta(minutes=10)
                ).isoformat()
            }
            
            preload_data = {
                "visualization_id": "viz123",
                "preload_regions": [
                    {"x": 0, "y": 0, "width": 400, "height": 300},
                    {"x": 400, "y": 0, "width": 400, "height": 300}
                ],
                "preload_strategy": "viewport_centered"
            }
            
            response = client.post("/progressive/preload", json=preload_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "preload_id" in data
            assert data["items_queued"] == 500
    
    def test_preload_data_missing_visualization_id(self, client, mock_db):
        """Test data preloading with missing visualization_id."""
        with patch('src.api.progressive.get_db') as mock_get_db:
            mock_get_db.return_value = mock_db
            
            preload_data = {"preload_regions": []}
            
            response = client.post("/progressive/preload", json=preload_data)
            
            assert response.status_code == 400
            assert "visualization_id is required" in response.json()["detail"]

    # Statistics and Configuration Endpoints Tests
    
    def test_get_loading_statistics_success(self, client):
        """Test successful loading statistics retrieval."""
        with patch.object(progressive_loading_service, 'get_loading_statistics') as mock_stats:
            
            mock_stats.return_value = {
                "success": True,
                "statistics": {
                    "total_tasks": 150,
                    "active_tasks": 5,
                    "completed_tasks": 140,
                    "failed_tasks": 5,
                    "average_load_time": 45.5,
                    "average_memory_usage": "85MB",
                    "cache_hit_rate": 0.78,
                    "strategy_usage": {
                        "lod_based": 80,
                        "distance_based": 35,
                        "importance_based": 25,
                        "streaming": 10
                    }
                }
            }
            
            response = client.get("/progressive/statistics")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "statistics" in data
            stats = data["statistics"]
            assert stats["total_tasks"] == 150
            assert stats["cache_hit_rate"] == 0.78
    
    def test_get_loading_statistics_with_filters(self, client):
        """Test loading statistics with date filters."""
        with patch.object(progressive_loading_service, 'get_loading_statistics') as mock_stats:
            
            mock_stats.return_value = {
                "success": True,
                "statistics": {
                    "total_tasks": 25,
                    "active_tasks": 2,
                    "date_range": {
                        "start_date": "2023-01-01T00:00:00Z",
                        "end_date": "2023-01-31T23:59:59Z"
                    }
                }
            }
            
            start_date = "2023-01-01T00:00:00Z"
            end_date = "2023-01-31T23:59:59Z"
            response = client.get(f"/progressive/statistics?start_date={start_date}&end_date={end_date}")
            
            assert response.status_code == 200
            data = response.json()
            assert "statistics" in data
            stats = data["statistics"]
            assert "date_range" in stats
    
    def test_get_loading_strategies_success(self, client):
        """Test successful loading strategies retrieval."""
        response = client.get("/progressive/loading-strategies")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "loading_strategies" in data
        assert len(data["loading_strategies"]) > 0
        
        # Check structure of loading strategies
        strategy = data["loading_strategies"][0]
        assert "value" in strategy
        assert "name" in strategy
        assert "description" in strategy
        assert "use_cases" in strategy
    
    def test_get_detail_levels_success(self, client):
        """Test successful detail levels retrieval."""
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
        assert "node_count" in level
        assert "memory_estimate" in level
    
    def test_get_priorities_success(self, client):
        """Test successful priorities retrieval."""
        response = client.get("/progressive/priorities")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "priorities" in data
        assert len(data["priorities"]) > 0
        
        # Check structure of priorities
        priority = data["priorities"][0]
        assert "value" in priority
        assert "name" in priority
        assert "description" in priority
        assert "processing_order" in priority

    # Advanced Features Tests
    
    def test_estimate_load_time_success(self, client, mock_db):
        """Test successful load time estimation."""
        with patch('src.api.progressive.get_db') as mock_get_db, \
             patch.object(progressive_loading_service, 'estimate_load_time') as mock_estimate:
            
            mock_get_db.return_value = mock_db
            mock_estimate.return_value = {
                "success": True,
                "estimation": {
                    "estimated_time_seconds": 180.5,
                    "estimated_time_minutes": 3.0,
                    "complexity_score": 7.5,
                    "memory_requirement": "120MB",
                    "recommended_strategy": "lod_based",
                    "confidence": 0.85
                }
            }
            
            estimate_data = {
                "visualization_id": "viz123",
                "detail_level": "high",
                "loading_strategy": "parallel",
                "viewport_size": 1000000  # 1M pixels
            }
            
            response = client.post("/progressive/estimate-load", json=estimate_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "estimation" in data
            estimation = data["estimation"]
            assert estimation["estimated_time_minutes"] == 3.0
            assert estimation["complexity_score"] == 7.5
    
    def test_optimize_settings_success(self, client, mock_db):
        """Test successful settings optimization."""
        with patch('src.api.progressive.get_db') as mock_get_db, \
             patch.object(progressive_loading_service, 'optimize_settings') as mock_optimize:
            
            mock_get_db.return_value = mock_db
            mock_optimize.return_value = {
                "success": True,
                "optimization": {
                    "previous_settings": {
                        "cache_size": "50MB",
                        "preload_distance": 200
                    },
                    "optimized_settings": {
                        "cache_size": "75MB",
                        "preload_distance": 150,
                        "loading_strategy": "importance_based"
                    },
                    "performance_improvement": "15%",
                    "memory_efficiency": "+20%",
                    "optimization_applied_at": datetime.utcnow().isoformat()
                }
            }
            
            optimize_data = {
                "visualization_id": "viz123",
                "optimization_goals": ["performance", "memory"],
                "user_preferences": {
                    "prioritize_speed": True,
                    "max_memory": "200MB"
                }
            }
            
            response = client.post("/progressive/optimize-settings", json=optimize_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "optimization" in data
            optimization = data["optimization"]
            assert optimization["performance_improvement"] == "15%"
    
    def test_get_health_status_success(self, client):
        """Test successful health status retrieval."""
        with patch.object(progressive_loading_service, 'get_health_status') as mock_health:
            
            mock_health.return_value = {
                "success": True,
                "health": {
                    "status": "healthy",
                    "active_tasks": 5,
                    "memory_usage": "85MB",
                    "cache_status": "active",
                    "last_error": None,
                    "uptime_seconds": 3600
                }
            }
            
            response = client.get("/progressive/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "health" in data
            health = data["health"]
            assert health["status"] == "healthy"
            assert health["active_tasks"] == 5


class TestProgressiveAPIHelpers:
    """Test helper functions in progressive API."""
    
    def test_get_strategy_description(self):
        """Test strategy description helper."""
        from src.api.progressive import _get_strategy_description
        
        desc = _get_strategy_description(LoadingStrategy.LOD_BASED)
        assert "Level of Detail" in desc
        
        desc = _get_strategy_description(LoadingStrategy.DISTANCE_BASED)
        assert "distance" in desc.lower()
    
    def test_get_detail_level_description(self):
        """Test detail level description helper."""
        from src.api.progressive import _get_detail_level_description
        
        desc = _get_detail_level_description(DetailLevel.HIGH)
        assert "high" in desc.lower()
        assert "detail" in desc.lower()
    
    def test_get_priority_description(self):
        """Test priority description helper."""
        from src.api.progressive import _get_priority_description
        
        desc = _get_priority_description(LoadingPriority.HIGH)
        assert "high" in desc.lower()
        assert "priority" in desc.lower()


class TestProgressiveAPIEdgeCases:
    """Test edge cases and error conditions for Progressive API."""
    
    @pytest.fixture
    def client(self):
        """Create a test client for progressive API."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)

    def test_unicode_data_in_progressive_load(self, client, mock_db):
        """Test progressive load with unicode data."""
        with patch('src.api.progressive.get_db') as mock_get_db, \
             patch.object(progressive_loading_service, 'start_progressive_load') as mock_load:
            
            mock_get_db.return_value = mock_db
            mock_load.return_value = {"success": True, "task_id": "unicode123"}
            
            # Unicode data
            load_data = {
                "visualization_id": "viz测试",
                "parameters": {
                    "title": "テスト可視化",
                    "description": "可视化测试"
                }
            }
            
            response = client.post("/progressive/load", json=load_data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True
    
    def test_extremely_large_viewport(self, client, mock_db):
        """Test with extremely large viewport."""
        with patch('src.api.progressive.get_db') as mock_get_db:
            mock_get_db.return_value = mock_db
            
            load_data = {
                "visualization_id": "viz123",
                "viewport": {
                    "width": 50000,  # Extremely large
                    "height": 50000,
                    "zoom": 0.001
                }
            }
            
            response = client.post("/progressive/load", json=load_data)
            
            # Should handle large viewport gracefully
            assert response.status_code in [200, 400, 422]
    
    def test_invalid_date_range_in_statistics(self, client):
        """Test statistics with invalid date range."""
        with patch.object(progressive_loading_service, 'get_loading_statistics') as mock_stats:
            
            mock_stats.return_value = {"success": False, "error": "Invalid date range"}
            
            # Invalid date range (end before start)
            response = client.get("/progressive/statistics?start_date=2023-01-31&end_date=2023-01-01")
            
            assert response.status_code == 500
            assert "Invalid date range" in response.json()["detail"]
    
    def test_concurrent_progressive_operations(self, client):
        """Test concurrent progressive operations."""
        import threading
        results = []
        
        def make_request():
            response = client.get("/progressive/loading-strategies")
            results.append(response.status_code)
        
        # Create multiple threads
        threads = [threading.Thread(target=make_request) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 5


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "--tb=short"])
