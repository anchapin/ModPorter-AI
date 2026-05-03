"""
Feedback-driven re-ranking for search results.

This module implements re-ranking based on user correction patterns,
allowing the search system to learn from user feedback.
"""

import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

ai_engine_path = str(Path(__file__).parent.parent.parent)
if ai_engine_path not in sys.path:
    sys.path.insert(0, ai_engine_path)

from schemas.multimodal_schema import SearchResult


@dataclass
class FeedbackBoost:
    """Feedback boost information for a chunk."""

    chunk_id: uuid.UUID
    boost_score: float
    correction_count: int
    last_correction_date: Optional[str]


class FeedbackReranker:
    """Re-rank search results based on user correction patterns."""

    STATUS_WEIGHTS = {
        "approved": 1.0,
        "pending": 0.3,
        "rejected": -0.5,
        "applied": 1.0,
    }

    def __init__(self, decay_factor: float = 0.95, db_session=None):
        """Initialize the feedback reranker.

        Args:
            decay_factor: Older corrections have less impact (0-1)
            db_session: Optional database session for CorrectionStore
        """
        self.decay_factor = decay_factor
        self._db_session = db_session
        self._correction_store = None

    async def initialize(self, db_session):
        """Initialize with database session."""
        self._db_session = db_session
        from learning.correction_store import CorrectionStore

        self._correction_store = CorrectionStore()
        await self._correction_store.initialize(db_session)

    async def rerank_with_feedback(
        self,
        query: str,
        initial_results: List[SearchResult],
        user_id: Optional[str] = None,
    ) -> List[SearchResult]:
        """Re-rank search results incorporating correction feedback.

        Algorithm:
        1. Fetch corrections for chunks in initial_results
        2. Calculate boost scores based on:
           - Number of corrections (more = stronger signal)
           - Recency (newer corrections weighted higher)
           - Correction status (approved > pending)
        3. Apply boost to original relevance scores
        4. Re-sort results
        """
        if not initial_results:
            return initial_results

        chunk_ids = []
        doc_id_to_chunk = {}
        for result in initial_results:
            doc_id = getattr(result.document, "id", None)
            if doc_id:
                chunk_id = uuid.UUID(str(doc_id)) if isinstance(doc_id, str) else doc_id
                chunk_ids.append(chunk_id)
                doc_id_to_chunk[str(chunk_id)] = result

        if not chunk_ids:
            return initial_results

        feedback_boosts = await self.get_feedback_boost(chunk_ids)

        boost_map = {boost.chunk_id: boost for boost in feedback_boosts}

        for result in initial_results:
            doc_id = getattr(result.document, "id", None)
            if doc_id:
                chunk_id = uuid.UUID(str(doc_id)) if isinstance(doc_id, str) else doc_id
                boost = boost_map.get(chunk_id)
                if boost:
                    result.final_score = result.final_score + boost.boost_score
                    if result.match_explanation:
                        result.match_explanation += f"; Feedback boost: {boost.boost_score:.3f}"
                    else:
                        result.match_explanation = f"Feedback boost: {boost.boost_score:.3f}"

        initial_results.sort(key=lambda x: x.final_score, reverse=True)

        for i, result in enumerate(initial_results):
            result.rank = i + 1

        return initial_results

    async def get_feedback_boost(
        self,
        chunk_ids: List[uuid.UUID],
    ) -> List[FeedbackBoost]:
        """Get feedback boost scores for chunks."""
        if not self._correction_store:
            return []

        boosts = []
        try:
            corrections = await self._correction_store.get_corrections(
                job_id=None, status=None, limit=1000
            )

            chunk_corrections = {}
            for correction in corrections:
                original_chunk_id = correction.get("original_chunk_id")
                if original_chunk_id:
                    chunk_id = (
                        uuid.UUID(original_chunk_id)
                        if isinstance(original_chunk_id, str)
                        else original_chunk_id
                    )
                    if chunk_id in chunk_ids:
                        if str(chunk_id) not in chunk_corrections:
                            chunk_corrections[str(chunk_id)] = []
                        chunk_corrections[str(chunk_id)].append(correction)

            for chunk_id in chunk_ids:
                chunk_corrections_list = chunk_corrections.get(str(chunk_id), [])
                if chunk_corrections_list:
                    boost_score = self._calculate_boost_score_for_corrections(
                        chunk_corrections_list
                    )
                    last_date = None
                    if chunk_corrections_list:
                        last_date = chunk_corrections_list[0].get("submitted_at")

                    boosts.append(
                        FeedbackBoost(
                            chunk_id=chunk_id,
                            boost_score=boost_score,
                            correction_count=len(chunk_corrections_list),
                            last_correction_date=last_date,
                        )
                    )

        except Exception:
            pass

        return boosts

    def _calculate_boost_score_for_corrections(
        self,
        corrections: List[dict],
    ) -> float:
        """Calculate boost score from a list of corrections for a chunk."""
        if not corrections:
            return 0.0

        total_boost = 0.0

        for correction in corrections:
            status = correction.get("status", "pending")
            submitted_at = correction.get("submitted_at")

            status_weight = self.STATUS_WEIGHTS.get(status, 0.0)

            recency_factor = 1.0
            if submitted_at:
                try:
                    if isinstance(submitted_at, str):
                        submitted_date = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
                    else:
                        submitted_date = submitted_at

                    days_since = (
                        datetime.now(timezone.utc) - submitted_date.replace(tzinfo=None)
                    ).days
                    recency_factor = self.decay_factor ** max(days_since, 0)
                except Exception:
                    recency_factor = 1.0

            correction_boost = status_weight * recency_factor
            total_boost += correction_boost

        min_boost = -0.5
        max_boost = 0.5
        normalized_boost = max(min_boost, min(max_boost, total_boost * 0.1))

        return normalized_boost

    def _calculate_boost_score(
        self,
        correction_count: int,
        last_correction_date: Optional[str],
        status_weights: List[float],
    ) -> float:
        """Calculate boost score for a chunk (legacy method)."""
        if correction_count == 0:
            return 0.0

        if status_weights:
            avg_weight = sum(status_weights) / len(status_weights)
        else:
            avg_weight = 0.3

        recency_factor = 1.0
        if last_correction_date:
            try:
                if isinstance(last_correction_date, str):
                    submitted_date = datetime.fromisoformat(
                        last_correction_date.replace("Z", "+00:00")
                    )
                else:
                    submitted_date = last_correction_date

                days_since = (datetime.now(timezone.utc) - submitted_date.replace(tzinfo=None)).days
                recency_factor = self.decay_factor ** max(days_since, 0)
            except Exception:
                recency_factor = 1.0

        boost = correction_count * avg_weight * recency_factor

        min_boost = -0.5
        max_boost = 0.5
        return max(min_boost, min(max_boost, boost * 0.1))

    async def get_user_preferences(
        self,
        user_id: str,
    ) -> Dict[str, float]:
        """Get learned user preferences from their corrections."""
        if not self._correction_store:
            return {}

        try:
            corrections = await self._correction_store.get_corrections(
                job_id=None, status=None, limit=1000
            )

            user_corrections = [c for c in corrections if c.get("user_id") == user_id]

            if not user_corrections:
                return {}

            preferences = {
                "correction_count": len(user_corrections),
                "approval_rate": 0.0,
                "avg_correction_length_change": 0.0,
            }

            approved = sum(1 for c in user_corrections if c.get("status") == "approved")
            if user_corrections:
                preferences["approval_rate"] = approved / len(user_corrections)

            length_changes = []
            for c in user_corrections:
                orig_len = len(c.get("original_output", ""))
                corr_len = len(c.get("corrected_output", ""))
                if orig_len > 0:
                    length_changes.append(corr_len / orig_len)

            if length_changes:
                preferences["avg_correction_length_change"] = sum(length_changes) / len(
                    length_changes
                )

            return preferences

        except Exception:
            return {}


async def rerank_with_feedback(
    query: str,
    initial_results: List[SearchResult],
    user_id: Optional[str] = None,
    decay_factor: float = 0.95,
) -> List[SearchResult]:
    """Standalone function to re-rank results with feedback."""
    reranker = FeedbackReranker(decay_factor=decay_factor)
    return await reranker.rerank_with_feedback(query, initial_results, user_id)
