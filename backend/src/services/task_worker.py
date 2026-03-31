"""
Task Worker Service
Worker process that consumes tasks from the async task queue.

Issue: #379 - Implement async task queue (Phase 3)
"""

import asyncio
import logging
from typing import Dict, Any, Callable

from services.task_queue import AsyncTaskQueue, get_task_queue, Task

logger = logging.getLogger(__name__)


class TaskWorker:
    """
    Worker that processes tasks from the async task queue.
    Supports concurrent processing and graceful shutdown.
    """

    def __init__(self, queue: AsyncTaskQueue, num_workers: int = 3, poll_interval: float = 1.0):
        self.queue = queue
        self.num_workers = num_workers
        self.poll_interval = poll_interval
        self._running = False
        self._workers: list[asyncio.Task] = []
        self._task_handlers: Dict[str, Callable] = {}

    def register_handler(self, task_name: str, handler: Callable) -> None:
        """Register a handler for a specific task type"""
        self._task_handlers[task_name] = handler
        logger.info(f"Registered handler for task: {task_name}")

    async def process_task(self, task: Task) -> bool:
        """Process a single task"""
        try:
            handler = self._task_handlers.get(task.name)

            if handler is None:
                logger.warning(f"No handler registered for task: {task.name}")
                await self.queue.fail(
                    task.id, f"No handler for task type: {task.name}", retry=False
                )
                return False

            # Execute the handler
            result = await handler(task.payload)

            # Mark as complete
            await self.queue.complete(task.id, result)
            return True

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Task {task.id} failed: {error_msg}")

            # Let the queue handle retry logic
            await self.queue.fail(task.id, error_msg, retry=True)
            return False

    async def worker_loop(self, worker_id: int) -> None:
        """Worker loop that processes tasks"""
        logger.info(f"Worker {worker_id} started")

        while self._running:
            try:
                # Get next task from queue
                task = await self.queue.dequeue()

                if task is None:
                    # No task available, wait before polling again
                    await asyncio.sleep(self.poll_interval)
                    continue

                logger.info(f"Worker {worker_id} processing task {task.id} ({task.name})")

                # Process the task
                await self.process_task(task)

            except asyncio.CancelledError:
                logger.info(f"Worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)  # Brief pause before retrying

        logger.info(f"Worker {worker_id} stopped")

    async def start(self) -> None:
        """Start the worker processes"""
        self._running = True

        # Create worker tasks
        for i in range(self.num_workers):
            worker = asyncio.create_task(self.worker_loop(i))
            self._workers.append(worker)

        logger.info(f"Started {self.num_workers} worker(s)")

    async def stop(self, timeout: float = 30.0) -> None:
        """Stop the worker processes gracefully"""
        logger.info("Stopping workers...")
        self._running = False

        # Cancel all worker tasks
        for worker in self._workers:
            worker.cancel()

        # Wait for workers to finish
        if self._workers:
            await asyncio.wait_for(
                asyncio.gather(*self._workers, return_exceptions=True), timeout=timeout
            )

        self._workers.clear()
        logger.info("All workers stopped")


# Example task handlers
async def handle_conversion_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Example handler for conversion tasks"""
    job_id = payload.get("job_id")
    file_id = payload.get("file_id")

    logger.info(f"Processing conversion job: {job_id}")

    # Simulate work
    await asyncio.sleep(5)

    return {
        "job_id": job_id,
        "status": "completed",
        "result_url": f"/api/v1/conversions/{job_id}/download",
    }


async def handle_asset_conversion_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Example handler for asset conversion tasks"""
    asset_id = payload.get("asset_id")

    logger.info(f"Processing asset conversion: {asset_id}")

    # Simulate work
    await asyncio.sleep(2)

    return {"asset_id": asset_id, "status": "converted"}


# Main worker entry point
async def main():
    """Main entry point for the worker"""
    import signal

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create queue
    queue = await get_task_queue()

    # Create worker
    worker = TaskWorker(queue, num_workers=3)

    # Register handlers
    worker.register_handler("conversion", handle_conversion_task)
    worker.register_handler("asset_conversion", handle_asset_conversion_task)

    # Handle shutdown signals properly
    shutdown_event = asyncio.Event()

    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        shutdown_event.set()

    # Register signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        try:
            loop.add_signal_handler(sig, lambda s=sig: signal_handler(s, None))
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass

    # Start worker
    await worker.start()

    try:
        # Keep running until shutdown signal
        await shutdown_event.wait()
        logger.info("Shutdown signal received")
    except KeyboardInterrupt:
        logger.info("Interrupted by keyboard")
    finally:
        await worker.stop(timeout=30.0)


if __name__ == "__main__":
    asyncio.run(main())
