"""Unit tests for ReviewerAgent."""

import json
import tempfile
from pathlib import Path
from datetime import datetime


from qa.reviewer import ReviewerAgent, ValidationIssue
from qa.context import QAContext
from qa.validators import AgentOutput


class TestReviewerAgentImports:
    """Test that all imports work correctly."""

    def test_agent_imports(self):
        """Verify imports work correctly."""
        from qa.reviewer import ReviewerAgent, review

        assert ReviewerAgent is not None
        assert review is not None

    def test_agent_instantiation(self):
        """Verify agent can be instantiated."""
        agent = ReviewerAgent()
        assert agent is not None
        assert agent.temperature == 0.0

    def test_agent_custom_temperature(self):
        """Verify agent can be instantiated with custom temperature."""
        agent = ReviewerAgent(temperature=0.5)
        assert agent.temperature == 0.5


class TestReviewerAgentQAContext:
    """Test agent receives QAContext correctly."""

    def test_agent_receives_qa_context(self):
        """Verify agent can receive QAContext."""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            java_path = job_dir / "source.java"
            bedrock_path = job_dir / "bedrock"

            bedrock_path.mkdir(parents=True)
            java_path.write_text("// Test Java file\npublic class TestItem {}")

            context = QAContext(
                job_id="test-job-123",
                job_dir=job_dir,
                source_java_path=java_path,
                output_bedrock_path=bedrock_path,
                metadata={"test": True},
                validation_results={},
                created_at=datetime.now(),
                current_agent=None,
            )

            agent = ReviewerAgent()
            result = agent.execute(context)

            assert isinstance(result, AgentOutput)
            assert "quality_score" in result.result


class TestESLintValidation:
    """Test ESLint validation."""

    def test_eslint_validation_no_ts_files(self):
        """Verify ESLint handles missing TypeScript files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            java_path = job_dir / "source.java"
            bedrock_path = job_dir / "bedrock"

            bedrock_path.mkdir(parents=True)
            java_path.write_text("// Test Java file")

            context = QAContext(
                job_id="test-eslint-123",
                job_dir=job_dir,
                source_java_path=java_path,
                output_bedrock_path=bedrock_path,
                metadata={},
                validation_results={},
                created_at=datetime.now(),
                current_agent=None,
            )

            agent = ReviewerAgent()
            result = agent.execute(context)

            assert isinstance(result, AgentOutput)
            assert result.result.get("warning_count", 0) > 0


class TestJSONSchemaValidation:
    """Test JSON schema validation."""

    def test_json_schema_validation_missing_output(self):
        """Verify JSON validation handles missing output directory."""
        agent = ReviewerAgent()
        issues = agent._validate_json_schemas(Path("/nonexistent"))

        assert len(issues) > 0
        assert any(i.issue_type == "missing_dir" for i in issues)

    def test_json_schema_validation_valid_block(self):
        """Verify JSON validation accepts valid block schema."""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            blocks_dir = job_dir / "blocks"
            blocks_dir.mkdir(parents=True)

            valid_block = {
                "format_version": "1.20.10",
                "minecraft:block": {
                    "description": {"identifier": "modporter:test"},
                    "components": {"minecraft:unit_cube": {}},
                },
            }
            block_file = blocks_dir / "test.json"
            block_file.write_text(json.dumps(valid_block))

            agent = ReviewerAgent()
            issues = agent._validate_json_schemas(job_dir)

            has_error = any(i.severity == "error" for i in issues)
            assert not has_error


class TestTypeScriptCompilation:
    """Test TypeScript compilation check."""

    def test_typescript_compilation_no_file(self):
        """Verify tsc handles missing file gracefully."""
        agent = ReviewerAgent()
        issues = agent._run_tsc(Path("/nonexistent.ts"))

        assert len(issues) == 0


class TestScriptAPIVerification:
    """Test Script API method usage verification."""

    def test_script_api_verification_no_file(self):
        """Verify Script API check handles missing file gracefully."""
        agent = ReviewerAgent()
        issues = agent._verify_script_api_usage(Path("/nonexistent.ts"))

        assert len(issues) == 0

    def test_script_api_verification_valid_api(self):
        """Verify Script API check accepts valid API usage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ts_file = Path(tmpdir) / "test.ts"
            ts_file.write_text("""
import { Entity, Block } from '@minecraft/server';
export class Test {
    getBlock(): Block {
        return null;
    }
}
""")

            agent = ReviewerAgent()
            issues = agent._verify_script_api_usage(ts_file)

            assert isinstance(issues, list)


class TestIssueFlagging:
    """Test issue flagging with line numbers."""

    def test_issue_flagging(self):
        """Verify issues are flagged with line numbers."""
        issue = ValidationIssue(
            issue_type="test",
            message="Test error",
            line=10,
            column=5,
            severity="error",
            file_path="test.ts",
        )

        assert issue.line == 10
        assert issue.column == 5
        assert issue.severity == "error"

        issue_dict = issue.to_dict()
        assert issue_dict["line"] == 10
        assert issue_dict["severity"] == "error"


class TestQualityScoreGeneration:
    """Test quality score calculation."""

    def test_quality_score_no_issues(self):
        """Verify quality score is 100 with no issues."""
        agent = ReviewerAgent()
        score = agent._calculate_quality_score([])

        assert score == 100

    def test_quality_score_with_errors(self):
        """Verify quality score deduction for errors."""
        issues = [
            ValidationIssue("test", "error 1", severity="error"),
            ValidationIssue("test", "error 2", severity="error"),
        ]
        agent = ReviewerAgent()
        score = agent._calculate_quality_score(issues)

        assert score == 80

    def test_quality_score_with_warnings(self):
        """Verify quality score deduction for warnings."""
        issues = [
            ValidationIssue("test", "warning 1", severity="warning"),
            ValidationIssue("test", "warning 2", severity="warning"),
            ValidationIssue("test", "warning 3", severity="warning"),
            ValidationIssue("test", "warning 4", severity="warning"),
        ]
        agent = ReviewerAgent()
        score = agent._calculate_quality_score(issues)

        assert score == 100 - (4 * 3)

    def test_quality_score_minimum(self):
        """Verify quality score never goes below 0."""
        issues = [ValidationIssue("test", f"error {i}", severity="error") for i in range(20)]
        agent = ReviewerAgent()
        score = agent._calculate_quality_score(issues)

        assert score == 0


class TestOutputValidation:
    """Test output schema validation."""

    def test_output_validation(self):
        """Verify output passes schema validation."""
        output_data = {
            "agent_name": "reviewer",
            "success": True,
            "result": {"quality_score": 100, "total_issues": 0},
            "errors": [],
            "execution_time_ms": 100,
        }

        validated = AgentOutput(**output_data)

        assert validated.agent_name == "reviewer"
        assert validated.success is True
        assert validated.errors == []


class TestTemperatureConfiguration:
    """Test temperature=0 configuration."""

    def test_temperature_zero(self):
        """Verify temperature=0 is used."""
        agent = ReviewerAgent()

        assert agent.temperature == 0.0

        agent2 = ReviewerAgent(temperature=0.0)
        assert agent2.temperature == 0.0


class TestFixSuggestions:
    """Test auto-fix suggestion generation."""

    def test_fix_suggestions_eslint(self):
        """Verify ESLint fix suggestions."""
        issues = [ValidationIssue("eslint", "test", severity="error")]
        agent = ReviewerAgent()
        suggestions = agent._generate_fix_suggestions(issues)

        assert "eslint" in suggestions

    def test_fix_suggestions_typescript(self):
        """Verify TypeScript fix suggestions."""
        issues = [ValidationIssue("typescript", "test", severity="error")]
        agent = ReviewerAgent()
        suggestions = agent._generate_fix_suggestions(issues)

        assert "typescript" in suggestions


class TestConvenienceFunction:
    """Test convenience review function."""

    def test_review_function(self):
        """Verify review convenience function works."""
        from qa.reviewer import review

        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            java_path = job_dir / "source.java"
            bedrock_path = job_dir / "bedrock"

            bedrock_path.mkdir(parents=True)
            java_path.write_text("// Test")

            context = QAContext(
                job_id="test-func",
                job_dir=job_dir,
                source_java_path=java_path,
                output_bedrock_path=bedrock_path,
                metadata={},
                validation_results={},
                created_at=datetime.now(),
                current_agent=None,
            )

            result = review(context)
            assert isinstance(result, AgentOutput)


class TestValidationResultsStorage:
    """Test that validation results are stored in context."""

    def test_stores_validation_results(self):
        """Verify results stored in context.validation_results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            java_path = job_dir / "source.java"
            bedrock_path = job_dir / "bedrock"

            bedrock_path.mkdir(parents=True)
            java_path.write_text("// Test")

            context = QAContext(
                job_id="test-store",
                job_dir=job_dir,
                source_java_path=java_path,
                output_bedrock_path=bedrock_path,
                metadata={},
                validation_results={},
                created_at=datetime.now(),
                current_agent=None,
            )

            agent = ReviewerAgent()
            agent.execute(context)

            assert "reviewer" in context.validation_results
            assert "quality_score" in context.validation_results["reviewer"]
