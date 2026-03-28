import asyncio
import logging
from typing import Dict, Any, List
import time
import structlog

from qa.context import QAContext
from qa.validators import AgentOutput, validate_agent_output
from utils.error_recovery import CircuitBreaker, CircuitBreakerOpenError

logger = structlog.get_logger(__name__)


class QAOrchestrator:
    def __init__(
        self,
        timeout_seconds: int = 300,
    ):
        self.timeout_seconds = timeout_seconds
        self.agents: List[str] = ["translator", "reviewer", "tester", "semantic_checker"]
        self._breakers: Dict[str, CircuitBreaker] = {}
        for agent_name in self.agents:
            self._breakers[agent_name] = CircuitBreaker(
                name=f"{agent_name}_agent",
                fail_max=3,
                reset_timeout=300,
            )

    def run_qa_pipeline(self, context: QAContext) -> QAContext:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                raise RuntimeError(
                    "Cannot run sync version in async context. Use run_qa_pipeline_async instead."
                )
            return loop.run_until_complete(self.run_qa_pipeline_async(context))
        except RuntimeError:
            return asyncio.run(self.run_qa_pipeline_async(context))

    async def run_qa_pipeline_async(self, context: QAContext) -> QAContext:
        for agent_name in self.agents:
            context.current_agent = agent_name
            logger.info("Running agent", agent=agent_name, job_id=context.job_id)

            try:
                agent_output = await self.run_agent(context, agent_name)
                validated = validate_agent_output(agent_output)

                context.validation_results[agent_name] = {
                    "success": validated.success,
                    "result": validated.result,
                    "errors": validated.errors,
                    "execution_time_ms": validated.execution_time_ms,
                }
                logger.info(
                    "Agent completed",
                    agent=agent_name,
                    success=validated.success,
                    job_id=context.job_id,
                )
            except CircuitBreakerOpenError as e:
                logger.error("Agent circuit open, skipping", agent=agent_name, error=str(e))
                context.validation_results[agent_name] = {
                    "success": False,
                    "error": "Circuit breaker open",
                    "skipped": True,
                }
            except asyncio.TimeoutError:
                logger.error("Agent timed out", agent=agent_name)
                context.validation_results[agent_name] = {
                    "success": False,
                    "error": "Timeout",
                }
            except Exception as e:
                logger.error("Agent failed", agent=agent_name, error=str(e))
                context.validation_results[agent_name] = {
                    "success": False,
                    "error": str(e),
                }

        context.current_agent = None
        return context

    async def run_agent(self, context: QAContext, agent_name: str) -> Dict[str, Any]:
        breaker = self._breakers[agent_name]

        async def run_with_timeout():
            return await asyncio.wait_for(
                self._execute_agent_placeholder(context, agent_name),
                timeout=self.timeout_seconds,
            )

        def run_async():
            return asyncio.run(run_with_timeout())

        try:
            if asyncio.get_event_loop().is_running():
                return await self._run_with_breaker_async(breaker, context, agent_name)
            else:
                return breaker.call(lambda: asyncio.run(run_with_timeout()))
        except CircuitBreakerOpenError:
            raise
        except RuntimeError:
            return await self._run_with_breaker_async(breaker, context, agent_name)

    async def _run_with_breaker_async(
        self, breaker: CircuitBreaker, context: QAContext, agent_name: str
    ) -> Dict[str, Any]:
        if str(breaker.state.value) == "open":
            raise CircuitBreakerOpenError(f"Circuit breaker '{agent_name}' is open")

        try:
            result = await asyncio.wait_for(
                self._execute_agent_placeholder(context, agent_name),
                timeout=self.timeout_seconds,
            )
            breaker._on_success()
            return result
        except Exception as e:
            breaker._on_failure()
            raise

    async def _execute_agent_placeholder(
        self, context: QAContext, agent_name: str
    ) -> Dict[str, Any]:
        start_time = int(time.time() * 1000)
        await asyncio.sleep(0.1)
        end_time = int(time.time() * 1000)

        return {
            "agent_name": agent_name,
            "success": True,
            "result": {
                "message": f"{agent_name} agent completed",
                "job_id": context.job_id,
            },
            "errors": [],
            "execution_time_ms": end_time - start_time,
        }
