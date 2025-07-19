#!/usr/bin/env python3
"""
Test script to verify the Crew AI + Ollama integration fix
"""

import os
import sys
import json
import tempfile
from pathlib import Path
import logging

# Add the ai-engine directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai-engine'))

from src.crew.conversion_crew import ModPorterConversionCrew
from src.agents.java_analyzer import JavaAnalyzerAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_tool_parameter_handling():
    """Test that tools properly handle mod path parameters"""
    logger.info("Testing tool parameter handling...")
    
    # Create a test JAR file
    test_jar_path = "/tmp/test_mod.jar"
    
    # Create a simple test JAR file
    import zipfile
    with zipfile.ZipFile(test_jar_path, 'w') as jar:
        # Add a simple class file
        jar.writestr("com/example/TestMod.class", b"fake class file")
        # Add metadata
        jar.writestr("mcmod.info", json.dumps([{
            "modid": "testmod",
            "name": "Test Mod",
            "version": "1.0.0",
            "description": "A test mod for verification"
        }]))
    
    # Test the analyze_mod_structure_tool with different parameter formats
    agent = JavaAnalyzerAgent.get_instance()
    
    # Test 1: Direct string path (old format)
    logger.info("Testing direct string path...")
    try:
        # Use the tool's run method directly
        result1 = JavaAnalyzerAgent.analyze_mod_structure_tool.run(test_jar_path)
        data1 = json.loads(result1)
        logger.info(f"Direct string result: {data1.get('success', False)}")
    except Exception as e:
        logger.error(f"Direct string test failed: {e}")
    
    # Test 2: JSON format (new format)
    logger.info("Testing JSON format...")
    try:
        result2 = JavaAnalyzerAgent.analyze_mod_structure_tool.run(json.dumps({"mod_path": test_jar_path}))
        data2 = json.loads(result2)
        logger.info(f"JSON format result: {data2.get('success', False)}")
    except Exception as e:
        logger.error(f"JSON format test failed: {e}")
    
    # Test 3: Dict format
    logger.info("Testing dict format...")
    try:
        result3 = JavaAnalyzerAgent.analyze_mod_structure_tool.run({"mod_path": test_jar_path})
        data3 = json.loads(result3)
        logger.info(f"Dict format result: {data3.get('success', False)}")
    except Exception as e:
        logger.error(f"Dict format test failed: {e}")
    
    # Clean up
    if os.path.exists(test_jar_path):
        os.remove(test_jar_path)
    
    return True

def test_crew_integration():
    """Test the full Crew AI integration with Ollama"""
    logger.info("Testing Crew AI integration...")
    
    # Set environment variables for Ollama
    os.environ["USE_OLLAMA"] = "true"
    os.environ["OLLAMA_MODEL"] = "llama3.2"
    os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
    
    # Create test files
    test_jar_path = "/tmp/test_integration.jar"
    output_path = "/tmp/test_output.mcaddon"
    
    # Create a simple test JAR
    import zipfile
    with zipfile.ZipFile(test_jar_path, 'w') as jar:
        jar.writestr("com/example/TestBlock.java", """
        package com.example;
        public class TestBlock {
            public static final String REGISTRY_NAME = "test_block";
        }
        """)
        jar.writestr("mcmod.info", json.dumps([{
            "modid": "testmod",
            "name": "Test Mod",
            "version": "1.0.0"
        }]))
    
    try:
        # Test the conversion crew with Ollama
        crew = ModPorterConversionCrew()
        result = crew.convert_mod(
            mod_path=Path(test_jar_path),
            output_path=Path(output_path),
            smart_assumptions=True
        )
        
        logger.info(f"Conversion result: {result.get('status', 'unknown')}")
        logger.info(f"Success rate: {result.get('overall_success_rate', 0)}")
        
        return result.get('status') == 'completed'
        
    except Exception as e:
        logger.error(f"Crew integration test failed: {e}")
        return False
    
    finally:
        # Clean up
        for path in [test_jar_path, output_path]:
            if os.path.exists(path):
                os.remove(path)

def main():
    """Run all tests"""
    logger.info("Starting Crew AI + Ollama integration tests...")
    
    success = True
    
    # Test 1: Tool parameter handling
    if not test_tool_parameter_handling():
        success = False
    
    # Test 2: Crew integration
    if not test_crew_integration():
        success = False
    
    if success:
        logger.info("✅ All tests passed! The Crew AI + Ollama integration fix is working correctly.")
    else:
        logger.error("❌ Some tests failed. Please check the logs above.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
