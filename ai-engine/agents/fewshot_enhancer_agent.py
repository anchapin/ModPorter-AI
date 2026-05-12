"""
Few-Shot Enhancer Agent for PortKit

Uses frontier AI models via OpenRouter to provide intelligent first-pass conversion.
This agent integrates premium_client.py into the crew workflow for hybrid conversion.

Usage:
    from agents.fewshot_enhancer_agent import FewShotEnhancerAgent

    agent = FewShotEnhancerAgent()
    result = agent.enhance(java_source="public class MyMod {}", instruction="Custom sword mod")
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from utils.logging_config import get_agent_logger

logger = get_agent_logger("fewshot_enhancer")

# Few-shot examples are imported from premium_client to avoid duplication
try:
    from mmsd.premium_client import (
        FEW_SHOT_EXAMPLES,
        MODEL_CONFIGS,
        PortKitPremium,
        ConversionResult,
    )
except ImportError:
    try:
        from ai_engine.mmsd.premium_client import (
            FEW_SHOT_EXAMPLES,
            MODEL_CONFIGS,
            PortKitPremium,
            ConversionResult,
        )
    except ImportError:
        logger.warning("premium_client not available, few-shot enhancement disabled")
        FEW_SHOT_EXAMPLES = []
        MODEL_CONFIGS = {}
        PortKitPremium = None
        ConversionResult = None


@dataclass
class EnhancementResult:
    """Result from few-shot enhancement."""

    success: bool
    reasoning: str
    bedrock_manifest: str
    bedrock_script: str
    model_used: str
    latency_ms: int
    error: str = ""
    quality_score: float = 0.0  # Estimated quality 0-10


class FewShotEnhancerAgent:
    """
    Few-shot enhancement agent that uses frontier AI models for initial conversion.

    This agent provides a fast, cost-effective first pass for the conversion pipeline.
    It generates an initial Bedrock draft that can be refined by other agents.

    Integration Points:
    - JavaAnalyzerAgent → Produces AST, this agent uses Java source directly
    - LogicTranslatorAgent → Refines the output from this agent
    - QAValidatorAgent → Validates the final output

    Cost: ~$0.006 per enhancement
    Speed: ~40 seconds
    Quality: 6-7/10 (good for simple mods, needs refinement for complex ones)
    """

    _instance = None

    def __init__(self, model: str = "deepseek-v4-pro"):
        """
        Initialize the FewShotEnhancerAgent.

        Args:
            model: Model to use for few-shot enhancement.
                  Options: deepseek-v4-pro, deepseek-v4-flash, kimi-k2, glm-5
        """
        self.model = model
        self.logger = logger
        self._client = None
        self._api_key = None

    def _get_client(self) -> Optional[PortKitPremium]:
        """Get or create OpenRouter client."""
        if self._client is None:
            api_key = os.environ.get("OPENROUTER_API_KEY", "")
            if not api_key:
                self.logger.warning("OPENROUTER_API_KEY not set, few-shot enhancement unavailable")
                return None
            self._api_key = api_key
            try:
                self._client = PortKitPremium(api_key=api_key, model=self.model)
            except Exception as e:
                self.logger.error(f"Failed to create premium client: {e}")
                return None
        return self._client

    def enhance(
        self,
        java_source: str,
        instruction: str,
        model: Optional[str] = None,
        use_fallback: bool = True,
    ) -> EnhancementResult:
        """
        Generate initial Bedrock conversion using few-shot prompting.

        Args:
            java_source: Java mod source code
            instruction: Natural language description of the mod
            model: Override model to use
            use_fallback: Use fallback models on rate limit

        Returns:
            EnhancementResult with draft conversion
        """
        client = self._get_client()
        if not client:
            return EnhancementResult(
                success=False,
                reasoning="",
                bedrock_manifest="",
                bedrock_script="",
                model_used=self.model,
                latency_ms=0,
                error="OPENROUTER_API_KEY not configured",
                quality_score=0.0,
            )

        try:
            actual_model = model or self.model
            self.logger.info(f"Enhancing with model: {actual_model}")

            result = client.convert(
                instruction=instruction,
                java_source=java_source,
                model=actual_model,
            )

            if result.success:
                return EnhancementResult(
                    success=True,
                    reasoning=result.reasoning,
                    bedrock_manifest=result.bedrock_manifest,
                    bedrock_script=result.bedrock_script,
                    model_used=result.model_used,
                    latency_ms=result.latency_ms,
                    error="",
                    quality_score=self._estimate_quality(result),
                )
            else:
                return EnhancementResult(
                    success=False,
                    reasoning=result.reasoning,
                    bedrock_manifest="",
                    bedrock_script="",
                    model_used=actual_model,
                    latency_ms=result.latency_ms,
                    error=result.error or "Conversion failed",
                    quality_score=0.0,
                )

        except Exception as e:
            self.logger.error(f"Enhancement failed: {e}")
            return EnhancementResult(
                success=False,
                reasoning="",
                bedrock_manifest="",
                bedrock_script="",
                model_used=model or self.model,
                latency_ms=0,
                error=str(e),
                quality_score=0.0,
            )

    def enhance_batch(
        self,
        conversions: List[Dict[str, str]],
        model: Optional[str] = None,
    ) -> List[EnhancementResult]:
        """
        Enhance multiple conversions in batch.

        Args:
            conversions: List of {"java_source": str, "instruction": str}
            model: Model to use

        Returns:
            List of EnhancementResult
        """
        results = []
        for conv in conversions:
            result = self.enhance(
                java_source=conv.get("java_source", ""),
                instruction=conv.get("instruction", "Custom mod"),
                model=model,
            )
            results.append(result)
        return results

    def estimate_cost(
        self,
        instruction: str,
        java_source: str,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Estimate API cost for an enhancement."""
        client = self._get_client()
        if not client:
            return {"error": "Client not available"}

        return client.estimate_cost(
            instruction=instruction,
            java_source=java_source,
            model=model,
        )

    def _estimate_quality(self, result: ConversionResult) -> float:
        """
        Estimate output quality based on completeness.

        Quality indicators:
        - Has manifest with proper format_version: +2
        - Has script with event handlers: +2
        - Has reasoning with conversion plan: +2
        - Script uses proper @minecraft/server imports: +1
        - No obvious errors in output: +1
        """
        score = 0.0

        if result.bedrock_manifest:
            if "format_version" in result.bedrock_manifest:
                score += 2.0
            if "header" in result.bedrock_manifest and "modules" in result.bedrock_manifest:
                score += 1.0

        if result.bedrock_script:
            if "@minecraft/server" in result.bedrock_script:
                score += 1.0
            if any(
                keyword in result.bedrock_script
                for keyword in ["world.afterEvents", "system.runInterval", "player.on"]
            ):
                score += 1.5
            if "import" in result.bedrock_script and "from" in result.bedrock_script:
                score += 0.5

        if result.reasoning:
            if "Conversion Plan" in result.reasoning or "##" in result.reasoning:
                score += 1.0

        return min(score, 10.0)

    def close(self):
        """Close the client connection."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class FewShotEnhancerTools:
    """
    Tool wrapper for CrewAI integration.

    Provides tools that can be used by the crew orchestrator.
    """

    @staticmethod
    def enhance_tool(java_source: str, instruction: str, model: str = "deepseek-v4-pro") -> str:
        """
        CrewAI tool for few-shot enhancement.

        Usage in crew:
            from crewai import Agent, Task

            enhancer = Agent(
                role="Enhancer",
                goal="Generate initial Bedrock conversion draft",
                tools=[FewShotEnhancerTools.enhance_tool]
            )

            enhancement_task = Task(
                description="Enhance this Java mod: {java_source}",
                agent=enhancer,
                tool=FewShotEnhancerTools.enhance_tool
            )
        """
        agent = FewShotEnhancerAgent(model=model)
        result = agent.enhance(java_source=java_source, instruction=instruction)
        agent.close()

        if result.success:
            return f"""Enhanced Conversion (model: {result.model_used}, {result.latency_ms}ms)

## Reasoning
{result.reasoning}

## Bedrock Manifest
```json
{result.bedrock_manifest}
```

## Bedrock Script
```javascript
{result.bedrock_script}
```

Quality Score: {result.quality_score}/10
"""
        else:
            return f"Enhancement failed: {result.error}"

    @staticmethod
    def get_tools() -> List[callable]:
        """Return list of tools for CrewAI registration."""
        return [
            FewShotEnhancerTools.enhance_tool,
        ]
