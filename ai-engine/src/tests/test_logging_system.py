"""
Comprehensive test suite for the enhanced logging system
"""

import pytest
import logging
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import time

# Import the logging components
from src.utils.logging_config import (
    AgentLogFormatter,
    AgentLogger,
    setup_logging,
    get_agent_logger,
    get_crew_logger,
    log_performance
)


class TestAgentLogFormatter:
    """Test the custom log formatter"""
    
    def test_basic_formatting(self):
        """Test basic log message formatting"""
        formatter = AgentLogFormatter(include_agent_context=False)
        
        # Create a mock log record
        record = logging.LogRecord(
            name="agents.java_analyzer",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        assert "JavaAnalyzer: Test message" in formatted
        assert "[INFO]" in formatted
    
    def test_context_formatting(self):
        """Test formatting with agent context"""
        formatter = AgentLogFormatter(include_agent_context=True)
        
        record = logging.LogRecord(
            name="agents.logic_translator",
            level=logging.DEBUG,
            pathname="",
            lineno=0,
            msg="Processing data",
            args=(),
            exc_info=None
        )
        
        # Add context
        record.agent_context = {"operation": "translate", "data_size": 1024}
        
        formatted = formatter.format(record)
        
        assert "LogicTranslator: Processing data" in formatted
        assert "Context:" in formatted
        assert "operation" in formatted
        assert "data_size" in formatted
    
    def test_performance_formatting(self):
        """Test formatting with performance timing"""
        formatter = AgentLogFormatter(include_agent_context=True)
        
        record = logging.LogRecord(
            name="crew.conversion_crew",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Operation completed",
            args=(),
            exc_info=None
        )
        
        record.operation_time = 1.234
        
        formatted = formatter.format(record)
        
        assert "Crew: Operation completed" in formatted
        assert "Duration: 1.234s" in formatted
    
    def test_tool_usage_formatting(self):
        """Test formatting with tool usage information"""
        formatter = AgentLogFormatter(include_agent_context=True)
        
        record = logging.LogRecord(
            name="agents.java_analyzer",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Tool executed",
            args=(),
            exc_info=None
        )
        
        record.tool_name = "rag_search_tool"
        record.tool_result = "Found 3 documentation entries"
        
        formatted = formatter.format(record)
        
        assert "Tool: rag_search_tool" in formatted
        assert "Result: Found 3 documentation entries" in formatted


class TestAgentLogger:
    """Test the enhanced agent logger"""
    
    def setup_method(self):
        """Setup for each test"""
        setup_logging(debug_mode=True, enable_file_logging=False)
        self.logger = AgentLogger("test.agent")
    
    def test_basic_logging_methods(self):
        """Test basic logging methods"""
        # These should not raise exceptions
        self.logger.info("Test info message")
        self.logger.debug("Test debug message")
        self.logger.warning("Test warning message")
        self.logger.error("Test error message")
    
    def test_operation_logging(self):
        """Test operation start/complete logging"""
        self.logger.log_operation_start("test_operation", param1="value1")
        self.logger.log_operation_complete("test_operation", 1.234, result="success")
    
    def test_tool_usage_logging(self):
        """Test tool usage logging"""
        self.logger.log_tool_usage("test_tool", result="success", duration=0.123)
        self.logger.log_tool_usage("test_tool", result={"key": "value"})
    
    def test_agent_decision_logging(self):
        """Test agent decision logging"""
        self.logger.log_agent_decision(
            "use_smart_assumption",
            "Block material not found in documentation",
            confidence=0.85,
            fallback="STONE"
        )
    
    def test_data_transfer_logging(self):
        """Test data transfer logging"""
        self.logger.log_data_transfer(
            "JavaAnalyzer",
            "LogicTranslator", 
            "block_data",
            data_size=1024
        )
    
    def test_context_parameters(self):
        """Test logging with context parameters"""
        self.logger.info("Test message", test_param="value", number=42)
        self.logger.debug("Debug message", agent_context={"key": "value"})


class TestLoggingSetup:
    """Test the logging setup functionality"""
    
    def test_basic_setup(self):
        """Test basic logging setup"""
        setup_logging(debug_mode=False, enable_file_logging=False)
        
        # Should not raise exceptions
        logger = get_agent_logger("test_agent")
        logger.info("Test message")
    
    def test_debug_mode_setup(self):
        """Test debug mode setup"""
        setup_logging(debug_mode=True, enable_file_logging=False)
        
        # Check that debug level is set
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
    
    def test_file_logging_setup(self):
        """Test file logging setup"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            setup_logging(
                debug_mode=True,
                enable_file_logging=True,
                log_file=str(log_file)
            )
            
            logger = get_agent_logger("test_agent")
            logger.info("Test file logging")
            
            # Check that log file was created and contains content
            assert log_file.exists()
            content = log_file.read_text()
            assert "Test file logging" in content
    
    def test_environment_variable_setup(self):
        """Test setup with environment variables"""
        with patch.dict(os.environ, {
            'LOG_LEVEL': 'WARNING',
            'DEBUG': 'false',
            'ENABLE_FILE_LOGGING': 'false'
        }):
            setup_logging()
            
            root_logger = logging.getLogger()
            assert root_logger.level == logging.WARNING


class TestLoggerFactories:
    """Test logger factory functions"""
    
    def test_get_agent_logger(self):
        """Test agent logger factory"""
        logger = get_agent_logger("test_agent")
        assert isinstance(logger, AgentLogger)
        assert "test_agent" in logger.logger.name
    
    def test_get_crew_logger(self):
        """Test crew logger factory"""
        logger = get_crew_logger()
        assert isinstance(logger, AgentLogger)
        assert "crew" in logger.logger.name
    
    def test_logger_singleton_behavior(self):
        """Test that loggers with same name are related"""
        logger1 = get_agent_logger("same_agent")
        logger2 = get_agent_logger("same_agent")
        
        # They should use the same underlying logger
        assert logger1.logger.name == logger2.logger.name


class TestPerformanceDecorator:
    """Test the performance logging decorator"""
    
    def setup_method(self):
        """Setup for each test"""
        setup_logging(debug_mode=True, enable_file_logging=False)
    
    def test_basic_performance_logging(self):
        """Test basic performance decorator functionality"""
        
        class TestClass:
            def __init__(self):
                self.logger = get_agent_logger("test_agent")
            
            @log_performance("test_method")
            def test_method(self, param1, param2="default"):
                time.sleep(0.01)  # Small delay for timing
                return f"Result: {param1}, {param2}"
        
        test_obj = TestClass()
        result = test_obj.test_method("test_param", param2="custom")
        
        assert result == "Result: test_param, custom"
    
    def test_performance_logging_with_exception(self):
        """Test performance decorator with exceptions"""
        
        class TestClass:
            def __init__(self):
                self.logger = get_agent_logger("test_agent")
            
            @log_performance("failing_method")
            def failing_method(self):
                raise ValueError("Test exception")
        
        test_obj = TestClass()
        
        with pytest.raises(ValueError):
            test_obj.failing_method()
    
    def test_performance_logging_without_logger(self):
        """Test performance decorator without logger attribute"""
        
        @log_performance("standalone_function")
        def standalone_function(param):
            return f"Processed: {param}"
        
        result = standalone_function("test")
        assert result == "Processed: test"


class TestIntegration:
    """Integration tests for the logging system"""
    
    def test_full_logging_workflow(self):
        """Test a complete logging workflow"""
        setup_logging(debug_mode=True, enable_file_logging=False)
        
        # Simulate agent workflow
        analyzer_logger = get_agent_logger("java_analyzer")
        translator_logger = get_agent_logger("logic_translator")
        crew_logger = get_crew_logger()
        
        # Start conversion
        crew_logger.log_operation_start("mod_conversion", mod_path="/test/mod.jar")
        
        # Java analyzer work
        analyzer_logger.log_operation_start("analyze_mod", mod_path="/test/mod.jar")
        analyzer_logger.log_tool_usage("jar_extractor", result="Extracted 15 files")
        analyzer_logger.log_agent_decision("use_forge_framework", "Found @Mod annotation", confidence=0.95)
        analyzer_logger.log_operation_complete("analyze_mod", 2.345, result="success")
        
        # Data transfer
        crew_logger.log_data_transfer("JavaAnalyzer", "LogicTranslator", "mod_metadata", data_size=2048)
        
        # Logic translator work
        translator_logger.log_operation_start("translate_logic", blocks_count=3)
        translator_logger.log_tool_usage("rag_search", result="Found 5 documentation entries")
        translator_logger.log_operation_complete("translate_logic", 1.567, result="success")
        
        # Complete conversion
        crew_logger.log_operation_complete("mod_conversion", 5.123, result="success")
    
    def test_error_handling_workflow(self):
        """Test error handling in logging workflow"""
        setup_logging(debug_mode=True, enable_file_logging=False)
        
        logger = get_agent_logger("test_agent")
        
        try:
            raise ValueError("Simulated error")
        except Exception as e:
            logger.error(f"Operation failed: {e}", 
                        error_type=type(e).__name__,
                        operation="test_operation")


class TestLogOutput:
    """Test log output and formatting"""
    
    def test_log_output_structure(self, caplog):
        """Test that log output has expected structure"""
        setup_logging(debug_mode=True, enable_file_logging=False)
        
        logger = get_agent_logger("test_agent")
        
        with caplog.at_level(logging.INFO):
            logger.info("Test message", test_param="value")
        
        # Check that log was captured
        assert len(caplog.records) > 0
        
        # Check log record structure
        record = caplog.records[-1]
        assert "test_agent" in record.name
        assert record.levelname == "INFO"
        assert "Test message" in record.message
    
    def test_debug_mode_verbosity(self, caplog):
        """Test that debug mode increases verbosity"""
        setup_logging(debug_mode=True, enable_file_logging=False)
        
        logger = get_agent_logger("test_agent")
        
        with caplog.at_level(logging.DEBUG):
            logger.debug("Debug message", context_data={"key": "value"})
        
        assert len(caplog.records) > 0
        record = caplog.records[-1]
        assert record.levelname == "DEBUG"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
