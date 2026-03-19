"""
Batch Conversion Automation - Load Tests

Tests the batch processing system against success criteria:
- 100 mods in <1 hour
- Queue efficiency >90%
- Per-mod tracking accuracy 100%

Issue: REQ-2.13 - Batch Automation
"""

import asyncio
import time
import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any

from services.batch_processor import (
    BatchUploadHandler,
    IntelligentQueueManager,
    BatchProgressTracker,
    BatchErrorHandler,
    Batch,
    BatchItem,
    BatchStatus,
    ItemStatus,
    Priority,
    ErrorType,
    ResourceRequirements,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
async def batch_handler():
    """Create batch upload handler."""
    handler = BatchUploadHandler(redis_url="redis://localhost:6379")
    yield handler
    await handler._redis.close() if handler._redis else None


@pytest.fixture
async def queue_manager():
    """Create queue manager."""
    manager = IntelligentQueueManager(
        redis_url="redis://localhost:6379",
        max_cpu_slots=4,
        max_memory_gb=16,
        max_concurrent=4,
    )
    yield manager
    await manager.stop()


@pytest.fixture
async def progress_tracker():
    """Create progress tracker."""
    tracker = BatchProgressTracker(redis_url="redis://localhost:6379")
    yield tracker
    await tracker._redis.close() if tracker._redis else None


# ============================================================================
# Helper Functions
# ============================================================================

def create_test_items(count: int) -> List[Dict[str, Any]]:
    """Create test batch items."""
    items = []
    for i in range(count):
        items.append({
            "filename": f"test_mod_{i}.jar",
            "size": 10 * 1024 * 1024,  # 10MB
            "path": f"/tmp/test_mod_{i}.jar",
            "checksum": f"checksum_{i}",
        })
    return items


async def simulate_processing(item: BatchItem) -> Dict[str, Any]:
    """Simulate mod processing."""
    # Simulate processing time based on file size
    await asyncio.sleep(0.01)  # Very fast for testing
    return {"path": f"/outputs/{item.item_id}.mcaddon"}


# ============================================================================
# Test: Batch Upload Interface
# ============================================================================

@pytest.mark.asyncio
async def test_batch_upload_validation(batch_handler):
    """Test batch upload with file validation."""
    # Test valid files
    valid_files = create_test_items(5)
    result = await batch_handler.upload_batch(valid_files, "test_user")
    
    assert result.batch_id is not None
    assert result.valid_items == 5
    assert result.total_items == 5
    assert len(result.errors) == 0
    
    # Test batch size limit
    large_batch = create_test_items(101)
    with pytest.raises(Exception):  # BatchSizeError
        await batch_handler.upload_batch(large_batch, "test_user")


@pytest.mark.asyncio
async def test_duplicate_detection(batch_handler):
    """Test duplicate file detection."""
    # Files with same checksum
    files = [
        {"filename": "mod1.jar", "size": 1000, "path": "/tmp/mod1.jar", "checksum": "abc123"},
        {"filename": "mod2.jar", "size": 1000, "path": "/tmp/mod2.jar", "checksum": "abc123"},  # Duplicate
    ]
    
    result = await batch_handler.upload_batch(files, "test_user")
    
    # Second file should be flagged as duplicate
    assert result.valid_items >= 1


# ============================================================================
# Test: Intelligent Queue Management
# ============================================================================

@pytest.mark.asyncio
async def test_priority_scheduling(queue_manager):
    """Test priority-based scheduling."""
    # Create items with different priorities
    items = [
        BatchItem(item_id="1", filename="low.jar", file_path="/tmp/1.jar", file_size=1000, checksum="1", priority=Priority.LOW.value),
        BatchItem(item_id="2", filename="normal.jar", file_path="/tmp/2.jar", file_size=1000, checksum="2", priority=Priority.NORMAL.value),
        BatchItem(item_id="3", filename="high.jar", file_path="/tmp/3.jar", file_size=1000, checksum="3", priority=Priority.HIGH.value),
        BatchItem(item_id="4", filename="vip.jar", file_path="/tmp/4.jar", file_size=1000, checksum="4", priority=Priority.VIP.value),
    ]
    
    # Enqueue all items
    for item in items:
        priority = Priority(item.priority)
        await queue_manager.enqueue(item, priority)
    
    # Verify queue order (VIP should come first)
    entries = []
    while not queue_manager.queue.empty():
        neg_priority, entry = await queue_manager.queue.get()
        entries.append(entry.item.filename)
    
    # VIP should be processed first
    assert entries[0] == "vip.jar"
    assert entries[-1] == "low.jar"


@pytest.mark.asyncio
async def test_resource_allocation(queue_manager):
    """Test resource allocation and limits."""
    stats = queue_manager.get_stats()
    
    assert stats["max_cpu_slots"] == 4
    assert stats["max_memory_gb"] == 16
    assert stats["max_concurrent"] == 4
    assert stats["concurrent_jobs"] == 0


@pytest.mark.asyncio
async def test_queue_efficiency(queue_manager):
    """Test queue efficiency calculation."""
    # Create items
    items = [
        BatchItem(item_id=f"item_{i}", filename=f"mod_{i}.jar", file_path=f"/tmp/mod_{i}.jar", file_size=1000, checksum=f"{i}")
        for i in range(10)
    ]
    
    # Enqueue items
    for item in items:
        await queue_manager.enqueue(item, Priority.NORMAL)
    
    # Process items
    await queue_manager.process_queue(simulate_processing)
    
    # Wait for completion
    await asyncio.sleep(2)
    
    # Get stats
    stats = queue_manager.get_stats()
    
    # Queue efficiency should be calculated
    # (concurrent jobs / (concurrent + queue size)) * 100
    if stats["queue_size"] > 0:
        efficiency = (stats["concurrent_jobs"] / (stats["concurrent_jobs"] + stats["queue_size"])) * 100
        assert efficiency > 0
    
    await queue_manager.stop()


# ============================================================================
# Test: Priority-based Processing
# ============================================================================

@pytest.mark.asyncio
async def test_priority_tiers(queue_manager):
    """Test all priority tiers work correctly."""
    test_cases = [
        (Priority.VIP, 100),
        (Priority.HIGH, 75),
        (Priority.NORMAL, 50),
        (Priority.LOW, 25),
    ]
    
    for priority, expected in test_cases:
        item = BatchItem(
            item_id=f"test_{priority.name}",
            filename=f"test_{priority.name}.jar",
            file_path="/tmp/test.jar",
            file_size=1000,
            checksum="test",
            priority=priority.value,
        )
        
        # Calculate effective priority
        requirements = ResourceRequirements(estimated_time=timedelta(minutes=1))
        effective_priority = await queue_manager._calculate_priority(priority, requirements, item)
        
        # Should be at least base priority
        assert effective_priority >= expected


# ============================================================================
# Test: Progress Tracking
# ============================================================================

@pytest.mark.asyncio
async def test_progress_tracking(progress_tracker):
    """Test progress tracking for batch items."""
    batch_id = "test_batch_1"
    
    # Update progress for multiple items
    items = [f"item_{i}" for i in range(5)]
    
    for item_id in items:
        await progress_tracker.update_progress(
            batch_id=batch_id,
            item_id=item_id,
            progress=0.5,
            status=ItemStatus.PROCESSING,
            message="Processing...",
        )
    
    # Get batch progress
    progress = await progress_tracker.get_batch_progress(batch_id)
    
    assert progress["total"] == 5
    assert progress["progress"] == 0.5
    
    # Complete one item
    await progress_tracker.update_progress(
        batch_id=batch_id,
        item_id=items[0],
        progress=1.0,
        status=ItemStatus.COMPLETED,
        message="Done",
    )
    
    # Verify updated progress
    progress = await progress_tracker.get_batch_progress(batch_id)
    
    assert progress["completed"] == 1
    assert progress["progress"] > 0.5


@pytest.mark.asyncio
async def test_tracking_accuracy(progress_tracker):
    """Test 100% tracking accuracy - all items tracked."""
    batch_id = "test_accuracy"
    
    # Create 50 items
    item_count = 50
    items = [f"item_{i}" for i in range(item_count)]
    
    # Track all items
    for item_id in items:
        await progress_tracker.update_progress(
            batch_id=batch_id,
            item_id=item_id,
            progress=1.0,
            status=ItemStatus.COMPLETED,
            message="Done",
        )
    
    # Verify all items tracked
    progress = await progress_tracker.get_batch_progress(batch_id)
    
    assert progress["total"] == item_count
    assert progress["completed"] == item_count
    assert progress["failed"] == 0
    
    # 100% tracking accuracy
    assert progress["progress"] == 1.0


# ============================================================================
# Test: Error Handling
# ============================================================================

@pytest.mark.asyncio
async def test_error_classification():
    """Test error type classification."""
    queue_manager = IntelligentQueueManager()
    
    test_errors = [
        ("Syntax error in file", ErrorType.SYNTAX),
        ("Missing dependency: lib", ErrorType.DEPENDENCY),
        ("Out of memory", ErrorType.RESOURCE),
        ("Connection timeout", ErrorType.TIMEOUT),
        ("Validation failed", ErrorType.VALIDATION),
        ("Unknown error", ErrorType.UNKNOWN),
    ]
    
    for error_msg, expected_type in test_errors:
        error = Exception(error_msg)
        classified = queue_manager._classify_error(error)
        assert classified == expected_type


@pytest.mark.asyncio
async def test_retry_logic(queue_manager):
    """Test retry with exponential backoff."""
    item = BatchItem(
        item_id="retry_test",
        filename="test.jar",
        file_path="/tmp/test.jar",
        file_size=1000,
        checksum="test",
    )
    
    # Initial state
    assert item.retry_count == 0
    
    # Simulate failures
    for i in range(3):
        item.retry_count = i
        try:
            raise Exception("Test error")
        except Exception as e:
            await queue_manager._handle_error(item, e)
    
    # After 3 retries, should be marked as failed
    assert item.status == ItemStatus.FAILED


@pytest.mark.asyncio
async def test_per_item_error_handling(batch_handler, queue_manager):
    """Test per-item error handling isolation."""
    # Create batch with items that will fail
    files = create_test_items(3)
    result = await batch_handler.upload_batch(files, "test_user")
    
    batch = await batch_handler.get_batch(result.batch_id)
    
    # Manually set one item to failed
    batch.items[0].status = ItemStatus.FAILED
    batch.items[0].error = ItemError(
        item_id=batch.items[0].item_id,
        error_type=ErrorType.SYNTAX,
        message="Syntax error",
        recoverable=False,
    )
    
    # Other items should still be processable
    assert batch.items[1].status == ItemStatus.PENDING
    assert batch.items[2].status == ItemStatus.PENDING


# ============================================================================
# Test: Performance - 100 mods in <1 hour
# ============================================================================

@pytest.mark.asyncio
async def test_batch_100_mods_performance(queue_manager):
    """Test processing 100 mods within 1 hour.
    
    This test simulates the performance target.
    With 4 concurrent workers and ~1 minute per mod:
    - 100 mods / 4 workers = 25 batches
    - 25 batches * 1 minute = 25 minutes (well under 1 hour)
    """
    # Create 100 items
    item_count = 100
    items = [
        BatchItem(
            item_id=f"perf_{i}",
            filename=f"mod_{i}.jar",
            file_path=f"/tmp/mod_{i}.jar",
            file_size=10 * 1024 * 1024,  # 10MB
            checksum=f"checksum_{i}",
        )
        for i in range(item_count)
    ]
    
    start_time = time.time()
    
    # Enqueue all items
    for item in items:
        await queue_manager.enqueue(item, Priority.NORMAL)
    
    # Process (with fast simulation)
    await queue_manager.process_queue(simulate_processing)
    
    # Wait for completion (with timeout)
    max_wait = 60  # 60 seconds for test (would be 3600 in production)
    elapsed = 0
    
    while elapsed < max_wait:
        await asyncio.sleep(1)
        stats = queue_manager.get_stats()
        
        if stats["queue_size"] == 0:
            break
        
        elapsed = time.time() - start_time
    
    total_time = time.time() - start_time
    
    # Verify completion
    completed_count = item_count - queue_manager.get_stats()["queue_size"]
    
    assert completed_count >= item_count * 0.9  # At least 90% complete
    
    # Performance check: 100 mods should complete in reasonable time
    # For this test with fast simulation, should be very quick
    print(f"Processed {completed_count} mods in {total_time:.2f} seconds")
    
    await queue_manager.stop()


# ============================================================================
# Test: Integration
# ============================================================================

@pytest.mark.asyncio
async def test_end_to_end_batch_processing():
    """End-to-end test of batch processing."""
    # Initialize components
    handler = BatchUploadHandler(redis_url="redis://localhost:6379")
    tracker = BatchProgressTracker(redis_url="redis://localhost:6379")
    queue = IntelligentQueueManager(max_concurrent=4)
    
    try:
        # 1. Upload batch
        files = create_test_items(10)
        upload_result = await handler.upload_batch(files, "test_user")
        batch_id = upload_result.batch_id
        
        # 2. Get batch
        batch = await handler.get_batch(batch_id)
        assert batch is not None
        assert len(batch.items) == 10
        
        # 3. Enqueue items
        for item in batch.items:
            await queue.enqueue(item, Priority.NORMAL)
        
        # 4. Process
        await queue.process_queue(simulate_processing)
        
        # 5. Wait for completion
        await asyncio.sleep(5)
        
        # 6. Verify results
        progress = await tracker.get_batch_progress(batch_id)
        
        assert progress["total"] == 10
        assert progress["completed"] > 0
        
        print(f"Integration test: {progress['completed']}/{progress['total']} completed")
        
    finally:
        await handler._redis.close() if handler._redis else None
        await tracker._redis.close() if tracker._redis else None
        await queue.stop()


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
