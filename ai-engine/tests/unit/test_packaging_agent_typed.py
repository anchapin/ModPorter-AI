"""Tests for the typed BaseTool wrappers in agents/packaging_agent.py.

These wrappers replace the previous bare ``@tool @staticmethod`` decorators
(Phase 8 A4b, refs #1201). Each tool now exposes an explicit Pydantic
``args_schema`` so chat models with native tool-calling can invoke it with
validated arguments rather than an opaque single string.

Pattern matches PR #1453 (qa typed args) and the A4a refactor: the legacy
``<name>_data: str`` shape is preserved end-to-end so existing call sites
and the existing coverage suite (``tests/test_packaging_agent.py``) pass
unchanged.
"""

from __future__ import annotations

import pytest
from langchain_core.tools import BaseTool
from pydantic import BaseModel, ValidationError

from agents.packaging_agent import (
    PackagingAgent,
    _AnalyzeConversionComponentsInput,
    _AnalyzeConversionComponentsTool,
    _BuildMcaddonInput,
    _BuildMcaddonTool,
    _CreatePackageStructureInput,
    _CreatePackageStructureTool,
    _GenerateBlocksAndItemsInput,
    _GenerateBlocksAndItemsTool,
    _GenerateEnhancedManifestsInput,
    _GenerateEnhancedManifestsTool,
    _GenerateEntitiesInput,
    _GenerateEntitiesTool,
    _GenerateManifestsInput,
    _GenerateManifestsTool,
    _GenerateValidationReportInput,
    _GenerateValidationReportTool,
    _PackageEnhancedAddonInput,
    _PackageEnhancedAddonTool,
    _ValidateEnhancedAddonInput,
    _ValidateEnhancedAddonTool,
    _ValidateManifestSchemaInput,
    _ValidateManifestSchemaTool,
    _ValidateMcaddonStructureInput,
    _ValidateMcaddonStructureTool,
    _ValidatePackageInput,
    _ValidatePackageTool,
)


# ─────────────────────────────────────────────────────────────────────────────
# Identity: each class-attribute alias is the corresponding typed BaseTool
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def agent():
    """Reset the singleton so each test gets a fresh agent."""
    PackagingAgent._instance = None
    return PackagingAgent.get_instance()


_TOOL_TABLE = [
    (
        "analyze_conversion_components_tool",
        _AnalyzeConversionComponentsTool,
        _AnalyzeConversionComponentsInput,
    ),
    (
        "create_package_structure_tool",
        _CreatePackageStructureTool,
        _CreatePackageStructureInput,
    ),
    ("generate_manifests_tool", _GenerateManifestsTool, _GenerateManifestsInput),
    ("validate_package_tool", _ValidatePackageTool, _ValidatePackageInput),
    ("build_mcaddon_tool", _BuildMcaddonTool, _BuildMcaddonInput),
    (
        "generate_enhanced_manifests_tool",
        _GenerateEnhancedManifestsTool,
        _GenerateEnhancedManifestsInput,
    ),
    (
        "generate_blocks_and_items_tool",
        _GenerateBlocksAndItemsTool,
        _GenerateBlocksAndItemsInput,
    ),
    ("generate_entities_tool", _GenerateEntitiesTool, _GenerateEntitiesInput),
    (
        "package_enhanced_addon_tool",
        _PackageEnhancedAddonTool,
        _PackageEnhancedAddonInput,
    ),
    (
        "validate_enhanced_addon_tool",
        _ValidateEnhancedAddonTool,
        _ValidateEnhancedAddonInput,
    ),
    (
        "validate_mcaddon_structure_tool",
        _ValidateMcaddonStructureTool,
        _ValidateMcaddonStructureInput,
    ),
    (
        "validate_manifest_schema_tool",
        _ValidateManifestSchemaTool,
        _ValidateManifestSchemaInput,
    ),
    (
        "generate_validation_report_tool",
        _GenerateValidationReportTool,
        _GenerateValidationReportInput,
    ),
]


class TestClassAttrIsTypedBaseTool:
    @pytest.mark.parametrize("tool_attr,expected_class,expected_schema", _TOOL_TABLE)
    def test_alias_is_basetool_subclass(self, tool_attr, expected_class, expected_schema):
        tool_instance = getattr(PackagingAgent, tool_attr)
        assert isinstance(tool_instance, BaseTool), tool_attr
        assert isinstance(tool_instance, expected_class), tool_attr
        assert tool_instance.args_schema is expected_schema, tool_attr
        assert issubclass(tool_instance.args_schema, BaseModel), tool_attr
        # Tool name mirrors the legacy @tool wrapper name.
        assert tool_instance.name == tool_attr, tool_attr

    def test_get_tools_returns_thirteen_typed_basetools(self, agent):
        tools = agent.get_tools()
        assert len(tools) == 13
        assert all(isinstance(t, BaseTool) for t in tools)
        assert all(t.args_schema is not None for t in tools)
        names = [t.name for t in tools]
        assert names == [name for name, *_ in _TOOL_TABLE]


# ─────────────────────────────────────────────────────────────────────────────
# Schema validation: empty strings rejected, extra fields rejected
# ─────────────────────────────────────────────────────────────────────────────


# Schemas with a min_length=1 string field.
_MIN_LENGTH_SCHEMAS = [
    (_AnalyzeConversionComponentsInput, "component_data"),
    (_CreatePackageStructureInput, "structure_data"),
    (_GenerateManifestsInput, "manifest_data"),
    (_ValidatePackageInput, "validation_data"),
    (_GenerateEnhancedManifestsInput, "mod_data"),
    (_GenerateBlocksAndItemsInput, "conversion_data"),
    (_GenerateEntitiesInput, "entity_data"),
    (_PackageEnhancedAddonInput, "package_data"),
    (_ValidateEnhancedAddonInput, "addon_path"),
    (_ValidateMcaddonStructureInput, "mcaddon_path"),
    (_ValidateManifestSchemaInput, "manifest_data"),
    (_GenerateValidationReportInput, "mcaddon_path"),
]

# All schemas (including the Any-typed _BuildMcaddonInput).
_ALL_SCHEMAS = _MIN_LENGTH_SCHEMAS + [(_BuildMcaddonInput, "build_data")]


class TestSchemaValidation:
    @pytest.mark.parametrize("schema_class,field_name", _MIN_LENGTH_SCHEMAS)
    def test_min_length_rejects_empty_string(self, schema_class, field_name):
        with pytest.raises(ValidationError):
            schema_class.model_validate({field_name: ""})

    @pytest.mark.parametrize("schema_class,field_name", _ALL_SCHEMAS)
    def test_extra_fields_rejected(self, schema_class, field_name):
        with pytest.raises(ValidationError):
            schema_class.model_validate({field_name: "{}", "rogue": True})

    @pytest.mark.parametrize("schema_class,field_name", _ALL_SCHEMAS)
    def test_missing_required_field_rejected(self, schema_class, field_name):
        with pytest.raises(ValidationError):
            schema_class.model_validate({})

    def test_build_mcaddon_accepts_string(self):
        # _BuildMcaddonInput preserves Any-typed build_data legacy shape.
        schema = _BuildMcaddonInput.model_validate({"build_data": "{}"})
        assert schema.build_data == "{}"

    def test_build_mcaddon_accepts_dict(self):
        schema = _BuildMcaddonInput.model_validate({"build_data": {"key": "value"}})
        assert schema.build_data == {"key": "value"}


# ─────────────────────────────────────────────────────────────────────────────
# invoke() rejects bad shapes at the BaseTool layer (i.e. validation runs
# before _run is called)
# ─────────────────────────────────────────────────────────────────────────────


class TestInvokeValidationGuards:
    def test_invoke_with_empty_string_raises(self):
        with pytest.raises(ValidationError):
            PackagingAgent.analyze_conversion_components_tool.invoke({"component_data": ""})

    def test_invoke_missing_field_raises(self):
        with pytest.raises(ValidationError):
            PackagingAgent.create_package_structure_tool.invoke({})

    def test_invoke_extra_field_raises(self):
        with pytest.raises(ValidationError):
            PackagingAgent.generate_entities_tool.invoke({"entity_data": "{}", "rogue": True})


# ─────────────────────────────────────────────────────────────────────────────
# Drive-by guards: F401 cleanup + logger fix
# ─────────────────────────────────────────────────────────────────────────────


class TestDriveByCleanups:
    """Item 9 cleanup folded into A4b: F401 imports removed; logger fixed."""

    def test_no_unused_imports_for_manifest_generator(self):
        # ``ManifestGenerator`` was an F401 in the previous import.
        # The module currently imports the alias ``_ManifestGenerator`` only.
        import agents.packaging_agent as mod

        assert not hasattr(mod, "ManifestGenerator"), (
            "ManifestGenerator should not be re-exported from packaging_agent "
            "after the A4b F401 cleanup"
        )

    def test_no_unused_imports_for_packaging_coordinator(self):
        import agents.packaging_agent as mod

        assert not hasattr(mod, "PackagingCoordinator"), (
            "PackagingCoordinator should not be re-exported from "
            "packaging_agent after the A4b F401 cleanup"
        )

    def test_logger_is_logger_instance_not_string(self):
        # Pre-existing bug: ``logger = __name__`` produced a str, so the
        # error-branch ``logger.error(...)`` calls would raise AttributeError.
        # A4b fixes this by binding ``logger = logging.getLogger(__name__)``.
        import logging

        from agents.packaging_agent import logger

        assert isinstance(logger, logging.Logger), (
            f"logger should be a logging.Logger, got {type(logger).__name__}"
        )
        # And the logger-name matches the module — a sanity check.
        assert logger.name == "agents.packaging_agent"
