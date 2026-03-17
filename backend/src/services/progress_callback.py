"""
Progress Callback System

WebSocket-based progress updates from AI Engine to backend to frontend.
"""

import logging
<<<<<<< HEAD
=======
import json
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
from typing import Optional, Set, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ProgressCallback:
    """Progress callback handler for conversion jobs."""
<<<<<<< HEAD

    def __init__(self):
        self._subscribers: Dict[str, Set] = {}  # job_id -> set of callbacks
        self._progress_history: Dict[str, list] = {}  # job_id -> list of progress updates

    def subscribe(self, job_id: str, callback):
        """
        Subscribe to progress updates for a job.

=======
    
    def __init__(self):
        self._subscribers: Dict[str, Set] = {}  # job_id -> set of callbacks
        self._progress_history: Dict[str, list] = {}  # job_id -> list of progress updates
    
    def subscribe(self, job_id: str, callback):
        """
        Subscribe to progress updates for a job.
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        Args:
            job_id: Job ID
            callback: Async callback function(progress_data)
        """
        if job_id not in self._subscribers:
            self._subscribers[job_id] = set()
            self._progress_history[job_id] = []
<<<<<<< HEAD

        self._subscribers[job_id].add(callback)
        logger.debug(f"Subscriber added for job {job_id}")

    def unsubscribe(self, job_id: str, callback):
        """
        Unsubscribe from progress updates.

=======
        
        self._subscribers[job_id].add(callback)
        logger.debug(f"Subscriber added for job {job_id}")
    
    def unsubscribe(self, job_id: str, callback):
        """
        Unsubscribe from progress updates.
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        Args:
            job_id: Job ID
            callback: Callback function to remove
        """
        if job_id in self._subscribers:
            self._subscribers[job_id].discard(callback)
            if not self._subscribers[job_id]:
                del self._subscribers[job_id]
            logger.debug(f"Subscriber removed for job {job_id}")
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    async def update_progress(
        self,
        job_id: str,
        progress: int,
        current_stage: str,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Send progress update to all subscribers.
<<<<<<< HEAD

=======
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        Args:
            job_id: Job ID
            progress: Progress percentage (0-100)
            current_stage: Current stage name
            message: Optional status message
            metadata: Optional additional metadata
        """
        progress_data = {
            "job_id": job_id,
            "progress": progress,
            "current_stage": current_stage,
            "message": message or "",
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
<<<<<<< HEAD

        # Store in history
        if job_id in self._progress_history:
            self._progress_history[job_id].append(progress_data)

=======
        
        # Store in history
        if job_id in self._progress_history:
            self._progress_history[job_id].append(progress_data)
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        # Notify subscribers
        if job_id in self._subscribers:
            for callback in self._subscribers[job_id].copy():
                try:
                    await callback(progress_data)
                except Exception as e:
                    logger.error(f"Progress callback failed: {e}")
<<<<<<< HEAD

        logger.debug(f"Progress update for {job_id}: {progress}% - {current_stage}")

    def get_progress_history(self, job_id: str) -> list:
        """Get progress history for a job."""
        return self._progress_history.get(job_id, [])

=======
        
        logger.debug(f"Progress update for {job_id}: {progress}% - {current_stage}")
    
    def get_progress_history(self, job_id: str) -> list:
        """Get progress history for a job."""
        return self._progress_history.get(job_id, [])
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def cleanup_job(self, job_id: str):
        """Clean up job data after completion."""
        if job_id in self._subscribers:
            del self._subscribers[job_id]
        if job_id in self._progress_history:
            del self._progress_history[job_id]
        logger.debug(f"Cleaned up job {job_id}")


# Singleton instance
_progress_callback = None


def get_progress_callback() -> ProgressCallback:
    """Get or create progress callback singleton."""
    global _progress_callback
    if _progress_callback is None:
        _progress_callback = ProgressCallback()
    return _progress_callback


# Conversion stage constants
class ConversionStages:
    """Conversion stage names."""
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    QUEUED = "queued"
    ANALYZING = "analyzing"
    TRANSLATING = "translating"
    VALIDATING = "validating"
    PACKAGING = "packaging"
    COMPLETED = "completed"
    FAILED = "failed"


# Progress percentages for each stage
STAGE_PROGRESS = {
    ConversionStages.QUEUED: 0,
    ConversionStages.ANALYZING: 10,
    ConversionStages.TRANSLATING: 40,
    ConversionStages.VALIDATING: 80,
    ConversionStages.PACKAGING: 90,
    ConversionStages.COMPLETED: 100,
    ConversionStages.FAILED: -1,
}
