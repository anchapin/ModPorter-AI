import pytest
import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from qa.orchestrator import QAOrchestrator
from qa.context import QAContext
from qa.validators import AgentOutput
from utils.error_recovery import CircuitBreaker, CircuitBreakerOpenError


@pytest.fixture
def orchestrator():
    return QAOrchestrator()


@pytest.fixture
def context():
    return QAContext(
        job_id="test-job",
        job_dir=Path("."),
        source_java_path=Path("."),
        output_bedrock_path=Path("."),
    )


class TestOrchestratorRunsAllAgents:
    @pytest.mark.asyncio
    async def test_orchestrator_runs_all_agents(self, orchestrator, context):
        result = await orchestrator.run_qa_pipeline_async(context)
        assert len(result.validation_results) == 4
        assert "translator" in result.validation_results
        assert "reviewer" in result.validation_results
        assert "tester" in result.validation_results
        assert "semantic_checker" in result.validation_results


class TestContextPassesBetweenAgents:
    @pytest.mark.asyncio
    async def test_context_current_agent_updates(self, orchestrator, context):
        agent_order = []

        original_execute = orchestrator._execute_agent_placeholder

        async def track_agent(ctx, agent_name):
            agent_order.append(ctx.current_agent)
            return await original_execute(ctx, agent_name)

        orchestrator._execute_agent_placeholder = track_agent
        await orchestrator.run_qa_pipeline_async(context)

        assert agent_order == [
            "translator",
            "reviewer",
            "tester",
            "semantic_checker",
        ]


class TestValidationResultsMerged:
    @pytest.mark.asyncio
    async def test_validation_results_contain_all_results(self, orchestrator, context):
        result = await orchestrator.run_qa_pipeline_async(context)
        for agent in orchestrator.agents:
            assert agent in result.validation_results
            assert result.validation_results[agent]["success"] is True


class TestCircuitBreakerOpens:
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self):
        from utils.error_recovery import CircuitState

        orch = QAOrchestrator()
        breaker = orch._breakers["translator"]
        breaker._failure_count = 3
        breaker._state = CircuitState.OPEN

        ctx = QAContext(
            job_id="test-job",
            job_dir=Path("."),
            source_java_path=Path("."),
            output_bedrock_path=Path("."),
        )

        result = await orch.run_qa_pipeline_async(ctx)
        assert result.validation_results["translator"]["skipped"] is True


class TestTimeoutEnforced:
    @pytest.mark.asyncio
    async def test_timeout_handled_gracefully(self):
        orch = QAOrchestrator(timeout_seconds=1)

        async def slow_agent(ctx, agent_name):
            await asyncio.sleep(5)
            return {
                "agent_name": agent_name,
                "success": True,
                "result": {},
                "errors": [],
                "execution_time_ms": 5000,
            }

        orch._execute_agent_placeholder = slow_agent

        ctx = QAContext(
            job_id="test-job",
            job_dir=Path("."),
            source_java_path=Path("."),
            output_bedrock_path=Path("."),
        )

        result = await orch.run_qa_pipeline_async(ctx)
        assert result.validation_results["translator"]["error"] == "Timeout"
