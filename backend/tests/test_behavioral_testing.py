
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from backend.src.api.behavioral_testing import router
from uuid import uuid4

client = TestClient(router)

def test_create_behavioral_test():
    test_request = {
        "conversion_id": str(uuid4()),
        "test_scenarios": [
            {
                "scenario": "Test Scenario",
                "steps": [{"action": "do_something"}],
            }
        ],
    }

    with patch("backend.src.api.behavioral_testing.BackgroundTasks.add_task") as mock_add_task:
        response = client.post("/tests", json=test_request)

        assert response.status_code == 200
        assert response.json()["status"] == "RUNNING"
        assert response.json()["total_scenarios"] == 1
        mock_add_task.assert_called_once()

def test_get_behavioral_test():
    test_id = uuid4()
    response = client.get(f"/tests/{test_id}")

    assert response.status_code == 200
    assert response.json()["test_id"] == str(test_id)
    assert response.json()["status"] == "MOCK_COMPLETED"

def test_get_test_scenarios():
    test_id = uuid4()
    response = client.get(f"/tests/{test_id}/scenarios")

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["scenario_name"] == "Block Interaction Test"

def test_get_test_report():
    test_id = uuid4()
    response = client.get(f"/tests/{test_id}/report")

    assert response.status_code == 200
    assert response.json()["report_type"] == "Behavioral Test Report"

def test_get_test_report_invalid_format():
    test_id = uuid4()
    response = client.get(f"/tests/{test_id}/report?format=invalid")

    assert response.status_code == 400
    assert response.json()["detail"] == "Format must be json, text, or html"

def test_delete_behavioral_test():
    test_id = uuid4()
    response = client.delete(f"/tests/{test_id}")

    assert response.status_code == 200
    assert response.json()["message"] == f"Test {test_id} deleted successfully"
