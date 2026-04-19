"""
Comprehensive pytest tests for db/crud.py - Database CRUD Module.
Coverage target: 80%+
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from db import crud
from db.models import (
    ConversionJob,
    ConversionFeedback,
    DocumentEmbedding,
    Experiment,
    ExperimentVariant,
    ExperimentResult,
    BehaviorFile,
    AddonAsset,
    Asset,
    PatternSubmission,
)


class TestJobCRUD:
    """Test job-related CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_job_success(self):
        """Test creating a job successfully."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.flush = AsyncMock()

        job = await crud.create_job(
            session=mock_session,
            file_id="test-file-123",
            original_filename="test.jar",
            target_version="1.20.0",
            options={"test": True},
        )

        assert job is not None
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_job_no_commit(self):
        """Test creating a job without committing."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        job = await crud.create_job(
            session=mock_session,
            file_id="test-file-123",
            original_filename="test.jar",
            target_version="1.20.0",
            commit=False,
        )

        assert job is not None
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_job_success(self):
        """Test getting a job by ID."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_job = MagicMock(spec=ConversionJob)
        mock_result.scalar_one_or_none.return_value = mock_job
        mock_session.execute.return_value = mock_result

        job_id = str(uuid.uuid4())
        job = await crud.get_job(session=mock_session, job_id=job_id)

        assert job == mock_job
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_job_invalid_uuid(self):
        """Test getting job with invalid UUID."""
        mock_session = AsyncMock(spec=AsyncSession)

        job = await crud.get_job(session=mock_session, job_id="not-a-uuid")

        assert job is None

    @pytest.mark.asyncio
    async def test_update_job_status_success(self):
        """Test updating job status."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_job = MagicMock(spec=ConversionJob)
        mock_result.scalar_one_or_none.return_value = mock_job
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        job_id = str(uuid.uuid4())
        job = await crud.update_job_status(session=mock_session, job_id=job_id, status="completed")

        assert job == mock_job
        mock_session.execute.assert_called()

    @pytest.mark.asyncio
    async def test_update_job_status_invalid_uuid(self):
        """Test updating job status with invalid UUID."""
        mock_session = AsyncMock(spec=AsyncSession)

        job = await crud.update_job_status(
            session=mock_session, job_id="invalid", status="completed"
        )

        assert job is None

    @pytest.mark.asyncio
    async def test_update_job_progress_success(self):
        """Test updating job progress."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_progress = MagicMock()
        mock_result.scalar_one.return_value = mock_progress
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        job_id = str(uuid.uuid4())
        progress = await crud.update_job_progress(session=mock_session, job_id=job_id, progress=50)

        assert progress == mock_progress

    @pytest.mark.asyncio
    async def test_update_job_progress_invalid_uuid(self):
        """Test updating progress with invalid UUID."""
        mock_session = AsyncMock(spec=AsyncSession)

        with pytest.raises(ValueError):
            await crud.update_job_progress(session=mock_session, job_id="invalid", progress=50)

    @pytest.mark.asyncio
    async def test_get_job_progress_success(self):
        """Test getting job progress."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_progress = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_progress
        mock_session.execute.return_value = mock_result

        job_id = str(uuid.uuid4())
        progress = await crud.get_job_progress(session=mock_session, job_id=job_id)

        assert progress == mock_progress

    @pytest.mark.asyncio
    async def test_list_jobs_empty(self):
        """Test listing jobs with empty result."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_result

        jobs, total = await crud.list_jobs(session=mock_session)

        assert jobs == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_list_jobs_with_results(self):
        """Test listing jobs with results."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_job1 = MagicMock(spec=ConversionJob)
        mock_job2 = MagicMock(spec=ConversionJob)
        mock_result.scalars.return_value.all.return_value = [mock_job1, mock_job2]
        mock_result.scalar.return_value = 2
        mock_session.execute.return_value = mock_result

        jobs, total = await crud.list_jobs(session=mock_session)

        assert len(jobs) == 2
        assert total == 2

    @pytest.mark.asyncio
    async def test_upsert_progress_alias(self):
        """Test upsert_progress is alias for update_job_progress."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_progress = MagicMock()
        mock_result.scalar_one.return_value = mock_progress
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        job_id = str(uuid.uuid4())
        progress = await crud.upsert_progress(session=mock_session, job_id=job_id, progress=75)

        assert progress == mock_progress


class TestFeedbackCRUD:
    """Test feedback-related CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_enhanced_feedback_success(self):
        """Test creating enhanced feedback."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        job_id = uuid.uuid4()
        feedback = await crud.create_enhanced_feedback(
            session=mock_session,
            job_id=job_id,
            feedback_type="thumbs_up",
            user_id="user123",
            comment="Great!",
            quality_rating=5,
        )

        assert feedback is not None
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_enhanced_feedback_minimal(self):
        """Test creating feedback with minimal data."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        def mock_refresh(feedback):
            feedback.id = uuid.uuid4()
            return None

        mock_session.refresh.side_effect = mock_refresh

        job_id = uuid.uuid4()
        feedback = await crud.create_enhanced_feedback(
            session=mock_session,
            job_id=job_id,
            feedback_type="thumbs_up",
        )

        assert feedback is not None

    @pytest.mark.asyncio
    async def test_get_feedback_success(self):
        """Test getting feedback by ID."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_feedback = MagicMock(spec=ConversionFeedback)
        mock_result.scalar_one_or_none.return_value = mock_feedback
        mock_session.execute.return_value = mock_result

        feedback_id = uuid.uuid4()
        feedback = await crud.get_feedback(session=mock_session, feedback_id=feedback_id)

        assert feedback == mock_feedback

    @pytest.mark.asyncio
    async def test_get_feedback_by_job_id(self):
        """Test getting feedback by job ID."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_feedback1 = MagicMock(spec=ConversionFeedback)
        mock_feedback2 = MagicMock(spec=ConversionFeedback)
        mock_result.scalars.return_value.all.return_value = [mock_feedback1, mock_feedback2]
        mock_session.execute.return_value = mock_result

        job_id = uuid.uuid4()
        feedbacks = await crud.get_feedback_by_job_id(session=mock_session, job_id=job_id)

        assert len(feedbacks) == 2

    @pytest.mark.asyncio
    async def test_list_all_feedback(self):
        """Test listing all feedback."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        feedbacks = await crud.list_all_feedback(session=mock_session)

        assert feedbacks == []


class TestDocumentEmbeddingCRUD:
    """Test document embedding CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_document_embedding(self):
        """Test creating document embedding."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        embedding = [0.1, 0.2, 0.3] * 128  # Mock embedding vector
        doc = await crud.create_document_embedding(
            db=mock_session,
            embedding=embedding,
            document_source="test_source",
            content_hash="abc123",
        )

        assert doc is not None
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_document_embedding_by_id(self):
        """Test getting embedding by ID."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_embedding = MagicMock(spec=DocumentEmbedding)
        mock_result.scalar_one_or_none.return_value = mock_embedding
        mock_session.execute.return_value = mock_result

        embedding_id = uuid.uuid4()
        embedding = await crud.get_document_embedding_by_id(
            db=mock_session, embedding_id=embedding_id
        )

        assert embedding == mock_embedding

    @pytest.mark.asyncio
    async def test_get_document_embedding_by_hash(self):
        """Test getting embedding by hash."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_embedding = MagicMock(spec=DocumentEmbedding)
        mock_result.scalar_one_or_none.return_value = mock_embedding
        mock_session.execute.return_value = mock_result

        embedding = await crud.get_document_embedding_by_hash(
            db=mock_session, content_hash="hash123"
        )

        assert embedding == mock_embedding

    @pytest.mark.asyncio
    async def test_update_document_embedding(self):
        """Test updating document embedding."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_embedding = MagicMock(spec=DocumentEmbedding)
        mock_result.scalar_one_or_none.return_value = mock_embedding
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        embedding_id = uuid.uuid4()
        new_embedding = [0.1, 0.2, 0.3] * 128
        updated = await crud.update_document_embedding(
            db=mock_session,
            embedding_id=embedding_id,
            embedding=new_embedding,
        )

        assert updated == mock_embedding

    @pytest.mark.asyncio
    async def test_update_document_embedding_not_found(self):
        """Test updating non-existent embedding."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        embedding_id = uuid.uuid4()
        updated = await crud.update_document_embedding(
            db=mock_session,
            embedding_id=embedding_id,
            embedding=[0.1],
        )

        assert updated is None

    @pytest.mark.asyncio
    async def test_delete_document_embedding(self):
        """Test deleting document embedding."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_embedding = MagicMock(spec=DocumentEmbedding)
        mock_result.scalar_one_or_none.return_value = mock_embedding
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        embedding_id = uuid.uuid4()
        deleted = await crud.delete_document_embedding(db=mock_session, embedding_id=embedding_id)

        assert deleted is True

    @pytest.mark.asyncio
    async def test_delete_document_embedding_not_found(self):
        """Test deleting non-existent embedding."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        embedding_id = uuid.uuid4()
        deleted = await crud.delete_document_embedding(db=mock_session, embedding_id=embedding_id)

        assert deleted is False


class TestDocumentChunkCRUD:
    """Test document chunk operations."""

    @pytest.mark.asyncio
    async def test_create_document_with_chunks(self):
        """Test creating document with chunks."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        chunks = [
            {"content": "chunk1", "embedding": [0.1] * 384, "content_hash": "hash1"},
            {"content": "chunk2", "embedding": [0.2] * 384, "content_hash": "hash2"},
        ]

        parent, created_chunks = await crud.create_document_with_chunks(
            db=mock_session,
            chunks=chunks,
            document_source="test",
            title="Test Doc",
        )

        assert parent is not None
        assert len(created_chunks) == 2

    @pytest.mark.asyncio
    async def test_get_document_with_chunks(self):
        """Test getting document with chunks."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_parent = MagicMock(spec=DocumentEmbedding)
        mock_chunks = [MagicMock(spec=DocumentEmbedding), MagicMock(spec=DocumentEmbedding)]
        mock_result.scalar_one_or_none.return_value = mock_parent
        mock_result.scalars.return_value.all.return_value = mock_chunks
        mock_session.execute.return_value = mock_result

        document_id = uuid.uuid4()
        parent, chunks = await crud.get_document_with_chunks(
            db=mock_session, document_id=document_id
        )

        assert parent == mock_parent
        assert len(chunks) == 2

    @pytest.mark.asyncio
    async def test_get_chunks_by_parent(self):
        """Test getting chunks by parent ID."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_chunks = [MagicMock(spec=DocumentEmbedding)]
        mock_result.scalars.return_value.all.return_value = mock_chunks
        mock_session.execute.return_value = mock_result

        parent_id = uuid.uuid4()
        chunks = await crud.get_chunks_by_parent(db=mock_session, parent_document_id=parent_id)

        assert len(chunks) == 1

    @pytest.mark.asyncio
    async def test_search_similar_chunks(self):
        """Test searching similar chunks."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_chunks = [MagicMock(spec=DocumentEmbedding)]
        mock_result.scalars.return_value.all.return_value = mock_chunks
        mock_session.execute.return_value = mock_result

        query_embedding = [0.1] * 384
        chunks = await crud.search_similar_chunks(
            db=mock_session, query_embedding=query_embedding, limit=5
        )

        assert len(chunks) == 1

    @pytest.mark.asyncio
    async def test_find_similar_embeddings(self):
        """Test finding similar embeddings."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_embeddings = [MagicMock(spec=DocumentEmbedding)]
        mock_result.scalars.return_value.all.return_value = mock_embeddings
        mock_session.execute.return_value = mock_result

        query_embedding = [0.1] * 384
        embeddings = await crud.find_similar_embeddings(
            db=mock_session, query_embedding=query_embedding
        )

        assert len(embeddings) == 1


class TestExperimentCRUD:
    """Test experiment CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_experiment(self):
        """Test creating experiment."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        experiment = await crud.create_experiment(
            session=mock_session,
            name="Test Experiment",
            description="Test description",
            status="draft",
        )

        assert experiment is not None
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_experiment(self):
        """Test getting experiment by ID."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_experiment = MagicMock(spec=Experiment)
        mock_result.scalar_one_or_none.return_value = mock_experiment
        mock_session.execute.return_value = mock_result

        experiment_id = uuid.uuid4()
        experiment = await crud.get_experiment(session=mock_session, experiment_id=experiment_id)

        assert experiment == mock_experiment

    @pytest.mark.asyncio
    async def test_list_experiments(self):
        """Test listing experiments."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        experiments = await crud.list_experiments(session=mock_session)

        assert experiments == []

    @pytest.mark.asyncio
    async def test_list_experiments_with_status(self):
        """Test listing experiments with status filter."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_experiment = MagicMock(spec=Experiment)
        mock_result.scalars.return_value.all.return_value = [mock_experiment]
        mock_session.execute.return_value = mock_result

        experiments = await crud.list_experiments(session=mock_session, status="active")

        assert len(experiments) == 1

    @pytest.mark.asyncio
    async def test_update_experiment(self):
        """Test updating experiment."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_experiment = MagicMock(spec=Experiment)
        mock_result.scalar_one_or_none.return_value = mock_experiment
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        experiment_id = uuid.uuid4()
        updated = await crud.update_experiment(
            session=mock_session,
            experiment_id=experiment_id,
            name="Updated Name",
        )

        assert updated == mock_experiment

    @pytest.mark.asyncio
    async def test_update_experiment_not_found(self):
        """Test updating non-existent experiment."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        experiment_id = uuid.uuid4()
        updated = await crud.update_experiment(
            session=mock_session,
            experiment_id=experiment_id,
            name="Updated Name",
        )

        assert updated is None

    @pytest.mark.asyncio
    async def test_delete_experiment(self):
        """Test deleting experiment."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_experiment = MagicMock(spec=Experiment)
        mock_result.scalar_one_or_none.return_value = mock_experiment
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        experiment_id = uuid.uuid4()
        deleted = await crud.delete_experiment(session=mock_session, experiment_id=experiment_id)

        assert deleted is True

    @pytest.mark.asyncio
    async def test_delete_experiment_not_found(self):
        """Test deleting non-existent experiment."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        experiment_id = uuid.uuid4()
        deleted = await crud.delete_experiment(session=mock_session, experiment_id=experiment_id)

        assert deleted is False


class TestExperimentVariantCRUD:
    """Test experiment variant CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_experiment_variant(self):
        """Test creating experiment variant."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        experiment_id = uuid.uuid4()
        variant = await crud.create_experiment_variant(
            session=mock_session,
            experiment_id=experiment_id,
            name="Test Variant",
            is_control=False,
        )

        assert variant is not None

    @pytest.mark.asyncio
    async def test_create_experiment_variant_as_control(self):
        """Test creating control variant."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Mock existing control check
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        experiment_id = uuid.uuid4()
        variant = await crud.create_experiment_variant(
            session=mock_session,
            experiment_id=experiment_id,
            name="Control Variant",
            is_control=True,
        )

        assert variant is not None

    @pytest.mark.asyncio
    async def test_get_experiment_variant(self):
        """Test getting experiment variant."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_variant = MagicMock(spec=ExperimentVariant)
        mock_result.scalar_one_or_none.return_value = mock_variant
        mock_session.execute.return_value = mock_result

        variant_id = uuid.uuid4()
        variant = await crud.get_experiment_variant(session=mock_session, variant_id=variant_id)

        assert variant == mock_variant

    @pytest.mark.asyncio
    async def test_list_experiment_variants(self):
        """Test listing experiment variants."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        experiment_id = uuid.uuid4()
        variants = await crud.list_experiment_variants(
            session=mock_session, experiment_id=experiment_id
        )

        assert variants == []

    @pytest.mark.asyncio
    async def test_update_experiment_variant(self):
        """Test updating experiment variant."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_variant = MagicMock(spec=ExperimentVariant)
        mock_variant.is_control = False
        mock_result.scalar_one_or_none.return_value = mock_variant
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        variant_id = uuid.uuid4()
        updated = await crud.update_experiment_variant(
            session=mock_session,
            variant_id=variant_id,
            name="Updated Variant",
        )

        assert updated == mock_variant

    @pytest.mark.asyncio
    async def test_delete_experiment_variant(self):
        """Test deleting experiment variant."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_variant = MagicMock(spec=ExperimentVariant)
        mock_result.scalar_one_or_none.return_value = mock_variant
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        variant_id = uuid.uuid4()
        deleted = await crud.delete_experiment_variant(session=mock_session, variant_id=variant_id)

        assert deleted is True


class TestExperimentResultCRUD:
    """Test experiment result CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_experiment_result(self):
        """Test creating experiment result."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        variant_id = uuid.uuid4()
        session_id = uuid.uuid4()
        result = await crud.create_experiment_result(
            session=mock_session,
            variant_id=variant_id,
            session_id=session_id,
            kpi_quality=0.95,
            kpi_speed=100,
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_experiment_result(self):
        """Test getting experiment result."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_exp_result = MagicMock(spec=ExperimentResult)
        mock_result.scalar_one_or_none.return_value = mock_exp_result
        mock_session.execute.return_value = mock_result

        result_id = uuid.uuid4()
        result = await crud.get_experiment_result(session=mock_session, result_id=result_id)

        assert result == mock_exp_result

    @pytest.mark.asyncio
    async def test_list_experiment_results(self):
        """Test listing experiment results."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        results = await crud.list_experiment_results(session=mock_session)

        assert results == []


class TestBehaviorFileCRUD:
    """Test behavior file CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_behavior_file(self):
        """Test creating behavior file."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        conversion_id = str(uuid.uuid4())
        behavior_file = await crud.create_behavior_file(
            session=mock_session,
            conversion_id=conversion_id,
            file_path="blocks/test.json",
            file_type="json",
            content='{"test": true}',
        )

        assert behavior_file is not None

    @pytest.mark.asyncio
    async def test_create_behavior_file_invalid_conversion_id(self):
        """Test creating behavior file with invalid conversion ID."""
        mock_session = AsyncMock(spec=AsyncSession)

        with pytest.raises(ValueError):
            await crud.create_behavior_file(
                session=mock_session,
                conversion_id="invalid",
                file_path="test.json",
                file_type="json",
                content="{}",
            )

    @pytest.mark.asyncio
    async def test_create_behavior_file_path_traversal(self):
        """Test creating behavior file with path traversal."""
        mock_session = AsyncMock(spec=AsyncSession)
        conversion_id = str(uuid.uuid4())

        with pytest.raises(ValueError, match="path traversal"):
            await crud.create_behavior_file(
                session=mock_session,
                conversion_id=conversion_id,
                file_path="../etc/passwd",
                file_type="json",
                content="{}",
            )

    @pytest.mark.asyncio
    async def test_create_behavior_file_absolute_path(self):
        """Test creating behavior file with absolute path."""
        mock_session = AsyncMock(spec=AsyncSession)
        conversion_id = str(uuid.uuid4())

        with pytest.raises(ValueError, match="absolute path"):
            await crud.create_behavior_file(
                session=mock_session,
                conversion_id=conversion_id,
                file_path="/absolute/path.json",
                file_type="json",
                content="{}",
            )

    @pytest.mark.asyncio
    async def test_get_behavior_file(self):
        """Test getting behavior file."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_file = MagicMock(spec=BehaviorFile)
        mock_result.scalar_one_or_none.return_value = mock_file
        mock_session.execute.return_value = mock_result

        file_id = str(uuid.uuid4())
        behavior_file = await crud.get_behavior_file(session=mock_session, file_id=file_id)

        assert behavior_file == mock_file

    @pytest.mark.asyncio
    async def test_get_behavior_file_invalid_id(self):
        """Test getting behavior file with invalid ID."""
        mock_session = AsyncMock(spec=AsyncSession)

        result = await crud.get_behavior_file(session=mock_session, file_id="invalid")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_behavior_files_by_conversion(self):
        """Test getting behavior files by conversion."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        conversion_id = str(uuid.uuid4())
        files = await crud.get_behavior_files_by_conversion(
            session=mock_session, conversion_id=conversion_id
        )

        assert files == []

    @pytest.mark.asyncio
    async def test_get_behavior_files_by_conversion_invalid_id(self):
        """Test getting behavior files with invalid conversion ID."""
        mock_session = AsyncMock(spec=AsyncSession)

        files = await crud.get_behavior_files_by_conversion(
            session=mock_session, conversion_id="invalid"
        )

        assert files == []

    @pytest.mark.asyncio
    async def test_update_behavior_file_content(self):
        """Test updating behavior file content."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_file = MagicMock(spec=BehaviorFile)
        mock_result.scalar_one_or_none.return_value = mock_file
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        file_id = str(uuid.uuid4())
        updated = await crud.update_behavior_file_content(
            session=mock_session,
            file_id=file_id,
            content='{"updated": true}',
        )

        assert updated == mock_file

    @pytest.mark.asyncio
    async def test_update_behavior_file_content_invalid_id(self):
        """Test updating behavior file with invalid ID."""
        mock_session = AsyncMock(spec=AsyncSession)

        updated = await crud.update_behavior_file_content(
            session=mock_session,
            file_id="invalid",
            content="{}",
        )

        assert updated is None

    @pytest.mark.asyncio
    async def test_delete_behavior_file(self):
        """Test deleting behavior file."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_file = MagicMock(spec=BehaviorFile)
        mock_result.scalar_one_or_none.return_value = mock_file
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        file_id = str(uuid.uuid4())
        deleted = await crud.delete_behavior_file(session=mock_session, file_id=file_id)

        assert deleted is True

    @pytest.mark.asyncio
    async def test_delete_behavior_file_not_found(self):
        """Test deleting non-existent behavior file."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        file_id = str(uuid.uuid4())
        deleted = await crud.delete_behavior_file(session=mock_session, file_id=file_id)

        assert deleted is False

    @pytest.mark.asyncio
    async def test_get_behavior_files_by_type(self):
        """Test getting behavior files by type."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        conversion_id = str(uuid.uuid4())
        files = await crud.get_behavior_files_by_type(
            session=mock_session,
            conversion_id=conversion_id,
            file_type="json",
        )

        assert files == []


class TestAddonAssetCRUD:
    """Test addon asset CRUD operations."""

    @pytest.mark.asyncio
    async def test_get_addon_asset(self):
        """Test getting addon asset."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_asset = MagicMock(spec=AddonAsset)
        mock_result.scalar_one_or_none.return_value = mock_asset
        mock_session.execute.return_value = mock_result

        asset_id = str(uuid.uuid4())
        asset = await crud.get_addon_asset(session=mock_session, asset_id=asset_id)

        assert asset == mock_asset

    @pytest.mark.asyncio
    async def test_get_addon_asset_invalid_id(self):
        """Test getting addon asset with invalid ID."""
        mock_session = AsyncMock(spec=AsyncSession)

        with pytest.raises(ValueError):
            await crud.get_addon_asset(session=mock_session, asset_id="invalid")

    @pytest.mark.asyncio
    async def test_create_addon_asset(self):
        """Test creating addon asset."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        addon_id = str(uuid.uuid4())
        asset = await crud.create_addon_asset(
            session=mock_session,
            addon_id=addon_id,
            asset_type="texture",
            file_path="textures/test.png",
            original_filename="test.png",
        )

        assert asset is not None

    @pytest.mark.asyncio
    async def test_create_addon_asset_invalid_addon_id(self):
        """Test creating addon asset with invalid addon ID."""
        mock_session = AsyncMock(spec=AsyncSession)

        with pytest.raises(ValueError):
            await crud.create_addon_asset(
                session=mock_session,
                addon_id="invalid",
                asset_type="texture",
                file_path="test.png",
                original_filename="test.png",
            )

    @pytest.mark.asyncio
    async def test_create_addon_asset_path_traversal(self):
        """Test creating addon asset with path traversal."""
        mock_session = AsyncMock(spec=AsyncSession)
        addon_id = str(uuid.uuid4())

        with pytest.raises(ValueError, match="path traversal"):
            await crud.create_addon_asset(
                session=mock_session,
                addon_id=addon_id,
                asset_type="texture",
                file_path="../etc/passwd",
                original_filename="test.png",
            )

    @pytest.mark.asyncio
    async def test_update_addon_asset(self):
        """Test updating addon asset."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_asset = MagicMock(spec=AddonAsset)
        mock_result.scalar_one_or_none.return_value = mock_asset
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        asset_id = str(uuid.uuid4())
        updated = await crud.update_addon_asset(
            session=mock_session,
            asset_id=asset_id,
            asset_type="model",
        )

        assert updated == mock_asset

    @pytest.mark.asyncio
    async def test_delete_addon_asset(self):
        """Test deleting addon asset."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_asset = MagicMock(spec=AddonAsset)
        mock_result.scalar_one_or_none.return_value = mock_asset
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        asset_id = str(uuid.uuid4())
        deleted = await crud.delete_addon_asset(session=mock_session, asset_id=asset_id)

        assert deleted is True

    @pytest.mark.asyncio
    async def test_list_addon_assets(self):
        """Test listing addon assets."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        addon_id = str(uuid.uuid4())
        assets = await crud.list_addon_assets(session=mock_session, addon_id=addon_id)

        assert assets == []


class TestAssetCRUD:
    """Test asset CRUD operations."""

    @pytest.mark.asyncio
    async def test_get_asset(self):
        """Test getting asset."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_asset = MagicMock(spec=Asset)
        mock_result.scalar_one_or_none.return_value = mock_asset
        mock_session.execute.return_value = mock_result

        asset_id = str(uuid.uuid4())
        asset = await crud.get_asset(session=mock_session, asset_id=asset_id)

        assert asset == mock_asset

    @pytest.mark.asyncio
    async def test_create_asset(self):
        """Test creating asset."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        conversion_id = str(uuid.uuid4())
        asset = await crud.create_asset(
            session=mock_session,
            conversion_id=conversion_id,
            asset_type="texture",
            original_path="/path/to/texture.png",
            original_filename="texture.png",
        )

        assert asset is not None

    @pytest.mark.asyncio
    async def test_update_asset_status(self):
        """Test updating asset status."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_asset = MagicMock(spec=Asset)
        mock_result.scalar_one_or_none.return_value = mock_asset
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        asset_id = str(uuid.uuid4())
        updated = await crud.update_asset_status(
            session=mock_session,
            asset_id=asset_id,
            status="completed",
        )

        assert updated == mock_asset

    @pytest.mark.asyncio
    async def test_update_asset_metadata(self):
        """Test updating asset metadata."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_asset = MagicMock(spec=Asset)
        mock_result.scalar_one_or_none.return_value = mock_asset
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        asset_id = str(uuid.uuid4())
        updated = await crud.update_asset_metadata(
            session=mock_session,
            asset_id=asset_id,
            asset_metadata={"key": "value"},
        )

        assert updated == mock_asset

    @pytest.mark.asyncio
    async def test_delete_asset(self):
        """Test deleting asset."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_asset = MagicMock(spec=Asset)
        mock_result.scalar_one_or_none.return_value = mock_asset
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        asset_id = str(uuid.uuid4())
        deleted = await crud.delete_asset(session=mock_session, asset_id=asset_id)

        assert deleted is True

    @pytest.mark.asyncio
    async def test_list_assets_for_conversion(self):
        """Test listing assets for conversion."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        conversion_id = str(uuid.uuid4())
        assets = await crud.list_assets_for_conversion(
            session=mock_session, conversion_id=conversion_id
        )

        assert assets == []


class TestPatternSubmissionCRUD:
    """Test pattern submission CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_pattern_submission(self):
        """Test creating pattern submission."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        submission = await crud.create_pattern_submission(
            session=mock_session,
            java_pattern="public class Test {}",
            bedrock_pattern="export class Test {}",
            description="Test pattern",
            contributor_id="user123",
            tags=["test"],
            category="class",
        )

        assert submission is not None

    @pytest.mark.asyncio
    async def test_get_pattern_submission(self):
        """Test getting pattern submission."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_submission = MagicMock(spec=PatternSubmission)
        mock_result.scalar_one_or_none.return_value = mock_submission
        mock_session.execute.return_value = mock_result

        submission_id = str(uuid.uuid4())
        submission = await crud.get_pattern_submission(
            session=mock_session, submission_id=submission_id
        )

        assert submission == mock_submission

    @pytest.mark.asyncio
    async def test_get_pattern_submission_invalid_id(self):
        """Test getting pattern submission with invalid ID."""
        mock_session = AsyncMock(spec=AsyncSession)

        with pytest.raises(ValueError):
            await crud.get_pattern_submission(session=mock_session, submission_id="invalid")

    @pytest.mark.asyncio
    async def test_get_pending_submissions(self):
        """Test getting pending submissions."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        submissions = await crud.get_pending_submissions(session=mock_session)

        assert submissions == []

    @pytest.mark.asyncio
    async def test_update_pattern_submission_status(self):
        """Test updating pattern submission status."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_submission = MagicMock(spec=PatternSubmission)
        mock_result.scalar_one_or_none.return_value = mock_submission
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        submission_id = str(uuid.uuid4())
        updated = await crud.update_pattern_submission_status(
            session=mock_session,
            submission_id=submission_id,
            status="approved",
            reviewed_by="admin",
            notes="Looks good",
        )

        assert updated == mock_submission

    @pytest.mark.asyncio
    async def test_update_pattern_submission_not_found(self):
        """Test updating non-existent pattern submission."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        submission_id = str(uuid.uuid4())

        with pytest.raises(ValueError):
            await crud.update_pattern_submission_status(
                session=mock_session,
                submission_id=submission_id,
                status="approved",
                reviewed_by="admin",
            )

    @pytest.mark.asyncio
    async def test_vote_on_pattern_upvote(self):
        """Test upvoting pattern."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_submission = MagicMock(spec=PatternSubmission)
        mock_submission.upvotes = 0
        mock_result.scalar_one_or_none.return_value = mock_submission
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        submission_id = str(uuid.uuid4())
        updated = await crud.vote_on_pattern(
            session=mock_session,
            submission_id=submission_id,
            upvote=True,
        )

        assert updated.upvotes == 1

    @pytest.mark.asyncio
    async def test_vote_on_pattern_downvote(self):
        """Test downvoting pattern."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_submission = MagicMock(spec=PatternSubmission)
        mock_submission.downvotes = 0
        mock_result.scalar_one_or_none.return_value = mock_submission
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        submission_id = str(uuid.uuid4())
        updated = await crud.vote_on_pattern(
            session=mock_session,
            submission_id=submission_id,
            upvote=False,
        )

        assert updated.downvotes == 1
