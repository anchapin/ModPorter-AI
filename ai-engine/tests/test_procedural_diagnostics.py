"""
Unit tests for Procedural Execution Diagnostic Suite

Tests the diagnostic suite that measures whether agents faithfully execute
multi-step conversion procedures without deviation.
"""

import pytest
from typing import Any, Dict, List

from testing.procedural_diagnostics import (
    Deviation,
    DeviationType,
    FidelityMetrics,
    ProcedureAnalyzer,
    ProcedureDefinition,
    ProcedureStep,
    ProcedureTracer,
    ProceduralDiagnosticsSuite,
    StepExecution,
    StepStatus,
)


@pytest.fixture
def conversion_procedure() -> ProcedureDefinition:
    return ProceduralDiagnosticsSuite.create_conversion_procedure()


@pytest.fixture
def tracer(conversion_procedure) -> ProcedureTracer:
    return ProcedureTracer(conversion_procedure)


@pytest.fixture
def analyzer(conversion_procedure) -> ProcedureAnalyzer:
    return ProcedureAnalyzer(conversion_procedure)


@pytest.fixture
def diagnostics_suite() -> ProceduralDiagnosticsSuite:
    return ProceduralDiagnosticsSuite()


class TestProcedureStep:
    def test_procedure_step_creation(self):
        step = ProcedureStep(
            step_id="test_step",
            name="Test Step",
            description="A test procedure step",
        )
        assert step.step_id == "test_step"
        assert step.name == "Test Step"
        assert step.required is True
        assert step.conditional is False

    def test_procedure_step_with_dependencies(self):
        step = ProcedureStep(
            step_id="step_b",
            name="Step B",
            description="Depends on step A",
            expected_dependencies=["step_a"],
        )
        assert "step_a" in step.expected_dependencies


class TestProcedureDefinition:
    def test_procedure_definition_auto_order(self):
        steps = [
            ProcedureStep(step_id="a", name="A", description="First"),
            ProcedureStep(step_id="b", name="B", description="Second"),
        ]
        proc = ProcedureDefinition(
            procedure_id="test",
            name="Test Procedure",
            description="Test",
            steps=steps,
        )
        assert proc.expected_order == ["a", "b"]

    def test_procedure_definition_explicit_order(self):
        steps = [
            ProcedureStep(step_id="a", name="A", description="First"),
            ProcedureStep(step_id="b", name="B", description="Second"),
        ]
        proc = ProcedureDefinition(
            procedure_id="test",
            name="Test Procedure",
            description="Test",
            steps=steps,
            expected_order=["b", "a"],
        )
        assert proc.expected_order == ["b", "a"]


class TestProcedureTracer:
    def test_tracer_initialization(self, tracer, conversion_procedure):
        assert tracer.procedure == conversion_procedure
        assert len(tracer.step_executions) == 0
        tracer.begin_procedure()
        assert len(tracer.step_executions) == len(conversion_procedure.steps)
        assert tracer.execution_order == []

    def test_record_step_start(self, tracer):
        tracer.begin_procedure()
        tracer.record_step_start("analyze")
        assert tracer.step_executions["analyze"].status == StepStatus.IN_PROGRESS
        assert "analyze" in tracer.execution_order

    def test_record_step_completion(self, tracer):
        tracer.begin_procedure()
        tracer.record_step_start("analyze")
        tracer.record_step_completion("analyze", output={"assets": []})
        assert tracer.step_executions["analyze"].status == StepStatus.COMPLETED
        assert tracer.step_executions["analyze"].output == {"assets": []}

    def test_record_step_skip(self, tracer):
        tracer.begin_procedure()
        tracer.record_step_skip("analyze", "Not needed for this mod type")
        assert tracer.step_executions["analyze"].status == StepStatus.SKIPPED
        assert "Not needed" in tracer.step_executions["analyze"].error

    def test_record_step_failure(self, tracer):
        tracer.begin_procedure()
        tracer.record_step_start("analyze")
        tracer.record_step_failure("analyze", "Analysis failed: corrupted JAR")
        assert tracer.step_executions["analyze"].status == StepStatus.FAILED
        assert "corrupted JAR" in tracer.step_executions["analyze"].error

    def test_execution_order_tracking(self, tracer):
        tracer.begin_procedure()
        tracer.record_step_start("analyze")
        tracer.record_step_completion("analyze")
        tracer.record_step_start("plan")
        tracer.record_step_completion("plan")
        assert tracer.execution_order == ["analyze", "plan"]

    def test_get_trace(self, tracer):
        tracer.begin_procedure()
        tracer.record_step_start("analyze")
        tracer.record_step_completion("analyze")
        tracer.end_procedure()
        trace = tracer.get_trace()
        assert "analyze" in trace["execution_order"]
        assert trace["start_time"] is not None
        assert trace["end_time"] is not None


class TestProcedureAnalyzer:
    def test_no_deviations_for_correct_execution(
        self, tracer, analyzer, conversion_procedure
    ):
        tracer.begin_procedure()
        for step in conversion_procedure.steps:
            tracer.record_step_start(step.step_id)
            tracer.record_step_completion(step.step_id)
        tracer.end_procedure()
        deviations = analyzer.analyze(tracer)
        assert len(deviations) == 0

    def test_detect_skipped_required_step(self, tracer, analyzer, conversion_procedure):
        tracer.begin_procedure()
        tracer.record_step_start("analyze")
        tracer.record_step_completion("analyze")
        tracer.record_step_start("plan")
        tracer.record_step_completion("plan")
        tracer.end_procedure()
        deviations = analyzer.analyze(tracer)
        skipped = [d for d in deviations if d.deviation_type == DeviationType.SKIPPED_STEP]
        assert len(skipped) >= 4

    def test_detect_reordered_steps(self, tracer, analyzer):
        procedure = ProcedureDefinition(
            procedure_id="order_test",
            name="Order Test",
            description="Test reordering detection",
            steps=[
                ProcedureStep(
                    step_id="first",
                    name="First",
                    description="Should be first",
                    expected_dependencies=[],
                ),
                ProcedureStep(
                    step_id="second",
                    name="Second",
                    description="Should be second",
                    expected_dependencies=["first"],
                ),
            ],
        )
        tracer2 = ProcedureTracer(procedure)
        tracer2.begin_procedure()
        tracer2.record_step_start("second")
        tracer2.record_step_completion("second")
        tracer2.record_step_start("first")
        tracer2.record_step_completion("first")
        tracer2.end_procedure()
        analyzer2 = ProcedureAnalyzer(procedure)
        deviations = analyzer2.analyze(tracer2)
        reordered = [d for d in deviations if d.deviation_type == DeviationType.REORDERED_STEP]
        assert len(reordered) > 0

    def test_detect_extra_steps(self, tracer, analyzer):
        procedure = ProcedureDefinition(
            procedure_id="extra_test",
            name="Extra Step Test",
            description="Test extra step detection",
            steps=[
                ProcedureStep(step_id="only", name="Only", description="Only step"),
            ],
        )
        tracer2 = ProcedureTracer(procedure)
        tracer2.begin_procedure()
        tracer2.record_step_start("only")
        tracer2.record_step_completion("only")
        tracer2.record_step_start("unexpected")
        tracer2.record_step_completion("unexpected")
        tracer2.end_procedure()
        analyzer2 = ProcedureAnalyzer(procedure)
        deviations = analyzer2.analyze(tracer2)
        extra = [d for d in deviations if d.deviation_type == DeviationType.EXTRA_STEP]
        assert len(extra) == 1
        assert extra[0].step_id == "unexpected"

    def test_detect_partial_step(self, tracer, analyzer):
        procedure = ProcedureDefinition(
            procedure_id="partial_test",
            name="Partial Test",
            description="Test partial step detection",
            steps=[
                ProcedureStep(step_id="start", name="Start", description="Start step"),
            ],
        )
        tracer2 = ProcedureTracer(procedure)
        tracer2.begin_procedure()
        tracer2.record_step_start("start")
        tracer2.end_procedure()
        analyzer2 = ProcedureAnalyzer(procedure)
        deviations = analyzer2.analyze(tracer2)
        partial = [d for d in deviations if d.deviation_type == DeviationType.PARTIAL_STEP]
        assert len(partial) == 1


class TestProceduralDiagnosticsSuite:
    def test_register_procedure(self, diagnostics_suite, conversion_procedure):
        diagnostics_suite.register_procedure(conversion_procedure)
        retrieved = diagnostics_suite.get_procedure(conversion_procedure.procedure_id)
        assert retrieved is not None
        assert retrieved.name == conversion_procedure.name

    def test_start_and_end_tracing(self, diagnostics_suite, conversion_procedure):
        diagnostics_suite.register_procedure(conversion_procedure)
        tracer = diagnostics_suite.start_tracing(conversion_procedure.procedure_id)
        assert tracer is not None
        assert tracer.procedure == conversion_procedure
        ended_tracer = diagnostics_suite.end_tracing(conversion_procedure.procedure_id)
        assert ended_tracer is not None

    def test_analyze_execution(self, diagnostics_suite, conversion_procedure):
        diagnostics_suite.register_procedure(conversion_procedure)
        tracer = diagnostics_suite.start_tracing(conversion_procedure.procedure_id)
        tracer.begin_procedure()
        for step in conversion_procedure.steps:
            tracer.record_step_start(step.step_id)
            tracer.record_step_completion(step.step_id)
        metrics = diagnostics_suite.analyze_execution(conversion_procedure.procedure_id)
        assert metrics is not None
        assert metrics.fidelity_score == 1.0
        assert metrics.completed_steps == len(conversion_procedure.steps)
        assert metrics.skipped_steps == 0

    def test_analyze_with_skipped_steps(self, diagnostics_suite, conversion_procedure):
        diagnostics_suite.register_procedure(conversion_procedure)
        tracer = diagnostics_suite.start_tracing(conversion_procedure.procedure_id)
        tracer.begin_procedure()
        tracer.record_step_start("analyze")
        tracer.record_step_completion("analyze")
        tracer.record_step_start("plan")
        tracer.record_step_completion("plan")
        tracer.record_step_skip("translate", "Not needed")
        tracer.record_step_skip("convert_assets", "No assets in mod")
        metrics = diagnostics_suite.analyze_execution(conversion_procedure.procedure_id)
        assert metrics is not None
        assert metrics.fidelity_score < 1.0
        assert metrics.skipped_steps >= 2

    def test_get_diagnostic_summary(self, diagnostics_suite, conversion_procedure):
        diagnostics_suite.register_procedure(conversion_procedure)
        tracer = diagnostics_suite.start_tracing(conversion_procedure.procedure_id)
        tracer.begin_procedure()
        for step in conversion_procedure.steps:
            tracer.record_step_start(step.step_id)
            tracer.record_step_completion(step.step_id)
        diagnostics_suite.analyze_execution(conversion_procedure.procedure_id)
        summary = diagnostics_suite.get_diagnostic_summary(
            conversion_procedure.procedure_id
        )
        assert summary["total_runs"] == 1
        assert summary["average_fidelity_score"] == 1.0

    def test_generate_report_json(self, diagnostics_suite, conversion_procedure):
        diagnostics_suite.register_procedure(conversion_procedure)
        tracer = diagnostics_suite.start_tracing(conversion_procedure.procedure_id)
        tracer.begin_procedure()
        for step in conversion_procedure.steps:
            tracer.record_step_start(step.step_id)
            tracer.record_step_completion(step.step_id)
        metrics = diagnostics_suite.analyze_execution(conversion_procedure.procedure_id)
        report = diagnostics_suite.generate_report(metrics, format="json")
        assert "procedure_name" in report
        assert "fidelity_score" in report
        assert "deviations" in report

    def test_generate_report_text(self, diagnostics_suite, conversion_procedure):
        diagnostics_suite.register_procedure(conversion_procedure)
        tracer = diagnostics_suite.start_tracing(conversion_procedure.procedure_id)
        tracer.begin_procedure()
        for step in conversion_procedure.steps:
            tracer.record_step_start(step.step_id)
            tracer.record_step_completion(step.step_id)
        metrics = diagnostics_suite.analyze_execution(conversion_procedure.procedure_id)
        report = diagnostics_suite.generate_report(metrics, format="text")
        assert "Fidelity Score" in report
        assert "No deviations" in report

    def test_create_conversion_procedure(self):
        procedure = ProceduralDiagnosticsSuite.create_conversion_procedure()
        assert procedure.procedure_id == "java_to_bedrock_conversion"
        assert len(procedure.steps) == 6
        step_ids = {s.step_id for s in procedure.steps}
        assert "analyze" in step_ids
        assert "plan" in step_ids
        assert "translate" in step_ids
        assert "convert_assets" in step_ids
        assert "package" in step_ids
        assert "validate" in step_ids


class TestFidelityMetrics:
    def test_fidelity_score_calculation_full_execution(self, diagnostics_suite):
        procedure = ProcedureDefinition(
            procedure_id="calc_test",
            name="Calculation Test",
            description="Test fidelity scoring",
            steps=[
                ProcedureStep(step_id="s1", name="Step 1", description="First"),
                ProcedureStep(step_id="s2", name="Step 2", description="Second"),
            ],
        )
        diagnostics_suite.register_procedure(procedure)
        tracer = diagnostics_suite.start_tracing("calc_test")
        tracer.begin_procedure()
        tracer.record_step_start("s1")
        tracer.record_step_completion("s1")
        tracer.record_step_start("s2")
        tracer.record_step_completion("s2")
        metrics = diagnostics_suite.analyze_execution("calc_test")
        assert metrics.fidelity_score == 1.0

    def test_fidelity_score_calculation_with_deviation(self, diagnostics_suite):
        procedure = ProcedureDefinition(
            procedure_id="deviation_test",
            name="Deviation Test",
            description="Test with deviations",
            steps=[
                ProcedureStep(step_id="s1", name="Step 1", description="First"),
                ProcedureStep(step_id="s2", name="Step 2", description="Second"),
                ProcedureStep(step_id="s3", name="Step 3", description="Third"),
            ],
        )
        diagnostics_suite.register_procedure(procedure)
        tracer = diagnostics_suite.start_tracing("deviation_test")
        tracer.begin_procedure()
        tracer.record_step_start("s1")
        tracer.record_step_completion("s1")
        metrics = diagnostics_suite.analyze_execution("deviation_test")
        assert metrics.fidelity_score < 1.0
        assert len(metrics.deviations) > 0


class TestDiagnosticIntegration:
    def test_get_last_metrics(self, diagnostics_suite, conversion_procedure):
        diagnostics_suite.register_procedure(conversion_procedure)
        tracer = diagnostics_suite.start_tracing(conversion_procedure.procedure_id)
        tracer.begin_procedure()
        for step in conversion_procedure.steps:
            tracer.record_step_start(step.step_id)
            tracer.record_step_completion(step.step_id)
        metrics = diagnostics_suite.analyze_execution(conversion_procedure.procedure_id)
        last = diagnostics_suite.get_diagnostic_summary(conversion_procedure.procedure_id)
        assert last["total_runs"] == 1
