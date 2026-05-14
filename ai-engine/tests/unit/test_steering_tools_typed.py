"""Tests for the typed BaseTool wrappers in agents/logic_translator/steering_tools.py.

These wrappers replace the previous bare ``@tool`` decorators (PR #1448 follow-up).
Each tool now exposes an explicit Pydantic ``args_schema`` so chat models with
native tool-calling can invoke it with structured arguments rather than a
JSON-encoded string blob.

Pattern matches PR #1447's typed migration of ``logic_translator/tools.py``.
"""

from __future__ import annotations

import json

import pytest
from langchain_core.tools import BaseTool
from pydantic import BaseModel, ValidationError

from agents.logic_translator.steering_tools import (
    ApplySteeringInput,
    ApplySteeringTool,
    ConfigureSteeringInput,
    ConfigureSteeringTool,
    DisableSteeringTool,
    EnableSteeringTool,
    EvaluateConversionQualityInput,
    EvaluateConversionQualityTool,
    GetSteeringStatsTool,
    _NoArgs,
    apply_steering_tool,
    configure_steering_tool,
    disable_steering_tool,
    enable_steering_tool,
    evaluate_conversion_quality_tool,
    get_steering_stats_tool,
    register_steering_tools,
)


class TestModuleLevelInstancesAreTypedBaseTools:
    """Verify the import-name aliases that the wider codebase uses are now
    BaseTool instances with proper args_schema. PR #1448 follow-up.
    """

    @pytest.mark.parametrize(
        "tool_instance,expected_class,expected_schema_name",
        [
            (configure_steering_tool, ConfigureSteeringTool, "ConfigureSteeringInput"),
            (apply_steering_tool, ApplySteeringTool, "ApplySteeringInput"),
            (get_steering_stats_tool, GetSteeringStatsTool, "_NoArgs"),
            (enable_steering_tool, EnableSteeringTool, "_NoArgs"),
            (disable_steering_tool, DisableSteeringTool, "_NoArgs"),
            (
                evaluate_conversion_quality_tool,
                EvaluateConversionQualityTool,
                "EvaluateConversionQualityInput",
            ),
        ],
    )
    def test_instance_is_typed_basetool(self, tool_instance, expected_class, expected_schema_name):
        assert isinstance(tool_instance, BaseTool)
        assert isinstance(tool_instance, expected_class)
        assert tool_instance.args_schema is not None
        assert tool_instance.args_schema.__name__ == expected_schema_name
        assert issubclass(tool_instance.args_schema, BaseModel)


class TestNoArgTools:
    """Tools with empty args_schema accept ``invoke({})`` and return JSON strings."""

    def test_enable_tool_invoke_empty_dict(self):
        result = enable_steering_tool.invoke({})
        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["steering_enabled"] is True

    def test_disable_tool_invoke_empty_dict(self):
        result = disable_steering_tool.invoke({})
        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["steering_enabled"] is False

    def test_stats_tool_invoke_empty_dict(self):
        result = get_steering_stats_tool.invoke({})
        parsed = json.loads(result)
        assert parsed["success"] is True
        assert "stats" in parsed
        assert "steering_enabled" in parsed["stats"]


class TestApplySteeringTool:
    def test_invoke_with_typed_args(self):
        result = apply_steering_tool.invoke(
            {
                "java_code": "public class X { void foo() {} }",
                "bedrock_code": "const x = { foo: () => {} };",
            }
        )
        parsed = json.loads(result)
        # Apply returns evaluation metrics — just assert it parses and has shape
        assert "success" in parsed or "evaluation" in parsed or "metrics" in parsed

    def test_args_schema_rejects_empty_strings(self):
        with pytest.raises(ValidationError):
            ApplySteeringInput.model_validate({"java_code": "", "bedrock_code": "anything"})

    def test_args_schema_rejects_extra_fields(self):
        with pytest.raises(ValidationError):
            ApplySteeringInput.model_validate(
                {"java_code": "x", "bedrock_code": "y", "rogue_field": True}
            )


class TestConfigureSteeringTool:
    def test_invoke_with_minimal_args_uses_defaults(self):
        result = configure_steering_tool.invoke({})
        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["config"]["steering_scale"] == 2.0
        assert parsed["config"]["inference_backend"] == "openai_compatible"

    def test_invoke_with_typed_overrides(self):
        result = configure_steering_tool.invoke(
            {
                "steering_scale": 3.5,
                "inference_backend": "vllm",
                "suppression_targets": ["java_forge_suppress"],
            }
        )
        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["config"]["steering_scale"] == 3.5
        assert parsed["config"]["inference_backend"] == "vllm"
        assert parsed["config"]["suppression_targets"] == ["java_forge_suppress"]

    def test_args_schema_rejects_extra_fields(self):
        with pytest.raises(ValidationError):
            ConfigureSteeringInput.model_validate({"made_up_field": 1})


class TestEvaluateConversionQualityTool:
    def test_invoke_with_typed_args(self):
        result = evaluate_conversion_quality_tool.invoke(
            {
                "original_java": "public class X {}",
                "generated_bedrock": "const x = {};",
                "steering_applied": False,
            }
        )
        parsed = json.loads(result)
        # Result.to_json() shape — just assert it parses to a dict
        assert isinstance(parsed, dict)

    def test_steering_applied_defaults_to_true(self):
        # Validate via the schema that the default is True
        validated = EvaluateConversionQualityInput.model_validate(
            {"original_java": "x", "generated_bedrock": "y"}
        )
        assert validated.steering_applied is True

    def test_args_schema_rejects_empty_required_strings(self):
        with pytest.raises(ValidationError):
            EvaluateConversionQualityInput.model_validate(
                {"original_java": "", "generated_bedrock": "y"}
            )


class TestNoArgsSchema:
    def test_no_args_schema_rejects_extra_fields(self):
        with pytest.raises(ValidationError):
            _NoArgs.model_validate({"any_field": True})

    def test_no_args_schema_accepts_empty(self):
        validated = _NoArgs.model_validate({})
        assert validated.model_dump() == {}


class TestRegisterSteeringTools:
    def test_register_attaches_all_six_tools_to_agent(self):
        class FakeAgent:
            tools: list = []

        agent = FakeAgent()
        agent.tools = []
        register_steering_tools(agent)
        names = {t.name for t in agent.tools}
        assert names == {
            "configure_steering_tool",
            "apply_steering_tool",
            "get_steering_stats_tool",
            "enable_steering_tool",
            "disable_steering_tool",
            "evaluate_conversion_quality_tool",
        }

    def test_register_skips_when_agent_has_no_tools_attr(self):
        # Should not raise even if agent has no `tools` attribute
        class BareAgent:
            pass

        register_steering_tools(BareAgent())  # no exception
