"""
Unit tests for TaskGraph and TaskNode.
"""

import pytest
import time
import json
from unittest.mock import patch
from orchestration.task_graph import TaskGraph, TaskNode, TaskStatus

class TestTaskNode:
    def test_task_duration(self):
        node = TaskNode("t1", "agent", "type", {})
        assert node.duration is None
        
        node.mark_started()
        time.sleep(0.01)
        node.mark_completed("result")
        assert node.duration > 0

    def test_terminal_states(self):
        node = TaskNode("t", "a", "t", {})
        assert not node.is_terminal
        
        node.status = TaskStatus.COMPLETED
        assert node.is_terminal
        
        node.status = TaskStatus.FAILED
        assert node.is_terminal
        
        node.status = TaskStatus.CANCELLED
        assert node.is_terminal

    def test_retry_logic(self):
        node = TaskNode("t", "a", "t", {}, max_retries=2)
        node.status = TaskStatus.FAILED
        assert node.can_retry()
        
        node.prepare_retry()
        assert node.retry_count == 1
        assert node.status == TaskStatus.PENDING
        
        node.status = TaskStatus.FAILED
        node.prepare_retry()
        assert node.retry_count == 2
        assert not node.can_retry()
        
        with pytest.raises(ValueError, match="cannot be retried"):
            node.prepare_retry()

    def test_to_dict(self):
        node = TaskNode("t1", "agent", "type", {"key": "val"})
        d = node.to_dict()
        assert d["task_id"] == "t1"
        assert d["status"] == "pending"

    def test_duration_edge_cases(self):
        node = TaskNode("t", "a", "t", {})
        assert node.duration is None
        node.started_at = time.time()
        assert node.duration is None
        node.completed_at = time.time()
        assert node.duration >= 0

    def test_mark_failed_duration(self):
        node = TaskNode("t", "a", "t", {})
        node.mark_started()
        node.mark_failed("error")
        assert node.status == TaskStatus.FAILED
        assert node.duration is not None

    def test_is_ready(self):
        node = TaskNode("t", "a", "t", {})
        assert not node.is_ready
        node.status = TaskStatus.READY
        assert node.is_ready

class TestTaskGraph:
    @pytest.fixture
    def graph(self):
        return TaskGraph()

    def test_add_task_duplicate_logging(self, graph):
        task = TaskNode("t1", "a", "t", {})
        graph.add_task(task)
        with patch('logging.Logger.warning') as mock_log:
            assert graph.add_task(task) is False
            assert mock_log.called

    def test_would_create_cycle_internal(self, graph):
        # t1 -> t2 -> t3
        graph.add_task(TaskNode("t1", "a", "t", {}))
        graph.add_task(TaskNode("t2", "a", "t", {}))
        graph.add_task(TaskNode("t3", "a", "t", {}))
        graph.add_dependency("t2", "t1")
        graph.add_dependency("t3", "t2")
        
        # t1 depending on t3 would create cycle
        assert graph._would_create_cycle("t1", "t3") is True
        # t3 depending on t1 is fine
        assert graph._would_create_cycle("t3", "t1") is False

    def test_are_dependencies_satisfied_missing_dep(self, graph):
        task = TaskNode("t1", "a", "t", {})
        task.dependencies.add("missing")
        assert graph._are_dependencies_satisfied(task) is False

    def test_has_failed_tasks(self, graph):
        assert not graph.has_failed_tasks()
        task = TaskNode("t1", "a", "t", {})
        task.status = TaskStatus.FAILED
        graph.add_task(task)
        assert graph.has_failed_tasks() is True

    def test_get_completion_stats_empty(self, graph):
        stats = graph.get_completion_stats()
        assert stats["total_tasks"] == 0
        assert stats["completion_rate"] == 0

    def test_add_task_duplicate(self, graph):
        task = TaskNode("t1", "a", "t", {})
        assert graph.add_task(task) is True
        assert not graph.add_task(task) # Duplicate

    def test_add_dependency_cycle(self, graph):
        graph.add_task(TaskNode("t1", "a", "t", {}))
        graph.add_task(TaskNode("t2", "a", "t", {}))
        
        assert graph.add_dependency("t2", "t1") is True
        # Creating cycle: t1 depends on t2 which depends on t1
        assert graph.add_dependency("t1", "t2") is False

    def test_add_dependency_missing_tasks(self, graph):
        assert graph.add_dependency("missing1", "missing2") is False

    def test_get_ready_tasks_priority(self, graph):
        # t1 low priority, t2 high priority
        t1 = TaskNode("t1", "a", "t", {}, priority=1)
        t2 = TaskNode("t2", "a", "t", {}, priority=10)
        graph.add_task(t1)
        graph.add_task(t2)
        
        ready = graph.get_ready_tasks()
        assert len(ready) == 2
        assert ready[0].task_id == "t2" # Higher priority first

    def test_mark_task_completed_with_spawn(self, graph):
        def spawn_more(result):
            return [TaskNode("spawned", "agent", "type", {})]
            
        parent = TaskNode("parent", "a", "t", {})
        parent.spawn_callback = spawn_more
        graph.add_task(parent)
        
        spawned = graph.mark_task_completed("parent", "ok")
        assert len(spawned) == 1
        assert "spawned" in graph.nodes

    def test_mark_task_completed_spawn_error(self, graph):
        def bad_spawn(result):
            raise Exception("Spawn crash")
            
        task = TaskNode("t1", "a", "t", {})
        task.spawn_callback = bad_spawn
        graph.add_task(task)
        
        # Should catch exception and return empty list
        assert graph.mark_task_completed("t1", "ok") == []

    def test_mark_task_completed_missing(self, graph):
        assert graph.mark_task_completed("missing", "res") == []

    def test_mark_task_failed_missing(self, graph):
        assert graph.mark_task_failed("missing", "err") is False

    def test_retry_task_missing_or_invalid(self, graph):
        assert graph.retry_task("missing") is False
        
        task = TaskNode("t1", "a", "t", {}) # Status PENDING, can't retry
        graph.add_task(task)
        assert graph.retry_task("t1") is False

    def test_permanently_failed(self, graph):
        task = TaskNode("t1", "a", "t", {}, max_retries=0)
        task.status = TaskStatus.FAILED
        graph.add_task(task)
        assert graph.has_permanently_failed_tasks() is True

    def test_to_json(self, graph):
        graph.add_task(TaskNode("t1", "a", "t", {}))
        j = graph.to_json()
        data = json.loads(j)
        assert "nodes" in data
        assert "t1" in data["nodes"]

    def test_visualize_graph(self, graph):
        task = TaskNode("t1", "agent", "type", {})
        task.dependencies.add("dep")
        graph.add_task(task)
        viz = graph.visualize_graph()
        assert "t1" in viz
        assert "dep" in viz
