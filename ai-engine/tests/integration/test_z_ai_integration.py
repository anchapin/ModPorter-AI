"""
Integration tests for Z.AI LLM backend
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from utils.rate_limiter import (
    create_z_ai_llm, 
    get_llm_backend,
    ZAIConfig,
    RateLimitedZAI
)


class TestZAIIntegration:
    """Test suite for Z.AI integration"""
    
    @pytest.mark.asyncio
    async def test_z_ai_config_from_environment(self):
        """Test that Z.AI configuration is correctly loaded from environment variables"""
        # Set up environment variables
        env_vars = {
            'Z_AI_API_KEY': 'test-key',
            'Z_AI_MODEL': 'glm-4-test',
            'Z_AI_BASE_URL': 'https://test.z.ai/v1',
            'Z_AI_MAX_RETRIES': '5',
            'Z_AI_TIMEOUT': '600',
            'Z_AI_TEMPERATURE': '0.5',
            'Z_AI_MAX_TOKENS': '2000'
        }
        
        with patch.dict(os.environ, env_vars):
            config = ZAIConfig()
            zai_llm = RateLimitedZAI(config)
            
            assert zai_llm.config.api_key == 'test-key'
            assert zai_llm.config.model == 'glm-4-test'
            assert zai_llm.config.base_url == 'https://test.z.ai/v1'
            assert zai_llm.config.max_retries == 5
            assert zai_llm.config.timeout == 600
            assert zai_llm.config.temperature == 0.5
            assert zai_llm.config.max_tokens == 2000
    
    @pytest.mark.asyncio
    async def test_z_ai_missing_api_key(self):
        """Test that Z.AI fails gracefully when API key is missing"""
        with patch.dict(os.environ, {'Z_AI_API_KEY': ''}, clear=False):
            with pytest.raises(ValueError, match="Z.AI API key is required"):
                create_z_ai_llm()
    
    @pytest.mark.asyncio
    async def test_get_llm_backend_prioritizes_z_ai(self):
        """Test that get_llm_backend() prioritizes Z.AI over other backends"""
        env_vars = {
            'USE_Z_AI': 'true',
            'Z_AI_API_KEY': 'test-key'
        }
        
        # Mock the Z.AI client to avoid actual API calls
        mock_client = MagicMock()
        
        with patch.dict(os.environ, env_vars):
            with patch('openai.OpenAI', return_value=mock_client):
                llm = get_llm_backend()
                assert isinstance(llm, RateLimitedZAI)
    
    @pytest.mark.asyncio
    async def test_get_llm_backend_fallback_to_ollama(self):
        """Test fallback to Ollama when Z.AI is not configured"""
        env_vars = {
            'USE_Z_AI': 'false',
            'USE_OLLAMA': 'true'
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            with patch('utils.rate_limiter.create_ollama_llm') as mock_ollama:
                mock_llm = MagicMock()
                mock_ollama.return_value = mock_llm
                
                llm = get_llm_backend()
                mock_ollama.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_z_ai_message_conversion(self):
        """Test that different input formats are correctly converted to messages"""
        env_vars = {'Z_AI_API_KEY': 'test-key'}
        
        with patch.dict(os.environ, env_vars):
            with patch('openai.OpenAI') as mock_openai:
                # Mock the OpenAI client and response
                mock_client = MagicMock()
                mock_openai.return_value = mock_client
                
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "Test response"
                mock_response.choices[0].finish_reason = "stop"
                mock_response.usage = MagicMock()
                mock_response.usage.model_dump.return_value = {"total_tokens": 10}
                
                mock_client.chat.completions.create.return_value = mock_response
                
                # Test string input
                zai_llm = create_z_ai_llm()
                messages = zai_llm._convert_to_messages("Hello world")
                assert messages == [{"role": "user", "content": "Hello world"}]
                
                # Test list input
                class MockMessage:
                    def __init__(self, content, msg_type="user"):
                        self.content = content
                        self.type = msg_type
                
                msg_list = [MockMessage("Hello"), MockMessage("How are you?")]
                messages = zai_llm._convert_to_messages(msg_list)
                assert len(messages) == 2
                assert messages[0]["role"] == "user"
                assert messages[0]["content"] == "Hello"
    
    @pytest.mark.asyncio
    async def test_z_ai_crew_mode_compatibility(self):
        """Test CrewAI compatibility mode"""
        env_vars = {'Z_AI_API_KEY': 'test-key'}
        
        with patch.dict(os.environ, env_vars):
            with patch('openai.OpenAI'):
                zai_llm = create_z_ai_llm()
                
                # Test CrewAI mode methods don't raise exceptions
                zai_llm.enable_crew_mode()
                zai_llm.disable_crew_mode()
    
    @pytest.mark.asyncio 
    async def test_z_ai_rate_limiting(self):
        """Test that rate limiting is applied to Z.AI calls"""
        env_vars = {'Z_AI_API_KEY': 'test-key'}
        
        with patch.dict(os.environ, env_vars):
            with patch('openai.OpenAI') as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client
                
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "Test response"
                mock_response.choices[0].finish_reason = "stop"
                mock_response.usage = MagicMock()
                mock_response.usage.model_dump.return_value = {"total_tokens": 10}
                
                mock_client.chat.completions.create.return_value = mock_response
                
                zai_llm = create_z_ai_llm()
                
                # Test that invoke works with rate limiting
                result = zai_llm.invoke("Test message")
                assert result.content == "Test response"
                
                # Verify the API client was called
                mock_client.chat.completions.create.assert_called()


@pytest.mark.integration
class TestZAIIntegrationWithCrewAI:
    """Test Z.AI integration specifically with CrewAI workflows"""
    
    @pytest.mark.asyncio
    async def test_z_ai_llm_in_crewai_workflow(self):
        """Test that Z.AI LLM can be used in CrewAI workflows"""
        env_vars = {
            'USE_Z_AI': 'true',
            'Z_AI_API_KEY': 'test-key'
        }
        
        with patch.dict(os.environ, env_vars):
            with patch('openai.OpenAI') as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client
                
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "CrewAI response"
                mock_response.choices[0].finish_reason = "stop"
                mock_response.usage = MagicMock()
                mock_response.usage.model_dump.return_value = {"total_tokens": 15}
                
                mock_client.chat.completions.create.return_value = mock_response
                
                # Test the invoke method (used by CrewAI)
                llm = get_llm_backend()
                result = llm.invoke("Analyze this Java code")
                
                assert result.content == "CrewAI response"
                assert 'model' in result.response_metadata
                assert 'finish_reason' in result.response_metadata
                assert 'usage' in result.response_metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
