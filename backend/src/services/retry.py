"""
Retry Logic with Exponential Backoff
Provides retry utilities for handling transient failures.

Issue: #455 - Comprehensive Error Handling (Phase 3)
"""

import asyncio
import functools
import logging
import time
from typing import Callable, Optional, Type, Tuple, Any
from datetime import datetime

from .metrics import record_conversion_job

logger = logging.getLogger(__name__)


# Error categories for retry logic
class RetryableError(Exception):
    """Base class for errors that should trigger a retry."""
    pass


class NonRetryableError(Exception):
    """Base class for errors that should NOT trigger a retry."""
    pass


# Specific error categories matching Issue #455
class ParseError(RetryableError):
    """Error during file parsing - may be transient."""
    pass


class AssetError(RetryableError):
    """Error with asset processing - may be transient."""
    pass


class LogicError(NonRetryableError):
    """Error in conversion logic - should not retry."""
    pass


class PackageError(RetryableError):
    """Error during packaging - may be transient."""
    pass


class ValidationError(NonRetryableError):
    """Error during validation - should not retry."""
    pass


class NetworkError(RetryableError):
    """Network-related error - should retry."""
    pass


class RateLimitError(RetryableError):
    """Rate limit exceeded - should retry with backoff."""
    pass


class TimeoutError(RetryableError):
    """Operation timeout - may succeed on retry."""
    pass


# Default retryable exceptions
DEFAULT_RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    RetryableError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
)

# Non-retryable exceptions
DEFAULT_NON_RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    NonRetryableError,
    ValueError,
    TypeError,
    KeyError,
)


def categorize_error(error: Exception) -> str:
    """
    Categorize an error based on its type.
    
    Returns one of: parse_error, asset_error, logic_error, 
                    package_error, validation_error, network_error,
                    rate_limit_error, timeout_error, unknown_error
    """
    error_type = type(error).__name__
    error_msg = str(error).lower()
    
    # Check specific error types
    if isinstance(error, ParseError):
        return "parse_error"
    if isinstance(error, AssetError):
        return "asset_error"
    if isinstance(error, LogicError):
        return "logic_error"
    if isinstance(error, PackageError):
        return "package_error"
    if isinstance(error, ValidationError):
        return "validation_error"
    if isinstance(error, NetworkError):
        return "network_error"
    if isinstance(error, RateLimitError):
        return "rate_limit_error"
    if isinstance(error, RetryableError):
        return "timeout_error"
    
    # Check error message patterns
    if "parse" in error_type.lower() or "parse" in error_msg:
        return "parse_error"
    if "asset" in error_type.lower() or "asset" in error_msg:
        return "asset_error"
    if "logic" in error_type.lower() or "convert" in error_msg:
        return "logic_error"
    if "package" in error_type.lower() or "packag" in error_msg:
        return "package_error"
    if "valid" in error_type.lower() or "valid" in error_msg:
        return "validation_error"
    if "network" in error_type.lower() or "connection" in error_msg:
        return "network_error"
    if "rate limit" in error_msg or "429" in error_msg:
        return "rate_limit_error"
    if "timeout" in error_type.lower() or "timeout" in error_msg:
        return "timeout_error"
    
    return "unknown_error"


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
        non_retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or DEFAULT_RETRYABLE_EXCEPTIONS
        self.non_retryable_exceptions = non_retryable_exceptions or DEFAULT_NON_RETRYABLE_EXCEPTIONS


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate delay with exponential backoff and optional jitter."""
    delay = config.base_delay * (config.exponential_base ** (attempt - 1))
    delay = min(delay, config.max_delay)
    
    if config.jitter:
        import random
        delay = delay * (0.5 + random.random() * 0.5)
    
    return delay


def is_retryable(error: Exception, config: RetryConfig) -> bool:
    """Determine if an error is retryable."""
    # Check non-retryable first
    for exc_type in config.non_retryable_exceptions:
        if isinstance(error, exc_type):
            return False
    
    # Check retryable
    for exc_type in config.retryable_exceptions:
        if isinstance(error, exc_type):
            return True
    
    # Default to retryable for unknown errors
    return True


async def retry_async(
    func: Callable,
    *args,
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
    job_id: Optional[str] = None,
    **kwargs
) -> Any:
    """
    Async retry decorator with exponential backoff.
    
    Args:
        func: Async function to retry
        *args: Positional arguments for func
        config: Retry configuration
        on_retry: Callback function called on each retry (error, attempt)
        job_id: Optional job ID for metrics tracking
        **kwargs: Keyword arguments for func
    
    Returns:
        Result of func
    
    Raises:
        The last exception if all retries are exhausted
    """
    if config is None:
        config = RetryConfig()
    
    last_error = None
    
    for attempt in range(1, config.max_attempts + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_error = e
            
            # Determine if we should retry
            if not is_retryable(e, config):
                logger.warning(
                    f"Non-retryable error in {func.__name__}: {type(e).__name__}: {e}"
                )
                raise
            
            # Check if we have more attempts
            if attempt >= config.max_attempts:
                logger.error(
                    f"Max retry attempts ({config.max_attempts}) reached for {func.__name__}"
                )
                break
            
            # Calculate delay
            delay = calculate_delay(attempt, config)
            
            # Log retry attempt
            error_category = categorize_error(e)
            logger.warning(
                f"Retry {attempt}/{config.max_attempts} for {func.__name__} "
                f"after {delay:.2f}s - Error: {error_category}: {e}"
            )
            
            # Call on_retry callback
            if on_retry:
                on_retry(e, attempt)
            
            # Wait before retry
            await asyncio.sleep(delay)
    
    # All retries exhausted
    if last_error:
        raise last_error


def retry_sync(
    func: Callable,
    *args,
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
    **kwargs
) -> Any:
    """
    Synchronous retry decorator with exponential backoff.
    
    Args:
        func: Function to retry
        *args: Positional arguments for func
        config: Retry configuration
        on_retry: Callback function called on each retry (error, attempt)
        **kwargs: Keyword arguments for func
    
    Returns:
        Result of func
    
    Raises:
        The last exception if all retries are exhausted
    """
    if config is None:
        config = RetryConfig()
    
    last_error = None
    
    for attempt in range(1, config.max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            
            # Determine if we should retry
            if not is_retryable(e, config):
                logger.warning(
                    f"Non-retryable error in {func.__name__}: {type(e).__name__}: {e}"
                )
                raise
            
            # Check if we have more attempts
            if attempt >= config.max_attempts:
                logger.error(
                    f"Max retry attempts ({config.max_attempts}) reached for {func.__name__}"
                )
                break
            
            # Calculate delay
            delay = calculate_delay(attempt, config)
            
            # Log retry attempt
            error_category = categorize_error(e)
            logger.warning(
                f"Retry {attempt}/{config.max_attempts} for {func.__name__} "
                f"after {delay:.2f}s - Error: {error_category}: {e}"
            )
            
            # Call on_retry callback
            if on_retry:
                on_retry(e, attempt)
            
            # Wait before retry
            time.sleep(delay)
    
    # All retries exhausted
    if last_error:
        raise last_error


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator for adding retry logic to async functions.
    
    Usage:
        @with_retry(RetryConfig(max_attempts=5, base_delay=2.0))
        async def my_function():
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_async(func, *args, config=config, **kwargs)
        return wrapper
    return decorator


def with_retry_sync(config: Optional[RetryConfig] = None):
    """
    Decorator for adding retry logic to sync functions.
    
    Usage:
        @with_retry_sync(RetryConfig(max_attempts=5, base_delay=2.0))
        def my_function():
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return retry_sync(func, *args, config=config, **kwargs)
        return wrapper
    return decorator
