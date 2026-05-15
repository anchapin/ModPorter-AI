"""Tests for the typed BaseTool wrappers in agents/bedrock_architect.py and
agents/bedrock_builder.py.

These wrappers replace the previous bare ``@tool @staticmethod`` decorators
(Phase 8 A4a, refs #1201). Each tool now exposes an explicit Pydantic
``args_schema`` so chat models with native tool-calling can invoke it with
validated arguments rather than an opaque single string.

Pattern matches PR #1453 (qa typed args) and PR #1451 (steering typed args):
the legacy ``<name>_data: str`` shape is preserved end-to-end so existing
call sites and the existing coverage suite (``test_bedrock_architect_coverage``,
``test_bedrock_builder_mvp``) pass unchanged.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.tools import BaseTool
from pydantic import BaseModel, ValidationError

from agents.bedrock_architect import (
    BedrockArchitectAgent,
    _AnalyzeJavaFeatureInput,
    _AnalyzeJavaFeatureTool,
    _ApplySmartAssumptionInput,
    _ApplySmartAssumptionTool,
    _CreateConversionPlanInput,
    _CreateConversionPlanTool,
    _CreateLlmConversionPlanInput,
    _CreateLlmConversionPlanTool,
    _GenerateBlockDefinitionsInput,
    _GenerateBlockDefinitionsTool,
    _GenerateEntityDefinitionsInput,
    _GenerateEntityDefinitionsTool,
    _GenerateItemDefinitionsInput,
    _GenerateItemDefinitionsTool,
    _GenerateRecipeDefinitionsInput,
    _GenerateRecipeDefinitionsTool,
    _GetAssumptionConflictsInput,
    _GetAssumptionConflictsTool,
    _ValidateBedrockCompatibilityInput,
    _ValidateBedrockCompatibilityTool,
)
from agents.bedrock_builder import (
    BedrockBuilderAgent,
    _BuildBedrockStructureInput,
    _BuildBedrockStructureTool,
    _ConvertAssetsInput,
    _ConvertAssetsTool,
    _GenerateBlockDefinitionsInput as _BuilderGenerateBlockDefinitionsInput,
    _GenerateBlockDefinitionsTool as _BuilderGenerateBlockDefinitionsTool,
    _PackageAddonInput,
    _PackageAddonTool,
)


# ─────────────────────────────────────────────────────────────────────────────
# Architect: instance / schema identity
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def architect():
    """Reset Architect singleton so each test gets a clean engine."""
    BedrockArchitectAgent._instance = None
    return BedrockArchitectAgent.get_instance()


class TestArchitectInstancesAreTypedBaseTools:
    """Verify the class-attribute aliases are typed BaseTool instances."""

    @pytest.mark.parametrize(
        "tool_attr,expected_class,expected_schema",
        [
            ("analyze_java_feature_tool", _AnalyzeJavaFeatureTool, _AnalyzeJavaFeatureInput),
            ("apply_smart_assumption_tool", _ApplySmartAssumptionTool, _ApplySmartAssumptionInput),
            ("create_conversion_plan_tool", _CreateConversionPlanTool, _CreateConversionPlanInput),
            (
                "get_assumption_conflicts_tool",
                _GetAssumptionConflictsTool,
                _GetAssumptionConflictsInput,
            ),
            (
                "validate_bedrock_compatibility_tool",
                _ValidateBedrockCompatibilityTool,
                _ValidateBedrockCompatibilityInput,
            ),
            (
                "generate_block_definitions_tool",
                _GenerateBlockDefinitionsTool,
                _GenerateBlockDefinitionsInput,
            ),
            (
                "generate_item_definitions_tool",
                _GenerateItemDefinitionsTool,
                _GenerateItemDefinitionsInput,
            ),
            (
                "generate_recipe_definitions_tool",
                _GenerateRecipeDefinitionsTool,
                _GenerateRecipeDefinitionsInput,
            ),
            (
                "generate_entity_definitions_tool",
                _GenerateEntityDefinitionsTool,
                _GenerateEntityDefinitionsInput,
            ),
            (
                "create_llm_conversion_plan_tool",
                _CreateLlmConversionPlanTool,
                _CreateLlmConversionPlanInput,
            ),
        ],
    )
    def test_class_attr_is_typed_basetool(self, tool_attr, expected_class, expected_schema):
        tool_instance = getattr(BedrockArchitectAgent, tool_attr)
        assert isinstance(tool_instance, BaseTool), tool_attr
        assert isinstance(tool_instance, expected_class), tool_attr
        assert tool_instance.args_schema is expected_schema, tool_attr
        assert issubclass(tool_instance.args_schema, BaseModel), tool_attr
        # Tool name mirrors the legacy @tool wrapper name.
        assert tool_instance.name == tool_attr, tool_attr

    def test_get_tools_returns_ten_typed_basetools(self, architect):
        tools = architect.get_tools()
        assert len(tools) == 10
        assert all(isinstance(t, BaseTool) for t in tools)
        assert all(t.args_schema is not None for t in tools)
        names = [t.name for t in tools]
        assert names == [
            "analyze_java_feature_tool",
            "apply_smart_assumption_tool",
            "create_conversion_plan_tool",
            "get_assumption_conflicts_tool",
            "validate_bedrock_compatibility_tool",
            "generate_block_definitions_tool",
            "generate_item_definitions_tool",
            "generate_recipe_definitions_tool",
            "generate_entity_definitions_tool",
            "create_llm_conversion_plan_tool",
        ]


# ─────────────────────────────────────────────────────────────────────────────
# Architect: schema validation
# ─────────────────────────────────────────────────────────────────────────────


class TestArchitectSchemaValidation:
    """args_schema rejects empty strings and extra fields at validation time."""

    @pytest.mark.parametrize(
        "schema_class,field_name",
        [
            (_AnalyzeJavaFeatureInput, "feature_data"),
            (_ApplySmartAssumptionInput, "assumption_data"),
            (_GetAssumptionConflictsInput, "conflict_data"),
            (_ValidateBedrockCompatibilityInput, "compatibility_data"),
            (_GenerateBlockDefinitionsInput, "block_data"),
            (_GenerateItemDefinitionsInput, "item_data"),
            (_GenerateRecipeDefinitionsInput, "recipe_data"),
            (_GenerateEntityDefinitionsInput, "entity_data"),
            (_CreateLlmConversionPlanInput, "plan_data"),
        ],
    )
    def test_min_length_rejects_empty_string(self, schema_class, field_name):
        with pytest.raises(ValidationError):
            schema_class.model_validate({field_name: ""})

    @pytest.mark.parametrize(
        "schema_class,field_name",
        [
            (_AnalyzeJavaFeatureInput, "feature_data"),
            (_ApplySmartAssumptionInput, "assumption_data"),
            (_CreateConversionPlanInput, "plan_data"),
            (_GetAssumptionConflictsInput, "conflict_data"),
            (_ValidateBedrockCompatibilityInput, "compatibility_data"),
            (_GenerateBlockDefinitionsInput, "block_data"),
            (_GenerateItemDefinitionsInput, "item_data"),
            (_GenerateRecipeDefinitionsInput, "recipe_data"),
            (_GenerateEntityDefinitionsInput, "entity_data"),
            (_CreateLlmConversionPlanInput, "plan_data"),
        ],
    )
    def test_extra_fields_rejected(self, schema_class, field_name):
        with pytest.raises(ValidationError):
            schema_class.model_validate({field_name: "{}", "rogue": True})

    @pytest.mark.parametrize(
        "schema_class,field_name",
        [
            (_AnalyzeJavaFeatureInput, "feature_data"),
            (_ApplySmartAssumptionInput, "assumption_data"),
            (_CreateConversionPlanInput, "plan_data"),
            (_GetAssumptionConflictsInput, "conflict_data"),
            (_ValidateBedrockCompatibilityInput, "compatibility_data"),
            (_GenerateBlockDefinitionsInput, "block_data"),
            (_GenerateItemDefinitionsInput, "item_data"),
            (_GenerateRecipeDefinitionsInput, "recipe_data"),
            (_GenerateEntityDefinitionsInput, "entity_data"),
            (_CreateLlmConversionPlanInput, "plan_data"),
        ],
    )
    def test_missing_required_field_rejected(self, schema_class, field_name):
        with pytest.raises(ValidationError):
            schema_class.model_validate({})

    def test_create_conversion_plan_accepts_list(self):
        # plan_data is typed as Any to preserve legacy str-or-list semantics.
        schema = _CreateConversionPlanInput.model_validate({"plan_data": [{"feature_id": "x"}]})
        assert schema.plan_data == [{"feature_id": "x"}]

    def test_create_conversion_plan_accepts_string(self):
        schema = _CreateConversionPlanInput.model_validate({"plan_data": "[]"})
        assert schema.plan_data == "[]"


# ─────────────────────────────────────────────────────────────────────────────
# Architect: invoke smoke tests (typed dict shape)
# ─────────────────────────────────────────────────────────────────────────────


class TestArchitectInvokeRoundtrips:
    """invoke({"<name>_data": ...}) returns the same JSON the impl would produce."""

    def test_analyze_java_feature_invoke_basic(self, architect):
        feature_data = json.dumps({"feature_id": "x", "feature_type": "block", "name": "X"})
        with patch.object(architect.smart_assumption_engine, "analyze_feature") as mock:
            result = MagicMock()
            result.applied_assumption = None
            result.conflicting_assumptions = []
            result.conflict_resolution_reason = None
            mock.return_value = result
            out = json.loads(
                BedrockArchitectAgent.analyze_java_feature_tool.invoke(
                    {"feature_data": feature_data}
                )
            )
        assert out["feature_id"] == "x"
        assert "directly convertible" in out["recommendation"]

    def test_get_assumption_conflicts_invoke(self, architect):
        with patch.object(architect.smart_assumption_engine, "get_conflict_analysis") as mock:
            mock.return_value = {"conflicts": []}
            out = json.loads(
                BedrockArchitectAgent.get_assumption_conflicts_tool.invoke(
                    {"conflict_data": json.dumps({"feature_type": "block"})}
                )
            )
        assert "conflicts" in out

    def test_generate_block_definitions_invoke(self, architect):
        block_data = json.dumps({"id": "test_block", "name": "Test Block"})
        out = json.loads(
            BedrockArchitectAgent.generate_block_definitions_tool.invoke({"block_data": block_data})
        )
        assert out["success"] is True
        assert out["component_type"] == "block"

    def test_generate_block_definitions_invalid_json_returns_error(self, architect):
        out = json.loads(
            BedrockArchitectAgent.generate_block_definitions_tool.invoke({"block_data": "not json"})
        )
        assert out["success"] is False
        assert "Invalid JSON" in out["error"]

    def test_validate_bedrock_compatibility_invoke(self, architect):
        compat = json.dumps(
            {
                "components": [
                    {
                        "original_feature_id": "c1",
                        "impact_level": "high",
                        "assumption_type": "dimension",
                    }
                ]
            }
        )
        out = json.loads(
            BedrockArchitectAgent.validate_bedrock_compatibility_tool.invoke(
                {"compatibility_data": compat}
            )
        )
        assert out["is_compatible"] is True
        assert len(out["component_validations"]) == 1
        assert any("dimension" in w.lower() for w in out["warnings"])

    def test_create_conversion_plan_invoke_with_list(self, architect):
        with (
            patch.object(architect.smart_assumption_engine, "analyze_feature") as mock_a,
            patch.object(architect.smart_assumption_engine, "apply_assumption") as mock_app,
            patch.object(
                architect.smart_assumption_engine, "generate_assumption_report"
            ) as mock_rep,
        ):
            ar = MagicMock()
            ar.applied_assumption = MagicMock()
            mock_a.return_value = ar
            comp = MagicMock()
            comp.original_feature_id = "f1"
            comp.original_feature_type = "block"
            comp.assumption_type = "x"
            comp.bedrock_equivalent = "y"
            comp.impact_level = "low"
            comp.user_explanation = "e"
            comp.technical_notes = "n"
            mock_app.return_value = comp
            rep = MagicMock()
            rep.assumptions_applied = []
            mock_rep.return_value = rep

            # Pass a Python list, not a JSON string — exercises the Any branch.
            out = json.loads(
                BedrockArchitectAgent.create_conversion_plan_tool.invoke(
                    {"plan_data": [{"feature_id": "f1", "feature_type": "block"}]}
                )
            )
        assert out["success"] is True
        assert out["conversion_plan_components"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# Builder: instance / schema identity
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def builder():
    BedrockBuilderAgent._instance = None
    return BedrockBuilderAgent.get_instance()


class TestBuilderInstancesAreTypedBaseTools:
    """Verify the class-attribute aliases on BedrockBuilderAgent."""

    @pytest.mark.parametrize(
        "tool_attr,expected_class,expected_schema_name",
        [
            (
                "build_bedrock_structure_tool",
                _BuildBedrockStructureTool,
                "_BuildBedrockStructureInput",
            ),
            (
                "generate_block_definitions_tool",
                _BuilderGenerateBlockDefinitionsTool,
                "_GenerateBlockDefinitionsInput",
            ),
            ("convert_assets_tool", _ConvertAssetsTool, "_ConvertAssetsInput"),
            ("package_addon_tool", _PackageAddonTool, "_PackageAddonInput"),
        ],
    )
    def test_class_attr_is_typed_basetool(self, tool_attr, expected_class, expected_schema_name):
        tool_instance = getattr(BedrockBuilderAgent, tool_attr)
        assert isinstance(tool_instance, BaseTool), tool_attr
        assert isinstance(tool_instance, expected_class), tool_attr
        assert tool_instance.args_schema is not None, tool_attr
        assert tool_instance.args_schema.__name__ == expected_schema_name, tool_attr
        assert tool_instance.name == tool_attr, tool_attr

    def test_get_tools_returns_four_typed_basetools(self, builder):
        tools = builder.get_tools()
        assert len(tools) == 4
        assert all(isinstance(t, BaseTool) for t in tools)
        assert all(t.args_schema is not None for t in tools)
        assert [t.name for t in tools] == [
            "build_bedrock_structure_tool",
            "generate_block_definitions_tool",
            "convert_assets_tool",
            "package_addon_tool",
        ]


# ─────────────────────────────────────────────────────────────────────────────
# Builder: schema validation
# ─────────────────────────────────────────────────────────────────────────────


class TestBuilderSchemaValidation:
    @pytest.mark.parametrize(
        "schema_class,field_name",
        [
            (_BuildBedrockStructureInput, "structure_data"),
            (_BuilderGenerateBlockDefinitionsInput, "block_data"),
            (_ConvertAssetsInput, "asset_data"),
            (_PackageAddonInput, "package_data"),
        ],
    )
    def test_min_length_rejects_empty_string(self, schema_class, field_name):
        with pytest.raises(ValidationError):
            schema_class.model_validate({field_name: ""})

    @pytest.mark.parametrize(
        "schema_class,field_name",
        [
            (_BuildBedrockStructureInput, "structure_data"),
            (_BuilderGenerateBlockDefinitionsInput, "block_data"),
            (_ConvertAssetsInput, "asset_data"),
            (_PackageAddonInput, "package_data"),
        ],
    )
    def test_extra_fields_rejected(self, schema_class, field_name):
        with pytest.raises(ValidationError):
            schema_class.model_validate({field_name: "{}", "rogue": True})

    @pytest.mark.parametrize(
        "schema_class",
        [
            _BuildBedrockStructureInput,
            _BuilderGenerateBlockDefinitionsInput,
            _ConvertAssetsInput,
            _PackageAddonInput,
        ],
    )
    def test_missing_required_field_rejected(self, schema_class):
        with pytest.raises(ValidationError):
            schema_class.model_validate({})


# ─────────────────────────────────────────────────────────────────────────────
# Builder: invoke smoke tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBuilderInvokeRoundtrips:
    def test_build_bedrock_structure_invoke(self):
        out = json.loads(
            BedrockBuilderAgent.build_bedrock_structure_tool.invoke({"structure_data": "{}"})
        )
        assert out == {"success": True, "message": "Structure created"}

    def test_generate_block_definitions_invoke(self):
        out = json.loads(
            BedrockBuilderAgent.generate_block_definitions_tool.invoke({"block_data": "{}"})
        )
        assert out == {"success": True, "message": "Block definitions generated"}

    def test_convert_assets_invoke(self):
        out = json.loads(BedrockBuilderAgent.convert_assets_tool.invoke({"asset_data": "{}"}))
        assert out == {"success": True, "message": "Assets converted"}

    def test_package_addon_invoke(self):
        out = json.loads(BedrockBuilderAgent.package_addon_tool.invoke({"package_data": "{}"}))
        assert out == {"success": True, "message": "Addon packaged"}

    def test_invoke_with_empty_string_raises(self):
        with pytest.raises(ValidationError):
            BedrockBuilderAgent.build_bedrock_structure_tool.invoke({"structure_data": ""})

    def test_invoke_missing_field_raises(self):
        with pytest.raises(ValidationError):
            BedrockBuilderAgent.convert_assets_tool.invoke({})

    def test_invoke_extra_field_raises(self):
        with pytest.raises(ValidationError):
            BedrockBuilderAgent.package_addon_tool.invoke({"package_data": "{}", "rogue": True})
