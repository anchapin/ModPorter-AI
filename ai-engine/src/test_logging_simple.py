#!/usr/bin/env python3
"""
Simple test script for the enhanced logging system
"""

import sys
import os
from pathlib import Path

# Test the logging configuration directly
def test_logging_config():
    """Test the logging configuration module directly"""
    print("=== Testing Logging Configuration ===")
    
    try:
        # Add src to path for imports (needed for standalone test script)
        sys.path.insert(0, str(Path(__file__).parent))
        
        # Test basic imports
        from utils.logging_config import AgentLogFormatter, AgentLogger, setup_logging
        print("✓ Successfully imported logging components")
        
        # Test formatter
        formatter = AgentLogFormatter(include_agent_context=True)
        print("✓ Created AgentLogFormatter")
        
        # Test logger
        logger = AgentLogger("test.agent")
        print("✓ Created AgentLogger")
        
        # Test setup
        setup_logging(debug_mode=True, enable_file_logging=False)
        print("✓ Setup logging configuration")
        
        # Test logging methods
        logger.info("Test info message")
        logger.debug("Test debug message", test_param="value")
        logger.log_operation_start("test_operation", param1="value1")
        logger.log_tool_usage("test_tool", result="success")
        logger.log_operation_complete("test_operation", 0.123)
        
        print("✓ All logging methods work correctly")
        
    except Exception as e:
        print(f"✗ Error testing logging config: {e}")
        return False
    
    return True


def test_environment_variables():
    """Test environment variable handling"""
    print("\n=== Testing Environment Variables ===")
    
    # Test different log levels
    test_vars = {
        'LOG_LEVEL': 'DEBUG',
        'DEBUG': 'true',
        'ENABLE_FILE_LOGGING': 'false'
    }
    
    for var, value in test_vars.items():
        os.environ[var] = value
        print(f"✓ Set {var}={value}")
    
    try:
        # Add src to path for imports (needed for standalone test script)  
        sys.path.insert(0, str(Path(__file__).parent))
        
        from utils.logging_config import setup_logging
        setup_logging()
        print("✓ Environment variables processed correctly")
    except Exception as e:
        print(f"✗ Error with environment variables: {e}")
        return False
    
    return True


def main():
    """Run simple logging tests"""
    print("ModPorter AI Engine - Simple Logging Test")
    print("=" * 45)
    
    success = True
    success &= test_logging_config()
    success &= test_environment_variables()
    
    print("\n" + "=" * 45)
    if success:
        print("✓ All simple logging tests passed!")
    else:
        print("✗ Some logging tests failed")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
