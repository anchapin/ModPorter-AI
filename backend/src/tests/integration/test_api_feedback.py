import uuid

def test_submit_feedback_invalid_job_id(client):
    """Test feedback submission with a non-existent job_id."""
    invalid_job_id = str(uuid.uuid4())
    feedback_payload = {
        "job_id": invalid_job_id,
        "feedback_type": "thumbs_down",
        "comment": "This job does not exist.",
    }
    response = client.post("/api/v1/feedback", json=feedback_payload)
    assert response.status_code == 404
    assert f"Conversion job with ID '{invalid_job_id}' not found" in response.json()["detail"]

def test_submit_feedback_missing_fields(client):
    """Test feedback submission with missing required fields."""
    feedback_payload = {
        "job_id": str(uuid.uuid4()),
        "comment": "Missing type.",
    }
    response = client.post("/api/v1/feedback", json=feedback_payload)
    assert response.status_code == 422

    data = response.json()
    assert any(err["type"] == "missing" and err["loc"] == ["body", "feedback_type"] for err in data["detail"])

def test_get_training_data_empty(client):
    """Test fetching training data when no feedback exists."""
    response = client.get("/api/v1/ai/training_data")
    assert response.status_code == 200
    data = response.json()
    assert data["data"] == []
    assert data["total"] == 0  # Should be 0 when no training data exists
    assert data["limit"] == 100  # Default limit
    assert data["skip"] == 0     # Default skip
