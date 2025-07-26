"""
Centralized logging configuration for ModPorter AI Engine
Provides structured logging for all agents and crew operations
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
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
        context['decision'] = decision
        context['reasoning'] = reasoning
        self.info(f"Decision: {decision}", agent_context=context)
    
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
        extra = {}
        for key, value in kwargs.items():
            if key in ['agent_context', 'operation_time', 'tool_name', 'tool_result']:
                extra[key] = value
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
            import time
            
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
