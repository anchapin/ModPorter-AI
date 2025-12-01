#!/usr/bin/env python3
"""
Test script to validate langchain-code + Z.AI integration
"""
import os
import subprocess
import sys

def test_environment():
    """Test if environment variables are set correctly"""
    print("🔍 Testing Environment Configuration...")

    required_vars = {
        'OPENAI_API_KEY': 'your_zai_api_key_here',
        'OPENAI_BASE_URL': 'https://api.z.ai/api/coding/paas/v4'
    }

    all_set = True
    for var, expected in required_vars.items():
        value = os.getenv(var, '')
        if not value or value == expected:
            print(f"❌ {var}: Not properly configured")
            all_set = False
        else:
            print(f"✅ {var}: {value[:20]}..." if len(value) > 20 else f"✅ {var}: {value}")

    return all_set

def test_langchain_code_installation():
    """Test if langchain-code is properly installed"""
    print("\n🔍 Testing langchain-code Installation...")

    try:
        result = subprocess.run(['langcode', '--version'],
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ langchain-code is installed")
            return True
        else:
            print("❌ langchain-code not responding correctly")
            return False
    except FileNotFoundError:
        print("❌ langchain-code not found")
        return False
    except subprocess.TimeoutExpired:
        print("❌ langchain-code timeout")
        return False
    except Exception as e:
        print(f"❌ Error testing langchain-code: {e}")
        return False

def test_doctor():
    """Run langchain-code doctor to check configuration"""
    print("\n🔍 Running langchain-code Doctor...")

    try:
        result = subprocess.run(['langcode', 'doctor'],
                              capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            # Check if OpenAI provider is OK
            if "OpenAI               OK" in result.stdout:
                print("✅ OpenAI provider configured (pointing to Z.AI)")
                return True
            else:
                print("❌ OpenAI provider not properly configured")
                return False
        else:
            print(f"❌ Doctor command failed: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Error running doctor: {e}")
        return False

def test_api_connection():
    """Test connection to Z.AI API (requires valid API key)"""
    print("\n🔍 Testing Z.AI API Connection...")

    api_key = os.getenv('OPENAI_API_KEY')
    base_url = os.getenv('OPENAI_BASE_URL')

    if not api_key or api_key == 'your_zai_api_key_here':
        print("⚠️  Skipping API test - no valid API key configured")
        return True  # Don't fail setup for missing API key

    if not base_url:
        print("❌ OPENAI_BASE_URL not configured")
        return False

    try:
        import requests

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        # Simple test request
        data = {
            'model': 'GLM-4.5-air',
            'messages': [{'role': 'user', 'content': 'Hello'}],
            'max_tokens': 10
        }

        response = requests.post(f'{base_url}/chat/completions',
                               headers=headers, json=data, timeout=10)

        if response.status_code == 200:
            print("✅ Z.AI API connection successful")
            return True
        elif response.status_code == 401:
            print("❌ Invalid API key")
            return False
        else:
            print(f"❌ API error: {response.status_code}")
            return False

    except ImportError:
        print("⚠️  Cannot test API - requests library not available")
        return True
    except Exception as e:
        print(f"❌ API connection test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing langchain-code + Z.AI Integration")
    print("=" * 50)

    tests = [
        test_environment,
        test_langchain_code_installation,
        test_doctor,
        test_api_connection
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with error: {e}")
            results.append(False)

    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")

    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"✅ All {total} tests passed! Ready to use langchain-code with Z.AI.")
        print("\n🎯 Next steps:")
        print("1. Run: langcode chat --llm openai --mode react")
        print("2. Try: langcode feature \"Add hello world function\" --llm openai")
    else:
        print(f"❌ {total - passed} of {total} tests failed. Check configuration above.")
        if not results[0]:  # Environment test failed
            print("\n🔧 Fix environment:")
            print("1. Copy .env.example to .env")
            print("2. Replace 'your_zai_api_key_here' with your actual Z.AI API key")
        if not results[1]:  # Installation test failed
            print("\n🔧 Install langchain-code:")
            print("pip install langchain-code")

if __name__ == "__main__":
    main()