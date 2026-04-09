"""
Unit tests for RateLimiter and LLM wrappers.
"""

import pytest
import time
from unittest.mock import MagicMock, patch
from utils.rate_limiter import RateLimiter, RateLimitConfig, with_rate_limiting, _execute_with_retry, RateLimitedChatOpenAI, create_ollama_llm, RateLimitedZAI

class TestRateLimiter:
    def test_clean_old_requests(self):
        limiter = RateLimiter()
        now = time.time()
        limiter.request_times = [now - 70, now - 30]
        limiter.token_usage = [{"time": now - 70, "tokens": 100}, {"time": now - 30, "tokens": 200}]
        
        limiter._clean_old_requests(now)
        assert len(limiter.request_times) == 1
        assert len(limiter.token_usage) == 1
        assert limiter.request_times[0] == now - 30

    def test_should_rate_limit_requests(self):
        config = RateLimitConfig(requests_per_minute=2)
        limiter = RateLimiter(config)
        now = time.time()
        limiter.request_times = [now - 10, now - 5]
        
        should_limit, wait_time = limiter._should_rate_limit()
        assert should_limit is True
        assert wait_time > 0

    def test_should_rate_limit_tokens(self):
        config = RateLimitConfig(tokens_per_minute=1000)
        limiter = RateLimiter(config)
        now = time.time()
        limiter.token_usage = [{"time": now - 5, "tokens": 900}]
        
        # Adding 200 more tokens should trigger limit
        should_limit, wait_time = limiter._should_rate_limit(estimated_tokens=200)
        assert should_limit is True
        assert wait_time > 0

    def test_wait_if_needed(self):
        limiter = RateLimiter()
        with patch.object(limiter, '_should_rate_limit', return_value=(True, 0.1)), \
             patch('time.sleep') as mock_sleep:
            limiter.wait_if_needed()
            mock_sleep.assert_called_once_with(0.1)

class TestExecuteWithRetry:
    def test_success_first_try(self):
        func = MagicMock(return_value="success")
        limiter = RateLimiter()
        res = _execute_with_retry(func, limiter, RateLimitConfig())
        assert res == "success"
        assert func.call_count == 1

    def test_retry_on_429(self):
        func = MagicMock(side_effect=[Exception("Rate limit 429"), "success"])
        limiter = RateLimiter()
        config = RateLimitConfig(max_retries=1, base_delay=0.01)
        with patch('time.sleep'):
            res = _execute_with_retry(func, limiter, config)
            assert res == "success"
            assert func.call_count == 2

    def test_retry_on_temporary_error(self):
        func = MagicMock(side_effect=[Exception("503 Service Unavailable"), "success"])
        limiter = RateLimiter()
        config = RateLimitConfig(max_retries=1, base_delay=0.01)
        with patch('time.sleep'):
            res = _execute_with_retry(func, limiter, config)
            assert res == "success"

    def test_no_retry_on_fatal_error(self):
        func = MagicMock(side_effect=ValueError("Invalid arg"))
        limiter = RateLimiter()
        with pytest.raises(ValueError):
            _execute_with_retry(func, limiter, RateLimitConfig())
        assert func.call_count == 1

class TestRateLimitedChatOpenAI:
    @patch('utils.rate_limiter.ChatOpenAI')
    def test_initialization(self, mock_chat):
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            llm = RateLimitedChatOpenAI(model_name="gpt-4")
            assert llm.model_name == "gpt-4"
            mock_chat.assert_called_once()

    @patch('utils.rate_limiter.ChatOpenAI')
    def test_invoke(self, mock_chat):
        mock_instance = mock_chat.return_value
        mock_instance.invoke.return_value = "response"
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            llm = RateLimitedChatOpenAI()
            res = llm.invoke("hello")
            assert res == "response"

class TestOllamaLLM:
    def test_create_ollama_llm_success(self):
        mock_litellm = MagicMock()
        with patch.dict('sys.modules', {'litellm': mock_litellm}):
            mock_litellm.completion.return_value = MagicMock(choices=[MagicMock(message=MagicMock(content="hi"), finish_reason="stop")], usage=None)
            
            llm = create_ollama_llm(model_name="llama3")
            res = llm.invoke("hello")
            assert res.content == "hi"

    def test_create_ollama_llm_import_error(self):
        with patch.dict('sys.modules', {'litellm': None}):
            with pytest.raises(ImportError):
                create_ollama_llm()

class TestZAI:
    def test_zai_initialization(self):
        with patch.dict('os.environ', {'Z_AI_API_KEY': 'test-key', 'Z_AI_BASE_URL': 'http://z.ai'}):
            with patch('openai.OpenAI'):
                llm = RateLimitedZAI()
                assert llm.config.api_key == "test-key"

    def test_zai_invoke(self):
        with patch.dict('os.environ', {'Z_AI_API_KEY': 'test-key'}):
            with patch('openai.OpenAI') as mock_openai:
                mock_client = mock_openai.return_value
                mock_client.chat.completions.create.return_value = MagicMock(choices=[MagicMock(message=MagicMock(content="z-hi"), finish_reason="stop")], usage=None)
                
                llm = RateLimitedZAI()
                res = llm.invoke("hello")
                assert res.content == "z-hi"
class TestDecorators:
    def test_with_rate_limiting(self):
        func = MagicMock(return_value="ok")
        decorated = with_rate_limiting()(func)
        assert decorated("test") == "ok"
        assert func.called

class TestExecuteWithRetryExhaustion:
    def test_exhaust_retries_429(self):
        func = MagicMock(side_effect=Exception("429 Too Many Requests"))
        limiter = RateLimiter()
        config = RateLimitConfig(max_retries=1, base_delay=0.01)
        with patch('time.sleep'), patch('logging.Logger.error'):
            with pytest.raises(Exception, match="429"):
                _execute_with_retry(func, limiter, config)
        assert func.call_count == 2

    def test_exhaust_retries_temporary(self):
        func = MagicMock(side_effect=Exception("503 error"))
        limiter = RateLimiter()
        config = RateLimitConfig(max_retries=1, base_delay=0.01)
        with patch('time.sleep'):
            with pytest.raises(Exception, match="503"):
                _execute_with_retry(func, limiter, config)

class TestRateLimitedChatOpenAIOverrides:
    @patch('utils.rate_limiter.ChatOpenAI')
    def test_env_overrides(self, mock_chat):
        with patch.dict('os.environ', {
            'OPENAI_API_KEY': 'key',
            'OPENAI_RPM_LIMIT': '10',
            'OPENAI_TPM_LIMIT': '1000',
            'OPENAI_MAX_RETRIES': '5'
        }):
            llm = RateLimitedChatOpenAI()
            assert llm.rate_config.requests_per_minute == 10
            assert llm.rate_config.tokens_per_minute == 1000
            assert llm.rate_config.max_retries == 5

    @patch('utils.rate_limiter.ChatOpenAI')
    def test_other_methods(self, mock_chat):
        mock_instance = mock_chat.return_value
        mock_instance.generate.return_value = "gen"
        mock_instance.predict.return_value = "pred"

        with patch.dict('os.environ', {'OPENAI_API_KEY': 'key'}):
            llm = RateLimitedChatOpenAI()
            assert llm.generate(["msg"]) == "gen"
            assert llm.predict("hi") == "pred"
            assert llm("call") == mock_instance.invoke.return_value

class TestLiteLLMOllamaWrapperMethods:
    def test_wrapper_methods(self):
        mock_litellm = MagicMock()
        with patch.dict('sys.modules', {'litellm': mock_litellm}):
            mock_litellm.completion.return_value = MagicMock(choices=[MagicMock(message=MagicMock(content="resp"), finish_reason="stop")], usage=None)

            llm = create_ollama_llm()
            assert llm.generate("q").content == "resp"
            assert llm.predict("q").content == "resp"
            assert llm("q").content == "resp"
            llm.enable_crew_mode()
            llm.disable_crew_mode()

    def test_wrapper_invoke_complex_input(self):
        mock_litellm = MagicMock()
        with patch.dict('sys.modules', {'litellm': mock_litellm}):
            llm = create_ollama_llm()

            # Message objects
            msg = MagicMock(); msg.content = "cont"; msg.type = "user"
            llm.invoke([msg])
            assert mock_litellm.completion.called

class TestRateLimitedZAIOverrides:
    def test_zai_overrides(self):
        with patch.dict('os.environ', {
            'Z_AI_API_KEY': 'key',
            'Z_AI_MODEL': 'model-x',
            'Z_AI_MAX_RETRIES': '2'
        }), patch('openai.OpenAI'):
            llm = RateLimitedZAI()
            assert llm.config.model == "model-x"
            assert llm.config.max_retries == 2

            with patch.object(llm, '_execute_with_rate_limit', return_value="ok"):
                assert llm.generate("q") == "ok"
                assert llm.predict("q") == "ok"

