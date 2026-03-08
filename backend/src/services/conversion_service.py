"""
Conversion Service - AI Engine Integration

Handles the conversion workflow by:
1. Transferring mod files to AI Engine
2. Starting conversion jobs
3. Polling for progress updates
4. Broadcasting progress to WebSocket clients
5. Handling errors and propagating them to frontend
"""

import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, AsyncIterator
from datetime import datetime

import httpx

from services.ai_engine_client import (
    AIEngineClient,
    get_ai_engine_client,
    close_ai_engine_client,
    AIEngineError,
)
from services.cache import CacheService
from websocket.progress_handler import ProgressHandler, AgentStatus

logger = logging.getLogger(__name__)

# Configuration
AI_ENGINE_URL = os.getenv("AI_ENGINE_URL", "http://ai-engine:8001")
AI_ENGINE_TIMEOUT = httpx.Timeout(1800.0)  # 30 minutes
# Docker paths for shared volumes between backend and AI Engine
CONTAINER_TEMP_UPLOADS_DIR = "/app/temp_uploads"
CONTAINER_CONVERSION_OUTPUTS_DIR = "/app/conversion_outputs"
# Local paths (for development)
LOCAL_TEMP_UPLOADS_DIR = os.getenv("TEMP_UPLOADS_DIR", "temp_uploads")
LOCAL_CONVERSION_OUTPUTS_DIR = os.getenv("CONVERSION_OUTPUTS_DIR", "conversion_outputs")
POLL_INTERVAL = 2.0  # seconds between status polls


def _get_container_path(local_path: str, container_path: str) -> str:
    """
    Get the appropriate path based on whether we're in a container.

    Args:
        local_path: Local development path
        container_path: Container path (used in Docker)

    Returns:
        The appropriate path
    """
    # Check if we're in a container by looking for container-specific env
    if os.path.exists(container_path) or os.getenv("DOCKER_CONTAINER"):
        return container_path
    return local_path


class ConversionService:
    """
    Service for handling conversion workflow with AI Engine integration.

    This service:
    - Transfers mod files to AI Engine (via shared volume or HTTP)
    - Starts conversion jobs
    - Polls for progress updates
    - Broadcasts progress via WebSocket
    - Handles errors and propagates to frontend
    """

    def __init__(
        self,
        ai_engine_client: Optional[AIEngineClient] = None,
        cache_service: Optional[CacheService] = None,
    ):
        self.ai_client = ai_engine_client or get_ai_engine_client()
        self.cache = cache_service or CacheService()

    async def _transfer_file_to_ai_engine(
        self,
        file_path: str,
        conversion_id: str,
    ) -> str:
        """
        Transfer the mod file to AI Engine.

        In Docker, files are shared via volumes. We copy the file to the
        shared temp directory that AI Engine can access.

        Args:
            file_path: Source file path on backend
            conversion_id: Conversion job ID (used for directory naming)

        Returns:
            The path where AI Engine can access the file
        """
        # Determine the target directory based on environment
        target_dir = _get_container_path(
            os.path.join(LOCAL_TEMP_UPLOADS_DIR, conversion_id),
            f"{CONTAINER_TEMP_UPLOADS_DIR}/{conversion_id}",
        )

        # Ensure the target directory exists
        os.makedirs(target_dir, exist_ok=True)

        # Get the filename
        filename = os.path.basename(file_path)
        target_path = os.path.join(target_dir, filename)

        # Copy file to shared location (async file I/O would be better but this works)
        # Using shutil for reliability
        shutil.copy2(file_path, target_path)

        logger.info(f"Transferred file to {target_path} for AI Engine")

        return target_path

    async def process_conversion(
        self,
        conversion_id: str,
        file_path: str,
        original_filename: str,
        target_version: str,
        options: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process a conversion by sending it to the AI Engine.

        This method:
        1. Updates job status to processing
        2. Sends file to AI Engine
        3. Polls for status updates
        4. Broadcasts progress to WebSocket
        5. Returns the result or error

        Args:
            conversion_id: The conversion job ID
            file_path: Path to the mod file
            original_filename: Original filename for reference
            target_version: Target Minecraft version
            options: Conversion options

        Returns:
            Dict with conversion result (output_path, download_url, etc.)
        """
        job_id = conversion_id
        output_filename = f"{conversion_id}_converted.mcaddon"
        # Use appropriate paths based on environment (container vs local)
        output_dir = _get_container_path(
            LOCAL_CONVERSION_OUTPUTS_DIR, CONTAINER_CONVERSION_OUTPUTS_DIR
        )
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, output_filename)

        # Prepare conversion options
        conversion_options = {
            "target_version": target_version,
            "output_path": f"{_get_container_path(LOCAL_CONVERSION_OUTPUTS_DIR, CONTAINER_CONVERSION_OUTPUTS_DIR)}/{output_filename}",
            **options,
        }

        try:
            # Update status to processing
            await self._update_job_status(
                conversion_id=conversion_id,
                status="processing",
                progress=5,
                message="Starting conversion...",
            )

            # Broadcast start to WebSocket
            await ProgressHandler.broadcast_agent_start(
                conversion_id=conversion_id,
                agent="AIEngine",
                message="Starting AI Engine conversion...",
            )

            # Transfer file to AI Engine (via shared volume in Docker)
            logger.info(f"Transferring file to AI Engine for conversion {conversion_id}")
            try:
                ai_engine_mod_path = await self._transfer_file_to_ai_engine(
                    file_path=file_path,
                    conversion_id=conversion_id,
                )
                logger.info(f"File transferred to {ai_engine_mod_path}")
            except Exception as e:
                logger.error(f"Failed to transfer file to AI Engine: {e}")
                await self._handle_error(conversion_id, f"File transfer failed: {str(e)}")
                raise

            # Start conversion on AI Engine
            logger.info(f"Starting conversion {conversion_id} on AI Engine")

            try:
                response = await self.ai_client.start_conversion(
                    job_id=job_id,
                    mod_file_path=ai_engine_mod_path,
                    conversion_options=conversion_options,
                )

                logger.info(f"AI Engine started conversion: {response}")

            except AIEngineError as e:
                logger.error(f"AI Engine error starting conversion: {e}")
                await self._handle_error(conversion_id, str(e))
                raise
            except Exception as e:
                logger.error(f"Failed to start conversion: {e}")
                await self._handle_error(conversion_id, f"Failed to start conversion: {str(e)}")
                raise

            # Poll for status updates
            await self._poll_and_broadcast(conversion_id)

            # Get final status
            final_status = await self.ai_client.get_conversion_status(job_id)

            if final_status.get("status") == "completed":
                # Update final status
                await self._update_job_status(
                    conversion_id=conversion_id,
                    status="completed",
                    progress=100,
                    message="Conversion completed successfully",
                )

                # Broadcast completion
                download_url = f"/api/v1/conversions/{conversion_id}/download"
                await ProgressHandler.broadcast_conversion_complete(
                    conversion_id=conversion_id,
                    download_url=download_url,
                )

                return {
                    "status": "completed",
                    "output_path": output_path,
                    "download_url": download_url,
                    "message": "Conversion completed successfully",
                }
            else:
                error_msg = final_status.get("message", "Conversion failed")
                await self._handle_error(conversion_id, error_msg)
                return {
                    "status": "failed",
                    "error": error_msg,
                }

        except asyncio.CancelledError:
            logger.info(f"Conversion {conversion_id} was cancelled")
            await self._update_job_status(
                conversion_id=conversion_id,
                status="cancelled",
                progress=0,
                message="Conversion cancelled",
            )
            await ProgressHandler.broadcast_conversion_failed(
                conversion_id=conversion_id,
                error_message="Conversion was cancelled",
            )
            raise

        except Exception as e:
            logger.error(f"Conversion {conversion_id} failed: {e}")
            await self._handle_error(conversion_id, str(e))
            raise

    async def _poll_and_broadcast(self, conversion_id: str) -> None:
        """
        Poll AI Engine for status updates and broadcast to WebSocket.

        Args:
            conversion_id: The conversion job ID
        """
        try:
            async for status in self.ai_client.poll_conversion_status(
                conversion_id,
                poll_interval=POLL_INTERVAL,
            ):
                # Extract status info
                ai_status = status.get("status", "unknown")
                progress = status.get("progress", 0)
                message = status.get("message", "Processing...")
                current_stage = status.get("current_stage", "processing")

                # Map AI Engine status to our status
                if ai_status == "queued":
                    our_status = "queued"
                elif ai_status == "in_progress":
                    our_status = "processing"
                elif ai_status == "completed":
                    our_status = "completed"
                elif ai_status == "failed":
                    our_status = "failed"
                else:
                    our_status = "processing"

                # Update job status in cache
                await self._update_job_status(
                    conversion_id=conversion_id,
                    status=our_status,
                    progress=progress,
                    message=message,
                )

                # Map to agent status
                if our_status == "completed":
                    agent_status = AgentStatus.COMPLETED
                elif our_status == "failed":
                    agent_status = AgentStatus.FAILED
                else:
                    agent_status = AgentStatus.IN_PROGRESS

                # Broadcast progress update
                await ProgressHandler.broadcast_progress(
                    conversion_id=conversion_id,
                    agent="AIEngine",
                    status=agent_status,
                    progress=progress,
                    message=f"[{current_stage}] {message}",
                    details={"current_stage": current_stage},
                )

                logger.debug(f"Conversion {conversion_id} progress: {progress}% - {message}")

                # Stop polling on terminal states
                if ai_status in ("completed", "failed", "cancelled"):
                    break

        except AIEngineError as e:
            logger.error(f"Error polling AI Engine: {e}")
            await self._handle_error(conversion_id, f"Status check failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in poll loop: {e}")
            await self._handle_error(conversion_id, f"Status polling failed: {str(e)}")

    async def _update_job_status(
        self,
        conversion_id: str,
        status: str,
        progress: int,
        message: str,
    ) -> None:
        """
        Update job status in cache.

        Args:
            conversion_id: The conversion job ID
            status: New status
            progress: Progress percentage
            message: Status message
        """
        await self.cache.set_job_status(
            conversion_id,
            {
                "conversion_id": conversion_id,
                "status": status,
                "progress": progress,
                "message": message,
                "updated_at": datetime.utcnow().isoformat(),
            },
        )
        await self.cache.set_progress(conversion_id, progress)

    async def _handle_error(
        self,
        conversion_id: str,
        error_message: str,
    ) -> None:
        """
        Handle conversion error by updating status and broadcasting to WebSocket.

        Args:
            conversion_id: The conversion job ID
            error_message: Error message
        """
        await self._update_job_status(
            conversion_id=conversion_id,
            status="failed",
            progress=0,
            message=f"Error: {error_message}",
        )

        await ProgressHandler.broadcast_conversion_failed(
            conversion_id=conversion_id,
            error_message=error_message,
        )


# Global service instance
_conversion_service: Optional[ConversionService] = None


def get_conversion_service() -> ConversionService:
    """Get or create the global conversion service instance."""
    global _conversion_service
    if _conversion_service is None:
        _conversion_service = ConversionService()
    return _conversion_service


async def process_conversion_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Task handler for processing conversion jobs.

    This function is called by the task queue worker to process
    conversion jobs in the background.

    Args:
        payload: Task payload containing conversion details
            - conversion_id: The job ID
            - file_id: File identifier
            - file_path: Path to the mod file
            - original_filename: Original filename
            - target_version: Target Minecraft version
            - options: Conversion options

    Returns:
        Dict with conversion result
    """
    service = get_conversion_service()

    conversion_id = payload.get("conversion_id")
    file_path = payload.get("file_path")
    original_filename = payload.get("original_filename", "unknown")
    target_version = payload.get("target_version", "1.20.0")
    options = payload.get("options", {})

    logger.info(f"Processing conversion task: {conversion_id}")

    try:
        result = await service.process_conversion(
            conversion_id=conversion_id,
            file_path=file_path,
            original_filename=original_filename,
            target_version=target_version,
            options=options,
        )

        logger.info(f"Conversion task completed: {conversion_id}, status: {result.get('status')}")
        return result

    except Exception as e:
        logger.error(f"Conversion task failed: {conversion_id}, error: {e}")
        raise
