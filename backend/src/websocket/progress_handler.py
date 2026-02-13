"""
Progress message handler for WebSocket broadcasts.

This module defines the message schema and helper functions for
sending agent progress updates through WebSocket connections.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum

from .manager import manager

logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    """Status of an agent during conversion."""

    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ProgressMessageData(BaseModel):
    """Data payload for an agent progress update."""

    agent: str = Field(..., description="Name of the agent (e.g., 'JavaAnalyzerAgent')")
    status: AgentStatus = Field(..., description="Current status of the agent")
    progress: int = Field(
        ...,
        ge=0,
        le=100,
        description="Progress percentage (0-100)",
    )
    message: str = Field(..., description="Human-readable progress message")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="ISO 8601 timestamp of the progress update",
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional details about the progress"
    )


class ProgressMessage(BaseModel):
    """WebSocket message format for agent progress updates."""

    type: str = Field(default="agent_progress", description="Message type identifier")
    data: ProgressMessageData = Field(..., description="Progress update data")


def progress_message(
    agent: str,
    status: AgentStatus,
    progress: int,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> ProgressMessage:
    """
    Create a progress message for WebSocket broadcast.

    Args:
        agent: Name of the agent
        status: Current agent status
        progress: Progress percentage (0-100)
        message: Human-readable progress message
        details: Optional additional details

    Returns:
        ProgressMessage ready for broadcast
    """
    return ProgressMessage(
        data=ProgressMessageData(
            agent=agent,
            status=status,
            progress=progress,
            message=message,
            details=details,
        )
    )


class ProgressHandler:
    """
    Handler for broadcasting progress updates to WebSocket clients.

    This class provides a high-level interface for sending progress updates
    during the conversion workflow.
    """

    @staticmethod
    async def broadcast_progress(
        conversion_id: str,
        agent: str,
        status: AgentStatus,
        progress: int,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Broadcast a progress update to all connected clients for a conversion.

        Args:
            conversion_id: UUID of the conversion job
            agent: Name of the agent
            status: Current agent status
            progress: Progress percentage (0-100)
            message: Human-readable progress message
            details: Optional additional details
        """
        msg = progress_message(agent, status, progress, message, details)

        try:
            await manager.broadcast(msg.model_dump(), conversion_id)
            logger.debug(
                f"Progress broadcast for {conversion_id}: {agent} - {progress}% - {message}"
            )
        except Exception as e:
            logger.error(f"Failed to broadcast progress for {conversion_id}: {e}")

    @staticmethod
    async def broadcast_agent_start(
        conversion_id: str, agent: str, message: Optional[str] = None
    ):
        """
        Broadcast that an agent has started processing.

        Args:
            conversion_id: UUID of the conversion job
            agent: Name of the agent
            message: Optional custom message
        """
        await ProgressHandler.broadcast_progress(
            conversion_id=conversion_id,
            agent=agent,
            status=AgentStatus.IN_PROGRESS,
            progress=0,
            message=message or f"{agent} started processing",
        )

    @staticmethod
    async def broadcast_agent_update(
        conversion_id: str,
        agent: str,
        progress: int,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Broadcast an agent progress update.

        Args:
            conversion_id: UUID of the conversion job
            agent: Name of the agent
            progress: Progress percentage (0-100)
            message: Human-readable progress message
            details: Optional additional details
        """
        await ProgressHandler.broadcast_progress(
            conversion_id=conversion_id,
            agent=agent,
            status=AgentStatus.IN_PROGRESS,
            progress=progress,
            message=message,
            details=details,
        )

    @staticmethod
    async def broadcast_agent_complete(
        conversion_id: str, agent: str, message: Optional[str] = None
    ):
        """
        Broadcast that an agent has completed processing.

        Args:
            conversion_id: UUID of the conversion job
            agent: Name of the agent
            message: Optional custom message
        """
        await ProgressHandler.broadcast_progress(
            conversion_id=conversion_id,
            agent=agent,
            status=AgentStatus.COMPLETED,
            progress=100,
            message=message or f"{agent} completed successfully",
        )

    @staticmethod
    async def broadcast_agent_failed(
        conversion_id: str, agent: str, error_message: str
    ):
        """
        Broadcast that an agent has failed.

        Args:
            conversion_id: UUID of the conversion job
            agent: Name of the agent
            error_message: Error message describing the failure
        """
        await ProgressHandler.broadcast_progress(
            conversion_id=conversion_id,
            agent=agent,
            status=AgentStatus.FAILED,
            progress=0,
            message=f"{agent} failed: {error_message}",
            details={"error": error_message},
        )

    @staticmethod
    async def broadcast_conversion_complete(
        conversion_id: str, download_url: str
    ):
        """
        Broadcast that the entire conversion has completed.

        Args:
            conversion_id: UUID of the conversion job
            download_url: URL to download the converted add-on
        """
        msg = ProgressMessage(
            type="conversion_complete",
            data=ProgressMessageData(
                agent="ConversionWorkflow",
                status=AgentStatus.COMPLETED,
                progress=100,
                message="Conversion completed successfully",
                details={"download_url": download_url},
            ),
        )

        try:
            await manager.broadcast(msg.model_dump(), conversion_id)
            logger.info(f"Conversion complete broadcast for {conversion_id}")
        except Exception as e:
            logger.error(f"Failed to broadcast conversion complete for {conversion_id}: {e}")

    @staticmethod
    async def broadcast_conversion_failed(conversion_id: str, error_message: str):
        """
        Broadcast that the entire conversion has failed.

        Args:
            conversion_id: UUID of the conversion job
            error_message: Error message describing the failure
        """
        msg = ProgressMessage(
            type="conversion_failed",
            data=ProgressMessageData(
                agent="ConversionWorkflow",
                status=AgentStatus.FAILED,
                progress=0,
                message=f"Conversion failed: {error_message}",
                details={"error": error_message},
            ),
        )

        try:
            await manager.broadcast(msg.model_dump(), conversion_id)
            logger.error(f"Conversion failed broadcast for {conversion_id}")
        except Exception as e:
            logger.error(f"Failed to broadcast conversion failed for {conversion_id}: {e}")
