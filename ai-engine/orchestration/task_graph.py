"""
Task Graph implementation for managing agent dependencies and execution order.
Part of Phase 2: Core Orchestration Engine Implementation
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Set, Any, Optional, Callable
import logging
import time
from concurrent.futures import Future
import json

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Status of a task in the execution pipeline"""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskNode:
    """
    Represents a single task (agent execution) in the task graph
    """
    task_id: str
    agent_name: str
    agent_type: str
    input_data: Dict[str, Any]
    dependencies: Set[str] = field(default_factory=set)
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 1  # Higher number = higher priority
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    future: Optional[Future] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Dynamic spawning capability
    spawn_callback: Optional[Callable[[Any], List['TaskNode']]] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate task execution duration if completed"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    @property
    def is_ready(self) -> bool:
        """Check if task is ready to execute (all dependencies satisfied)"""
        return self.status == TaskStatus.READY
    
    @property
    def is_terminal(self) -> bool:
        """Check if task is in a terminal state"""
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
    
    def mark_started(self):
        """Mark task as started"""
        self.status = TaskStatus.RUNNING
        self.started_at = time.time()
        logger.debug(f"Task {self.task_id} ({self.agent_name}) started")
    
    def mark_completed(self, result: Any):
        """Mark task as completed with result"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = time.time()
        self.result = result
        duration_str = f"{self.duration:.2f}s" if self.duration is not None else "unknown duration"
        logger.info(f"Task {self.task_id} ({self.agent_name}) completed in {duration_str}")
    
    def mark_failed(self, error: str):
        """Mark task as failed with error"""
        self.status = TaskStatus.FAILED
        self.completed_at = time.time()
        self.error = error
        duration_str = f"{self.duration:.2f}s" if self.duration is not None else "unknown duration"
        logger.error(f"Task {self.task_id} ({self.agent_name}) failed after {duration_str}: {error}")
    
    def can_retry(self) -> bool:
        """Check if task can be retried"""
        return self.retry_count < self.max_retries and self.status == TaskStatus.FAILED
    
    def prepare_retry(self):
        """Prepare task for retry"""
        if not self.can_retry():
            raise ValueError(f"Task {self.task_id} cannot be retried")
        
        self.retry_count += 1
        self.status = TaskStatus.PENDING
        self.started_at = None
        self.completed_at = None
        self.error = None
        self.future = None
        logger.info(f"Task {self.task_id} prepared for retry {self.retry_count}/{self.max_retries}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for serialization"""
        return {
            'task_id': self.task_id,
            'agent_name': self.agent_name,
            'agent_type': self.agent_type,
            'status': self.status.value,
            'priority': self.priority,
            'dependencies': list(self.dependencies),
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'duration': self.duration,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'error': self.error
        }


class TaskGraph:
    """
    Directed Acyclic Graph (DAG) for managing task dependencies and execution order.
    Supports dynamic task spawning and parallel execution.
    """
    
    def __init__(self):
        self.nodes: Dict[str, TaskNode] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self._lock = None  # Will be set to appropriate lock type
        
    def add_task(self, task: TaskNode) -> bool:
        """
        Add a task to the graph
        
        Args:
            task: TaskNode to add
            
        Returns:
            True if task was added successfully, False if already exists
        """
        if task.task_id in self.nodes:
            logger.warning(f"Task {task.task_id} already exists in graph")
            return False
        
        self.nodes[task.task_id] = task
        logger.debug(f"Added task {task.task_id} ({task.agent_name}) to graph")
        return True
    
    def add_dependency(self, task_id: str, dependency_id: str) -> bool:
        """
        Add a dependency relationship between tasks
        
        Args:
            task_id: ID of task that depends on dependency_id
            dependency_id: ID of task that must complete first
            
        Returns:
            True if dependency was added, False if it would create a cycle
        """
        if task_id not in self.nodes or dependency_id not in self.nodes:
            logger.error(f"Cannot add dependency: task {task_id} or {dependency_id} not found")
            return False
        
        # Check for cycle before adding
        if self._would_create_cycle(task_id, dependency_id):
            logger.error(f"Adding dependency {dependency_id} -> {task_id} would create cycle")
            return False
        
        self.nodes[task_id].dependencies.add(dependency_id)
        logger.debug(f"Added dependency: {dependency_id} -> {task_id}")
        return True
    
    def _would_create_cycle(self, task_id: str, dependency_id: str) -> bool:
        """Check if adding a dependency would create a cycle"""
        # Simple DFS to detect cycle
        visited = set()
        
        def has_path(start: str, end: str) -> bool:
            if start == end:
                return True
            if start in visited:
                return False
            
            visited.add(start)
            for dep in self.nodes.get(start, TaskNode("", "", "", {})).dependencies:
                if has_path(dep, end):
                    return True
            return False
        
        return has_path(dependency_id, task_id)
    
    def get_ready_tasks(self) -> List[TaskNode]:
        """
        Get all tasks that are ready to execute (dependencies satisfied)
        
        Returns:
            List of TaskNode objects ready for execution, sorted by priority
        """
        ready_tasks = []
        
        for task in self.nodes.values():
            if task.status == TaskStatus.PENDING:
                # Check if all dependencies are completed
                if self._are_dependencies_satisfied(task):
                    task.status = TaskStatus.READY
                    ready_tasks.append(task)
        
        # Sort by priority (higher first), then by creation time
        ready_tasks.sort(key=lambda t: (-t.priority, t.created_at))
        return ready_tasks
    
    def _are_dependencies_satisfied(self, task: TaskNode) -> bool:
        """Check if all dependencies for a task are satisfied"""
        for dep_id in task.dependencies:
            dep_task = self.nodes.get(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        return True
    
    def mark_task_completed(self, task_id: str, result: Any) -> List[TaskNode]:
        """
        Mark a task as completed and handle dynamic spawning
        
        Args:
            task_id: ID of completed task
            result: Result from task execution
            
        Returns:
            List of newly spawned tasks (if any)
        """
        if task_id not in self.nodes:
            logger.error(f"Task {task_id} not found in graph")
            return []
        
        task = self.nodes[task_id]
        task.mark_completed(result)
        
        # Record execution history
        self.execution_history.append({
            'task_id': task_id,
            'agent_name': task.agent_name,
            'status': 'completed',
            'duration': task.duration,
            'timestamp': time.time()
        })
        
        # Handle dynamic spawning if callback is provided
        spawned_tasks = []
        if task.spawn_callback:
            try:
                new_tasks = task.spawn_callback(result)
                for new_task in new_tasks:
                    if self.add_task(new_task):
                        spawned_tasks.append(new_task)
                        logger.info(f"Dynamically spawned task {new_task.task_id} from {task_id}")
            except Exception as e:
                logger.error(f"Error in dynamic spawning for task {task_id}: {e}")
        
        return spawned_tasks
    
    def mark_task_failed(self, task_id: str, error: str) -> bool:
        """
        Mark a task as failed
        
        Args:
            task_id: ID of failed task
            error: Error message
            
        Returns:
            True if task can be retried, False otherwise
        """
        if task_id not in self.nodes:
            logger.error(f"Task {task_id} not found in graph")
            return False
        
        task = self.nodes[task_id]
        task.mark_failed(error)
        
        # Record execution history
        self.execution_history.append({
            'task_id': task_id,
            'agent_name': task.agent_name,
            'status': 'failed',
            'error': error,
            'timestamp': time.time()
        })
        
        return task.can_retry()
    
    def retry_task(self, task_id: str) -> bool:
        """
        Prepare a failed task for retry
        
        Args:
            task_id: ID of task to retry
            
        Returns:
            True if task was prepared for retry, False otherwise
        """
        if task_id not in self.nodes:
            logger.error(f"Task {task_id} not found in graph")
            return False
        
        task = self.nodes[task_id]
        if not task.can_retry():
            logger.warning(f"Task {task_id} cannot be retried")
            return False
        
        task.prepare_retry()
        return True
    
    def is_complete(self) -> bool:
        """Check if all tasks in the graph are completed"""
        return all(task.is_terminal for task in self.nodes.values())
    
    def has_failed_tasks(self) -> bool:
        """Check if any tasks have failed"""
        return any(
            task.status == TaskStatus.FAILED
            for task in self.nodes.values()
        )
    
    def has_permanently_failed_tasks(self) -> bool:
        """Check if any tasks have failed and cannot be retried"""
        return any(
            task.status == TaskStatus.FAILED and not task.can_retry() 
            for task in self.nodes.values()
        )
    
    def get_completion_stats(self) -> Dict[str, Any]:
        """Get completion statistics for the graph"""
        total_tasks = len(self.nodes)
        completed_tasks = sum(1 for task in self.nodes.values() if task.status == TaskStatus.COMPLETED)
        failed_tasks = sum(1 for task in self.nodes.values() if task.status == TaskStatus.FAILED)
        running_tasks = sum(1 for task in self.nodes.values() if task.status == TaskStatus.RUNNING)
        
        total_duration = sum(
            task.duration for task in self.nodes.values() 
            if task.duration is not None
        )
        
        return {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks,
            'running_tasks': running_tasks,
            'pending_tasks': total_tasks - completed_tasks - failed_tasks - running_tasks,
            'completion_rate': completed_tasks / total_tasks if total_tasks > 0 else 0,
            'total_duration': total_duration,
            'average_task_duration': total_duration / completed_tasks if completed_tasks > 0 else 0
        }
    
    def to_json(self) -> str:
        """Export graph structure to JSON"""
        graph_data = {
            'nodes': {task_id: task.to_dict() for task_id, task in self.nodes.items()},
            'execution_history': self.execution_history,
            'stats': self.get_completion_stats()
        }
        return json.dumps(graph_data, indent=2)
    
    def visualize_graph(self) -> str:
        """Create a simple text visualization of the graph"""
        lines = ["Task Graph Visualization:"]
        lines.append("=" * 50)
        
        for task in self.nodes.values():
            status_icon = {
                TaskStatus.PENDING: "⏳",
                TaskStatus.READY: "🟡", 
                TaskStatus.RUNNING: "🔄",
                TaskStatus.COMPLETED: "✅",
                TaskStatus.FAILED: "❌",
                TaskStatus.CANCELLED: "⏹️"
            }.get(task.status, "❓")
            
            deps_str = f" (deps: {', '.join(task.dependencies)})" if task.dependencies else ""
            duration_str = f" ({task.duration:.2f}s)" if task.duration is not None else ""
            
            lines.append(f"{status_icon} {task.task_id}: {task.agent_name}{deps_str}{duration_str}")
        
        return "\n".join(lines)