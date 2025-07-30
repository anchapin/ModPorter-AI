"""
Tests for the TaskGraph implementation
"""

import pytest
import time
from unittest.mock import Mock

from orchestration.task_graph import TaskGraph, TaskNode, TaskStatus


class TestTaskNode:
    """Test TaskNode functionality"""
    
    def test_task_node_creation(self):
        """Test basic TaskNode creation"""
        task = TaskNode(
            task_id="test_task",
            agent_name="test_agent",
            agent_type="analyzer",
            input_data={"key": "value"},
            priority=3
        )
        
        assert task.task_id == "test_task"
        assert task.agent_name == "test_agent"
        assert task.agent_type == "analyzer"
        assert task.input_data == {"key": "value"}
        assert task.priority == 3
        assert task.status == TaskStatus.PENDING
        assert not task.is_ready
        assert not task.is_terminal
        assert task.duration is None
    
    def test_task_execution_lifecycle(self):
        """Test task execution lifecycle"""
        task = TaskNode(
            task_id="lifecycle_test",
            agent_name="test_agent",
            agent_type="analyzer",
            input_data={}
        )
        
        # Mark as started
        task.mark_started()
        assert task.status == TaskStatus.RUNNING
        assert task.started_at is not None
        assert not task.is_terminal
        
        # Mark as completed
        result = {"output": "test result"}
        task.mark_completed(result)
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None
        assert task.result == result
        assert task.is_terminal
        assert task.duration is not None
        assert task.duration > 0
    
    def test_task_failure_and_retry(self):
        """Test task failure and retry logic"""
        task = TaskNode(
            task_id="retry_test",
            agent_name="test_agent",
            agent_type="analyzer",
            input_data={},
            max_retries=2
        )
        
        # Mark as failed
        task.mark_started()
        task.mark_failed("Test error")
        
        assert task.status == TaskStatus.FAILED
        assert task.error == "Test error"
        assert task.is_terminal
        assert task.can_retry()
        
        # Prepare for retry
        task.prepare_retry()
        assert task.status == TaskStatus.PENDING
        assert task.retry_count == 1
        assert task.error is None
        assert not task.is_terminal
    
    def test_task_serialization(self):
        """Test task dictionary conversion"""
        task = TaskNode(
            task_id="serialize_test",
            agent_name="test_agent",
            agent_type="analyzer",
            input_data={"test": "data"},
            dependencies={"dep1", "dep2"}
        )
        
        task_dict = task.to_dict()
        
        assert task_dict["task_id"] == "serialize_test"
        assert task_dict["agent_name"] == "test_agent"
        assert task_dict["status"] == "pending"
        assert sorted(task_dict["dependencies"]) == ["dep1", "dep2"]
        assert "created_at" in task_dict


class TestTaskGraph:
    """Test TaskGraph functionality"""
    
    def test_task_graph_creation(self):
        """Test basic TaskGraph creation"""
        graph = TaskGraph()
        assert len(graph.nodes) == 0
        assert graph.is_complete()
        assert not graph.has_failed_tasks()
    
    def test_add_tasks(self):
        """Test adding tasks to graph"""
        graph = TaskGraph()
        
        task1 = TaskNode("task1", "agent1", "type1", {})
        task2 = TaskNode("task2", "agent2", "type2", {})
        
        assert graph.add_task(task1)
        assert graph.add_task(task2)
        assert len(graph.nodes) == 2
        
        # Try to add duplicate
        assert not graph.add_task(task1)
        assert len(graph.nodes) == 2
    
    def test_dependencies(self):
        """Test dependency management"""
        graph = TaskGraph()
        
        task1 = TaskNode("task1", "agent1", "type1", {})
        task2 = TaskNode("task2", "agent2", "type2", {})
        task3 = TaskNode("task3", "agent3", "type3", {})
        
        graph.add_task(task1)
        graph.add_task(task2)
        graph.add_task(task3)
        
        # Add valid dependencies
        assert graph.add_dependency("task2", "task1")
        assert graph.add_dependency("task3", "task2")
        
        # Try to create cycle
        assert not graph.add_dependency("task1", "task3")
        
        assert "task1" in graph.nodes["task2"].dependencies
        assert "task2" in graph.nodes["task3"].dependencies
    
    def test_ready_tasks(self):
        """Test getting ready tasks"""
        graph = TaskGraph()
        
        task1 = TaskNode("task1", "agent1", "type1", {}, priority=5)
        task2 = TaskNode("task2", "agent2", "type2", {}, priority=3)
        task3 = TaskNode("task3", "agent3", "type3", {}, priority=4)
        
        graph.add_task(task1)
        graph.add_task(task2)
        graph.add_task(task3)
        
        graph.add_dependency("task2", "task1")
        graph.add_dependency("task3", "task1")
        
        # Initially, only task1 should be ready (no dependencies)
        ready_tasks = graph.get_ready_tasks()
        assert len(ready_tasks) == 1
        assert ready_tasks[0].task_id == "task1"
        
        # Complete task1, now task2 and task3 should be ready (sorted by priority)
        graph.mark_task_completed("task1", {"result": "done"})
        ready_tasks = graph.get_ready_tasks()
        assert len(ready_tasks) == 2
        assert ready_tasks[0].task_id == "task3"  # Higher priority (4)
        assert ready_tasks[1].task_id == "task2"  # Lower priority (3)
    
    def test_completion_tracking(self):
        """Test completion and failure tracking"""
        graph = TaskGraph()
        
        task1 = TaskNode("task1", "agent1", "type1", {})
        task2 = TaskNode("task2", "agent2", "type2", {})
        
        graph.add_task(task1)
        graph.add_task(task2)
        
        assert not graph.is_complete()
        assert not graph.has_failed_tasks()
        
        # Complete one task
        graph.mark_task_completed("task1", {"result": "success"})
        assert not graph.is_complete()
        
        # Fail the other task
        graph.mark_task_failed("task2", "Test failure")
        assert graph.is_complete()
        assert graph.has_failed_tasks()
    
    def test_dynamic_spawning(self):
        """Test dynamic task spawning"""
        graph = TaskGraph()
        
        def spawn_callback(result):
            """Spawn additional tasks based on result"""
            if result.get("spawn_tasks"):
                return [
                    TaskNode(f"spawned_{i}", f"agent_{i}", "spawned", {})
                    for i in range(2)
                ]
            return []
        
        task1 = TaskNode("task1", "agent1", "type1", {}, spawn_callback=spawn_callback)
        graph.add_task(task1)
        
        # Complete task with spawning
        result = {"spawn_tasks": True}
        spawned_tasks = graph.mark_task_completed("task1", result)
        
        assert len(spawned_tasks) == 2
        assert len(graph.nodes) == 3  # Original + 2 spawned
        assert "spawned_0" in graph.nodes
        assert "spawned_1" in graph.nodes
    
    def test_completion_stats(self):
        """Test completion statistics"""
        graph = TaskGraph()
        
        for i in range(5):
            task = TaskNode(f"task{i}", f"agent{i}", "type", {})
            graph.add_task(task)
        
        # Complete some tasks
        graph.mark_task_completed("task0", {"result": "done"})
        graph.mark_task_completed("task1", {"result": "done"})
        
        # Fail one task
        graph.mark_task_failed("task2", "Error")
        
        stats = graph.get_completion_stats()
        
        assert stats["total_tasks"] == 5
        assert stats["completed_tasks"] == 2
        assert stats["failed_tasks"] == 1
        assert stats["pending_tasks"] == 2
        assert stats["completion_rate"] == 0.4  # 2/5
    
    def test_graph_visualization(self):
        """Test graph visualization"""
        graph = TaskGraph()
        
        task1 = TaskNode("analyze", "java_analyzer", "analyzer", {})
        task2 = TaskNode("package", "packager", "packager", {})
        
        graph.add_task(task1)
        graph.add_task(task2)
        graph.add_dependency("package", "analyze")
        
        # Complete analyze task
        graph.mark_task_completed("analyze", {"result": "success"})
        
        visualization = graph.visualize_graph()
        
        assert "Task Graph Visualization" in visualization
        assert "✅ analyze: java_analyzer" in visualization
        assert "🟡 package: packager" in visualization or "⏳ package: packager" in visualization


class TestTaskGraphIntegration:
    """Integration tests for TaskGraph with complex scenarios"""
    
    def test_complex_workflow(self):
        """Test a complex workflow similar to the conversion pipeline"""
        graph = TaskGraph()
        
        # Create tasks similar to conversion workflow
        analyze_task = TaskNode("analyze", "java_analyzer", "analyzer", {}, priority=5)
        plan_task = TaskNode("plan", "bedrock_architect", "planner", {}, priority=4)
        translate_task = TaskNode("translate", "logic_translator", "translator", {}, priority=3)
        convert_assets_task = TaskNode("convert_assets", "asset_converter", "converter", {}, priority=3)
        package_task = TaskNode("package", "packaging_agent", "packager", {}, priority=2)
        validate_task = TaskNode("validate", "qa_validator", "validator", {}, priority=1)
        
        # Add tasks to graph
        for task in [analyze_task, plan_task, translate_task, convert_assets_task, package_task, validate_task]:
            graph.add_task(task)
        
        # Set up dependencies (similar to conversion pipeline)
        graph.add_dependency("plan", "analyze")
        graph.add_dependency("translate", "plan")
        graph.add_dependency("convert_assets", "plan")
        graph.add_dependency("package", "translate")
        graph.add_dependency("package", "convert_assets")
        graph.add_dependency("validate", "package")
        
        # Simulate execution
        execution_order = []
        
        while not graph.is_complete() and not graph.has_failed_tasks():
            ready_tasks = graph.get_ready_tasks()
            
            if not ready_tasks:
                break
            
            # Execute ready tasks (simulate)
            for task in ready_tasks:
                execution_order.append(task.task_id)
                graph.mark_task_completed(task.task_id, {"result": f"completed_{task.task_id}"})
        
        # Verify execution order makes sense
        assert execution_order[0] == "analyze"
        assert execution_order[1] == "plan"
        
        # translate and convert_assets can run in parallel after plan
        parallel_tasks = execution_order[2:4]
        assert "translate" in parallel_tasks
        assert "convert_assets" in parallel_tasks
        
        assert execution_order[4] == "package"
        assert execution_order[5] == "validate"
        
        # Verify completion
        assert graph.is_complete()
        assert not graph.has_failed_tasks()
        
        stats = graph.get_completion_stats()
        assert stats["completion_rate"] == 1.0
        assert stats["total_tasks"] == 6