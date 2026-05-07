import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import status
from fastapi.testclient import TestClient
from fastapi import FastAPI

from api.feedback import router, submit_issue_report, IssueReportRequest


app = FastAPI()
app.include_router(router)


@pytest.fixture
def mock_db():
    mock = AsyncMock()
    mock.commit = AsyncMock()
    mock.refresh = AsyncMock()
    mock.add = MagicMock()
    return mock


@pytest.fixture
def mock_job():
    job = MagicMock()
    job.id = uuid.uuid4()
    job.status = "completed"
    return job


class TestSubmitIssueReport:
    """Tests for POST /feedback/issues endpoint"""

    def test_issue_report_request_model_valid(self):
        """Test IssueReportRequest model validation"""
        request = IssueReportRequest(
            job_id=str(uuid.uuid4()),
            mod_name="Test Mod",
            version="1.0.0",
            conversion_score=75.5,
            failing_categories=["Custom Rendering"],
            description="Test description",
            severity="high",
            contact_email="test@example.com",
        )
        assert request.job_id is not None
        assert request.mod_name == "Test Mod"
        assert request.severity == "high"

    def test_issue_report_request_model_defaults(self):
        """Test IssueReportRequest with default values"""
        request = IssueReportRequest(
            job_id=str(uuid.uuid4()),
            mod_name="Test Mod",
            version="1.0.0",
            conversion_score=50.0,
            description="Test description",
        )
        assert request.severity == "medium"
        assert request.contact_email is None
        assert request.failing_categories == []

    @pytest.mark.asyncio
    async def test_submit_issue_report_success(self, mock_db, mock_job):
        """Test successful issue report submission"""
        with patch("api.feedback.crud.get_job", new_callable=AsyncMock) as mock_get_job:
            mock_get_job.return_value = mock_job

            report = IssueReportRequest(
                job_id=str(uuid.uuid4()),
                mod_name="My Awesome Mod",
                version="3.2.1",
                conversion_score=72.5,
                failing_categories=["Custom Rendering", "Network Packets"],
                description="Entities are not spawning correctly in Bedrock edition.",
                severity="high",
            )

            result = await submit_issue_report(report, mock_db)

            assert (
                result.message == "Thank you for your report! Our team will investigate this issue."
            )
            assert result.severity == "high"
            assert result.report_id is not None
            assert result.expected_response_time == "< 24 hours"
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_issue_report_invalid_job_id(self, mock_db):
        """Test issue report with invalid job ID format"""
        report = IssueReportRequest(
            job_id="not-a-valid-uuid",
            mod_name="Test Mod",
            version="1.0.0",
            conversion_score=50.0,
            description="Test description",
        )

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await submit_issue_report(report, mock_db)
        assert exc_info.value.status_code == 400
        assert "Invalid job ID format" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_submit_issue_report_invalid_severity(self, mock_db):
        """Test issue report with invalid severity"""
        report = IssueReportRequest(
            job_id=str(uuid.uuid4()),
            mod_name="Test Mod",
            version="1.0.0",
            conversion_score=50.0,
            description="Test description",
            severity="invalid",
        )

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await submit_issue_report(report, mock_db)
        assert exc_info.value.status_code == 400
        assert "Invalid severity" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_submit_issue_report_job_not_found(self, mock_db):
        """Test issue report when job does not exist"""
        with patch("api.feedback.crud.get_job", new_callable=AsyncMock) as mock_get_job:
            mock_get_job.return_value = None

            report = IssueReportRequest(
                job_id=str(uuid.uuid4()),
                mod_name="Test Mod",
                version="1.0.0",
                conversion_score=50.0,
                description="Test description",
            )

            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await submit_issue_report(report, mock_db)
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_submit_issue_report_critical_severity(self, mock_db, mock_job):
        """Test issue report with critical severity"""
        with patch("api.feedback.crud.get_job", new_callable=AsyncMock) as mock_get_job:
            mock_get_job.return_value = mock_job

            report = IssueReportRequest(
                job_id=str(uuid.uuid4()),
                mod_name="Critical Mod",
                version="1.0.0",
                conversion_score=10.0,
                failing_categories=["Everything"],
                description="Everything is broken",
                severity="critical",
            )

            result = await submit_issue_report(report, mock_db)

            assert result.severity == "critical"
            assert result.expected_response_time == "< 2 hours"

    @pytest.mark.asyncio
    async def test_submit_issue_report_low_severity(self, mock_db, mock_job):
        """Test issue report with low severity"""
        with patch("api.feedback.crud.get_job", new_callable=AsyncMock) as mock_get_job:
            mock_get_job.return_value = mock_job

            report = IssueReportRequest(
                job_id=str(uuid.uuid4()),
                mod_name="Minor Mod",
                version="1.0.0",
                conversion_score=95.0,
                failing_categories=["Minor UI glitch"],
                description="Minor UI glitch, not critical",
                severity="low",
            )

            result = await submit_issue_report(report, mock_db)

            assert result.severity == "low"
            assert result.expected_response_time == "< 1 week"

    @pytest.mark.asyncio
    async def test_submit_issue_report_without_contact(self, mock_db, mock_job):
        """Test issue report without contact email"""
        with patch("api.feedback.crud.get_job", new_callable=AsyncMock) as mock_get_job:
            mock_get_job.return_value = mock_job

            report = IssueReportRequest(
                job_id=str(uuid.uuid4()),
                mod_name="Anonymous Mod",
                version="2.0.0",
                conversion_score=60.0,
                failing_categories=["Unknown"],
                description="Issue without contact",
            )

            result = await submit_issue_report(report, mock_db)

            assert result.message is not None
            assert result.report_id is not None
            assert result.expected_response_time == "< 3 days"

    @pytest.mark.asyncio
    async def test_submit_issue_report_empty_failing_categories(self, mock_db, mock_job):
        """Test issue report with empty failing categories"""
        with patch("api.feedback.crud.get_job", new_callable=AsyncMock) as mock_get_job:
            mock_get_job.return_value = mock_job

            report = IssueReportRequest(
                job_id=str(uuid.uuid4()),
                mod_name="Clean Mod",
                version="1.0.0",
                conversion_score=100.0,
                failing_categories=[],
                description="Perfect conversion except something minor",
                severity="low",
            )

            result = await submit_issue_report(report, mock_db)

            assert result.report_id is not None
