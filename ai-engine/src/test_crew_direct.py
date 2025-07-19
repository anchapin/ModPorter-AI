#!/usr/bin/env python3
"""
Test CrewAI directly with optimized Ollama to isolate the issue
"""

import os
import sys
import logging
import tempfile
from pathlib import Path

# Add the ai-engine directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_crew_directly():
    """Test CrewAI directly with minimal setup"""
    try:
        # Set environment variables
        os.environ["USE_OLLAMA"] = "true"
        os.environ["OLLAMA_MODEL"] = "llama3.2"
        os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
        
        from crewai import Agent, Task, Crew, Process
        from src.utils.rate_limiter import create_ollama_llm
        from src.agents.java_analyzer import JavaAnalyzerAgent
        
        # Create optimized Ollama LLM
        llm = create_ollama_llm(
            model_name="llama3.2",
            base_url="http://localhost:11434",
            temperature=0.1,
            max_tokens=512,  # Very small for testing
            request_timeout=120,  # 2 minutes
            num_ctx=2048,  # Smaller context
            num_batch=256,  # Smaller batch
            num_thread=4,  # Fewer threads
            streaming=False
        )
        
        # Enable CrewAI mode
        if hasattr(llm, 'enable_crew_mode'):
            llm.enable_crew_mode()
            
        print("✅ LLM created and configured for CrewAI")
        
        # Create simple agent
        analyzer_agent = JavaAnalyzerAgent()
        
        agent = Agent(
            role="Simple Test Agent",
            goal="Provide a simple response",
            backstory="You are a test agent that provides brief responses.",
            verbose=True,
            allow_delegation=False,
            llm=llm,
            memory=False,  # Disable memory for testing
            tools=[]  # No tools to isolate LLM issue
        )
        
        print("✅ Agent created")
        
        # Create simple task
        task = Task(
            description="Say hello and provide a brief summary of what you do. Keep it under 100 characters.",
            agent=agent,
            expected_output="A brief greeting and summary under 100 characters"
        )
        
        print("✅ Task created")
        
        # Create crew
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True
        )
        
        print("✅ Crew created")
        
        # Test execution
        print("🚀 Starting crew execution...")
        result = crew.kickoff()
        
        print(f"✅ Crew executed successfully: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Crew test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_crew_directly()
    sys.exit(0 if success else 1)