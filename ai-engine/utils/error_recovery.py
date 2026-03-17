"""
Error Recovery System for automatic failure handling

Features:
- Retry with exponential backoff
- Circuit breaker pattern
- Recovery strategies for common failures
- Graceful degradation
"""

import time
import logging
import random
from typing import Callable, Any, Optional, Dict, List, Type
from functools import wraps
from dataclasses import dataclass, field
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Severity levels for errors."""
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    LOW = "low"  # Can retry immediately
    MEDIUM = "medium"  # Retry with backoff
    HIGH = "high"  # May need intervention
    CRITICAL = "critical"  # Stop execution


@dataclass
class RecoveryStrategy:
    """Strategy for recovering from errors."""
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    name: str
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True  # Add randomness to avoid thundering herd
    retryable_exceptions: List[Type[Exception]] = field(default_factory=list)

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt with exponential backoff."""
<<<<<<< HEAD
        delay = min(self.base_delay * (self.backoff_factor**attempt), self.max_delay)
=======
        delay = min(self.base_delay * (self.backoff_factor ** attempt), self.max_delay)
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        if self.jitter:
            # Add up to 10% jitter
            delay = delay * (0.9 + 0.2 * random.random())
        return delay


# Pre-defined recovery strategies
RETRY_IMMEDIATELY = RecoveryStrategy(
    name="retry_immediately",
    max_retries=5,
    base_delay=0.1,
    max_delay=1.0,
    retryable_exceptions=[ConnectionError, TimeoutError],
)

STANDARD_RETRY = RecoveryStrategy(
    name="standard_retry",
    max_retries=3,
    base_delay=1.0,
    max_delay=30.0,
    retryable_exceptions=[Exception],
)

CONSERVATIVE_RETRY = RecoveryStrategy(
    name="conservative_retry",
    max_retries=2,
    base_delay=5.0,
    max_delay=60.0,
    retryable_exceptions=[ConnectionError],
)


class CircuitState(Enum):
    """Circuit breaker states."""
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, stop calls
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreaker:
    """
    Circuit breaker pattern for preventing cascade failures.
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    When too many failures occur, the circuit opens and prevents
    further calls for a cooldown period. After cooldown, it allows
    one test call (half-open state). If successful, circuit closes.
    """

    def __init__(
        self,
        name: str = "default",
        fail_max: int = 5,
        reset_timeout: float = 60.0,
        half_open_max_calls: int = 1,
    ):
        """
        Initialize circuit breaker.
<<<<<<< HEAD

=======
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        Args:
            name: Name for logging
            fail_max: Number of failures before opening circuit
            reset_timeout: Seconds to wait before trying again
            half_open_max_calls: Calls allowed in half-open state
        """
        self.name = name
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self.half_open_max_calls = half_open_max_calls
<<<<<<< HEAD

=======
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = threading.Lock()
<<<<<<< HEAD

        logger.info(
            f"CircuitBreaker '{name}' initialized: fail_max={fail_max}, reset_timeout={reset_timeout}s"
        )
=======
        
        logger.info(f"CircuitBreaker '{name}' initialized: fail_max={fail_max}, reset_timeout={reset_timeout}s")
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                # Check if timeout has passed
                if self._last_failure_time:
                    elapsed = time.time() - self._last_failure_time
                    if elapsed >= self.reset_timeout:
<<<<<<< HEAD
                        logger.info(
                            f"CircuitBreaker '{self.name}': timeout elapsed, transitioning to HALF_OPEN"
                        )
=======
                        logger.info(f"CircuitBreaker '{self.name}': timeout elapsed, transitioning to HALF_OPEN")
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
                        self._state = CircuitState.HALF_OPEN
                        self._half_open_calls = 0
            return self._state

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.
<<<<<<< HEAD

=======
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
<<<<<<< HEAD

        Returns:
            Function result

=======
            
        Returns:
            Function result
            
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        Raises:
            CircuitBreakerError: If circuit is open
        """
        with self._lock:
            current_state = self.state
<<<<<<< HEAD

            if current_state == CircuitState.OPEN:
                logger.warning(f"CircuitBreaker '{self.name}': OPEN - rejecting call")
                raise CircuitBreakerOpen(f"Circuit breaker '{self.name}' is open")

            if current_state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    logger.warning(f"CircuitBreaker '{self.name}': HALF_OPEN - max calls reached")
                    raise CircuitBreakerOpen(
                        f"Circuit breaker '{self.name}' half-open call limit reached"
                    )
=======
            
            if current_state == CircuitState.OPEN:
                logger.warning(f"CircuitBreaker '{self.name}': OPEN - rejecting call")
                raise CircuitBreakerOpen(f"Circuit breaker '{self.name}' is open")
            
            if current_state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    logger.warning(f"CircuitBreaker '{self.name}': HALF_OPEN - max calls reached")
                    raise CircuitBreakerOpen(f"Circuit breaker '{self.name}' half-open call limit reached")
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
                self._half_open_calls += 1
                logger.info(f"CircuitBreaker '{self.name}': HALF_OPEN - allowing test call")

        # Execute the function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
<<<<<<< HEAD
        except Exception:
=======
        except Exception as e:
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                logger.info(f"CircuitBreaker '{self.name}': success in HALF_OPEN, closing circuit")
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
            else:
                self._success_count += 1
                # Reset failure count on success
                self._failure_count = 0

    def _on_failure(self):
        """Handle failed call."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
<<<<<<< HEAD

            if self._state == CircuitState.HALF_OPEN:
                logger.warning(
                    f"CircuitBreaker '{self.name}': failure in HALF_OPEN, opening circuit"
                )
                self._state = CircuitState.OPEN
            elif self._failure_count >= self.fail_max:
                logger.warning(
                    f"CircuitBreaker '{self.name}': failure limit reached, opening circuit"
                )
=======
            
            if self._state == CircuitState.HALF_OPEN:
                logger.warning(f"CircuitBreaker '{self.name}': failure in HALF_OPEN, opening circuit")
                self._state = CircuitState.OPEN
            elif self._failure_count >= self.fail_max:
                logger.warning(f"CircuitBreaker '{self.name}': failure limit reached, opening circuit")
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
                self._state = CircuitState.OPEN

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "last_failure_time": self._last_failure_time,
            }


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open."""
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    pass


class RecoveryError(Exception):
    """Exception for recovery failures."""
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    pass


def with_retry(strategy: RecoveryStrategy = STANDARD_RETRY):
    """
    Decorator for adding retry logic to functions.
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    Usage:
        @with_retry(STANDARD_RETRY)
        def flaky_function():
            ...
<<<<<<< HEAD

    Args:
        strategy: Recovery strategy to use
    """

=======
            
    Args:
        strategy: Recovery strategy to use
    """
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
<<<<<<< HEAD

            for attempt in range(strategy.max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except Exception as e:
                    last_exception = e

                    # Check if exception is retryable
                    is_retryable = any(
                        isinstance(e, exc_type) for exc_type in strategy.retryable_exceptions
                    )

                    if not is_retryable:
                        logger.error(f"Non-retryable error in {func.__name__}: {e}")
                        raise

                    # Check if we should retry
                    if attempt >= strategy.max_retries:
                        logger.error(
                            f"Max retries ({strategy.max_retries}) exceeded for {func.__name__}"
                        )
                        raise RecoveryError(f"Failed after {strategy.max_retries} retries") from e

=======
            
            for attempt in range(strategy.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    last_exception = e
                    
                    # Check if exception is retryable
                    is_retryable = any(
                        isinstance(e, exc_type) 
                        for exc_type in strategy.retryable_exceptions
                    )
                    
                    if not is_retryable:
                        logger.error(f"Non-retryable error in {func.__name__}: {e}")
                        raise
                    
                    # Check if we should retry
                    if attempt >= strategy.max_retries:
                        logger.error(f"Max retries ({strategy.max_retries}) exceeded for {func.__name__}")
                        raise RecoveryError(f"Failed after {strategy.max_retries} retries") from e
                    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
                    # Calculate delay and wait
                    delay = strategy.get_delay(attempt)
                    logger.warning(
                        f"Retryable error in {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s (attempt {attempt + 1}/{strategy.max_retries})"
                    )
                    time.sleep(delay)
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


def with_circuit_breaker(
    name: str = None,
    fail_max: int = 5,
    reset_timeout: float = 60.0,
):
    """
    Decorator for adding circuit breaker to functions.
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    Usage:
        @with_circuit_breaker("my_function", fail_max=3)
        def external_api_call():
            ...
<<<<<<< HEAD

=======
            
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    Args:
        name: Circuit breaker name (defaults to function name)
        fail_max: Failures before opening circuit
        reset_timeout: Seconds before trying again
    """
<<<<<<< HEAD

    def decorator(func: Callable) -> Callable:
        cb_name = name or func.__name__
        breaker = CircuitBreaker(name=cb_name, fail_max=fail_max, reset_timeout=reset_timeout)

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            return breaker.call(func, *args, **kwargs)

        # Expose circuit breaker for monitoring
        wrapper.circuit_breaker = breaker

        return wrapper

=======
    def decorator(func: Callable) -> Callable:
        cb_name = name or func.__name__
        breaker = CircuitBreaker(name=cb_name, fail_max=fail_max, reset_timeout=reset_timeout)
        
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            return breaker.call(func, *args, **kwargs)
        
        # Expose circuit breaker for monitoring
        wrapper.circuit_breaker = breaker
        
        return wrapper
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    return decorator


class ErrorRecoverySystem:
    """
    Centralized error recovery system for the conversion pipeline.
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    Manages:
    - Recovery strategies for different error types
    - Circuit breakers for external services
    - Error classification and handling
    """

    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.recovery_strategies: Dict[str, RecoveryStrategy] = {
            "network": RETRY_IMMEDIATELY,
            "llm_api": STANDARD_RETRY,
            "file_io": CONSERVATIVE_RETRY,
        }
        self._lock = threading.Lock()
<<<<<<< HEAD

=======
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        logger.info("ErrorRecoverySystem initialized")

    def register_circuit_breaker(
        self,
        name: str,
        fail_max: int = 5,
        reset_timeout: float = 60.0,
    ) -> CircuitBreaker:
        """Register a circuit breaker."""
        with self._lock:
            cb = CircuitBreaker(name=name, fail_max=fail_max, reset_timeout=reset_timeout)
            self.circuit_breakers[name] = cb
            logger.info(f"Registered circuit breaker: {name}")
            return cb

    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self.circuit_breakers.get(name)

    def execute_with_recovery(
        self,
        operation: str,
        func: Callable,
        *args,
        **kwargs,
    ) -> Any:
        """
        Execute function with error recovery.
<<<<<<< HEAD

=======
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        Args:
            operation: Operation name for logging
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
<<<<<<< HEAD

=======
            
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        Returns:
            Function result
        """
        strategy = self.recovery_strategies.get("llm_api", STANDARD_RETRY)
        last_exception = None
<<<<<<< HEAD

=======
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        for attempt in range(strategy.max_retries + 1):
            try:
                # Check circuit breakers
                for cb_name, cb in self.circuit_breakers.items():
                    if cb.state == CircuitState.OPEN:
                        logger.warning(f"Circuit breaker '{cb_name}' is OPEN")
                        # Could implement fallback behavior here
<<<<<<< HEAD

                return func(*args, **kwargs)

            except Exception as e:
                last_exception = e
                logger.error(f"Error in {operation} (attempt {attempt + 1}): {e}")

                if attempt >= strategy.max_retries:
                    logger.error(f"{operation} failed after {strategy.max_retries} retries")
                    break

                delay = strategy.get_delay(attempt)
                logger.info(f"Retrying {operation} in {delay:.2f}s...")
                time.sleep(delay)

=======
                
                return func(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                logger.error(f"Error in {operation} (attempt {attempt + 1}): {e}")
                
                if attempt >= strategy.max_retries:
                    logger.error(f"{operation} failed after {strategy.max_retries} retries")
                    break
                
                delay = strategy.get_delay(attempt)
                logger.info(f"Retrying {operation} in {delay:.2f}s...")
                time.sleep(delay)
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        raise RecoveryError(f"{operation} failed: {last_exception}") from last_exception

    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics from all circuit breakers."""
        stats = {
            "circuit_breakers": {},
            "recovery_strategies": {
                name: {
                    "max_retries": strategy.max_retries,
                    "base_delay": strategy.base_delay,
                }
                for name, strategy in self.recovery_strategies.items()
            },
        }
<<<<<<< HEAD

        for name, cb in self.circuit_breakers.items():
            stats["circuit_breakers"][name] = cb.get_stats()

=======
        
        for name, cb in self.circuit_breakers.items():
            stats["circuit_breakers"][name] = cb.get_stats()
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        return stats


# Global recovery system instance
_recovery_system: Optional[ErrorRecoverySystem] = None
_system_lock = threading.Lock()


def get_recovery_system() -> ErrorRecoverySystem:
    """Get or create global recovery system."""
    global _recovery_system
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    with _system_lock:
        if _recovery_system is None:
            _recovery_system = ErrorRecoverySystem()
        return _recovery_system
