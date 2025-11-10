"""
Progressive Loading Service for Complex Visualizations

This service provides progressive loading capabilities for complex knowledge graph
visualizations, including level-of-detail, streaming, and adaptive loading.
"""

import logging
import asyncio
import uuid
import time
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)


class LoadingStrategy(Enum):
    """Progressive loading strategies."""
    LOD_BASED = "lod_based"  # Level of Detail
    DISTANCE_BASED = "distance_based"
    IMPORTANCE_BASED = "importance_based"
    CLUSTER_BASED = "cluster_based"
    TIME_BASED = "time_based"
    HYBRID = "hybrid"


class DetailLevel(Enum):
    """Detail levels for progressive loading."""
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    FULL = "full"


class LoadingPriority(Enum):
    """Loading priorities."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BACKGROUND = "background"


@dataclass
class LoadingTask:
    """Task for progressive loading."""
    task_id: str
    loading_strategy: LoadingStrategy
    detail_level: DetailLevel
    priority: LoadingPriority
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_items: int = 0
    loaded_items: int = 0
    chunk_size: int = 100
    current_chunk: int = 0
    total_chunks: int = 0
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    status: str = "pending"  # pending, loading, completed, failed


@dataclass
class ViewportInfo:
    """Information about current viewport."""
    center_x: float
    center_y: float
    zoom_level: float
    width: float
    height: float
    visible_bounds: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LoadingChunk:
    """Chunk of data for progressive loading."""
    chunk_id: str
    chunk_index: int
    total_chunks: int
    items: List[Dict[str, Any]] = field(default_factory=list)
    detail_level: DetailLevel
    load_priority: LoadingPriority
    estimated_size_bytes: int = 0
    load_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LoadingCache:
    """Cache for progressive loading data."""
    cache_id: str
    loading_strategy: LoadingStrategy
    detail_level: DetailLevel
    viewport_hash: str
    chunks: Dict[int, LoadingChunk] = field(default_factory=dict)
    total_items: int = 0
    loaded_items: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    ttl_seconds: int = 300  # 5 minutes


class ProgressiveLoadingService:
    """Progressive loading service for complex visualizations."""
    
    def __init__(self):
        self.active_tasks: Dict[str, LoadingTask] = {}
        self.loading_caches: Dict[str, LoadingCache] = {}
        self.viewport_history: Dict[str, List[ViewportInfo]] = {}
        self.loading_statistics: Dict[str, Any] = {}
        
        self.executor = ThreadPoolExecutor(max_workers=6)
        self.lock = threading.RLock()
        
        # Loading thresholds
        self.min_zoom_for_detailed_loading = 0.5
        self.max_items_per_chunk = 500
        self.default_chunk_size = 100
        self.cache_ttl_seconds = 300
        
        # Performance metrics
        self.total_loads = 0
        self.total_load_time = 0.0
        self.average_load_time = 0.0
        
        # Background loading thread
        self.background_thread: Optional[threading.Thread] = None
        self.stop_background = False
        self._start_background_loading()
    
    async def start_progressive_load(
        self,
        visualization_id: str,
        loading_strategy: LoadingStrategy,
        initial_detail_level: DetailLevel = DetailLevel.LOW,
        viewport: Optional[Dict[str, Any]] = None,
        priority: LoadingPriority = LoadingPriority.MEDIUM,
        parameters: Dict[str, Any] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Start progressive loading for a visualization.
        
        Args:
            visualization_id: ID of the visualization
            loading_strategy: Strategy for progressive loading
            initial_detail_level: Initial detail level to load
            viewport: Current viewport information
            priority: Loading priority
            parameters: Additional loading parameters
            db: Database session
        
        Returns:
            Loading task result
        """
        try:
            task_id = str(uuid.uuid4())
            
            # Create viewport info
            viewport_info = None
            if viewport:
                viewport_info = ViewportInfo(
                    center_x=viewport.get("center_x", 0),
                    center_y=viewport.get("center_y", 0),
                    zoom_level=viewport.get("zoom_level", 1.0),
                    width=viewport.get("width", 1000),
                    height=viewport.get("height", 800)
                )
                
                # Calculate visible bounds
                zoom_factor = 1.0 / max(viewport_info.zoom_level, 0.1)
                viewport_info.visible_bounds = {
                    "min_x": viewport_info.center_x - (viewport_info.width / 2) * zoom_factor,
                    "max_x": viewport_info.center_x + (viewport_info.width / 2) * zoom_factor,
                    "min_y": viewport_info.center_y - (viewport_info.height / 2) * zoom_factor,
                    "max_y": viewport_info.center_y + (viewport_info.height / 2) * zoom_factor
                }
            
            # Estimate total items
            total_items = await self._estimate_total_items(
                visualization_id, loading_strategy, initial_detail_level, 
                viewport_info, parameters, db
            )
            
            # Create loading task
            task = LoadingTask(
                task_id=task_id,
                loading_strategy=loading_strategy,
                detail_level=initial_detail_level,
                priority=priority,
                created_at=datetime.utcnow(),
                total_items=total_items,
                chunk_size=min(parameters.get("chunk_size", self.default_chunk_size), self.max_items_per_chunk),
                parameters=parameters or {},
                metadata={
                    "visualization_id": visualization_id,
                    "viewport_info": viewport_info,
                    "initial_detail_level": initial_detail_level.value
                }
            )
            
            # Calculate total chunks
            task.total_chunks = max(1, (total_items + task.chunk_size - 1) // task.chunk_size)
            
            with self.lock:
                self.active_tasks[task_id] = task
                
                # Update viewport history
                if viewport_info:
                    if visualization_id not in self.viewport_history:
                        self.viewport_history[visualization_id] = []
                    self.viewport_history[visualization_id].append(viewport_info)
                    
                    # Keep only last 10 viewports
                    if len(self.viewport_history[visualization_id]) > 10:
                        self.viewport_history[visualization_id] = self.viewport_history[visualization_id][-10:]
            
            # Start loading in background
            asyncio.create_task(self._execute_loading_task(task_id, db))
            
            return {
                "success": True,
                "task_id": task_id,
                "visualization_id": visualization_id,
                "loading_strategy": loading_strategy.value,
                "initial_detail_level": initial_detail_level.value,
                "priority": priority.value,
                "estimated_total_items": total_items,
                "chunk_size": task.chunk_size,
                "total_chunks": task.total_chunks,
                "status": task.status,
                "message": "Progressive loading started"
            }
            
        except Exception as e:
            logger.error(f"Error starting progressive load: {e}")
            return {
                "success": False,
                "error": f"Failed to start progressive loading: {str(e)}"
            }
    
    async def get_loading_progress(
        self,
        task_id: str
    ) -> Dict[str, Any]:
        """
        Get progress of a loading task.
        
        Args:
            task_id: ID of the loading task
        
        Returns:
            Loading progress information
        """
        try:
            with self.lock:
                if task_id not in self.active_tasks:
                    return {
                        "success": False,
                        "error": "Loading task not found"
                    }
                
                task = self.active_tasks[task_id]
                
                # Calculate progress percentage
                progress_percentage = 0.0
                if task.total_items > 0:
                    progress_percentage = (task.loaded_items / task.total_items) * 100
                
                # Calculate loading rate
                loading_rate = 0.0
                estimated_remaining = 0.0
                
                if task.started_at and task.loaded_items > 0:
                    elapsed_time = (datetime.utcnow() - task.started_at).total_seconds()
                    if elapsed_time > 0:
                        loading_rate = task.loaded_items / elapsed_time
                        remaining_items = task.total_items - task.loaded_items
                        estimated_remaining = remaining_items / loading_rate if loading_rate > 0 else 0
                
                return {
                    "success": True,
                    "task_id": task_id,
                    "status": task.status,
                    "progress": {
                        "total_items": task.total_items,
                        "loaded_items": task.loaded_items,
                        "progress_percentage": progress_percentage,
                        "current_chunk": task.current_chunk,
                        "total_chunks": task.total_chunks,
                        "loading_rate_items_per_second": loading_rate,
                        "estimated_remaining_seconds": estimated_remaining
                    },
                    "timing": {
                        "created_at": task.created_at.isoformat(),
                        "started_at": task.started_at.isoformat() if task.started_at else None,
                        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                        "elapsed_seconds": (
                            (datetime.utcnow() - task.started_at).total_seconds()
                            if task.started_at else 0
                        )
                    },
                    "parameters": task.parameters,
                    "result": task.result if task.status == "completed" else None,
                    "error_message": task.error_message
                }
                
        except Exception as e:
            logger.error(f"Error getting loading progress: {e}")
            return {
                "success": False,
                "error": f"Failed to get loading progress: {str(e)}"
            }
    
    async def update_loading_level(
        self,
        task_id: str,
        new_detail_level: DetailLevel,
        viewport: Optional[Dict[str, Any]] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Update loading level for an existing task.
        
        Args:
            task_id: ID of the loading task
            new_detail_level: New detail level to load
            viewport: Updated viewport information
            db: Database session
        
        Returns:
            Update result
        """
        try:
            with self.lock:
                if task_id not in self.active_tasks:
                    return {
                        "success": False,
                        "error": "Loading task not found"
                    }
                
                task = self.active_tasks[task_id]
                
                if task.status not in ["pending", "loading"]:
                    return {
                        "success": False,
                        "error": f"Cannot update task in status: {task.status}"
                    }
                
                # Update viewport if provided
                if viewport:
                    viewport_info = ViewportInfo(
                        center_x=viewport.get("center_x", 0),
                        center_y=viewport.get("center_y", 0),
                        zoom_level=viewport.get("zoom_level", 1.0),
                        width=viewport.get("width", 1000),
                        height=viewport.get("height", 800)
                    )
                    
                    zoom_factor = 1.0 / max(viewport_info.zoom_level, 0.1)
                    viewport_info.visible_bounds = {
                        "min_x": viewport_info.center_x - (viewport_info.width / 2) * zoom_factor,
                        "max_x": viewport_info.center_x + (viewport_info.width / 2) * zoom_factor,
                        "min_y": viewport_info.center_y - (viewport_info.height / 2) * zoom_factor,
                        "max_y": viewport_info.center_y + (viewport_info.height / 2) * zoom_factor
                    }
                    
                    task.metadata["viewport_info"] = viewport_info
                    
                    # Update viewport history
                    viz_id = task.metadata.get("visualization_id")
                    if viz_id:
                        if viz_id not in self.viewport_history:
                            self.viewport_history[viz_id] = []
                        self.viewport_history[viz_id].append(viewport_info)
                        
                        # Keep only last 10 viewports
                        if len(self.viewport_history[viz_id]) > 10:
                            self.viewport_history[viz_id] = self.viewport_history[viz_id][-10]
                
                old_detail_level = task.detail_level
                task.detail_level = new_detail_level
                
                # Re-estimate total items for new detail level
                # This would typically require reloading with new parameters
            
            return {
                "success": True,
                "task_id": task_id,
                "old_detail_level": old_detail_level.value,
                "new_detail_level": new_detail_level.value,
                "message": "Loading level updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Error updating loading level: {e}")
            return {
                "success": False,
                "error": f"Failed to update loading level: {str(e)}"
            }
    
    async def preload_adjacent_areas(
        self,
        visualization_id: str,
        current_viewport: Dict[str, Any],
        preload_distance: float = 2.0,
        detail_level: DetailLevel = DetailLevel.LOW,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Preload areas adjacent to current viewport.
        
        Args:
            visualization_id: ID of the visualization
            current_viewport: Current viewport information
            preload_distance: Distance multiplier for preloading
            detail_level: Detail level for preloading
            db: Database session
        
        Returns:
            Preloading result
        """
        try:
            # Calculate extended viewport for preloading
            viewport_info = ViewportInfo(
                center_x=current_viewport.get("center_x", 0),
                center_y=current_viewport.get("center_y", 0),
                zoom_level=current_viewport.get("zoom_level", 1.0),
                width=current_viewport.get("width", 1000) * preload_distance,
                height=current_viewport.get("height", 800) * preload_distance
            )
            
            # Generate cache key
            viewport_hash = self._generate_viewport_hash(viewport_info)
            cache_id = f"{visualization_id}_{detail_level.value}_{viewport_hash}"
            
            # Check if already cached
            with self.lock:
                if cache_id in self.loading_caches:
                    cache = self.loading_caches[cache_id]
                    cache.last_accessed = datetime.utcnow()
                    
                    return {
                        "success": True,
                        "cache_id": cache_id,
                        "cached_items": cache.loaded_items,
                        "total_items": cache.total_items,
                        "message": "Adjacent areas already cached"
                    }
            
            # Start preloading task
            preload_task_id = str(uuid.uuid4())
            
            task = LoadingTask(
                task_id=preload_task_id,
                loading_strategy=LoadingStrategy.DISTANCE_BASED,
                detail_level=detail_level,
                priority=LoadingPriority.BACKGROUND,
                created_at=datetime.utcnow(),
                total_items=0,  # Will be estimated
                chunk_size=self.default_chunk_size,
                parameters={
                    "viewport_info": viewport_info,
                    "preload_mode": True,
                    "preload_distance": preload_distance
                },
                metadata={
                    "visualization_id": visualization_id,
                    "cache_id": cache_id
                }
            )
            
            with self.lock:
                self.active_tasks[preload_task_id] = task
            
            # Execute preloading
            asyncio.create_task(self._execute_preloading_task(preload_task_id, cache_id, db))
            
            return {
                "success": True,
                "preload_task_id": preload_task_id,
                "cache_id": cache_id,
                "preload_distance": preload_distance,
                "detail_level": detail_level.value,
                "extended_viewport": {
                    "center_x": viewport_info.center_x,
                    "center_y": viewport_info.center_y,
                    "width": viewport_info.width,
                    "height": viewport_info.height,
                    "zoom_level": viewport_info.zoom_level
                },
                "message": "Adjacent area preloading started"
            }
            
        except Exception as e:
            logger.error(f"Error preloading adjacent areas: {e}")
            return {
                "success": False,
                "error": f"Failed to preload adjacent areas: {str(e)}"
            }
    
    async def get_loading_statistics(
        self,
        visualization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get loading statistics and performance metrics.
        
        Args:
            visualization_id: Optional filter for specific visualization
        
        Returns:
            Loading statistics
        """
        try:
            with self.lock:
                # Filter tasks by visualization if specified
                tasks = list(self.active_tasks.values())
                if visualization_id:
                    tasks = [
                        task for task in tasks
                        if task.metadata.get("visualization_id") == visualization_id
                    ]
                
                # Calculate statistics
                total_tasks = len(tasks)
                completed_tasks = len([t for t in tasks if t.status == "completed"])
                failed_tasks = len([t for t in tasks if t.status == "failed"])
                loading_tasks = len([t for t in tasks if t.status == "loading"])
                
                total_items_loaded = sum(task.loaded_items for task in tasks)
                total_items_queued = sum(task.total_items for task in tasks)
                
                # Calculate average loading time
                completed_task_times = []
                for task in tasks:
                    if task.status == "completed" and task.started_at and task.completed_at:
                        execution_time = (task.completed_at - task.started_at).total_seconds()
                        completed_task_times.append(execution_time)
                
                avg_loading_time = sum(completed_task_times) / len(completed_task_times) if completed_task_times else 0
                
                # Cache statistics
                cache_stats = {}
                for cache_id, cache in self.loading_caches.items():
                    viz_id = cache_id.split("_")[0]
                    if not visualization_id or viz_id == visualization_id:
                        cache_stats[viz_id] = {
                            "cache_id": cache_id,
                            "total_items": cache.total_items,
                            "loaded_items": cache.loaded_items,
                            "loading_strategy": cache.loading_strategy.value,
                            "detail_level": cache.detail_level.value,
                            "cache_age_seconds": (datetime.utcnow() - cache.created_at).total_seconds(),
                            "last_accessed_seconds": (datetime.utcnow() - cache.last_accessed).total_seconds()
                        }
                
                return {
                    "success": True,
                    "statistics": {
                        "tasks": {
                            "total": total_tasks,
                            "completed": completed_tasks,
                            "failed": failed_tasks,
                            "loading": loading_tasks,
                            "completion_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
                        },
                        "items": {
                            "total_loaded": total_items_loaded,
                            "total_queued": total_items_queued,
                            "load_rate": total_items_loaded / max(avg_loading_time, 1)
                        },
                        "performance": {
                            "average_loading_time_seconds": avg_loading_time,
                            "total_loads": self.total_loads,
                            "total_load_time": self.total_load_time,
                            "average_load_time": self.average_load_time
                        },
                        "caches": {
                            "total_caches": len(self.loading_caches),
                            "cache_entries": cache_stats
                        },
                        "viewport_history": {
                            "total_viewports": sum(len(vph) for vph in self.viewport_history.values()),
                            "visualizations_with_history": len(self.viewport_history)
                        }
                    },
                    "visualization_id": visualization_id,
                    "calculated_at": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting loading statistics: {e}")
            return {
                "success": False,
                "error": f"Failed to get loading statistics: {str(e)}"
            }
    
    # Private Helper Methods
    
    def _start_background_loading(self):
        """Start background loading thread."""
        try:
            def background_loading_task():
                while not self.stop_background:
                    try:
                        # Clean up old caches
                        self._cleanup_expired_caches()
                        
                        # Optimize loading parameters based on statistics
                        self._optimize_loading_parameters()
                        
                        # Sleep for cleanup interval
                        time.sleep(30)  # 30 seconds
                        
                    except Exception as e:
                        logger.error(f"Error in background loading: {e}")
                        time.sleep(30)
            
            self.background_thread = threading.Thread(target=background_loading_task, daemon=True)
            self.background_thread.start()
            
        except Exception as e:
            logger.error(f"Error starting background loading: {e}")
    
    async def _execute_loading_task(self, task_id: str, db: AsyncSession):
        """Execute a progressive loading task."""
        try:
            with self.lock:
                if task_id not in self.active_tasks:
                    return
                
                task = self.active_tasks[task_id]
                task.status = "loading"
                task.started_at = datetime.utcnow()
            
            start_time = time.time()
            
            # Execute loading based on strategy
            if task.loading_strategy == LoadingStrategy.LOD_BASED:
                result = await self._execute_lod_loading(task, db)
            elif task.loading_strategy == LoadingStrategy.DISTANCE_BASED:
                result = await self._execute_distance_based_loading(task, db)
            elif task.loading_strategy == LoadingStrategy.IMPORTANCE_BASED:
                result = await self._execute_importance_based_loading(task, db)
            elif task.loading_strategy == LoadingStrategy.CLUSTER_BASED:
                result = await self._execute_cluster_based_loading(task, db)
            else:
                result = {"success": False, "error": f"Unsupported loading strategy: {task.loading_strategy.value}"}
            
            execution_time = (time.time() - start_time) * 1000
            
            with self.lock:
                if task_id in self.active_tasks:
                    task = self.active_tasks[task_id]
                    task.status = "completed" if result["success"] else "failed"
                    task.completed_at = datetime.utcnow()
                    task.result = result
                    task.error_message = result.get("error") if not result["success"] else None
                    
                    # Update statistics
                    self.total_loads += 1
                    self.total_load_time += execution_time
                    self.average_load_time = self.total_load_time / self.total_loads
                    
                    # Move to history (remove from active)
                    del self.active_tasks[task_id]
            
        except Exception as e:
            logger.error(f"Error executing loading task {task_id}: {e}")
            
            with self.lock:
                if task_id in self.active_tasks:
                    task = self.active_tasks[task_id]
                    task.status = "failed"
                    task.completed_at = datetime.utcnow()
                    task.error_message = str(e)
    
    async def _execute_lod_loading(self, task: LoadingTask, db: AsyncSession) -> Dict[str, Any]:
        """Execute Level of Detail based loading."""
        try:
            loaded_items = []
            chunks_loaded = 0
            
            # Determine what to load based on detail level
            detail_config = self._get_detail_level_config(task.detail_level)
            
            # Load in chunks
            for chunk_index in range(task.total_chunks):
                if task.status == "cancelled":
                    break
                
                offset = chunk_index * task.chunk_size
                limit = task.chunk_size
                
                # Load chunk based on detail level
                if task.detail_level in [DetailLevel.MINIMAL, DetailLevel.LOW]:
                    # Load only essential nodes
                    chunk_data = await self._load_minimal_chunk(
                        offset, limit, detail_config, task.metadata, db
                    )
                elif task.detail_level == DetailLevel.MEDIUM:
                    chunk_data = await self._load_medium_chunk(
                        offset, limit, detail_config, task.metadata, db
                    )
                else:
                    # Load full detail
                    chunk_data = await self._load_full_chunk(
                        offset, limit, detail_config, task.metadata, db
                    )
                
                loaded_items.extend(chunk_data)
                chunks_loaded += 1
                
                # Update task progress
                with self.lock:
                    if task.task_id in self.active_tasks:
                        task.loaded_items = len(loaded_items)
                        task.current_chunk = chunk_index + 1
                
                # Small delay to prevent overwhelming
                await asyncio.sleep(0.01)
            
            return {
                "success": True,
                "loaded_items": len(loaded_items),
                "chunks_loaded": chunks_loaded,
                "detail_level": task.detail_level.value,
                "items": loaded_items
            }
            
        except Exception as e:
            logger.error(f"Error in LOD loading: {e}")
            return {
                "success": False,
                "error": f"LOD loading failed: {str(e)}"
            }
    
    async def _execute_distance_based_loading(self, task: LoadingTask, db: AsyncSession) -> Dict[str, Any]:
        """Execute distance-based loading."""
        try:
            viewport_info = task.metadata.get("viewport_info")
            if not viewport_info:
                return {
                    "success": False,
                    "error": "Viewport information required for distance-based loading"
                }
            
            loaded_items = []
            chunks_loaded = 0
            
            # Load chunks based on distance from viewport center
            for chunk_index in range(task.total_chunks):
                if task.status == "cancelled":
                    break
                
                # Calculate distance-based parameters for this chunk
                distance_factor = (chunk_index / max(task.total_chunks - 1, 1))
                
                chunk_data = await self._load_distance_chunk(
                    chunk_index, task.chunk_size, viewport_info, 
                    distance_factor, task.detail_level, db
                )
                
                loaded_items.extend(chunk_data)
                chunks_loaded += 1
                
                # Update task progress
                with self.lock:
                    if task.task_id in self.active_tasks:
                        task.loaded_items = len(loaded_items)
                        task.current_chunk = chunk_index + 1
                
                await asyncio.sleep(0.01)
            
            return {
                "success": True,
                "loaded_items": len(loaded_items),
                "chunks_loaded": chunks_loaded,
                "loading_strategy": "distance_based",
                "items": loaded_items
            }
            
        except Exception as e:
            logger.error(f"Error in distance-based loading: {e}")
            return {
                "success": False,
                "error": f"Distance-based loading failed: {str(e)}"
            }
    
    async def _execute_importance_based_loading(self, task: LoadingTask, db: AsyncSession) -> Dict[str, Any]:
        """Execute importance-based loading."""
        try:
            loaded_items = []
            chunks_loaded = 0
            
            # Load items ordered by importance
            for chunk_index in range(task.total_chunks):
                if task.status == "cancelled":
                    break
                
                offset = chunk_index * task.chunk_size
                limit = task.chunk_size
                
                # Load chunk based on importance ranking
                chunk_data = await self._load_importance_chunk(
                    offset, limit, task.detail_level, task.metadata, db
                )
                
                loaded_items.extend(chunk_data)
                chunks_loaded += 1
                
                # Update task progress
                with self.lock:
                    if task.task_id in self.active_tasks:
                        task.loaded_items = len(loaded_items)
                        task.current_chunk = chunk_index + 1
                
                await asyncio.sleep(0.01)
            
            return {
                "success": True,
                "loaded_items": len(loaded_items),
                "chunks_loaded": chunks_loaded,
                "loading_strategy": "importance_based",
                "items": loaded_items
            }
            
        except Exception as e:
            logger.error(f"Error in importance-based loading: {e}")
            return {
                "success": False,
                "error": f"Importance-based loading failed: {str(e)}"
            }
    
    async def _execute_cluster_based_loading(self, task: LoadingTask, db: AsyncSession) -> Dict[str, Any]:
        """Execute cluster-based loading."""
        try:
            loaded_items = []
            chunks_loaded = 0
            
            # Load cluster by cluster based on importance
            for chunk_index in range(task.total_chunks):
                if task.status == "cancelled":
                    break
                
                chunk_data = await self._load_cluster_chunk(
                    chunk_index, task.chunk_size, task.detail_level, 
                    task.metadata, db
                )
                
                loaded_items.extend(chunk_data)
                chunks_loaded += 1
                
                # Update task progress
                with self.lock:
                    if task.task_id in self.active_tasks:
                        task.loaded_items = len(loaded_items)
                        task.current_chunk = chunk_index + 1
                
                await asyncio.sleep(0.01)
            
            return {
                "success": True,
                "loaded_items": len(loaded_items),
                "chunks_loaded": chunks_loaded,
                "loading_strategy": "cluster_based",
                "items": loaded_items
            }
            
        except Exception as e:
            logger.error(f"Error in cluster-based loading: {e}")
            return {
                "success": False,
                "error": f"Cluster-based loading failed: {str(e)}"
            }
    
    async def _estimate_total_items(
        self,
        visualization_id: str,
        loading_strategy: LoadingStrategy,
        detail_level: DetailLevel,
        viewport: Optional[ViewportInfo],
        parameters: Dict[str, Any],
        db: AsyncSession
    ) -> int:
        """Estimate total items to be loaded."""
        try:
            # Base estimation counts
            base_counts = {
                DetailLevel.MINIMAL: 100,
                DetailLevel.LOW: 500,
                DetailLevel.MEDIUM: 2000,
                DetailLevel.HIGH: 5000,
                DetailLevel.FULL: 10000
            }
            
            base_count = base_counts.get(detail_level, 1000)
            
            # Adjust based on viewport
            if viewport:
                # Smaller viewport = fewer items
                viewport_area = viewport.width * viewport.height
                viewport_factor = min(1.0, viewport_area / (1920 * 1080))  # Normalize to Full HD
                base_count = int(base_count * viewport_factor)
            
            # Adjust based on loading strategy
            strategy_factors = {
                LoadingStrategy.LOD_BASED: 1.0,
                LoadingStrategy.DISTANCE_BASED: 0.8,
                LoadingStrategy.IMPORTANCE_BASED: 1.2,
                LoadingStrategy.CLUSTER_BASED: 0.9,
                LoadingStrategy.HYBRID: 1.0
            }
            
            strategy_factor = strategy_factors.get(loading_strategy, 1.0)
            estimated_count = int(base_count * strategy_factor)
            
            return max(estimated_count, 10)  # Minimum 10 items
            
        except Exception as e:
            logger.error(f"Error estimating total items: {e}")
            return 1000  # Default estimation
    
    def _generate_viewport_hash(self, viewport: ViewportInfo) -> str:
        """Generate hash for viewport caching."""
        try:
            import hashlib
            
            viewport_string = f"{viewport.center_x}_{viewport.center_y}_{viewport.zoom_level}_{viewport.width}_{viewport.height}"
            return hashlib.md5(viewport_string.encode()).hexdigest()
            
        except Exception:
            return f"viewport_{int(time.time())}"
    
    def _get_detail_level_config(self, detail_level: DetailLevel) -> Dict[str, Any]:
        """Get configuration for detail level."""
        configs = {
            DetailLevel.MINIMAL: {
                "include_properties": False,
                "include_relationships": False,
                "include_patterns": False,
                "max_nodes_per_type": 20
            },
            DetailLevel.LOW: {
                "include_properties": True,
                "include_relationships": True,
                "include_patterns": False,
                "max_nodes_per_type": 100
            },
            DetailLevel.MEDIUM: {
                "include_properties": True,
                "include_relationships": True,
                "include_patterns": True,
                "max_nodes_per_type": 500
            },
            DetailLevel.HIGH: {
                "include_properties": True,
                "include_relationships": True,
                "include_patterns": True,
                "max_nodes_per_type": 2000
            },
            DetailLevel.FULL: {
                "include_properties": True,
                "include_relationships": True,
                "include_patterns": True,
                "max_nodes_per_type": None
            }
        }
        
        return configs.get(detail_level, configs[DetailLevel.MEDIUM])
    
    def _cleanup_expired_caches(self):
        """Clean up expired loading caches."""
        try:
            current_time = datetime.utcnow()
            expired_caches = []
            
            for cache_id, cache in self.loading_caches.items():
                cache_age = (current_time - cache.last_accessed).total_seconds()
                if cache_age > self.cache_ttl_seconds:
                    expired_caches.append(cache_id)
            
            for cache_id in expired_caches:
                del self.loading_caches[cache_id]
                
            if expired_caches:
                logger.info(f"Cleaned up {len(expired_caches)} expired loading caches")
                
        except Exception as e:
            logger.error(f"Error cleaning up expired caches: {e}")
    
    def _optimize_loading_parameters(self):
        """Optimize loading parameters based on performance statistics."""
        try:
            # This would analyze performance metrics and adjust parameters
            # For now, just log current statistics
            if self.total_loads > 0:
                logger.debug(f"Loading performance: {self.average_load_time:.2f}ms average over {self.total_loads} loads")
                
        except Exception as e:
            logger.error(f"Error optimizing loading parameters: {e}")


# Singleton instance
progressive_loading_service = ProgressiveLoadingService()
