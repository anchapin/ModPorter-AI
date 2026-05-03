# backend/src/tests/unit/test_api_qa.py
import pytest
from api.qa import start_qa_task, get_qa_status, get_qa_report, list_qa_tasks, mock_qa_tasks
from uuid import uuid4


@pytest.fixture(autouse=True)
def clear_mock_tasks():
    """Clear mock_qa_tasks before each test."""
    mock_qa_tasks.clear()


def test_start_qa_task_success():
    conversion_id = str(uuid4())
    response = start_qa_task(conversion_id)
    assert response["success"] is True
    assert "task_id" in response
    assert response["status"] == "pending"
    assert response["task_id"] in mock_qa_tasks


def test_start_qa_task_invalid_id():
    response = start_qa_task("invalid-uuid")
    assert response["success"] is False
    assert "error" in response


def test_get_qa_status_not_found():
    response = get_qa_status("non-existent-task")
    assert response["success"] is False
    assert response["error"] == "Task not found."


def test_get_qa_status_progression():
    conversion_id = str(uuid4())
    start_resp = start_qa_task(conversion_id)
    task_id = start_resp["task_id"]

    # Initially pending
    assert mock_qa_tasks[task_id]["status"] == "pending"

    # We might need to call it multiple times because of random.random() < 0.3
    # but for unit tests, we can just mock random or force it.
    # For now, let's just force the status to test the logic.
    mock_qa_tasks[task_id]["status"] = "running"
    response = get_qa_status(task_id)
    assert response["success"] is True
    assert response["task_info"]["progress"] > 0


def test_get_qa_report_not_ready():
    conversion_id = str(uuid4())
    start_resp = start_qa_task(conversion_id)
    task_id = start_resp["task_id"]

    response = get_qa_report(task_id)
    assert response["success"] is False
    assert "not available" in response["error"]


def test_get_qa_report_success():
    conversion_id = str(uuid4())
    start_resp = start_qa_task(conversion_id)
    task_id = start_resp["task_id"]

    # Force completion
    mock_qa_tasks[task_id]["status"] = "completed"
    mock_qa_tasks[task_id]["results_summary"] = {"overall_quality_score": 0.85}

    response = get_qa_report(task_id, report_format="json")
    assert response["success"] is True
    assert "report" in response
    assert response["report"]["overall_quality_score"] == 0.85


def test_get_qa_report_html():
    conversion_id = str(uuid4())
    start_resp = start_qa_task(conversion_id)
    task_id = start_resp["task_id"]
    mock_qa_tasks[task_id]["status"] = "completed"

    response = get_qa_report(task_id, report_format="html_summary")
    assert response["success"] is True
    assert "html_content" in response


def test_get_qa_report_unsupported():
    conversion_id = str(uuid4())
    start_resp = start_qa_task(conversion_id)
    task_id = start_resp["task_id"]
    mock_qa_tasks[task_id]["status"] = "completed"

    response = get_qa_report(task_id, report_format="xml")
    assert response["success"] is False
    assert "Unsupported" in response["error"]


def test_list_qa_tasks():
    id1 = str(uuid4())
    id2 = str(uuid4())
    start_qa_task(id1)
    start_qa_task(id2)

    response = list_qa_tasks()
    assert response["success"] is True
    assert len(response["tasks"]) == 2
    assert response["count"] == 2


def test_list_qa_tasks_filter():
    id1 = str(uuid4())
    id2 = str(uuid4())
    start_qa_task(id1)
    resp2 = start_qa_task(id2)
    task_id2 = resp2["task_id"]
    mock_qa_tasks[task_id2]["status"] = "completed"

    # Filter by conversion_id
    resp = list_qa_tasks(conversion_id=id1)
    assert len(resp["tasks"]) == 1
    assert resp["tasks"][0]["conversion_id"] == id1

    # Filter by status
    resp = list_qa_tasks(status="completed")
    assert len(resp["tasks"]) == 1
    assert resp["tasks"][0]["status"] == "completed"
