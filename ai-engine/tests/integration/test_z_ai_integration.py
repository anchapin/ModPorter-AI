"""Integration tests for the Z.AI LLM backend (issue #1201).

After the LangChain/LangGraph migration, ``create_z_ai_llm`` returns a
stock ``langchain_openai.ChatOpenAI`` configured against the Z.AI
OpenAI-compatible endpoint. The tests below verify environment-variable
plumbing and provider-priority logic without making real network calls.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from langchain_core.language_models import BaseChatModel

from utils.rate_limiter import (
    ZAIConfig,
    create_z_ai_llm,
    get_llm_backend,
)


class TestZAIIntegration:
    """Configuration and provider-priority tests for the Z.AI backend."""

    @pytest.mark.asyncio
    async def test_z_ai_config_from_environment(self):
        env_vars = {
            "Z_AI_API_KEY": "test-key",
            "Z_AI_MODEL": "glm-4-test",
            "Z_AI_BASE_URL": "https://test.z.ai/v1",
            "Z_AI_MAX_RETRIES": "5",
            "Z_AI_TIMEOUT": "600",
            "Z_AI_TEMPERATURE": "0.5",
            "Z_AI_MAX_TOKENS": "2000",
        }

        with patch.dict(os.environ, env_vars):
            llm = create_z_ai_llm(ZAIConfig())

            assert isinstance(llm, BaseChatModel)
            # ChatOpenAI exposes the configured model and base_url as attributes.
            assert (
                getattr(llm, "model_name", None) == "glm-4-test"
                or getattr(llm, "model", None) == "glm-4-test"
            )
            base_url = str(getattr(llm, "openai_api_base", "") or getattr(llm, "base_url", ""))
            assert "test.z.ai/v1" in base_url

    @pytest.mark.asyncio
    async def test_z_ai_missing_api_key(self):
        with patch.dict(os.environ, {"Z_AI_API_KEY": ""}, clear=False):
            with pytest.raises(ValueError, match="Z.AI API key is required"):
                create_z_ai_llm()

    @pytest.mark.asyncio
    async def test_get_llm_backend_prioritises_z_ai(self):
        env_vars = {"USE_Z_AI": "true", "Z_AI_API_KEY": "test-key"}
        # Disable the OpenAI-compatible path so Z.AI gets selected.
        with patch.dict(os.environ, env_vars, clear=False):
            with patch(
                "utils.rate_limiter.create_openai_compatible_llm", side_effect=Exception("disabled")
            ):
                with patch("langchain_openai.ChatOpenAI") as mock_chat:
                    fake_model = MagicMock(spec=BaseChatModel)
                    mock_chat.return_value = fake_model
                    # Ensure LLM_BASE_URL won't trigger compatible path
                    with patch("utils.config.Config") as mock_cfg:
                        mock_cfg.return_value.LLM_BASE_URL = ""
                        llm = get_llm_backend()
                        assert llm is fake_model

    @pytest.mark.asyncio
    async def test_get_llm_backend_falls_back_to_ollama(self):
        env_vars = {"USE_Z_AI": "false", "USE_OLLAMA": "true"}
        with patch.dict(os.environ, env_vars, clear=False):
            with (
                patch("utils.rate_limiter.create_ollama_llm") as mock_ollama,
                patch("utils.config.Config") as mock_cfg,
            ):
                mock_cfg.return_value.LLM_BASE_URL = ""
                fake = MagicMock(spec=BaseChatModel)
                mock_ollama.return_value = fake

                llm = get_llm_backend()
                mock_ollama.assert_called_once()
                assert llm is fake


@pytest.mark.integration
class TestZAIIntegrationWithLangGraph:
    """Z.AI in the LangGraph pipeline produces a BaseChatModel."""

    @pytest.mark.asyncio
    async def test_z_ai_llm_in_langgraph_pipeline(self):
        env_vars = {"USE_Z_AI": "true", "Z_AI_API_KEY": "test-key"}
        with patch.dict(os.environ, env_vars, clear=False):
            with (
                patch("utils.config.Config") as mock_cfg,
                patch("langchain_openai.ChatOpenAI") as mock_chat,
            ):
                mock_cfg.return_value.LLM_BASE_URL = ""
                fake_llm = MagicMock(spec=BaseChatModel)
                mock_chat.return_value = fake_llm

                llm = get_llm_backend()
                # Must be a BaseChatModel so LangGraph nodes can use it.
                assert llm is fake_llm


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
