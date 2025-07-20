#!/usr/bin/env python3
"""
Simple test to debug Crew AI execution
"""

import os
import sys
import logging
from pathlib import Path
import tempfile
import zipfile
import json

# Add the ai-engine directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_simple_crew():
    """Test the most basic crew execution"""
    try:
        # Use Ollama for testing
        os.environ["USE_OLLAMA"] = "true"
        
        from src.crew.conversion_crew import ModPorterConversionCrew
        
        # Create a simple test JAR
        test_jar_path = "/tmp/debug_test.jar"
        with zipfile.ZipFile(test_jar_path, 'w') as jar:
            jar.writestr("com/example/TestBlock.java", "public class TestBlock {}")
            jar.writestr("mcmod.info", json.dumps([{
                "modid": "debugmod",
                "name": "Debug Mod",
                "version": "1.0.0"
            }]))
        
        print("✅ Test JAR created successfully")
        
        # Try to create the crew
        crew = ModPorterConversionCrew()
        print("✅ Crew created successfully")
        
        # Test just the first task (analyze) to see what happens
        try:
            # Create inputs for the crew
            inputs = {
                'mod_path': test_jar_path,
                'output_path': '/tmp/debug_output.mcaddon',
                'temp_dir': '/tmp/debug_temp',
                'smart_assumptions_enabled': True,
                'include_dependencies': True
            }
            
            print(f"📋 Testing crew with inputs: {inputs}")
            
            # Try to run just the first task
            result = crew.crew.kickoff(inputs=inputs)
            print(f"✅ Crew execution completed: {result}")
            
        except Exception as crew_error:
            print(f"❌ Crew execution failed: {crew_error}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_crew()