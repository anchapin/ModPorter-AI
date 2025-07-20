#!/usr/bin/env python3
"""
Debug specific LLM timeout issue
"""

import os
import sys
import logging
import time

# Add the ai-engine directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_llm_with_tool_output():
    """Test LLM with tool output to isolate timeout issue"""
    try:
        # Set environment variables
        os.environ["USE_OLLAMA"] = "true"
        os.environ["OLLAMA_MODEL"] = "llama3.2"
        os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
        
        from src.utils.rate_limiter import create_ollama_llm
        
        # Create optimized Ollama LLM
        llm = create_ollama_llm(
            model_name="llama3.2",
            base_url="http://localhost:11434",
            temperature=0.1,
            max_tokens=256,  # Very small for debugging
            request_timeout=60,  # Shorter timeout for debugging
            num_ctx=2048,  # Smaller context
            num_batch=256,  # Smaller batch
            num_thread=4,  # Fewer threads
            streaming=False
        )
        
        print("✅ Ollama LLM created successfully")
        
        # Test with simple prompt first
        print("Testing simple prompt...")
        start_time = time.time()
        response = llm.invoke("Hello, respond with just 'Hi'")
        end_time = time.time()
        print(f"✅ Simple response ({end_time - start_time:.2f}s): {response}")
        
        # Test with tool output (the problematic scenario)
        print("Testing with tool output...")
        tool_output = '{"success": true, "assets": {"textures": [], "models": [], "sounds": [], "other_assets": [], "asset_summary": {"summary": "Asset extraction completed"}}, "conversion_notes": ["Assets ready for conversion analysis"]}'
        
        prompt = f"""Based on this tool output: {tool_output}
        
        Provide a brief analysis (max 50 words):"""
        
        start_time = time.time()
        response2 = llm.invoke(prompt)
        end_time = time.time()
        print(f"✅ Tool output response ({end_time - start_time:.2f}s): {response2}")
        
        # Test with even more complex prompt (closer to CrewAI task)
        print("Testing complex task prompt...")
        complex_prompt = """You are a Java Mod Analyzer. Analyze the mod file and provide a JSON response with:
        1. Feature categorization
        2. Asset summary
        3. Dependencies
        Keep response under 200 characters."""
        
        start_time = time.time()
        response3 = llm.invoke(complex_prompt)
        end_time = time.time()
        print(f"✅ Complex response ({end_time - start_time:.2f}s): {response3}")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_llm_with_tool_output()
    sys.exit(0 if success else 1)