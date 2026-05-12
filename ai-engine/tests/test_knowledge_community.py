"""Unit tests for Knowledge Community modules."""

import pytest
from datetime import datetime, timezone

from knowledge.community.submission import (
    SubmissionStatus,
    PatternSubmission,
)
from knowledge.community.validation import (
    ValidationResult,
    PatternValidator,
)


class TestSubmissionStatus:
    """Test cases for SubmissionStatus enum."""

    def test_pending_status(self):
        """Test PENDING status value."""
        assert SubmissionStatus.PENDING.value == "pending"

    def test_under_review_status(self):
        """Test UNDER_REVIEW status value."""
        assert SubmissionStatus.UNDER_REVIEW.value == "under_review"

    def test_approved_status(self):
        """Test APPROVED status value."""
        assert SubmissionStatus.APPROVED.value == "approved"

    def test_rejected_status(self):
        """Test REJECTED status value."""
        assert SubmissionStatus.REJECTED.value == "rejected"


class TestPatternSubmission:
    """Test cases for PatternSubmission dataclass."""

    def test_basic_submission_creation(self):
        """Test creating a basic pattern submission."""
        submission = PatternSubmission(
            id="test-id-123",
            java_pattern="public class MyClass {\n    public void test() {}\n}",
            bedrock_pattern='{"format_version": 2, "header": {}}',
            description="A test pattern for unit testing",
            contributor_id="test-user",
            status=SubmissionStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )

        assert submission.status == SubmissionStatus.PENDING
        assert submission.java_pattern == "public class MyClass {\n    public void test() {}\n}"
        assert submission.bedrock_pattern == '{"format_version": 2, "header": {}}'
        assert submission.description == "A test pattern for unit testing"
        assert submission.id == "test-id-123"

    def test_submission_with_all_fields(self):
        """Test creating a pattern submission with all optional fields."""
        now = datetime.now(timezone.utc)
        submission = PatternSubmission(
            id="test-id-456",
            java_pattern="public class MyClass {\n    public void test() {}\n}",
            bedrock_pattern='{"format_version": 2, "header": {}}',
            description="A test pattern for unit testing",
            contributor_id="test-user",
            status=SubmissionStatus.APPROVED,
            created_at=now,
            reviewed_by="reviewer_user",
            review_notes="Looks good",
            reviewed_at=now,
            upvotes=10,
            downvotes=2,
            tags=["test", "example"],
            category="functionality",
        )

        assert submission.status == SubmissionStatus.APPROVED
        assert submission.reviewed_by == "reviewer_user"
        assert submission.review_notes == "Looks good"
        assert submission.reviewed_at == now
        assert submission.upvotes == 10
        assert submission.downvotes == 2
        assert submission.tags == ["test", "example"]
        assert submission.category == "functionality"

    def test_submission_score_property(self):
        """Test that score property returns net votes."""
        submission = PatternSubmission(
            id="test-id",
            java_pattern="public class MyClass {\n    public void test() {}\n}",
            bedrock_pattern='{"format_version": 2}',
            description="A test pattern for unit testing",
            contributor_id="test-user",
            status=SubmissionStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            upvotes=15,
            downvotes=5,
        )
        assert submission.score == 10

    def test_submission_to_dict(self):
        """Test converting submission to dictionary."""
        now = datetime.now(timezone.utc)
        submission = PatternSubmission(
            id="test-id",
            java_pattern="public class MyClass {}",
            bedrock_pattern='{"format_version": 2}',
            description="A test pattern for unit testing",
            contributor_id="test-user",
            status=SubmissionStatus.PENDING,
            created_at=now,
        )
        result = submission.to_dict()

        assert result["id"] == "test-id"
        assert result["java_pattern"] == "public class MyClass {}"
        assert result["status"] == "pending"
        assert result["upvotes"] == 0
        assert result["downvotes"] == 0

    def test_submission_from_dict(self):
        """Test creating submission from dictionary."""
        now = datetime.now(timezone.utc)
        data = {
            "id": "test-id",
            "java_pattern": "public class MyClass {}",
            "bedrock_pattern": '{"format_version": 2}',
            "description": "A test pattern for unit testing",
            "contributor_id": "test-user",
            "status": "pending",
            "created_at": now.isoformat(),
            "upvotes": 5,
            "downvotes": 1,
        }
        submission = PatternSubmission.from_dict(data)

        assert submission.id == "test-id"
        assert submission.status == SubmissionStatus.PENDING
        assert submission.upvotes == 5
        assert submission.downvotes == 1

    def test_submission_requires_java_pattern(self):
        """Test that empty java_pattern raises ValueError."""
        with pytest.raises(ValueError, match="Java pattern cannot be empty"):
            PatternSubmission(
                id="test-id",
                java_pattern="",
                bedrock_pattern='{"format_version": 2}',
                description="A test pattern for unit testing",
                contributor_id="test-user",
                status=SubmissionStatus.PENDING,
                created_at=datetime.now(timezone.utc),
            )

    def test_submission_requires_description_length(self):
        """Test that short description raises ValueError."""
        with pytest.raises(ValueError, match="Description must be at least 20 characters"):
            PatternSubmission(
                id="test-id",
                java_pattern="public class MyClass {}",
                bedrock_pattern='{"format_version": 2}',
                description="Too short",
                contributor_id="test-user",
                status=SubmissionStatus.PENDING,
                created_at=datetime.now(timezone.utc),
            )

    def test_submission_requires_contributor_id(self):
        """Test that empty contributor_id raises ValueError."""
        with pytest.raises(ValueError, match="Contributor ID cannot be empty"):
            PatternSubmission(
                id="test-id",
                java_pattern="public class MyClass {}",
                bedrock_pattern='{"format_version": 2}',
                description="A test pattern for unit testing",
                contributor_id="",
                status=SubmissionStatus.PENDING,
                created_at=datetime.now(timezone.utc),
            )

    def test_submission_negative_upvotes_raises(self):
        """Test that negative upvotes raises ValueError."""
        with pytest.raises(ValueError, match="Upvotes cannot be negative"):
            PatternSubmission(
                id="test-id",
                java_pattern="public class MyClass {}",
                bedrock_pattern='{"format_version": 2}',
                description="A test pattern for unit testing",
                contributor_id="test-user",
                status=SubmissionStatus.PENDING,
                created_at=datetime.now(timezone.utc),
                upvotes=-1,
            )


class TestValidationResult:
    """Test cases for ValidationResult dataclass."""

    def test_valid_result_with_no_errors(self):
        """Test valid result with no errors."""
        result = ValidationResult(is_valid=True)
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_valid_result_with_warnings(self):
        """Test valid result with warnings."""
        result = ValidationResult(
            is_valid=True,
            warnings=["Style could be improved", "Consider refactoring"],
        )
        assert result.is_valid is True
        assert result.warnings == ["Style could be improved", "Consider refactoring"]

    def test_invalid_result_with_errors(self):
        """Test invalid result with errors."""
        result = ValidationResult(
            is_valid=False,
            errors=["Missing required field", "Invalid syntax"],
        )
        assert result.is_valid is False
        assert result.errors == ["Missing required field", "Invalid syntax"]

    def test_invalid_result_raises_on_conflict(self):
        """Test that invalid with errors raises ValueError on init."""
        with pytest.raises(ValueError, match="Cannot have errors and be valid"):
            ValidationResult(is_valid=True, errors=["Some error"])

    def test_validation_result_with_both(self):
        """Test result with both errors and warnings."""
        result = ValidationResult(
            is_valid=False,
            errors=["Critical error"],
            warnings=["Minor issue"],
        )
        assert result.is_valid is False
        assert result.errors == ["Critical error"]
        assert result.warnings == ["Minor issue"]


class TestPatternValidator:
    """Test cases for PatternValidator class."""

    @pytest.fixture
    def validator(self):
        """Create a PatternValidator instance."""
        return PatternValidator()

    @pytest.mark.asyncio
    async def test_validate_pattern_valid(self, validator):
        """Test validating a valid pattern."""
        result = await validator.validate_pattern(
            java_pattern="package com.example;\npublic class MyClass {\n    public void test() {}\n}",
            bedrock_pattern='{"format_version": 2, "header": {}}',
            description="A well-documented test pattern with sufficient length",
        )
        assert result.is_valid is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_validate_pattern_missing_java_class(self, validator):
        """Test that Java code without class keyword is rejected."""
        result = await validator.validate_pattern(
            java_pattern="public void test() {}",
            bedrock_pattern='{"format_version": 2, "header": {}}',
            description="A well-documented test pattern with sufficient length",
        )
        assert result.is_valid is False
        assert any("class, interface, or enum keyword" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_validate_pattern_short_java_warns_about_lines(self, validator):
        """Test that short Java code produces warning about minimum lines."""
        result = await validator.validate_pattern(
            java_pattern="public class {}",
            bedrock_pattern='{"format_version": 2, "header": {}}',
            description="A well-documented test pattern with sufficient length",
        )
        # Should produce error about being too short
        assert any("too short" in e.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_validate_pattern_short_bedrock_warns_about_lines(self, validator):
        """Test that short Bedrock code produces error about minimum lines."""
        result = await validator.validate_pattern(
            java_pattern="package com.example;\npublic class MyClass {}",
            bedrock_pattern="{}",
            description="A well-documented test pattern with sufficient length",
        )
        assert result.is_valid is False
        assert any("too short" in e.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_validate_pattern_short_description(self, validator):
        """Test that short descriptions are rejected."""
        result = await validator.validate_pattern(
            java_pattern="package com.example;\npublic class MyClass {}",
            bedrock_pattern='{"format_version": 2, "header": {}}',
            description="Too short",
        )
        assert result.is_valid is False

    @pytest.mark.asyncio
    async def test_validate_pattern_detects_eval(self, validator):
        """Test that eval() is detected as malicious."""
        result = await validator.validate_pattern(
            java_pattern="""
package com.example;
public class MyClass {
    public void test() {
        eval("malicious");
    }
}
""",
            bedrock_pattern='{"format_version": 2, "header": {}}',
            description="A well-documented test pattern with sufficient length",
        )
        assert result.is_valid is False
        assert any("malicious" in e.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_validate_pattern_detects_script_tag(self, validator):
        """Test that script tags are detected."""
        result = await validator.validate_pattern(
            java_pattern="package com.example;\npublic class MyClass {}",
            bedrock_pattern="""
<script>
alert('xss');
</script>
""",
            description="A well-documented test pattern with sufficient length",
        )
        assert result.is_valid is False
        assert any("malicious" in e.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_validate_pattern_detects_process_builder(self, validator):
        """Test that ProcessBuilder is detected."""
        result = await validator.validate_pattern(
            java_pattern="""
package com.example;
public class MyClass {
    public void test() {
        new ProcessBuilder("rm -rf /").start();
    }
}
""",
            bedrock_pattern='{"format_version": 2, "header": {}}',
            description="A well-documented test pattern with sufficient length",
        )
        assert result.is_valid is False
        assert any("malicious" in e.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_validate_pattern_detects_document_cookie(self, validator):
        """Test that document.cookie is detected."""
        result = await validator.validate_pattern(
            java_pattern="package com.example;\npublic class MyClass {}",
            bedrock_pattern="""
<script>
var x = document.cookie;
</script>
""",
            description="A well-documented test pattern with sufficient length",
        )
        assert result.is_valid is False
        assert any("malicious" in e.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_validate_pattern_detects_import_statement(self, validator):
        """Test that __import__ is detected."""
        result = await validator.validate_pattern(
            java_pattern="package com.example;\npublic class MyClass {}",
            bedrock_pattern="""
<script>
__import__('os').system('rm -rf /');
</script>
""",
            description="A well-documented test pattern with sufficient length",
        )
        assert result.is_valid is False
        assert any("malicious" in e.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_validate_pattern_valid_with_warnings(self, validator):
        """Test validation with valid content but some warnings."""
        result = await validator.validate_pattern(
            java_pattern="public class MyClass {\n    public void test() {}\n}",
            bedrock_pattern='{"format_version": 2, "header": {}}',
            description="A well-documented test pattern with sufficient length",
        )
        # Valid structure but missing package/imports and access modifiers
        assert result.warnings or not result.errors

    def test_validator_malicious_patterns_compiled(self, validator):
        """Test that malicious patterns are compiled."""
        assert validator.malicious_regex is not None
        assert validator.malicious_regex.pattern != ""

    def test_validator_malicious_patterns_count(self):
        """Test that all malicious patterns are registered."""
        validator = PatternValidator()
        assert len(validator.MALICIOUS_PATTERNS) > 0
        # At minimum we should detect eval, __import__, exec, script tags
        patterns_str = "|".join(validator.MALICIOUS_PATTERNS)
        assert "eval" in patterns_str
        assert "script" in patterns_str

    @pytest.mark.asyncio
    async def test_validate_pattern_empty_java(self, validator):
        """Test validation with empty Java pattern."""
        result = await validator.validate_pattern(
            java_pattern="",
            bedrock_pattern='{"format_version": 2, "header": {}}',
            description="A well-documented test pattern with sufficient length",
        )
        assert result.is_valid is False

    @pytest.mark.asyncio
    async def test_validate_pattern_whitespace_java(self, validator):
        """Test validation with whitespace-only Java pattern."""
        result = await validator.validate_pattern(
            java_pattern="   \n   \n   ",
            bedrock_pattern='{"format_version": 2, "header": {}}',
            description="A well-documented test pattern with sufficient length",
        )
        assert result.is_valid is False

    def test_validate_java_pattern_class_keyword(self, validator):
        """Test _validate_java_pattern with class keyword."""
        result = validator._validate_java_pattern(
            "package com.example;\npublic class MyClass {\n}\n"
        )
        assert result.is_valid is True

    def test_validate_java_pattern_interface_keyword(self, validator):
        """Test _validate_java_pattern with interface keyword."""
        result = validator._validate_java_pattern(
            "public interface MyInterface {\n    void method();\n}\n"
        )
        assert result.is_valid is True

    def test_validate_java_pattern_enum_keyword(self, validator):
        """Test _validate_java_pattern with enum keyword."""
        result = validator._validate_java_pattern(
            "public enum MyEnum {\n    A,\n}\n"
        )
        assert result.is_valid is True
