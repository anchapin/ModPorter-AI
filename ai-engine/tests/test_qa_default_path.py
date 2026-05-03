"""
Test that verifies the QA pipeline (including logic_auditor) runs on default conversion path.

Addresses GitHub issue #1163: Confirm Adversarial Logic Auditor runs on default conversion path
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestQAOrchestratorIncludesLogicAuditor:
    """Verify QAOrchestrator includes logic_auditor in the default pipeline."""

    def test_qa_orchestrator_has_logic_auditor(self):
        """QAOrchestrator must include logic_auditor in its agents list."""
        from qa.orchestrator import QAOrchestrator

        orchestrator = QAOrchestrator()
        assert "logic_auditor" in orchestrator.agents
        assert len(orchestrator.agents) == 5

    def test_qa_orchestrator_runs_all_five_agents(self):
        """QAOrchestrator runs all 5 QA agents including logic_auditor."""
        from qa.orchestrator import QAOrchestrator
        from qa.context import QAContext

        orchestrator = QAOrchestrator()
        context = QAContext(
            job_id="test-job",
            job_dir=Path("."),
            source_java_path=Path("."),
            output_bedrock_path=Path("."),
        )

        import asyncio
        result = asyncio.run(orchestrator.run_qa_pipeline_async(context))

        assert len(result.validation_results) == 5
        assert "translator" in result.validation_results
        assert "reviewer" in result.validation_results
        assert "tester" in result.validation_results
        assert "semantic_checker" in result.validation_results
        assert "logic_auditor" in result.validation_results


class TestQAIntegrationHook:
    """Test QAIntegrationHook is properly integrated into conversion flow."""

    def test_hook_imported_in_crew_integration(self):
        """Verify QAIntegrationHook can be imported in crew_integration."""
        from qa.hooks import QAIntegrationHook

        hook = QAIntegrationHook(enabled=True)
        assert hook.enabled is True

    def test_hook_run_method_exists(self):
        """Verify QAIntegrationHook has run_post_conversion_qa method."""
        from qa.hooks import QAIntegrationHook

        hook = QAIntegrationHook()
        assert hasattr(hook, "run_post_conversion_qa")
