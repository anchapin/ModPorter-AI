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
    data = response.json()
    # Error format uses 'message' or 'details' instead of 'detail'
    msg = data.get("message") or str(data.get("details") or "")
    assert (
        f"Conversion job with ID '{invalid_job_id}' not found" in msg or "not found" in msg.lower()
    )


def test_submit_feedback_missing_fields(client):
    """Test feedback submission with missing required fields."""
    feedback_payload = {
        "job_id": str(uuid.uuid4()),
        "comment": "Missing type.",
    }
    response = client.post("/api/v1/feedback", json=feedback_payload)
    assert response.status_code == 422

    data = response.json()
    # Error format uses 'details' (list of validation errors) instead of 'detail'
    details = data.get("details") or data.get("message", "")
    if isinstance(details, list):
        assert any(
            err.get("type") == "missing" and "feedback_type" in str(err.get("loc", []))
            for err in details
        )
    else:
        assert "feedback_type" in str(details).lower() or "validation" in str(details).lower()


def test_get_training_data_empty(client):
    """Test fetching training data when no feedback exists."""
    response = client.get("/api/v1/ai/training_data")
    assert response.status_code == 200
    data = response.json()
    assert data["data"] == []
    assert data["total"] == 0  # Should be 0 when no training data exists
    assert data["limit"] == 100  # Default limit
    assert data["skip"] == 0  # Default skip
