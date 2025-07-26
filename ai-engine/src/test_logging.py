#!/usr/bin/env python3
"""
Test script for the enhanced logging system
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Set PYTHONPATH to handle src imports
os.environ['PYTHONPATH'] = str(Path(__file__).parent)

try:
    from utils.logging_config import setup_logging, get_agent_logger, get_crew_logger, log_performance
    LOGGING_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import logging config: {e}")
    print("Testing basic logging functionality only...")
    LOGGING_AVAILABLE = False
    import logging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def test_basic_logging():
    """Test basic logging functionality"""
    print("=== Testing Basic Logging ===")
    
    if LOGGING_AVAILABLE:
        # Setup logging in debug mode
        setup_logging(debug_mode=True, enable_file_logging=False)
        
        # Test different logger types
        agent_logger = get_agent_logger("test_agent")
        crew_logger = get_crew_logger()
        
        # Test basic logging methods
        agent_logger.info("This is an info message from test agent")
        agent_logger.debug("This is a debug message with context", test_param="test_value")
        agent_logger.warning("This is a warning message")
        
        crew_logger.info("This is an info message from crew")
        crew_logger.debug("Crew debug message with context", operation="test_operation")
    else:
        # Fallback to basic logging
        logger = logging.getLogger("test_agent")
        logger.info("Basic logging test - info message")
        logger.debug("Basic logging test - debug message")
        logger.warning("Basic logging test - warning message")
    
    print("✓ Basic logging test completed")


def test_structured_logging():
    """Test structured logging features"""
    print("\n=== Testing Structured Logging ===")
    
    if not LOGGING_AVAILABLE:
        print("Skipping structured logging test - enhanced logging not available")
        return
    
    agent_logger = get_agent_logger("test_agent")
    
    # Test operation logging
    agent_logger.log_operation_start("test_operation", param1="value1", param2="value2")
    
    # Test tool usage logging
    agent_logger.log_tool_usage("test_tool", result="success", duration=0.123)
    
    # Test agent decision logging
    agent_logger.log_agent_decision(
        "use_smart_assumption", 
        "Block material not found in documentation",
        confidence=0.85,
        fallback="STONE"
    )
    
    # Test data transfer logging
    agent_logger.log_data_transfer("JavaAnalyzer", "LogicTranslator", "block_data", data_size=1024)
    
    agent_logger.log_operation_complete("test_operation", 1.234, result="success")
    
    print("✓ Structured logging test completed")


def test_performance_decorator():
    """Test the performance logging decorator"""
    print("\n=== Testing Performance Decorator ===")
    
    if not LOGGING_AVAILABLE:
        print("Skipping performance decorator test - enhanced logging not available")
        return
    
    class TestAgent:
        def __init__(self):
            self.logger = get_agent_logger("test_agent")
        
        @log_performance("test_method")
        def test_method(self, param1, param2="default"):
            """Test method with performance logging"""
            import time
            time.sleep(0.1)  # Simulate work
            return f"Processed {param1} with {param2}"
    
    agent = TestAgent()
    result = agent.test_method("test_data", param2="custom_value")
    print(f"Method result: {result}")
    
    print("✓ Performance decorator test completed")


def test_error_logging():
    """Test error logging scenarios"""
    print("\n=== Testing Error Logging ===")
    
    if LOGGING_AVAILABLE:
        agent_logger = get_agent_logger("test_agent")
        
        try:
            # Simulate an error
            raise ValueError("This is a test error for logging")
        except Exception as e:
            agent_logger.error(f"Caught test error: {e}", 
                              error_type=type(e).__name__,
                              operation="test_error_handling")
    else:
        logger = logging.getLogger("test_agent")
        try:
            raise ValueError("This is a test error for logging")
        except Exception as e:
            logger.error(f"Caught test error: {e}")
    
    print("✓ Error logging test completed")


def main():
    """Run all logging tests"""
    print("ModPorter AI Engine - Enhanced Logging System Test")
    print("=" * 50)
    
    if LOGGING_AVAILABLE:
        print("✓ Enhanced logging system available")
    else:
        print("⚠ Enhanced logging system not available - using basic logging")
    
    test_basic_logging()
    test_structured_logging()
    test_performance_decorator()
    test_error_logging()
    
    print("\n" + "=" * 50)
    print("All logging tests completed successfully!")
    
    if LOGGING_AVAILABLE:
        print("\nTo test with file logging, set ENABLE_FILE_LOGGING=true")
        print("To test different log levels, set LOG_LEVEL=DEBUG|INFO|WARNING|ERROR")
        print("To test debug mode, set DEBUG=true")


if __name__ == "__main__":
    main()
