"""
Batch Conversion Automation Service

Implements automated batch processing with:
- Batch upload interface
- Intelligent queue management
- Priority-based processing
- Batch progress tracking
- Per-item error handling

Success Criteria:
- 100 mods in <1 hour
- Queue efficiency >90%
- Per-mod tracking accuracy 100%

Issue: REQ-2.13 - Batch Automation
"""

import asyncio
import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, AsyncIterator

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class BatchStatus(Enum):
    """Batch processing status."""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIAL = "partial"  # Some items failed
    FAILED = "failed"
    CANCELLED = "cancelled"


class ItemStatus(Enum):
    """Individual batch item status."""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class Priority(Enum):
    """Priority levels for batch items."""
    VIP = 100
    HIGH = 75
    NORMAL = 50
    LOW = 25


class ErrorType(Enum):
    """Types of errors that can occur during processing."""
    SYNTAX = "syntax"
    DEPENDENCY = "dependency"
    RESOURCE = "resource"
    TIMEOUT = "timeout"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


@dataclass
class ItemError:
    """Error information for a batch item."""
    item_id: str
    error_type: ErrorType
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    recoverable: bool = True
    retry_count: int = 0
    last_retry: Optional[datetime] = None


@dataclass
class BatchItem:
    """Individual item in a batch."""
    item_id: str
    filename: str
    file_path: str
    file_size: int
    checksum: str
    status: ItemStatus = ItemStatus.PENDING
    priority: int = Priority.NORMAL.value
    mode_classification: Optional[str] = None
    progress: float = 0.0
    error: Optional[ItemError] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result_path: Optional[str] = None
    retry_count: int = 0
    dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "filename": self.filename,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "checksum": self.checksum,
            "status": self.status.value,
            "priority": self.priority,
            "mode_classification": self.mode_classification,
            "progress": self.progress,
            "error": {
                "type": self.error.error_type.value if self.error else None,
                "message": self.error.message if self.error else None,
                "recoverable": self.error.recoverable if self.error else None,
                "retry_count": self.error.retry_count if self.error else 0,
            } if self.error else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result_path": self.result_path,
            "retry_count": self.retry_count,
            "dependencies": self.dependencies,
        }


@dataclass
class Batch:
    """Batch of mods to be processed."""
    batch_id: str
    user_id: str
    items: List[BatchItem] = field(default_factory=list)
    status: BatchStatus = BatchStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_items: int = 0
    completed_items: int = 0
    failed_items: int = 0
    progress: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "user_id": self.user_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_items": self.total_items,
            "completed_items": self.completed_items,
            "failed_items": self.failed_items,
            "progress": self.progress,
            "items": [item.to_dict() for item in self.items],
        }


@dataclass
class BatchUploadResult:
    """Result of a batch upload operation."""
    batch_id: str
    total_items: int
    valid_items: int
    errors: List[ItemError] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "total_items": self.total_items,
            "valid_items": self.valid_items,
            "errors": [
                {
                    "item_id": e.item_id,
                    "error_type": e.error_type.value,
                    "message": e.message,
                    "recoverable": e.recoverable,
                }
                for e in self.errors
            ],
        }


@dataclass
class ResourceRequirements:
    """Resource requirements for a batch item."""
    estimated_time: timedelta
    memory_mb: int = 512
    cpu_cores: float = 0.5
    gpu_required: bool = False


@dataclass
class QueueEntry:
    """Entry in the priority queue."""
    item: BatchItem
    priority: int
    requirements: ResourceRequirements
    enqueued_at: datetime


class BatchUploadHandler:
    """Handle batch mod file uploads."""
    
    MAX_BATCH_SIZE = 100
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
    SUPPORTED_FORMATS = ['.jar', '.zip', '.tar.gz']
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self._redis: Optional[aioredis.Redis] = None
        self.BATCH_KEY_PREFIX = "batch:"
        self.ITEM_KEY_PREFIX = "batch:item:"
    
    async def _get_redis(self) -> aioredis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis
    
    async def upload_batch(
        self,
        files: List[Dict[str, Any]],
        user_id: str,
    ) -> BatchUploadResult:
        """Process batch upload request."""
        r = await self._get_redis()
        
        # Validate batch size
        if len(files) > self.MAX_BATCH_SIZE:
            raise BatchSizeError(
                f"Maximum {self.MAX_BATCH_SIZE} files allowed"
            )
        
        # Generate batch ID
        batch_id = str(uuid.uuid4())
        
        # Validate each file
        validated_files = []
        errors = []
        
        for file in files:
            try:
                validated = await self._validate_file(file)
                validated_files.append(validated)
            except ValidationError as e:
                errors.append(ItemError(
                    item_id=file.get("filename", "unknown"),
                    error_type=ErrorType.VALIDATION,
                    message=str(e),
                    recoverable=False,
                ))
        
        # Create batch record
        batch = Batch(
            batch_id=batch_id,
            user_id=user_id,
            items=[self._create_batch_item(f) for f in validated_files],
            status=BatchStatus.PENDING,
            created_at=datetime.utcnow(),
            total_items=len(validated_files),
        )
        
        # Store batch in Redis
        await r.set(
            f"{self.BATCH_KEY_PREFIX}{batch_id}",
            json.dumps(batch.to_dict()),
            ex=86400 * 7,  # 7 day TTL
        )
        
        return BatchUploadResult(
            batch_id=batch_id,
            total_items=len(files),
            valid_items=len(validated_files),
            errors=errors,
        )
    
    async def _validate_file(self, file: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single file."""
        filename = file.get("filename", "")
        file_size = file.get("size", 0)
        
        # Check file extension
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if f".{ext}" not in self.SUPPORTED_FORMATS:
            raise ValidationError(f"Unsupported file format: {ext}")
        
        # Check file size
        if file_size > self.MAX_FILE_SIZE:
            raise ValidationError(f"File too large: {file_size} bytes (max {self.MAX_FILE_SIZE})")
        
        if file_size == 0:
            raise ValidationError("File is empty")
        
        return file
    
    def _create_batch_item(self, file: Dict[str, Any]) -> BatchItem:
        """Create a BatchItem from validated file data."""
        return BatchItem(
            item_id=str(uuid.uuid4()),
            filename=file.get("filename", "unknown"),
            file_path=file.get("path", ""),
            file_size=file.get("size", 0),
            checksum=file.get("checksum", ""),
            status=ItemStatus.PENDING,
            priority=Priority.NORMAL.value,
        )
    
    async def get_batch(self, batch_id: str) -> Optional[Batch]:
        """Get batch by ID."""
        r = await self._get_redis()
        data = await r.get(f"{self.BATCH_KEY_PREFIX}{batch_id}")
        if not data:
            return None
        
        batch_dict = json.loads(data)
        return self._deserialize_batch(batch_dict)
    
    def _deserialize_batch(self, data: Dict[str, Any]) -> Batch:
        """Deserialize batch from dict."""
        items = []
        for item_data in data.get("items", []):
            item = BatchItem(
                item_id=item_data["item_id"],
                filename=item_data["filename"],
                file_path=item_data["file_path"],
                file_size=item_data["file_size"],
                checksum=item_data["checksum"],
                status=ItemStatus(item_data.get("status", "pending")),
                priority=item_data.get("priority", Priority.NORMAL.value),
                mode_classification=item_data.get("mode_classification"),
                progress=item_data.get("progress", 0.0),
                started_at=datetime.fromisoformat(item_data["started_at"]) if item_data.get("started_at") else None,
                completed_at=datetime.fromisoformat(item_data["completed_at"]) if item_data.get("completed_at") else None,
                result_path=item_data.get("result_path"),
                retry_count=item_data.get("retry_count", 0),
            )
            items.append(item)
        
        return Batch(
            batch_id=data["batch_id"],
            user_id=data["user_id"],
            items=items,
            status=BatchStatus(data.get("status", "pending")),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            total_items=data.get("total_items", len(items)),
            completed_items=data.get("completed_items", 0),
            failed_items=data.get("failed_items", 0),
            progress=data.get("progress", 0.0),
        )
    
    async def update_batch(self, batch: Batch) -> None:
        """Update batch in Redis."""
        r = await self._get_redis()
        await r.set(
            f"{self.BATCH_KEY_PREFIX}{batch.batch_id}",
            json.dumps(batch.to_dict()),
            ex=86400 * 7,
        )


class BatchSizeError(Exception):
    """Error when batch size exceeds limit."""
    pass


class ValidationError(Exception):
    """Error during file validation."""
    pass


class RecoveryFailedError(Exception):
    """Error when recovery fails."""
    pass


class IntelligentQueueManager:
    """Manage conversion queue with intelligence."""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        max_cpu_slots: int = 4,
        max_memory_gb: int = 16,
        max_concurrent: int = 4,
    ):
        self.redis_url = redis_url
        self._redis: Optional[aioredis.Redis] = None
        self.max_cpu_slots = max_cpu_slots
        self.max_memory_gb = max_memory_gb
        self.max_concurrent = max_concurrent
        
        # Resource tracking
        self._cpu_in_use = 0
        self._memory_in_use = 0
        self._concurrent_jobs = 0
        
        # Queue
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running = False
        self._workers: List[asyncio.Task] = []
        
        # Callbacks
        self.processing_callback: Optional[Callable] = None
    
    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis
    
    async def enqueue(
        self,
        item: BatchItem,
        priority: Priority = Priority.NORMAL,
    ) -> None:
        """Add item to queue with priority."""
        # Analyze resource requirements
        requirements = await self._analyze_requirements(item)
        
        # Calculate effective priority
        effective_priority = await self._calculate_priority(
            base=priority,
            requirements=requirements,
            item=item,
        )
        
        # Create queue entry
        queue_entry = QueueEntry(
            item=item,
            priority=effective_priority,
            requirements=requirements,
            enqueued_at=datetime.utcnow(),
        )
        
        # Enqueue (use negative priority for max-heap behavior)
        await self.queue.put((-effective_priority, queue_entry))
        
        # Update item status
        item.status = ItemStatus.QUEUED
        item.priority = effective_priority
        
        logger.info(f"Item {item.item_id} enqueued with priority {effective_priority}")
    
    async def _analyze_requirements(self, item: BatchItem) -> ResourceRequirements:
        """Analyze resource requirements for an item."""
        # Estimate based on file size
        base_time = timedelta(minutes=1)
        
        if item.file_size > 100 * 1024 * 1024:  # > 100MB
            base_time = timedelta(minutes=5)
        elif item.file_size > 50 * 1024 * 1024:  # > 50MB
            base_time = timedelta(minutes=3)
        
        return ResourceRequirements(
            estimated_time=base_time,
            memory_mb=min(1024, max(256, item.file_size // 1024 // 100)),
            cpu_cores=0.5,
            gpu_required=False,
        )
    
    async def _calculate_priority(
        self,
        base: Priority,
        requirements: ResourceRequirements,
        item: BatchItem,
    ) -> int:
        """Calculate effective priority considering wait time."""
        base_priority = base.value
        
        # Estimate wait time based on queue depth
        queue_size = self.queue.qsize() if hasattr(self.queue, 'qsize') else 0
        wait_time_estimate = timedelta(
            seconds=queue_size * requirements.estimated_time.total_seconds()
        )
        
        # Boost priority for long-waiting items
        if wait_time_estimate > timedelta(minutes=5):
            base_priority += 10
        elif wait_time_estimate > timedelta(minutes=2):
            base_priority += 5
        
        # Boost for smaller, simpler jobs
        if requirements.estimated_time < timedelta(minutes=2):
            base_priority += 5
        
        return min(base_priority, 100)  # Cap at 100
    
    async def process_queue(self, processing_func: Callable[[BatchItem], Any]) -> None:
        """Main queue processing loop."""
        self._running = True
        
        # Start worker pool
        self._workers = [
            asyncio.create_task(self._worker(processing_func))
            for _ in range(self.max_concurrent)
        ]
        
        logger.info(f"Queue processing started with {self.max_concurrent} workers")
    
    async def _worker(self, processing_func: Callable[[BatchItem], Any]) -> None:
        """Worker task that processes items from queue."""
        while self._running:
            try:
                # Get next item from queue
                try:
                    neg_priority, entry = await asyncio.wait_for(
                        self.queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                item = entry.item
                
                # Check resources
                if not await self._can_process(entry.requirements):
                    # Re-queue with backoff
                    await self.queue.put((neg_priority, entry))
                    await asyncio.sleep(0.5)
                    continue
                
                # Acquire resources
                await self._acquire_resources(entry.requirements)
                
                try:
                    # Process item
                    item.status = ItemStatus.PROCESSING
                    item.started_at = datetime.utcnow()
                    
                    result = await processing_func(item)
                    
                    # Mark complete
                    item.status = ItemStatus.COMPLETED
                    item.completed_at = datetime.utcnow()
                    item.result_path = result.get("path") if result else None
                    item.progress = 1.0
                    
                    logger.info(f"Item {item.item_id} completed successfully")
                    
                except Exception as e:
                    # Handle error
                    await self._handle_error(item, e)
                    
                finally:
                    # Release resources
                    await self._release_resources(entry.requirements)
                    self.queue.task_done()
                    
            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(1)
    
    async def _can_process(self, requirements: ResourceRequirements) -> bool:
        """Check if resources are available."""
        return (
            self._cpu_in_use < self.max_cpu_slots and
            self._memory_in_use + requirements.memory_mb < self.max_memory_gb * 1024 and
            self._concurrent_jobs < self.max_concurrent
        )
    
    async def _acquire_resources(self, requirements: ResourceRequirements) -> None:
        """Acquire resources for processing."""
        self._cpu_in_use += requirements.cpu_cores
        self._memory_in_use += requirements.memory_mb
        self._concurrent_jobs += 1
    
    async def _release_resources(self, requirements: ResourceRequirements) -> None:
        """Release resources after processing."""
        self._cpu_in_use = max(0, self._cpu_in_use - requirements.cpu_cores)
        self._memory_in_use = max(0, self._memory_in_use - requirements.memory_mb)
        self._concurrent_jobs = max(0, self._concurrent_jobs - 1)
    
    async def _handle_error(self, item: BatchItem, error: Exception) -> None:
        """Handle processing error."""
        error_type = self._classify_error(error)
        
        item.error = ItemError(
            item_id=item.item_id,
            error_type=error_type,
            message=str(error),
            recoverable=True,
            retry_count=item.retry_count,
        )
        
        if item.retry_count < 3:
            # Retry with backoff
            item.status = ItemStatus.RETRYING
            item.retry_count += 1
            
            # Use small delay for testing, normal for production
            import os
            if os.environ.get('TESTING'):
                backoff = 0.001
            else:
                backoff = 2 ** item.retry_count * 10  # 20s, 40s, 80s
            await asyncio.sleep(backoff)
            
            # Re-queue with base priority (50 = NORMAL)
            base_priority = Priority.NORMAL
            await self.enqueue(item, base_priority)
            logger.info(f"Item {item.item_id} requeued (retry {item.retry_count})")
        else:
            # Max retries exceeded
            item.status = ItemStatus.FAILED
            item.error.recoverable = False
            logger.error(f"Item {item.item_id} failed after max retries")
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """Classify error type."""
        error_msg = str(error).lower()
        
        if "syntax" in error_msg:
            return ErrorType.SYNTAX
        elif "dependency" in error_msg:
            return ErrorType.DEPENDENCY
        elif "memory" in error_msg or "resource" in error_msg:
            return ErrorType.RESOURCE
        elif "timeout" in error_msg:
            return ErrorType.TIMEOUT
        elif "validation" in error_msg:
            return ErrorType.VALIDATION
        else:
            return ErrorType.UNKNOWN
    
    async def stop(self) -> None:
        """Stop queue processing."""
        self._running = False
        
        # Cancel workers
        for worker in self._workers:
            worker.cancel()
        
        await asyncio.gather(*self._workers, return_exceptions=True)
        logger.info("Queue processing stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            "queue_size": self.queue.qsize(),
            "cpu_in_use": self._cpu_in_use,
            "memory_in_use_mb": self._memory_in_use,
            "concurrent_jobs": self._concurrent_jobs,
            "max_cpu_slots": self.max_cpu_slots,
            "max_memory_gb": self.max_memory_gb,
            "max_concurrent": self.max_concurrent,
        }


class BatchProgressTracker:
    """Track progress of batch operations."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self._redis: Optional[aioredis.Redis] = None
        self.PROGRESS_KEY_PREFIX = "batch:progress:"
    
    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis
    
    async def update_progress(
        self,
        batch_id: str,
        item_id: str,
        progress: float,
        status: ItemStatus,
        message: str = "",
    ) -> None:
        """Update progress for a single item."""
        r = await self._get_redis()
        
        progress_data = {
            "batch_id": batch_id,
            "item_id": item_id,
            "progress": progress,
            "status": status.value,
            "message": message,
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        await r.hset(
            f"{self.PROGRESS_KEY_PREFIX}{batch_id}",
            mapping={item_id: json.dumps(progress_data)}
        )
    
    async def get_item_progress(self, batch_id: str, item_id: str) -> Optional[Dict]:
        """Get progress for a specific item."""
        r = await self._get_redis()
        data = await r.hget(f"{self.PROGRESS_KEY_PREFIX}{batch_id}", item_id)
        return json.loads(data) if data else None
    
    async def get_batch_progress(self, batch_id: str) -> Dict[str, Any]:
        """Get overall batch progress."""
        r = await self._get_redis()
        all_items = await r.hgetall(f"{self.PROGRESS_KEY_PREFIX}{batch_id}")
        
        total = len(all_items)
        if total == 0:
            return {"total": 0, "completed": 0, "failed": 0, "progress": 0.0}
        
        completed = sum(1 for p in all_items.values() if json.loads(p).get("status") == "completed")
        failed = sum(1 for p in all_items.values() if json.loads(p).get("status") == "failed")
        
        # Calculate average progress
        total_progress = sum(json.loads(p).get("progress", 0) for p in all_items.values())
        avg_progress = total_progress / total if total > 0 else 0.0
        
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "progress": avg_progress,
            "items": {k: json.loads(v) for k, v in all_items.items()},
        }
    
    async def watch_batch(self, batch_id: str) -> AsyncIterator[Dict[str, Any]]:
        """Watch batch progress (for WebSocket streaming)."""
        r = await self._get_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe(f"batch:{batch_id}:progress")
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield json.loads(message["data"])
        finally:
            await pubsub.unsubscribe(f"batch:{batch_id}:progress")
            await pubsub.close()


class BatchErrorHandler:
    """Handle errors for batch items with recovery strategies."""
    
    RECOVERY_STRATEGIES: Dict[ErrorType, Callable] = {}
    
    def __init__(self, queue_manager: IntelligentQueueManager):
        self.queue_manager = queue_manager
        self.syntax_fixer = None  # Placeholder for syntax fixing service
        self.validator = None    # Placeholder for validation service
    
    async def handle_error(self, item: BatchItem, error: Exception) -> Dict[str, Any]:
        """Handle error and attempt recovery."""
        error_type = self._classify_error(error)
        
        # Check max retries
        if item.retry_count >= 3:
            item.status = ItemStatus.FAILED
            return {
                "action": "failed",
                "recoverable": False,
                "reason": "Max retries exceeded",
            }
        
        # Try recovery
        recovery_strategy = self.RECOVERY_STRATEGIES.get(error_type)
        if recovery_strategy:
            try:
                await recovery_strategy(item, error)
                item.retry_count += 1
                item.status = ItemStatus.QUEUED
                
                return {
                    "action": "retrying",
                    "recoverable": True,
                    "retry_after": item.retry_count * 2,
                }
            except Exception as recovery_error:
                logger.error(f"Recovery failed: {recovery_error}")
        
        # Default: requeue with backoff
        await self._requeue_with_backoff(item)
        
        return {
            "action": "requeued",
            "recoverable": True,
        }
    
    async def _requeue_with_backoff(self, item: BatchItem) -> None:
        """Requeue item with exponential backoff."""
        backoff_seconds = (2 ** item.retry_count) * 10
        
        item.status = ItemStatus.QUEUED
        item.retry_count += 1
        
        await self.queue_manager.enqueue(item, Priority(item.priority))
        logger.info(f"Item {item.item_id} requeued with {backoff_seconds}s backoff")
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """Classify error type."""
        error_msg = str(error).lower()
        
        if "syntax" in error_msg:
            return ErrorType.SYNTAX
        elif "dependency" in error_msg:
            return ErrorType.DEPENDENCY
        elif "memory" in error_msg or "resource" in error_msg:
            return ErrorType.RESOURCE
        elif "timeout" in error_msg:
            return ErrorType.TIMEOUT
        else:
            return ErrorType.UNKNOWN


# Singleton instances
_batch_upload_handler: Optional[BatchUploadHandler] = None
_queue_manager: Optional[IntelligentQueueManager] = None
_progress_tracker: Optional[BatchProgressTracker] = None


def get_batch_upload_handler() -> BatchUploadHandler:
    """Get or create batch upload handler singleton."""
    global _batch_upload_handler
    if _batch_upload_handler is None:
        _batch_upload_handler = BatchUploadHandler()
    return _batch_upload_handler


def get_queue_manager() -> IntelligentQueueManager:
    """Get or create queue manager singleton."""
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = IntelligentQueueManager()
    return _queue_manager


def get_progress_tracker() -> BatchProgressTracker:
    """Get or create progress tracker singleton."""
    global _progress_tracker
    if _progress_tracker is None:
        _progress_tracker = BatchProgressTracker()
    return _progress_tracker
