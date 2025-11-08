"""
Rate limiting utility for OpenAI API calls and LLM interactions
"""

import time
import logging
from typing import Any, Callable, Optional
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


@dataclass
class ZAIConfig:
    """Configuration for Z.AI LLM backend"""
    api_key: str = ""
    model: str = "glm-4-plus"
    base_url: str = "https://api.z.ai/v1"
    max_retries: int = 3
    timeout: int = 300
    temperature: float = 0.1
    max_tokens: int = 4000


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


class RateLimitedChatOpenAI:
    """
    A proper wrapper class for ChatOpenAI that implements rate limiting
    """
    def __init__(self, model_name: str = "gpt-4", **kwargs):
        self.model_name = model_name
        self.temperature = kwargs.get('temperature', 0.1)
        self.max_tokens = kwargs.get('max_tokens', 4000)
        
        # Default rate limiting configuration
        self.rate_config = RateLimitConfig(
            requests_per_minute=50,  # Conservative limit
            tokens_per_minute=40000,  # Conservative token limit
            max_retries=3,
            base_delay=1.0,
            max_delay=60.0,
            backoff_factor=2.0
        )
        
        # Override with environment variables if available
        if os.getenv("OPENAI_RPM_LIMIT"):
            self.rate_config.requests_per_minute = int(os.getenv("OPENAI_RPM_LIMIT"))
        if os.getenv("OPENAI_TPM_LIMIT"):
            self.rate_config.tokens_per_minute = int(os.getenv("OPENAI_TPM_LIMIT"))
        if os.getenv("OPENAI_MAX_RETRIES"):
            self.rate_config.max_retries = int(os.getenv("OPENAI_MAX_RETRIES"))
        
        # Get API key from environment or kwargs
        api_key = kwargs.get('openai_api_key') or os.getenv('OPENAI_API_KEY')
        
        # Create the underlying ChatOpenAI instance
        try:
            self._base_llm = ChatOpenAI(
                model=model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                openai_api_key=api_key
            )
        except Exception as e:
            # No fallback - if OpenAI fails, raise the error
            logger.error(f"OpenAI LLM initialization failed: {e}")
            raise
        
        self.rate_limiter = RateLimiter(self.rate_config)
    
    def invoke(self, input_data, **kwargs):
        """Implement the invoke method with rate limiting"""
        return _execute_with_retry(
            self._base_llm.invoke, 
            self.rate_limiter, 
            self.rate_config, 
            input_data, 
            **kwargs
        )
    
    def generate(self, messages, **kwargs):
        """Implement the generate method with rate limiting"""
        return _execute_with_retry(
            self._base_llm.generate,
            self.rate_limiter,
            self.rate_config,
            messages,
            **kwargs
        )
    
    def predict(self, text, **kwargs):
        """Implement the predict method with rate limiting"""
        return _execute_with_retry(
            self._base_llm.predict,
            self.rate_limiter,
            self.rate_config,
            text,
            **kwargs
        )
    
    def __call__(self, *args, **kwargs):
        """Make the instance callable"""
        return self.invoke(*args, **kwargs)
    
    def __getattr__(self, name):
        """Delegate any other attributes to the underlying LLM"""
        return getattr(self._base_llm, name)


def create_rate_limited_llm(model_name: str = "gpt-4", **kwargs):
    """
    Factory function to create a rate-limited LLM instance
    """
    return RateLimitedChatOpenAI(model_name=model_name, **kwargs)


def create_ollama_llm(model_name: str = "llama3.2", base_url: str = None, **kwargs):
    """
    Factory function to create an Ollama LLM instance for local inference
    
    Args:
        model_name: Name of the Ollama model to use (e.g., "llama3.2", "ollama/llama3.2", "codellama", "mistral")
        base_url: Base URL for Ollama server (auto-detected if None)
        **kwargs: Additional parameters for the LLM
    
    Returns:
        LiteLLM-compatible instance for CrewAI
    """
    try:
        # Use LiteLLM for CrewAI compatibility
        import litellm
        
        # Auto-detect base URL if not provided
        if base_url is None:
            base_url = "http://ollama:11434" if os.getenv("DOCKER_ENVIRONMENT") else "http://localhost:11434"
        
        # Configure LiteLLM for Ollama
        litellm.set_verbose = False
        
        # Remove ollama/ prefix if present since we'll add it for LiteLLM
        clean_model_name = model_name.replace("ollama/", "") if model_name.startswith("ollama/") else model_name
        
        logger.info(f"Creating Ollama LLM with LiteLLM model: ollama/{clean_model_name}")
        logger.info(f"Using Ollama base URL: {base_url}")
        
        # Create LiteLLM-compatible wrapper for Ollama
        class LiteLLMOllamaWrapper:
            def __init__(self, model_name, base_url, **kwargs):
                self.model = f"ollama/{model_name}"
                self.base_url = base_url
                self.temperature = kwargs.get('temperature', 0.1)
                self.max_tokens = kwargs.get('max_tokens', 1024)
                self.request_timeout = kwargs.get('request_timeout', 300)
                
                # Set LiteLLM environment variables
                os.environ["OLLAMA_API_BASE"] = base_url
                
            def invoke(self, messages, **kwargs):
                """LangChain-compatible invoke method"""
                try:
                    # Convert messages to LiteLLM format
                    if isinstance(messages, str):
                        messages = [{"role": "user", "content": messages}]
                    elif hasattr(messages, 'content'):
                        messages = [{"role": "user", "content": messages.content}]
                    elif isinstance(messages, list) and len(messages) > 0:
                        if hasattr(messages[0], 'content'):
                            messages = [{"role": msg.type if hasattr(msg, 'type') else "user", 
                                       "content": msg.content} for msg in messages]
                    
                    # Make LiteLLM call
                    response = litellm.completion(
                        model=self.model,
                        messages=messages,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                        timeout=self.request_timeout,
                        stream=False
                    )
                    
                    # Create LangChain-compatible response
                    from langchain_core.messages import AIMessage
                    return AIMessage(
                        content=response.choices[0].message.content,
                        response_metadata={
                            'model': self.model,
                            'finish_reason': response.choices[0].finish_reason,
                            'usage': response.usage.dict() if response.usage else {}
                        }
                    )
                    
                except Exception as e:
                    logger.error(f"LiteLLM Ollama call failed: {e}")
                    raise e
                    
            def generate(self, messages, **kwargs):
                """LangChain-compatible generate method"""
                return self.invoke(messages, **kwargs)
                
            def predict(self, text, **kwargs):
                """LangChain-compatible predict method"""
                return self.invoke(text, **kwargs)
                
            def __call__(self, *args, **kwargs):
                return self.invoke(*args, **kwargs)
                
            def enable_crew_mode(self):
                """Enable CrewAI compatibility mode"""
                logger.info(f"CrewAI mode enabled - model: {self.model}")
                
            def disable_crew_mode(self):
                """Disable CrewAI compatibility mode"""
                logger.info(f"CrewAI mode disabled - model: {self.model}")
        
        wrapper = LiteLLMOllamaWrapper(
            model_name=clean_model_name,
            base_url=base_url,
            **kwargs
        )
        
        logger.info("LiteLLM Ollama wrapper created successfully")
        return wrapper
            
    except ImportError:
        logger.error("litellm not installed. Install with: pip install litellm")
        raise ImportError("litellm package is required for Ollama support with CrewAI")
    except Exception as e:
        logger.error(f"Failed to create LiteLLM Ollama wrapper: {e}")
        raise e




class RateLimitedZAI:
    """
    A rate-limited wrapper for Z.AI LLM backend
    """
    def __init__(self, config: ZAIConfig = None):
        self.config = config or ZAIConfig()
        
        # Load configuration from environment variables
        if os.getenv("Z_AI_API_KEY"):
            self.config.api_key = os.getenv("Z_AI_API_KEY")
        if os.getenv("Z_AI_MODEL"):
            self.config.model = os.getenv("Z_AI_MODEL")
        if os.getenv("Z_AI_BASE_URL"):
            self.config.base_url = os.getenv("Z_AI_BASE_URL")
        if os.getenv("Z_AI_MAX_RETRIES"):
            self.config.max_retries = int(os.getenv("Z_AI_MAX_RETRIES"))
        if os.getenv("Z_AI_TIMEOUT"):
            self.config.timeout = int(os.getenv("Z_AI_TIMEOUT"))
        if os.getenv("Z_AI_TEMPERATURE"):
            self.config.temperature = float(os.getenv("Z_AI_TEMPERATURE"))
        if os.getenv("Z_AI_MAX_TOKENS"):
            self.config.max_tokens = int(os.getenv("Z_AI_MAX_TOKENS"))
        
        if not self.config.api_key:
            raise ValueError("Z.AI API key is required. Set Z_AI_API_KEY environment variable.")
        
        # Initialize rate limiter
        self.rate_config = RateLimitConfig(
            requests_per_minute=50,  # Conservative limit for Z.AI
            tokens_per_minute=40000,
            max_retries=self.config.max_retries,
            base_delay=1.0,
            max_delay=60.0,
            backoff_factor=2.0
        )
        
        self.rate_limiter = RateLimiter(self.rate_config)
        
        # Import OpenAI client for Z.AI compatibility (Z.AI uses OpenAI-compatible API)
        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout
            )
        except ImportError:
            raise ImportError("openai package is required for Z.AI support")
        
        logger.info(f"Z.AI LLM initialized with model: {self.config.model}")
    
    def invoke(self, input_data, **kwargs):
        """Invoke the Z.AI model with rate limiting"""
        return self._execute_with_rate_limit(self._invoke_internal, input_data, **kwargs)
    
    def generate(self, messages, **kwargs):
        """Generate response using Z.AI model with rate limiting"""
        return self._execute_with_rate_limit(self._generate_internal, messages, **kwargs)
    
    def predict(self, text, **kwargs):
        """Predict using Z.AI model with rate limiting"""
        return self._execute_with_rate_limit(self._predict_internal, text, **kwargs)
    
    def _execute_with_rate_limit(self, func, *args, **kwargs):
        """Execute function with rate limiting and retry logic"""
        return _execute_with_retry(func, self.rate_limiter, self.rate_config, *args, **kwargs)
    
    def _invoke_internal(self, input_data, **kwargs):
        """Internal invoke implementation"""
        # Convert input_data to messages format
        messages = self._convert_to_messages(input_data)
        
        response = self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=kwargs.get('temperature', self.config.temperature),
            max_tokens=kwargs.get('max_tokens', self.config.max_tokens),
            **{k: v for k, v in kwargs.items() if k not in ['temperature', 'max_tokens']}
        )
        
        # Create LangChain-compatible response
        from langchain_core.messages import AIMessage
        return AIMessage(
            content=response.choices[0].message.content,
            response_metadata={
                'model': self.config.model,
                'finish_reason': response.choices[0].finish_reason,
                'usage': response.usage.model_dump() if response.usage else {}
            }
        )
    
    def _generate_internal(self, messages, **kwargs):
        """Internal generate implementation"""
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        elif hasattr(messages, 'content'):
            messages = [{"role": "user", "content": messages.content}]
        elif isinstance(messages, list) and len(messages) > 0:
            if hasattr(messages[0], 'content'):
                messages = [{"role": msg.type if hasattr(msg, 'type') else "user", 
                           "content": msg.content} for msg in messages]
        
        response = self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=kwargs.get('temperature', self.config.temperature),
            max_tokens=kwargs.get('max_tokens', self.config.max_tokens),
            **{k: v for k, v in kwargs.items() if k not in ['temperature', 'max_tokens']}
        )
        
        from langchain_core.messages import AIMessage
        return AIMessage(
            content=response.choices[0].message.content,
            response_metadata={
                'model': self.config.model,
                'finish_reason': response.choices[0].finish_reason,
                'usage': response.usage.model_dump() if response.usage else {}
            }
        )
    
    def _predict_internal(self, text, **kwargs):
        """Internal predict implementation"""
        messages = [{"role": "user", "content": text}]
        response = self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=kwargs.get('temperature', self.config.temperature),
            max_tokens=kwargs.get('max_tokens', self.config.max_tokens),
            **{k: v for k, v in kwargs.items() if k not in ['temperature', 'max_tokens']}
        )
        
        return response.choices[0].message.content
    
    def _convert_to_messages(self, input_data):
        """Convert various input formats to messages list"""
        if isinstance(input_data, str):
            return [{"role": "user", "content": input_data}]
        elif hasattr(input_data, 'content'):
            return [{"role": "user", "content": input_data.content}]
        elif isinstance(input_data, list) and len(input_data) > 0:
            if hasattr(input_data[0], 'content'):
                return [{"role": msg.type if hasattr(msg, 'type') else "user", 
                        "content": msg.content} for msg in input_data]
        return [{"role": "user", "content": str(input_data)}]
    
    def __call__(self, *args, **kwargs):
        """Make the instance callable"""
        return self.invoke(*args, **kwargs)
    
    def enable_crew_mode(self):
        """Enable CrewAI compatibility mode"""
        logger.info(f"CrewAI mode enabled for Z.AI - model: {self.config.model}")
        
    def disable_crew_mode(self):
        """Disable CrewAI compatibility mode"""
        logger.info(f"CrewAI mode disabled for Z.AI - model: {self.config.model}")


def create_z_ai_llm(config: ZAIConfig = None):
    """
    Factory function to create a rate-limited Z.AI LLM instance
    
    Args:
        config: ZAIConfig instance. If None, loads from environment variables.
    
    Returns:
        RateLimitedZAI instance
    """
    return RateLimitedZAI(config)


def get_llm_backend():
    """
    Get the best available LLM backend based on configuration and availability
    Priority order: Z.AI > Ollama > OpenAI
    
    Returns:
        LLM instance for use with CrewAI
    """
    # Check if Z.AI is enabled and configured
    if os.getenv("USE_Z_AI", "false").lower() == "true":
        try:
            logger.info("Attempting to initialize Z.AI LLM backend...")
            z_ai_llm = create_z_ai_llm()
            logger.info("Z.AI LLM backend initialized successfully")
            return z_ai_llm
        except Exception as e:
            logger.warning(f"Failed to initialize Z.AI backend: {e}")
    
    # Check if Ollama is enabled
    if os.getenv("USE_OLLAMA", "true").lower() == "true":
        try:
            logger.info("Attempting to initialize Ollama LLM backend...")
            ollama_llm = create_ollama_llm()
            logger.info("Ollama LLM backend initialized successfully")
            return ollama_llm
        except Exception as e:
            logger.warning(f"Failed to initialize Ollama backend: {e}")
    
    # Fallback to OpenAI if available
    try:
        logger.info("Attempting to initialize OpenAI LLM backend...")
        openai_llm = create_rate_limited_llm()
        logger.info("OpenAI LLM backend initialized successfully")
        return openai_llm
    except Exception as e:
        logger.warning(f"Failed to initialize OpenAI backend: {e}")
    
    # If all backends fail, raise an error
    raise RuntimeError(
        "No LLM backend available. Please configure one of the following:\n"
        "- Z.AI: Set USE_Z_AI=true and Z_AI_API_KEY environment variable\n"
        "- Ollama: Set USE_OLLAMA=true and ensure Ollama service is running\n"
        "- OpenAI: Set OPENAI_API_KEY environment variable"
    )


def get_fallback_llm():
    """
    Get a fallback LLM for when OpenAI is unavailable - uses only Ollama
    """
    try:
        # Use Ollama as the only fallback
        from langchain_ollama import ChatOllama
        
        # Get Ollama model from environment or use default
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
        # Auto-detect base URL based on environment
        default_base_url = "http://ollama:11434" if os.getenv("DOCKER_ENVIRONMENT") else "http://localhost:11434"
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", default_base_url)
        
        logger.info(f"Attempting to use Ollama as fallback with model: {ollama_model}")
        logger.info(f"Using Ollama base URL: {ollama_base_url}")
        
        ollama_llm = ChatOllama(
            model=ollama_model,
            base_url=ollama_base_url,
            temperature=0.1,
            num_predict=1024,  # Reduced for faster responses
            top_k=40,
            top_p=0.9,
            repeat_penalty=1.1,
            request_timeout=300,  # 5 minute timeout
            # Performance optimizations
            num_ctx=4096,
            num_batch=512,
            num_thread=8,
            streaming=False,
        )
        
        logger.info("Ollama fallback LLM created successfully")
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
