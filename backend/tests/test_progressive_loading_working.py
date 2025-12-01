"""
Comprehensive tests for Progressive Loading Service

Tests progressive loading capabilities for complex knowledge graph visualizations,
including level-of-detail, streaming, and adaptive loading strategies.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.progressive_loading import (
    ProgressiveLoadingService,
    LoadingStrategy,
    DetailLevel,
    LoadingPriority,
    LoadingTask,
    ViewportInfo,
    LoadingChunk,
    LoadingCache,
    progressive_loading_service,
)


class TestLoadingStrategy:
    """Test LoadingStrategy enum."""

    def test_loading_strategy_values(self):
        """Test LoadingStrategy enum values."""
        assert LoadingStrategy.LOD_BASED.value == "lod_based"
        assert LoadingStrategy.DISTANCE_BASED.value == "distance_based"
        assert LoadingStrategy.IMPORTANCE_BASED.value == "importance_based"
        assert LoadingStrategy.CLUSTER_BASED.value == "cluster_based"
        assert LoadingStrategy.TIME_BASED.value == "time_based"
        assert LoadingStrategy.HYBRID.value == "hybrid"


class TestDetailLevel:
    """Test DetailLevel enum."""

    def test_detail_level_values(self):
        """Test DetailLevel enum values."""
        assert DetailLevel.MINIMAL.value == "minimal"
        assert DetailLevel.LOW.value == "low"
        assert DetailLevel.MEDIUM.value == "medium"
        assert DetailLevel.HIGH.value == "high"
        assert DetailLevel.FULL.value == "full"


class TestLoadingPriority:
    """Test LoadingPriority enum."""

    def test_loading_priority_values(self):
        """Test LoadingPriority enum values."""
        assert LoadingPriority.CRITICAL.value == "critical"
        assert LoadingPriority.HIGH.value == "high"
        assert LoadingPriority.MEDIUM.value == "medium"
        assert LoadingPriority.LOW.value == "low"
        assert LoadingPriority.BACKGROUND.value == "background"


class TestLoadingTask:
    """Test LoadingTask dataclass."""

    def test_loading_task_creation(self):
        """Test LoadingTask creation with all fields."""
        task = LoadingTask(
            task_id="task_123",
            loading_strategy=LoadingStrategy.LOD_BASED,
            detail_level=DetailLevel.MEDIUM,
            priority=LoadingPriority.HIGH,
            created_at=datetime.utcnow(),
            total_items=1000,
            chunk_size=100,
            parameters={"test": "data"},
        )

        assert task.task_id == "task_123"
        assert task.loading_strategy == LoadingStrategy.LOD_BASED
        assert task.detail_level == DetailLevel.MEDIUM
        assert task.priority == LoadingPriority.HIGH
        assert task.total_items == 1000
        assert task.chunk_size == 100
        assert task.status == "pending"
        assert task.parameters["test"] == "data"

    def test_loading_task_defaults(self):
        """Test LoadingTask with default values."""
        task = LoadingTask(
            task_id="task_456",
            loading_strategy=LoadingStrategy.DISTANCE_BASED,
            detail_level=DetailLevel.LOW,
            priority=LoadingPriority.MEDIUM,
            created_at=datetime.utcnow(),
        )

        assert task.total_items == 0
        assert task.loaded_items == 0
        assert task.current_chunk == 0
        assert task.total_chunks == 0
        assert task.status == "pending"
        assert task.parameters == {}
        assert task.result == {}


class TestViewportInfo:
    """Test ViewportInfo dataclass."""

    def test_viewport_info_creation(self):
        """Test ViewportInfo creation."""
        viewport = ViewportInfo(
            center_x=100.0, center_y=200.0, zoom_level=1.5, width=800.0, height=600.0
        )

        assert viewport.center_x == 100.0
        assert viewport.center_y == 200.0
        assert viewport.zoom_level == 1.5
        assert viewport.width == 800.0
        assert viewport.height == 600.0

        # Check visible bounds are calculated
        assert "min_x" in viewport.visible_bounds
        assert "max_x" in viewport.visible_bounds
        assert "min_y" in viewport.visible_bounds
        assert "max_y" in viewport.visible_bounds


class TestLoadingChunk:
    """Test LoadingChunk dataclass."""

    def test_loading_chunk_creation(self):
        """Test LoadingChunk creation."""
        chunk = LoadingChunk(
            chunk_id="chunk_123",
            chunk_index=2,
            total_chunks=10,
            detail_level=DetailLevel.MEDIUM,
            load_priority=LoadingPriority.HIGH,
            items=[{"id": 1}, {"id": 2}],
        )

        assert chunk.chunk_id == "chunk_123"
        assert chunk.chunk_index == 2
        assert chunk.total_chunks == 10
        assert chunk.detail_level == DetailLevel.MEDIUM
        assert chunk.load_priority == LoadingPriority.HIGH
        assert len(chunk.items) == 2


class TestLoadingCache:
    """Test LoadingCache dataclass."""

    def test_loading_cache_creation(self):
        """Test LoadingCache creation."""
        cache = LoadingCache(
            cache_id="cache_123",
            loading_strategy=LoadingStrategy.LOD_BASED,
            detail_level=DetailLevel.MEDIUM,
            viewport_hash="viewport_hash_123",
        )

        assert cache.cache_id == "cache_123"
        assert cache.loading_strategy == LoadingStrategy.LOD_BASED
        assert cache.detail_level == DetailLevel.MEDIUM
        assert cache.viewport_hash == "viewport_hash_123"
        assert cache.total_items == 0
        assert cache.loaded_items == 0
        assert cache.ttl_seconds == 300


class TestProgressiveLoadingService:
    """Test ProgressiveLoadingService class."""

    @pytest.fixture
    def service(self):
        """Create fresh service instance for each test."""
        return ProgressiveLoadingService()

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def sample_viewport(self):
        """Sample viewport for testing."""
        return {
            "center_x": 100.0,
            "center_y": 200.0,
            "zoom_level": 1.5,
            "width": 800.0,
            "height": 600.0,
        }

    def test_service_initialization(self, service):
        """Test service initialization."""
        assert service.active_tasks == {}
        assert service.loading_caches == {}
        assert service.viewport_history == {}
        assert service.loading_statistics == {}
        assert service.executor is not None
        assert service.lock is not None
        assert service.min_zoom_for_detailed_loading == 0.5
        assert service.max_items_per_chunk == 500
        assert service.default_chunk_size == 100
        assert service.cache_ttl_seconds == 300
        assert service.total_loads == 0
        assert service.total_load_time == 0.0
        assert service.average_load_time == 0.0
        assert service.background_thread is not None
        assert service.stop_background is False

    @pytest.mark.asyncio
    async def test_start_progressive_load_success(
        self, service, mock_db, sample_viewport
    ):
        """Test successful progressive load start."""
        with patch.object(service, "_estimate_total_items", return_value=1000):
            result = await service.start_progressive_load(
                visualization_id="viz_123",
                loading_strategy=LoadingStrategy.LOD_BASED,
                initial_detail_level=DetailLevel.MEDIUM,
                viewport=sample_viewport,
                priority=LoadingPriority.HIGH,
                parameters={"test": "data"},
                db=mock_db,
            )

            assert result["success"] is True
            assert "task_id" in result
            assert result["visualization_id"] == "viz_123"
            assert result["loading_strategy"] == LoadingStrategy.LOD_BASED.value
            assert result["initial_detail_level"] == DetailLevel.MEDIUM.value
            assert result["priority"] == LoadingPriority.HIGH.value
            assert result["estimated_total_items"] == 1000
            assert result["chunk_size"] <= 500  # Should not exceed max_items_per_chunk
            assert result["status"] == "pending"

            # Check task was created
            task_id = result["task_id"]
            assert task_id in service.active_tasks
            task = service.active_tasks[task_id]
            assert task.loading_strategy == LoadingStrategy.LOD_BASED
            assert task.detail_level == DetailLevel.MEDIUM
            assert task.priority == LoadingPriority.HIGH

    @pytest.mark.asyncio
    async def test_start_progressive_load_without_viewport(self, service, mock_db):
        """Test progressive load start without viewport."""
        with patch.object(service, "_estimate_total_items", return_value=500):
            result = await service.start_progressive_load(
                visualization_id="viz_456",
                loading_strategy=LoadingStrategy.DISTANCE_BASED,
                initial_detail_level=DetailLevel.LOW,
                db=mock_db,
            )

            assert result["success"] is True
            assert result["visualization_id"] == "viz_456"
            assert result["loading_strategy"] == LoadingStrategy.DISTANCE_BASED.value
            assert result["initial_detail_level"] == DetailLevel.LOW.value

    @pytest.mark.asyncio
    async def test_start_progressive_load_error(self, service, mock_db):
        """Test progressive load start with error."""
        with patch.object(
            service, "_estimate_total_items", side_effect=Exception("Database error")
        ):
            result = await service.start_progressive_load(
                visualization_id="viz_error",
                loading_strategy=LoadingStrategy.LOD_BASED,
                db=mock_db,
            )

            assert result["success"] is False
            assert "Failed to start progressive loading" in result["error"]

    @pytest.mark.asyncio
    async def test_get_loading_progress_success(self, service, sample_viewport):
        """Test successful loading progress retrieval."""
        # Create a test task
        task = LoadingTask(
            task_id="progress_task",
            loading_strategy=LoadingStrategy.LOD_BASED,
            detail_level=DetailLevel.MEDIUM,
            priority=LoadingPriority.HIGH,
            created_at=datetime.utcnow(),
            total_items=1000,
            chunk_size=100,
            parameters={"test": "data"},
        )
        task.total_chunks = 10
        task.loaded_items = 350
        task.current_chunk = 4
        task.started_at = datetime.utcnow() - timedelta(seconds=30)

        service.active_tasks["progress_task"] = task

        result = await service.get_loading_progress("progress_task")

        assert result["success"] is True
        assert result["task_id"] == "progress_task"
        assert result["status"] == "pending"
        assert result["progress"]["total_items"] == 1000
        assert result["progress"]["loaded_items"] == 350
        assert result["progress"]["progress_percentage"] == 35.0
        assert result["progress"]["current_chunk"] == 4
        assert result["progress"]["total_chunks"] == 10
        assert result["progress"]["loading_rate_items_per_second"] >= 0
        assert result["timing"]["created_at"] is not None
        assert result["timing"]["started_at"] is not None

    @pytest.mark.asyncio
    async def test_get_loading_progress_not_found(self, service):
        """Test loading progress for non-existent task."""
        result = await service.get_loading_progress("nonexistent_task")

        assert result["success"] is False
        assert "Loading task not found" in result["error"]

    @pytest.mark.asyncio
    async def test_get_loading_progress_completed(self, service):
        """Test loading progress for completed task."""
        # Create completed task
        task = LoadingTask(
            task_id="completed_task",
            loading_strategy=LoadingStrategy.LOD_BASED,
            detail_level=DetailLevel.MEDIUM,
            priority=LoadingPriority.HIGH,
            created_at=datetime.utcnow() - timedelta(minutes=1),
            started_at=datetime.utcnow() - timedelta(seconds=50),
            completed_at=datetime.utcnow() - timedelta(seconds=10),
            total_items=500,
            loaded_items=500,
            chunk_size=100,
        )
        task.total_chunks = 5
        task.current_chunk = 5
        task.status = "completed"
        task.result = {"success": True, "items": []}

        service.active_tasks["completed_task"] = task

        result = await service.get_loading_progress("completed_task")

        assert result["success"] is True
        assert result["status"] == "completed"
        assert result["progress"]["progress_percentage"] == 100.0
        assert result["result"] is not None
        assert result["timing"]["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_update_loading_level_success(self, service, sample_viewport):
        """Test successful loading level update."""
        # Create active task
        task = LoadingTask(
            task_id="update_task",
            loading_strategy=LoadingStrategy.LOD_BASED,
            detail_level=DetailLevel.LOW,
            priority=LoadingPriority.MEDIUM,
            created_at=datetime.utcnow(),
            total_items=500,
            chunk_size=100,
        )
        task.status = "loading"
        task.metadata = {
            "visualization_id": "viz_update",
            "initial_detail_level": DetailLevel.LOW.value,
        }

        service.active_tasks["update_task"] = task

        result = await service.update_loading_level(
            task_id="update_task",
            new_detail_level=DetailLevel.HIGH,
            viewport=sample_viewport,
            db=AsyncMock(),
        )

        assert result["success"] is True
        assert result["task_id"] == "update_task"
        assert result["old_detail_level"] == DetailLevel.LOW.value
        assert result["new_detail_level"] == DetailLevel.HIGH.value
        assert task.detail_level == DetailLevel.HIGH

    @pytest.mark.asyncio
    async def test_update_loading_level_task_not_found(self, service):
        """Test updating loading level for non-existent task."""
        result = await service.update_loading_level(
            task_id="nonexistent", new_detail_level=DetailLevel.HIGH
        )

        assert result["success"] is False
        assert "Loading task not found" in result["error"]

    @pytest.mark.asyncio
    async def test_update_loading_level_wrong_status(self, service):
        """Test updating loading level for completed task."""
        # Create completed task
        task = LoadingTask(
            task_id="completed_task",
            loading_strategy=LoadingStrategy.LOD_BASED,
            detail_level=DetailLevel.LOW,
            priority=LoadingPriority.MEDIUM,
            created_at=datetime.utcnow(),
        )
        task.status = "completed"

        service.active_tasks["completed_task"] = task

        result = await service.update_loading_level(
            task_id="completed_task", new_detail_level=DetailLevel.HIGH
        )

        assert result["success"] is False
        assert "Cannot update task in status: completed" in result["error"]

    @pytest.mark.asyncio
    async def test_preload_adjacent_areas_success(
        self, service, sample_viewport, mock_db
    ):
        """Test successful adjacent area preloading."""
        result = await service.preload_adjacent_areas(
            visualization_id="viz_preload",
            current_viewport=sample_viewport,
            preload_distance=2.0,
            detail_level=DetailLevel.LOW,
            db=mock_db,
        )

        assert result["success"] is True
        assert "preload_task_id" in result
        assert "cache_id" in result
        assert result["preload_distance"] == 2.0
        assert result["detail_level"] == DetailLevel.LOW.value
        assert result["extended_viewport"]["width"] == 1600.0  # 800 * 2.0
        assert result["extended_viewport"]["height"] == 1200.0  # 600 * 2.0

    @pytest.mark.asyncio
    async def test_preload_adjacent_areas_cached(self, service, sample_viewport):
        """Test adjacent area preloading when already cached."""
        # Create existing cache
        cache_id = "viz_preload_low_viewport_hash_123"
        existing_cache = LoadingCache(
            cache_id=cache_id,
            loading_strategy=LoadingStrategy.DISTANCE_BASED,
            detail_level=DetailLevel.LOW,
            viewport_hash="viewport_hash_123",
            total_items=500,
            loaded_items=500,
        )

        service.loading_caches[cache_id] = existing_cache

        with patch.object(
            service, "_generate_viewport_hash", return_value="viewport_hash_123"
        ):
            result = await service.preload_adjacent_areas(
                visualization_id="viz_preload",
                current_viewport=sample_viewport,
                detail_level=DetailLevel.LOW,
            )

            assert result["success"] is True
            assert result["cache_id"] == cache_id
            assert result["cached_items"] == 500
            assert result["total_items"] == 500
            assert "already cached" in result["message"]

    @pytest.mark.asyncio
    async def test_get_loading_statistics_all(self, service):
        """Test getting loading statistics for all visualizations."""
        # Create some test tasks
        task1 = LoadingTask(
            task_id="task1",
            loading_strategy=LoadingStrategy.LOD_BASED,
            detail_level=DetailLevel.MEDIUM,
            priority=LoadingPriority.HIGH,
            created_at=datetime.utcnow(),
            total_items=1000,
            loaded_items=1000,
            chunk_size=100,
        )
        task1.status = "completed"
        task1.started_at = datetime.utcnow() - timedelta(seconds=30)
        task1.completed_at = datetime.utcnow()

        task2 = LoadingTask(
            task_id="task2",
            loading_strategy=LoadingStrategy.DISTANCE_BASED,
            detail_level=DetailLevel.LOW,
            priority=LoadingPriority.MEDIUM,
            created_at=datetime.utcnow(),
            total_items=500,
            loaded_items=250,
            chunk_size=50,
        )
        task2.status = "loading"
        task2.started_at = datetime.utcnow() - timedelta(seconds=20)

        task3 = LoadingTask(
            task_id="task3",
            loading_strategy=LoadingStrategy.IMPORTANCE_BASED,
            detail_level=DetailLevel.HIGH,
            priority=LoadingPriority.CRITICAL,
            created_at=datetime.utcnow(),
            total_items=300,
            loaded_items=100,
            chunk_size=25,
        )
        task3.status = "failed"
        task3.started_at = datetime.utcnow() - timedelta(seconds=10)
        task3.completed_at = datetime.utcnow()
        task3.error_message = "Loading failed"

        service.active_tasks = {"task1": task1, "task2": task2, "task3": task3}

        # Add some caches
        cache1 = LoadingCache(
            cache_id="viz1_medium_hash",
            loading_strategy=LoadingStrategy.LOD_BASED,
            detail_level=DetailLevel.MEDIUM,
            viewport_hash="hash1",
            total_items=500,
            loaded_items=500,
        )
        cache2 = LoadingCache(
            cache_id="viz2_low_hash",
            loading_strategy=LoadingStrategy.DISTANCE_BASED,
            detail_level=DetailLevel.LOW,
            viewport_hash="hash2",
            total_items=200,
            loaded_items=150,
        )

        service.loading_caches = {"cache1": cache1.cache_id, "cache2": cache2.cache_id}
        service.viewport_history = {
            "viz1": [ViewportInfo(0, 0, 1, 100, 100)],
            "viz2": [ViewportInfo(50, 50, 2, 200, 200)],
        }

        result = await service.get_loading_statistics()

        assert result["success"] is True
        assert result["statistics"]["tasks"]["total"] == 3
        assert result["statistics"]["tasks"]["completed"] == 1
        assert result["statistics"]["tasks"]["failed"] == 1
        assert result["statistics"]["tasks"]["loading"] == 1
        assert result["statistics"]["items"]["total_loaded"] == 1350  # 1000 + 250 + 100
        assert result["statistics"]["items"]["total_queued"] == 1800  # 1000 + 500 + 300
        assert result["statistics"]["caches"]["total_caches"] == 2
        assert result["statistics"]["viewport_history"]["total_viewports"] == 2
        assert (
            result["statistics"]["viewport_history"]["visualizations_with_history"] == 2
        )

    @pytest.mark.asyncio
    async def test_get_loading_statistics_filtered(self, service):
        """Test getting loading statistics for specific visualization."""
        # Create tasks for different visualizations
        task1 = LoadingTask(
            task_id="viz1_task",
            loading_strategy=LoadingStrategy.LOD_BASED,
            detail_level=DetailLevel.MEDIUM,
            priority=LoadingPriority.HIGH,
            created_at=datetime.utcnow(),
            total_items=1000,
            loaded_items=1000,
        )
        task1.metadata = {"visualization_id": "viz1"}
        task1.status = "completed"

        task2 = LoadingTask(
            task_id="viz2_task",
            loading_strategy=LoadingStrategy.DISTANCE_BASED,
            detail_level=DetailLevel.LOW,
            priority=LoadingPriority.MEDIUM,
            created_at=datetime.utcnow(),
            total_items=500,
            loaded_items=250,
        )
        task2.metadata = {"visualization_id": "viz2"}
        task2.status = "loading"

        service.active_tasks = {"viz1_task": task1, "viz2_task": task2}

        result = await service.get_loading_statistics(visualization_id="viz1")

        assert result["success"] is True
        assert result["visualization_id"] == "viz1"
        assert result["statistics"]["tasks"]["total"] == 1  # Only viz1 tasks
        assert result["statistics"]["tasks"]["completed"] == 1
        assert result["statistics"]["items"]["total_loaded"] == 1000
        assert result["statistics"]["items"]["total_queued"] == 1000

    @pytest.mark.asyncio
    async def test_execute_lod_loading(self, service, mock_db):
        """Test Level of Detail based loading execution."""
        task = LoadingTask(
            task_id="lod_task",
            loading_strategy=LoadingStrategy.LOD_BASED,
            detail_level=DetailLevel.MEDIUM,
            priority=LoadingPriority.HIGH,
            created_at=datetime.utcnow(),
            total_items=300,
            chunk_size=100,
        )
        task.total_chunks = 3

        with (
            patch.object(
                service,
                "_load_medium_chunk",
                return_value=[{"id": i} for i in range(100)],
            ),
            patch.object(
                service,
                "_load_medium_chunk",
                return_value=[{"id": i} for i in range(100, 200)],
            ),
            patch.object(
                service,
                "_load_medium_chunk",
                return_value=[{"id": i} for i in range(200, 300)],
            ),
        ):
            result = await service._execute_lod_loading(task, mock_db)

            assert result["success"] is True
            assert result["loaded_items"] == 300
            assert result["chunks_loaded"] == 3
            assert result["detail_level"] == DetailLevel.MEDIUM.value
            assert len(result["items"]) == 300

    @pytest.mark.asyncio
    async def test_execute_lod_loading_cancelled(self, service, mock_db):
        """Test LOD loading when task is cancelled."""
        task = LoadingTask(
            task_id="cancelled_task",
            loading_strategy=LoadingStrategy.LOD_BASED,
            detail_level=DetailLevel.MEDIUM,
            priority=LoadingPriority.HIGH,
            created_at=datetime.utcnow(),
            total_items=300,
            chunk_size=100,
        )
        task.total_chunks = 3
        task.status = "cancelled"

        with patch.object(
            service, "_load_medium_chunk", return_value=[{"id": i} for i in range(100)]
        ):
            result = await service._execute_lod_loading(task, mock_db)

            # Should stop early due to cancellation
            assert result["success"] is True
            assert result["loaded_items"] <= 100  # Should not load all chunks

    @pytest.mark.asyncio
    async def test_execute_distance_based_loading(self, service, mock_db):
        """Test distance-based loading execution."""
        viewport_info = ViewportInfo(100, 100, 1.5, 800, 600)

        task = LoadingTask(
            task_id="distance_task",
            loading_strategy=LoadingStrategy.DISTANCE_BASED,
            detail_level=DetailLevel.MEDIUM,
            priority=LoadingPriority.HIGH,
            created_at=datetime.utcnow(),
            total_items=200,
            chunk_size=50,
        )
        task.total_chunks = 4
        task.metadata = {"viewport_info": viewport_info}

        with patch.object(
            service, "_load_distance_chunk", return_value=[{"id": i} for i in range(50)]
        ):
            result = await service._execute_distance_based_loading(task, mock_db)

            assert result["success"] is True
            assert result["loaded_items"] == 200  # 4 chunks * 50 items
            assert result["chunks_loaded"] == 4
            assert result["loading_strategy"] == "distance_based"

    @pytest.mark.asyncio
    async def test_execute_distance_based_loading_no_viewport(self, service, mock_db):
        """Test distance-based loading without viewport info."""
        task = LoadingTask(
            task_id="no_viewport_task",
            loading_strategy=LoadingStrategy.DISTANCE_BASED,
            detail_level=DetailLevel.MEDIUM,
            priority=LoadingPriority.HIGH,
            created_at=datetime.utcnow(),
            total_items=200,
            chunk_size=50,
        )
        task.total_chunks = 4
        task.metadata = {}

        result = await service._execute_distance_based_loading(task, mock_db)

        assert result["success"] is False
        assert "Viewport information required" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_importance_based_loading(self, service, mock_db):
        """Test importance-based loading execution."""
        task = LoadingTask(
            task_id="importance_task",
            loading_strategy=LoadingStrategy.IMPORTANCE_BASED,
            detail_level=DetailLevel.HIGH,
            priority=LoadingPriority.CRITICAL,
            created_at=datetime.utcnow(),
            total_items=150,
            chunk_size=30,
        )
        task.total_chunks = 5

        with patch.object(
            service,
            "_load_importance_chunk",
            return_value=[{"id": i} for i in range(30)],
        ):
            result = await service._execute_importance_based_loading(task, mock_db)

            assert result["success"] is True
            assert result["loaded_items"] == 150  # 5 chunks * 30 items
            assert result["chunks_loaded"] == 5
            assert result["loading_strategy"] == "importance_based"

    @pytest.mark.asyncio
    async def test_execute_cluster_based_loading(self, service, mock_db):
        """Test cluster-based loading execution."""
        task = LoadingTask(
            task_id="cluster_task",
            loading_strategy=LoadingStrategy.CLUSTER_BASED,
            detail_level=DetailLevel.LOW,
            priority=LoadingPriority.LOW,
            created_at=datetime.utcnow(),
            total_items=100,
            chunk_size=25,
        )
        task.total_chunks = 4

        with patch.object(
            service, "_load_cluster_chunk", return_value=[{"id": i} for i in range(25)]
        ):
            result = await service._execute_cluster_based_loading(task, mock_db)

            assert result["success"] is True
            assert result["loaded_items"] == 100  # 4 chunks * 25 items
            assert result["chunks_loaded"] == 4
            assert result["loading_strategy"] == "cluster_based"

    @pytest.mark.asyncio
    async def test_estimate_total_items(self, service):
        """Test total items estimation."""
        total_items = await service._estimate_total_items(
            visualization_id="viz_estimate",
            loading_strategy=LoadingStrategy.LOD_BASED,
            detail_level=DetailLevel.MEDIUM,
            viewport=None,
            parameters={},
            db=AsyncMock(),
        )

        assert isinstance(total_items, int)
        assert total_items >= 10  # Minimum items
        # Should be based on detail level config
        assert total_items > 500  # Medium level should have more than 500 items

    @pytest.mark.asyncio
    async def test_estimate_total_items_with_viewport(self, service, sample_viewport):
        """Test total items estimation with viewport."""
        viewport_info = ViewportInfo(**sample_viewport)

        total_items = await service._estimate_total_items(
            visualization_id="viz_viewport",
            loading_strategy=LoadingStrategy.LOD_BASED,
            detail_level=DetailLevel.HIGH,
            viewport=viewport_info,
            parameters={},
            db=AsyncMock(),
        )

        assert isinstance(total_items, int)
        assert total_items >= 10

        # Smaller viewport should have fewer items
        small_viewport = ViewportInfo(0, 0, 1.0, 100, 100)  # Much smaller
        small_items = await service._estimate_total_items(
            visualization_id="viz_small",
            loading_strategy=LoadingStrategy.LOD_BASED,
            detail_level=DetailLevel.HIGH,
            viewport=small_viewport,
            parameters={},
            db=AsyncMock(),
        )

        assert small_items < total_items  # Smaller viewport should have fewer items

    def test_generate_viewport_hash(self, service):
        """Test viewport hash generation."""
        viewport1 = ViewportInfo(100.0, 200.0, 1.5, 800.0, 600.0)
        viewport2 = ViewportInfo(100.0, 200.0, 1.5, 800.0, 600.0)
        viewport3 = ViewportInfo(100.0, 200.0, 1.5, 800.0, 601.0)  # Different height

        hash1 = service._generate_viewport_hash(viewport1)
        hash2 = service._generate_viewport_hash(viewport2)
        hash3 = service._generate_viewport_hash(viewport3)

        assert hash1 == hash2  # Same viewport should have same hash
        assert hash1 != hash3  # Different viewport should have different hash
        assert isinstance(hash1, str)
        assert len(hash1) > 0

    def test_get_detail_level_config(self, service):
        """Test detail level configuration retrieval."""
        minimal_config = service._get_detail_level_config(DetailLevel.MINIMAL)
        assert minimal_config["include_properties"] is False
        assert minimal_config["include_relationships"] is False
        assert minimal_config["include_patterns"] is False
        assert minimal_config["max_nodes_per_type"] == 20

        medium_config = service._get_detail_level_config(DetailLevel.MEDIUM)
        assert medium_config["include_properties"] is True
        assert medium_config["include_relationships"] is True
        assert medium_config["include_patterns"] is True
        assert medium_config["max_nodes_per_type"] == 500

        full_config = service._get_detail_level_config(DetailLevel.FULL)
        assert full_config["include_properties"] is True
        assert full_config["include_relationships"] is True
        assert full_config["include_patterns"] is True
        assert full_config["max_nodes_per_type"] is None

    def test_cleanup_expired_caches(self, service):
        """Test cleanup of expired caches."""
        # Create current cache
        current_cache = LoadingCache(
            cache_id="current",
            loading_strategy=LoadingStrategy.LOD_BASED,
            detail_level=DetailLevel.MEDIUM,
            viewport_hash="current_hash",
        )

        # Create expired cache (older than TTL)
        expired_cache = LoadingCache(
            cache_id="expired",
            loading_strategy=LoadingStrategy.LOD_BASED,
            detail_level=DetailLevel.MEDIUM,
            viewport_hash="expired_hash",
        )
        expired_cache.last_accessed = datetime.utcnow() - timedelta(
            seconds=400
        )  # Older than 300s TTL

        service.loading_caches = {"current": current_cache, "expired": expired_cache}

        service._cleanup_expired_caches()

        assert "current" in service.loading_caches
        assert "expired" not in service.loading_caches


class TestServiceIntegration:
    """Integration tests for Progressive Loading service."""

    @pytest.mark.asyncio
    async def test_full_loading_workflow(self):
        """Test complete progressive loading workflow."""
        service = ProgressiveLoadingService()
        mock_db = AsyncMock(spec=AsyncSession)

        sample_viewport = {
            "center_x": 100.0,
            "center_y": 200.0,
            "zoom_level": 1.5,
            "width": 800.0,
            "height": 600.0,
        }

        # Start loading
        with patch.object(service, "_estimate_total_items", return_value=300):
            start_result = await service.start_progressive_load(
                visualization_id="integration_test",
                loading_strategy=LoadingStrategy.LOD_BASED,
                initial_detail_level=DetailLevel.MEDIUM,
                viewport=sample_viewport,
                priority=LoadingPriority.HIGH,
                db=mock_db,
            )

            assert start_result["success"] is True
            task_id = start_result["task_id"]

        # Wait a moment for background loading to start
        await asyncio.sleep(0.1)

        # Check progress
        progress_result = await service.get_loading_progress(task_id)
        assert progress_result["success"] is True
        assert progress_result["status"] in ["pending", "loading"]

        # Update loading level
        update_result = await service.update_loading_level(
            task_id=task_id, new_detail_level=DetailLevel.HIGH, viewport=sample_viewport
        )
        assert update_result["success"] is True

        # Get statistics
        stats_result = await service.get_loading_statistics()
        assert stats_result["success"] is True
        assert stats_result["statistics"]["tasks"]["total"] >= 1

        # Test preloading
        preload_result = await service.preload_adjacent_areas(
            visualization_id="integration_test",
            current_viewport=sample_viewport,
            preload_distance=1.5,
            detail_level=DetailLevel.LOW,
            db=mock_db,
        )
        assert preload_result["success"] is True


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.fixture
    def service(self):
        """Create fresh service instance."""
        return ProgressiveLoadingService()

    @pytest.mark.asyncio
    async def test_loading_task_execution_error(self, service, mock_db):
        """Test handling of loading task execution errors."""
        task = LoadingTask(
            task_id="error_task",
            loading_strategy=LoadingStrategy.LOD_BASED,
            detail_level=DetailLevel.MEDIUM,
            priority=LoadingPriority.HIGH,
            created_at=datetime.utcnow(),
            total_items=200,
            chunk_size=100,
        )
        task.total_chunks = 2

        with patch.object(
            service, "_load_medium_chunk", side_effect=Exception("Loading error")
        ):
            result = await service._execute_lod_loading(task, mock_db)

            assert result["success"] is False
            assert "LOD loading failed" in result["error"]

    @pytest.mark.asyncio
    async def test_progress_retrieval_error(self, service):
        """Test progress retrieval error handling."""
        # Create corrupted task with invalid data
        task = LoadingTask(
            task_id="corrupted_task",
            loading_strategy=LoadingStrategy.LOD_BASED,
            detail_level=DetailLevel.MEDIUM,
            priority=LoadingPriority.HIGH,
            created_at=datetime.utcnow(),
            total_items=0,  # Invalid (division by zero)
            loaded_items=0,
        )

        service.active_tasks["corrupted_task"] = task

        # Should handle gracefully without crashing
        result = await service.get_loading_progress("corrupted_task")

        assert result["success"] is True  # Should still succeed
        assert result["progress"]["progress_percentage"] == 0.0

    def test_viewport_hash_generation_error(self, service):
        """Test viewport hash generation error handling."""
        # Create viewport with potentially problematic data
        viewport = ViewportInfo(float("inf"), float("-inf"), 0.0, 0.0, 0.0)

        # Should not crash, should return some hash
        hash_result = service._generate_viewport_hash(viewport)
        assert isinstance(hash_result, str)
        assert len(hash_result) > 0

    def test_singleton_instance(self):
        """Test that singleton instance is properly exported."""
        assert progressive_loading_service is not None
        assert isinstance(progressive_loading_service, ProgressiveLoadingService)
