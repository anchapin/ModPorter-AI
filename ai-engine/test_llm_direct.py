#!/usr/bin/env python3
"""
Test LLM response processing directly to isolate the issue
"""

import os
import sys
import logging
from pathlib import Path

# Add the ai-engine directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_llm_response_processing():
    """Test LLM response processing directly"""
    try:
        from src.utils.rate_limiter import create_ollama_llm
        
        # Create Ollama LLM
        llm = create_ollama_llm(
            model_name="llama3.2",
            base_url="http://localhost:11434",
            temperature=0.1,
            max_tokens=256,
            request_timeout=60,
            streaming=False
        )
        
        print("✅ LLM created")
        
        # Test direct invoke
        print("Testing direct invoke...")
        result1 = llm.invoke("Summarize this tool output in one sentence: {\"success\": true, \"assets\": {\"textures\": [], \"models\": [], \"sounds\": [], \"other_assets\": [], \"asset_summary\": {\"summary\": \"Asset extraction completed\"}}, \"conversion_notes\": [\"Assets ready for conversion analysis\"]}")
        print(f"Direct invoke result: {result1}")
        
        # Test CrewAI mode
        print("Testing CrewAI mode...")
        if hasattr(llm, 'enable_crew_mode'):
            llm.enable_crew_mode()
            
        result2 = llm.invoke("Summarize this tool output in one sentence: {\"success\": true, \"assets\": {\"textures\": [], \"models\": [], \"sounds\": [], \"other_assets\": [], \"asset_summary\": {\"summary\": \"Asset extraction completed\"}}, \"conversion_notes\": [\"Assets ready for conversion analysis\"]}")
        print(f"CrewAI mode result: {result2}")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_llm_response_processing()
    sys.exit(0 if success else 1)