"""
Timeout Manager for AI Conversion Engine
Provides centralized timeout management for LLM calls, agent tasks, and pipeline stages
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar, Union
import yaml

logger = logging.getLogger(__name__)

T = TypeVar('T')


class TimeoutExceeded(Exception):
    """Exception raised when a timeout is exceeded."""
    
    def __init__(
        self,
        message: str,
        operation: str,
        timeout_seconds: float,
        elapsed_seconds: float,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.operation = operation
        self.timeout_seconds = timeout_seconds
        self.elapsed_seconds = elapsed_seconds
        self.context = context or {}
        self.timestamp = datetime.utcnow()
    
    def __str__(self) -> str:
        return (
            f"TimeoutExceeded: {self.operation} timed out after "
            f"{self.elapsed_seconds:.2f}s (limit: {self.timeout_seconds}s)"
        )


class TaskTimeout(Exception):
    """Exception for agent task timeout with graceful termination support."""
    
    def __init__(
        self,
        message: str,
        task_name: str,
        deadline: datetime,
        progress: Optional[float] = None,
        partial_result: Optional[Any] = None
    ):
        super().__init__(message)
        self.task_name = task_name
        self.deadline = deadline
        self.progress = progress
        self.partial_result = partial_result
        self.timestamp = datetime.utcnow()


@dataclass
class TimeoutConfig:
    """Configuration for all timeout settings."""
    
    # LLM timeouts by provider and operation
    llm_timeout: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    # Agent task timeouts by agent type
    agent_timeout: Dict[str, int] = field(default_factory=dict)
    
    # Pipeline stage timeouts
    pipeline_timeout: Dict[str, int] = field(default_factory=dict)
    
    # General timeout settings
    timeouts: Dict[str, Any] = field(default_factory=dict)
    
    # Warning threshold (0.0 - 1.0)
    warning_threshold: float = 0.8
    
    @classmethod
    def from_yaml(cls, config_path: Union[str, Path]) -> "TimeoutConfig":
        """Load timeout configuration from YAML file."""
        config_path = Path(config_path)
        
        if not config_path.exists():
            logger.warning(f"Timeout config not found at {config_path}, using defaults")
            return cls._default()
        
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f) or {}
        
        return cls(
            llm_timeout=data.get('llm_timeout', {}),
            agent_timeout=data.get('agent_timeout', {}),
            pipeline_timeout=data.get('pipeline_timeout', {}),
            timeouts=data.get('timeouts', {}),
            warning_threshold=data.get('agent_timeout', {}).get('warning_threshold', 0.8)
        )
    
    @classmethod
    def _default(cls) -> "TimeoutConfig":
        """Create default timeout configuration."""
        return cls(
            llm_timeout={
                'openai': {'translate': 120, 'analyze': 60, 'validate': 30},
                'anthropic': {'translate': 120, 'analyze': 60, 'validate': 30},
                'ollama': {'translate': 180, 'analyze': 90, 'validate': 45},
            },
            agent_timeout={
                'java_analyzer': 120,
                'bedrock_architect': 60,
                'logic_translator': 180,
                'asset_converter': 120,
                'packaging_agent': 60,
                'qa_validator': 90,
                'warning_threshold': 0.8,
            },
            pipeline_timeout={
                'analysis': 180,
                'conversion': 300,
                'validation': 120,
                'packaging': 60,
                'total_job': 1800,
            },
            timeouts={
                'enabled': True,
                'default': 300,
                'max': 3600,
            },
            warning_threshold=0.8,
        )
    
    def get_llm_timeout(self, provider: str, operation: str) -> int:
        """Get LLM timeout for a specific provider and operation."""
        provider_timeouts = self.llm_timeout.get(provider, {})
        return provider_timeouts.get(operation, self.timeouts.get('default', 300))
    
    def get_agent_timeout(self, agent_type: str) -> int:
        """Get timeout for a specific agent type."""
        return self.agent_timeout.get(agent_type, self.timeouts.get('default', 300))
    
    def get_pipeline_timeout(self, stage: str) -> int:
        """Get timeout for a specific pipeline stage."""
        return self.pipeline_timeout.get(stage, self.timeouts.get('default', 300))


class TimeoutContext:
    """Context manager for async operations with timeout support."""
    
    def __init__(
        self,
        timeout: float,
        operation: str,
        on_warning: Optional[Callable[[float, float], None]] = None,
        on_timeout: Optional[Callable[[], None]] = None
    ):
        self.timeout = timeout
        self.operation = operation
        self.on_warning = on_warning
        self.on_timeout = on_timeout
        self.start_time: Optional[float] = None
        self.warning_emitted = False
    
    async def __aenter__(self):
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        
        # Check for warning threshold
        config = TimeoutConfig._default()
        if not self.warning_emitted and elapsed >= self.timeout * config.warning_threshold:
            self.warning_emitted = True
            if self.on_warning:
                self.on_warning(elapsed, self.timeout)
        
        # Check for timeout
        if elapsed >= self.timeout:
            if self.on_timeout:
                self.on_timeout()
            raise TimeoutExceeded(
                f"Operation '{self.operation}' timed out after {elapsed:.2f}s",
                operation=self.operation,
                timeout_seconds=self.timeout,
                elapsed_seconds=elapsed
            )
        
        return False


class DeadlineTracker:
    """Track deadlines for multiple stages with progress reporting."""
    
    def __init__(self, config: TimeoutConfig):
        self.config = config
        self.start_time: Optional[float] = None
        self.stage_start_times: Dict[str, float] = {}
        self.stage_progress: Dict[str, float] = {}
        self.completed_stages: set = set()
    
    def start(self):
        """Start overall job tracking."""
        self.start_time = time.time()
        logger.info(f"Deadline tracker started at {datetime.utcnow()}")
    
    def start_stage(self, stage: str):
        """Mark the start of a pipeline stage."""
        self.stage_start_times[stage] = time.time()
        logger.debug(f"Stage '{stage}' started")
    
    def complete_stage(self, stage: str, progress: float = 1.0):
        """Mark a stage as completed."""
        if stage in self.stage_start_times:
            elapsed = time.time() - self.stage_start_times[stage]
            logger.info(f"Stage '{stage}' completed in {elapsed:.2f}s")
        self.completed_stages.add(stage)
        self.stage_progress[stage] = progress
    
    def set_progress(self, stage: str, progress: float):
        """Update progress for a stage (0.0 - 1.0)."""
        self.stage_progress[stage] = progress
    
    def get_elapsed(self) -> float:
        """Get elapsed time since job start."""
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time
    
    def get_stage_elapsed(self, stage: str) -> float:
        """Get elapsed time for a specific stage."""
        start = self.stage_start_times.get(stage)
        if start is None:
            return 0.0
        return time.time() - start
    
    def get_remaining(self, stage: str) -> float:
        """Get remaining time for a specific stage."""
        timeout = self.config.get_pipeline_timeout(stage)
        elapsed = self.get_stage_elapsed(stage)
        return max(0.0, timeout - elapsed)
    
    def get_job_remaining(self) -> float:
        """Get remaining time for the overall job."""
        timeout = self.config.pipeline_timeout.get('total_job', 1800)
        elapsed = self.get_elapsed()
        return max(0.0, timeout - elapsed)
    
    def is_stage_timeout(self, stage: str) -> bool:
        """Check if a stage has exceeded its timeout."""
        return self.get_remaining(stage) <= 0
    
    def is_job_timeout(self) -> bool:
        """Check if the overall job has exceeded its timeout."""
        return self.get_job_remaining() <= 0
    
    def get_progress_with_eta(self) -> Dict[str, Any]:
        """Get overall progress with ETA calculation."""
        elapsed = self.get_elapsed()
        total_timeout = self.config.pipeline_timeout.get('total_job', 1800)
        overall_progress = min(1.0, elapsed / total_timeout)
        
        # Calculate ETA based on completed stages
        completed = len(self.completed_stages)
        total_stages = len(self.config.pipeline_timeout) - 1  # Exclude 'total_job'
        
        if completed > 0:
            avg_time_per_stage = elapsed / completed
            remaining_stages = total_stages - completed
            eta_seconds = avg_time_per_stage * remaining_stages
        else:
            eta_seconds = total_timeout - elapsed
        
        return {
            'elapsed_seconds': elapsed,
            'remaining_seconds': max(0, total_timeout - elapsed),
            'overall_progress': overall_progress,
            'stages_completed': completed,
            'total_stages': total_stages,
            'eta_seconds': max(0, eta_seconds),
            'stage_progress': dict(self.stage_progress),
        }
    
    def check_stage_deadline(self, stage: str) -> bool:
        """Check if a stage can still complete within its deadline."""
        remaining = self.get_remaining(stage)
        min_time_needed = 10  # Minimum seconds needed to make progress
        
        if remaining < min_time_needed:
            logger.warning(
                f"Stage '{stage}' deadline approaching: {remaining:.2f}s remaining"
            )
            return False
        return True


# Global timeout config instance
_timeout_config: Optional[TimeoutConfig] = None


def get_timeout_config(config_path: Optional[Union[str, Path]] = None) -> TimeoutConfig:
    """Get or create the global timeout configuration."""
    global _timeout_config
    
    if _timeout_config is None:
        if config_path is None:
            # Try default locations
            possible_paths = [
                Path(__file__).parent.parent / "config" / "timeouts.yaml",
                Path.cwd() / "ai-engine" / "config" / "timeouts.yaml",
            ]
            for path in possible_paths:
                if path.exists():
                    config_path = path
                    break
        
        if config_path:
            _timeout_config = TimeoutConfig.from_yaml(config_path)
        else:
            _timeout_config = TimeoutConfig._default()
    
    return _timeout_config


def set_timeout_config(config: TimeoutConfig):
    """Set the global timeout configuration."""
    global _timeout_config
    _timeout_config = config


@asynccontextmanager
async def timeout_context(
    seconds: float,
    operation: str,
    config: Optional[TimeoutConfig] = None
):
    """Async context manager for timeout handling."""
    if config is None:
        config = get_timeout_config()
    
    warning_threshold = config.warning_threshold
    
    async with asyncio.timeout(seconds) as cm:
        start_time = time.time()
        
        try:
            yield cm
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            logger.error(f"Timeout in '{operation}' after {elapsed:.2f}s")
            raise TimeoutExceeded(
                f"Operation '{operation}' timed out",
                operation=operation,
                timeout_seconds=seconds,
                elapsed_seconds=elapsed
            )


async def run_with_timeout(
    coro,
    timeout_seconds: float,
    operation: str,
    on_warning: Optional[Callable[[float, float], None]] = None
):
    """Run an async coroutine with timeout."""
    config = get_timeout_config()
    
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        elapsed = timeout_seconds
        logger.error(f"Timeout in '{operation}' after {elapsed:.2f}s")
        
        if on_warning:
            on_warning(elapsed, timeout_seconds)
        
        raise TimeoutExceeded(
            f"Operation '{operation}' timed out",
            operation=operation,
            timeout_seconds=timeout_seconds,
            elapsed_seconds=elapsed
        )


def create_deadline_tracker(config: Optional[TimeoutConfig] = None) -> DeadlineTracker:
    """Create a new deadline tracker with the given config."""
    if config is None:
        config = get_timeout_config()
    return DeadlineTracker(config)
