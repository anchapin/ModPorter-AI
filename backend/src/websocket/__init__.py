"""
WebSocket support for real-time conversion progress updates.

This module provides WebSocket connection management and progress broadcasting
for conversion jobs.
"""

from .manager import ConnectionManager
from .progress_handler import ProgressHandler, progress_message

__all__ = ["ConnectionManager", "ProgressHandler", "progress_message"]
