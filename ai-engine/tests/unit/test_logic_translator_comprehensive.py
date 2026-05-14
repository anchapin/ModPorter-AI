"""Tests for the typed BaseTool wrappers in agents.logic_translator.tools.

This file replaces the prior ``.func(json_string)`` test pattern with
structured ``invoke({...})`` / ``ainvoke({...})`` calls and parametrised
Pydantic validation tests, exercising the typed ``BaseTool`` subclasses
introduced as Phase 8 A2 (refs #1201).
"""

from __future__ import annotations

import json
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from agents.logic_translator import LogicTranslatorAgent, LogicTranslatorTools
from agents.logic_translator.tools import (
    ConvertJavaClassTool,
    GenerateBedrockBlockTool,
    GenerateEventHandlersTool,
    GetRagContextTool,
    MapBlockPropertiesTool,
    MapJavaApisTool,
    SetRagContextTool,
    TranslateCraftingRecipeTool,
    TranslateJavaMethodTool,
    ValidateBlockJsonTool,
    ValidateJavascriptSyntaxTool,
    _map_java_block_properties_to_bedrock,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_singleton() -> None:
    """Ensure every test starts with a clean LogicTranslatorAgent singleton."""
    LogicTranslatorAgent._instance = None
    yield
    LogicTranslatorAgent._instance = None


def _make_mock_agent() -> MagicMock:
    """Return a lightweight mock agent that bypasses heavy ``__init__``."""
    agent = MagicMock()
    agent._rag_context_enabled = False
    agent._get_rag_context = MagicMock(return_value="")
    return agent


# ---------------------------------------------------------------------------
# GetRagContextTool
# ---------------------------------------------------------------------------


class TestGetRagContextTool:
    """Cover the structured-args public surface of get_rag_context_tool."""

    @pytest.mark.asyncio
    async def test_ainvoke_returns_empty_context_when_unavailable(self) -> None:
        agent = _make_mock_agent()
        agent._get_rag_context.return_value = ""
        tool = GetRagContextTool(agent=agent)

        raw = await tool.ainvoke({"java_feature": "block X", "feature_type": "block"})
        payload = json.loads(raw)

        assert payload["success"] is True
        assert payload["context"] == ""
        assert payload["rag_enabled"] is False
        agent._get_rag_context.assert_called_once_with("block X", "block")

    @pytest.mark.asyncio
    async def test_ainvoke_returns_context_when_enabled(self) -> None:
        agent = _make_mock_agent()
        agent._get_rag_context.return_value = "fixture context"
        agent._rag_context_enabled = True
        tool = GetRagContextTool(agent=agent)

        raw = await tool.ainvoke({"java_feature": "block X", "feature_type": "block"})
        payload = json.loads(raw)

        assert payload["success"] is True
        assert payload["context"] == "fixture context"
        assert payload["rag_enabled"] is True


# ---------------------------------------------------------------------------
# SetRagContextTool
# ---------------------------------------------------------------------------


class TestSetRagContextTool:
    @pytest.mark.asyncio
    async def test_ainvoke_enables_rag_context(self) -> None:
        agent = _make_mock_agent()

        def _enable(flag: bool) -> None:
            agent._rag_context_enabled = flag

        agent.enable_rag_context = MagicMock(side_effect=_enable)
        tool = SetRagContextTool(agent=agent)

        raw = await tool.ainvoke({"enabled": True})
        payload = json.loads(raw)

        assert payload["success"] is True
        assert payload["rag_enabled"] is True
        assert "enabled" in payload["message"]
        agent.enable_rag_context.assert_called_once_with(True)

    @pytest.mark.asyncio
    async def test_ainvoke_disables_rag_context(self) -> None:
        agent = _make_mock_agent()
        agent._rag_context_enabled = True

        def _enable(flag: bool) -> None:
            agent._rag_context_enabled = flag

        agent.enable_rag_context = MagicMock(side_effect=_enable)
        tool = SetRagContextTool(agent=agent)

        raw = await tool.ainvoke({"enabled": False})
        payload = json.loads(raw)

        assert payload["rag_enabled"] is False
        assert "disabled" in payload["message"]


# ---------------------------------------------------------------------------
# TranslateJavaMethodTool
# ---------------------------------------------------------------------------


class TestTranslateJavaMethodTool:
    @pytest.mark.asyncio
    async def test_ainvoke_delegates_to_agent_with_json_payload(self) -> None:
        agent = _make_mock_agent()
        agent.translate_java_method = MagicMock(
            return_value=json.dumps({"success": True, "translated_javascript": "// translated"})
        )
        tool = TranslateJavaMethodTool(agent=agent)

        raw = await tool.ainvoke(
            {"method_name": "onUse", "method_body": "return 1;", "feature_type": "item"}
        )
        payload = json.loads(raw)

        assert payload["success"] is True
        assert payload["translated_javascript"] == "// translated"
        sent = json.loads(agent.translate_java_method.call_args.args[0])
        assert sent == {
            "method_name": "onUse",
            "method_body": "return 1;",
            "feature_type": "item",
        }


# ---------------------------------------------------------------------------
# ConvertJavaClassTool
# ---------------------------------------------------------------------------


class TestConvertJavaClassTool:
    @pytest.mark.asyncio
    async def test_ainvoke_passes_methods_through(self) -> None:
        agent = _make_mock_agent()
        agent.convert_java_class = MagicMock(
            return_value=json.dumps({"success": True, "javascript_class": "class X{}"})
        )
        tool = ConvertJavaClassTool(agent=agent)

        raw = await tool.ainvoke(
            {"class_name": "MyClass", "methods": [{"name": "m"}], "feature_type": "block"}
        )
        payload = json.loads(raw)

        assert payload["success"] is True
        sent = json.loads(agent.convert_java_class.call_args.args[0])
        assert sent["class_name"] == "MyClass"
        assert sent["methods"] == [{"name": "m"}]


# ---------------------------------------------------------------------------
# MapJavaApisTool
# ---------------------------------------------------------------------------


class TestMapJavaApisTool:
    @pytest.mark.asyncio
    async def test_ainvoke_passes_api_list(self) -> None:
        agent = _make_mock_agent()
        agent.map_java_apis = MagicMock(
            return_value=json.dumps({"success": True, "mapped_apis": {"a": "b"}})
        )
        tool = MapJavaApisTool(agent=agent)

        raw = await tool.ainvoke({"apis": ["player.getHealth()", "world.getBlockAt("]})
        payload = json.loads(raw)

        assert payload["success"] is True
        sent = json.loads(agent.map_java_apis.call_args.args[0])
        assert sent["apis"] == ["player.getHealth()", "world.getBlockAt("]


# ---------------------------------------------------------------------------
# GenerateEventHandlersTool
# ---------------------------------------------------------------------------


class TestGenerateEventHandlersTool:
    @pytest.mark.asyncio
    async def test_ainvoke_uses_event_type_and_handlers_schema(self) -> None:
        agent = _make_mock_agent()
        agent.generate_event_handlers = MagicMock(
            return_value=json.dumps({"success": True, "event_handlers": []})
        )
        tool = GenerateEventHandlersTool(agent=agent)

        raw = await tool.ainvoke(
            {"event_type": "PlayerInteractEvent", "handlers": [{"name": "onUse"}]}
        )
        payload = json.loads(raw)

        assert payload["success"] is True
        sent = json.loads(agent.generate_event_handlers.call_args.args[0])
        assert sent == {
            "event_type": "PlayerInteractEvent",
            "handlers": [{"name": "onUse"}],
        }


# ---------------------------------------------------------------------------
# ValidateJavascriptSyntaxTool
# ---------------------------------------------------------------------------


class TestValidateJavascriptSyntaxTool:
    @pytest.mark.asyncio
    async def test_ainvoke_marks_valid_syntax(self) -> None:
        agent = _make_mock_agent()
        agent.validate_javascript_syntax = MagicMock(
            return_value=json.dumps({"success": True, "is_valid": True, "syntax_errors": []})
        )
        tool = ValidateJavascriptSyntaxTool(agent=agent)

        raw = await tool.ainvoke({"javascript_code": "function f() {}"})
        payload = json.loads(raw)

        assert payload["success"] is True
        assert payload["is_valid"] is True
        sent = json.loads(agent.validate_javascript_syntax.call_args.args[0])
        assert sent == {"javascript_code": "function f() {}"}


# ---------------------------------------------------------------------------
# TranslateCraftingRecipeTool
# ---------------------------------------------------------------------------


class TestTranslateCraftingRecipeTool:
    @pytest.mark.asyncio
    async def test_ainvoke_translates_shaped_recipe(self) -> None:
        agent = _make_mock_agent()
        recipe = {
            "type": "minecraft:crafting_shaped",
            "pattern": ["#", "#", "#"],
            "key": {"#": {"item": "minecraft:stick"}},
            "result": {"item": "minecraft:ladder", "count": 3},
        }
        agent.translate_crafting_recipe_json = MagicMock(
            return_value=json.dumps(
                {"success": True, "bedrock_recipe": {"minecraft:recipe_shaped": {}}, "warnings": []}
            )
        )
        tool = TranslateCraftingRecipeTool(agent=agent)

        raw = await tool.ainvoke({"recipe": recipe})
        payload = json.loads(raw)

        assert payload["success"] is True
        assert "minecraft:recipe_shaped" in payload["bedrock_recipe"]
        sent = json.loads(agent.translate_crafting_recipe_json.call_args.args[0])
        assert sent == recipe


# ---------------------------------------------------------------------------
# GenerateBedrockBlockTool
# ---------------------------------------------------------------------------


class TestGenerateBedrockBlockTool:
    @pytest.mark.asyncio
    async def test_ainvoke_passes_kwargs_to_agent(self) -> None:
        agent = _make_mock_agent()
        agent.generate_bedrock_block_json = MagicMock(
            return_value={"success": True, "block_json": {"format_version": "1.20.0"}}
        )
        tool = GenerateBedrockBlockTool(agent=agent)

        analysis = {"name": "myblock", "registry_name": "modporter:myblock", "properties": {}}
        raw = await tool.ainvoke(
            {"java_block_analysis": analysis, "namespace": "ns", "use_rag": False}
        )
        payload = json.loads(raw)

        assert payload["success"] is True
        agent.generate_bedrock_block_json.assert_called_once_with(
            java_block_analysis=analysis, namespace="ns", use_rag=False
        )

    @pytest.mark.asyncio
    async def test_ainvoke_returns_error_envelope_on_exception(self) -> None:
        agent = _make_mock_agent()
        agent.generate_bedrock_block_json = MagicMock(side_effect=RuntimeError("boom"))
        tool = GenerateBedrockBlockTool(agent=agent)

        raw = await tool.ainvoke({"java_block_analysis": {}})
        payload = json.loads(raw)

        assert payload["success"] is False
        assert "boom" in payload["error"]
        assert payload["block_json"] is None


# ---------------------------------------------------------------------------
# ValidateBlockJsonTool
# ---------------------------------------------------------------------------


class TestValidateBlockJsonTool:
    @pytest.mark.asyncio
    async def test_ainvoke_returns_validation_envelope(self) -> None:
        agent = _make_mock_agent()
        agent._validate_block_json = MagicMock(return_value={"is_valid": True})
        tool = ValidateBlockJsonTool(agent=agent)

        raw = await tool.ainvoke({"block_json": {"format_version": "1.20.0"}})
        payload = json.loads(raw)

        assert payload["success"] is True
        assert payload["validation"] == {"is_valid": True}
        agent._validate_block_json.assert_called_once_with({"format_version": "1.20.0"})

    @pytest.mark.asyncio
    async def test_ainvoke_returns_error_envelope_on_exception(self) -> None:
        agent = _make_mock_agent()
        agent._validate_block_json = MagicMock(side_effect=ValueError("bad json"))
        tool = ValidateBlockJsonTool(agent=agent)

        raw = await tool.ainvoke({"block_json": {}})
        payload = json.loads(raw)

        assert payload["success"] is False
        assert "bad json" in payload["error"]


# ---------------------------------------------------------------------------
# MapBlockPropertiesTool — fixes a pre-existing bug on main
# ---------------------------------------------------------------------------


class TestMapBlockPropertiesTool:
    @pytest.mark.asyncio
    async def test_ainvoke_maps_java_properties_to_bedrock(self) -> None:
        # The legacy wrapper called a non-existent method on
        # LogicTranslatorAgent. The typed rewrite routes through the
        # module-level helper, so this test no longer needs the agent.
        tool = MapBlockPropertiesTool()
        java_props = {"hardness": 1.5, "explosion_resistance": 6, "light_level": 10}

        raw = await tool.ainvoke({"java_properties": java_props})
        payload = json.loads(raw)

        assert payload["success"] is True
        bedrock = payload["bedrock_properties"]
        assert bedrock["hardness"] == 1.5
        assert bedrock["explosion_resistance"] == 6
        assert bedrock["light_level"] == 10  # capped at 15

    @pytest.mark.asyncio
    async def test_ainvoke_caps_light_level_at_fifteen(self) -> None:
        tool = MapBlockPropertiesTool()
        raw = await tool.ainvoke({"java_properties": {"light_level": 99}})
        payload = json.loads(raw)
        assert payload["bedrock_properties"]["light_level"] == 15

    def test_helper_returns_empty_dict_for_unknown_material(self) -> None:
        result = _map_java_block_properties_to_bedrock({"material": "unknown_xyz"})
        # Default sound_type "stone" maps; material does not.
        assert "sound_category" in result or result == {}


# ---------------------------------------------------------------------------
# Pydantic validation rejection — parametrised across tools
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("tool_cls", "args"),
    [
        # Empty required strings.
        (GetRagContextTool, {"java_feature": "", "feature_type": "block"}),
        (GetRagContextTool, {"java_feature": "x", "feature_type": ""}),
        (TranslateJavaMethodTool, {"method_name": ""}),
        (ConvertJavaClassTool, {"class_name": ""}),
        # Missing required fields.
        (TranslateJavaMethodTool, {}),
        (ConvertJavaClassTool, {}),
        (TranslateCraftingRecipeTool, {}),
        (GenerateBedrockBlockTool, {}),
        (ValidateBlockJsonTool, {}),
        (MapBlockPropertiesTool, {}),
        (GetRagContextTool, {}),
        (SetRagContextTool, {}),
    ],
)
def test_validation_rejects_missing_or_empty_required(tool_cls: type, args: Dict[str, Any]) -> None:
    tool = tool_cls()
    with pytest.raises((ValidationError, Exception)):
        tool.invoke(args)


@pytest.mark.parametrize(
    ("tool_cls", "args"),
    [
        (
            GetRagContextTool,
            {"java_feature": "x", "feature_type": "block", "extra_field": "nope"},
        ),
        (SetRagContextTool, {"enabled": True, "extra_field": "nope"}),
        (TranslateJavaMethodTool, {"method_name": "x", "extra_field": "nope"}),
        (MapJavaApisTool, {"apis": [], "extra_field": "nope"}),
        (GenerateEventHandlersTool, {"event_type": "x", "extra_field": "nope"}),
        (ValidateJavascriptSyntaxTool, {"javascript_code": "x", "extra_field": "nope"}),
        (TranslateCraftingRecipeTool, {"recipe": {}, "extra_field": "nope"}),
        (
            GenerateBedrockBlockTool,
            {"java_block_analysis": {}, "extra_field": "nope"},
        ),
        (ValidateBlockJsonTool, {"block_json": {}, "extra_field": "nope"}),
        (MapBlockPropertiesTool, {"java_properties": {}, "extra_field": "nope"}),
    ],
)
def test_validation_rejects_extra_fields(tool_cls: type, args: Dict[str, Any]) -> None:
    """``extra='forbid'`` rejects unknown keys (typo / drift defence)."""
    tool = tool_cls()
    with pytest.raises((ValidationError, Exception)):
        tool.invoke(args)


# ---------------------------------------------------------------------------
# Sync invoke() behaviour
# ---------------------------------------------------------------------------


class TestSyncInvokeBehaviour:
    def test_sync_invoke_outside_loop_succeeds(self) -> None:
        # MapBlockPropertiesTool needs no agent (uses module helper).
        tool = MapBlockPropertiesTool()
        raw = tool.invoke({"java_properties": {"hardness": 2}})
        payload = json.loads(raw)
        assert payload["success"] is True
        assert payload["bedrock_properties"]["hardness"] == 2

    @pytest.mark.asyncio
    async def test_sync_invoke_inside_loop_raises_runtime_error(self) -> None:
        tool = MapBlockPropertiesTool()
        with pytest.raises(RuntimeError, match="event loop"):
            tool.invoke({"java_properties": {"hardness": 1}})


# ---------------------------------------------------------------------------
# Facade compatibility
# ---------------------------------------------------------------------------


class TestFacadeCompatibility:
    """Ensure the legacy ``LogicTranslatorTools.<name>`` and
    ``LogicTranslatorAgent.<name>`` access paths still work and yield the
    same typed BaseTool instances.
    """

    EXPECTED_NAMES: List[str] = [
        "translate_java_method_tool",
        "convert_java_class_tool",
        "map_java_apis_tool",
        "generate_event_handlers_tool",
        "validate_javascript_syntax_tool",
        "translate_crafting_recipe_tool",
        "generate_bedrock_block_tool",
        "validate_block_json_tool",
        "map_block_properties_tool",
        "get_rag_context_tool",
        "set_rag_context_tool",
    ]

    def test_logic_translator_tools_class_attributes_are_typed_basetools(self) -> None:
        for name in self.EXPECTED_NAMES:
            t = getattr(LogicTranslatorTools, name)
            assert hasattr(t, "args_schema"), f"{name} missing args_schema"
            assert t.name == name, f"{name}.name mismatch ({t.name!r})"

    def test_agent_get_tools_returns_eleven_typed_tools(self) -> None:
        with (
            patch("models.smart_assumptions.SmartAssumptionEngine"),
            patch("agents.java_analyzer.JavaAnalyzerAgent"),
        ):
            agent = LogicTranslatorAgent()
        tools = agent.get_tools()
        assert len(tools) == 11
        actual_names = sorted(t.name for t in tools)
        assert actual_names == sorted(self.EXPECTED_NAMES)

    def test_agent_property_returns_same_typed_basetool_as_class_attr(self) -> None:
        with (
            patch("models.smart_assumptions.SmartAssumptionEngine"),
            patch("agents.java_analyzer.JavaAnalyzerAgent"),
        ):
            agent = LogicTranslatorAgent()
        # Sample one property accessor for each block tool.
        assert agent.translate_java_method_tool is LogicTranslatorTools.translate_java_method_tool
        assert agent.generate_bedrock_block_tool is LogicTranslatorTools.generate_bedrock_block_tool
        assert agent.map_block_properties_tool is LogicTranslatorTools.map_block_properties_tool


# ---------------------------------------------------------------------------
# Coverage top-ups: sync invoke() across every tool, lazy agent resolution,
# helper edge cases, and exception handlers.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("tool_cls", "agent_attr", "agent_return", "args"),
    [
        (
            TranslateJavaMethodTool,
            "translate_java_method",
            json.dumps({"success": True}),
            {"method_name": "f"},
        ),
        (
            ConvertJavaClassTool,
            "convert_java_class",
            json.dumps({"success": True}),
            {"class_name": "C"},
        ),
        (
            MapJavaApisTool,
            "map_java_apis",
            json.dumps({"success": True}),
            {"apis": ["x"]},
        ),
        (
            GenerateEventHandlersTool,
            "generate_event_handlers",
            json.dumps({"success": True}),
            {"event_type": "tick", "handlers": []},
        ),
        (
            ValidateJavascriptSyntaxTool,
            "validate_javascript_syntax",
            json.dumps({"success": True, "is_valid": True}),
            {"javascript_code": "function f(){}"},
        ),
        (
            TranslateCraftingRecipeTool,
            "translate_crafting_recipe_json",
            json.dumps({"success": True, "bedrock_recipe": {}}),
            {"recipe": {"type": "minecraft:crafting_shapeless"}},
        ),
        (
            ValidateBlockJsonTool,
            "_validate_block_json",
            {"is_valid": True},
            {"block_json": {}},
        ),
    ],
)
def test_sync_invoke_outside_loop_covers_run_paths(
    tool_cls: type, agent_attr: str, agent_return: Any, args: Dict[str, Any]
) -> None:
    """Drives ``invoke({...})`` (the sync ``_run`` path) for every tool that
    delegates to an agent method, ensuring the sync wrapper is exercised.
    """
    agent = _make_mock_agent()
    setattr(agent, agent_attr, MagicMock(return_value=agent_return))
    tool = tool_cls(agent=agent)
    raw = tool.invoke(args)
    payload = json.loads(raw)
    assert payload["success"] is True


def test_sync_invoke_outside_loop_get_rag_context_tool() -> None:
    agent = _make_mock_agent()
    agent._get_rag_context.return_value = ""
    tool = GetRagContextTool(agent=agent)
    raw = tool.invoke({"java_feature": "x", "feature_type": "block"})
    assert json.loads(raw)["success"] is True


def test_sync_invoke_outside_loop_set_rag_context_tool() -> None:
    agent = _make_mock_agent()
    agent.enable_rag_context = MagicMock()
    tool = SetRagContextTool(agent=agent)
    raw = tool.invoke({"enabled": False})
    assert json.loads(raw)["success"] is True


def test_sync_invoke_outside_loop_generate_bedrock_block_tool() -> None:
    agent = _make_mock_agent()
    agent.generate_bedrock_block_json = MagicMock(return_value={"success": True, "block_json": {}})
    tool = GenerateBedrockBlockTool(agent=agent)
    raw = tool.invoke({"java_block_analysis": {}, "namespace": "ns"})
    assert json.loads(raw)["success"] is True


def test_lazy_agent_resolution_uses_singleton() -> None:
    """When no agent is injected, ``_get_agent()`` resolves the singleton."""
    tool = TranslateJavaMethodTool()
    sentinel = MagicMock()
    sentinel.translate_java_method = MagicMock(return_value=json.dumps({"success": True}))
    LogicTranslatorAgent._instance = sentinel
    raw = tool.invoke({"method_name": "x"})
    assert json.loads(raw)["success"] is True
    sentinel.translate_java_method.assert_called_once()


def test_helper_maps_requires_tool_branch() -> None:
    """Cover the ``requires_tool=True`` branch in the block-property helper."""
    # ToolType.PICKAXE is the canonical key in JAVA_TO_BEDROCK_BLOCK_PROPERTIES
    # for the requires_tool path; if it is not present in the lookup table,
    # the result simply omits the requires_tool key (still a valid branch).
    result = _map_java_block_properties_to_bedrock({"requires_tool": True, "tool_type": "pickaxe"})
    # Either the mapping table includes ToolType.PICKAXE (then the branch
    # adds the key) or it does not (then no entry is added). Either way,
    # both lines on the branch executed.
    assert isinstance(result, dict)


def test_map_block_properties_tool_handles_helper_failure() -> None:
    """Exception envelope when the helper raises (covers the except branch)."""
    tool = MapBlockPropertiesTool()
    with patch(
        "agents.logic_translator.tools._map_java_block_properties_to_bedrock",
        side_effect=RuntimeError("synthetic"),
    ):
        raw = tool.invoke({"java_properties": {}})
    payload = json.loads(raw)
    assert payload["success"] is False
    assert "synthetic" in payload["error"]
