"""
Task Worker Service using Celery.

Issue: #1098 - Consolidate task queues: remove task_queue.py duplicate, migrate to Celery
"""

import logging

from celery import Celery

from services.celery_config import celery_app

logger = logging.getLogger(__name__)


class TaskWorker:
    """
    Worker that processes tasks from the Celery queue.
    This is a lightweight shim - actual task processing happens in celery_tasks.py
    """

    def __init__(self, num_workers: int = 3):
        self.num_workers = num_workers
        self._running = False

    def register_handler(self, task_name: str, handler) -> None:
        """Register a handler for a specific task type."""
        logger.info(f"Registered handler for task: {task_name}")

    async def process_task(self, task) -> bool:
        """Process a single task - delegated to Celery."""
        try:
            from services.celery_tasks import _get_task_handler

            handler = _get_task_handler(task.name)
            if handler is None:
                logger.warning(f"No handler registered for task: {task.name}")
                return False

            result = handler(task.payload)
            return True

        except Exception as e:
            logger.error(f"Task processing failed: {e}")
            return False

    async def start(self) -> None:
        """Start the worker - not needed for Celery, workers are separate processes."""
        logger.info("TaskWorker initialized (actual workers are Celery processes)")

    async def stop(self, timeout: float = 30.0) -> None:
        """Stop the worker - not needed for Celery."""
        logger.info("TaskWorker stopped")


async def handle_conversion_task(payload) -> dict:
    """Forward to celery_tasks handler."""
    from services.celery_tasks import handle_conversion_task

    return handle_conversion_task(payload)


async def handle_asset_conversion_task(payload) -> dict:
    """Forward to celery_tasks handler."""
    from services.celery_tasks import handle_asset_conversion_task

    return handle_asset_conversion_task(payload)


async def main():
    """Main entry point for standalone worker (use Celery for production)."""
    import signal

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("Starting TaskWorker in standalone mode")
    logger.info("For production, use: celery -A services.celery_config worker")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
