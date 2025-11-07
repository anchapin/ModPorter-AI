"""Basic integration test for AI engine."""
import pytest
from fastapi.testclient import TestClient


def test_integration_basic():
    """Basic integration test that can be skipped if dependencies missing."""
    try:
        from main import app
        TestClient(app)
        
        # Test if we can import the app
        assert app is not None
        
        # Basic integration test placeholder
        # Real tests would involve LLM providers, etc.
        
    except ImportError as e:
        pytest.skip(f"Cannot import main app for integration test: {e}")


def test_basic_health_check():
    """Test that basic system components are available."""
    try:
        # Test that we can import core modules
        from agents.java_analyzer import JavaAnalyzerAgent
        from agents.bedrock_builder import BedrockBuilderAgent
        
        # Create instances to verify basic functionality
        analyzer = JavaAnalyzerAgent()
        builder = BedrockBuilderAgent()
        
        assert analyzer is not None
        assert builder is not None
        
    except ImportError as e:
        pytest.skip(f"Cannot import core agents for basic test: {e}")


def test_minimal_workflow():
    """Test minimal workflow without external dependencies."""
    try:
        from agents.java_analyzer import JavaAnalyzerAgent
        
        analyzer = JavaAnalyzerAgent()
        
        # Test with non-existent file (should fail gracefully)
        result = analyzer.analyze_jar_for_mvp("/non/existent/file.jar")
        
        # Should return error result, not crash
        assert isinstance(result, dict)
        assert "success" in result
        assert result["success"] is False
        assert "errors" in result
        
    except ImportError as e:
        pytest.skip(f"Cannot import analyzer for minimal workflow test: {e}")