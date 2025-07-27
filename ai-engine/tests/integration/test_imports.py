"""Test basic imports to verify package structure."""
import pytest


def test_can_import_main():
    """Test that we can import the main app."""
    try:
        from main import app
        assert app is not None
        print("✅ Successfully imported main app")
    except ImportError as e:
        pytest.fail(f"Cannot import main app: {e}")


def test_can_import_agents():
    """Test that we can import agents."""
    try:
        from agents.java_analyzer import JavaAnalyzerAgent
        from agents.bedrock_builder import BedrockBuilderAgent
        
        analyzer = JavaAnalyzerAgent()
        builder = BedrockBuilderAgent()
        
        assert analyzer is not None
        assert builder is not None
        print("✅ Successfully imported agents")
    except ImportError as e:
        pytest.fail(f"Cannot import agents: {e}")


def test_python_path():
    """Test Python path setup."""
    import sys
    import os
    
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    print(f"Files in current dir: {os.listdir('.')}")
    
    # Check if main.py exists
    assert os.path.exists("main.py"), "main.py should exist in current directory"
    assert os.path.exists("agents"), "agents directory should exist"
    assert os.path.exists("agents/__init__.py"), "agents/__init__.py should exist"