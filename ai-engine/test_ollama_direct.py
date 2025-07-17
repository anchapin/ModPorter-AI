#!/usr/bin/env python3
"""
Test Ollama connection directly without CrewAI
"""

import os
import sys
import logging

# Add the ai-engine directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_ollama_direct():
    """Test Ollama connection directly"""
    try:
        # Set environment variables
        os.environ["USE_OLLAMA"] = "true"
        os.environ["OLLAMA_MODEL"] = "llama3.2"
        os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
        
        from src.utils.rate_limiter import create_ollama_llm
        
        # Create Ollama LLM with optimized settings
        llm = create_ollama_llm(
            model_name="llama3.2",
            base_url="http://localhost:11434",
            temperature=0.1,
            max_tokens=512,  # Reduced for faster response
            request_timeout=300,  # Extended timeout
            num_ctx=4096,  # Context window
            num_batch=512,  # Batch processing
            num_thread=8,  # Multi-threading
            streaming=False  # Disable streaming
        )
        
        print("✅ Ollama LLM created successfully")
        
        # Test simple invocation
        response = llm.invoke("Say hello")
        print(f"✅ Ollama response: {response}")
        
        # Test with tool output format
        tool_output = '{"success": true, "assets": {"textures": [], "models": [], "sounds": [], "other_assets": [], "asset_summary": {"summary": "Asset extraction completed"}}, "conversion_notes": ["Assets ready for conversion analysis"]}'
        
        response2 = llm.invoke(f"Analyze this tool output and provide a summary: {tool_output}")
        print(f"✅ Tool output response: {response2}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ollama test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ollama_direct()
    sys.exit(0 if success else 1)