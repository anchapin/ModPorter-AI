"""
Error Handler with Retry Logic

Handles errors with exponential backoff and categorization.
"""

import logging
import asyncio
<<<<<<< HEAD
from typing import Optional, Callable, TypeVar
=======
from typing import Optional, Callable, Any, TypeVar
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
from functools import wraps
import time

logger = logging.getLogger(__name__)

<<<<<<< HEAD
T = TypeVar("T")
=======
T = TypeVar('T')
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))


class ConversionError(Exception):
    """Base exception for conversion errors."""
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable
        self.message = message


class AIEngineUnavailableError(ConversionError):
    """AI Engine is unavailable."""
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def __init__(self, message: str = "AI Engine unavailable"):
        super().__init__(message, retryable=True)


class ConversionTimeoutError(ConversionError):
    """Conversion timed out."""
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def __init__(self, message: str = "Conversion timed out"):
        super().__init__(message, retryable=True)


class InvalidInputError(ConversionError):
    """Invalid input provided."""
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def __init__(self, message: str):
        super().__init__(message, retryable=False)


class ModelUnavailableError(ConversionError):
    """Translation model unavailable."""
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def __init__(self, message: str = "Model unavailable"):
        super().__init__(message, retryable=True)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
<<<<<<< HEAD
    retryable_exceptions: tuple = (
        AIEngineUnavailableError,
        ConversionTimeoutError,
        ModelUnavailableError,
    ),
):
    """
    Decorator for retrying with exponential backoff.

=======
    retryable_exceptions: tuple = (AIEngineUnavailableError, ConversionTimeoutError, ModelUnavailableError),
):
    """
    Decorator for retrying with exponential backoff.
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        retryable_exceptions: Tuple of exceptions that trigger retry
    """
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
<<<<<<< HEAD

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)

                except retryable_exceptions as e:
                    last_exception = e

                    if attempt >= max_retries:
                        logger.error(f"Max retries exceeded for {func.__name__}: {e}")
                        raise

                    # Calculate delay with exponential backoff and jitter
                    delay = min(base_delay * (exponential_base**attempt), max_delay)
                    jitter = delay * 0.1 * (0.5 + asyncio.get_event_loop().time() % 1)
                    total_delay = delay + jitter

=======
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                    
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt >= max_retries:
                        logger.error(f"Max retries exceeded for {func.__name__}: {e}")
                        raise
                    
                    # Calculate delay with exponential backoff and jitter
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)
                    jitter = delay * 0.1 * (0.5 + asyncio.get_event_loop().time() % 1)
                    total_delay = delay + jitter
                    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {total_delay:.2f}s"
                    )
<<<<<<< HEAD

                    await asyncio.sleep(total_delay)

=======
                    
                    await asyncio.sleep(total_delay)
                    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
                except ConversionError as e:
                    # Non-retryable conversion error
                    logger.error(f"Non-retryable error in {func.__name__}: {e}")
                    raise
<<<<<<< HEAD

=======
                    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
                except Exception as e:
                    # Unexpected error - log and re-raise
                    logger.exception(f"Unexpected error in {func.__name__}: {e}")
                    raise ConversionError(f"Unexpected error: {e}", retryable=False)
<<<<<<< HEAD

            # Should not reach here, but just in case
            raise last_exception

        return wrapper

=======
            
            # Should not reach here, but just in case
            raise last_exception
        
        return wrapper
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    return decorator


def categorize_error(error: Exception) -> dict:
    """
    Categorize an error for user-friendly messaging.
<<<<<<< HEAD

    Args:
        error: Exception to categorize

=======
    
    Args:
        error: Exception to categorize
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    Returns:
        Error category dict with user message and technical details
    """
    if isinstance(error, InvalidInputError):
        return {
            "category": "invalid_input",
            "user_message": "The provided mod file has issues. Please check the file and try again.",
            "technical_details": error.message,
            "retryable": False,
        }
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    elif isinstance(error, (AIEngineUnavailableError, ModelUnavailableError)):
        return {
            "category": "service_unavailable",
            "user_message": "The conversion service is temporarily unavailable. Please try again in a few moments.",
            "technical_details": error.message,
            "retryable": True,
        }
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    elif isinstance(error, ConversionTimeoutError):
        return {
            "category": "timeout",
            "user_message": "The conversion took too long. Please try again with a smaller mod file.",
            "technical_details": error.message,
            "retryable": True,
        }
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    elif isinstance(error, ConversionError):
        return {
            "category": "conversion_error",
            "user_message": "An error occurred during conversion. Please try again.",
            "technical_details": error.message,
            "retryable": error.retryable,
        }
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    else:
        # Unknown error
        return {
            "category": "unknown",
            "user_message": "An unexpected error occurred. Our team has been notified.",
            "technical_details": str(error),
            "retryable": False,
        }


def get_user_friendly_error(error: Exception) -> str:
    """
    Get user-friendly error message.
<<<<<<< HEAD

    Args:
        error: Exception

=======
    
    Args:
        error: Exception
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    Returns:
        User-friendly message string
    """
    category = categorize_error(error)
    return category["user_message"]


class ErrorHandler:
    """Centralized error handler for conversion service."""
<<<<<<< HEAD

    def __init__(self):
        self._error_counts = {}  # error_type -> count
        self._last_error_time = {}  # error_type -> timestamp

    def record_error(self, error: Exception, job_id: Optional[str] = None):
        """Record an error for monitoring."""
        error_type = type(error).__name__

        if error_type not in self._error_counts:
            self._error_counts[error_type] = 0

        self._error_counts[error_type] += 1
        self._last_error_time[error_type] = time.time()

        logger.error(
            f"Error recorded: {error_type} - {error}",
            extra={"job_id": job_id} if job_id else {},
        )

=======
    
    def __init__(self):
        self._error_counts = {}  # error_type -> count
        self._last_error_time = {}  # error_type -> timestamp
    
    def record_error(self, error: Exception, job_id: Optional[str] = None):
        """Record an error for monitoring."""
        error_type = type(error).__name__
        
        if error_type not in self._error_counts:
            self._error_counts[error_type] = 0
        
        self._error_counts[error_type] += 1
        self._last_error_time[error_type] = time.time()
        
        logger.error(
            f"Error recorded: {error_type} - {error}",
            extra={"job_id": job_id} if job_id else {}
        )
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def get_error_stats(self) -> dict:
        """Get error statistics."""
        return {
            "error_counts": self._error_counts.copy(),
            "last_error_times": self._last_error_time.copy(),
            "total_errors": sum(self._error_counts.values()),
        }
<<<<<<< HEAD

    def should_alert(self, error_type: str, threshold: int = 10, window_seconds: int = 300) -> bool:
        """
        Check if we should alert on this error type.

=======
    
    def should_alert(self, error_type: str, threshold: int = 10, window_seconds: int = 300) -> bool:
        """
        Check if we should alert on this error type.
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        Args:
            error_type: Error type name
            threshold: Alert threshold
            window_seconds: Time window in seconds
<<<<<<< HEAD

=======
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        Returns:
            True if should alert
        """
        count = self._error_counts.get(error_type, 0)
        last_time = self._last_error_time.get(error_type, 0)
<<<<<<< HEAD

        # Check if we're in an error burst
        return bool(count >= threshold and time.time() - last_time < window_seconds)
=======
        
        # Check if we're in an error burst
        if count >= threshold and (time.time() - last_time) < window_seconds:
            return True
        
        return False
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))


# Singleton instance
_error_handler = None


def get_error_handler() -> ErrorHandler:
    """Get or create error handler singleton."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler
