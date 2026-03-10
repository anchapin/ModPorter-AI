#!/usr/bin/env python3
"""
Test script for Z.AI backend integration
"""

import os
import sys
import logging

# Add the ai-engine directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai-engine"))

from ai_engine.utils.rate_limiter import create_z_ai_llm, get_llm_backend

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def test_z_ai_direct():
    """Test Z.AI backend directly"""
    print("\n🤖 Testing Z.AI Backend Directly")
    print("=" * 50)

    try:
        # Check if Z.AI is configured
        if not os.getenv("Z_AI_API_KEY"):
            print("❌ Z.AI API key not found in environment")
            return False

        print(f"✅ Z.AI API key found: {os.getenv('Z_AI_API_KEY')[:10]}...")
        print(f"📝 Model: {os.getenv('Z_AI_MODEL', 'glm-4-plus')}")
        print(f"🌐 Base URL: {os.getenv('Z_AI_BASE_URL', 'https://api.z.ai/v1')}")

        # Create Z.AI LLM instance
        zai_llm = create_z_ai_llm()
        print("✅ Z.AI LLM instance created successfully")

        # Test basic functionality
        test_message = "Explain Java mod compatibility in Minecraft in one paragraph."
        print(f"\n🧪 Testing with message: '{test_message}'")

        response = zai_llm.invoke(test_message)
        print(f"✅ Response received: {response.content[:200]}...")

        # Test metadata
        print(f"📊 Response metadata:")
        print(f"   - Model: {response.response_metadata.get('model', 'N/A')}")
        print(f"   - Finish reason: {response.response_metadata.get('finish_reason', 'N/A')}")
        if "usage" in response.response_metadata:
            usage = response.response_metadata["usage"]
            print(f"   - Token usage: {usage}")

        return True

    except Exception as e:
        print(f"❌ Error testing Z.AI directly: {e}")
        return False


def test_backend_selection():
    """Test backend selection logic"""
    print("\n🔀 Testing Backend Selection Logic")
    print("=" * 50)

    try:
        # Test with current environment
        llm = get_llm_backend()
        llm_type = type(llm).__name__
        print(f"✅ Selected backend: {llm_type}")

        # Test basic functionality
        test_message = "What is Minecraft modding?"
        response = llm.invoke(test_message)
        print(f"✅ Response received: {response.content[:150]}...")

        return True

    except Exception as e:
        print(f"❌ Error testing backend selection: {e}")
        return False


def test_crewai_compatibility():
    """Test CrewAI compatibility"""
    print("\n🤝 Testing CrewAI Compatibility")
    print("=" * 50)

    try:
        from crewai import Agent, Task, Crew

        # Get LLM backend
        llm = get_llm_backend()

        # Create a simple agent
        analyzer = Agent(
            role="Java Expert",
            goal="Analyze Java code for mod compatibility",
            backstory="Expert in Minecraft modding and Java development",
            llm=llm,
            verbose=True,
        )

        # Create a simple task
        task = Task(
            description="Explain what makes a Minecraft mod compatible with different versions",
            agent=analyzer,
            expected_output="Brief explanation of mod compatibility",
        )

        # Create and run crew
        crew = Crew(agents=[analyzer], tasks=[task])

        print("🧪 Running CrewAI task...")
        result = crew.kickoff()

        print(f"✅ CrewAI result: {result[:200]}...")
        return True

    except ImportError:
        print("⚠️ CrewAI not available, skipping compatibility test")
        return True
    except Exception as e:
        print(f"❌ Error testing CrewAI compatibility: {e}")
        return False


def test_environment_variables():
    """Test and display environment configuration"""
    print("\n🔧 Environment Configuration")
    print("=" * 50)

    # Z.AI Configuration
    print("🤖 Z.AI Configuration:")
    print(f"   - USE_Z_AI: {os.getenv('USE_Z_AI', 'false')}")
    print(f"   - Z_AI_API_KEY: {'✅ Set' if os.getenv('Z_AI_API_KEY') else '❌ Not set'}")
    print(f"   - Z_AI_MODEL: {os.getenv('Z_AI_MODEL', 'glm-4-plus')}")
    print(f"   - Z_AI_BASE_URL: {os.getenv('Z_AI_BASE_URL', 'https://api.z.ai/v1')}")

    # Ollama Configuration
    print("\n🦙 Ollama Configuration:")
    print(f"   - USE_OLLAMA: {os.getenv('USE_OLLAMA', 'false')}")
    print(f"   - OLLAMA_MODEL: {os.getenv('OLLAMA_MODEL', 'llama3.2')}")
    print(f"   - OLLAMA_BASE_URL: {os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}")

    # OpenAI Configuration
    print("\n🧠 OpenAI Configuration:")
    print(f"   - OPENAI_API_KEY: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Not set'}")


def main():
    """Main test function"""
    print("🚀 Z.AI Backend Integration Test")
    print("=" * 50)

    # Test environment setup
    test_environment_variables()

    # Run tests
    tests = [
        ("Z.AI Direct", test_z_ai_direct),
        ("Backend Selection", test_backend_selection),
        ("CrewAI Compatibility", test_crewai_compatibility),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 50)

    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("🎉 All tests passed! Z.AI integration is working correctly.")
        return 0
    else:
        print("⚠️ Some tests failed. Check the configuration and logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
