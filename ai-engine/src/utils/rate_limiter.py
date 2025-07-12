"""
Rate limiting utility for OpenAI API calls and LLM interactions
"""

import time
import logging
from typing import Any, Callable
from functools import wraps
from dataclasses import dataclass
import os
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    requests_per_minute: int = 60
    tokens_per_minute: int = 60000
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0


class RateLimiter:
    """
    Rate limiter for OpenAI API calls with exponential backoff
    """
    
    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self.request_times: list = []
        self.token_usage: list = []
        self.last_request_time: float = 0
        
    def _clean_old_requests(self, current_time: float):
        """Remove requests older than 1 minute"""
        minute_ago = current_time - 60
        self.request_times = [t for t in self.request_times if t > minute_ago]
        self.token_usage = [t for t in self.token_usage if t['time'] > minute_ago]
    
    def _get_current_token_usage(self) -> int:
        """Get current token usage in the last minute"""
        return sum(t['tokens'] for t in self.token_usage)
    
    def _should_rate_limit(self, estimated_tokens: int = 1000) -> tuple[bool, float]:
        """Check if we should rate limit and return wait time"""
        current_time = time.time()
        self._clean_old_requests(current_time)
        
        # Check request rate
        if len(self.request_times) >= self.config.requests_per_minute:
            oldest_request = min(self.request_times)
            wait_time = 60 - (current_time - oldest_request)
            return True, max(0, wait_time)
        
        # Check token rate
        current_tokens = self._get_current_token_usage()
        if current_tokens + estimated_tokens > self.config.tokens_per_minute:
            oldest_token = min(self.token_usage, key=lambda x: x['time'])['time']
            wait_time = 60 - (current_time - oldest_token)
            return True, max(0, wait_time)
        
        return False, 0
    
    def record_request(self, tokens_used: int = 1000):
        """Record a successful request"""
        current_time = time.time()
        self.request_times.append(current_time)
        self.token_usage.append({'time': current_time, 'tokens': tokens_used})
        self.last_request_time = current_time
    
    def wait_if_needed(self, estimated_tokens: int = 1000):
        """Wait if rate limiting is needed"""
        should_limit, wait_time = self._should_rate_limit(estimated_tokens)
        if should_limit and wait_time > 0:
            logger.info(f"Rate limiting: waiting {wait_time:.2f} seconds")
            time.sleep(wait_time)


# Removed RateLimitedChatOpenAI class to avoid Pydantic compatibility issues
# Using function-based approach instead


def with_rate_limiting(rate_config: RateLimitConfig = None):
    """
    Decorator for adding rate limiting to any OpenAI API function
    """
    def decorator(func):
        rate_limiter = RateLimiter(rate_config)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return _execute_with_retry(func, rate_limiter, rate_config or RateLimitConfig(), *args, **kwargs)
        
        return wrapper
    return decorator


def _execute_with_retry(func: Callable, rate_limiter: RateLimiter, rate_config: RateLimitConfig, *args, **kwargs) -> Any:
    """Execute function with rate limiting and retry logic"""
    last_exception = None
    
    for attempt in range(rate_config.max_retries + 1):
        try:
            # Apply rate limiting
            estimated_tokens = len(str(args[0] if args else "").split()) * 1.3 if args else 1000
            rate_limiter.wait_if_needed(int(estimated_tokens))
            
            # Execute the function
            result = func(*args, **kwargs)
            
            # Record successful request
            rate_limiter.record_request(int(estimated_tokens))
            
            return result
            
        except Exception as e:
            last_exception = e
            error_msg = str(e).lower()
            
            # Check if it's a rate limit error
            if any(keyword in error_msg for keyword in ['rate limit', '429', 'too many requests']):
                if attempt < rate_config.max_retries:
                    wait_time = min(rate_config.base_delay * (rate_config.backoff_factor ** attempt), rate_config.max_delay)
                    logger.warning(f"Rate limit hit, retrying in {wait_time:.2f}s (attempt {attempt + 1}/{rate_config.max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Rate limit exceeded after {rate_config.max_retries} retries")
                    raise e
            
            # Check if it's a temporary error
            elif any(keyword in error_msg for keyword in ['timeout', 'connection', 'temporary', '503', '502']):
                if attempt < rate_config.max_retries:
                    wait_time = min(rate_config.base_delay * (rate_config.backoff_factor ** attempt), rate_config.max_delay)
                    logger.warning(f"Temporary error, retrying in {wait_time:.2f}s: {e}")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Temporary error persisted after {rate_config.max_retries} retries")
                    raise e
            
            # For other errors, don't retry
            else:
                logger.error(f"Non-retryable error: {e}")
                raise e
    
    # If we get here, all retries failed
    raise last_exception


def create_rate_limited_llm(model_name: str = "gpt-4", **kwargs):
    """
    Factory function to create a rate-limited LLM instance
    """
    # Default rate limiting configuration
    rate_config = RateLimitConfig(
        requests_per_minute=50,  # Conservative limit
        tokens_per_minute=40000,  # Conservative token limit
        max_retries=3,
        base_delay=1.0,
        max_delay=60.0,
        backoff_factor=2.0
    )
    
    # Override with environment variables if available
    if os.getenv("OPENAI_RPM_LIMIT"):
        rate_config.requests_per_minute = int(os.getenv("OPENAI_RPM_LIMIT"))
    if os.getenv("OPENAI_TPM_LIMIT"):
        rate_config.tokens_per_minute = int(os.getenv("OPENAI_TPM_LIMIT"))
    if os.getenv("OPENAI_MAX_RETRIES"):
        rate_config.max_retries = int(os.getenv("OPENAI_MAX_RETRIES"))
    
    # Create a regular ChatOpenAI instance first
    base_llm = ChatOpenAI(
        model=model_name,
        temperature=kwargs.get('temperature', 0.1),
        max_tokens=kwargs.get('max_tokens', 4000)
    )
    
    # Add rate limiting capabilities
    rate_limiter = RateLimiter(rate_config)
    
    # Create wrapper methods - check what methods are available
    if hasattr(base_llm, 'invoke'):
        original_invoke = base_llm.invoke
        def rate_limited_invoke(*args, **kwargs):
            return _execute_with_retry(original_invoke, rate_limiter, rate_config, *args, **kwargs)
        base_llm.invoke = rate_limited_invoke
    
    if hasattr(base_llm, 'generate'):
        original_generate = base_llm.generate
        def rate_limited_generate(*args, **kwargs):
            return _execute_with_retry(original_generate, rate_limiter, rate_config, *args, **kwargs)
        base_llm.generate = rate_limited_generate
    
    if hasattr(base_llm, 'call'):
        original_call = base_llm.call
        def rate_limited_call(*args, **kwargs):
            return _execute_with_retry(original_call, rate_limiter, rate_config, *args, **kwargs)
        base_llm.call = rate_limited_call
    
    if hasattr(base_llm, 'predict'):
        original_predict = base_llm.predict
        def rate_limited_predict(*args, **kwargs):
            return _execute_with_retry(original_predict, rate_limiter, rate_config, *args, **kwargs)
        base_llm.predict = rate_limited_predict
    
    return base_llm


def create_ollama_llm(model_name: str = "llama3.2", base_url: str = "http://localhost:11434", **kwargs):
    """
    Factory function to create an Ollama LLM instance for local inference
    
    Args:
        model_name: Name of the Ollama model to use (e.g., "llama3.2", "ollama/llama3.2", "codellama", "mistral")
        base_url: Base URL for Ollama server
        **kwargs: Additional parameters for the LLM
    
    Returns:
        ChatOllama instance configured for Ollama
    """
    try:
        from langchain_ollama import ChatOllama
        
        # Remove ollama/ prefix if present since ChatOllama expects just the model name
        clean_model_name = model_name.replace("ollama/", "") if model_name.startswith("ollama/") else model_name
        
        logger.info(f"Creating Ollama LLM with ChatOllama model: {clean_model_name}")
        
        ollama_llm = ChatOllama(
            model=clean_model_name,
            base_url=base_url,
            temperature=kwargs.get('temperature', 0.1),
            num_predict=kwargs.get('max_tokens', 4000),
            repeat_penalty=kwargs.get('repeat_penalty', 1.1),
        )
        
        # Test the connection
        try:
            test_response = ollama_llm.invoke("Hello, are you working?")
            logger.info(f"Ollama LLM test successful: {type(test_response)}")
            
            # After successful creation, modify the model property for CrewAI/LiteLLM compatibility
            if not ollama_llm.model.startswith("ollama/"):
                ollama_llm.model = f"ollama/{ollama_llm.model}"
                logger.info(f"Modified model property for CrewAI compatibility: {ollama_llm.model}")
            
            return ollama_llm
        except Exception as test_error:
            logger.error(f"Ollama LLM test failed: {test_error}")
            raise test_error
            
    except ImportError:
        logger.error("langchain-ollama not installed. Install with: pip install langchain-ollama")
        raise ImportError("langchain-ollama package is required for Ollama support")
    except Exception as e:
        logger.error(f"Failed to create Ollama LLM: {e}")
        raise e


class MockLLM:
    """
    A mock LLM that properly implements the LangChain interface
    """
    def __init__(self):
        self.model_name = "mock-llm"
        self.temperature = 0.1
        self.max_tokens = 4000
        
    def invoke(self, input_text, **kwargs):
        """Mock invoke method that returns a realistic response"""
        # Return a mock response that looks like a real LangChain response
        class MockResponse:
            def __init__(self, content):
                self.content = content
                
            def __str__(self):
                return self.content
                
        return MockResponse("Mock analysis complete - Java mod structure identified with textures, models, and custom blocks.")
        
    def generate(self, messages, **kwargs):
        """Mock generate method"""
        class MockGeneration:
            def __init__(self, content):
                self.text = content
                
        class MockLLMResult:
            def __init__(self, generations):
                self.generations = [generations]
                
        return MockLLMResult([MockGeneration("Mock generation complete")])
        
    def predict(self, text, **kwargs):
        """Mock predict method for older LangChain interfaces"""
        return "Mock prediction complete"
        
    def call(self, inputs, **kwargs):
        """Mock call method for older LangChain interfaces"""
        return "Mock call complete"
        
    def __call__(self, *args, **kwargs):
        """Make the mock callable"""
        return self.invoke(*args, **kwargs)


def get_fallback_llm():
    """
    Get a fallback LLM for when OpenAI is unavailable
    """
    try:
        # Try using Ollama as the only fallback
        from langchain_ollama import ChatOllama
        
        # Get Ollama model from environment or use default
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        
        logger.info(f"Attempting to use Ollama as fallback with model: {ollama_model}")
        
        ollama_llm = ChatOllama(
            model=ollama_model,
            base_url=ollama_base_url,
            temperature=0.1,
            num_predict=4000,
            top_k=40,
            top_p=0.9,
            repeat_penalty=1.1,
        )
        
        # Test the connection
        test_response = ollama_llm.invoke("Hello")
        logger.info(f"Ollama fallback connection successful: {test_response}")
        
        return ollama_llm
        
    except Exception as e:
        logger.error(f"Failed to create fallback Ollama LLM: {e}")
        raise RuntimeError(
            f"No LLM available. Ollama fallback failed: {e}. "
            "Troubleshooting steps: "
            "1. Ensure the Ollama service is running. "
            "2. Verify the environment variables OLLAMA_MODEL and OLLAMA_BASE_URL are correctly set. "
            "3. Check network connectivity to the base URL. "
            "For more information, visit the Ollama documentation: https://ollama.ai/docs/setup."
        )