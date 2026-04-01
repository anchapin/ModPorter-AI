"""
Tests for Conversion Failure Analysis - src/services/conversion_failure_analysis.py
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from services.conversion_failure_analysis import (
    FailureSeverity,
    FailureSource,
    FailureDetail,
    ConversionFailure,
    determine_failure_severity,
    determine_failure_source,
    log_conversion_failure,
    log_retry_success,
    log_retry_failure,
    RECOVERY_SUGGESTIONS,
)


class TestEnums:
    """Tests for enum types."""

    def test_failure_severity_values(self):
        """Test FailureSeverity enum values."""
        assert FailureSeverity.LOW.value == "low"
        assert FailureSeverity.MEDIUM.value == "medium"
        assert FailureSeverity.HIGH.value == "high"
        assert FailureSeverity.CRITICAL.value == "critical"

    def test_failure_source_values(self):
        """Test FailureSource enum values."""
        assert FailureSource.FILE_UPLOAD.value == "file_upload"
        assert FailureSource.FILE_PARSING.value == "file_parsing"
        assert FailureSource.MOD_ANALYSIS.value == "mod_analysis"
        assert FailureSource.ASSET_CONVERSION.value == "asset_conversion"
        assert FailureSource.CODE_TRANSLATION.value == "code_translation"
        assert FailureSource.PACKAGING.value == "packaging"
        assert FailureSource.VALIDATION.value == "validation"
        assert FailureSource.UNKNOWN.value == "unknown"


class TestDetermineFailureSeverity:
    """Tests for determine_failure_severity function."""

    def test_critical_with_high_retry_count(self):
        """Test critical severity with high retry count."""
        result = determine_failure_severity("logic_error", retry_count=3)
        assert result == FailureSeverity.CRITICAL

    def test_critical_category_with_retry(self):
        """Test critical category with any retry count >= 1."""
        result = determine_failure_severity("package_error", retry_count=1)
        assert result == FailureSeverity.CRITICAL

    def test_critical_category_no_retry(self):
        """Test critical category without retry."""
        result = determine_failure_severity("package_error", retry_count=0)
        assert result == FailureSeverity.HIGH

    def test_high_category_with_retry(self):
        """Test high category with retry."""
        result = determine_failure_severity("parse_error", retry_count=1)
        assert result == FailureSeverity.HIGH

    def test_high_category_no_retry(self):
        """Test high category without retry."""
        result = determine_failure_severity("parse_error", retry_count=0)
        assert result == FailureSeverity.MEDIUM

    def test_medium_category(self):
        """Test medium category."""
        result = determine_failure_severity("validation_error", retry_count=0)
        assert result == FailureSeverity.MEDIUM

    def test_network_error_medium(self):
        """Test network error is medium severity."""
        result = determine_failure_severity("network_error", retry_count=0)
        assert result == FailureSeverity.MEDIUM

    def test_unknown_category_low(self):
        """Test unknown category defaults to low."""
        result = determine_failure_severity("some_unknown_error", retry_count=0)
        assert result == FailureSeverity.LOW

    def test_asset_error_high(self):
        """Test asset error is high severity."""
        result = determine_failure_severity("asset_error", retry_count=1)
        assert result == FailureSeverity.HIGH


class TestDetermineFailureSource:
    """Tests for determine_failure_source function."""

    def test_file_upload(self):
        """Test file upload source detection."""
        result = determine_failure_source("file_upload")
        assert result == FailureSource.FILE_UPLOAD

    def test_file_upload_variation(self):
        """Test file upload with variation."""
        result = determine_failure_source("during_upload")
        assert result == FailureSource.FILE_UPLOAD

    def test_file_parsing(self):
        """Test file parsing source detection."""
        result = determine_failure_source("parsing")
        assert result == FailureSource.FILE_PARSING

    def test_parsing_variation(self):
        """Test parsing variation."""
        result = determine_failure_source("java_parsing_stage")
        assert result == FailureSource.FILE_PARSING

    def test_mod_analysis(self):
        """Test mod analysis source detection."""
        result = determine_failure_source("mod_analysis")
        assert result == FailureSource.MOD_ANALYSIS

    def test_analysis_variation(self):
        """Test analysis variation."""
        result = determine_failure_source("analyze_mods")
        assert result == FailureSource.MOD_ANALYSIS

    def test_asset_conversion(self):
        """Test asset conversion source detection."""
        result = determine_failure_source("asset_conversion")
        assert result == FailureSource.ASSET_CONVERSION

    def test_asset_variation(self):
        """Test asset variation."""
        result = determine_failure_source("converting_assets")
        assert result == FailureSource.ASSET_CONVERSION

    def test_code_translation(self):
        """Test code translation source detection."""
        result = determine_failure_source("code_translation")
        assert result == FailureSource.CODE_TRANSLATION

    def test_translate_variation(self):
        """Test translate variation."""
        result = determine_failure_source("translating_code")
        assert result == FailureSource.CODE_TRANSLATION

    def test_convert_variation(self):
        """Test convert variation."""
        result = determine_failure_source("converting_java")
        assert result == FailureSource.CODE_TRANSLATION

    def test_packaging(self):
        """Test packaging source detection."""
        result = determine_failure_source("packaging")
        assert result == FailureSource.PACKAGING

    def test_pack_variation(self):
        """Test pack variation."""
        result = determine_failure_source("creating_package")
        assert result == FailureSource.PACKAGING

    def test_validation(self):
        """Test validation source detection."""
        result = determine_failure_source("validation")
        assert result == FailureSource.VALIDATION

    def test_valid_variation(self):
        """Test valid variation."""
        result = determine_failure_source("running_validation")
        assert result == FailureSource.VALIDATION

    def test_unknown_source(self):
        """Test unknown source."""
        result = determine_failure_source("random_stage")
        assert result == FailureSource.UNKNOWN

    def test_none_stage(self):
        """Test None stage returns unknown."""
        result = determine_failure_source(None)
        assert result == FailureSource.UNKNOWN


class TestConversionFailure:
    """Tests for ConversionFailure dataclass."""

    def test_init(self):
        """Test ConversionFailure initialization."""
        failure = ConversionFailure(
            job_id="job-123",
            correlation_id="corr-456",
            timestamp="2024-01-01T00:00:00Z",
            failure_severity="high",
            failure_source="parsing",
            failure_summary="Parse error in line 50",
            user_message="Could not parse the file",
        )

        assert failure.job_id == "job-123"
        assert failure.correlation_id == "corr-456"
        assert failure.failure_severity == "high"
        assert failure.failure_source == "parsing"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        failure = ConversionFailure(
            job_id="job-123",
            correlation_id="corr-456",
            timestamp="2024-01-01T00:00:00Z",
            failure_severity="high",
            failure_source="parsing",
            failure_summary="Error",
            user_message="Message",
            retry_count=2,
        )

        result = failure.to_dict()

        assert result["job_id"] == "job-123"
        assert result["retry_count"] == 2
        assert "failure_details" in result

    def test_to_dict_with_details(self):
        """Test to_dict with failure details."""
        detail = FailureDetail(
            error_type="SyntaxError", error_message="Unexpected token", error_category="parse_error"
        )

        failure = ConversionFailure(
            job_id="job-123",
            correlation_id="corr-456",
            timestamp="2024-01-01T00:00:00Z",
            failure_severity="high",
            failure_source="parsing",
            failure_summary="Error",
            user_message="Message",
            failure_details=[detail],
        )

        result = failure.to_dict()

        assert len(result["failure_details"]) == 1
        assert result["failure_details"][0]["error_type"] == "SyntaxError"


class TestLogConversionFailure:
    """Tests for log_conversion_failure function."""

    def test_basic_logging(self):
        """Test basic failure logging."""
        with patch("services.conversion_failure_analysis.get_correlation_id", return_value=None):
            with patch(
                "services.conversion_failure_analysis.set_correlation_id", return_value="test-corr"
            ):
                with patch("services.conversion_failure_analysis._log_failure"):
                    failure = log_conversion_failure(
                        job_id="job-123",
                        error=ValueError("Test error"),
                        error_category="parse_error",
                    )

                    assert failure.job_id == "job-123"
                    assert failure.failure_summary is not None

    def test_logging_with_all_params(self):
        """Test logging with all parameters."""
        with patch(
            "services.conversion_failure_analysis.get_correlation_id", return_value="existing-corr"
        ):
            with patch("services.conversion_failure_analysis._log_failure"):
                failure = log_conversion_failure(
                    job_id="job-123",
                    error=ValueError("Test error"),
                    error_category="asset_error",
                    conversion_stage="converting_assets",
                    mod_type="forge_mod",
                    target_version="1.20.0",
                    retry_count=2,
                    additional_context={"key": "value"},
                )

                assert failure.mod_type == "forge_mod"
                assert failure.target_version == "1.20.0"
                assert failure.retry_count == 2

    def test_recovery_suggestions(self):
        """Test recovery suggestions are included."""
        with patch("services.conversion_failure_analysis.get_correlation_id", return_value=None):
            with patch(
                "services.conversion_failure_analysis.set_correlation_id", return_value="test"
            ):
                with patch("services.conversion_failure_analysis._log_failure"):
                    failure = log_conversion_failure(
                        job_id="job-123", error=ValueError("Error"), error_category="parse_error"
                    )

                    assert len(failure.recovery_suggestions) > 0

    def test_user_message_generated(self):
        """Test user message is generated."""
        with patch("services.conversion_failure_analysis.get_correlation_id", return_value=None):
            with patch(
                "services.conversion_failure_analysis.set_correlation_id", return_value="test"
            ):
                with patch("services.conversion_failure_analysis._log_failure"):
                    failure = log_conversion_failure(
                        job_id="job-123", error=ValueError("Error"), error_category="parse_error"
                    )

                    assert failure.user_message is not None
                    assert len(failure.user_message) > 0


class TestLogRetrySuccess:
    """Tests for log_retry_success function."""

    def test_log_retry_success(self):
        """Test retry success logging."""
        with patch(
            "services.conversion_failure_analysis.get_correlation_id", return_value="corr-123"
        ):
            with patch("logging.Logger.info") as mock_log:
                log_retry_success("job-123", previous_attempts=3)

                mock_log.assert_called_once()
                call_args = mock_log.call_args
                assert "job-123" in str(call_args)


class TestLogRetryFailure:
    """Tests for log_retry_failure function."""

    def test_log_retry_failure(self):
        """Test retry failure logging."""
        with patch(
            "services.conversion_failure_analysis.get_correlation_id", return_value="corr-123"
        ):
            with patch("logging.Logger.warning") as mock_log:
                log_retry_failure(
                    job_id="job-123",
                    attempt=2,
                    error=ValueError("Still failing"),
                    error_category="network_error",
                )

                mock_log.assert_called_once()


class TestRecoverySuggestions:
    """Tests for recovery suggestion mappings."""

    def test_parse_error_suggestions(self):
        """Test parse error has suggestions."""
        suggestions = RECOVERY_SUGGESTIONS.get("parse_error", [])
        assert len(suggestions) > 0
        assert any("JAR" in s or "valid" in s.lower() for s in suggestions)

    def test_asset_error_suggestions(self):
        """Test asset error has suggestions."""
        suggestions = RECOVERY_SUGGESTIONS.get("asset_error", [])
        assert len(suggestions) > 0

    def test_logic_error_suggestions(self):
        """Test logic error has suggestions."""
        suggestions = RECOVERY_SUGGESTIONS.get("logic_error", [])
        assert len(suggestions) > 0

    def test_package_error_suggestions(self):
        """Test package error has suggestions."""
        suggestions = RECOVERY_SUGGESTIONS.get("package_error", [])
        assert len(suggestions) > 0

    def test_validation_error_suggestions(self):
        """Test validation error has suggestions."""
        suggestions = RECOVERY_SUGGESTIONS.get("validation_error", [])
        assert len(suggestions) > 0

    def test_network_error_suggestions(self):
        """Test network error has suggestions."""
        suggestions = RECOVERY_SUGGESTIONS.get("network_error", [])
        assert len(suggestions) > 0

    def test_rate_limit_suggestions(self):
        """Test rate limit error has suggestions."""
        suggestions = RECOVERY_SUGGESTIONS.get("rate_limit_error", [])
        assert len(suggestions) > 0

    def test_timeout_suggestions(self):
        """Test timeout error has suggestions."""
        suggestions = RECOVERY_SUGGESTIONS.get("timeout_error", [])
        assert len(suggestions) > 0

    def test_unknown_error_suggestions(self):
        """Test unknown error has fallback suggestions."""
        suggestions = RECOVERY_SUGGESTIONS.get("unknown_error", [])
        assert len(suggestions) > 0


class TestEdgeCases:
    """Tests for edge cases."""

    def test_failure_detail_defaults(self):
        """Test FailureDetail with default values."""
        detail = FailureDetail(
            error_type="Error", error_message="Message", error_category="unknown"
        )

        assert detail.stack_trace is None
        assert detail.file_path is None
        assert detail.line_number is None
        assert detail.context == {}

    def test_failure_detail_with_all_fields(self):
        """Test FailureDetail with all fields."""
        detail = FailureDetail(
            error_type="Error",
            error_message="Message",
            error_category="parse_error",
            stack_trace="Traceback...",
            file_path="/path/to/file.java",
            line_number=42,
            context={"key": "value"},
        )

        assert detail.stack_trace == "Traceback..."
        assert detail.file_path == "/path/to/file.java"
        assert detail.line_number == 42
        assert detail.context["key"] == "value"

    def test_conversion_failure_with_defaults(self):
        """Test ConversionFailure with default values."""
        failure = ConversionFailure(
            job_id="job-123",
            correlation_id="corr-456",
            timestamp="2024-01-01T00:00:00Z",
            failure_severity="low",
            failure_source="unknown",
            failure_summary="Summary",
            user_message="Message",
        )

        assert failure.retry_count == 0
        assert failure.was_retry_successful is None
        assert failure.conversion_stage is None
        assert failure.mod_type is None
        assert failure.target_version is None
        assert failure.recovery_suggestions == []
        assert failure.failure_details == []
        assert failure.additional_context == {}

    def test_severity_ordering(self):
        """Test severity levels are ordered correctly."""
        # LOW < MEDIUM < HIGH < CRITICAL
        severities = [
            FailureSeverity.LOW,
            FailureSeverity.MEDIUM,
            FailureSeverity.HIGH,
            FailureSeverity.CRITICAL,
        ]
        values = [s.value for s in severities]

        # Verify all values are different
        assert len(set(values)) == len(values)

    def test_all_error_categories_have_suggestions(self):
        """Test all error categories in suggestions."""
        expected_categories = [
            "parse_error",
            "asset_error",
            "logic_error",
            "package_error",
            "validation_error",
            "network_error",
            "rate_limit_error",
            "timeout_error",
            "unknown_error",
        ]

        for category in expected_categories:
            assert category in RECOVERY_SUGGESTIONS
            assert len(RECOVERY_SUGGESTIONS[category]) > 0
