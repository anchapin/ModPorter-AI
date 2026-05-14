"""
Steering Integration for LogicTranslator Agent.

This module provides LangChain tool wrappers for applying SAE-based feature steering
during Java to Bedrock code conversion. Integrates with LogicTranslatorAgent
to suppress Java idioms in generated Bedrock code.

Usage:
    from agents.logic_translator.tools import (
        SteeringTools,
        apply_steering_to_translation_tool,
    )

    # Apply steering during translation
    result = SteeringTools.apply_steering_tool(java_code, bedrock_code)
"""

import json
from typing import List, Optional

from typing import ClassVar

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field

from steering import (
    SteeringPipelineConfig,
    get_steering_pipeline,
    configure_steering_pipeline,
    SteeringEvaluator,
    evaluate_steering_effectiveness,
)

from utils.logging_config import get_agent_logger

logger = get_agent_logger("logic_translator.steering_tools")


class SteeringTools:
    """
    Collection of LangChain tools for SAE-based feature steering.

    These tools integrate with the LogicTranslatorAgent to provide
    real-time idiom suppression during code conversion.
    """

    @staticmethod
    def get_steering_enabled() -> bool:
        """Check if steering is enabled."""
        pipeline = get_steering_pipeline()
        return pipeline._steering_enabled

    @staticmethod
    def configure_steering(
        sae_endpoint: Optional[str] = None,
        sae_api_key: Optional[str] = None,
        steering_scale: float = 2.0,
        suppression_targets: Optional[List[str]] = None,
        inference_backend: str = "openai_compatible",
        inference_endpoint: Optional[str] = None,
    ) -> str:
        """
        Configure the steering pipeline.

        Args:
            sae_endpoint: SAE service endpoint URL
            sae_api_key: API key for SAE service
            steering_scale: Steering vector magnitude (default 2.0)
            suppression_targets: List of idiom types to suppress
            inference_backend: Backend type (openai_compatible, vllm, sglang, transformers)
            inference_endpoint: Custom inference endpoint URL

        Returns:
            JSON string with configuration status
        """
        try:
            config = SteeringPipelineConfig(
                sae_endpoint=sae_endpoint,
                sae_api_key=sae_api_key,
                steering_scale=steering_scale,
                suppression_targets=suppression_targets
                or [
                    "java_forge_suppress",
                    "java_class_suppress",
                ],
                inference_backend=inference_backend,
                inference_endpoint=inference_endpoint,
            )

            pipeline = configure_steering_pipeline(config)
            pipeline.enable_steering()

            return json.dumps(
                {
                    "success": True,
                    "steering_enabled": True,
                    "config": {
                        "steering_scale": steering_scale,
                        "suppression_targets": config.suppression_targets,
                        "inference_backend": inference_backend,
                    },
                }
            )

        except Exception as e:
            logger.error(f"Failed to configure steering: {e}")
            return json.dumps(
                {
                    "success": False,
                    "error": str(e),
                    "steering_enabled": False,
                }
            )

    @staticmethod
    def apply_steering(
        java_code: str,
        bedrock_code: str,
        steering_features: Optional[List[int]] = None,
    ) -> str:
        """
        Apply steering to a Java-to-Bedrock conversion and evaluate.

        Args:
            java_code: Original Java code
            bedrock_code: Generated Bedrock code
            steering_features: Optional feature IDs used for steering

        Returns:
            JSON string with evaluation results and steering metadata
        """
        try:
            pipeline = get_steering_pipeline()
            evaluator = SteeringEvaluator()

            # Evaluate the conversion
            result = evaluator.evaluate_generation(
                original_java=java_code,
                generated_bedrock=bedrock_code,
                steering_applied=pipeline._steering_enabled,
                steering_features=steering_features,
            )

            return json.dumps(
                {
                    "success": True,
                    "evaluation": result.to_dict(),
                    "steering_applied": pipeline._steering_enabled,
                }
            )

        except Exception as e:
            logger.error(f"Failed to apply steering evaluation: {e}")
            return json.dumps(
                {
                    "success": False,
                    "error": str(e),
                }
            )

    @staticmethod
    def get_steering_stats() -> str:
        """
        Get current steering pipeline statistics.

        Returns:
            JSON string with pipeline stats
        """
        try:
            pipeline = get_steering_pipeline()
            stats = pipeline.get_stats()

            return json.dumps(
                {
                    "success": True,
                    "stats": stats,
                }
            )

        except Exception as e:
            logger.error(f"Failed to get steering stats: {e}")
            return json.dumps(
                {
                    "success": False,
                    "error": str(e),
                }
            )

    @staticmethod
    def enable_steering() -> str:
        """Enable steering globally."""
        try:
            pipeline = get_steering_pipeline()
            pipeline.enable_steering()

            return json.dumps(
                {
                    "success": True,
                    "steering_enabled": True,
                }
            )

        except Exception as e:
            logger.error(f"Failed to enable steering: {e}")
            return json.dumps(
                {
                    "success": False,
                    "error": str(e),
                }
            )

    @staticmethod
    def disable_steering() -> str:
        """Disable steering globally."""
        try:
            pipeline = get_steering_pipeline()
            pipeline.disable_steering()

            return json.dumps(
                {
                    "success": True,
                    "steering_enabled": False,
                }
            )

        except Exception as e:
            logger.error(f"Failed to disable steering: {e}")
            return json.dumps(
                {
                    "success": False,
                    "error": str(e),
                }
            )


# ─────────────────────────────────────────────────────────────────────────────
# Typed args_schema models — one per LangChain tool wrapper
# ─────────────────────────────────────────────────────────────────────────────


class ConfigureSteeringInput(BaseModel):
    """Args for :class:`ConfigureSteeringTool`."""

    model_config = ConfigDict(extra="forbid")
    sae_endpoint: Optional[str] = Field(
        default=None,
        description="Optional SAE service endpoint URL.",
    )
    sae_api_key: Optional[str] = Field(
        default=None,
        description="Optional API key for the SAE service.",
    )
    steering_scale: float = Field(
        default=2.0,
        description="Steering vector magnitude (default 2.0).",
    )
    suppression_targets: Optional[List[str]] = Field(
        default=None,
        description=(
            'Idiom types to suppress, e.g. ["java_forge_suppress", '
            '"java_class_suppress"]. None uses pipeline defaults.'
        ),
    )
    inference_backend: str = Field(
        default="openai_compatible",
        description=(
            "Inference backend identifier: openai_compatible, vllm, sglang, or transformers."
        ),
    )
    inference_endpoint: Optional[str] = Field(
        default=None,
        description="Optional custom inference endpoint URL.",
    )


class ApplySteeringInput(BaseModel):
    """Args for :class:`ApplySteeringTool`."""

    model_config = ConfigDict(extra="forbid")
    java_code: str = Field(
        min_length=1,
        description="Original Java source code that was converted.",
    )
    bedrock_code: str = Field(
        min_length=1,
        description="Generated Bedrock JavaScript code to evaluate.",
    )


class _NoArgs(BaseModel):
    """Empty input schema for steering tools that take no arguments."""

    model_config = ConfigDict(extra="forbid")


class EvaluateConversionQualityInput(BaseModel):
    """Args for :class:`EvaluateConversionQualityTool`."""

    model_config = ConfigDict(extra="forbid")
    original_java: str = Field(
        min_length=1,
        description="Original Java source code.",
    )
    generated_bedrock: str = Field(
        min_length=1,
        description="Generated Bedrock JavaScript / JSON code.",
    )
    steering_applied: bool = Field(
        default=True,
        description="Whether SAE steering was used during generation.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Typed BaseTool subclasses — replace the previous @tool decorated wrappers
# ─────────────────────────────────────────────────────────────────────────────


class _BaseSteeringTool(BaseTool):
    """Common scaffolding for the steering typed tool wrappers."""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ConfigureSteeringTool(_BaseSteeringTool):
    """Configure SAE-based feature steering for Java idiom suppression."""

    name: str = "configure_steering_tool"
    description: str = (
        "Configure SAE-based feature steering. "
        "Args: sae_endpoint, sae_api_key, steering_scale, "
        "suppression_targets, inference_backend, inference_endpoint."
    )
    args_schema: ClassVar[type[BaseModel]] = ConfigureSteeringInput

    def _run(  # type: ignore[override]
        self,
        sae_endpoint: Optional[str] = None,
        sae_api_key: Optional[str] = None,
        steering_scale: float = 2.0,
        suppression_targets: Optional[List[str]] = None,
        inference_backend: str = "openai_compatible",
        inference_endpoint: Optional[str] = None,
    ) -> str:
        return SteeringTools.configure_steering(
            sae_endpoint=sae_endpoint,
            sae_api_key=sae_api_key,
            steering_scale=steering_scale,
            suppression_targets=suppression_targets,
            inference_backend=inference_backend,
            inference_endpoint=inference_endpoint,
        )


class ApplySteeringTool(_BaseSteeringTool):
    """Evaluate whether Java idioms were properly suppressed in the conversion."""

    name: str = "apply_steering_tool"
    description: str = (
        "Apply SAE-based steering evaluation to a Java→Bedrock conversion. "
        "Returns suppression rate, quality score, and warnings. "
        "Args: java_code (str, required), bedrock_code (str, required)."
    )
    args_schema: ClassVar[type[BaseModel]] = ApplySteeringInput

    def _run(self, java_code: str, bedrock_code: str) -> str:  # type: ignore[override]
        return SteeringTools.apply_steering(java_code, bedrock_code)


class GetSteeringStatsTool(_BaseSteeringTool):
    """Return current steering pipeline statistics."""

    name: str = "get_steering_stats_tool"
    description: str = (
        "Get steering pipeline statistics: generation counts, steering "
        "applications, feature tracking. Takes no arguments."
    )
    args_schema: ClassVar[type[BaseModel]] = _NoArgs

    def _run(self) -> str:  # type: ignore[override]
        return SteeringTools.get_steering_stats()


class EnableSteeringTool(_BaseSteeringTool):
    """Enable SAE-based feature steering globally."""

    name: str = "enable_steering_tool"
    description: str = "Enable SAE-based feature steering globally. Takes no arguments."
    args_schema: ClassVar[type[BaseModel]] = _NoArgs

    def _run(self) -> str:  # type: ignore[override]
        return SteeringTools.enable_steering()


class DisableSteeringTool(_BaseSteeringTool):
    """Disable SAE-based feature steering globally."""

    name: str = "disable_steering_tool"
    description: str = "Disable SAE-based feature steering globally. Takes no arguments."
    args_schema: ClassVar[type[BaseModel]] = _NoArgs

    def _run(self) -> str:  # type: ignore[override]
        return SteeringTools.disable_steering()


class EvaluateConversionQualityTool(_BaseSteeringTool):
    """Evaluate the quality of a Java-to-Bedrock conversion."""

    name: str = "evaluate_conversion_quality_tool"
    description: str = (
        "Evaluate Java→Bedrock conversion quality. Returns overall score "
        "(0-100) and per-category metrics. "
        "Args: original_java (str, required), generated_bedrock (str, required), "
        "steering_applied (bool, default True)."
    )
    args_schema: ClassVar[type[BaseModel]] = EvaluateConversionQualityInput

    def _run(  # type: ignore[override]
        self,
        original_java: str,
        generated_bedrock: str,
        steering_applied: bool = True,
    ) -> str:
        result = evaluate_steering_effectiveness(
            java_code=original_java,
            bedrock_code=generated_bedrock,
            steering_applied=steering_applied,
        )
        return result.to_json()


# ─────────────────────────────────────────────────────────────────────────────
# Module-level tool instances — preserve the names the wider codebase imports
# ─────────────────────────────────────────────────────────────────────────────

configure_steering_tool: ConfigureSteeringTool = ConfigureSteeringTool()
apply_steering_tool: ApplySteeringTool = ApplySteeringTool()
get_steering_stats_tool: GetSteeringStatsTool = GetSteeringStatsTool()
enable_steering_tool: EnableSteeringTool = EnableSteeringTool()
disable_steering_tool: DisableSteeringTool = DisableSteeringTool()
evaluate_conversion_quality_tool: EvaluateConversionQualityTool = EvaluateConversionQualityTool()


def register_steering_tools(agent) -> None:
    """Register all steering tools with a LangChain agent.

    Args:
        agent: LangChain agent instance to register tools with

    Usage:
        from agents.logic_translator.translator import LogicTranslatorAgent

        agent = LogicTranslatorAgent()
        register_steering_tools(agent)
    """
    steering_tools = [
        configure_steering_tool,
        apply_steering_tool,
        get_steering_stats_tool,
        enable_steering_tool,
        disable_steering_tool,
        evaluate_conversion_quality_tool,
    ]

    for steering_tool in steering_tools:
        if hasattr(agent, "tools"):
            agent.tools.append(steering_tool)
        logger.info(f"Registered steering tool: {steering_tool.name}")
