"""
Unit tests for FewShotEnhancerAgent

Tests the few-shot enhancement agent for hybrid conversion workflow.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass


class TestFewShotEnhancerAgent:
    """Test suite for FewShotEnhancerAgent"""

    @pytest.fixture
    def sample_java_source(self):
        return '''package com.example.mod;

import net.minecraft.item.Item;
import net.minecraft.item.ItemSword;
import net.minecraft.item.ItemStack;
import net.minecraft.creativetab.CreativeTabs;
import net.minecraftforge.event.RegistryEvent;
import net.minecraftforge.fml.common.Mod;

@Mod(modid = "testmod", name = "Test Mod", version = "1.0")
public class TestMod {
    public static Item TEST_SWORD = new ItemSword(Item.ToolMaterial.DIAMOND) {
        @Override
        public boolean hitEntity(ItemStack stack, EntityLiving target, EntityLiving attacker) {
            target.setGlowing(true);
            return super.hitEntity(stack, target, attacker);
        }
    }.setCreativeTab(CreativeTabs.COMBAT)
      .setRegistryName("test_sword");
}'''

    @pytest.fixture
    def sample_instruction(self):
        return "Test sword mod that makes entities glow when hit"

    @pytest.fixture
    def mock_premium_client(self):
        """Mock premium client for testing without API calls"""
        with patch("agents.fewshot_enhancer_agent.PortKitPremium") as mock_client:
            instance = MagicMock()
            instance.list_models.return_value = {
                "deepseek-v4-pro": "deepseek/deepseek-chat-v3.1",
                "kimi-k2": "moonshotai/kimi-k2",
            }
            instance.estimate_cost.return_value = {
                "model": "deepseek-v4-pro",
                "input_tokens_est": 1200,
                "output_tokens_est": 2048,
                "cost_usd_est": 0.0054,
            }
            mock_client.return_value = instance
            yield instance

    def test_agent_initialization_default_model(self):
        """Test agent initializes with default model"""
        from agents.fewshot_enhancer_agent import FewShotEnhancerAgent

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("agents.fewshot_enhancer_agent.PortKitPremium") as mock_client:
                mock_client.return_value = MagicMock()
                agent = FewShotEnhancerAgent()

                assert agent.model == "deepseek-v4-pro"
                assert agent._client is None  # Lazily initialized

    def test_agent_initialization_custom_model(self):
        """Test agent initializes with custom model"""
        from agents.fewshot_enhancer_agent import FewShotEnhancerAgent

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("agents.fewshot_enhancer_agent.PortKitPremium"):
                agent = FewShotEnhancerAgent(model="kimi-k2")

                assert agent.model == "kimi-k2"

    def test_agent_requires_api_key(self):
        """Test agent handles missing API key gracefully"""
        from agents.fewshot_enhancer_agent import FewShotEnhancerAgent

        with patch.dict("os.environ", {}, clear=True):
            agent = FewShotEnhancerAgent()
            client = agent._get_client()

            assert client is None

    def test_enhance_returns_enhancement_result(self, sample_java_source, sample_instruction):
        """Test enhance() returns proper EnhancementResult"""
        from agents.fewshot_enhancer_agent import FewShotEnhancerAgent, EnhancementResult

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.reasoning = "1. **Item Registration**: Java → Bedrock"
        mock_result.bedrock_manifest = '{"format_version": 2}'
        mock_result.bedrock_script = 'import { world } from "@minecraft/server";'
        mock_result.model_used = "deepseek-v4-pro"
        mock_result.latency_ms = 5000
        mock_result.error = ""

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("agents.fewshot_enhancer_agent.PortKitPremium") as mock_client:
                mock_client.return_value = MagicMock()
                mock_client.return_value.convert.return_value = mock_result

                agent = FewShotEnhancerAgent()
                result = agent.enhance(sample_java_source, sample_instruction)

                assert isinstance(result, EnhancementResult)
                assert result.success is True
                assert result.model_used == "deepseek-v4-pro"

    def test_enhance_handles_api_failure(self, sample_java_source, sample_instruction):
        """Test enhance() handles API errors gracefully"""
        from agents.fewshot_enhancer_agent import FewShotEnhancerAgent

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("agents.fewshot_enhancer_agent.PortKitPremium") as mock_client:
                mock_client.return_value = MagicMock()
                mock_client.return_value.convert.side_effect = Exception("API Error")

                agent = FewShotEnhancerAgent()
                result = agent.enhance(sample_java_source, sample_instruction)

                assert result.success is False
                assert "API Error" in result.error

    def test_enhance_batch(self, sample_java_source, sample_instruction):
        """Test batch enhancement with multiple conversions"""
        from agents.fewshot_enhancer_agent import FewShotEnhancerAgent, EnhancementResult

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.reasoning = "Conversion"
        mock_result.bedrock_manifest = "{}"
        mock_result.bedrock_script = ""
        mock_result.model_used = "deepseek-v4-pro"
        mock_result.latency_ms = 1000
        mock_result.error = ""

        conversions = [
            {"java_source": sample_java_source, "instruction": sample_instruction},
            {"java_source": sample_java_source, "instruction": "Another mod"},
        ]

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("agents.fewshot_enhancer_agent.PortKitPremium") as mock_client:
                mock_client.return_value = MagicMock()
                mock_client.return_value.convert.return_value = mock_result

                agent = FewShotEnhancerAgent()
                results = agent.enhance_batch(conversions)

                assert len(results) == 2
                assert all(isinstance(r, EnhancementResult) for r in results)

    def test_estimate_cost(self, sample_java_source, sample_instruction):
        """Test cost estimation"""
        from agents.fewshot_enhancer_agent import FewShotEnhancerAgent

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("agents.fewshot_enhancer_agent.PortKitPremium") as mock_client:
                mock_client.return_value = MagicMock()
                mock_client.return_value.estimate_cost.return_value = {
                    "model": "deepseek-v4-pro",
                    "input_tokens_est": 1200,
                    "output_tokens_est": 2048,
                    "cost_usd_est": 0.0054,
                }

                agent = FewShotEnhancerAgent()
                cost = agent.estimate_cost(sample_instruction, sample_java_source)

                assert cost["cost_usd_est"] == 0.0054

    def test_estimate_quality_with_manifest(self):
        """Test quality estimation for manifest-containing output"""
        from agents.fewshot_enhancer_agent import FewShotEnhancerAgent, ConversionResult

        result = ConversionResult(
            success=True,
            reasoning="## Conversion Plan\n\n1. Item Registration",
            bedrock_manifest='{"format_version": 2, "header": {"name": "Test"}, "modules": []}',
            bedrock_script='import { world } from "@minecraft/server";\nworld.afterEvents.entityHitEntity.subscribe(() => {});',
            model_used="deepseek-v4-pro",
            tier="premium",
            latency_ms=5000,
            error="",
        )

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("agents.fewshot_enhancer_agent.PortKitPremium"):
                agent = FewShotEnhancerAgent()
                score = agent._estimate_quality(result)

                assert score > 0
                assert score <= 10

    def test_estimate_quality_low_output(self):
        """Test quality estimation for minimal output"""
        from agents.fewshot_enhancer_agent import FewShotEnhancerAgent, ConversionResult

        result = ConversionResult(
            success=True,
            reasoning="",
            bedrock_manifest="",
            bedrock_script="",
            model_used="deepseek-v4-pro",
            tier="premium",
            latency_ms=5000,
            error="",
        )

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("agents.fewshot_enhancer_agent.PortKitPremium"):
                agent = FewShotEnhancerAgent()
                score = agent._estimate_quality(result)

                assert score == 0

    def test_context_manager(self):
        """Test agent works as context manager"""
        from agents.fewshot_enhancer_agent import FewShotEnhancerAgent

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("agents.fewshot_enhancer_agent.PortKitPremium") as mock_client:
                mock_instance = MagicMock()
                mock_client.return_value = mock_instance

                with FewShotEnhancerAgent() as agent:
                    assert agent is not None
                    # Access _get_client() to initialize it
                    agent._get_client()

                mock_instance.close.assert_called_once()

    def test_close(self):
        """Test close() method"""
        from agents.fewshot_enhancer_agent import FewShotEnhancerAgent

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("agents.fewshot_enhancer_agent.PortKitPremium") as mock_client:
                mock_client.return_value = MagicMock()

                agent = FewShotEnhancerAgent()
                agent._get_client()  # Initialize client
                agent.close()

                mock_client.return_value.close.assert_called_once()
                assert agent._client is None


class TestFewShotEnhancerTools:
    """Test suite for FewShotEnhancerTools"""

    def test_enhance_tool_returns_string(self):
        """Test enhance_tool returns formatted string"""
        from agents.fewshot_enhancer_agent import FewShotEnhancerTools, EnhancementResult

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.reasoning = "Test reasoning"
        mock_result.bedrock_manifest = '{"format_version": 2}'
        mock_result.bedrock_script = 'import { world } from "@minecraft/server";'
        mock_result.model_used = "deepseek-v4-pro"
        mock_result.latency_ms = 5000
        mock_result.quality_score = 7.5

        with patch("agents.fewshot_enhancer_agent.FewShotEnhancerAgent") as mock_agent_class:
            mock_agent_class.return_value.enhance.return_value = mock_result

            result = FewShotEnhancerTools.enhance_tool(
                java_source="public class Test {}",
                instruction="Test mod",
            )

            assert isinstance(result, str)
            assert "deepseek-v4-pro" in result
            assert "Test reasoning" in result

    def test_enhance_tool_failure(self):
        """Test enhance_tool handles failure"""
        from agents.fewshot_enhancer_agent import FewShotEnhancerTools, EnhancementResult

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "API Error"

        with patch("agents.fewshot_enhancer_agent.FewShotEnhancerAgent") as mock_agent_class:
            mock_agent_class.return_value.enhance.return_value = mock_result

            result = FewShotEnhancerTools.enhance_tool(
                java_source="public class Test {}",
                instruction="Test mod",
            )

            assert "Enhancement failed" in result
            assert "API Error" in result

    def test_get_tools(self):
        """Test get_tools returns list of tools"""
        from agents.fewshot_enhancer_agent import FewShotEnhancerTools

        tools = FewShotEnhancerTools.get_tools()

        assert isinstance(tools, list)
        assert len(tools) > 0
        assert callable(tools[0])


class TestEnhancementResult:
    """Test suite for EnhancementResult dataclass"""

    def test_enhancement_result_creation(self):
        """Test EnhancementResult can be created"""
        from agents.fewshot_enhancer_agent import EnhancementResult

        result = EnhancementResult(
            success=True,
            reasoning="Test",
            bedrock_manifest="{}",
            bedrock_script="",
            model_used="test-model",
            latency_ms=1000,
        )

        assert result.success is True
        assert result.quality_score == 0.0  # Default

    def test_enhancement_result_with_quality(self):
        """Test EnhancementResult with quality score"""
        from agents.fewshot_enhancer_agent import EnhancementResult

        result = EnhancementResult(
            success=True,
            reasoning="Test",
            bedrock_manifest="{}",
            bedrock_script="",
            model_used="test-model",
            latency_ms=1000,
            quality_score=7.5,
        )

        assert result.quality_score == 7.5
