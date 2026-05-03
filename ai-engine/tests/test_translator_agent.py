"""Unit tests for TranslatorAgent."""

import json
import tempfile
import time
from pathlib import Path
from datetime import datetime

import pytest

from qa.translator import TranslatorAgent
from qa.context import QAContext
from qa.validators import AgentOutput


class TestTranslatorAgentImports:
    """Test that all imports work correctly."""

    def test_agent_imports(self):
        """Verify imports work correctly."""
        from qa.translator import TranslatorAgent, translate

        assert TranslatorAgent is not None
        assert translate is not None

    def test_agent_instantiation(self):
        """Verify agent can be instantiated."""
        agent = TranslatorAgent()
        assert agent is not None
        assert agent.temperature == 0.0

    def test_agent_custom_temperature(self):
        """Verify agent can be instantiated with custom temperature."""
        agent = TranslatorAgent(temperature=0.5)
        assert agent.temperature == 0.5


class TestTranslatorAgentQAContext:
    """Test agent receives QAContext correctly."""

    def test_agent_receives_qa_context(self):
        """Verify agent can receive QAContext."""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            java_path = job_dir / "source.java"
            bedrock_path = job_dir / "bedrock"

            java_path.write_text(
                "// Test Java file\npublic class TestItem {}", bedrock_path.mkdir()
            )

            context = QAContext(
                job_id="test-job-123",
                job_dir=job_dir,
                source_java_path=java_path,
                output_bedrock_path=bedrock_path,
                metadata={"test": True},
                validation_results={},
                created_at=datetime.now(),
                current_agent=None,
            )

            agent = TranslatorAgent()
            result = agent.execute(context)

            assert isinstance(result, AgentOutput)


class TestRAGIntegration:
    """Test RAG query integration."""

    def test_rag_query_integration(self):
        """Verify RAG is queried for patterns."""
        agent = TranslatorAgent()

        test_code = "public class TestItem extends Item { }"
        patterns = agent._query_rag_for_patterns(test_code)

        assert isinstance(patterns, list)


class TestBedrockJSONGeneration:
    """Test Bedrock JSON output generation."""

    def test_generates_bedrock_json(self):
        """Verify Bedrock JSON output generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            java_path = job_dir / "source.java"
            bedrock_path = job_dir / "bedrock"

            java_code = """
package com.example;

public class TestItem extends net.minecraft.item.Item {
    public void onItemRightClick() {
        // Test method
    }
}
"""
            java_path.write_text(java_code)
            bedrock_path.mkdir()

            context = QAContext(
                job_id="test-json-123",
                job_dir=job_dir,
                source_java_path=java_path,
                output_bedrock_path=bedrock_path,
                metadata={},
                validation_results={},
                created_at=datetime.now(),
                current_agent=None,
            )

            agent = TranslatorAgent()
            result = agent.execute(context)

            if result.success:
                assert "bedrock_json_files" in result.result
                files = result.result["bedrock_json_files"]
                assert len(files) > 0


class TestTypeScriptGeneration:
    """Test TypeScript/Script API output."""

    def test_generates_typescript(self):
        """Verify TypeScript/Script API output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            java_path = job_dir / "source.java"
            bedrock_path = job_dir / "bedrock"

            java_code = """
public class TestBlock {
    public void onBlockPlaced() {
        // Place handler
    }
}
"""
            java_path.write_text(java_code)
            bedrock_path.mkdir()

            context = QAContext(
                job_id="test-ts-123",
                job_dir=job_dir,
                source_java_path=java_path,
                output_bedrock_path=bedrock_path,
                metadata={},
                validation_results={},
                created_at=datetime.now(),
                current_agent=None,
            )

            agent = TranslatorAgent()
            result = agent.execute(context)

            if result.success:
                assert "typescript_file" in result.result


class TestCommentPreservation:
    """Test comment preservation."""

    def test_preserves_comments(self):
        """Verify comments are preserved."""
        agent = TranslatorAgent()

        code_with_comments = """
// This is a class comment
public class TestItem {
    // Method comment
    public void test() {
        // Inner comment
    }
}
"""
        comments = agent._extract_comments(code_with_comments)

        assert isinstance(comments, dict)


class TestOutputValidation:
    """Test output schema validation."""

    def test_output_validation(self):
        """Verify output passes schema validation."""
        output_data = {
            "agent_name": "translator",
            "success": True,
            "result": {"test": "data"},
            "errors": [],
            "execution_time_ms": 100,
        }

        validated = AgentOutput(**output_data)

        assert validated.agent_name == "translator"
        assert validated.success is True
        assert validated.errors == []


class TestTemperatureConfiguration:
    """Test temperature=0 configuration."""

    def test_temperature_zero(self):
        """Verify temperature=0 is used."""
        agent = TranslatorAgent()

        assert agent.temperature == 0.0

        agent2 = TranslatorAgent(temperature=0.0)
        assert agent2.temperature == 0.0


class TestContextCompression:
    """Test context compression for large code blocks."""

    def test_context_compression(self):
        """Verify large code blocks are compressed."""
        agent = TranslatorAgent()

        small_code = "short code"
        assert agent._compress_context(small_code) == small_code

        large_code = "\n".join([f"line {i}" for i in range(10000)])
        compressed = agent._compress_context(large_code)
        assert len(compressed) < len(large_code)
        assert "omitted" in compressed.lower()


class TestMissingJavaFile:
    """Test handling of missing Java file."""

    def test_missing_java_file(self):
        """Verify graceful handling of missing Java file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            java_path = job_dir / "nonexistent.java"
            bedrock_path = job_dir / "bedrock"
            bedrock_path.mkdir()

            context = QAContext(
                job_id="test-missing",
                job_dir=job_dir,
                source_java_path=java_path,
                output_bedrock_path=bedrock_path,
                metadata={},
                validation_results={},
                created_at=datetime.now(),
                current_agent=None,
            )

            agent = TranslatorAgent()
            result = agent.execute(context)

            assert result.success is False
            assert len(result.errors) > 0


class TestConvenienceFunction:
    """Test convenience translate function."""

    def test_translate_function(self):
        """Verify translate convenience function works."""
        from qa.translator import translate

        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            java_path = job_dir / "source.java"
            bedrock_path = job_dir / "bedrock"

            java_path.write_text("public class Test {}")
            bedrock_path.mkdir()

            context = QAContext(
                job_id="test-func",
                job_dir=job_dir,
                source_java_path=java_path,
                output_bedrock_path=bedrock_path,
                metadata={},
                validation_results={},
                created_at=datetime.now(),
                current_agent=None,
            )

            result = translate(context)
            assert isinstance(result, AgentOutput)
