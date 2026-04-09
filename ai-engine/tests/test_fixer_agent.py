"""Unit tests for FixerAgent."""

import json
import tempfile
from pathlib import Path
from datetime import datetime


from qa.fixer import FixerAgent, FixResult
from qa.context import QAContext
from qa.validators import AgentOutput


class TestFixerAgentImports:
    """Test that all imports work correctly."""

    def test_agent_imports(self):
        """Verify imports work correctly."""
        from qa.fixer import FixerAgent, fix

        assert FixerAgent is not None
        assert fix is not None

    def test_agent_instantiation(self):
        """Verify agent can be instantiated."""
        agent = FixerAgent()
        assert agent is not None
        assert agent.temperature == 0.0

    def test_agent_custom_temperature(self):
        """Verify agent can be instantiated with custom temperature."""
        agent = FixerAgent(temperature=0.5)
        assert agent.temperature == 0.5


class TestFixerAgentQAContext:
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
                validation_results={
                    "reviewer": {"quality_score": 80, "error_count": 2, "warning_count": 3}
                },
                created_at=datetime.now(),
                current_agent=None,
            )

            agent = FixerAgent()
            result = agent.execute(context)

            assert isinstance(result, AgentOutput)


class TestReadReviewResults:
    """Test reading review results from context."""

    def test_reads_review_results(self):
        """Verify agent reads review results from context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            java_path = job_dir / "source.java"
            bedrock_path = job_dir / "bedrock"

            bedrock_path.mkdir(parents=True)
            java_path.write_text("// Test")

            context = QAContext(
                job_id="test-review-123",
                job_dir=job_dir,
                source_java_path=java_path,
                output_bedrock_path=bedrock_path,
                metadata={},
                validation_results={
                    "reviewer": {"quality_score": 50, "error_count": 5, "warning_count": 10}
                },
                created_at=datetime.now(),
                current_agent=None,
            )

            agent = FixerAgent()
            result = agent.execute(context)

            assert "fixes_attempted" in result.result


class TestNoReviewResults:
    """Test handling when no review results exist."""

    def test_no_review_results(self):
        """Verify agent handles missing review results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            java_path = job_dir / "source.java"
            bedrock_path = job_dir / "bedrock"

            bedrock_path.mkdir(parents=True)
            java_path.write_text("// Test")

            context = QAContext(
                job_id="test-no-review",
                job_dir=job_dir,
                source_java_path=java_path,
                output_bedrock_path=bedrock_path,
                metadata={},
                validation_results={},
                created_at=datetime.now(),
                current_agent=None,
            )

            agent = FixerAgent()
            result = agent.execute(context)

            assert result.success is False
            assert len(result.errors) > 0


class TestESLintFixAttempt:
    """Test ESLint fix attempts."""

    def test_eslint_fix_attempt_no_files(self):
        """Verify ESLint fix handles no TypeScript files."""
        agent = FixerAgent()
        with tempfile.TemporaryDirectory() as tmpdir:
            results = agent._fix_eslint_issues(Path(tmpdir))
            assert len(results) > 0
            assert results[0].issue_type == "eslint"


class TestJSONSchemaFix:
    """Test JSON schema fixes."""

    def test_json_schema_fix_missing_output(self):
        """Verify JSON schema fix handles missing directory."""
        agent = FixerAgent()
        results = agent._fix_json_schema_issues(Path("/nonexistent"))
        assert len(results) > 0

    def test_json_schema_fix_valid_block(self):
        """Verify JSON schema fix works on valid block."""
        with tempfile.TemporaryDirectory() as tmpdir:
            blocks_dir = Path(tmpdir) / "blocks"
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

            agent = FixerAgent()
            results = agent._fix_json_schema_issues(Path(tmpdir))

            fixed = any(f.fix_applied for f in results)
            assert fixed is True

    def test_json_schema_fix_missing_keys(self):
        """Verify JSON schema fix adds missing keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            blocks_dir = Path(tmpdir) / "blocks"
            blocks_dir.mkdir(parents=True)

            invalid_block = {"minecraft:block": {"description": {}}}
            block_file = blocks_dir / "incomplete.json"
            block_file.write_text(json.dumps(invalid_block))

            agent = FixerAgent()
            results = agent._fix_json_schema_issues(Path(tmpdir))

            has_fix = any(f.fix_applied and f.issue_type == "schema" for f in results)
            assert has_fix


class TestTypeScriptFixAttempt:
    """Test TypeScript fix attempts."""

    def test_typescript_fix_attempt_no_file(self):
        """Verify TypeScript fix handles missing file gracefully."""
        agent = FixerAgent()
        results = agent._fix_typescript_issues(Path("/nonexistent"))
        assert len(results) > 0

    def test_typescript_fix_valid_file(self):
        """Verify TypeScript fix works on valid file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ts_file = Path(tmpdir) / "test.ts"
            ts_file.write_text("// Valid TypeScript\nexport class Test {}")

            agent = FixerAgent()
            results = agent._fix_typescript_issues(Path(tmpdir))

            assert isinstance(results, list)


class TestFixResult:
    """Test FixResult class."""

    def test_fix_result_creation(self):
        """Verify FixResult can be created."""
        fix = FixResult("test", "Test error", True, "Fixed", "test.ts", 10)

        assert fix.issue_type == "test"
        assert fix.original_message == "Test error"
        assert fix.fix_applied is True
        assert fix.fix_description == "Fixed"
        assert fix.file_path == "test.ts"
        assert fix.line == 10

    def test_fix_result_to_dict(self):
        """Verify FixResult converts to dict."""
        fix = FixResult("test", "Test error", True, "Fixed", "test.ts", 10)
        fix_dict = fix.to_dict()

        assert isinstance(fix_dict, dict)
        assert fix_dict["issue_type"] == "test"
        assert fix_dict["fix_applied"] is True


class TestRevalidation:
    """Test re-validation of fixes."""

    def test_revalidate_fixes(self):
        """Verify revalidation runs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bedrock_path = Path(tmpdir) / "bedrock"
            bedrock_path.mkdir(parents=True)

            agent = FixerAgent()
            reval = agent._revalidate_fixes(bedrock_path)

            assert "files_checked" in reval
            assert "validation_passed" in reval


class TestFixRate:
    """Test fix rate calculation."""

    def test_calculate_fix_rate(self):
        """Verify fix rate is calculated correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            java_path = job_dir / "source.java"
            bedrock_path = job_dir / "bedrock"

            bedrock_path.mkdir(parents=True)
            java_path.write_text("// Test")

            context = QAContext(
                job_id="test-rate",
                job_dir=job_dir,
                source_java_path=java_path,
                output_bedrock_path=bedrock_path,
                metadata={},
                validation_results={
                    "reviewer": {"quality_score": 50, "error_count": 2, "warning_count": 3}
                },
                created_at=datetime.now(),
                current_agent=None,
            )

            agent = FixerAgent()
            result = agent.execute(context)

            assert "fix_rate_percent" in result.result
            assert "fixes_applied" in result.result


class TestOutputValidation:
    """Test output schema validation."""

    def test_output_validation(self):
        """Verify output passes schema validation."""
        output_data = {
            "agent_name": "fixer",
            "success": True,
            "result": {"fixes_applied": 5, "fix_rate_percent": 80.0},
            "errors": [],
            "execution_time_ms": 100,
        }

        validated = AgentOutput(**output_data)

        assert validated.agent_name == "fixer"
        assert validated.success is True
        assert validated.errors == []


class TestTemperatureConfiguration:
    """Test temperature=0 configuration."""

    def test_temperature_zero(self):
        """Verify temperature=0 is used."""
        agent = FixerAgent()

        assert agent.temperature == 0.0

        agent2 = FixerAgent(temperature=0.0)
        assert agent2.temperature == 0.0


class TestConvenienceFunction:
    """Test convenience fix function."""

    def test_fix_function(self):
        """Verify fix convenience function works."""
        from qa.fixer import fix

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
                validation_results={
                    "reviewer": {"quality_score": 90, "error_count": 0, "warning_count": 1}
                },
                created_at=datetime.now(),
                current_agent=None,
            )

            result = fix(context)
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
                validation_results={
                    "reviewer": {"quality_score": 80, "error_count": 1, "warning_count": 2}
                },
                created_at=datetime.now(),
                current_agent=None,
            )

            agent = FixerAgent()
            agent.execute(context)

            assert "fixer" in context.validation_results
            assert "fixes_applied" in context.validation_results["fixer"]
