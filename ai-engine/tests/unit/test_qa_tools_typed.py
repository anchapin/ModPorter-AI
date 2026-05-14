"""Tests for the typed BaseTool wrappers in agents/qa/__init__.py.

These wrappers replace the previous ``@tool @staticmethod`` decorators (PR #1448
follow-up A3). Each tool now exposes an explicit Pydantic ``args_schema`` so chat
models with native tool-calling can invoke it with structured arguments rather
than rely on the JSON-encoded string blob convention.

Pattern matches PR #1447's typed migration of ``logic_translator/tools.py``
and PR #1451's typed migration of ``logic_translator/steering_tools.py``.

Also covers the ``agents.qa_validator`` deprecation alias, which has been a
silent-breakage risk since the module split: the alias must continue to
re-export ``QAValidatorAgent`` and emit a ``DeprecationWarning``.
"""

from __future__ import annotations

import json
import warnings

import pytest
from langchain_core.tools import BaseTool
from pydantic import ValidationError

from agents.qa import (
    QAValidatorAgent,
    _AnalyzeBedrockCompatibilityInput,
    _AnalyzeBedrockCompatibilityTool,
    _AssessPerformanceMetricsInput,
    _AssessPerformanceMetricsTool,
    _GenerateQaReportInput,
    _GenerateQaReportTool,
    _RunFunctionalTestsInput,
    _RunFunctionalTestsTool,
    _ValidateConversionQualityInput,
    _ValidateConversionQualityTool,
    _ValidateMcaddonInput,
    _ValidateMcaddonTool,
)


_TOOLS = [
    (
        "validate_conversion_quality_tool",
        _ValidateConversionQualityTool,
        _ValidateConversionQualityInput,
    ),
    ("validate_mcaddon_tool", _ValidateMcaddonTool, _ValidateMcaddonInput),
    ("run_functional_tests_tool", _RunFunctionalTestsTool, _RunFunctionalTestsInput),
    (
        "analyze_bedrock_compatibility_tool",
        _AnalyzeBedrockCompatibilityTool,
        _AnalyzeBedrockCompatibilityInput,
    ),
    (
        "assess_performance_metrics_tool",
        _AssessPerformanceMetricsTool,
        _AssessPerformanceMetricsInput,
    ),
    ("generate_qa_report_tool", _GenerateQaReportTool, _GenerateQaReportInput),
]


class TestQAToolsAreTypedBaseTools:
    """The 6 wrappers that replaced @tool @staticmethod must now be typed BaseTool
    instances accessible via both class attribute and instance attribute.
    """

    @pytest.mark.parametrize("attr_name,expected_class,expected_schema", _TOOLS)
    def test_class_attr_is_typed_basetool(self, attr_name, expected_class, expected_schema):
        tool = getattr(QAValidatorAgent, attr_name)
        assert isinstance(tool, BaseTool), f"{attr_name} is not a BaseTool"
        assert isinstance(tool, expected_class), f"{attr_name} wrong type"
        assert tool.args_schema is expected_schema
        assert tool.name == attr_name

    @pytest.mark.parametrize("attr_name,expected_class,expected_schema", _TOOLS)
    def test_instance_attr_is_typed_basetool(self, attr_name, expected_class, expected_schema):
        agent = QAValidatorAgent.get_instance()
        tool = getattr(agent, attr_name)
        assert isinstance(tool, BaseTool)
        assert isinstance(tool, expected_class)
        assert tool.args_schema is expected_schema

    def test_get_tools_returns_all_six(self):
        agent = QAValidatorAgent.get_instance()
        tools = agent.get_tools()
        assert len(tools) == 6
        names = {t.name for t in tools}
        assert names == {name for name, _, _ in _TOOLS}
        for t in tools:
            assert isinstance(t, BaseTool)
            assert t.args_schema is not None


class TestArgsSchemasRejectInvalidInputs:
    """Each schema must reject empty required strings and rogue extra fields."""

    @pytest.mark.parametrize(
        "schema_cls,arg_name",
        [
            (_ValidateConversionQualityInput, "quality_data"),
            (_ValidateMcaddonInput, "mcaddon_path"),
            (_RunFunctionalTestsInput, "test_data"),
            (_AnalyzeBedrockCompatibilityInput, "compatibility_data"),
            (_AssessPerformanceMetricsInput, "performance_data"),
            (_GenerateQaReportInput, "report_data"),
        ],
    )
    def test_rejects_empty_string(self, schema_cls, arg_name):
        with pytest.raises(ValidationError):
            schema_cls.model_validate({arg_name: ""})

    @pytest.mark.parametrize(
        "schema_cls,arg_name",
        [
            (_ValidateConversionQualityInput, "quality_data"),
            (_ValidateMcaddonInput, "mcaddon_path"),
        ],
    )
    def test_rejects_extra_fields(self, schema_cls, arg_name):
        with pytest.raises(ValidationError):
            schema_cls.model_validate({arg_name: "x", "rogue": True})


class TestInvokeReturnsValidJSON:
    """Each tool's _run path must return a JSON string when invoked with valid args."""

    def test_validate_mcaddon_tool_invoke_with_invalid_path(self):
        agent = QAValidatorAgent.get_instance()
        result = agent.validate_mcaddon_tool.invoke({"mcaddon_path": "/nonexistent/x.mcaddon"})
        # Underlying validate_mcaddon should report a 'fail' status (not crash).
        # The wrapper sets success = (status != "error"), so success=True for a 'fail'.
        parsed = json.loads(result)
        assert "status" in parsed
        assert parsed["status"] in {"fail", "partial"}  # not "error"
        assert parsed["success"] is True
        assert parsed["overall_score"] == 0

    def test_run_functional_tests_invoke(self):
        agent = QAValidatorAgent.get_instance()
        result = agent.run_functional_tests_tool.invoke({"test_data": "{}"})
        # Should return a JSON string regardless of underlying outcome
        json.loads(result)  # raises if not JSON


class TestQaValidatorDeprecationAlias:
    """The agents.qa_validator shim must remain importable, must re-export
    QAValidatorAgent, and must emit a DeprecationWarning on import.

    This test is the explicit guard called out in PR #1448's followups
    against silent breakage of the alias.
    """

    def test_alias_emits_deprecation_warning(self):
        # Force a fresh import so the warning is re-emitted.
        import importlib
        import sys

        sys.modules.pop("agents.qa_validator", None)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            importlib.import_module("agents.qa_validator")

        deprecation_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert any("qa_validator" in str(w.message) for w in deprecation_warnings), (
            f"Expected a DeprecationWarning mentioning qa_validator, got: "
            f"{[str(w.message) for w in deprecation_warnings]}"
        )

    def test_alias_re_exports_qa_validator_agent(self):
        from agents import qa_validator

        # The alias must expose QAValidatorAgent identically to the canonical
        # location.
        from agents.qa import QAValidatorAgent as Canonical

        assert hasattr(qa_validator, "QAValidatorAgent")
        assert qa_validator.QAValidatorAgent is Canonical

    def test_alias_re_exports_validation_constants(self):
        from agents import qa_validator

        # These were the public re-exports before the split.
        for name in [
            "ValidationCache",
            "VALIDATION_RULES",
            "VALIDATION_CATEGORIES",
            "PASS_THRESHOLD",
            "VALID_BLOCK_COMPONENTS",
            "VALID_ENTITY_COMPONENTS",
            "VALID_SOUND_FORMATS",
        ]:
            assert hasattr(qa_validator, name), f"qa_validator alias missing {name}"
