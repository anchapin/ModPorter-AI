from qa.hooks import QAIntegrationHook, run_post_conversion_qa
from qa.context import QAContext


class TestHookDiscoversFiles:
    def test_hook_discovers_java_files(self, tmp_path):
        source_dir = tmp_path / "source_java"
        source_dir.mkdir()
        (source_dir / "Main.java").write_text("public class Main {}")
        (source_dir / "Helper.java").write_text("public class Helper {}")

        hook = QAIntegrationHook()
        java_files = hook._discover_java_files(tmp_path)

        assert len(java_files) == 2
        assert any(f.name == "Main.java" for f in java_files)
        assert any(f.name == "Helper.java" for f in java_files)

    def test_hook_discovers_bedrock_files(self, tmp_path):
        behavior_dir = tmp_path / "behavior_pack" / "functions"
        behavior_dir.mkdir(parents=True)
        (behavior_dir / "test.mcfunction").write_text("say hello")

        resource_dir = tmp_path / "resource_pack" / "textures"
        resource_dir.mkdir(parents=True)
        (resource_dir / "block").mkdir()
        (resource_dir / "block" / "test.png").write_text("fake png")

        hook = QAIntegrationHook()
        bedrock_files = hook._discover_bedrock_files(tmp_path)

        assert len(bedrock_files) == 2
        assert any("test.mcfunction" in str(f) for f in bedrock_files)
        assert any("test.png" in str(f) for f in bedrock_files)


class TestHookCreatesQAContext:
    def test_hook_creates_qa_context(self, tmp_path):
        source_dir = tmp_path / "source_java"
        source_dir.mkdir()
        (source_dir / "Main.java").write_text("public class Main {}")

        behavior_dir = tmp_path / "behavior_pack"
        behavior_dir.mkdir()
        (behavior_dir / "manifest.json").write_text("{}")

        hook = QAIntegrationHook()
        context = hook.create_qa_context_from_job_dir(tmp_path)

        assert context.job_id == tmp_path.name
        assert context.metadata["source_java_count"] == 1
        assert context.metadata["output_bedrock_count"] == 1


class TestHookReturnsSummary:
    def test_hook_returns_summary(self, tmp_path):
        hook = QAIntegrationHook()

        mock_context = QAContext(
            job_id="test-job",
            job_dir=tmp_path,
            source_java_path=tmp_path,
            output_bedrock_path=tmp_path,
        )
        mock_context.validation_results = {
            "translator": {"success": True},
            "reviewer": {"success": True},
            "tester": {"success": False, "error": "Test failed"},
            "semantic_checker": {"skipped": True},
        }

        summary = hook._create_summary(mock_context)

        assert summary["job_id"] == "test-job"
        assert summary["overall_success"] is False
        assert len(summary["successful_agents"]) == 2
        assert len(summary["failed_agents"]) == 1
        assert len(summary["skipped_agents"]) == 1

    def test_hook_disabled_returns_skipped(self, tmp_path):
        hook = QAIntegrationHook(enabled=False)
        result = hook.run_post_conversion_qa(tmp_path)

        assert result["skipped"] is True
        assert result["reason"] == "QA disabled"


class TestRunPostConversionQAFunction:
    def test_run_post_conversion_qa_function(self, tmp_path):
        result = run_post_conversion_qa(tmp_path, enabled=False)
        assert result["skipped"] is True
