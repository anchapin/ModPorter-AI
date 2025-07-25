"""
End-to-end integration test for mod conversion workflow.

Tests the complete pipeline: upload JAR -> start conversion -> wait for completion -> download .mcaddon

Issue #170: https://github.com/anchapin/ModPorter-AI/issues/170
"""

import pytest
import time
from pathlib import Path


class TestEndToEndIntegration:
    """End-to-end integration tests for the conversion workflow."""

    def test_complete_jar_to_mcaddon_conversion(self, client):
        """
        Complete test: uploads simple_copper_block.jar → waits for Celery job → downloads .mcaddon.
        
        This is the core test required by issue #170:
        - Upload tests/fixtures/simple_copper_block.jar
        - Use FastAPI TestClient + simulated Celery processing
        - Assert HTTP 200 and non-zero .mcaddon bytes
        """
        
        # Step 1: Verify fixture exists
        fixture_path = Path(__file__).parent.parent.parent.parent.parent / "tests" / "fixtures" / "simple_copper_block.jar"
        assert fixture_path.exists(), f"Test fixture not found: {fixture_path}"
        
        # Step 2: Upload the JAR file
        with open(fixture_path, "rb") as jar_file:
            upload_response = client.post(
                "/api/v1/upload",
                files={"file": ("simple_copper_block.jar", jar_file, "application/java-archive")}
            )
        
        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
        upload_data = upload_response.json()
        assert "file_id" in upload_data
        assert upload_data["original_filename"] == "simple_copper_block.jar"
        file_id = upload_data["file_id"]
        
        # Step 3: Start conversion job
        conversion_response = client.post(
            "/api/v1/convert",
            json={
                "file_id": file_id,
                "original_filename": "simple_copper_block.jar",
                "target_version": "1.20.0",
                "options": {"test_mode": True}
            }
        )
        
        assert conversion_response.status_code == 200, f"Conversion start failed: {conversion_response.text}"
        conversion_data = conversion_response.json()
        assert "job_id" in conversion_data
        assert conversion_data["status"] in ["preprocessing", "queued"]
        job_id = conversion_data["job_id"]
        
        # Step 4: Poll for completion (simulating Celery job processing)
        max_attempts = 30  # 30 attempts * 2 seconds = 1 minute max wait
        poll_interval = 2  # seconds
        
        final_status = None
        for attempt in range(max_attempts):
            status_response = client.get(f"/api/v1/convert/{job_id}/status")
            
            assert status_response.status_code == 200, f"Status check failed: {status_response.text}"
            status_data = status_response.json()
            
            assert "job_id" in status_data
            assert "status" in status_data
            assert "progress" in status_data
            assert status_data["job_id"] == job_id
            
            final_status = status_data["status"]
            
            # Check if job reached final state
            if final_status in ["completed", "failed"]:
                break
            
            # Wait before next poll
            if attempt < max_attempts - 1:
                time.sleep(poll_interval)
        
        # Assert conversion completed successfully
        assert final_status == "completed", f"Job did not complete successfully. Final status: {final_status}"
        
        # Step 5: Download the converted .mcaddon file
        download_response = client.get(f"/api/v1/convert/{job_id}/download")
        
        assert download_response.status_code == 200, f"Download failed: {download_response.status_code}"
        
        # Step 6: Assert non-zero .mcaddon bytes (core requirement from issue #170)
        mcaddon_content = download_response.content
        assert len(mcaddon_content) > 0, "Downloaded .mcaddon file has zero bytes"
        
        # Additional validation: should be a valid ZIP file (mcaddon is ZIP format)
        assert mcaddon_content.startswith(b'PK'), "Downloaded file is not a valid ZIP/mcaddon format"
        
        # Log success metrics for debugging
        print(f"✅ Integration test passed:")
        print(f"   - Job ID: {job_id}")
        print(f"   - Final status: {final_status}")
        print(f"   - .mcaddon size: {len(mcaddon_content):,} bytes")
        
    def test_job_appears_in_conversions_list(self, client):
        """
        Verify that completed jobs appear in the conversions list endpoint.
        """
        fixture_path = Path(__file__).parent.parent.parent.parent.parent / "tests" / "fixtures" / "simple_copper_block.jar"
        
        # Upload and convert (abbreviated version of above test)
        with open(fixture_path, "rb") as jar_file:
            upload_response = client.post(
                "/api/v1/upload",
                files={"file": ("simple_copper_block.jar", jar_file, "application/java-archive")}
            )
        
        file_id = upload_response.json()["file_id"]
        
        conversion_response = client.post(
            "/api/v1/convert",
            json={
                "file_id": file_id,
                "original_filename": "simple_copper_block.jar",
                "target_version": "1.20.0"
            }
        )
        
        job_id = conversion_response.json()["job_id"]
        
        # Wait for completion (short wait for list test)
        for _ in range(15):
            status_response = client.get(f"/api/v1/convert/{job_id}/status")
            if status_response.json()["status"] in ["completed", "failed"]:
                break
            time.sleep(2)
        
        # Test: Job appears in conversions list
        list_response = client.get("/api/v1/conversions")
        assert list_response.status_code == 200, f"List conversions failed: {list_response.text}"
        
        conversions = list_response.json()
        assert isinstance(conversions, list), "Conversions should be a list"
        
        # Find our job in the list
        our_job = None
        for conversion in conversions:
            if conversion.get("job_id") == job_id:
                our_job = conversion
                break
        
        assert our_job is not None, f"Job {job_id} not found in conversions list"
        assert "status" in our_job
        assert "progress" in our_job

    def test_error_handling_invalid_file_type(self, client):
        """
        Test error handling for invalid file types.
        """
        
        # Try to upload a text file instead of JAR
        invalid_content = b"This is not a JAR file"
        
        upload_response = client.post(
            "/api/v1/upload",
            files={"file": ("invalid.txt", invalid_content, "text/plain")}
        )
        
        assert upload_response.status_code == 400, "Should reject invalid file types"
        error_data = upload_response.json()
        assert "detail" in error_data
        assert "not supported" in error_data["detail"].lower()

    def test_nonexistent_job_status(self, client):
        """
        Test error handling for non-existent job status checks.
        """
        
        fake_job_id = "12345678-1234-1234-1234-123456789012"
        
        status_response = client.get(f"/api/v1/convert/{fake_job_id}/status")
        
        assert status_response.status_code == 404, "Should return 404 for non-existent jobs"
        error_data = status_response.json()
        assert "detail" in error_data
        assert "not found" in error_data["detail"].lower()


if __name__ == "__main__":
    # Allow running the test directly for debugging
    pytest.main([__file__, "-v"])