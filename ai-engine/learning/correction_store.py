"""
Correction storage and retrieval for user correction learning system.

Provides async methods for managing correction submissions in the knowledge base.
"""

import uuid
import sys
import os
from typing import List, Optional
from datetime import datetime, timezone
from pathlib import Path

ai_engine_path = str(Path(__file__).parent.parent)
if ai_engine_path not in sys.path:
    sys.path.insert(0, ai_engine_path)


class CorrectionStore:
    """Store and retrieve user corrections for knowledge base updates."""

    def __init__(self):
        self._db_session = None
        self._initialized = False

    async def initialize(self, db_session):
        """Initialize with database session."""
        self._db_session = db_session
        self._initialized = True

    async def add_correction(
        self,
        job_id: uuid.UUID,
        user_id: Optional[str],
        original_output: str,
        corrected_output: str,
        correction_rationale: Optional[str] = None,
        original_chunk_id: Optional[uuid.UUID] = None,
    ) -> dict:
        """Add a new correction submission."""
        if not self._initialized:
            raise RuntimeError("CorrectionStore not initialized. Call initialize() first.")

        CorrectionSubmission = await self._get_correction_model()
        if CorrectionSubmission is None:
            raise RuntimeError("CorrectionSubmission model not available")

        correction = CorrectionSubmission(
            job_id=job_id,
            user_id=user_id,
            original_output=original_output,
            corrected_output=corrected_output,
            correction_rationale=correction_rationale,
            original_chunk_id=original_chunk_id,
            status="pending",
        )

        self._db_session.add(correction)
        await self._db_session.commit()
        await self._db_session.refresh(correction)

        return {
            "id": str(correction.id),
            "job_id": str(correction.job_id),
            "original_output": correction.original_output,
            "corrected_output": correction.corrected_output,
            "correction_rationale": correction.correction_rationale,
            "status": correction.status,
            "submitted_at": correction.submitted_at.isoformat(),
        }

    async def get_corrections(
        self,
        job_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[dict]:
        """Get corrections with optional filters."""
        if not self._initialized:
            raise RuntimeError("CorrectionStore not initialized. Call initialize() first.")

        CorrectionSubmission = await self._get_correction_model()
        if CorrectionSubmission is None:
            raise RuntimeError("CorrectionSubmission model not available")

        from sqlalchemy import select

        query = select(CorrectionSubmission)

        if job_id:
            query = query.where(CorrectionSubmission.job_id == job_id)

        if status:
            query = query.where(CorrectionSubmission.status == status)

        query = query.order_by(CorrectionSubmission.submitted_at.desc()).offset(offset).limit(limit)

        result = await self._db_session.execute(query)
        corrections = result.scalars().all()

        return [
            {
                "id": str(c.id),
                "job_id": str(c.job_id),
                "original_output": c.original_output,
                "corrected_output": c.corrected_output,
                "correction_rationale": c.correction_rationale,
                "status": c.status,
                "submitted_at": c.submitted_at.isoformat(),
            }
            for c in corrections
        ]

    async def get_pending_corrections(self) -> List[dict]:
        """Get all pending corrections for review."""
        return await self.get_corrections(status="pending", limit=1000)

    async def update_correction_status(
        self,
        correction_id: uuid.UUID,
        status: str,
        reviewed_by: Optional[str] = None,
        review_notes: Optional[str] = None,
    ) -> dict:
        """Update correction status after review."""
        if not self._initialized:
            raise RuntimeError("CorrectionStore not initialized. Call initialize() first.")

        CorrectionSubmission = await self._get_correction_model()
        if CorrectionSubmission is None:
            raise RuntimeError("CorrectionSubmission model not available")

        from sqlalchemy import select

        query = select(CorrectionSubmission).where(CorrectionSubmission.id == correction_id)
        result = await self._db_session.execute(query)
        correction = result.scalar_one_or_none()

        if not correction:
            raise ValueError(f"Correction {correction_id} not found")

        correction.status = status
        correction.reviewed_by = reviewed_by
        correction.review_notes = review_notes
        correction.reviewed_at = datetime.now(timezone.utc)

        await self._db_session.commit()
        await self._db_session.refresh(correction)

        return {
            "id": str(correction.id),
            "job_id": str(correction.job_id),
            "status": correction.status,
            "reviewed_by": correction.reviewed_by,
            "review_notes": correction.review_notes,
            "reviewed_at": correction.reviewed_at.isoformat() if correction.reviewed_at else None,
        }

    async def mark_applied(self, correction_id: uuid.UUID) -> dict:
        """Mark correction as applied to knowledge base."""
        if not self._initialized:
            raise RuntimeError("CorrectionStore not initialized. Call initialize() first.")

        CorrectionSubmission = await self._get_correction_model()
        if CorrectionSubmission is None:
            raise RuntimeError("CorrectionSubmission model not available")

        from sqlalchemy import select

        query = select(CorrectionSubmission).where(CorrectionSubmission.id == correction_id)
        result = await self._db_session.execute(query)
        correction = result.scalar_one_or_none()

        if not correction:
            raise ValueError(f"Correction {correction_id} not found")

        correction.status = "applied"
        correction.applied_at = datetime.now(timezone.utc)
        correction.embedding_updated = True

        await self._db_session.commit()
        await self._db_session.refresh(correction)

        return {
            "id": str(correction.id),
            "job_id": str(correction.job_id),
            "status": correction.status,
            "applied_at": correction.applied_at.isoformat() if correction.applied_at else None,
            "embedding_updated": correction.embedding_updated,
        }

    async def _get_correction_model(self):
        """Dynamically load the CorrectionSubmission model from backend."""
        try:
            backend_path = os.path.join(os.path.dirname(__file__), "..", "..", "backend", "src")
            if backend_path not in sys.path:
                sys.path.insert(0, backend_path)

            from db.models import CorrectionSubmission

            return CorrectionSubmission
        except ImportError:
            return None
