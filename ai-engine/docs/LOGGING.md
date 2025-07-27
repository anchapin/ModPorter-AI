# Enhanced Agent Logging System

This document describes the comprehensive logging system implemented for the ModPorter AI Engine to improve debugging and monitoring of multi-agent interactions.

## Overview

The enhanced logging system provides structured, contextual logging for all agents and crew operations, making it easier to debug multi-agent interactions and understand agent decision-making processes.

## Features

### 1. Structured Logging
- **Agent Context**: Each log entry includes agent name and operation context
- **Operation Tracking**: Start/complete logging with timing information
- **Tool Usage Logging**: Detailed logging of tool invocations and results
- **Decision Logging**: Agent reasoning and decision-making processes
- **Data Transfer Logging**: Inter-agent communication tracking

### 2. Performance Monitoring
- **Operation Timing**: Automatic timing of operations with decorators
- **Performance Metrics**: Duration tracking for all major operations
- **Bottleneck Identification**: Easy identification of slow operations

### 3. Configurable Output
- **Log Levels**: DEBUG, INFO, WARNING, ERROR with environment control
- **Debug Mode**: Extra verbose output for development
- **File Logging**: Optional file output with rotation
- **Console Logging**: Structured console output

### 4. Agent-Specific Features
- **Agent Identification**: Clear identification of which agent generated each log
- **Context Preservation**: Maintains context across agent operations
- **Error Tracking**: Enhanced error logging with context

## Configuration

### Environment Variables

```bash
# Log level configuration
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR  # Default: INFO

# Debug mode (extra verbose output)
DEBUG=true|false  # Default: false

# File logging
ENABLE_FILE_LOGGING=true|false  # Default: true
LOG_DIR=/path/to/logs  # Default: /tmp/modporter-ai/logs

# Log file rotation
LOG_MAX_SIZE=10485760  # 10MB default
LOG_BACKUP_COUNT=5  # Number of backup files
```

### Setup in Application

```python
from utils.logging_config import setup_logging
```

## Usage

### Agent Logging

```python
from utils.logging_config import get_agent_logger, log_performance

class MyAgent:
    def __init__(self):
        self.logger = get_agent_logger("my_agent")
    
    def process_data(self, data):
        # Basic logging
        self.logger.info("Processing data", data_size=len(data))
        
        # Operation logging
        self.logger.log_operation_start("data_processing", 
                                      data_type=type(data).__name__)
        
        # Tool usage logging
        result = self.use_tool("analysis_tool", data)
        self.logger.log_tool_usage("analysis_tool", 
                                 result=result, 
                                 duration=0.123)
        
        # Decision logging
        self.logger.log_agent_decision(
            "use_smart_assumption",
            "Data incomplete, using default values",
            confidence=0.85,
            fallback="default_value"
        )
        
        # Operation completion
        self.logger.log_operation_complete("data_processing", 
                                         1.234, 
                                         result="success")
```

### Performance Logging

```python
from utils.logging_config import log_performance

class MyAgent:
    def __init__(self):
        self.logger = get_agent_logger("my_agent")
    
    @log_performance("expensive_operation")
    def expensive_operation(self, param1, param2):
        """This method will be automatically timed and logged"""
        # Do expensive work
        return result
```

### Crew Logging

```python
from src.utils.logging_config import get_crew_logger

class MyConversionCrew:
    def __init__(self):
        self.logger = get_crew_logger()
    
    def execute_conversion(self):
        self.logger.log_operation_start("conversion", 
                                      agents_count=5,
                                      conversion_type="block")
        
        # Log data transfers between agents
        self.logger.log_data_transfer(
            "JavaAnalyzer", 
            "LogicTranslator", 
            "block_data",
            data_size=1024
        )
```

## Log Format

### Standard Format
```
2025-07-26 04:00:15.123 [INFO] JavaAnalyzer: Starting analysis of SimpleStoneBlock.java | Context: {"mod_path": "/app/test.jar", "file_size": 1024}
```

### Debug Format (with context)
```
2025-07-26 04:00:15.123 [DEBUG] JavaAnalyzer: Extracted class name: CustomStoneBlock | Context: {"class_name": "CustomStoneBlock", "package": "com.example.mod"} | Duration: 0.045s
```

### Tool Usage Format
```
2025-07-26 04:00:16.456 [INFO] LogicTranslator: Used tool: rag_search_tool | Tool: rag_search_tool | Result: Found 3 relevant documentation entries | Duration: 0.234s
```

### Data Transfer Format
```
2025-07-26 04:00:17.789 [INFO] Crew: Data transfer: block_data from JavaAnalyzer to LogicTranslator | Context: {"from_agent": "JavaAnalyzer", "to_agent": "LogicTranslator", "data_type": "block_data", "data_size": 1024}
```

## Implementation Details

### Core Components

1. **AgentLogFormatter**: Custom formatter for structured output
2. **AgentLogger**: Enhanced logger with agent-specific methods
3. **setup_logging()**: Centralized configuration function
4. **log_performance**: Decorator for automatic performance logging

### File Structure
```
ai-engine/src/utils/
├── logging_config.py          # Main logging configuration
└── __init__.py               # Package initialization
```

### Integration Points

1. **main.py**: Application startup logging configuration
2. **agents/*.py**: Individual agent logging enhancement
3. **crew/conversion_crew.py**: Crew-level operation logging
4. **tools/*.py**: Tool usage logging (future enhancement)

## Debugging Workflows

### Development Debugging
```bash
# Enable debug mode
export DEBUG=true
export LOG_LEVEL=DEBUG

# Run with verbose logging
python main.py
```

### Production Monitoring
```bash
# Enable file logging with rotation
export ENABLE_FILE_LOGGING=true
export LOG_LEVEL=INFO
export LOG_DIR=/var/log/modporter-ai

# Monitor logs
tail -f /var/log/modporter-ai/ai-engine.log
```

### Performance Analysis
```bash
# Enable performance logging
export DEBUG=true

# Filter performance logs
grep "Duration:" /var/log/modporter-ai/ai-engine.log | sort -k6 -n
```

## Testing

### Unit Tests
```python
# Test logging configuration
python test_logging_simple.py

# Test in Docker environment
docker compose exec ai-engine python -c "
from src.utils.logging_config import setup_logging, get_agent_logger
setup_logging(debug_mode=True)
logger = get_agent_logger('test')
logger.info('Test successful')
"
```

### Integration Tests
```python
# Test agent logging integration
pytest tests/test_agent_logging.py

# Test crew logging integration  
pytest tests/test_crew_logging.py
```

## Best Practices

### 1. Agent Implementation
- Always use `get_agent_logger(agent_name)` for consistent naming
- Log operation start/complete for major operations
- Include relevant context in log messages
- Use appropriate log levels (DEBUG for detailed info, INFO for important events)

### 2. Error Handling
- Always log errors with context
- Include error type and operation context
- Use structured logging for better parsing

### 3. Performance Considerations
- Use `@log_performance` decorator for expensive operations
- Avoid logging large data structures directly
- Use log levels appropriately to control verbosity

### 4. Security
- Never log sensitive information (API keys, passwords)
- Sanitize user input before logging
- Use appropriate log rotation to manage disk space

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure PYTHONPATH includes src directory
2. **Permission Errors**: Check log directory permissions
3. **Performance Impact**: Adjust log level in production
4. **Disk Space**: Configure log rotation appropriately

### Debug Commands
```bash
# Check logging configuration
python -c "from src.utils.logging_config import setup_logging; setup_logging(debug_mode=True)"

# Test agent logger
python -c "from src.utils.logging_config import get_agent_logger; logger = get_agent_logger('test'); logger.info('Test')"

# Verify log files
ls -la /tmp/modporter-ai/logs/
```

## Future Enhancements

1. **Centralized Log Aggregation**: Integration with ELK stack or similar
2. **Real-time Monitoring**: WebSocket-based log streaming
3. **Performance Dashboards**: Grafana integration for performance metrics
4. **Alert System**: Automated alerts for errors and performance issues
5. **Log Analysis Tools**: Automated log analysis and pattern detection

## Related Issues

- Issue #153: Logging: Add Comprehensive Agent Logging
- Issue #159: Comprehensive Testing Framework with Behavioral Validation
- Issue #161: A/B Testing Infrastructure for Agent Strategy Optimization
