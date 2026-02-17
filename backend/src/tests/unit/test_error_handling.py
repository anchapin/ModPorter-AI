"""
Tests for Comprehensive Error Handling (Issue #455)

Tests the error categories, retry logic, and error metrics.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestErrorCategories:
    """Test error category definitions"""
    
    def test_error_categories_defined(self):
        """Test that all required error categories are defined"""
        from services.error_handlers import ERROR_CATEGORIES
        
        required_categories = [
            "parse_error",
            "asset_error", 
            "logic_error",
            "package_error",
            "validation_error",
            "network_error",
            "rate_limit_error",
            "timeout_error",
        ]
        
        for category in required_categories:
            assert category in ERROR_CATEGORIES
            assert ERROR_CATEGORIES[category]  # Non-empty message
    
    def test_custom_exceptions(self):
        """Test custom exception classes"""
        from services.error_handlers import (
            ModPorterException,
            ParseError,
            AssetError,
            LogicError,
            PackageError,
            ValidationError,
            RateLimitException,
            ConversionException,
            FileProcessingException,
            NotFoundException,
        )
        
        # Test ParseError
        exc = ParseError("Parse failed", "Check file format")
        assert exc.error_type == "parse_error"
        assert exc.status_code == 422
        
        # Test AssetError
        exc = AssetError("Asset error", "Missing texture")
        assert exc.error_type == "asset_error"
        
        # Test LogicError
        exc = LogicError("Logic failed", "Conversion issue")
        assert exc.error_type == "logic_error"
        assert exc.status_code == 500
        
        # Test PackageError
        exc = PackageError("Package failed", "Try again")
        assert exc.error_type == "package_error"
        assert exc.status_code == 500
        
        # Test ValidationError
        exc = ValidationError("Validation failed", "Check input")
        assert exc.error_type == "validation_error"
        
        # Test RateLimitException
        exc = RateLimitException(retry_after=60)
        assert exc.error_type == "rate_limit_error"
        assert exc.status_code == 429
        assert exc.details["retry_after"] == 60


class TestErrorCategorization:
    """Test error categorization function"""
    
    def test_categorize_parse_error(self):
        """Test parse error categorization"""
        from services.error_handlers import _categorize_error, ParseError
        
        # Test by exception type
        error = ParseError("test", "test")
        assert _categorize_error(error) == "parse_error"
    
    def test_categorize_asset_error(self):
        """Test asset error categorization"""
        from services.error_handlers import _categorize_error, AssetError
        
        error = AssetError("test", "test")
        assert _categorize_error(error) == "asset_error"
    
    def test_categorize_logic_error(self):
        """Test logic error categorization"""
        from services.error_handlers import _categorize_error, LogicError
        
        error = LogicError("test", "test")
        assert _categorize_error(error) == "logic_error"
    
    def test_categorize_package_error(self):
        """Test package error categorization"""
        from services.error_handlers import _categorize_error, PackageError
        
        error = PackageError("test", "test")
        assert _categorize_error(error) == "package_error"


class TestRetryLogic:
    """Test retry logic"""
    
    def test_retry_config_defaults(self):
        """Test RetryConfig default values"""
        from services.retry import RetryConfig
        
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
    
    def test_retry_config_custom(self):
        """Test RetryConfig with custom values"""
        from services.retry import RetryConfig
        
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            jitter=False,
        )
        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0
        assert config.jitter is False
    
    def test_calculate_delay(self):
        """Test delay calculation with exponential backoff"""
        from services.retry import calculate_delay, RetryConfig
        
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        
        # First attempt: 1.0 * 2^0 = 1.0
        assert calculate_delay(1, config) == 1.0
        # Second attempt: 1.0 * 2^1 = 2.0
        assert calculate_delay(2, config) == 2.0
        # Third attempt: 1.0 * 2^2 = 4.0
        assert calculate_delay(3, config) == 4.0
    
    def test_is_retryable(self):
        """Test retryable error detection"""
        from services.retry import is_retryable, RetryConfig, RetryableError, NonRetryableError
        
        config = RetryConfig()
        
        # RetryableError should be retryable
        assert is_retryable(RetryableError("test"), config) is True
        
        # NonRetryableError should not be retryable
        assert is_retryable(NonRetryableError("test"), config) is False
    
    def test_categorize_error_function(self):
        """Test the categorize_error function"""
        from services.retry import categorize_error, ParseError, AssetError, LogicError
        
        # Test by exception type
        assert categorize_error(ParseError("test", "test")) == "parse_error"
        assert categorize_error(AssetError("test", "test")) == "asset_error"
        assert categorize_error(LogicError("test", "test")) == "logic_error"


class TestConversionFailureAnalysis:
    """Test conversion failure analysis"""
    
    def test_failure_severity_determination(self):
        """Test severity determination"""
        from services.conversion_failure_analysis import determine_failure_severity, FailureSeverity
        
        # High retry count = critical
        assert determine_failure_severity("parse_error", 3) == FailureSeverity.CRITICAL
        assert determine_failure_severity("parse_error", 5) == FailureSeverity.CRITICAL
        
        # First attempt, critical category = high
        assert determine_failure_severity("logic_error", 0) == FailureSeverity.HIGH
        
        # Retry on critical category = critical
        assert determine_failure_severity("logic_error", 1) == FailureSeverity.CRITICAL
        
        # First attempt, high category = medium
        assert determine_failure_severity("parse_error", 0) == FailureSeverity.MEDIUM
        
        # Retry on high category = high
        assert determine_failure_severity("parse_error", 1) == FailureSeverity.HIGH
        
        # Medium category = medium
        assert determine_failure_severity("validation_error", 0) == FailureSeverity.MEDIUM
        
        # Unknown = low
        assert determine_failure_severity("unknown_error", 0) == FailureSeverity.LOW
    
    def test_failure_source_determination(self):
        """Test failure source determination"""
        from services.conversion_failure_analysis import determine_failure_source, FailureSource
        
        assert determine_failure_source("upload") == FailureSource.FILE_UPLOAD
        assert determine_failure_source("parsing") == FailureSource.FILE_PARSING
        assert determine_failure_source("analyzing") == FailureSource.MOD_ANALYSIS
        assert determine_failure_source("asset conversion") == FailureSource.ASSET_CONVERSION
        assert determine_failure_source("code translation") == FailureSource.CODE_TRANSLATION
        assert determine_failure_source("packaging") == FailureSource.PACKAGING
        assert determine_failure_source("validation") == FailureSource.VALIDATION
        assert determine_failure_source(None) == FailureSource.UNKNOWN
        assert determine_failure_source("unknown") == FailureSource.UNKNOWN
    
    def test_recovery_suggestions(self):
        """Test recovery suggestions are defined"""
        from services.conversion_failure_analysis import RECOVERY_SUGGESTIONS
        
        assert "parse_error" in RECOVERY_SUGGESTIONS
        assert "asset_error" in RECOVERY_SUGGESTIONS
        assert "logic_error" in RECOVERY_SUGGESTIONS
        assert "package_error" in RECOVERY_SUGGESTIONS
        assert "validation_error" in RECOVERY_SUGGESTIONS
        assert "network_error" in RECOVERY_SUGGESTIONS
        assert "rate_limit_error" in RECOVERY_SUGGESTIONS
        assert "timeout_error" in RECOVERY_SUGGESTIONS
        assert "unknown_error" in RECOVERY_SUGGESTIONS
        
        # Each should have non-empty suggestions
        for category, suggestions in RECOVERY_SUGGESTIONS.items():
            assert len(suggestions) > 0


class TestErrorMetrics:
    """Test error metrics"""
    
    def test_metrics_import(self):
        """Test that error metrics can be imported"""
        try:
            from services.metrics import error_total, error_rate, retry_attempts_total, successful_retries_total
            assert error_total is not None
            assert error_rate is not None
            assert retry_attempts_total is not None
            assert successful_retries_total is not None
        except ImportError as e:
            pytest.skip(f"Metrics not available: {e}")
    
    def test_record_error_function(self):
        """Test record_error function exists"""
        try:
            from services.metrics import record_error
            assert callable(record_error)
        except ImportError as e:
            pytest.skip(f"Metrics not available: {e}")
    
    def test_record_retry_functions(self):
        """Test retry recording functions"""
        try:
            from services.metrics import record_retry_attempt, record_successful_retry
            assert callable(record_retry_attempt)
            assert callable(record_successful_retry)
        except ImportError as e:
            pytest.skip(f"Metrics not available: {e}")


class TestStructuredLogging:
    """Test structured logging"""
    
    def test_correlation_id_context(self):
        """Test correlation ID context management"""
        from services.structured_logging import (
            set_correlation_id,
            get_correlation_id,
            clear_correlation_id,
        )
        
        # Initially no correlation ID
        clear_correlation_id()
        assert get_correlation_id() is None
        
        # Set correlation ID
        cid = set_correlation_id()
        assert cid is not None
        assert get_correlation_id() == cid
        
        # Clear and verify
        clear_correlation_id()
        assert get_correlation_id() is None
    
    def test_log_context_manager(self):
        """Test LogContext context manager"""
        from services.structured_logging import LogContext, get_correlation_id
        
        # Test basic context management
        original_cid = get_correlation_id()
        
        with LogContext(correlation_id="test-123", user_id="user-1"):
            assert get_correlation_id() == "test-123"
        
        # After context, should be restored
        # (Note: might be None if there was no original)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
