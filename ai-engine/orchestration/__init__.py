"""
Enhanced Multi-Agent Orchestration System

This module provides parallel execution and dynamic spawning capabilities
for the PortKit conversion pipeline, as outlined in Issue #156.
"""

from .orchestrator import ParallelOrchestrator
from .strategy_selector import OrchestrationStrategy, StrategySelector
from .task_graph import TaskGraph, TaskNode, TaskStatus
from .worker_pool import WorkerPool

__all__ = [
    "TaskGraph",
    "TaskNode",
    "TaskStatus",
    "ParallelOrchestrator",
    "WorkerPool",
    "OrchestrationStrategy",
    "StrategySelector",
]
