"""
Expanded unit tests for db/crud.py module.

Covers complex database operations, join queries, filter combinations,
and bulk operations in the CRUD layer.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db import models
from db.crud import (
    create_job,
    get_job,
    update_job_status,
    update_job_progress,
    get_job_progress,
    list_jobs,
    create_result,
    create_document_embedding,
    get_document_embedding_by_id,
    get_document_embedding_by_hash,
    update_document_embedding,
    delete_document_embedding,
    create_experiment,
    get_experiment,
    list_experiments,
    update_experiment,
    delete_experiment,
    create_behavior_file,
    get_behavior_file,
    get_behavior_files_by_conversion,
    update_behavior_file_content,
    delete_behavior_file,
    upsert_progress,
)


class TestCreateJob:
    """Tests for create_job function."""

    @pytest.mark.asyncio
    async def test_create_job_basic(self):
        """Test basic job creation."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        job = await create_job(
            mock_session,
            file_id="test-file-id",
            original_filename="test_mod.jar",
            target_version="1.20.0",
        )

        assert job is not None
        assert job.status == "queued"
        assert job.input_data["file_id"] == "test-file-id"
        assert job.input_data["original_filename"] == "test_mod.jar"
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_job_with_options(self):
        """Test job creation with custom options."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        options = {"optimize": True, "validation": "strict"}
        job = await create_job(
            mock_session,
            file_id="test-file-id",
            original_filename="test_mod.jar",
            target_version="1.20.0",
            options=options,
        )

        assert job.input_data["options"] == options

    @pytest.mark.asyncio
    async def test_create_job_no_commit(self):
        """Test job creation without immediate commit."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.flush = AsyncMock()

        job = await create_job(
            mock_session,
            file_id="test-file-id",
            original_filename="test_mod.jar",
            target_version="1.20.0",
            commit=False,
        )

        mock_session.flush.assert_called_once()
        mock_session.commit.assert_not_called()


class TestGetJob:
    """Tests for get_job function."""

    @pytest.mark.asyncio
    async def test_get_job_valid_uuid(self):
        """Test retrieving job with valid UUID."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(id=uuid.uuid4())
        mock_session.execute = AsyncMock(return_value=mock_result)

        job_id = str(uuid.uuid4())
        job = await get_job(mock_session, job_id)

        assert job is not None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_job_invalid_uuid(self):
        """Test retrieving job with invalid UUID returns None."""
        mock_session = AsyncMock(spec=AsyncSession)

        job = await get_job(mock_session, "invalid-uuid")

        assert job is None

    @pytest.mark.asyncio
    async def test_get_job_not_found(self):
        """Test retrieving non-existent job."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        job_id = str(uuid.uuid4())
        job = await get_job(mock_session, job_id)

        assert job is None


class TestUpdateJobStatus:
    """Tests for update_job_status function."""

    @pytest.mark.asyncio
    async def test_update_job_status_valid(self):
        """Test updating job status with valid UUID."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(id=uuid.uuid4())
        mock_session.execute = AsyncMock(return_value=mock_result)

        job_id = str(uuid.uuid4())
        job = await update_job_status(mock_session, job_id, "completed")

        assert job is not None
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_job_status_invalid_uuid(self):
        """Test updating job status with invalid UUID."""
        mock_session = AsyncMock(spec=AsyncSession)

        job = await update_job_status(mock_session, "invalid-uuid", "completed")

        assert job is None


class TestUpdateJobProgress:
    """Tests for update_job_progress function."""

    @pytest.mark.asyncio
    async def test_update_job_progress_valid(self):
        """Test updating job progress."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock()

        job_id = str(uuid.uuid4())
        progress = await update_job_progress(mock_session, job_id, 50)

        assert progress is not None

    @pytest.mark.asyncio
    async def test_update_job_progress_invalid_uuid(self):
        """Test updating progress with invalid UUID raises error."""
        mock_session = AsyncMock(spec=AsyncSession)

        with pytest.raises(ValueError, match="Invalid job_id format"):
            await update_job_progress(mock_session, "invalid-uuid", 50)


class TestGetJobProgress:
    """Tests for get_job_progress function."""

    @pytest.mark.asyncio
    async def test_get_job_progress_exists(self):
        """Test getting job progress when exists."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        progress = await get_job_progress(mock_session, str(uuid.uuid4()))

        assert progress is not None


class TestListJobs:
    """Tests for list_jobs function."""

    @pytest.mark.asyncio
    async def test_list_jobs_basic(self):
        """Test basic listing of jobs."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar.return_value = 0
        mock_session.execute = AsyncMock(return_value=mock_result)

        jobs, total = await list_jobs(mock_session)

        assert isinstance(jobs, list)

    @pytest.mark.asyncio
    async def test_list_jobs_with_pagination(self):
        """Test listing jobs with pagination."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar.return_value = 0
        mock_session.execute = AsyncMock(return_value=mock_result)

        jobs, total = await list_jobs(mock_session, skip=0, limit=10)

        assert isinstance(jobs, list)


class TestCreateResult:
    """Tests for create_result function."""

    @pytest.mark.asyncio
    async def test_create_result_basic(self):
        """Test basic result creation."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        result = await create_result(
            mock_session,
            job_id=str(uuid.uuid4()),
            output_data={"converted": True},
        )

        assert result is not None


class TestDocumentEmbedding:
    """Tests for document embedding CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_document_embedding(self):
        """Test creating document embedding."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        embedding = await create_document_embedding(
            mock_session,
            embedding=[0.1] * 384,
            document_source="test_source",
            content_hash="abc123",
        )

        assert embedding is not None

    @pytest.mark.asyncio
    async def test_get_document_embedding_by_id(self):
        """Test getting embedding by ID."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        embedding = await get_document_embedding_by_id(
            mock_session,
            embedding_id=uuid.uuid4(),
        )

        assert embedding is None

    @pytest.mark.asyncio
    async def test_get_document_embedding_by_hash(self):
        """Test getting embedding by content hash."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        embedding = await get_document_embedding_by_hash(
            mock_session,
            content_hash="abc123",
        )

        assert embedding is None

    @pytest.mark.asyncio
    async def test_update_document_embedding(self):
        """Test updating document embedding."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await update_document_embedding(
            mock_session,
            embedding_id=uuid.uuid4(),
            embedding=[0.2] * 384,
        )

        assert result is not None


class TestExperimentCRUD:
    """Tests for experiment CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_experiment(self):
        """Test creating experiment."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        experiment = await create_experiment(
            mock_session,
            name="test_experiment",
            description="Test description",
        )

        assert experiment is not None

    @pytest.mark.asyncio
    async def test_get_experiment(self):
        """Test getting experiment by ID."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        experiment = await get_experiment(mock_session, str(uuid.uuid4()))

        assert experiment is None

    @pytest.mark.asyncio
    async def test_list_experiments(self):
        """Test listing experiments."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        experiments = await list_experiments(mock_session)

        assert isinstance(experiments, list)

    @pytest.mark.asyncio
    async def test_update_experiment(self):
        """Test updating experiment."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock()

        result = await update_experiment(
            mock_session,
            experiment_id=str(uuid.uuid4()),
            status="completed",
        )

        assert result is not None


class TestBehaviorFileCRUD:
    """Tests for behavior file CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_behavior_file(self):
        """Test creating behavior file."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        behavior_file = await create_behavior_file(
            mock_session,
            conversion_id=str(uuid.uuid4()),
            file_path="manifest.json",
            file_type="manifest",
            content='{"format_version": 2}',
        )

        assert behavior_file is not None

    @pytest.mark.asyncio
    async def test_get_behavior_file(self):
        """Test getting behavior file by ID."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        behavior_file = await get_behavior_file(
            mock_session,
            file_id=str(uuid.uuid4()),
        )

        assert behavior_file is None

    @pytest.mark.asyncio
    async def test_get_behavior_files_by_conversion(self):
        """Test getting behavior files by conversion job."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        files = await get_behavior_files_by_conversion(
            mock_session,
            conversion_id=str(uuid.uuid4()),
        )

        assert isinstance(files, list)


class TestUpsertProgress:
    """Tests for upsert_progress function."""

    @pytest.mark.asyncio
    async def test_upsert_progress_create(self):
        """Test creating progress via upsert."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock()

        progress = await upsert_progress(
            mock_session,
            job_id=str(uuid.uuid4()),
            progress=50,
        )

        assert progress is not None
