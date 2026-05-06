"""
Enhanced Multi-Agent Orchestration System

This module provides parallel execution and dynamic spawning capabilities
for the PortKit conversion pipeline, as outlined in Issue #156.
"""

from .orchestrator import ParallelOrchestrator
from .strategy_selector import OrchestrationStrategy, StrategySelector
from .task_graph import TaskGraph, TaskNode, TaskStatus
from .worker_pool import WorkerPool
from .langgraph_pipeline import (
    ConversionPipeline,
    ConversionState,
    LangGraphOrchestrator,
    NodeStatus,
    NodeResult,
    create_checkpointer,
    BlockConversionInput,
    EntityConversionInput,
    RecipeConversionInput,
    AssetConversionInput,
    BlockConversionOutput,
    EntityConversionOutput,
)
from .run_agent import (
    RunAgent,
    RunAgentPlan,
    Step,
    StepContext,
    StepStatus as RunAgentStepStatus,
    Constraint,
    StepResult,
)
from .run_agent_integration import RunAgentOrchestrator, RunAgentCrewBridge

__all__ = [
    # Legacy orchestration components
    "TaskGraph",
    "TaskNode",
    "TaskStatus",
    "ParallelOrchestrator",
    "WorkerPool",
    "OrchestrationStrategy",
    "StrategySelector",
    # LangGraph-based pipeline (migration from CrewAI per issue #1201)
    "ConversionPipeline",
    "ConversionState",
    "LangGraphOrchestrator",
    "NodeStatus",
    "NodeResult",
    "create_checkpointer",
    # PydanticAI input/output schemas for typed node calls
    "BlockConversionInput",
    "EntityConversionInput",
    "RecipeConversionInput",
    "AssetConversionInput",
    "BlockConversionOutput",
    "EntityConversionOutput",
    # RunAgent components
    "RunAgent",
    "RunAgentPlan",
    "Step",
    "StepContext",
    "StepResult",
    "Constraint",
    "RunAgentStepStatus",
    "RunAgentOrchestrator",
    "RunAgentCrewBridge",
]
