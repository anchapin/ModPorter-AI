"""
Batch Conversion Automation System

Enables automated batch processing with:
- Batch upload interface
- Intelligent queue management
- Priority-based processing
- Real-time progress tracking
"""

import logging
<<<<<<< HEAD
from typing import Dict, List, Optional, Any
=======
from typing import Dict, List, Optional, Any, Tuple
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict
import threading
import time
import uuid

logger = logging.getLogger(__name__)


class Priority(Enum):
    """Conversion priority levels."""
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class BatchStatus(Enum):
    """Batch job status."""
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIAL = "partial"  # Some failed
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchJob:
    """Represents a batch conversion job."""
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    batch_id: str
    user_id: str
    mods: List[Dict[str, Any]]  # List of mod paths/info
    priority: Priority = Priority.NORMAL
    status: BatchStatus = BatchStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    # Progress tracking
    total_mods: int = 0
    completed_mods: int = 0
    failed_mods: int = 0
    current_progress: float = 0.0  # 0.0 to 100.0
<<<<<<< HEAD

    # Results
    results: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    # Settings
    auto_start: bool = True
    notify_on_complete: bool = True

=======
    
    # Results
    results: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    # Settings
    auto_start: bool = True
    notify_on_complete: bool = True
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "user_id": self.user_id,
            "total_mods": self.total_mods,
            "completed_mods": self.completed_mods,
            "failed_mods": self.failed_mods,
            "progress": self.current_progress,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "estimated_completion": self.estimated_completion(),
        }
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def estimated_completion(self) -> Optional[str]:
        """Estimate completion time."""
        if self.started_at is None:
            return None
<<<<<<< HEAD

        # Assume ~2 minutes per mod average
        remaining = self.total_mods - self.completed_mods
        estimated_minutes = remaining * 2

        from datetime import timedelta

=======
        
        # Assume ~2 minutes per mod average
        remaining = self.total_mods - self.completed_mods
        estimated_minutes = remaining * 2
        
        from datetime import timedelta
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        eta = self.started_at + timedelta(minutes=estimated_minutes)
        return eta.isoformat()


@dataclass
class QueueStats:
    """Statistics for the conversion queue."""
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    total_jobs: int = 0
    pending_jobs: int = 0
    processing_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
<<<<<<< HEAD

    total_mods: int = 0
    mods_completed: int = 0
    mods_failed: int = 0

    avg_wait_time: float = 0.0  # seconds
    avg_process_time: float = 0.0  # seconds

=======
    
    total_mods: int = 0
    mods_completed: int = 0
    mods_failed: int = 0
    
    avg_wait_time: float = 0.0  # seconds
    avg_process_time: float = 0.0  # seconds
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_jobs": self.total_jobs,
            "pending_jobs": self.pending_jobs,
            "processing_jobs": self.processing_jobs,
            "completed_jobs": self.completed_jobs,
            "failed_jobs": self.failed_jobs,
            "total_mods": self.total_mods,
            "mods_completed": self.mods_completed,
            "mods_failed": self.mods_failed,
            "avg_wait_time_sec": self.avg_wait_time,
            "avg_process_time_sec": self.avg_process_time,
        }


class BatchConversionQueue:
    """
    Intelligent queue management for batch conversions.
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    Features:
    - Priority-based scheduling
    - Fair queuing
    - Rate limiting
    - Resource management
    """
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self.jobs: Dict[str, BatchJob] = {}
        self.priority_queues: Dict[Priority, List[str]] = {
            Priority.URGENT: [],
            Priority.HIGH: [],
            Priority.NORMAL: [],
            Priority.LOW: [],
        }
        self.active_jobs: List[str] = []
        self.completed_jobs: List[str] = []
        self._lock = threading.Lock()
        self._processor_thread: Optional[threading.Thread] = None
        self._running = False
<<<<<<< HEAD

        logger.info(f"BatchConversionQueue initialized (max_concurrent={max_concurrent})")

=======
        
        logger.info(f"BatchConversionQueue initialized (max_concurrent={max_concurrent})")
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def submit_job(self, job: BatchJob) -> str:
        """Submit a batch job to the queue."""
        with self._lock:
            self.jobs[job.batch_id] = job
            self.priority_queues[job.priority].append(job.batch_id)
            job.status = BatchStatus.QUEUED
<<<<<<< HEAD

            logger.info(
                f"Batch job submitted: {job.batch_id} ({job.total_mods} mods, priority={job.priority.name})"
            )

            # Auto-start processing if not running
            if not self._running:
                self.start_processing()

            return job.batch_id

=======
            
            logger.info(f"Batch job submitted: {job.batch_id} ({job.total_mods} mods, priority={job.priority.name})")
            
            # Auto-start processing if not running
            if not self._running:
                self.start_processing()
            
            return job.batch_id
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def get_next_job(self) -> Optional[BatchJob]:
        """Get the next job to process based on priority."""
        with self._lock:
            # Check priority queues in order
<<<<<<< HEAD
            for priority in [
                Priority.URGENT,
                Priority.HIGH,
                Priority.NORMAL,
                Priority.LOW,
            ]:
                if self.priority_queues[priority]:
                    job_id = self.priority_queues[priority].pop(0)
                    job = self.jobs.get(job_id)

=======
            for priority in [Priority.URGENT, Priority.HIGH, Priority.NORMAL, Priority.LOW]:
                if self.priority_queues[priority]:
                    job_id = self.priority_queues[priority].pop(0)
                    job = self.jobs.get(job_id)
                    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
                    if job and job.status == BatchStatus.QUEUED:
                        self.active_jobs.append(job_id)
                        job.status = BatchStatus.PROCESSING
                        job.started_at = datetime.now()
                        return job
<<<<<<< HEAD

            return None

=======
            
            return None
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def complete_job(self, job_id: str, success: bool = True):
        """Mark a job as completed."""
        with self._lock:
            job = self.jobs.get(job_id)
            if not job:
                return
<<<<<<< HEAD

            job.completed_at = datetime.now()
            job.status = BatchStatus.COMPLETED if success else BatchStatus.FAILED

            if job_id in self.active_jobs:
                self.active_jobs.remove(job_id)

            self.completed_jobs.append(job_id)

            # Update progress
            job.current_progress = 100.0

            logger.info(f"Batch job completed: {job_id} (success={success})")

=======
            
            job.completed_at = datetime.now()
            job.status = BatchStatus.COMPLETED if success else BatchStatus.FAILED
            
            if job_id in self.active_jobs:
                self.active_jobs.remove(job_id)
            
            self.completed_jobs.append(job_id)
            
            # Update progress
            job.current_progress = 100.0
            
            logger.info(f"Batch job completed: {job_id} (success={success})")
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def update_job_progress(self, job_id: str, completed: int, failed: int):
        """Update job progress."""
        with self._lock:
            job = self.jobs.get(job_id)
            if not job:
                return
<<<<<<< HEAD

            job.completed_mods = completed
            job.failed_mods = failed
            job.current_progress = (completed / job.total_mods * 100) if job.total_mods > 0 else 0

=======
            
            job.completed_mods = completed
            job.failed_mods = failed
            job.current_progress = (completed / job.total_mods * 100) if job.total_mods > 0 else 0
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a job."""
        job = self.jobs.get(job_id)
        return job.to_dict() if job else None
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def get_queue_stats(self) -> QueueStats:
        """Get queue statistics."""
        with self._lock:
            stats = QueueStats()
<<<<<<< HEAD

=======
            
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
            stats.total_jobs = len(self.jobs)
            stats.pending_jobs = sum(len(q) for q in self.priority_queues.values())
            stats.processing_jobs = len(self.active_jobs)
            stats.completed_jobs = len(self.completed_jobs)
<<<<<<< HEAD

=======
            
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
            # Count mods
            for job in self.jobs.values():
                stats.total_mods += job.total_mods
                stats.mods_completed += job.completed_mods
                stats.mods_failed += job.failed_mods
<<<<<<< HEAD

            return stats

=======
            
            return stats
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def start_processing(self):
        """Start the background processor thread."""
        if self._running:
            return
<<<<<<< HEAD

=======
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        self._running = True
        self._processor_thread = threading.Thread(target=self._process_loop, daemon=True)
        self._processor_thread.start()
        logger.info("Batch processor started")
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def stop_processing(self):
        """Stop the background processor thread."""
        self._running = False
        if self._processor_thread:
            self._processor_thread.join(timeout=5)
        logger.info("Batch processor stopped")
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def _process_loop(self):
        """Background processing loop."""
        while self._running:
            # Check if we can process more jobs
            with self._lock:
                can_process = len(self.active_jobs) < self.max_concurrent
<<<<<<< HEAD

=======
            
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
            if can_process:
                job = self.get_next_job()
                if job:
                    # In production, this would trigger actual processing
                    # For now, just simulate
                    logger.debug(f"Processing job: {job.batch_id}")
            else:
                time.sleep(1)  # Wait before checking again
<<<<<<< HEAD

=======
            
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
            time.sleep(0.1)  # Small delay to prevent busy waiting


class BatchProgressTracker:
    """
    Real-time progress tracking for batch conversions.
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    Features:
    - Per-mod progress
    - Overall batch progress
    - ETA calculation
    - Progress callbacks
    """
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def __init__(self):
        self.batch_progress: Dict[str, Dict[str, Any]] = {}
        self.callbacks: Dict[str, List[callable]] = defaultdict(list)
        self._lock = threading.Lock()
        logger.info("BatchProgressTracker initialized")
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def register_batch(self, batch_id: str, total_mods: int):
        """Register a new batch for tracking."""
        with self._lock:
            self.batch_progress[batch_id] = {
                "batch_id": batch_id,
                "total_mods": total_mods,
                "completed_mods": 0,
                "failed_mods": 0,
                "current_mod": None,
                "progress": 0.0,
                "started_at": datetime.now().isoformat(),
                "completed_at": None,
                "eta_minutes": None,
            }
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def update_progress(
        self,
        batch_id: str,
        completed: int,
        failed: int,
        current_mod: Optional[str] = None,
    ):
        """Update batch progress."""
        with self._lock:
            if batch_id not in self.batch_progress:
                return
<<<<<<< HEAD

=======
            
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
            progress = self.batch_progress[batch_id]
            progress["completed_mods"] = completed
            progress["failed_mods"] = failed
            progress["current_mod"] = current_mod
<<<<<<< HEAD
            progress["progress"] = (
                (completed / progress["total_mods"] * 100) if progress["total_mods"] > 0 else 0
            )

            # Calculate ETA
            if completed > 0:
                elapsed = (
                    datetime.now() - datetime.fromisoformat(progress["started_at"])
                ).total_seconds()
                avg_per_mod = elapsed / completed
                remaining = progress["total_mods"] - completed
                progress["eta_minutes"] = (avg_per_mod * remaining) / 60

            # Trigger callbacks
            self._trigger_callbacks(batch_id, progress)

=======
            progress["progress"] = (completed / progress["total_mods"] * 100) if progress["total_mods"] > 0 else 0
            
            # Calculate ETA
            if completed > 0:
                elapsed = (datetime.now() - datetime.fromisoformat(progress["started_at"])).total_seconds()
                avg_per_mod = elapsed / completed
                remaining = progress["total_mods"] - completed
                progress["eta_minutes"] = (avg_per_mod * remaining) / 60
            
            # Trigger callbacks
            self._trigger_callbacks(batch_id, progress)
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def complete_batch(self, batch_id: str, success: bool = True):
        """Mark a batch as completed."""
        with self._lock:
            if batch_id not in self.batch_progress:
                return
<<<<<<< HEAD

            progress = self.batch_progress[batch_id]
            progress["completed_at"] = datetime.now().isoformat()
            progress["progress"] = 100.0 if success else progress["progress"]

            self._trigger_callbacks(batch_id, progress)

=======
            
            progress = self.batch_progress[batch_id]
            progress["completed_at"] = datetime.now().isoformat()
            progress["progress"] = 100.0 if success else progress["progress"]
            
            self._trigger_callbacks(batch_id, progress)
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def register_callback(self, batch_id: str, callback: callable):
        """Register a callback for progress updates."""
        with self._lock:
            self.callbacks[batch_id].append(callback)
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def _trigger_callbacks(self, batch_id: str, progress: Dict[str, Any]):
        """Trigger registered callbacks."""
        for callback in self.callbacks.get(batch_id, []):
            try:
                callback(progress)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")
<<<<<<< HEAD

    def get_progress(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get current progress for a batch."""
        return self.batch_progress.get(batch_id)

=======
    
    def get_progress(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get current progress for a batch."""
        return self.batch_progress.get(batch_id)
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def get_all_progress(self) -> List[Dict[str, Any]]:
        """Get progress for all active batches."""
        with self._lock:
            return list(self.batch_progress.values())


class BatchConversionManager:
    """
    Main manager for batch conversion automation.
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    Coordinates:
    - Batch submission
    - Queue management
    - Progress tracking
    - Results aggregation
    """
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def __init__(self, max_concurrent: int = 3):
        self.queue = BatchConversionQueue(max_concurrent)
        self.tracker = BatchProgressTracker()
        self._conversion_callback = None  # Would be actual conversion function
        logger.info("BatchConversionManager initialized")
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def create_batch(
        self,
        user_id: str,
        mod_paths: List[str],
        priority: Priority = Priority.NORMAL,
        auto_start: bool = True,
    ) -> BatchJob:
        """Create a new batch conversion job."""
        batch_id = str(uuid.uuid4())[:8]
<<<<<<< HEAD

=======
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        # Handle string priority
        if isinstance(priority, str):
            priority_map = {
                "low": Priority.LOW,
                "normal": Priority.NORMAL,
                "high": Priority.HIGH,
                "urgent": Priority.URGENT,
            }
            priority = priority_map.get(priority.lower(), Priority.NORMAL)
<<<<<<< HEAD

        # Prepare mod info
        mods = [{"path": path, "status": "pending"} for path in mod_paths]

=======
        
        # Prepare mod info
        mods = [{"path": path, "status": "pending"} for path in mod_paths]
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        # Create batch job
        job = BatchJob(
            batch_id=batch_id,
            user_id=user_id,
            mods=mods,
            priority=priority,
            total_mods=len(mod_paths),
            auto_start=auto_start,
        )
<<<<<<< HEAD

        # Register for progress tracking
        self.tracker.register_batch(batch_id, len(mod_paths))

        # Submit to queue
        self.queue.submit_job(job)

        logger.info(f"Batch created: {batch_id} ({len(mod_paths)} mods)")

        return job

    def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a batch job."""
        return self.queue.get_job_status(batch_id)

=======
        
        # Register for progress tracking
        self.tracker.register_batch(batch_id, len(mod_paths))
        
        # Submit to queue
        self.queue.submit_job(job)
        
        logger.info(f"Batch created: {batch_id} ({len(mod_paths)} mods)")
        
        return job
    
    def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a batch job."""
        return self.queue.get_job_status(batch_id)
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        stats = self.queue.get_queue_stats()
        return stats.to_dict()
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def cancel_batch(self, batch_id: str) -> bool:
        """Cancel a batch job."""
        job = self.queue.jobs.get(batch_id)
        if not job or job.status not in [BatchStatus.PENDING, BatchStatus.QUEUED]:
            return False
<<<<<<< HEAD

        job.status = BatchStatus.CANCELLED
        logger.info(f"Batch cancelled: {batch_id}")
        return True

    def set_conversion_callback(self, callback: callable):
        """Set callback for actual conversion processing."""
        self._conversion_callback = callback

=======
        
        job.status = BatchStatus.CANCELLED
        logger.info(f"Batch cancelled: {batch_id}")
        return True
    
    def set_conversion_callback(self, callback: callable):
        """Set callback for actual conversion processing."""
        self._conversion_callback = callback
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def process_batch(self, batch_id: str):
        """Process a batch job (simulated)."""
        job = self.queue.jobs.get(batch_id)
        if not job:
            return
<<<<<<< HEAD

        logger.info(f"Processing batch: {batch_id}")

=======
        
        logger.info(f"Processing batch: {batch_id}")
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        # Simulate processing each mod
        for i, mod in enumerate(job.mods):
            # Update progress
            self.tracker.update_progress(
                batch_id,
                completed=i,
                failed=job.failed_mods,
                current_mod=mod.get("path"),
            )
            self.queue.update_job_progress(batch_id, i, job.failed_mods)
<<<<<<< HEAD

            # Simulate conversion (would call actual conversion here)
            time.sleep(0.1)  # Simulate work
            mod["status"] = "completed"

=======
            
            # Simulate conversion (would call actual conversion here)
            time.sleep(0.1)  # Simulate work
            mod["status"] = "completed"
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        # Complete batch
        job.completed_mods = len(job.mods)
        self.tracker.complete_batch(batch_id, success=True)
        self.queue.complete_job(batch_id, success=True)
<<<<<<< HEAD

=======
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        logger.info(f"Batch processing complete: {batch_id}")


# Convenience functions
def create_batch_conversion(
    user_id: str,
    mod_paths: List[str],
    priority: str = "normal",
) -> BatchJob:
    """
    Create a batch conversion job.
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    Args:
        user_id: User identifier
        mod_paths: List of mod file paths
        priority: Priority level (low, normal, high, urgent)
<<<<<<< HEAD

=======
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    Returns:
        BatchJob instance
    """
    manager = BatchConversionManager()
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    priority_map = {
        "low": Priority.LOW,
        "normal": Priority.NORMAL,
        "high": Priority.HIGH,
        "urgent": Priority.URGENT,
    }
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    return manager.create_batch(
        user_id=user_id,
        mod_paths=mod_paths,
        priority=priority_map.get(priority.lower(), Priority.NORMAL),
    )


def get_batch_progress(batch_id: str) -> Optional[Dict[str, Any]]:
    """
    Get progress of a batch conversion.
<<<<<<< HEAD

    Args:
        batch_id: Batch job identifier

=======
    
    Args:
        batch_id: Batch job identifier
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    Returns:
        Progress dictionary or None
    """
    manager = BatchConversionManager()
    return manager.get_batch_status(batch_id)
