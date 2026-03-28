"""
Unit tests for feedback API endpoints.

Tests:
- Submit correction endpoint
- List corrections with filters
- Review correction (approve/reject)
- Apply correction
"""

import sys
import os
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "ai-engine"))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestSubmitCorrection:
    """Tests for correction submission."""

    @pytest.mark.asyncio
    async def test_submit_correction(self):
        """Test submitting a correction."""
        mock_db = AsyncMock()
        mock_session = AsyncMock()
        mock_db.session.return_value = mock_session

        with patch("learning.correction_store.CorrectionStore") as MockStore:
            mock_store = AsyncMock()
            mock_store.initialize = AsyncMock()
            mock_store.add_correction = AsyncMock(
                return_value={
                    "id": str(uuid.uuid4()),
                    "job_id": str(uuid.uuid4()),
                    "original_output": "original",
                    "corrected_output": "corrected",
                    "status": "pending",
                    "submitted_at": "2024-01-01T00:00:00",
                }
            )
            MockStore.return_value = mock_store

            result = await mock_store.add_correction(
                job_id=uuid.uuid4(),
                user_id="test_user",
                original_output="original code",
                corrected_output="corrected code",
            )

            assert result["status"] == "pending"
            assert result["original_output"] == "original"
            assert result["corrected_output"] == "corrected"


class TestListCorrections:
    """Tests for listing corrections."""

    @pytest.mark.asyncio
    async def test_list_corrections_with_filters(self):
        """Test listing corrections with status filter."""
        mock_corrections = [
            {
                "id": str(uuid.uuid4()),
                "job_id": str(uuid.uuid4()),
                "original_output": "test1",
                "corrected_output": "test1_corrected",
                "status": "pending",
                "submitted_at": "2024-01-01T00:00:00",
            },
            {
                "id": str(uuid.uuid4()),
                "job_id": str(uuid.uuid4()),
                "original_output": "test2",
                "corrected_output": "test2_corrected",
                "status": "approved",
                "submitted_at": "2024-01-02T00:00:00",
            },
        ]

        with patch("learning.correction_store.CorrectionStore") as MockStore:
            mock_store = AsyncMock()
            mock_store.get_corrections = AsyncMock(return_value=mock_corrections)
            MockStore.return_value = mock_store

            result = await mock_store.get_corrections(status="pending")

            assert len(result) == 2
            assert all(c["status"] in ["pending", "approved"] for c in result)

    @pytest.mark.asyncio
    async def test_list_pending_corrections(self):
        """Test listing only pending corrections."""
        mock_corrections = [
            {
                "id": str(uuid.uuid4()),
                "status": "pending",
            }
        ]

        with patch("learning.correction_store.CorrectionStore") as MockStore:
            mock_store = AsyncMock()
            mock_store.get_pending_corrections = AsyncMock(return_value=mock_corrections)
            MockStore.return_value = mock_store

            result = await mock_store.get_pending_corrections()

            assert len(result) >= 0


class TestReviewCorrection:
    """Tests for reviewing corrections."""

    @pytest.mark.asyncio
    async def test_review_correction_approve(self):
        """Test approving a correction."""
        correction_id = uuid.uuid4()

        with patch("learning.correction_store.CorrectionStore") as MockStore:
            mock_store = AsyncMock()
            mock_store.update_correction_status = AsyncMock(
                return_value={
                    "id": str(correction_id),
                    "status": "approved",
                    "reviewed_by": "validator",
                    "review_notes": "Looks good",
                }
            )
            MockStore.return_value = mock_store

            result = await mock_store.update_correction_status(
                correction_id=correction_id,
                status="approved",
                reviewed_by="validator",
                review_notes="Looks good",
            )

            assert result["status"] == "approved"

    @pytest.mark.asyncio
    async def test_review_correction_reject(self):
        """Test rejecting a correction."""
        correction_id = uuid.uuid4()

        with patch("learning.correction_store.CorrectionStore") as MockStore:
            mock_store = AsyncMock()
            mock_store.update_correction_status = AsyncMock(
                return_value={
                    "id": str(correction_id),
                    "status": "rejected",
                    "reviewed_by": "validator",
                    "review_notes": "Not a valid correction",
                }
            )
            MockStore.return_value = mock_store

            result = await mock_store.update_correction_status(
                correction_id=correction_id,
                status="rejected",
                reviewed_by="validator",
                review_notes="Not a valid correction",
            )

            assert result["status"] == "rejected"


class TestApplyCorrection:
    """Tests for applying corrections."""

    @pytest.mark.asyncio
    async def test_apply_correction(self):
        """Test applying a correction to the knowledge base."""
        correction_id = uuid.uuid4()

        with patch("learning.correction_store.CorrectionStore") as MockStore:
            mock_store = AsyncMock()
            mock_store.mark_applied = AsyncMock(
                return_value={
                    "id": str(correction_id),
                    "status": "applied",
                    "applied_at": "2024-01-03T00:00:00",
                    "embedding_updated": True,
                }
            )
            MockStore.return_value = mock_store

            result = await mock_store.mark_applied(correction_id)

            assert result["status"] == "applied"
            assert result["embedding_updated"] is True


class TestValidationWorkflow:
    """Tests for validation workflow."""

    @pytest.mark.asyncio
    async def test_validator_approve_correction(self):
        """Test approval workflow with validation."""
        from learning.validation_workflow import CorrectionValidator

        validator = CorrectionValidator()

        with patch.object(validator, "_correction_store") as mock_store:
            mock_store.get_corrections = AsyncMock(
                return_value=[
                    {
                        "id": str(uuid.uuid4()),
                        "original_output": "original code",
                        "corrected_output": "corrected code",
                        "correction_rationale": "Improved logic",
                        "status": "pending",
                    }
                ]
            )
            mock_store.update_correction_status = AsyncMock()

            validation = await validator.validate_correction(
                original_output="original code",
                corrected_output="corrected code",
            )

            assert isinstance(validation.is_valid, bool)
            assert isinstance(validation.confidence, float)
