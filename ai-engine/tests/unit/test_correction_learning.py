"""
Unit tests for correction learning system.

Tests:
- CorrectionStore: Storage and retrieval of corrections
- CorrectionValidator: Validation of corrections before approval
- FeedbackReranker: Re-ranking based on correction patterns
"""

import sys
import os
import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestCorrectionStore:
    """Tests for CorrectionStore class."""

    @pytest.fixture
    def mock_db(self):
        session = MagicMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def store(self, mock_db):
        from learning.correction_store import CorrectionStore
        store = CorrectionStore()
        # Mock _get_correction_model to return a mock class
        mock_model = MagicMock()
        mock_model.__name__ = "CorrectionSubmission"
        store._get_correction_model = AsyncMock(return_value=mock_model)
        return store

    @pytest.mark.asyncio
    async def test_store_initialization(self, store, mock_db):
        """Test store initialization."""
        await store.initialize(mock_db)
        assert store._db_session == mock_db
        assert store._initialized is True

    @pytest.mark.asyncio
    async def test_add_correction(self, store, mock_db):
        """Test adding a correction."""
        await store.initialize(mock_db)
        
        # Setup mock model instance
        mock_correction = MagicMock()
        mock_correction.id = uuid.uuid4()
        mock_correction.job_id = uuid.uuid4()
        mock_correction.original_output = "orig"
        mock_correction.corrected_output = "corr"
        mock_correction.correction_rationale = "rat"
        mock_correction.status = "pending"
        mock_correction.submitted_at = datetime.now(timezone.utc)
        
        # Ensure the model class returns the mock instance when called
        store._get_correction_model.return_value.return_value = mock_correction
        
        res = await store.add_correction(
            job_id=mock_correction.job_id,
            user_id="user1",
            original_output="orig",
            corrected_output="corr",
            correction_rationale="rat"
        )
        
        assert res["original_output"] == "orig"
        assert res["status"] == "pending"
        assert mock_db.add.called
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_get_corrections(self, store, mock_db):
        """Test retrieving corrections."""
        await store.initialize(mock_db)
        
        mock_correction = MagicMock()
        mock_correction.id = uuid.uuid4()
        mock_correction.job_id = uuid.uuid4()
        mock_correction.status = "pending"
        mock_correction.submitted_at = datetime.now(timezone.utc)
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_correction]
        mock_db.execute.return_value = mock_result
        
        with patch('sqlalchemy.select'):
            res = await store.get_corrections(status="pending")
            assert len(res) == 1
            assert res[0]["status"] == "pending"
            assert mock_db.execute.called

    @pytest.mark.asyncio
    async def test_get_corrections_with_job_id(self, store, mock_db):
        """Test retrieving corrections with job_id filter."""
        await store.initialize(mock_db)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        with patch('sqlalchemy.select'):
            res = await store.get_corrections(job_id=uuid.uuid4())
            assert res == []

    @pytest.mark.asyncio
    async def test_get_pending_corrections(self, store, mock_db):
        """Test get_pending_corrections helper."""
        await store.initialize(mock_db)
        with patch.object(store, 'get_corrections', return_value=[{"status": "pending"}]) as mock_get:
            res = await store.get_pending_corrections()
            assert len(res) == 1
            mock_get.assert_called_with(status="pending", limit=1000)

    @pytest.mark.asyncio
    async def test_update_correction_status(self, store, mock_db):
        """Test updating correction status."""
        await store.initialize(mock_db)
        
        mock_correction = MagicMock()
        mock_correction.id = uuid.uuid4()
        mock_correction.job_id = uuid.uuid4()
        mock_correction.status = "pending"
        mock_correction.reviewed_at = None
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_correction
        mock_db.execute.return_value = mock_result
        
        with patch('sqlalchemy.select'):
            res = await store.update_correction_status(
                correction_id=mock_correction.id,
                status="approved",
                reviewed_by="admin"
            )
            assert res["status"] == "approved"
            assert mock_correction.status == "approved"
            assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_update_correction_not_found(self, store, mock_db):
        """Test updating non-existent correction."""
        await store.initialize(mock_db)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with patch('sqlalchemy.select'):
            with pytest.raises(ValueError, match="not found"):
                await store.update_correction_status(uuid.uuid4(), "approved")

    @pytest.mark.asyncio
    async def test_mark_applied(self, store, mock_db):
        """Test marking correction as applied."""
        await store.initialize(mock_db)
        
        mock_correction = MagicMock()
        mock_correction.id = uuid.uuid4()
        mock_correction.job_id = uuid.uuid4()
        mock_correction.status = "approved"
        mock_correction.applied_at = None
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_correction
        mock_db.execute.return_value = mock_result
        
        with patch('sqlalchemy.select'):
            res = await store.mark_applied(mock_correction.id)
            assert res["status"] == "applied"
            assert mock_correction.embedding_updated is True
            assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_uninitialized_error(self, store):
        """Test error when store is not initialized."""
        from learning.correction_store import CorrectionStore
        fresh_store = CorrectionStore()
        with pytest.raises(RuntimeError, match="not initialized"):
            await fresh_store.add_correction(uuid.uuid4(), "u", "o", "c")

    @pytest.mark.asyncio
    async def test_model_not_available_error(self, store, mock_db):
        """Test error when model is not available."""
        await store.initialize(mock_db)
        store._get_correction_model = AsyncMock(return_value=None)
        
        with pytest.raises(RuntimeError, match="model not available"):
            await store.add_correction(uuid.uuid4(), "u", "o", "c")


class TestCorrectionValidator:
    """Tests for CorrectionValidator class."""

    @pytest.fixture
    def validator(self):
        from learning.validation_workflow import CorrectionValidator
        return CorrectionValidator()

    @pytest.mark.asyncio
    async def test_validator_initialize(self, validator):
        """Test validator initialization."""
        mock_db = MagicMock()
        with patch('learning.correction_store.CorrectionStore.initialize', new_callable=AsyncMock) as mock_init:
            await validator.initialize(mock_db)
            assert validator._db_session == mock_db
            assert validator._correction_store is not None
            mock_init.assert_called_once_with(mock_db)

    @pytest.mark.asyncio
    async def test_validator_valid_correction(self, validator):
        """Test validation of a valid correction."""
        original = "public class Block { }"
        corrected = "public class CustomBlock extends Block { private int value; }"
        result = await validator.validate_correction(original, corrected)
        assert result.is_valid is True
        assert result.confidence > 0.5

    @pytest.mark.asyncio
    async def test_validator_invalid_empty(self, validator):
        """Test validation fails for empty output."""
        res = await validator.validate_correction("orig", "")
        assert res.is_valid is False
        assert "empty" in res.issues[0].lower()

    @pytest.mark.asyncio
    async def test_validator_invalid_too_short(self, validator):
        """Test validation fails for too short output."""
        res = await validator.validate_correction("original", "a")
        assert res.is_valid is False
        assert "too short" in res.issues[0].lower()

    @pytest.mark.asyncio
    async def test_validator_invalid_identical(self, validator):
        """Test validation fails for identical output."""
        res = await validator.validate_correction("identical", "identical")
        assert res.is_valid is False
        assert "identical" in res.issues[0].lower()

    @pytest.mark.asyncio
    async def test_validator_malicious_patterns(self, validator):
        """Test detection of malicious patterns."""
        res = await validator.validate_correction("safe and long original string", "eval(something)")
        assert any("malicious" in issue for issue in res.issues)

    @pytest.mark.asyncio
    async def test_validator_json_syntax(self, validator):
        """Test validation of JSON syntax."""
        original = '{"key": "value", "long": "string to avoid ratio"}'
        corrected = '{"key": "value", "new": 123, "long": "string to avoid ratio"}'
        res = await validator.validate_correction(original, corrected)
        assert res.is_valid is True

        # Invalid JSON
        corrected_invalid = '{"key": "value", "broken"}'
        res = await validator.validate_correction(original, corrected_invalid)
        assert any("JSON" in issue for issue in res.issues)

    @pytest.mark.asyncio
    async def test_validator_syntax_unbalanced(self, validator):
        """Test detection of unbalanced braces/parens."""
        res = await validator.validate_correction("safe and long string", "function() { return 1;")
        assert any("braces" in issue for issue in res.issues)
        res = await validator.validate_correction("safe and long string", "def my_func(arg: ")
        assert any("parentheses" in issue for issue in res.issues)

    @pytest.mark.asyncio
    async def test_validator_semantic_coherence(self, validator):
        """Test semantic coherence check."""
        original = "word1 word2 word3 word4 word5"
        corrected = "completely unrelated text here"
        res = await validator.validate_correction(original, corrected)
        assert any("overlap" in s.lower() for s in res.suggestions)

    @pytest.mark.asyncio
    async def test_approve_correction_success(self, validator):
        """Test successful correction approval."""
        validator._correction_store = MagicMock()
        cid = uuid.uuid4()
        validator._correction_store.get_corrections = AsyncMock(return_value=[
            {
                "id": str(cid),
                "original_output": "original long enough output",
                "corrected_output": "original long enough output corrected",
                "status": "pending"
            }
        ])
        validator._correction_store.update_correction_status = AsyncMock()
        
        success, msg = await validator.approve_correction(cid)
        assert success is True
        assert validator._correction_store.update_correction_status.called

    @pytest.mark.asyncio
    async def test_approve_correction_failure(self, validator):
        """Test approval failure (exception in store)."""
        validator._correction_store = MagicMock()
        cid = uuid.uuid4()
        validator._correction_store.get_corrections = AsyncMock(return_value=[
            {
                "id": str(cid),
                "original_output": "original long enough output",
                "corrected_output": "original long enough output corrected"
            }
        ])
        validator._correction_store.update_correction_status = AsyncMock(side_effect=Exception("DB fail"))
        
        success, msg = await validator.approve_correction(cid)
        assert success is False
        assert "Failed" in msg

    @pytest.mark.asyncio
    async def test_batch_validate(self, validator):
        """Test batch validation."""
        validator._correction_store = MagicMock()
        cid1 = uuid.uuid4()
        validator._correction_store.get_corrections = AsyncMock(return_value=[
            {"id": str(cid1), "original_output": "long enough o1", "corrected_output": "long enough c1"}
        ])
        results = await validator.batch_validate([cid1])
        assert len(results) == 1
        assert results[0][1].is_valid is True


class TestFeedbackReranker:
    """Tests for FeedbackReranker class."""

    @pytest.fixture
    def reranker(self):
        from search.feedback_reranker import FeedbackReranker
        return FeedbackReranker(decay_factor=0.95)

    def test_reranker_initialization(self, reranker):
        assert reranker.decay_factor == 0.95

    def test_calculate_boost_score(self, reranker):
        assert reranker._calculate_boost_score(0, None, []) == 0.0
        assert reranker._calculate_boost_score(1, None, [1.0]) > 0

    @pytest.mark.asyncio
    async def test_rerank_empty(self, reranker):
        reranked = await reranker.rerank_with_feedback("query", [])
        assert reranked == []


def test_validation_result_to_dict():
    from learning.validation_workflow import ValidationResult
    res = ValidationResult(True, 0.9, [], [])
    d = res.to_dict()
    assert d["is_valid"] is True

@pytest.mark.asyncio
async def test_validate_correction_standalone():
    from learning.validation_workflow import validate_correction
    res = await validate_correction("test long enough", "test long enough corrected")
    assert res.is_valid is True
