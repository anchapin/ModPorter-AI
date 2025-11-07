"""
Worker Pool implementation for parallel agent execution.
Part of Phase 2: Core Orchestration Engine Implementation
"""

import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed, Future
from typing import Dict, List, Any, Optional, Callable, Union
import logging
import time
import threading
from dataclasses import dataclass
from enum import Enum
import queue
import signal
import sys

from .task_graph import TaskNode

logger = logging.getLogger(__name__)


class WorkerType(Enum):
    """Types of workers for different execution contexts"""
    THREAD = "thread"  # For I/O-bound tasks (LLM API calls)
    PROCESS = "process"  # For CPU-bound tasks (file processing)
    ASYNC = "async"  # For async I/O operations


@dataclass
class WorkerStats:
    """Statistics for worker performance tracking"""
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_execution_time: float = 0.0
    average_task_time: float = 0.0
    last_activity: Optional[float] = None
    
    def update_completion(self, execution_time: float):
        """Update stats after successful task completion"""
        self.tasks_completed += 1
        self.total_execution_time += execution_time
        self.average_task_time = self.total_execution_time / self.tasks_completed
        self.last_activity = time.time()
    
    def update_failure(self):
        """Update stats after task failure"""
        self.tasks_failed += 1
        self.last_activity = time.time()


class WorkerPool:
    """
    Manages a pool of workers for parallel task execution.
    Supports both thread-based (for I/O-bound LLM calls) and process-based (for CPU-bound work) execution.
    """
    
    def __init__(
        self,
        max_workers: Optional[int] = None,
        worker_type: WorkerType = WorkerType.THREAD,
        task_timeout: float = 300.0,  # 5 minutes default
        enable_monitoring: bool = True
    ):
        """
        Initialize the worker pool
        
        Args:
            max_workers: Maximum number of concurrent workers (None for auto-detect)
            worker_type: Type of workers to use
            task_timeout: Timeout for individual tasks in seconds
            enable_monitoring: Enable performance monitoring
        """
        self.worker_type = worker_type
        self.task_timeout = task_timeout
        self.enable_monitoring = enable_monitoring
        
        # Auto-detect max workers based on type
        if max_workers is None:
            if worker_type == WorkerType.PROCESS:
                max_workers = multiprocessing.cpu_count()
            else:
                max_workers = min(32, (multiprocessing.cpu_count() or 1) + 4)
        
        self.max_workers = max_workers
        self.executor: Optional[Union[ThreadPoolExecutor, ProcessPoolExecutor]] = None
        self.active_futures: Dict[str, Future] = {}
        self.worker_stats: Dict[int, WorkerStats] = {}
        self.task_queue = queue.PriorityQueue()
        self.shutdown_event = threading.Event()
        self.monitor_thread: Optional[threading.Thread] = None
        
        logger.info(f"Initialized WorkerPool with {max_workers} {worker_type.value} workers")
    
    def start(self):
        """Start the worker pool"""
        if self.executor is not None:
            logger.warning("WorkerPool already started")
            return
        
        try:
            if self.worker_type == WorkerType.PROCESS:
                self.executor = ProcessPoolExecutor(
                    max_workers=self.max_workers,
                    mp_context=multiprocessing.get_context('spawn')  # More reliable than fork
                )
            else:  # THREAD or ASYNC
                self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
            
            if self.enable_monitoring:
                self.monitor_thread = threading.Thread(target=self._monitor_workers, daemon=True)
                self.monitor_thread.start()
            
            logger.info(f"WorkerPool started with {self.max_workers} {self.worker_type.value} workers")
            
        except Exception as e:
            logger.error(f"Failed to start WorkerPool: {e}")
            raise
    
    def stop(self, wait: bool = True, timeout: float = 30.0):
        """
        Stop the worker pool
        
        Args:
            wait: Whether to wait for active tasks to complete
            timeout: Maximum time to wait for shutdown
        """
        if self.executor is None:
            return
        
        logger.info("Stopping WorkerPool...")
        self.shutdown_event.set()
        
        # Cancel active futures if not waiting
        if not wait:
            for task_id, future in self.active_futures.items():
                if not future.done():
                    future.cancel()
                    logger.debug(f"Cancelled task {task_id}")
        
        # Shutdown executor
        self.executor.shutdown(wait=wait, timeout=timeout)
        self.executor = None
        
        # Stop monitoring thread
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        
        logger.info("WorkerPool stopped")
    
    def submit_task(self, task: TaskNode, agent_executor: Callable) -> Future:
        """
        Submit a task for execution
        
        Args:
            task: TaskNode to execute
            agent_executor: Callable that executes the agent
            
        Returns:
            Future representing the task execution
        """
        if self.executor is None:
            raise RuntimeError("WorkerPool not started")
        
        if task.task_id in self.active_futures:
            logger.warning(f"Task {task.task_id} already submitted")
            return self.active_futures[task.task_id]
        
        # Create wrapper function for execution
        def execute_with_monitoring():
            start_time = time.time()
            worker_id = threading.get_ident()
            
            try:
                logger.debug(f"Worker {worker_id} starting task {task.task_id}")
                task.mark_started()
                
                # Execute the agent
                result = agent_executor(task)
                
                # Record stats
                execution_time = time.time() - start_time
                if self.enable_monitoring:
                    if worker_id not in self.worker_stats:
                        self.worker_stats[worker_id] = WorkerStats()
                    self.worker_stats[worker_id].update_completion(execution_time)
                
                logger.debug(f"Worker {worker_id} completed task {task.task_id} in {execution_time:.2f}s")
                return result
                
            except Exception as e:
                # Record failure stats
                if self.enable_monitoring and worker_id in self.worker_stats:
                    self.worker_stats[worker_id].update_failure()
                
                logger.error(f"Worker {worker_id} failed task {task.task_id}: {e}")
                raise
        
        # Submit task with timeout
        future = self.executor.submit(execute_with_monitoring)
        self.active_futures[task.task_id] = future
        
        logger.debug(f"Submitted task {task.task_id} to worker pool")
        return future
    
    def wait_for_completion(
        self, 
        tasks: List[TaskNode], 
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Wait for a set of tasks to complete
        
        Args:
            tasks: List of TaskNode objects to wait for
            timeout: Maximum time to wait (None for no timeout)
            
        Returns:
            Dictionary with completion results
        """
        if not tasks:
            return {'completed': [], 'failed': [], 'timeout': []}
        
        # Get futures for the tasks
        task_futures = {}
        for task in tasks:
            if task.task_id in self.active_futures:
                task_futures[task.task_id] = self.active_futures[task.task_id]
        
        completed_tasks = []
        failed_tasks = []
        timeout_tasks = []
        
        start_time = time.time()
        
        try:
            # Wait for completion with timeout
            for future in as_completed(task_futures.values(), timeout=timeout):
                elapsed_time = time.time() - start_time
                remaining_timeout = timeout - elapsed_time if timeout else None
                
                # Find which task this future belongs to
                task_id = None
                for tid, fut in task_futures.items():
                    if fut == future:
                        task_id = tid
                        break
                
                if task_id is None:
                    continue
                
                try:
                    result = future.result(timeout=remaining_timeout)
                    completed_tasks.append({'task_id': task_id, 'result': result})
                    logger.debug(f"Task {task_id} completed successfully")
                    
                except Exception as e:
                    failed_tasks.append({'task_id': task_id, 'error': str(e)})
                    logger.error(f"Task {task_id} failed: {e}")
                
                # Clean up future reference
                if task_id in self.active_futures:
                    del self.active_futures[task_id]
        
        except TimeoutError:
            # Handle timeout - identify which tasks didn't complete
            for task_id, future in task_futures.items():
                if not future.done():
                    timeout_tasks.append(task_id)
                    future.cancel()
                    logger.warning(f"Task {task_id} timed out after {timeout}s")
        
        return {
            'completed': completed_tasks,
            'failed': failed_tasks, 
            'timeout': timeout_tasks,
            'total_time': time.time() - start_time
        }
    
    def get_active_task_count(self) -> int:
        """Get the number of currently active tasks"""
        return len([f for f in self.active_futures.values() if not f.done()])
    
    def get_worker_stats(self) -> Dict[str, Any]:
        """Get worker pool statistics"""
        active_workers = len([f for f in self.active_futures.values() if not f.done()])
        total_completed = sum(stats.tasks_completed for stats in self.worker_stats.values())
        total_failed = sum(stats.tasks_failed for stats in self.worker_stats.values())
        
        avg_task_time = 0.0
        if self.worker_stats:
            total_time = sum(stats.total_execution_time for stats in self.worker_stats.values())
            if total_completed > 0:
                avg_task_time = total_time / total_completed
        
        return {
            'worker_type': self.worker_type.value,
            'max_workers': self.max_workers,
            'active_workers': active_workers,
            'active_tasks': len(self.active_futures),
            'total_completed': total_completed,
            'total_failed': total_failed,
            'success_rate': total_completed / (total_completed + total_failed) if (total_completed + total_failed) > 0 else 0,
            'average_task_time': avg_task_time,
            'worker_details': {
                worker_id: {
                    'tasks_completed': stats.tasks_completed,
                    'tasks_failed': stats.tasks_failed,
                    'average_time': stats.average_task_time,
                    'last_activity': stats.last_activity
                }
                for worker_id, stats in self.worker_stats.items()
            }
        }
    
    def _monitor_workers(self):
        """Background thread for monitoring worker health"""
        logger.debug("Worker monitoring thread started")
        
        while not self.shutdown_event.wait(timeout=30.0):  # Check every 30 seconds
            try:
                stats = self.get_worker_stats()
                
                # Log periodic stats
                logger.info(f"WorkerPool stats: {stats['active_workers']}/{stats['max_workers']} workers active, "
                          f"{stats['total_completed']} completed, {stats['total_failed']} failed, "
                          f"{stats['success_rate']:.2%} success rate")
                
                # Check for stuck tasks (running longer than 2x timeout)
                time.time()
                self.task_timeout * 2
                
                stuck_tasks = []
                for task_id, future in list(self.active_futures.items()):
                    if not future.done():
                        # This is a simplified check - in practice you'd track start times
                        # For now, just log active tasks
                        continue
                
                if stuck_tasks:
                    logger.warning(f"Found {len(stuck_tasks)} potentially stuck tasks")
                
            except Exception as e:
                logger.error(f"Error in worker monitoring: {e}")
        
        logger.debug("Worker monitoring thread stopped")
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()


# Utility functions for agent execution
def create_agent_executor(agent_instance, tools_mapping: Optional[Dict[str, Any]] = None):
    """
    Create an executor function for running an agent in the worker pool
    
    Args:
        agent_instance: The agent instance to execute
        tools_mapping: Optional mapping of tools for the agent
        
    Returns:
        Callable that can be used with WorkerPool.submit_task
    """
    def executor(task: TaskNode) -> Any:
        """Execute the agent with the given task"""
        try:
            # Set up the agent context
            if hasattr(agent_instance, 'set_input_data'):
                agent_instance.set_input_data(task.input_data)
            
            # Execute based on agent type
            if hasattr(agent_instance, 'run'):
                result = agent_instance.run(task.input_data)
            elif hasattr(agent_instance, 'execute'):
                result = agent_instance.execute(task.input_data)
            elif callable(agent_instance):
                result = agent_instance(task.input_data)
            else:
                raise ValueError(f"Don't know how to execute agent {agent_instance}")
            
            return result
            
        except Exception as e:
            logger.error(f"Agent execution failed for task {task.task_id}: {e}")
            raise
    
    return executor


def setup_signal_handlers(worker_pool: WorkerPool):
    """Set up signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down worker pool...")
        worker_pool.stop(wait=True, timeout=30.0)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)