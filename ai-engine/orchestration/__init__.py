"""
Enhanced Multi-Agent Orchestration System

This module provides parallel execution and dynamic spawning capabilities
for the ModPorter AI conversion pipeline, as outlined in Issue #156.
"""

from .task_graph import TaskGraph, TaskNode, TaskStatus
from .orchestrator import ParallelOrchestrator
from .worker_pool import WorkerPool
from .strategy_selector import OrchestrationStrategy, StrategySelector

__all__ = [
    'TaskGraph',
    'TaskNode', 
    'TaskStatus',
    'ParallelOrchestrator',
    'WorkerPool',
    'OrchestrationStrategy',
    'StrategySelector'
]