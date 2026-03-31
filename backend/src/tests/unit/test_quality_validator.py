"""
Unit tests for quality validator.
"""

import pytest
from backend.src.ingestion.validators.quality import (
    QualityValidator,
    ValidationResult,
)


class TestValidationResult:
    """Test cases for ValidationResult dataclass."""

    def test_creation(self):
        """Test creating validation result."""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["Warning 1"],
        )
        
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == ["Warning 1"]


class TestQualityValidator:
    """Test cases for QualityValidator class."""

    @pytest.fixture
    def validator(self):
        """Create quality validator instance."""
        return QualityValidator()

    def test_valid_document(self, validator):
        """Test valid document passes validation."""
        content = "This is a valid document with enough content to pass the minimum length requirement and contains meaningful text."
        metadata = {"title": "Test Doc", "source": "https://example.com"}
        
        result = validator.validate(content, metadata)
        
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_content_too_short(self, validator):
        """Test content that is too short."""
        content = "Short"
        metadata = {"title": "Test"}
        
        result = validator.validate(content, metadata)
        
        assert result.is_valid is False
        assert any("too short" in e.lower() for e in result.errors)

    def test_content_too_long(self, validator):
        """Test content that is too long."""
        content = "x" * 200000  # Exceeds MAX_LENGTH
        metadata = {"title": "Test"}
        
        result = validator.validate(content, metadata)
        
        assert result.is_valid is False
        assert any("too long" in e.lower() for e in result.errors)

    def test_empty_content(self, validator):
        """Test empty content."""
        content = ""
        metadata = {"title": "Test"}
        
        result = validator.validate(content, metadata)
        
        assert result.is_valid is False
        assert any("empty" in e.lower() for e in result.errors)

    def test_whitespace_only_content(self, validator):
        """Test whitespace-only content."""
        content = "   \n\t\t   "
        metadata = {"title": "Test"}
        
        result = validator.validate(content, metadata)
        
        assert result.is_valid is False
        assert any("empty" in e.lower() or "whitespace" in e.lower() for e in result.errors)

    def test_non_meaningful_content(self, validator):
        """Test non-meaningful content (too many symbols)."""
        content = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
        metadata = {"title": "Test"}
        
        result = validator.validate(content, metadata)
        
        assert result.is_valid is False
        assert any("meaningful" in e.lower() for e in result.errors)

    def test_missing_title_warning(self, validator):
        """Test warning for missing title."""
        content = "This is a valid document with enough content to pass validation requirements."
        metadata = {"source": "https://example.com"}
        
        result = validator.validate(content, metadata)
        
        assert result.is_valid is True
        assert any("title" in w.lower() for w in result.warnings)

    def test_missing_source_warning(self, validator):
        """Test warning for missing source."""
        content = "This is a valid document with enough content to pass validation requirements."
        metadata = {"title": "Test Doc"}
        
        result = validator.validate(content, metadata)
        
        assert result.is_valid is True
        assert any("source" in w.lower() for w in result.warnings)

    def test_repetitive_content_warning(self, validator):
        """Test warning for repetitive content."""
        sentence = "This is a repeated sentence that appears many times in the document. "
        content = sentence * 6  # Repeat 6 times (>= 5 threshold)
        metadata = {"title": "Test", "source": "test"}
        
        result = validator.validate(content, metadata)
        
        assert result.is_valid is True  # Repetitive is a warning, not error
        assert any("repetitive" in w.lower() or "spam" in w.lower() for w in result.warnings)

    def test_is_meaningful_method(self, validator):
        """Test _is_meaningful method directly."""
        assert validator._is_meaningful("Hello World 123") is True
        assert validator._is_meaningful("!!!@@@###") is False
        assert validator._is_meaningful("") is False

    def test_is_repetitive_method(self, validator):
        """Test _is_repetitive method directly."""
        # Non-repetitive
        assert validator._is_repetitive("This is sentence one. This is sentence two.") is False
        
        # Repetitive
        sentence = "This is a very long sentence that repeats many times in the document content."
        repetitive = " ".join([sentence] * 6)
        assert validator._is_repetitive(repetitive) is True

    def test_length_boundaries(self, validator):
        """Test content at length boundaries."""
        # At minimum length
        min_content = "a" * 50
        result = validator.validate(min_content, {"title": "Test"})
        assert result.is_valid is True
        
        # Just below minimum
        short_content = "a" * 49
        result = validator.validate(short_content, {"title": "Test"})
        assert result.is_valid is False

    def test_alphanumeric_ratio(self, validator):
        """Test alphanumeric ratio threshold."""
        # High ratio - valid
        content = "Hello World 123 Test 456" + (" x " * 30)  # ~50 chars with high ratio
        result = validator.validate(content, {"title": "Test", "source": "test"})
        assert result.is_valid is True
        
        # Low ratio - invalid (make sure it has enough length)
        content = "!!! ### ??? ..." * 10  # ~50 chars but low alphanumeric ratio
        result = validator.validate(content, {"title": "Test", "source": "test"})
        assert result.is_valid is False