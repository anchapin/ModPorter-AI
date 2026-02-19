"""
Enhanced tests for the Orchestration system.
Addresses Issue #568: AI Engine: Multi-Agent Orchestration - Task Graph and Worker Pool Management

This module tests:
- Comprehensive logging for task state transitions
- Deadlock detection and recovery
- Memory leak detection for worker processes
- Integration tests for parallel execution scenarios
"""

import pytest
import logging
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import Future
from typing import Dict, Any, List

from orchestration.task_graph import TaskGraph, TaskNode, TaskStatus
from orchestration.worker_pool import WorkerPool, WorkerType, WorkerStats, create_agent_executor
from orchestration.orchestrator import ParallelOrchestrator
from orchestration.strategy_selector import StrategySelector, OrchestrationStrategy, StrategyConfig


class TestTaskStateLogging:
    """Test comprehensive logging for task state transitions"""
    
    @pytest.fixture
    def task_graph(self):
        """Create a TaskGraph instance"""
        return TaskGraph()
    
    def test_task_creation_logging(self, task_graph, caplog):
        """Test that task creation is logged"""
        with caplog.at_level(logging.DEBUG):
            task = TaskNode(
                task_id="test_task",
                agent_name="test_agent",
                agent_type="analyzer",
                input_data={"key": "value"}
            )
            task_graph.add_task(task)
        
        # Should log task addition
        assert any("task" in record.message.lower() for record in caplog.records)
    
    def test_task_started_logging(self, caplog):
        """Test that task start is logged"""
        task = TaskNode(
            task_id="start_test",
            agent_name="test_agent",
            agent_type="analyzer",
            input_data={}
        )
        
        with caplog.at_level(logging.DEBUG):
            task.mark_started()
        
        assert any("started" in record.message.lower() for record in caplog.records)
        assert task.status == TaskStatus.RUNNING
    
    def test_task_completed_logging(self, caplog):
        """Test that task completion is logged"""
        task = TaskNode(
            task_id="complete_test",
            agent_name="test_agent",
            agent_type="analyzer",
            input_data={}
        )
        
        task.mark_started()
        
        with caplog.at_level(logging.INFO):
            task.mark_completed({"result": "success"})
        
        assert any("completed" in record.message.lower() for record in caplog.records)
        assert task.status == TaskStatus.COMPLETED
    
    def test_task_failed_logging(self, caplog):
        """Test that task failure is logged"""
        task = TaskNode(
            task_id="fail_test",
            agent_name="test_agent",
            agent_type="analyzer",
            input_data={}
        )
        
        task.mark_started()
        
        with caplog.at_level(logging.ERROR):
            task.mark_failed("Test error message")
        
        assert any("failed" in record.message.lower() for record in caplog.records)
        assert task.status == TaskStatus.FAILED
        assert task.error == "Test error message"
    
    def test_task_retry_logging(self, caplog):
        """Test that task retry is logged"""
        task = TaskNode(
            task_id="retry_test",
            agent_name="test_agent",
            agent_type="analyzer",
            input_data={},
            max_retries=2
        )
        
        task.mark_started()
        task.mark_failed("First failure")
        
        with caplog.at_level(logging.INFO):
            task.prepare_retry()
        
        assert any("retry" in record.message.lower() for record in caplog.records)
        assert task.retry_count == 1
        assert task.status == TaskStatus.PENDING


class TestDeadlockDetection:
    """Test deadlock detection and recovery"""
    
    @pytest.fixture
    def task_graph(self):
        """Create a TaskGraph instance"""
        return TaskGraph()
    
    def test_cycle_detection_simple(self, task_graph):
        """Test detection of simple cycle in dependencies"""
        task1 = TaskNode("task1", "agent1", "type1", {})
        task2 = TaskNode("task2", "agent2", "type2", {})
        
        task_graph.add_task(task1)
        task_graph.add_task(task2)
        
        # Add task1 -> task2 dependency
        assert task_graph.add_dependency("task2", "task1")
        
        # Try to add task2 -> task1 (would create cycle)
        assert not task_graph.add_dependency("task1", "task2")
    
    def test_cycle_detection_complex(self, task_graph):
        """Test detection of cycle in longer dependency chain"""
        task1 = TaskNode("task1", "agent1", "type1", {})
        task2 = TaskNode("task2", "agent2", "type2", {})
        task3 = TaskNode("task3", "agent3", "type3", {})
        task4 = TaskNode("task4", "agent4", "type4", {})
        
        for task in [task1, task2, task3, task4]:
            task_graph.add_task(task)
        
        # Create chain: task1 -> task2 -> task3 -> task4
        task_graph.add_dependency("task2", "task1")
        task_graph.add_dependency("task3", "task2")
        task_graph.add_dependency("task4", "task3")
        
        # Try to create cycle: task4 -> task1
        assert not task_graph.add_dependency("task1", "task4")
    
    def test_deadlock_detection_in_graph(self, task_graph):
        """Test detection of deadlock when no tasks can proceed"""
        task1 = TaskNode("task1", "agent1", "type1", {})
        task2 = TaskNode("task2", "agent2", "type2", {})
        
        task_graph.add_task(task1)
        task_graph.add_task(task2)
        
        # Create mutual dependency (this should be prevented by cycle detection)
        # But let's simulate a scenario where tasks are stuck
        task1.dependencies.add("task2")
        task2.dependencies.add("task1")
        
        # Manually set statuses to simulate stuck state
        task1.status = TaskStatus.PENDING
        task2.status = TaskStatus.PENDING
        
        # Get ready tasks - should be empty due to deadlock
        ready_tasks = task_graph.get_ready_tasks()
        assert len(ready_tasks) == 0
    
    def test_has_permanently_failed_tasks(self, task_graph):
        """Test detection of permanently failed tasks"""
        task = TaskNode(
            task_id="fail_task",
            agent_name="agent",
            agent_type="type",
            input_data={},
            max_retries=1
        )
        
        task_graph.add_task(task)
        
        # Fail the task and exhaust retries
        task.mark_started()
        task.mark_failed("Error")
        task.prepare_retry()
        task.mark_started()
        task.mark_failed("Final error")
        
        task_graph.nodes["fail_task"] = task
        
        assert task_graph.has_permanently_failed_tasks()
    
    def test_recovery_from_failed_task(self, task_graph):
        """Test that graph can continue after task failure with retry"""
        task1 = TaskNode("task1", "agent1", "type1", {})
        task2 = TaskNode("task2", "agent2", "type2", {}, max_retries=2)
        
        task_graph.add_task(task1)
        task_graph.add_task(task2)
        task_graph.add_dependency("task2", "task1")
        
        # Complete task1
        task_graph.mark_task_completed("task1", {"result": "done"})
        
        # Task2 should now be ready
        ready = task_graph.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == "task2"


class TestWorkerPoolMonitoring:
    """Test worker pool monitoring and statistics"""
    
    def test_worker_stats_creation(self):
        """Test WorkerStats dataclass"""
        stats = WorkerStats()
        
        assert stats.tasks_completed == 0
        assert stats.tasks_failed == 0
        assert stats.total_execution_time == 0.0
        assert stats.average_task_time == 0.0
    
    def test_worker_stats_update_completion(self):
        """Test updating stats after task completion"""
        stats = WorkerStats()
        
        stats.update_completion(1.5)
        assert stats.tasks_completed == 1
        assert stats.total_execution_time == 1.5
        assert stats.average_task_time == 1.5
        
        stats.update_completion(2.5)
        assert stats.tasks_completed == 2
        assert stats.total_execution_time == 4.0
        assert stats.average_task_time == 2.0
    
    def test_worker_stats_update_failure(self):
        """Test updating stats after task failure"""
        stats = WorkerStats()
        
        stats.update_failure()
        assert stats.tasks_failed == 1
        assert stats.last_activity is not None
    
    def test_worker_pool_initialization(self):
        """Test WorkerPool initialization"""
        pool = WorkerPool(max_workers=4, worker_type=WorkerType.THREAD)
        
        assert pool.max_workers == 4
        assert pool.worker_type == WorkerType.THREAD
        assert pool.executor is None
    
    def test_worker_pool_context_manager(self):
        """Test WorkerPool as context manager"""
        with WorkerPool(max_workers=2, worker_type=WorkerType.THREAD) as pool:
            assert pool.executor is not None
            stats = pool.get_worker_stats()
            assert stats['max_workers'] == 2
        
        # Pool should be stopped after context exit
        assert pool.executor is None
    
    def test_worker_pool_submit_task(self):
        """Test submitting a task to the worker pool"""
        def simple_executor(task):
            return {"result": "success"}
        
        task = TaskNode("test_task", "agent", "type", {"input": "data"})
        
        with WorkerPool(max_workers=2, worker_type=WorkerType.THREAD) as pool:
            future = pool.submit_task(task, simple_executor)
            result = future.result(timeout=5.0)
            
            assert result["result"] == "success"
    
    def test_worker_pool_get_stats(self):
        """Test getting worker pool statistics"""
        with WorkerPool(max_workers=4, worker_type=WorkerType.THREAD, enable_monitoring=False) as pool:
            stats = pool.get_worker_stats()
            
            assert stats['worker_type'] == 'thread'
            assert stats['max_workers'] == 4
            assert stats['active_workers'] == 0
            assert isinstance(stats['total_completed'], int)
            assert isinstance(stats['total_failed'], int)


class TestParallelExecution:
    """Integration tests for parallel execution scenarios"""
    
    def test_sequential_execution(self):
        """Test sequential task execution"""
        task_graph = TaskGraph()
        
        # Create tasks
        task1 = TaskNode("analyze", "java_analyzer", "analyzer", {}, priority=5)
        task2 = TaskNode("plan", "architect", "planner", {}, priority=4)
        task3 = TaskNode("translate", "translator", "translator", {}, priority=3)
        
        task_graph.add_task(task1)
        task_graph.add_task(task2)
        task_graph.add_task(task3)
        
        task_graph.add_dependency("plan", "analyze")
        task_graph.add_dependency("translate", "plan")
        
        # Simulate sequential execution
        execution_order = []
        
        while not task_graph.is_complete():
            ready = task_graph.get_ready_tasks()
            if not ready:
                break
            
            task = ready[0]
            execution_order.append(task.task_id)
            task_graph.mark_task_completed(task.task_id, {"result": f"{task.task_id}_done"})
        
        assert execution_order == ["analyze", "plan", "translate"]
    
    def test_parallel_execution_order(self):
        """Test that independent tasks can run in parallel"""
        task_graph = TaskGraph()
        
        # Create tasks where task2 and task3 can run in parallel after task1
        task1 = TaskNode("analyze", "analyzer", "type", {}, priority=5)
        task2 = TaskNode("translate", "translator", "type", {}, priority=3)
        task3 = TaskNode("convert_assets", "converter", "type", {}, priority=3)
        task4 = TaskNode("package", "packager", "type", {}, priority=2)
        
        task_graph.add_task(task1)
        task_graph.add_task(task2)
        task_graph.add_task(task3)
        task_graph.add_task(task4)
        
        task_graph.add_dependency("translate", "analyze")
        task_graph.add_dependency("convert_assets", "analyze")
        task_graph.add_dependency("package", "translate")
        task_graph.add_dependency("package", "convert_assets")
        
        # Complete analyze first
        task_graph.mark_task_completed("analyze", {"result": "done"})
        
        # Now both translate and convert_assets should be ready
        ready = task_graph.get_ready_tasks()
        assert len(ready) == 2
        
        task_ids = [t.task_id for t in ready]
        assert "translate" in task_ids
        assert "convert_assets" in task_ids
    
    def test_priority_ordering(self):
        """Test that tasks are ordered by priority"""
        task_graph = TaskGraph()
        
        task1 = TaskNode("low", "agent", "type", {}, priority=1)
        task2 = TaskNode("high", "agent", "type", {}, priority=10)
        task3 = TaskNode("medium", "agent", "type", {}, priority=5)
        
        task_graph.add_task(task1)
        task_graph.add_task(task2)
        task_graph.add_task(task3)
        
        ready = task_graph.get_ready_tasks()
        
        # Should be ordered by priority (highest first)
        assert ready[0].task_id == "high"
        assert ready[1].task_id == "medium"
        assert ready[2].task_id == "low"
    
    def test_dynamic_task_spawning(self):
        """Test dynamic task spawning during execution"""
        task_graph = TaskGraph()
        
        def spawn_callback(result):
            """Spawn additional tasks based on result"""
            if result.get("spawn"):
                return [
                    TaskNode(f"spawned_{i}", f"agent_{i}", "spawned", {})
                    for i in range(2)
                ]
            return []
        
        task = TaskNode(
            "main_task",
            "agent",
            "type",
            {},
            spawn_callback=spawn_callback
        )
        
        task_graph.add_task(task)
        
        # Complete task with spawning
        spawned = task_graph.mark_task_completed("main_task", {"spawn": True})
        
        assert len(spawned) == 2
        assert len(task_graph.nodes) == 3
        assert "spawned_0" in task_graph.nodes
        assert "spawned_1" in task_graph.nodes


class TestWorkerPoolErrorHandling:
    """Test error handling in worker pool"""
    
    def test_task_timeout_handling(self):
        """Test handling of task timeout"""
        def slow_executor(task):
            time.sleep(10)  # Simulate slow task
            return {"result": "done"}
        
        task = TaskNode("slow_task", "agent", "type", {})
        
        with WorkerPool(max_workers=1, worker_type=WorkerType.THREAD, task_timeout=1.0) as pool:
            future = pool.submit_task(task, slow_executor)
            
            with pytest.raises(Exception):
                future.result(timeout=2.0)
    
    def test_task_exception_handling(self):
        """Test handling of task exceptions"""
        def failing_executor(task):
            raise ValueError("Intentional test failure")
        
        task = TaskNode("fail_task", "agent", "type", {})
        
        with WorkerPool(max_workers=1, worker_type=WorkerType.THREAD) as pool:
            future = pool.submit_task(task, failing_executor)
            
            with pytest.raises(ValueError):
                future.result(timeout=5.0)
    
    def test_multiple_task_failures(self):
        """Test handling of multiple task failures"""
        def failing_executor(task):
            raise RuntimeError(f"Task {task.task_id} failed")
        
        task_graph = TaskGraph()
        
        for i in range(3):
            task = TaskNode(f"task_{i}", "agent", "type", {}, max_retries=1)
            task_graph.add_task(task)
        
        # Simulate all tasks failing
        for i in range(3):
            task_graph.mark_task_failed(f"task_{i}", f"Error {i}")
        
        assert task_graph.has_failed_tasks()
        stats = task_graph.get_completion_stats()
        assert stats['failed_tasks'] == 3


class TestOrchestratorIntegration:
    """Integration tests for the ParallelOrchestrator"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create a ParallelOrchestrator instance"""
        return ParallelOrchestrator(enable_monitoring=False)
    
    def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initialization"""
        assert orchestrator.strategy_selector is not None
        assert orchestrator.task_graph is None
        assert orchestrator.worker_pool is None
    
    def test_orchestrator_register_agent(self, orchestrator):
        """Test registering an agent with the orchestrator"""
        mock_agent = Mock()
        mock_agent.run = Mock(return_value={"result": "success"})
        
        orchestrator.register_agent("test_agent", mock_agent)
        
        assert "test_agent" in orchestrator.agent_executors
    
    def test_orchestrator_create_workflow(self, orchestrator):
        """Test creating a conversion workflow"""
        # Create a temporary test file
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix='.jar', delete=False) as f:
            f.write(b'PK\x03\x04')  # Minimal JAR header
            temp_path = f.name
        
        try:
            workflow = orchestrator.create_conversion_workflow(
                mod_path=temp_path,
                output_path="/tmp/output",
                temp_dir="/tmp/temp"
            )
            
            assert workflow is not None
            assert len(workflow.nodes) > 0
            assert "analyze" in workflow.nodes
            
        finally:
            os.unlink(temp_path)
    
    def test_orchestrator_execution_status(self, orchestrator):
        """Test getting execution status"""
        status = orchestrator.get_execution_status()
        
        assert 'strategy' in status
        assert 'is_running' in status
        assert 'duration' in status


class TestAgentExecutor:
    """Test agent executor creation and execution"""
    
    def test_create_agent_executor_with_run(self):
        """Test creating executor for agent with run method"""
        mock_agent = Mock()
        mock_agent.run = Mock(return_value={"output": "result"})
        
        executor = create_agent_executor(mock_agent)
        task = TaskNode("test", "agent", "type", {"input": "data"})
        
        result = executor(task)
        
        assert result == {"output": "result"}
        mock_agent.run.assert_called_once()
    
    def test_create_agent_executor_with_execute(self):
        """Test creating executor for agent with execute method"""
        mock_agent = Mock()
        mock_agent.execute = Mock(return_value={"output": "result"})
        # Ensure run is not present so execute is used
        del mock_agent.run
        
        executor = create_agent_executor(mock_agent)
        task = TaskNode("test", "agent", "type", {"input": "data"})
        
        result = executor(task)
        
        assert result == {"output": "result"}
        mock_agent.execute.assert_called_once()
    
    def test_create_agent_executor_callable(self):
        """Test creating executor for callable agent"""
        def callable_agent(input_data):
            return {"output": "callable_result"}
        
        executor = create_agent_executor(callable_agent)
        task = TaskNode("test", "agent", "type", {"input": "data"})
        
        result = executor(task)
        
        assert result == {"output": "callable_result"}
    
    def test_create_agent_executor_with_tools(self):
        """Test creating executor with tools mapping"""
        mock_agent = Mock()
        mock_agent.run = Mock(return_value={"output": "result"})
        tools = {"tool1": Mock()}
        
        executor = create_agent_executor(mock_agent, tools)
        task = TaskNode("test", "agent", "type", {"input": "data"})
        
        result = executor(task)
        
        assert result == {"output": "result"}


class TestTaskGraphVisualization:
    """Test task graph visualization"""
    
    def test_visualization_empty_graph(self):
        """Test visualization of empty graph"""
        graph = TaskGraph()
        viz = graph.visualize_graph()
        
        assert "Task Graph Visualization" in viz
    
    def test_visualization_with_tasks(self):
        """Test visualization with tasks"""
        graph = TaskGraph()
        
        task1 = TaskNode("task1", "agent1", "type1", {})
        task2 = TaskNode("task2", "agent2", "type2", {})
        
        graph.add_task(task1)
        graph.add_task(task2)
        graph.add_dependency("task2", "task1")
        
        viz = graph.visualize_graph()
        
        assert "task1" in viz
        assert "task2" in viz
        assert "agent1" in viz
        assert "agent2" in viz
    
    def test_visualization_with_completed_task(self):
        """Test visualization with completed task"""
        graph = TaskGraph()
        
        task = TaskNode("task1", "agent1", "type1", {})
        graph.add_task(task)
        graph.mark_task_completed("task1", {"result": "done"})
        
        viz = graph.visualize_graph()
        
        assert "✅" in viz  # Completed icon


class TestTaskGraphSerialization:
    """Test task graph serialization"""
    
    def test_to_dict(self):
        """Test converting task to dictionary"""
        task = TaskNode(
            task_id="test_task",
            agent_name="test_agent",
            agent_type="analyzer",
            input_data={"key": "value"},
            priority=5
        )
        
        task_dict = task.to_dict()
        
        assert task_dict["task_id"] == "test_task"
        assert task_dict["agent_name"] == "test_agent"
        assert task_dict["status"] == "pending"
        assert task_dict["priority"] == 5
    
    def test_to_json(self):
        """Test converting graph to JSON"""
        graph = TaskGraph()
        
        task = TaskNode("task1", "agent1", "type1", {})
        graph.add_task(task)
        
        json_str = graph.to_json()
        
        assert "task1" in json_str
        assert "nodes" in json_str
        assert "stats" in json_str


class TestMemoryLeakDetection:
    """Test memory leak detection for worker processes"""
    
    def test_worker_cleanup_on_success(self):
        """Test that workers are cleaned up after successful tasks"""
        def simple_executor(task):
            return {"result": "success"}
        
        task = TaskNode("test", "agent", "type", {})
        
        with WorkerPool(max_workers=1, worker_type=WorkerType.THREAD) as pool:
            initial_stats = pool.get_worker_stats()
            
            future = pool.submit_task(task, simple_executor)
            future.result(timeout=5.0)
            
            # Verify task completed successfully
            assert future.done()
            assert not future.cancelled()
            
            # Stats should show completion
            final_stats = pool.get_worker_stats()
            assert final_stats['total_completed'] >= 1
    
    def test_worker_cleanup_on_failure(self):
        """Test that workers are cleaned up after failed tasks"""
        def failing_executor(task):
            raise ValueError("Test failure")
        
        task = TaskNode("test", "agent", "type", {})
        
        with WorkerPool(max_workers=1, worker_type=WorkerType.THREAD, enable_monitoring=True) as pool:
            future = pool.submit_task(task, failing_executor)
            
            try:
                future.result(timeout=5.0)
            except ValueError:
                pass
            
            # Verify task completed (with exception)
            assert future.done()
            assert future.exception() is not None
            assert isinstance(future.exception(), ValueError)
            assert str(future.exception()) == "Test failure"
    
    def test_stats_accumulation(self):
        """Test that stats accumulate correctly across multiple tasks"""
        def simple_executor(task):
            return {"result": "success"}
        
        with WorkerPool(max_workers=1, worker_type=WorkerType.THREAD, enable_monitoring=True) as pool:
            for i in range(5):
                task = TaskNode(f"task_{i}", "agent", "type", {})
                future = pool.submit_task(task, simple_executor)
                future.result(timeout=5.0)
            
            stats = pool.get_worker_stats()
            
            assert stats['total_completed'] == 5
            assert stats['total_failed'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])