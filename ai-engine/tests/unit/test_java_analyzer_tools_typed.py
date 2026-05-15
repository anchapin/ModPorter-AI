"""Tests for the typed BaseTool wrappers in agents/java_analyzer/tools.py.

These wrappers replace the previous bare ``@tool @staticmethod`` decorators
(Phase 8 A6 — last A-slice, refs #1201). Each tool now exposes an explicit
Pydantic ``args_schema`` so chat models with native tool-calling can invoke
it with validated arguments rather than an opaque single string-or-dict.

Pattern matches PR #1453 (qa typed args), the A4a/A4b/A5 refactors, and is
the final A-slice required before the E (skeleton-regen) follow-up can
land.
"""

from __future__ import annotations

import pytest
from langchain_core.tools import BaseTool
from pydantic import BaseModel, ValidationError

from agents.java_analyzer import JavaAnalyzerAgent
from agents.java_analyzer.tools import (
    JavaAnalyzerTools,
    _AnalyzeComplexityWithLlmInput,
    _AnalyzeComplexityWithLlmTool,
    _AnalyzeDependenciesInput,
    _AnalyzeDependenciesTool,
    _AnalyzeModStructureInput,
    _AnalyzeModStructureTool,
    _ExtractAssetsInput,
    _ExtractAssetsTool,
    _ExtractModMetadataInput,
    _ExtractModMetadataTool,
    _IdentifyFeaturesInput,
    _IdentifyFeaturesTool,
)


# ─────────────────────────────────────────────────────────────────────────────
# Identity & schema
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def agent():
    """Reset the singleton so each test gets a fresh agent."""
    JavaAnalyzerAgent._instance = None
    return JavaAnalyzerAgent.get_instance()


_TOOL_TABLE = [
    ("analyze_mod_structure_tool", _AnalyzeModStructureTool, _AnalyzeModStructureInput),
    ("extract_mod_metadata_tool", _ExtractModMetadataTool, _ExtractModMetadataInput),
    ("identify_features_tool", _IdentifyFeaturesTool, _IdentifyFeaturesInput),
    ("analyze_dependencies_tool", _AnalyzeDependenciesTool, _AnalyzeDependenciesInput),
    ("extract_assets_tool", _ExtractAssetsTool, _ExtractAssetsInput),
    (
        "analyze_complexity_with_llm_tool",
        _AnalyzeComplexityWithLlmTool,
        _AnalyzeComplexityWithLlmInput,
    ),
]


class TestClassAttrIsTypedBaseTool:
    @pytest.mark.parametrize("tool_attr,expected_class,expected_schema", _TOOL_TABLE)
    def test_alias_on_tools_namespace(self, tool_attr, expected_class, expected_schema):
        # Bound on JavaAnalyzerTools (the tool-module class).
        tool_instance = getattr(JavaAnalyzerTools, tool_attr)
        assert isinstance(tool_instance, BaseTool), tool_attr
        assert isinstance(tool_instance, expected_class), tool_attr
        assert tool_instance.args_schema is expected_schema, tool_attr
        assert issubclass(tool_instance.args_schema, BaseModel), tool_attr
        assert tool_instance.name == tool_attr, tool_attr

    @pytest.mark.parametrize("tool_attr,expected_class,_schema", _TOOL_TABLE)
    def test_alias_on_agent_namespace(self, tool_attr, expected_class, _schema):
        # JavaAnalyzerAgent re-exposes them via class attributes that
        # reference JavaAnalyzerTools.<name>_tool at class-body time.
        # Identity must hold so .invoke({...}) on either alias hits the
        # same singleton.
        agent_attr = getattr(JavaAnalyzerAgent, tool_attr)
        tools_attr = getattr(JavaAnalyzerTools, tool_attr)
        assert agent_attr is tools_attr, tool_attr
        assert isinstance(agent_attr, expected_class), tool_attr

    def test_get_tools_returns_six_typed_basetools(self, agent):
        tools = agent.get_tools()
        assert len(tools) == 6
        assert all(isinstance(t, BaseTool) for t in tools)
        assert all(t.args_schema is not None for t in tools)
        names = [t.name for t in tools]
        assert names == [name for name, *_ in _TOOL_TABLE]


# ─────────────────────────────────────────────────────────────────────────────
# Schema validation
#
# Five of the six tools accept Any (Union[str, Dict] in the legacy shape) for
# their mod_data field, so empty-string rejection is only meaningful on
# _AnalyzeComplexityWithLlmInput.analysis_data.
# ─────────────────────────────────────────────────────────────────────────────


_ALL_FIELD_TABLE = [
    (_AnalyzeModStructureInput, "mod_data"),
    (_ExtractModMetadataInput, "mod_data"),
    (_IdentifyFeaturesInput, "mod_data"),
    (_AnalyzeDependenciesInput, "mod_data"),
    (_ExtractAssetsInput, "mod_data"),
    (_AnalyzeComplexityWithLlmInput, "analysis_data"),
]


class TestSchemaValidation:
    def test_min_length_rejects_empty_string_on_llm_tool(self):
        with pytest.raises(ValidationError):
            _AnalyzeComplexityWithLlmInput.model_validate({"analysis_data": ""})

    @pytest.mark.parametrize("schema_class,field_name", _ALL_FIELD_TABLE)
    def test_extra_fields_rejected(self, schema_class, field_name):
        with pytest.raises(ValidationError):
            schema_class.model_validate({field_name: "{}", "rogue": True})

    @pytest.mark.parametrize("schema_class,field_name", _ALL_FIELD_TABLE)
    def test_missing_required_field_rejected(self, schema_class, field_name):
        with pytest.raises(ValidationError):
            schema_class.model_validate({})

    @pytest.mark.parametrize(
        "schema_class",
        [
            _AnalyzeModStructureInput,
            _ExtractModMetadataInput,
            _IdentifyFeaturesInput,
            _AnalyzeDependenciesInput,
            _ExtractAssetsInput,
        ],
    )
    def test_mod_data_accepts_string_or_dict(self, schema_class):
        # Legacy Union[str, Dict] shape preserved via Any-typed field.
        s = schema_class.model_validate({"mod_data": '{"mod_path": "x"}'})
        assert s.mod_data == '{"mod_path": "x"}'
        d = schema_class.model_validate({"mod_data": {"mod_path": "x"}})
        assert d.mod_data == {"mod_path": "x"}


# ─────────────────────────────────────────────────────────────────────────────
# invoke() validation guards (validation runs before _run is called)
# ─────────────────────────────────────────────────────────────────────────────


class TestInvokeValidationGuards:
    def test_invoke_with_empty_string_on_llm_tool_raises(self):
        with pytest.raises(ValidationError):
            JavaAnalyzerAgent.analyze_complexity_with_llm_tool.invoke({"analysis_data": ""})

    def test_invoke_missing_field_raises(self):
        with pytest.raises(ValidationError):
            JavaAnalyzerAgent.extract_mod_metadata_tool.invoke({})

    def test_invoke_extra_field_raises(self):
        with pytest.raises(ValidationError):
            JavaAnalyzerAgent.analyze_dependencies_tool.invoke({"mod_data": "{}", "rogue": True})


# ─────────────────────────────────────────────────────────────────────────────
# Round-trip smoke: nonexistent mod_path → impl returns a structured error
# but does not raise. Exercises every tool's .invoke({...}) shape so the
# BaseTool→args_schema→_run→staticmethod plumbing is end-to-end verified
# without paying the cost of building a real fixture jar (the existing
# test_java_analyzer_comprehensive.py does that for 5 of 6 tools).
# ─────────────────────────────────────────────────────────────────────────────


class TestInvokeRoundtripsWithNonexistentPath:
    """Nonexistent mod_path returns a structured-error JSON, no exception."""

    @pytest.mark.parametrize(
        "tool_attr",
        [
            "analyze_mod_structure_tool",
            "extract_mod_metadata_tool",
            "identify_features_tool",
            "analyze_dependencies_tool",
            "extract_assets_tool",
        ],
    )
    def test_invoke_with_nonexistent_path(self, tool_attr):
        import json

        tool_instance = getattr(JavaAnalyzerAgent, tool_attr)
        out = tool_instance.invoke(
            {"mod_data": json.dumps({"mod_path": "/nonexistent/path/to/mod.jar"})}
        )
        # Must return a JSON string, never raise.
        parsed = json.loads(out)
        # Every impl returns either {"success": True, ...} or
        # {"success": False, "error": "..."} — pick whichever the impl chose.
        assert isinstance(parsed, dict), tool_attr
        # Sanity: the tool didn't get a half-applied schema (extract_assets,
        # for instance, might still report structure even on nonexistent path).
        assert "success" in parsed or "error" in parsed, tool_attr
