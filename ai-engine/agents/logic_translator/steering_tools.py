"""
Steering Integration for LogicTranslator Agent.

This module provides CrewAI tool wrappers for applying SAE-based feature steering
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
import logging
from typing import Any, Dict, List, Optional

try:
    from crewai.tools import tool
except ImportError:
    # Fallback if CrewAI not available
    def tool(func):
        return func

from steering import (
    SteeringPipeline,
    SteeringPipelineConfig,
    SteeringMode,
    get_steering_pipeline,
    configure_steering_pipeline,
    SteeringEvaluator,
    evaluate_steering_effectiveness,
    IdiomCategory,
)

from utils.logging_config import get_agent_logger

logger = get_agent_logger("logic_translator.steering_tools")


class SteeringTools:
    """
    Collection of CrewAI tools for SAE-based feature steering.

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
                suppression_targets=suppression_targets or [
                    "java_forge_suppress",
                    "java_class_suppress",
                ],
                inference_backend=inference_backend,
                inference_endpoint=inference_endpoint,
            )

            pipeline = configure_steering_pipeline(config)
            pipeline.enable_steering()

            return json.dumps({
                "success": True,
                "steering_enabled": True,
                "config": {
                    "steering_scale": steering_scale,
                    "suppression_targets": config.suppression_targets,
                    "inference_backend": inference_backend,
                },
            })

        except Exception as e:
            logger.error(f"Failed to configure steering: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "steering_enabled": False,
            })

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

            return json.dumps({
                "success": True,
                "evaluation": result.to_dict(),
                "steering_applied": pipeline._steering_enabled,
            })

        except Exception as e:
            logger.error(f"Failed to apply steering evaluation: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
            })

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

            return json.dumps({
                "success": True,
                "stats": stats,
            })

        except Exception as e:
            logger.error(f"Failed to get steering stats: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
            })

    @staticmethod
    def enable_steering() -> str:
        """Enable steering globally."""
        try:
            pipeline = get_steering_pipeline()
            pipeline.enable_steering()

            return json.dumps({
                "success": True,
                "steering_enabled": True,
            })

        except Exception as e:
            logger.error(f"Failed to enable steering: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
            })

    @staticmethod
    def disable_steering() -> str:
        """Disable steering globally."""
        try:
            pipeline = get_steering_pipeline()
            pipeline.disable_steering()

            return json.dumps({
                "success": True,
                "steering_enabled": False,
            })

        except Exception as e:
            logger.error(f"Failed to disable steering: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
            })


# CrewAI Tool Wrappers
@tool
def configure_steering_tool(config_json: str) -> str:
    """
    Configure SAE-based feature steering for Java idiom suppression.

    Args:
        config_json: JSON string with configuration:
            - sae_endpoint: Optional SAE endpoint URL
            - sae_api_key: Optional API key
            - steering_scale: Steering magnitude (default 2.0)
            - suppression_targets: List of targets like ["java_forge", "java_class"]
            - inference_backend: "openai_compatible", "vllm", "sglang", "transformers"
            - inference_endpoint: Optional custom inference URL

    Returns:
        JSON confirmation with steering status
    """
    try:
        config = json.loads(config_json)
    except json.JSONDecodeError:
        return json.dumps({"success": False, "error": "Invalid JSON config"})

    return SteeringTools.configure_steering(
        sae_endpoint=config.get("sae_endpoint"),
        sae_api_key=config.get("sae_api_key"),
        steering_scale=config.get("steering_scale", 2.0),
        suppression_targets=config.get("suppression_targets"),
        inference_backend=config.get("inference_backend", "openai_compatible"),
        inference_endpoint=config.get("inference_endpoint"),
    )


@tool
def apply_steering_tool(java_code: str, bedrock_code: str) -> str:
    """
    Apply SAE-based steering evaluation to a conversion result.

    This tool evaluates whether Java idioms were properly suppressed
    in the generated Bedrock code.

    Args:
        java_code: Original Java source code
        bedrock_code: Generated Bedrock JavaScript code

    Returns:
        JSON with evaluation metrics (suppression rate, quality score, warnings)
    """
    return SteeringTools.apply_steering(java_code, bedrock_code)


@tool
def get_steering_stats_tool() -> str:
    """
    Get current steering pipeline statistics.

    Returns:
        JSON with generation counts, steering applications, and feature tracking
    """
    return SteeringTools.get_steering_stats()


@tool
def enable_steering_tool() -> str:
    """
    Enable SAE-based feature steering globally.

    Returns:
        JSON confirmation
    """
    return SteeringTools.enable_steering()


@tool
def disable_steering_tool() -> str:
    """
    Disable SAE-based feature steering globally.

    Returns:
        JSON confirmation
    """
    return SteeringTools.disable_steering()


@tool
def evaluate_conversion_quality_tool(
    original_java: str, generated_bedrock: str, steering_applied: bool = True
) -> str:
    """
    Evaluate the quality of a Java-to-Bedrock conversion.

    Args:
        original_java: Original Java code
        generated_bedrock: Generated Bedrock code
        steering_applied: Whether steering was used (default True)

    Returns:
        JSON with overall quality score (0-100) and per-category metrics
    """
    result = evaluate_steering_effectiveness(
        java_code=original_java,
        bedrock_code=generated_bedrock,
        steering_applied=steering_applied,
    )

    return result.to_json()


def register_steering_tools(agent) -> None:
    """
    Register all steering tools with a CrewAI agent.

    Args:
        agent: CrewAI Agent instance to register tools with

    Usage:
        from agents.logic_translator.translator import LogicTranslatorAgent

        agent = LogicTranslatorAgent()
        register_steering_tools(agent)
        for tool in agent.tools:
            if 'steering' in str(tool):
                print(f"Registered: {tool.name}")
    """
    steering_tools = [
        configure_steering_tool,
        apply_steering_tool,
        get_steering_stats_tool,
        enable_steering_tool,
        disable_steering_tool,
        evaluate_conversion_quality_tool,
    ]

    for tool in steering_tools:
        if hasattr(agent, 'tools'):
            agent.tools.append(tool)
        logger.info(f"Registered steering tool: {tool.name}")