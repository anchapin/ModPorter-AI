"""Tests for the typed BaseTool wrappers in agents/recipe/__init__.py.

These wrappers replace the previous bare ``@tool @staticmethod`` decorators
(Phase 8 A5, refs #1201). Each tool now exposes an explicit Pydantic
``args_schema`` so chat models with native tool-calling can invoke it with
validated arguments rather than an opaque single string.

Pattern matches PR #1453 (qa typed args) and the A4a/A4b refactors. The
legacy single-string ``recipe_json`` / ``recipes_json`` /
``item_mapping_json`` / ``recipe_json`` shape is preserved end-to-end so
existing call sites and the existing coverage suites
(``tests/test_recipe_converter.py`` and
``tests/unit/test_recipe_converter.py``) pass unchanged.
"""

from __future__ import annotations

import json

import pytest
from langchain_core.tools import BaseTool
from pydantic import BaseModel, ValidationError

from agents.recipe import (
    RecipeConverterAgent,
    _ConvertRecipeInput,
    _ConvertRecipesBatchInput,
    _ConvertRecipesBatchTool,
    _ConvertRecipeTool,
    _MapItemIdInput,
    _MapItemIdTool,
    _ValidateRecipeInput,
    _ValidateRecipeTool,
)


# ─────────────────────────────────────────────────────────────────────────────
# Identity & schema
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def agent():
    """Reset the singleton so each test gets a fresh agent."""
    RecipeConverterAgent._instance = None
    return RecipeConverterAgent.get_instance()


_TOOL_TABLE = [
    ("convert_recipe_tool", _ConvertRecipeTool, _ConvertRecipeInput),
    ("convert_recipes_batch_tool", _ConvertRecipesBatchTool, _ConvertRecipesBatchInput),
    ("map_item_id_tool", _MapItemIdTool, _MapItemIdInput),
    ("validate_recipe_tool", _ValidateRecipeTool, _ValidateRecipeInput),
]


class TestClassAttrIsTypedBaseTool:
    @pytest.mark.parametrize("tool_attr,expected_class,expected_schema", _TOOL_TABLE)
    def test_alias_is_basetool_subclass(self, tool_attr, expected_class, expected_schema):
        tool_instance = getattr(RecipeConverterAgent, tool_attr)
        assert isinstance(tool_instance, BaseTool), tool_attr
        assert isinstance(tool_instance, expected_class), tool_attr
        assert tool_instance.args_schema is expected_schema, tool_attr
        assert issubclass(tool_instance.args_schema, BaseModel), tool_attr
        assert tool_instance.name == tool_attr, tool_attr

    def test_get_tools_returns_four_typed_basetools(self, agent):
        tools = agent.get_tools()
        assert len(tools) == 4
        assert all(isinstance(t, BaseTool) for t in tools)
        assert all(t.args_schema is not None for t in tools)
        names = [t.name for t in tools]
        assert names == [name for name, *_ in _TOOL_TABLE]


# ─────────────────────────────────────────────────────────────────────────────
# Schema validation
# ─────────────────────────────────────────────────────────────────────────────


_FIELD_TABLE = [
    (_ConvertRecipeInput, "recipe_json"),
    (_ConvertRecipesBatchInput, "recipes_json"),
    (_MapItemIdInput, "item_mapping_json"),
    (_ValidateRecipeInput, "recipe_json"),
]


class TestSchemaValidation:
    @pytest.mark.parametrize("schema_class,field_name", _FIELD_TABLE)
    def test_min_length_rejects_empty_string(self, schema_class, field_name):
        with pytest.raises(ValidationError):
            schema_class.model_validate({field_name: ""})

    @pytest.mark.parametrize("schema_class,field_name", _FIELD_TABLE)
    def test_extra_fields_rejected(self, schema_class, field_name):
        with pytest.raises(ValidationError):
            schema_class.model_validate({field_name: "{}", "rogue": True})

    @pytest.mark.parametrize("schema_class,field_name", _FIELD_TABLE)
    def test_missing_required_field_rejected(self, schema_class, field_name):
        with pytest.raises(ValidationError):
            schema_class.model_validate({})


# ─────────────────────────────────────────────────────────────────────────────
# invoke() validation guards
# ─────────────────────────────────────────────────────────────────────────────


class TestInvokeValidationGuards:
    def test_invoke_with_empty_string_raises(self):
        with pytest.raises(ValidationError):
            RecipeConverterAgent.convert_recipe_tool.invoke({"recipe_json": ""})

    def test_invoke_missing_field_raises(self):
        with pytest.raises(ValidationError):
            RecipeConverterAgent.validate_recipe_tool.invoke({})

    def test_invoke_extra_field_raises(self):
        with pytest.raises(ValidationError):
            RecipeConverterAgent.map_item_id_tool.invoke({"item_mapping_json": "{}", "rogue": True})


# ─────────────────────────────────────────────────────────────────────────────
# invoke() round-trip smoke tests — both the new `.invoke({...})` shape AND
# the legacy `.run(<json_string>)` single-input shape exercised by
# ``tests/test_recipe_converter.py`` continue to work.
# ─────────────────────────────────────────────────────────────────────────────


class TestInvokeRoundtrips:
    def test_validate_recipe_tool_invoke_shape(self):
        valid_recipe = {
            "format_version": "1.20.10",
            "minecraft:recipe_shaped": {
                "description": {"identifier": "test:r1"},
                "pattern": ["X"],
                "key": {"X": {"item": "minecraft:stone"}},
                "result": {"item": "minecraft:stone", "count": 1},
            },
        }
        out = json.loads(
            RecipeConverterAgent.validate_recipe_tool.invoke(
                {"recipe_json": json.dumps(valid_recipe)}
            )
        )
        assert out["valid"] is True

    def test_validate_recipe_tool_legacy_run_single_input_shape(self):
        # Legacy single-input ``.run(<json_string>)`` shape used by
        # ``tests/test_recipe_converter.py``. LangChain BaseTool.run() with
        # a single-field args_schema accepts a positional string.
        valid_recipe = {
            "format_version": "1.20.10",
            "minecraft:recipe_shaped": {
                "description": {"identifier": "test:r2"},
                "pattern": ["X"],
                "key": {"X": {"item": "minecraft:stone"}},
                "result": {"item": "minecraft:stone", "count": 1},
            },
        }
        out = json.loads(RecipeConverterAgent.validate_recipe_tool.run(json.dumps(valid_recipe)))
        assert out["valid"] is True

    def test_convert_recipes_batch_invoke(self):
        recipes = [
            {
                "recipe_data": {
                    "type": "minecraft:crafting_shaped",
                    "pattern": ["X"],
                    "key": {"X": {"item": "minecraft:stone"}},
                    "result": {"item": "minecraft:stone"},
                },
                "namespace": "test_mod",
            }
        ]
        out = json.loads(
            RecipeConverterAgent.convert_recipes_batch_tool.invoke(
                {"recipes_json": json.dumps(recipes)}
            )
        )
        assert out["success"] is True
        assert out["total_count"] == 1

    def test_map_item_id_invoke_with_list(self):
        mappings = [{"java": "minecraft:test", "bedrock": "minecraft:test_bedrock"}]
        out = json.loads(
            RecipeConverterAgent.map_item_id_tool.invoke(
                {"item_mapping_json": json.dumps(mappings)}
            )
        )
        assert out["success"] is True
        # And confirm the mapping landed on the agent.
        assert (
            RecipeConverterAgent.get_instance().custom_mappings.get("minecraft:test")
            == "minecraft:test_bedrock"
        )

    def test_convert_recipe_with_invalid_json_returns_error(self):
        out = json.loads(
            RecipeConverterAgent.convert_recipe_tool.invoke({"recipe_json": "not json"})
        )
        assert out["success"] is False
        assert "error" in out


# ─────────────────────────────────────────────────────────────────────────────
# Drive-by: recipe_converter.py shim no longer F401-imports ``tool``
# ─────────────────────────────────────────────────────────────────────────────


class TestRecipeConverterShimCleanup:
    def test_shim_no_longer_reexports_tool(self):
        # The deprecated shim ``agents.recipe_converter`` previously
        # imported ``tool`` from langchain_core.tools but never used it
        # (an F401 leftover from the pre-extraction refactor). The shim
        # now imports only what it re-exports.
        import agents.recipe_converter as shim

        assert not hasattr(shim, "tool"), (
            "agents.recipe_converter shim should no longer re-export `tool`"
        )

    def test_shim_still_reexports_public_api(self):
        from agents.recipe_converter import (
            CUSTOM_RECIPE_TYPES,
            FORGE_TAG_MAPPINGS,
            JAVA_TO_BEDROCK_ITEM_MAP,
            RecipeConverterAgent as ShimRecipeConverterAgent,
        )

        assert ShimRecipeConverterAgent is RecipeConverterAgent
        assert isinstance(FORGE_TAG_MAPPINGS, dict)
        assert isinstance(JAVA_TO_BEDROCK_ITEM_MAP, dict)
        assert CUSTOM_RECIPE_TYPES is not None
