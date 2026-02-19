"""
Centralized logging configuration for ModPorter AI Engine
Provides structured logging for all agents and crew operations

Issue #549: Enhanced with comprehensive agent logging capabilities
- Structured logging for all agents
- Agent decisions and reasoning logging
- Tool usage and results logging
- Debug mode for verbose output
- Log analysis tools
"""

import logging
import logging.handlers
import os
import sys
import time
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextvars import ContextVar
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import json


class AgentLogFormatter(logging.Formatter):
    """Custom formatter for agent logging with structured output"""
    
    def __init__(self, include_agent_context: bool = True):
        self.include_agent_context = include_agent_context
        super().__init__()
    
    def format(self, record: logging.LogRecord) -> str:
        # Base format with timestamp, level, and logger name
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # Extract agent name from logger name (e.g., 'agents.java_analyzer' -> 'JavaAnalyzer')
        logger_parts = record.name.split('.')
        if 'agents' in logger_parts:
            agent_idx = logger_parts.index('agents')
            if agent_idx + 1 < len(logger_parts):
                agent_name = logger_parts[agent_idx + 1].replace('_', '').title()
            else:
                agent_name = 'Agent'
        elif 'crew' in logger_parts:
            agent_name = 'Crew'
        else:
            agent_name = record.name.split('.')[-1].title()
        
        # Build the log message
        base_msg = f"{timestamp} [{record.levelname}] {agent_name}: {record.getMessage()}"
        
        # Add extra context if available
        if hasattr(record, 'agent_context') and self.include_agent_context:
            context = record.agent_context
            if isinstance(context, dict):
                context_str = json.dumps(context, separators=(',', ':'))
                base_msg += f" | Context: {context_str}"
        
        # Add operation timing if available
        if hasattr(record, 'operation_time'):
            base_msg += f" | Duration: {record.operation_time:.3f}s"
        
        # Add tool usage information if available
        if hasattr(record, 'tool_name'):
            base_msg += f" | Tool: {record.tool_name}"
            if hasattr(record, 'tool_result'):
                result_preview = str(record.tool_result)[:100]
                if len(str(record.tool_result)) > 100:
                    result_preview += "..."
                base_msg += f" | Result: {result_preview}"
        
        return base_msg


class AgentLogger:
    """Enhanced logger for agent operations with structured logging"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.agent_name = name.split('.')[-1].replace('_', '').title()
    
    def info(self, message: str, **kwargs):
        """Log info message with optional context"""
        extra = self._build_extra(**kwargs)
        self.logger.info(message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with optional context"""
        extra = self._build_extra(**kwargs)
        self.logger.debug(message, extra=extra)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with optional context"""
        extra = self._build_extra(**kwargs)
        self.logger.warning(message, extra=extra)
    
    def error(self, message: str, **kwargs):
        """Log error message with optional context"""
        extra = self._build_extra(**kwargs)
        self.logger.error(message, extra=extra)
    
    def log_operation_start(self, operation: str, **context):
        """Log the start of an operation"""
        self.info(f"Starting {operation}", agent_context=context)
    
    def log_operation_complete(self, operation: str, duration: float, **context):
        """Log the completion of an operation with timing"""
        self.info(f"Completed {operation}", operation_time=duration, agent_context=context)
    
    def log_tool_usage(self, tool_name: str, result: Any = None, duration: Optional[float] = None):
        """Log tool usage with results"""
        kwargs = {'tool_name': tool_name}
        if result is not None:
            kwargs['tool_result'] = result
        if duration is not None:
            kwargs['operation_time'] = duration
        
        self.info(f"Used tool: {tool_name}", **kwargs)
    
    def log_agent_decision(self, decision: str, reasoning: str, **context):
        """Log agent decision-making process"""
        log_context = context.copy()
        log_context['decision'] = decision
        log_context['reasoning'] = reasoning
        self.info(f"Decision: {decision}", agent_context=log_context)
    
    def log_data_transfer(self, from_agent: str, to_agent: str, data_type: str, data_size: Optional[int] = None):
        """Log data transfer between agents"""
        context = {
            'from_agent': from_agent,
            'to_agent': to_agent,
            'data_type': data_type
        }
        if data_size is not None:
            context['data_size'] = data_size
        
        self.info(f"Data transfer: {data_type} from {from_agent} to {to_agent}", agent_context=context)
    
    def _build_extra(self, **kwargs) -> Dict[str, Any]:
        """Build extra dictionary for logging"""
        valid_keys = {'agent_context', 'operation_time', 'tool_name', 'tool_result'}
        extra = {key: value for key, value in kwargs.items() if key in valid_keys}
        return extra


def setup_logging(
    log_level: str = None,
    log_file: Optional[str] = None,
    enable_file_logging: bool = True,
    debug_mode: bool = False,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> None:
    """
    Setup centralized logging configuration for the AI engine
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file (optional)
        enable_file_logging: Whether to enable file logging
        debug_mode: Enable debug mode with extra verbose output
        max_file_size: Maximum size of log file before rotation
        backup_count: Number of backup log files to keep
    """
    
    # Determine log level
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "DEBUG" if debug_mode else "INFO").upper()
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level, logging.INFO)
    
    # Create custom formatter
    formatter = AgentLogFormatter(include_agent_context=debug_mode)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if enabled)
    if enable_file_logging:
        if log_file is None:
            # Default log file location
            log_dir = Path(os.getenv("LOG_DIR", "/tmp/modporter-ai/logs"))
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "ai-engine.log"
        
        # Use rotating file handler to prevent huge log files
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels for third-party libraries to reduce noise
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("crewai").setLevel(logging.INFO if debug_mode else logging.WARNING)
    
    # Log the configuration
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {log_level}, Debug: {debug_mode}, File: {enable_file_logging}")


def get_agent_logger(agent_name: str) -> AgentLogger:
    """
    Get a configured logger for an agent
    
    Args:
        agent_name: Name of the agent (e.g., 'java_analyzer', 'logic_translator')
    
    Returns:
        AgentLogger instance
    """
    logger_name = f"agents.{agent_name}"
    return AgentLogger(logger_name)


def get_crew_logger() -> AgentLogger:
    """Get a configured logger for crew operations"""
    return AgentLogger("crew.conversion_crew")


# Performance timing decorator
def log_performance(operation_name: str = None):
    """Decorator to log operation performance"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            
            # Get logger from the class instance if available
            if args and hasattr(args[0], 'logger'):
                logger = args[0].logger
            else:
                logger = get_agent_logger(func.__module__.split('.')[-1])
            
            op_name = operation_name or func.__name__
            start_time = time.time()
            
            logger.log_operation_start(op_name)
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.log_operation_complete(op_name, duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Operation {op_name} failed after {duration:.3f}s: {str(e)}")
                raise
        
        return wrapper
    return decorator


# ============================================================================
# Issue #549: Comprehensive Agent Logging Enhancements
# ============================================================================

# Context variable for tracking operation context across async boundaries
_operation_context: ContextVar[Dict[str, Any]] = ContextVar('operation_context', default={})


@dataclass
class AgentDecision:
    """Represents an agent decision for logging and analysis"""
    agent_name: str
    decision_type: str
    decision: str
    reasoning: str
    confidence: Optional[float] = None
    alternatives_considered: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    duration_ms: Optional[float] = None


@dataclass
class ToolUsage:
    """Represents tool usage for logging and analysis"""
    agent_name: str
    tool_name: str
    input_params: Dict[str, Any]
    output_result: Any
    success: bool
    duration_ms: float
    error_message: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class AgentLogAnalyzer:
    """
    Log analysis tools for agent operations.
    Provides insights into agent behavior, decisions, and performance.
    """
    
    def __init__(self):
        self.decisions: List[AgentDecision] = []
        self.tool_usages: List[ToolUsage] = []
        self._lock = threading.Lock()
    
    def record_decision(self, decision: AgentDecision):
        """Record an agent decision for analysis"""
        with self._lock:
            self.decisions.append(decision)
    
    def record_tool_usage(self, usage: ToolUsage):
        """Record tool usage for analysis"""
        with self._lock:
            self.tool_usages.append(usage)
    
    def get_agent_statistics(self, agent_name: str = None) -> Dict[str, Any]:
        """Get statistics for a specific agent or all agents"""
        with self._lock:
            decisions = self.decisions
            tool_usages = self.tool_usages
        
        if agent_name:
            decisions = [d for d in decisions if d.agent_name == agent_name]
            tool_usages = [t for t in tool_usages if t.agent_name == agent_name]
        
        # Calculate decision statistics
        decision_types = defaultdict(int)
        avg_confidence = 0.0
        if decisions:
            for d in decisions:
                decision_types[d.decision_type] += 1
                if d.confidence is not None:
                    avg_confidence += d.confidence
            avg_confidence /= len([d for d in decisions if d.confidence is not None]) if decisions else 1
        
        # Calculate tool usage statistics
        tool_counts = defaultdict(int)
        tool_success_rate = defaultdict(lambda: {'success': 0, 'total': 0})
        avg_tool_duration = defaultdict(list)
        
        for t in tool_usages:
            tool_counts[t.tool_name] += 1
            tool_success_rate[t.tool_name]['total'] += 1
            if t.success:
                tool_success_rate[t.tool_name]['success'] += 1
            avg_tool_duration[t.tool_name].append(t.duration_ms)
        
        # Calculate average durations
        avg_durations = {}
        for tool, durations in avg_tool_duration.items():
            avg_durations[tool] = sum(durations) / len(durations) if durations else 0
        
        # Calculate success rates
        success_rates = {}
        for tool, counts in tool_success_rate.items():
            success_rates[tool] = counts['success'] / counts['total'] if counts['total'] > 0 else 0
        
        return {
            'agent_name': agent_name or 'all',
            'total_decisions': len(decisions),
            'total_tool_usages': len(tool_usages),
            'decision_types': dict(decision_types),
            'average_confidence': avg_confidence,
            'tool_usage_counts': dict(tool_counts),
            'tool_success_rates': success_rates,
            'average_tool_durations_ms': avg_durations,
        }
    
    def get_decision_trace(self, agent_name: str = None, limit: int = 100) -> List[Dict]:
        """Get a trace of recent decisions"""
        with self._lock:
            decisions = self.decisions.copy()
        
        if agent_name:
            decisions = [d for d in decisions if d.agent_name == agent_name]
        
        # Sort by timestamp (most recent first) and limit
        decisions = sorted(decisions, key=lambda d: d.timestamp, reverse=True)[:limit]
        
        return [asdict(d) for d in decisions]
    
    def get_tool_usage_trace(self, agent_name: str = None, limit: int = 100) -> List[Dict]:
        """Get a trace of recent tool usages"""
        with self._lock:
            usages = self.tool_usages.copy()
        
        if agent_name:
            usages = [u for u in usages if u.agent_name == agent_name]
        
        # Sort by timestamp (most recent first) and limit
        usages = sorted(usages, key=lambda u: u.timestamp, reverse=True)[:limit]
        
        return [asdict(u) for u in usages]
    
    def export_analysis(self, filepath: str):
        """Export analysis data to JSON file"""
        data = {
            'export_timestamp': datetime.now().isoformat(),
            'statistics': self.get_agent_statistics(),
            'decision_trace': self.get_decision_trace(limit=1000),
            'tool_usage_trace': self.get_tool_usage_trace(limit=1000),
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def clear(self):
        """Clear all recorded data"""
        with self._lock:
            self.decisions.clear()
            self.tool_usages.clear()


# Global log analyzer instance
_log_analyzer: Optional[AgentLogAnalyzer] = None


def get_log_analyzer() -> AgentLogAnalyzer:
    """Get the global log analyzer instance"""
    global _log_analyzer
    if _log_analyzer is None:
        _log_analyzer = AgentLogAnalyzer()
    return _log_analyzer


class EnhancedAgentLogger(AgentLogger):
    """
    Enhanced agent logger with comprehensive logging capabilities.
    
    Features:
    - Structured logging with context
    - Decision and reasoning logging
    - Tool usage tracking
    - Debug mode with verbose output
    - Integration with log analyzer
    """
    
    def __init__(self, name: str, debug_mode: bool = False):
        super().__init__(name)
        self._debug_mode = debug_mode or os.getenv("AGENT_DEBUG_MODE", "false").lower() == "true"
        self._analyzer = get_log_analyzer()
        self._operation_stack: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
    
    def set_debug_mode(self, enabled: bool):
        """Enable or disable debug mode"""
        self._debug_mode = enabled
        self.debug(f"Debug mode {'enabled' if enabled else 'disabled'}")
    
    def log_decision(
        self,
        decision_type: str,
        decision: str,
        reasoning: str,
        confidence: float = None,
        alternatives: List[str] = None,
        **context
    ):
        """
        Log an agent decision with reasoning.
        
        Args:
            decision_type: Type of decision (e.g., 'feature_mapping', 'code_translation')
            decision: The decision made
            reasoning: Explanation of why this decision was made
            confidence: Confidence level (0.0 to 1.0)
            alternatives: List of alternatives that were considered
            **context: Additional context for the decision
        """
        # Create decision record
        decision_record = AgentDecision(
            agent_name=self.agent_name,
            decision_type=decision_type,
            decision=decision,
            reasoning=reasoning,
            confidence=confidence,
            alternatives_considered=alternatives or [],
            context=context,
        )
        
        # Record for analysis
        self._analyzer.record_decision(decision_record)
        
        # Log the decision
        log_context = {
            'decision_type': decision_type,
            'confidence': confidence,
            'alternatives_count': len(alternatives) if alternatives else 0,
            **context
        }
        
        if self._debug_mode:
            # Verbose output in debug mode
            self.info(
                f"DECISION [{decision_type}]: {decision}",
                agent_context=log_context
            )
            self.debug(f"  Reasoning: {reasoning}")
            if alternatives:
                self.debug(f"  Alternatives considered: {alternatives}")
        else:
            self.info(
                f"Decision: {decision_type} -> {decision}",
                agent_context=log_context
            )
    
    def log_tool_call(
        self,
        tool_name: str,
        input_params: Dict[str, Any],
        result: Any = None,
        success: bool = True,
        duration_ms: float = 0,
        error: str = None
    ):
        """
        Log a tool call with input/output details.
        
        Args:
            tool_name: Name of the tool called
            input_params: Parameters passed to the tool
            result: Result returned by the tool
            success: Whether the tool call succeeded
            duration_ms: Duration of the tool call in milliseconds
            error: Error message if the call failed
        """
        # Create tool usage record
        usage_record = ToolUsage(
            agent_name=self.agent_name,
            tool_name=tool_name,
            input_params=input_params,
            output_result=result if not isinstance(result, str) else result[:1000],  # Truncate long strings
            success=success,
            duration_ms=duration_ms,
            error_message=error,
        )
        
        # Record for analysis
        self._analyzer.record_tool_usage(usage_record)
        
        # Log the tool call
        if success:
            self.info(
                f"Tool call: {tool_name} ({duration_ms:.1f}ms)",
                tool_name=tool_name,
                operation_time=duration_ms / 1000
            )
        else:
            self.error(
                f"Tool call failed: {tool_name} - {error}",
                tool_name=tool_name,
                operation_time=duration_ms / 1000
            )
        
        # Debug mode: log input/output details
        if self._debug_mode:
            self.debug(f"  Tool input: {json.dumps(input_params, default=str)[:500]}")
            if success and result is not None:
                result_str = str(result)[:500]
                self.debug(f"  Tool output: {result_str}")
    
    def log_reasoning_step(self, step: str, details: str = None):
        """
        Log a reasoning step in the agent's thought process.
        
        Args:
            step: Name/description of the reasoning step
            details: Additional details about the step
        """
        if self._debug_mode:
            self.debug(f"Reasoning: {step}")
            if details:
                self.debug(f"  Details: {details}")
    
    def log_state_change(self, state_name: str, old_value: Any, new_value: Any, reason: str = None):
        """
        Log a state change in the agent.
        
        Args:
            state_name: Name of the state variable
            old_value: Previous value
            new_value: New value
            reason: Reason for the change
        """
        context = {
            'state_name': state_name,
            'old_value': str(old_value)[:200],
            'new_value': str(new_value)[:200],
        }
        if reason:
            context['reason'] = reason
        
        self.debug(f"State change: {state_name}", agent_context=context)
    
    def push_operation(self, operation: str, **context):
        """Push an operation onto the operation stack"""
        with self._lock:
            self._operation_stack.append({
                'operation': operation,
                'context': context,
                'start_time': time.time(),
            })
        self.debug(f"Started operation: {operation}")
    
    def pop_operation(self, success: bool = True, error: str = None):
        """Pop an operation from the stack and log its completion"""
        with self._lock:
            if not self._operation_stack:
                self.warning("Attempted to pop operation from empty stack")
                return
            
            op = self._operation_stack.pop()
        
        duration = time.time() - op['start_time']
        operation = op['operation']
        
        if success:
            self.info(f"Completed operation: {operation} ({duration:.3f}s)")
        else:
            self.error(f"Failed operation: {operation} ({duration:.3f}s) - {error}")
    
    def get_current_operation(self) -> Optional[str]:
        """Get the current operation name"""
        with self._lock:
            if self._operation_stack:
                return self._operation_stack[-1]['operation']
            return None
    
    def log_error_with_trace(self, message: str, error: Exception = None):
        """
        Log an error with full stack trace.
        
        Args:
            message: Error message
            error: Exception object (optional)
        """
        self.error(message)
        
        if error and self._debug_mode:
            # Log full stack trace in debug mode
            trace = traceback.format_exc()
            self.debug(f"Stack trace:\n{trace}")
    
    def log_performance_metric(self, metric_name: str, value: float, unit: str = None):
        """
        Log a performance metric.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Unit of measurement
        """
        context = {
            'metric_name': metric_name,
            'metric_value': value,
            'metric_unit': unit,
        }
        self.debug(f"Performance: {metric_name} = {value}{unit or ''}", agent_context=context)


def get_enhanced_agent_logger(agent_name: str, debug_mode: bool = False) -> EnhancedAgentLogger:
    """
    Get an enhanced agent logger with comprehensive logging capabilities.
    
    Args:
        agent_name: Name of the agent
        debug_mode: Enable debug mode for verbose output
    
    Returns:
        EnhancedAgentLogger instance
    """
    logger_name = f"agents.{agent_name}"
    return EnhancedAgentLogger(logger_name, debug_mode=debug_mode)


def enable_global_debug_mode():
    """Enable debug mode for all enhanced agent loggers"""
    os.environ["AGENT_DEBUG_MODE"] = "true"


def disable_global_debug_mode():
    """Disable debug mode for all enhanced agent loggers"""
    os.environ["AGENT_DEBUG_MODE"] = "false"


def export_log_analysis(filepath: str = None):
    """
    Export log analysis to a JSON file.
    
    Args:
        filepath: Path to export file (optional, defaults to log directory)
    """
    if filepath is None:
        log_dir = Path(os.getenv("LOG_DIR", "/tmp/modporter-ai/logs"))
        log_dir.mkdir(parents=True, exist_ok=True)
        filepath = log_dir / f"agent_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    analyzer = get_log_analyzer()
    analyzer.export_analysis(str(filepath))
    
    logger = logging.getLogger(__name__)
    logger.info(f"Log analysis exported to: {filepath}")
    
    return filepath


def get_agent_log_summary(agent_name: str = None) -> Dict[str, Any]:
    """
    Get a summary of agent logging activity.
    
    Args:
        agent_name: Specific agent name (optional, returns all if not specified)
    
    Returns:
        Dictionary with agent statistics
    """
    analyzer = get_log_analyzer()
    return analyzer.get_agent_statistics(agent_name)
