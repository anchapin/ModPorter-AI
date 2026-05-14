"""Unit tests for the rebuilt LLM backend factories (issue #1201).

After the LangChain/LangGraph migration the bespoke ``RateLimitedChatOpenAI``,
``RateLimitedZAI`` and ``OpenAICompatibleLLM`` wrappers are gone — every
factory returns a stock LangChain ``BaseChatModel`` that uses
``langchain_core.rate_limiters.InMemoryRateLimiter`` for throttling.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from langchain_core.language_models import BaseChatModel

from utils.rate_limiter import (
    OpenAICompatibleConfig,
    RateLimitConfig,
    RateLimiter,
    ZAIConfig,
    create_ollama_llm,
    create_openai_compatible_llm,
    create_rate_limited_llm,
    create_z_ai_llm,
    get_fallback_llm,
    get_llm_backend,
)


class TestRateLimiterShim:
    """The legacy RateLimiter class is now a no-op shim retained for back-compat."""

    def test_construct_with_default_config(self):
        limiter = RateLimiter()
        assert isinstance(limiter.config, RateLimitConfig)
        assert limiter.config.requests_per_minute == 60

    def test_wait_and_record_are_no_ops(self):
        limiter = RateLimiter()
        # Must not raise; behaviour is delegated to the LangChain limiter.
        limiter.wait_if_needed(123)
        limiter.record_request(456)


class TestOpenAIFactory:
    @patch("langchain_openai.ChatOpenAI")
    def test_create_rate_limited_llm_returns_chat_openai(self, mock_chat):
        fake = MagicMock(spec=BaseChatModel)
        mock_chat.return_value = fake
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test"}):
            llm = create_rate_limited_llm("gpt-4o-mini", temperature=0.0)
        assert llm is fake
        # Keyword args include the LangChain rate limiter
        kwargs = mock_chat.call_args.kwargs
        assert "rate_limiter" in kwargs
        assert kwargs["model"] == "gpt-4o-mini"
        assert kwargs["temperature"] == 0.0


class TestZAIFactory:
    @patch("langchain_openai.ChatOpenAI")
    def test_create_z_ai_llm_uses_openai_compatible_endpoint(self, mock_chat):
        fake = MagicMock(spec=BaseChatModel)
        mock_chat.return_value = fake
        cfg = ZAIConfig(api_key="test", model="glm-4-test", base_url="https://api.z.ai/v1")
        llm = create_z_ai_llm(cfg)
        assert llm is fake
        kwargs = mock_chat.call_args.kwargs
        assert kwargs["base_url"] == "https://api.z.ai/v1"
        assert kwargs["model"] == "glm-4-test"
        assert kwargs["api_key"] == "test"

    def test_create_z_ai_llm_requires_api_key(self):
        cfg = ZAIConfig(api_key="")
        with patch.dict(os.environ, {"Z_AI_API_KEY": ""}, clear=False):
            with pytest.raises(ValueError, match="Z.AI API key is required"):
                create_z_ai_llm(cfg)


class TestOpenAICompatibleFactory:
    @patch("langchain_openai.ChatOpenAI")
    def test_create_openai_compatible_llm_uses_config(self, mock_chat):
        fake = MagicMock(spec=BaseChatModel)
        mock_chat.return_value = fake
        cfg = OpenAICompatibleConfig(
            api_key="key",
            model="custom-model",
            base_url="https://example.com/v1",
            provider="openrouter",
        )
        llm = create_openai_compatible_llm(cfg)
        assert llm is fake
        kwargs = mock_chat.call_args.kwargs
        assert kwargs["base_url"] == "https://example.com/v1"
        assert kwargs["model"] == "custom-model"


class TestOllamaFactory:
    @patch("langchain_ollama.ChatOllama")
    def test_create_ollama_llm_returns_chat_ollama(self, mock_chat):
        fake = MagicMock(spec=BaseChatModel)
        mock_chat.return_value = fake
        llm = create_ollama_llm(model_name="llama3.2", base_url="http://ollama:11434")
        assert llm is fake
        kwargs = mock_chat.call_args.kwargs
        assert kwargs["model"] == "llama3.2"
        assert kwargs["base_url"] == "http://ollama:11434"
        assert "rate_limiter" in kwargs

    @patch("langchain_ollama.ChatOllama")
    def test_create_ollama_llm_strips_litellm_prefix(self, mock_chat):
        fake = MagicMock(spec=BaseChatModel)
        mock_chat.return_value = fake
        create_ollama_llm(model_name="ollama/codellama")
        kwargs = mock_chat.call_args.kwargs
        assert kwargs["model"] == "codellama"


class TestBackendSelection:
    def test_get_llm_backend_prefers_openai_compatible_when_base_url_set(self):
        with (
            patch("utils.config.Config") as mock_cfg,
            patch("utils.rate_limiter.create_openai_compatible_llm") as mock_factory,
        ):
            mock_cfg.return_value.LLM_BASE_URL = "https://example.com/v1"
            mock_cfg.return_value.LLM_PROVIDER = "openrouter"
            fake = MagicMock(spec=BaseChatModel)
            mock_factory.return_value = fake
            assert get_llm_backend() is fake
            mock_factory.assert_called_once()

    def test_get_llm_backend_falls_back_to_openai_when_others_disabled(self):
        with (
            patch("utils.config.Config") as mock_cfg,
            patch("utils.rate_limiter.create_rate_limited_llm") as mock_oai,
            patch.dict(os.environ, {"USE_Z_AI": "false", "USE_OLLAMA": "false"}, clear=False),
        ):
            mock_cfg.return_value.LLM_BASE_URL = ""
            fake = MagicMock(spec=BaseChatModel)
            mock_oai.return_value = fake
            assert get_llm_backend() is fake

    @patch("langchain_ollama.ChatOllama")
    def test_get_fallback_llm_returns_chat_ollama(self, mock_chat):
        fake = MagicMock(spec=BaseChatModel)
        mock_chat.return_value = fake
        llm = get_fallback_llm()
        assert llm is fake
        kwargs = mock_chat.call_args.kwargs
        assert kwargs["model"] == "llama3.2"
