"""
Progress callback system for AI Engine to send real-time updates to backend.

This module provides a callback-based progress reporting system that allows
the AI Engine to send progress updates via Redis, which the backend can
subscribe to via WebSocket connections.

This addresses GitHub Issues:
- #401: Complete Crew orchestration for full conversion pipeline
- #399: Wire AI Engine to Backend API for full conversion pipeline
"""

import logging
import os
import json
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timezone
import asyncio

logger = logging.getLogger(__name__)

# Try to import Redis, but make it optional
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, progress callbacks will be disabled")


class ProgressCallback:
    """
    Callback handler for sending progress updates from AI Engine to backend.
    
    This class provides a way for the conversion crew to report progress
    that can be received by the backend via Redis pub/sub or polling.
    """
    
    def __init__(self, job_id: str, redis_url: Optional[str] = None):
        """
        Initialize progress callback for a specific job.
        
        Args:
            job_id: The conversion job ID
            redis_url: Optional Redis URL (defaults to env var REDIS_URL)
        """
        self.job_id = job_id
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = None
        self._connected = False
        
    async def connect(self) -> bool:
        """Connect to Redis"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, progress callbacks disabled")
            return False
            
        try:
            self.redis_client = aioredis.from_url(
                self.redis_url, 
                decode_responses=True
            )
            await self.redis_client.ping()
            self._connected = True
            logger.info(f"Progress callback connected to Redis for job {self.job_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to Redis for progress callbacks: {e}")
            self._connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            self._connected = False
    
    async def send_progress(
        self,
        agent: str,
        status: str,
        progress: int,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Send a progress update.
        
        Args:
            agent: Name of the agent (e.g., 'JavaAnalyzerAgent')
            status: Current status (queued, in_progress, completed, failed)
            progress: Progress percentage (0-100)
            message: Human-readable message
            details: Optional additional details
        """
        if not self._connected or not self.redis_client:
            logger.debug(f"Progress update skipped (not connected): {agent} - {progress}%")
            return
            
        try:
            progress_data = {
                "job_id": self.job_id,
                "agent": agent,
                "status": status,
                "progress": progress,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": details or {}
            }
            
            # Store in Redis with expiration (1 hour)
            key = f"ai_engine:progress:{self.job_id}"
            await self.redis_client.set(
                key,
                json.dumps(progress_data),
                ex=3600
            )
            
            # Also publish to channel for real-time updates
            channel = f"ai_engine:progress:{self.job_id}"
            await self.redis_client.publish(channel, json.dumps(progress_data))
            
            logger.debug(f"Progress update sent: {agent} - {progress}% - {message}")
            
        except Exception as e:
            logger.error(f"Failed to send progress update: {e}")
    
    async def broadcast_agent_start(self, agent: str, message: Optional[str] = None):
        """Broadcast that an agent has started"""
        await self.send_progress(
            agent=agent,
            status="in_progress",
            progress=0,
            message=message or f"{agent} started processing"
        )
    
    async def broadcast_agent_update(
        self, 
        agent: str, 
        progress: int, 
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Broadcast an agent progress update"""
        await self.send_progress(
            agent=agent,
            status="in_progress",
            progress=progress,
            message=message,
            details=details
        )
    
    async def broadcast_agent_complete(self, agent: str, message: Optional[str] = None):
        """Broadcast that an agent has completed"""
        await self.send_progress(
            agent=agent,
            status="completed",
            progress=100,
            message=message or f"{agent} completed successfully"
        )
    
    async def broadcast_agent_failed(self, agent: str, error_message: str):
        """Broadcast that an agent has failed"""
        await self.send_progress(
            agent=agent,
            status="failed",
            progress=0,
            message=f"{agent} failed: {error_message}",
            details={"error": error_message}
        )
    
    async def broadcast_conversion_complete(self, download_url: Optional[str] = None):
        """Broadcast that the entire conversion has completed"""
        await self.send_progress(
            agent="ConversionWorkflow",
            status="completed",
            progress=100,
            message="Conversion completed successfully",
            details={"download_url": download_url} if download_url else {}
        )
    
    async def broadcast_conversion_failed(self, error_message: str):
        """Broadcast that the conversion has failed"""
        await self.send_progress(
            agent="ConversionWorkflow",
            status="failed",
            progress=0,
            message=f"Conversion failed: {error_message}",
            details={"error": error_message}
        )


class ProgressCallbackManager:
    """
    Manager for multiple progress callbacks.
    
    Provides a centralized way to manage progress callbacks for
    multiple concurrent conversion jobs.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize the progress callback manager.
        
        Args:
            redis_url: Optional Redis URL
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self._callbacks: Dict[str, ProgressCallback] = {}
        self._lock = asyncio.Lock()
    
    async def get_callback(self, job_id: str) -> ProgressCallback:
        """
        Get or create a progress callback for a job.
        
        Args:
            job_id: The conversion job ID
            
        Returns:
            ProgressCallback instance for the job
        """
        async with self._lock:
            if job_id not in self._callbacks:
                callback = ProgressCallback(job_id, self.redis_url)
                await callback.connect()
                self._callbacks[job_id] = callback
            
            return self._callbacks[job_id]
    
    async def remove_callback(self, job_id: str):
        """
        Remove and cleanup a progress callback.
        
        Args:
            job_id: The conversion job ID
        """
        async with self._lock:
            if job_id in self._callbacks:
                await self._callbacks[job_id].disconnect()
                del self._callbacks[job_id]
    
    async def cleanup_all(self):
        """Clean up all callbacks"""
        async with self._lock:
            for callback in self._callbacks.values():
                await callback.disconnect()
            self._callbacks.clear()


# Global progress callback manager
_progress_manager: Optional[ProgressCallbackManager] = None


def get_progress_manager() -> ProgressCallbackManager:
    """Get the global progress callback manager"""
    global _progress_manager
    if _progress_manager is None:
        _progress_manager = ProgressCallbackManager()
    return _progress_manager


async def create_progress_callback(job_id: str) -> ProgressCallback:
    """
    Create a new progress callback for a job.
    
    This is the main entry point for creating progress callbacks
    in the AI Engine conversion process.
    
    Args:
        job_id: The conversion job ID
        
    Returns:
        ProgressCallback instance
    """
    manager = get_progress_manager()
    return await manager.get_callback(job_id)


async def cleanup_progress_callback(job_id: str):
    """
    Clean up a progress callback when a job completes.
    
    Args:
        job_id: The conversion job ID
    """
    manager = get_progress_manager()
    await manager.remove_callback(job_id)
