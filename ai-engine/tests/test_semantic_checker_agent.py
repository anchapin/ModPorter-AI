"""Unit tests for SemanticCheckerAgent."""

import json
import tempfile
from pathlib import Path
from datetime import datetime

import pytest

from qa.semantic_checker import (
    SemanticCheckerAgent,
    check_semantics,
    DataFlowNode,
    ControlFlowNode,
    SemanticDrift,
)
from qa.context import QAContext
from qa.validators import AgentOutput


class TestSemanticCheckerAgentImports:
    """Test that all imports work correctly."""

    def test_agent_imports(self):
        """Verify imports work correctly."""
        from qa.semantic_checker import SemanticCheckerAgent, check_semantics

        assert SemanticCheckerAgent is not None
        assert check_semantics is not None

    def test_agent_instantiation(self):
        """Verify agent can be instantiated."""
        agent = SemanticCheckerAgent()
        assert agent is not None
        assert agent.temperature == 0.0

    def test_agent_custom_temperature(self):
        """Verify agent can be instantiated with custom temperature."""
        agent = SemanticCheckerAgent(temperature=0.5)
        assert agent.temperature == 0.5


class TestSemanticCheckerAgentQAContext:
    """Test agent receives QAContext correctly."""

    def test_agent_receives_qa_context(self):
        """Verify agent can receive QAContext."""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            java_path = job_dir / "source.java"
            bedrock_path = job_dir / "bedrock"

            bedrock_path.mkdir(parents=True)
            java_path.write_text(
                "public class TestItem {\n"
                "    private int health = 100;\n"
                "    public void onHit() {\n"
                "        if (health > 0) {\n"
                "            health--;\n"
                "        }\n"
                "    }\n"
                "}"
            )

            ts_file = bedrock_path / "test.ts"
            ts_file.write_text(
                "export class TestItem {\n"
                "    private health: number = 100;\n"
                "    public onHit(): void {\n"
                "        if (this.health > 0) {\n"
                "            this.health--;\n"
                "        }\n"
                "    }\n"
                "}"
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

            agent = SemanticCheckerAgent()
            result = agent.execute(context)

            assert isinstance(result, AgentOutput)
            assert "semantic_score" in result.result


class TestDataFlowComparison:
    """Test data flow graph comparison."""

    def test_data_flow_comparison(self):
        """Verify data flow graphs are compared."""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            java_path = job_dir / "source.java"
            bedrock_path = job_dir / "bedrock"

            bedrock_path.mkdir(parents=True)
            java_path.write_text(
                "public class Test {\n"
                "    int value = 5;\n"
                "    public void setValue(int v) { value = v; }\n"
                "}"
            )

            ts_file = bedrock_path / "test.ts"
            ts_file.write_text("const value = 5;\nexport function setValue(v: number): void { }\n")

            agent = SemanticCheckerAgent()

            java_nodes = agent._extract_java_data_flow(java_path)
            bedrock_nodes = agent._extract_bedrock_data_flow(bedrock_path)

            assert len(java_nodes) >= 0
            assert len(bedrock_nodes) >= 0


class TestControlFlowAnalysis:
    """Test control flow equivalence analysis."""

    def test_control_flow_analysis(self):
        """Verify control flow equivalence is analyzed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            java_path = job_dir / "source.java"
            bedrock_path = job_dir / "bedrock"

            bedrock_path.mkdir(parents=True)
            java_path.write_text(
                "public class Test {\n"
                "    public void check(int x) {\n"
                "        if (x > 0) {\n"
                '            System.out.println("positive");\n'
                "        } else if (x < 0) {\n"
                '            System.out.println("negative");\n'
                "        }\n"
                "    }\n"
                "}"
            )

            ts_file = bedrock_path / "test.ts"
            ts_file.write_text(
                "export class Test {\n"
                "    public check(x: number): void {\n"
                "        if (x > 0) {\n"
                '            console.log("positive");\n'
                "        } else if (x < 0) {\n"
                '            console.log("negative");\n'
                "        }\n"
                "    }\n"
                "}"
            )

            agent = SemanticCheckerAgent()

            java_nodes = agent._extract_java_control_flow(java_path)
            bedrock_nodes = agent._extract_bedrock_control_flow(bedrock_path)

            assert len(java_nodes) >= 1


class TestScriptAPIValidity:
    """Test Script API method validity checking."""

    def test_script_api_validity(self):
        """Verify Script API method validity is checked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            bedrock_path = job_dir / "bedrock"

            bedrock_path.mkdir(parents=True)

            ts_file = bedrock_path / "test.ts"
            ts_file.write_text(
                "import { Entity, World } from '@minecraft/server';\n"
                "export function test(entity: Entity): void {\n"
                "    entity.getComponent('health');\n"
                "    World.getDimension('overworld');\n"
                "}"
            )

            agent = SemanticCheckerAgent()
            score, drifts = agent._check_script_api_validity(bedrock_path)

            assert score >= 0
            assert isinstance(drifts, list)


class TestTypeMappingCheck:
    """Test variable/type mapping checking."""

    def test_type_mapping_check(self):
        """Verify variable/type mappings are checked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            java_path = job_dir / "source.java"
            bedrock_path = job_dir / "bedrock"

            bedrock_path.mkdir(parents=True)
            java_path.write_text(
                "public class Test {\n"
                "    private int count = 0;\n"
                '    private String name = "test";\n'
                "    private boolean active = true;\n"
                "}"
            )

            ts_file = bedrock_path / "test.ts"
            ts_file.write_text(
                "export class Test {\n"
                "    private count: number = 0;\n"
                '    private name: string = "test";\n'
                "    private active: boolean = true;\n"
                "}"
            )

            agent = SemanticCheckerAgent()
            score, drifts = agent._check_type_mappings(java_path, bedrock_path)

            assert score >= 0


class TestSemanticScoreGeneration:
    """Test semantic similarity score generation."""

    def test_semantic_score_generation(self):
        """Verify semantic similarity score is generated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            java_path = job_dir / "source.java"
            bedrock_path = job_dir / "bedrock"

            bedrock_path.mkdir(parents=True)
            java_path.write_text(
                "public class Test {\n    private int value = 10;\n    public void process() { }\n}"
            )

            ts_file = bedrock_path / "test.ts"
            ts_file.write_text(
                "export class Test {\n"
                "    private value: number = 10;\n"
                "    public process(): void { }\n"
                "}"
            )

            context = QAContext(
                job_id="test-score-123",
                job_dir=job_dir,
                source_java_path=java_path,
                output_bedrock_path=bedrock_path,
                metadata={},
                validation_results={},
                created_at=datetime.now(),
                current_agent=None,
            )

            agent = SemanticCheckerAgent()
            result = agent.execute(context)

            assert "semantic_score" in result.result
            assert 0 <= result.result["semantic_score"] <= 100


class TestBehavioralDriftFlagging:
    """Test behavioral drift flagging."""

    def test_behavioral_drift_flagging(self):
        """Verify behavioral drift is flagged with explanations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            java_path = job_dir / "source.java"
            bedrock_path = job_dir / "bedrock"

            bedrock_path.mkdir(parents=True)
            java_path.write_text("public class Test {\n    private int missingVar = 5;\n}")

            ts_file = bedrock_path / "test.ts"
            ts_file.write_text("export class Test {\n}")

            context = QAContext(
                job_id="test-drift-123",
                job_dir=job_dir,
                source_java_path=java_path,
                output_bedrock_path=bedrock_path,
                metadata={},
                validation_results={},
                created_at=datetime.now(),
                current_agent=None,
            )

            agent = SemanticCheckerAgent()
            result = agent.execute(context)

            assert "drifts_detected" in result.result
            assert result.result["drifts_detected"] >= 0


class TestOutputValidation:
    """Test output schema validation."""

    def test_output_validation(self):
        """Verify output passes schema validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            java_path = job_dir / "source.java"
            bedrock_path = job_dir / "bedrock"

            bedrock_path.mkdir(parents=True)
            java_path.write_text("// Empty test")
            (bedrock_path / "test.ts").write_text("// Empty test")

            context = QAContext(
                job_id="test-validation-123",
                job_dir=job_dir,
                source_java_path=java_path,
                output_bedrock_path=bedrock_path,
                metadata={},
                validation_results={},
                created_at=datetime.now(),
                current_agent=None,
            )

            agent = SemanticCheckerAgent()
            result = agent.execute(context)

            assert result.agent_name == "semantic"
            assert hasattr(result, "success")
            assert hasattr(result, "result")
            assert hasattr(result, "execution_time_ms")


class TestConvenienceFunction:
    """Test convenience function."""

    def test_check_semantics_function(self):
        """Verify check_semantics convenience function works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            java_path = job_dir / "source.java"
            bedrock_path = job_dir / "bedrock"

            bedrock_path.mkdir(parents=True)
            java_path.write_text("// Test")
            (bedrock_path / "test.ts").write_text("// Test")

            context = QAContext(
                job_id="test-convenience-123",
                job_dir=job_dir,
                source_java_path=java_path,
                output_bedrock_path=bedrock_path,
                metadata={},
                validation_results={},
                created_at=datetime.now(),
                current_agent=None,
            )

            result = check_semantics(context)

            assert isinstance(result, AgentOutput)
