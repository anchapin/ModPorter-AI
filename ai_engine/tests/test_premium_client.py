"""
Tests for premium_client.py - PortKit Premium Conversion Client

Run with: pytest ai_engine/tests/test_premium_client.py -v
"""

import pytest
from unittest.mock import patch
import httpx  # noqa: F401 - used dynamically in test methods


class TestConversionResult:
    """Tests for ConversionResult dataclass."""

    def test_conversion_result_fields(self):
        from ai_engine.mmsd.premium_client import ConversionResult

        result = ConversionResult(
            success=True,
            reasoning="Test reasoning",
            bedrock_manifest='{"format_version": 2}',
            bedrock_script="console.log('test');",
            model_used="deepseek-v4-pro",
            latency_ms=1500,
            tier="premium",
        )

        assert result.success is True
        assert result.reasoning == "Test reasoning"
        assert result.bedrock_manifest == '{"format_version": 2}'
        assert result.bedrock_script == "console.log('test');"
        assert result.model_used == "deepseek-v4-pro"
        assert result.tier == "premium"
        assert result.latency_ms == 1500

    def test_conversion_result_defaults(self):
        from ai_engine.mmsd.premium_client import ConversionResult

        result = ConversionResult(success=False, error="Test error")

        assert result.success is False
        assert result.reasoning == ""
        assert result.bedrock_manifest == ""
        assert result.bedrock_script == ""
        assert result.tier == "premium"
        assert result.error == "Test error"


class TestMODELCONFIGS:
    """Tests for model configurations."""

    def test_all_models_have_required_fields(self):
        from ai_engine.mmsd.premium_client import MODEL_CONFIGS

        for model_key, config in MODEL_CONFIGS.items():
            assert "model_id" in config, f"{model_key} missing model_id"
            assert "provider" in config, f"{model_key} missing provider"
            assert "max_tokens" in config, f"{model_key} missing max_tokens"
            assert "temperature" in config, f"{model_key} missing temperature"
            assert config["provider"] == "openrouter"

    def test_default_fallback_order(self):
        from ai_engine.mmsd.premium_client import DEFAULT_FALLBACK_ORDER, MODEL_CONFIGS

        for model in DEFAULT_FALLBACK_ORDER:
            assert model in MODEL_CONFIGS, f"{model} not in MODEL_CONFIGS"


class TestFEW_SHOT_EXAMPLES:
    """Tests for few-shot examples."""

    def test_few_shot_examples_exist(self):
        from ai_engine.mmsd.premium_client import FEW_SHOT_EXAMPLES

        assert len(FEW_SHOT_EXAMPLES) == 3

    def test_few_shot_examples_structure(self):
        from ai_engine.mmsd.premium_client import FEW_SHOT_EXAMPLES

        for example in FEW_SHOT_EXAMPLES:
            assert "name" in example
            assert "user" in example
            assert "assistant" in example
            assert "java" in example["user"].lower() or "java" in example["assistant"].lower()


class TestPortKitPremiumInit:
    """Tests for PortKitPremium initialization."""

    def test_init_requires_api_key(self):
        from ai_engine.mmsd.premium_client import PortKitPremium

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
                PortKitPremium()

    def test_init_with_env_api_key(self):
        from ai_engine.mmsd.premium_client import PortKitPremium

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-test-key"}):
            client = PortKitPremium()
            assert client.api_key == "sk-test-key"
            client.close()

    def test_init_with_explicit_api_key(self):
        from ai_engine.mmsd.premium_client import PortKitPremium

        client = PortKitPremium(api_key="sk-explicit-key")
        assert client.api_key == "sk-explicit-key"
        client.close()

    def test_init_default_model(self):
        from ai_engine.mmsd.premium_client import PortKitPremium

        client = PortKitPremium(api_key="sk-test-key")
        assert client.model == "deepseek-v4-pro"
        client.close()

    def test_init_custom_model(self):
        from ai_engine.mmsd.premium_client import PortKitPremium

        client = PortKitPremium(api_key="sk-test-key", model="kimi-k2")
        assert client.model == "kimi-k2"
        client.close()

    def test_init_custom_fallback_models(self):
        from ai_engine.mmsd.premium_client import PortKitPremium

        client = PortKitPremium(
            api_key="sk-test-key",
            fallback_models=["kimi-k2", "deepseek-v4-pro"]
        )
        assert client.fallback_models == ["kimi-k2", "deepseek-v4-pro"]
        client.close()

    def test_context_manager(self):
        from ai_engine.mmsd.premium_client import PortKitPremium

        with PortKitPremium(api_key="sk-test-key") as client:
            assert client.api_key == "sk-test-key"


class TestPortKitPremiumMethods:
    """Tests for PortKitPremium methods."""

    def test_list_models(self):
        from ai_engine.mmsd.premium_client import PortKitPremium

        client = PortKitPremium(api_key="sk-test-key")
        models = client.list_models()

        assert "deepseek-v4-pro" in models
        assert "kimi-k2" in models
        assert models["deepseek-v4-pro"] == "deepseek/deepseek-chat-v3.1"
        client.close()

    def test_estimate_cost(self):
        from ai_engine.mmsd.premium_client import PortKitPremium

        client = PortKitPremium(api_key="sk-test-key")
        cost = client.estimate_cost(
            instruction="Test mod",
            java_source="public class Test {}"
        )

        assert "model" in cost
        assert "input_tokens_est" in cost
        assert "output_tokens_est" in cost
        assert "cost_usd_est" in cost
        assert cost["cost_usd_est"] > 0
        client.close()

    def test_estimate_cost_with_specific_model(self):
        from ai_engine.mmsd.premium_client import PortKitPremium

        client = PortKitPremium(api_key="sk-test-key")
        cost = client.estimate_cost(
            instruction="Test mod",
            java_source="public class Test {}",
            model="kimi-k2"
        )

        assert cost["model"] == "kimi-k2"
        client.close()


class TestBuildMessages:
    """Tests for message building."""

    def test_build_messages_structure(self):
        from ai_engine.mmsd.premium_client import PortKitPremium

        client = PortKitPremium(api_key="sk-test-key")
        messages = client._build_messages("Test instruction", "public class Test {}")

        assert len(messages) >= 5
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[-1]["role"] == "user"
        assert "Test instruction" in messages[-1]["content"]
        client.close()


class TestParseOutput:
    """Tests for output parsing."""

    def test_parse_output_extracts_reasoning_and_manifest(self):
        from ai_engine.mmsd.premium_client import PortKitPremium

        client = PortKitPremium(api_key="sk-test-key")
        output = """## Conversion Plan

1. **Block Registration**: Java uses `RegistryEvent` → Bedrock uses `blocks.json`

## Bedrock Add-on Output

### manifest.json
```json
{
    "format_version": 2,
    "header": {"name": "Test"}
}
```

### scripts/main.js
```javascript
import { world } from "@minecraft/server";
```"""

        result = client._parse_output(output, "deepseek-v4-pro", 1000)

        assert result.success is True
        assert "Block Registration" in result.reasoning
        assert "format_version" in result.bedrock_manifest
        assert "minecraft/server" in result.bedrock_script
        client.close()

    def test_parse_output_handles_missing_sections(self):
        from ai_engine.mmsd.premium_client import PortKitPremium

        client = PortKitPremium(api_key="sk-test-key")
        output = "No structured output here"

        result = client._parse_output(output, "deepseek-v4-pro", 1000)

        assert result.success is False
        client.close()


class TestAPIBases:
    """Tests for API base URLs."""

    def test_openrouter_base(self):
        from ai_engine.mmsd.premium_client import API_BASES

        assert API_BASES["openrouter"] == "https://openrouter.ai/api/v1"


class TestCLI:
    """Tests for CLI argument parsing."""

    def test_cli_help(self):
        from ai_engine.mmsd.premium_client import main
        import sys

        with patch.object(sys, "argv", ["premium_client.py", "--help"]):
            with pytest.raises(SystemExit):
                main()
