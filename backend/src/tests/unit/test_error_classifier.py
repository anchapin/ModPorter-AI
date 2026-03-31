"""Tests for the error classifier module."""

import pytest
from unittest.mock import MagicMock, patch

from services.error_classifier import (
    ErrorClassifier,
    ErrorClassification,
    ErrorType,
    ErrorSeverity,
    classify_error,
    get_classifier,
    ERROR_PATTERNS,
    ERROR_SEVERITY,
)


class TestErrorType:
    """Test ErrorType enum values."""

    def test_error_type_values(self):
        """Test all error type values exist."""
        assert ErrorType.NETWORK.value == "network"
        assert ErrorType.VALIDATION.value == "validation"
        assert ErrorType.TIMEOUT.value == "timeout"
        assert ErrorType.PARSE.value == "parse"
        assert ErrorType.ASSET.value == "asset"
        assert ErrorType.LOGIC.value == "logic"
        assert ErrorType.PACKAGE.value == "package"
        assert ErrorType.RATE_LIMIT.value == "rate_limit"
        assert ErrorType.AUTHENTICATION.value == "authentication"
        assert ErrorType.AUTHORIZATION.value == "authorization"
        assert ErrorType.NOT_FOUND.value == "not_found"
        assert ErrorType.CONFLICT.value == "conflict"
        assert ErrorType.QUOTA_EXCEEDED.value == "quota_exceeded"
        assert ErrorType.SERVICE_UNAVAILABLE.value == "service_unavailable"
        assert ErrorType.INTERNAL.value == "internal"
        assert ErrorType.UNKNOWN.value == "unknown"


class TestErrorSeverity:
    """Test ErrorSeverity enum values."""

    def test_severity_values(self):
        """Test all severity values exist."""
        assert ErrorSeverity.BLOCKING.value == "blocking"
        assert ErrorSeverity.WARNING.value == "warning"
        assert ErrorSeverity.INFO.value == "info"


class TestErrorClassification:
    """Test ErrorClassification dataclass."""

    def test_error_classification_creation(self):
        """Test creating an ErrorClassification."""
        classification = ErrorClassification(
            error_type=ErrorType.NETWORK,
            severity=ErrorSeverity.WARNING,
            confidence=0.9,
            matched_pattern="connection.*refused",
        )

        assert classification.error_type == ErrorType.NETWORK
        assert classification.severity == ErrorSeverity.WARNING
        assert classification.confidence == 0.9
        assert classification.matched_pattern == "connection.*refused"
        assert classification.details == {}

    def test_error_classification_to_dict(self):
        """Test converting classification to dictionary."""
        classification = ErrorClassification(
            error_type=ErrorType.VALIDATION,
            severity=ErrorSeverity.WARNING,
            confidence=1.0,
            matched_pattern="validation.*error",
            details={"field": "name"},
        )

        result = classification.to_dict()

        assert result["error_type"] == "validation"
        assert result["severity"] == "warning"
        assert result["confidence"] == 1.0
        assert result["matched_pattern"] == "validation.*error"
        assert result["details"]["field"] == "name"

    def test_error_classification_repr(self):
        """Test string representation."""
        classification = ErrorClassification(
            error_type=ErrorType.TIMEOUT,
            severity=ErrorSeverity.WARNING,
            confidence=0.85,
        )

        repr_str = repr(classification)

        assert "timeout" in repr_str
        assert "warning" in repr_str
        assert "0.85" in repr_str


class TestErrorClassifier:
    """Test ErrorClassifier class."""

    def test_classifier_initialization(self):
        """Test initializing the classifier."""
        classifier = ErrorClassifier()

        assert classifier._compiled_patterns is not None
        assert len(classifier._compiled_patterns) > 0

    def test_classify_network_error_direct_type(self):
        """Test classifying network error from retry module."""
        try:
            from src.services.retry import NetworkError

            error = NetworkError("Connection refused")
            classifier = ErrorClassifier()
            result = classifier.classify(error)

            assert result.error_type == ErrorType.NETWORK
            assert result.confidence >= 0.9
            assert result.matched_pattern is not None
        except ImportError:
            pytest.skip("retry module not available")

    def test_classify_timeout_error_direct_type(self):
        """Test classifying timeout error from retry module."""
        try:
            from src.services.retry import TimeoutError

            error = TimeoutError("Operation timed out")
            classifier = ErrorClassifier()
            result = classifier.classify(error)

            assert result.error_type == ErrorType.TIMEOUT
            assert result.confidence >= 0.9
        except ImportError:
            pytest.skip("retry module not available")

    def test_classify_validation_error_direct_type(self):
        """Test classifying validation error from retry module."""
        try:
            from src.services.retry import ValidationError

            error = ValidationError("Invalid value")
            classifier = ErrorClassifier()
            result = classifier.classify(error)

            assert result.error_type == ErrorType.VALIDATION
            assert result.confidence >= 0.9
        except ImportError:
            pytest.skip("retry module not available")

    def test_classify_parse_error_by_pattern(self):
        """Test classifying parse error by pattern match."""
        error = Exception("Failed to parse: unexpected token at line 10")
        classifier = ErrorClassifier()
        result = classifier.classify(error)

        assert result.error_type == ErrorType.PARSE
        assert result.matched_pattern is not None

    def test_classify_network_error_by_pattern(self):
        """Test classifying network error by pattern match."""
        error = Exception("Connection refused by host")
        classifier = ErrorClassifier()
        result = classifier.classify(error)

        assert result.error_type == ErrorType.NETWORK
        assert result.matched_pattern is not None

    def test_classify_rate_limit_by_pattern(self):
        """Test classifying rate limit error by pattern."""
        error = Exception("Rate limit exceeded: 429 Too Many Requests")
        classifier = ErrorClassifier()
        result = classifier.classify(error)

        assert result.error_type == ErrorType.RATE_LIMIT
        assert result.matched_pattern is not None

    def test_classify_timeout_by_pattern(self):
        """Test classifying timeout error by pattern."""
        error = Exception("The operation timed out after 30 seconds")
        classifier = ErrorClassifier()
        result = classifier.classify(error)

        assert result.error_type == ErrorType.TIMEOUT
        assert result.matched_pattern is not None

    def test_classify_asset_error_by_pattern(self):
        """Test classifying asset error by pattern."""
        error = Exception("Asset not found: texture_block")
        classifier = ErrorClassifier()
        result = classifier.classify(error)

        assert result.error_type == ErrorType.ASSET
        assert result.matched_pattern is not None

    def test_classify_package_error_by_pattern(self):
        """Test classifying package error by pattern."""
        error = Exception("Failed to create zip archive")
        classifier = ErrorClassifier()
        result = classifier.classify(error)

        assert result.error_type == ErrorType.PACKAGE
        assert result.matched_pattern is not None

    def test_classify_unknown_error(self):
        """Test classifying completely unknown error."""
        error = Exception("Some completely obscure error message xyz123")
        classifier = ErrorClassifier()
        result = classifier.classify(error)

        assert result.error_type == ErrorType.UNKNOWN
        assert result.confidence == 0.5

    def test_classify_with_context(self):
        """Test classification includes context."""
        error = Exception("Connection refused")
        context = {"job_id": "123", "operation": "conversion"}
        classifier = ErrorClassifier()
        result = classifier.classify(error, context)

        assert "job_id" in result.details["context"]
        assert result.details["context"]["job_id"] == "123"

    def test_get_recovery_priority_network(self):
        """Test recovery priority for network errors."""
        classifier = ErrorClassifier()
        classification = ErrorClassification(
            error_type=ErrorType.NETWORK,
            severity=ErrorSeverity.WARNING,
            confidence=1.0,
        )

        priority = classifier.get_recovery_priority(classification)

        assert priority == 10  # High priority

    def test_get_recovery_priority_logic(self):
        """Test recovery priority for logic errors."""
        classifier = ErrorClassifier()
        classification = ErrorClassification(
            error_type=ErrorType.LOGIC,
            severity=ErrorSeverity.BLOCKING,
            confidence=1.0,
        )

        priority = classifier.get_recovery_priority(classification)

        assert priority == 95  # Low priority (almost no recovery)


class TestClassifyErrorFunction:
    """Test the classify_error convenience function."""

    def test_classify_error_uses_global_classifier(self):
        """Test that classify_error uses the global classifier."""
        error = Exception("timeout error")
        result = classify_error(error)

        assert result.error_type == ErrorType.TIMEOUT

    def test_classify_error_with_context(self):
        """Test classify_error passes context through."""
        error = Exception("parse error")
        context = {"mod_id": "mod-123"}
        result = classify_error(error, context)

        assert result.details["context"]["mod_id"] == "mod-123"


class TestGetClassifier:
    """Test the get_classifier function."""

    def test_get_classifier_returns_same_instance(self):
        """Test that get_classifier returns singleton."""
        classifier1 = get_classifier()
        classifier2 = get_classifier()

        assert classifier1 is classifier2


class TestErrorSeverityMapping:
    """Test error severity mapping."""

    def test_network_is_warning(self):
        """Test network errors are warnings."""
        assert ERROR_SEVERITY[ErrorType.NETWORK] == ErrorSeverity.WARNING

    def test_validation_is_warning(self):
        """Test validation errors are warnings."""
        assert ERROR_SEVERITY[ErrorType.VALIDATION] == ErrorSeverity.WARNING

    def test_logic_is_blocking(self):
        """Test logic errors are blocking."""
        assert ERROR_SEVERITY[ErrorType.LOGIC] == ErrorSeverity.BLOCKING

    def test_authentication_is_blocking(self):
        """Test authentication errors are blocking."""
        assert ERROR_SEVERITY[ErrorType.AUTHENTICATION] == ErrorSeverity.BLOCKING

    def test_not_found_is_info(self):
        """Test not found errors are info level."""
        assert ERROR_SEVERITY[ErrorType.NOT_FOUND] == ErrorSeverity.INFO


class TestErrorPatterns:
    """Test error pattern definitions."""

    def test_network_patterns_exist(self):
        """Test network error patterns are defined."""
        assert ErrorType.NETWORK in ERROR_PATTERNS
        assert len(ERROR_PATTERNS[ErrorType.NETWORK]) > 0

    def test_validation_patterns_exist(self):
        """Test validation error patterns are defined."""
        assert ErrorType.VALIDATION in ERROR_PATTERNS
        assert len(ERROR_PATTERNS[ErrorType.VALIDATION]) > 0

    def test_all_error_types_have_patterns(self):
        """Test all error types have pattern definitions."""
        for error_type in ErrorType:
            if error_type != ErrorType.UNKNOWN:
                assert error_type in ERROR_PATTERNS, f"Missing patterns for {error_type}"


class TestPatternMatching:
    """Test pattern matching functionality."""

    def test_match_patterns_connection_refused(self):
        """Test matching connection refused pattern."""
        classifier = ErrorClassifier()
        matches = classifier._match_patterns("ConnectionRefusedError: Connection refused")

        assert len(matches) > 0
        assert any(m[0] == ErrorType.NETWORK for m in matches)

    def test_match_patterns_timeout(self):
        """Test matching timeout pattern."""
        classifier = ErrorClassifier()
        matches = classifier._match_patterns("TimeoutError: operation timed out")

        assert len(matches) > 0
        assert any(m[0] == ErrorType.TIMEOUT for m in matches)

    def test_match_patterns_rate_limit(self):
        """Test matching rate limit pattern."""
        classifier = ErrorClassifier()
        matches = classifier._match_patterns("RateLimitError: 429 Too Many Requests")

        assert len(matches) > 0
        assert any(m[0] == ErrorType.RATE_LIMIT for m in matches)

    def test_match_patterns_validation(self):
        """Test matching validation pattern."""
        classifier = ErrorClassifier()
        matches = classifier._match_patterns("ValidationError: invalid value for field 'name'")

        assert len(matches) > 0
        assert any(m[0] == ErrorType.VALIDATION for m in matches)
