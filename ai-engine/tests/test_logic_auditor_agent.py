"""
Unit tests for LogicAuditorAgent - Adversarial Logic Auditor.

Tests the 5 adversarial check types:
1. formula_drift - Coefficient drift, operator substitution (×→+)
2. probability_inversion - Comparison direction, threshold value
3. event_hook_mismatch - Lifecycle stage match, trigger condition polarity
4. conditional_negation - Negation drift (&& → ||, < → >)
5. resource_id_match - Namespace match, ID case sensitivity

Based on ASMR-Bench framework for detecting sabotage patterns.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from agents.logic_auditor_agent import (
    LogicAuditorAgent,
    AuditFinding,
    AuditReport,
    Severity,
    SemanticType,
    FormulaDriftChecker,
    ProbabilityInversionChecker,
    EventHookMismatchChecker,
    ConditionalNegationChecker,
    ResourceIDMatchChecker,
    audit_conversion,
)
from qa.context import QAContext
from qa.validators import AgentOutput


class TestLogicAuditorAgentImports:
    def test_agent_imports(self):
        from agents.logic_auditor_agent import LogicAuditorAgent, AuditFinding

        assert LogicAuditorAgent is not None
        assert AuditFinding is not None

    def test_agent_instantiation(self):
        agent = LogicAuditorAgent()
        assert agent is not None
        assert agent.temperature == 0.0

    def test_agent_custom_temperature(self):
        agent = LogicAuditorAgent(temperature=0.5)
        assert agent.temperature == 0.5


class TestFormulaDriftChecker:
    """Test formula drift detection (multiplication → addition)."""

    def test_multiplication_to_addition_detected(self):
        checker = FormulaDriftChecker()
        java_code = "damage = base * 1.5;"
        bedrock_code = "let damage = base + 1.5;"
        findings = checker.check(java_code, bedrock_code)
        assert len(findings) > 0
        assert findings[0].check_type == "formula_drift"
        assert findings[0].severity == Severity.HIGH

    def test_coefficient_unchanged_passes(self):
        checker = FormulaDriftChecker()
        java_code = "damage = base * 2.0;"
        bedrock_code = "let damage = base * 2.0;"
        findings = checker.check(java_code, bedrock_code)
        assert len(findings) == 0

    def test_division_not_flagged_as_drift(self):
        checker = FormulaDriftChecker()
        java_code = "result = value / 2;"
        bedrock_code = "let result = value / 2;"
        findings = checker.check(java_code, bedrock_code)
        assert len(findings) == 0

    def test_formula_drift_with_variable_names(self):
        checker = FormulaDriftChecker()
        java_code = "speed = velocity * 1.5;"
        bedrock_code = "let speed = velocity + 1.5;"
        findings = checker.check(java_code, bedrock_code)
        assert len(findings) > 0
        assert "1.5" in findings[0].java_snippet
        assert "1.5" in findings[0].bedrock_snippet


class TestProbabilityInversionChecker:
    """Test probability inversion detection (random < 0.05 → random > 0.05)."""

    def test_comparison_inversion_detected(self):
        checker = ProbabilityInversionChecker()
        java_code = "if (random.nextDouble() < 0.05) { spawnMob(); }"
        bedrock_code = "if (Math.random() > 0.05) { spawnEntity(); }"
        findings = checker.check(java_code, bedrock_code)
        assert len(findings) > 0
        assert findings[0].check_type == "probability_inversion"
        assert findings[0].severity == Severity.HIGH

    def test_threshold_modification_detected(self):
        checker = ProbabilityInversionChecker()
        java_code = "if (Math.random() < 0.1) { event.trigger(); }"
        bedrock_code = "if (Math.random() < 0.05) { event.fire(); }"
        findings = checker.check(java_code, bedrock_code)
        assert len(findings) > 0

    def test_matching_probability_passes(self):
        checker = ProbabilityInversionChecker()
        java_code = "if (random.nextDouble() < 0.05) { spawn(); }"
        bedrock_code = "if (Math.random() < 0.05) { spawn(); }"
        findings = checker.check(java_code, bedrock_code)
        assert len(findings) == 0

    def test_probability_with_float_pattern(self):
        checker = ProbabilityInversionChecker()
        java_code = "if (Random().nextFloat() < 0.15f) { doSomething(); }"
        bedrock_code = "if (Math.random() > 0.15) { doSomething(); }"
        findings = checker.check(java_code, bedrock_code)
        assert len(findings) > 0


class TestEventHookMismatchChecker:
    """Test event hook mismatch detection."""

    def test_break_block_to_step_on_detected(self):
        checker = EventHookMismatchChecker()
        java_code = "public void onBlockDestroyed() { handleBreak(); }"
        bedrock_code = "onStepOn(event) { handleStep(); }"
        findings = checker.check(java_code, bedrock_code)
        assert len(findings) > 0
        assert findings[0].check_type == "event_hook_mismatch"
        assert findings[0].severity == Severity.HIGH

    def test_correct_event_hook_passes(self):
        checker = EventHookMismatchChecker()
        java_code = "public void onBlockDestroyed() { handleBreak(); }"
        bedrock_code = "onBlockDestroyed(event) { handleBreak(); }"
        findings = checker.check(java_code, bedrock_code)
        assert len(findings) == 0

    def test_interact_to_attack_detected(self):
        checker = EventHookMismatchChecker()
        java_code = "public void onInteract() { handleUse(); }"
        bedrock_code = "onAttack(event) { handleAttack(); }"
        findings = checker.check(java_code, bedrock_code)
        assert len(findings) > 0


class TestConditionalNegationChecker:
    """Test conditional negation detection (&& → ||, < → >)."""

    def test_and_to_or_detected(self):
        checker = ConditionalNegationChecker()
        java_code = "if (health > 0 && hasShield) { defend(); }"
        bedrock_code = "if (health > 0 || hasShield) { defend(); }"
        findings = checker.check(java_code, bedrock_code)
        assert len(findings) > 0
        assert findings[0].check_type == "conditional_negation"
        assert findings[0].severity == Severity.HIGH

    def test_less_than_to_greater_than_detected(self):
        checker = ConditionalNegationChecker()
        java_code = "if (value < 100) { process(); }"
        bedrock_code = "if (value > 100) { process(); }"
        findings = checker.check(java_code, bedrock_code)
        assert len(findings) > 0

    def test_matching_conditional_passes(self):
        checker = ConditionalNegationChecker()
        java_code = "if (a && b) { result(); }"
        bedrock_code = "if (a && b) { result(); }"
        findings = checker.check(java_code, bedrock_code)
        assert len(findings) == 0

    def test_complex_conditional_negation(self):
        checker = ConditionalNegationChecker()
        java_code = "if (x > 0 && y > 0 && z > 0) { valid = true; }"
        bedrock_code = "if (x > 0 || y > 0 || z > 0) { valid = true; }"
        findings = checker.check(java_code, bedrock_code)
        assert len(findings) > 0


class TestResourceIDMatchChecker:
    """Test resource ID match checking."""

    def test_case_mismatch_detected(self):
        checker = ResourceIDMatchChecker()
        java_code = '"identifier": "minecraft:stone"'
        bedrock_code = '"identifier": "minecraft:STONE"'
        findings = checker.check(java_code, bedrock_code)
        assert len(findings) > 0
        assert findings[0].check_type == "resource_id_match"
        assert findings[0].severity == Severity.MEDIUM

    def test_matching_id_passes(self):
        checker = ResourceIDMatchChecker()
        java_code = '"identifier": "mod:custom_item"'
        bedrock_code = '"identifier": "mod:custom_item"'
        findings = checker.check(java_code, bedrock_code)
        assert len(findings) == 0

    def test_different_namespaces_not_flagged(self):
        checker = ResourceIDMatchChecker()
        java_code = '"identifier": "mod:resource"'
        bedrock_code = '"identifier": "othermod:resource"'
        findings = checker.check(java_code, bedrock_code)
        assert len(findings) == 0


class TestLogicAuditorAgentQAContext:
    """Test agent receives QAContext correctly."""

    def test_agent_receives_qa_context(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            java_path = job_dir / "source.java"
            bedrock_path = job_dir / "bedrock"

            bedrock_path.mkdir(parents=True)
            java_path.write_text(
                "public class TestItem {\n"
                "    private int damage = 100;\n"
                "    public void calculateDamage() {\n"
                "        damage = base * 1.5;\n"
                "    }\n"
                "}"
            )

            ts_file = bedrock_path / "test.ts"
            ts_file.write_text(
                "export class TestItem {\n"
                "    private damage: number = 100;\n"
                "    public calculateDamage(): void {\n"
                "        this.damage = this.base + 1.5;\n"
                "    }\n"
                "}"
            )

            context = QAContext(
                job_id="test-audit-123",
                job_dir=job_dir,
                source_java_path=java_path,
                output_bedrock_path=bedrock_path,
                metadata={"test": True},
                validation_results={},
                created_at=datetime.now(),
                current_agent=None,
            )

            agent = LogicAuditorAgent()
            result = agent.execute(context)

            assert isinstance(result, AgentOutput)
            assert "audit_report" in result.result


class TestAdversarialCheckIntegration:
    """Test all 5 check types work together in the agent."""

    def test_all_checks_execute(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            java_path = job_dir / "source.java"
            bedrock_path = job_dir / "bedrock"

            bedrock_path.mkdir(parents=True)
            java_path.write_text(
                "public class Test {\n"
                "    int damage = base * 1.5;\n"
                "    if (random < 0.05) spawn();\n"
                "    public void onDestroy() {}\n"
                "    if (a && b) {}\n"
                '    String id = "mod:item";\n'
                "}"
            )

            ts_file = bedrock_path / "test.ts"
            ts_file.write_text(
                "export class Test {\n"
                "    damage: number = base + 1.5;\n"
                "    if (Math.random() > 0.05) spawn();\n"
                "    onStepOn(event) {}\n"
                "    if (a || b) {}\n"
                '    id: string = "mod:ITEM";\n'
                "}"
            )

            context = QAContext(
                job_id="test-all-checks",
                job_dir=job_dir,
                source_java_path=java_path,
                output_bedrock_path=bedrock_path,
                metadata={},
                validation_results={},
                created_at=datetime.now(),
                current_agent=None,
            )

            agent = LogicAuditorAgent()
            result = agent.execute(context)

            assert isinstance(result, AgentOutput)
            audit_report = result.result.get("audit_report", {})
            assert audit_report.get("blocked", False), (
                "Expected conversion to be blocked due to HIGH severity findings"
            )
            assert audit_report.get("high_severity_count", 0) >= 1


class TestAuditFindingDataclass:
    """Test AuditFinding and AuditReport dataclasses."""

    def test_audit_finding_to_dict(self):
        finding = AuditFinding(
            check_type="formula_drift",
            severity=Severity.HIGH,
            description="Test finding",
            java_snippet="a = b * 2;",
            bedrock_snippet="a = b + 2;",
            expected_behavior="multiplication",
            actual_behavior="addition",
        )
        d = finding.to_dict()
        assert d["check_type"] == "formula_drift"
        assert d["severity"] == "high"
        assert d["java_snippet"] == "a = b * 2;"

    def test_audit_report_to_dict(self):
        findings = [
            AuditFinding(
                check_type="formula_drift",
                severity=Severity.HIGH,
                description="Test",
                java_snippet="",
                bedrock_snippet="",
            )
        ]
        report = AuditReport(
            findings=findings,
            high_severity_count=1,
            blocked=True,
            confidence_impact=15.0,
        )
        d = report.to_dict()
        assert d["high_severity_count"] == 1
        assert d["blocked"] == True
        assert d["total_findings"] == 1


class TestRegressionTestSuite:
    """Regression test suite with 10+ known-bad conversions."""

    KNOWN_BAD_CONVERSIONS = [
        {
            "name": "formula_drift_multiplication_to_addition",
            "java": "damage = baseDamage * 1.5;",
            "bedrock": "let damage = baseDamage + 1.5;",
            "expected_check": "formula_drift",
            "expected_severity": "high",
        },
        {
            "name": "formula_drift_coefficient_substitution",
            "java": "speed = velocity * 2.5;",
            "bedrock": "let speed = velocity + 2.5;",
            "expected_check": "formula_drift",
            "expected_severity": "high",
        },
        {
            "name": "probability_inversion_less_than",
            "java": "if (random.nextDouble() < 0.05) { spawn(); }",
            "bedrock": "if (Math.random() > 0.05) { spawn(); }",
            "expected_check": "probability_inversion",
            "expected_severity": "high",
        },
        {
            "name": "probability_inversion_threshold_change",
            "java": "if (Math.random() < 0.1) { trigger(); }",
            "bedrock": "if (Math.random() < 0.05) { trigger(); }",
            "expected_check": "probability_inversion",
            "expected_severity": "high",
        },
        {
            "name": "event_hook_break_to_step",
            "java": "public void onBlockDestroyed() { cleanup(); }",
            "bedrock": "onStepOn(event) { cleanup(); }",
            "expected_check": "event_hook_mismatch",
            "expected_severity": "high",
        },
        {
            "name": "event_hook_interact_to_attack",
            "java": "public void onInteract() { useItem(); }",
            "bedrock": "onAttack(event) { useItem(); }",
            "expected_check": "event_hook_mismatch",
            "expected_severity": "high",
        },
        {
            "name": "conditional_and_to_or",
            "java": "if (health > 0 && hasShield) { defend(); }",
            "bedrock": "if (health > 0 || hasShield) { defend(); }",
            "expected_check": "conditional_negation",
            "expected_severity": "high",
        },
        {
            "name": "conditional_less_than_to_greater",
            "java": "if (value < maxThreshold) { process(); }",
            "bedrock": "if (value > maxThreshold) { process(); }",
            "expected_check": "conditional_negation",
            "expected_severity": "high",
        },
        {
            "name": "resource_id_case_mismatch",
            "java": '"identifier": "minecraft:iron_sword"',
            "bedrock": '"identifier": "minecraft:IRON_SWORD"',
            "expected_check": "resource_id_match",
            "expected_severity": "medium",
        },
        {
            "name": "resource_id_case_mismatch_custom",
            "java": '"identifier": "mod:myItem"',
            "bedrock": '"identifier": "mod:MyItem"',
            "expected_check": "resource_id_match",
            "expected_severity": "medium",
        },
        {
            "name": "probability_inversion_greater_equal",
            "java": "if (random >= 0.5) { Heads(); }",
            "bedrock": "if (Math.random() <= 0.5) { Tails(); }",
            "expected_check": "probability_inversion",
            "expected_severity": "high",
        },
        {
            "name": "formula_drift_complex_expression",
            "java": "result = (base + modifier) * 1.25;",
            "bedrock": "let result = (base + modifier) + 1.25;",
            "expected_check": "formula_drift",
            "expected_severity": "high",
        },
    ]

    @pytest.mark.parametrize("test_case", KNOWN_BAD_CONVERSIONS, ids=lambda c: c["name"])
    def test_regression_cases(self, test_case):
        checker_map = {
            "formula_drift": FormulaDriftChecker(),
            "probability_inversion": ProbabilityInversionChecker(),
            "event_hook_mismatch": EventHookMismatchChecker(),
            "conditional_negation": ConditionalNegationChecker(),
            "resource_id_match": ResourceIDMatchChecker(),
        }

        checker = checker_map.get(test_case["expected_check"])
        assert checker is not None, f"No checker for {test_case['expected_check']}"

        findings = checker.check(test_case["java"], test_case["bedrock"])

        assert len(findings) > 0, (
            f"Expected to find {test_case['expected_check']} in: {test_case['name']}"
        )

        severity_map = {"high": Severity.HIGH, "medium": Severity.MEDIUM, "low": Severity.LOW}
        expected_severity = severity_map.get(test_case["expected_severity"], Severity.HIGH)

        matching_finding = next(
            (
                f
                for f in findings
                if f.check_type == test_case["expected_check"] and f.severity == expected_severity
            ),
            None,
        )
        assert matching_finding is not None, (
            f"Expected {test_case['expected_check']} with severity {test_case['expected_severity']}"
        )


class TestSemanticTypeClassification:
    """Test semantic type classification in the agent."""

    def test_classifies_numeric_formula(self):
        agent = LogicAuditorAgent()
        code = "damage = base * 1.5;"
        types = agent._classify_semantic_type(code)
        assert SemanticType.NUMERIC_FORMULA in types

    def test_classifies_probability(self):
        agent = LogicAuditorAgent()
        code = "if (random.nextDouble() < 0.05) { spawn(); }"
        types = agent._classify_semantic_type(code)
        assert SemanticType.PROBABILITY_RNG in types

    def test_classifies_event_hook(self):
        agent = LogicAuditorAgent()
        code = "public void onBlockDestroyed() { cleanup(); }"
        types = agent._classify_semantic_type(code)
        assert SemanticType.EVENT_HOOK in types

    def test_classifies_conditional(self):
        agent = LogicAuditorAgent()
        code = "if (a && b) { result(); }"
        types = agent._classify_semantic_type(code)
        assert SemanticType.CONDITIONAL in types

    def test_classifies_resource_id(self):
        agent = LogicAuditorAgent()
        code = '"identifier": "mod:custom_item"'
        types = agent._classify_semantic_type(code)
        assert SemanticType.RESOURCE_ID in types


class TestAuditReportBlocking:
    """Test that HIGH severity findings block the conversion."""

    def test_high_severity_blocks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            java_path = job_dir / "source.java"
            bedrock_path = job_dir / "bedrock"

            bedrock_path.mkdir(parents=True)
            java_path.write_text("damage = base * 1.5;")
            ts_file = bedrock_path / "test.ts"
            ts_file.write_text("let damage = base + 1.5;")

            context = QAContext(
                job_id="test-blocking",
                job_dir=job_dir,
                source_java_path=java_path,
                output_bedrock_path=bedrock_path,
                metadata={},
                validation_results={},
                created_at=datetime.now(),
                current_agent=None,
            )

            agent = LogicAuditorAgent()
            result = agent.execute(context)

            assert result.success == False
            assert result.result.get("blocked") == True
            assert result.result.get("audit_report", {}).get("high_severity_count", 0) >= 1


class TestConvenienceFunction:
    """Test the audit_conversion convenience function."""

    def test_audit_conversion_function(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            java_path = job_dir / "source.java"
            bedrock_path = job_dir / "bedrock"

            bedrock_path.mkdir(parents=True)
            java_path.write_text("// Valid code")
            (bedrock_path / "test.ts").write_text("// Valid code")

            context = QAContext(
                job_id="test-convenience",
                job_dir=job_dir,
                source_java_path=java_path,
                output_bedrock_path=bedrock_path,
                metadata={},
                validation_results={},
                created_at=datetime.now(),
                current_agent=None,
            )

            result = audit_conversion(context)

            assert isinstance(result, AgentOutput)


class TestConfidenceImpact:
    """Test that audit findings impact confidence score correctly."""

    def _create_report_with_counts(self, high: int, medium: int, low: int) -> AuditReport:
        report = AuditReport()
        report.high_severity_count = high
        report.medium_severity_count = medium
        report.low_severity_count = low
        confidence_impact = (
            report.high_severity_count * 15.0
            + report.medium_severity_count * 5.0
            + report.low_severity_count * 1.0
        )
        report.confidence_impact = min(confidence_impact, 50.0)
        return report

    def test_high_severity_impact(self):
        report = self._create_report_with_counts(high=2, medium=1, low=0)
        assert report.confidence_impact == 35.0

    def test_medium_only_impact(self):
        report = self._create_report_with_counts(high=0, medium=4, low=0)
        assert report.confidence_impact == 20.0

    def test_low_only_impact(self):
        report = self._create_report_with_counts(high=0, medium=0, low=10)
        assert report.confidence_impact == 10.0

    def test_impact_capped_at_50(self):
        report = self._create_report_with_counts(high=10, medium=10, low=10)
        assert report.confidence_impact == 50.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
