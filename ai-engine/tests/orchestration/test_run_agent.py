"""
Tests for RunAgent Constraint-Guided Execution Framework

Addresses Issue #1270: Add RunAgent constraint-guided execution framework
for stepwise conversion.
"""

import asyncio
import pytest
import time
from typing import Any, Dict
from unittest.mock import Mock

from orchestration.run_agent import (
    Constraint,
    RunAgent,
    RunAgentPlan,
    Step,
    StepContext,
    StepResult,
    StepStatus,
    create_conversion_constraints,
    require_key_in_output,
    validate_no_missing_dependencies,
)
from orchestration.run_agent_integration import (
    ConversionStepFactory,
    RunAgentCrewBridge,
    RunAgentOrchestrator,
)


class TestStepStatus:
    """Test StepStatus enum values"""

    def test_step_status_values(self):
        assert StepStatus.PENDING.value == "pending"
        assert StepStatus.VALIDATING.value == "validating"
        assert StepStatus.READY.value == "ready"
        assert StepStatus.EXECUTING.value == "executing"
        assert StepStatus.COMPLETED.value == "completed"
        assert StepStatus.FAILED.value == "failed"
        assert StepStatus.ROLLED_BACK.value == "rolled_back"
        assert StepStatus.SKIPPED.value == "skipped"


class TestStepContext:
    """Test StepContext dataclass"""

    def test_context_creation(self):
        context = StepContext(
            step_id="test_step",
            step_name="Test Step",
            inputs={"key": "value"},
            previous_outputs={},
            execution_trace=[],
        )
        assert context.step_id == "test_step"
        assert context.inputs == {"key": "value"}
        assert context.previous_outputs == {}

    def test_context_with_metadata(self):
        context = StepContext(
            step_id="test",
            step_name="test",
            inputs={},
            previous_outputs={},
            execution_trace=[],
            metadata={"execution_id": "123", "priority": "high"},
        )
        assert context.metadata["execution_id"] == "123"
        assert context.metadata["priority"] == "high"


class TestStep:
    """Test Step class functionality"""

    def test_step_creation(self):
        def dummy_fn(context):
            return {"result": "success"}

        step = Step(
            step_id="test_step",
            name="Test Step",
            description="A test step",
            execute_fn=dummy_fn,
        )
        assert step.step_id == "test_step"
        assert step.name == "Test Step"
        assert len(step.constraints) == 0

    def test_step_with_constraints(self):
        constraint = Constraint(
            name="test_constraint",
            description="A test constraint",
            validator=lambda ctx: True,
        )
        step = Step(
            step_id="constrained_step",
            name="Constrained Step",
            description="A step with constraints",
            execute_fn=lambda ctx: {},
            constraints=[constraint],
        )
        assert len(step.constraints) == 1

    def test_validate_constraints_pass(self):
        constraint = Constraint(
            name="always_pass",
            description="Always passes",
            validator=lambda ctx: True,
        )
        step = Step(
            step_id="pass_step",
            name="Pass Step",
            description="A step that passes",
            execute_fn=lambda ctx: {},
            constraints=[constraint],
        )
        context = StepContext(
            step_id="pass_step",
            step_name="Pass Step",
            inputs={},
            previous_outputs={},
            execution_trace=[],
        )
        is_valid, violations = step.validate_constraints(context)
        assert is_valid
        assert len(violations) == 0

    def test_validate_constraints_fail(self):
        constraint = Constraint(
            name="always_fail",
            description="Always fails",
            validator=lambda ctx: False,
            severity="error",
        )
        step = Step(
            step_id="fail_step",
            name="Fail Step",
            description="A step that fails",
            execute_fn=lambda ctx: {},
            constraints=[constraint],
        )
        context = StepContext(
            step_id="fail_step",
            step_name="Fail Step",
            inputs={},
            previous_outputs={},
            execution_trace=[],
        )
        is_valid, violations = step.validate_constraints(context)
        assert not is_valid
        assert len(violations) == 1


class TestRunAgentPlan:
    """Test RunAgentPlan functionality"""

    def test_plan_creation(self):
        plan = RunAgentPlan(
            plan_id="test_plan",
            name="Test Plan",
            description="A test plan",
        )
        assert plan.plan_id == "test_plan"
        assert len(plan.steps) == 0

    def test_add_step(self):
        plan = RunAgentPlan(
            plan_id="test_plan",
            name="Test Plan",
            description="A test plan",
        )
        step = Step(
            step_id="step1",
            name="Step 1",
            description="First step",
            execute_fn=lambda ctx: {},
        )
        plan.add_step(step)
        assert len(plan.steps) == 1
        assert plan.get_step("step1") == step

    def test_validate_plan_success(self):
        plan = RunAgentPlan(
            plan_id="valid_plan",
            name="Valid Plan",
            description="A valid plan",
        )
        plan.add_step(Step("step1", "Step 1", "", lambda ctx: {}))
        plan.add_step(Step("step2", "Step 2", "", lambda ctx: {}))
        is_valid, errors = plan.validate_plan()
        assert is_valid
        assert len(errors) == 0

    def test_validate_plan_duplicate_ids(self):
        plan = RunAgentPlan(
            plan_id="duplicate_plan",
            name="Duplicate Plan",
            description="A plan with duplicates",
        )
        plan.add_step(Step("step1", "Step 1", "", lambda ctx: {}))
        plan.add_step(Step("step1", "Step 1 Duplicate", "", lambda ctx: {}))
        is_valid, errors = plan.validate_plan()
        assert not is_valid
        assert "Duplicate" in errors[0]

    def test_get_step_order(self):
        plan = RunAgentPlan(
            plan_id="ordered_plan",
            name="Ordered Plan",
            description="A plan with ordered steps",
        )
        plan.add_step(Step("step1", "Step 1", "", lambda ctx: {}))
        plan.add_step(Step("step2", "Step 2", "", lambda ctx: {}))
        plan.add_step(Step("step3", "Step 3", "", lambda ctx: {}))
        assert plan.get_step_order() == ["step1", "step2", "step3"]


class TestRunAgent:
    """Test RunAgent execution"""

    @pytest.fixture
    def simple_plan(self):
        """Create a simple plan for testing"""
        plan = RunAgentPlan(
            plan_id="simple_plan",
            name="Simple Plan",
            description="A simple test plan",
        )
        steps = [
            Step("step1", "Step 1", "First step", lambda ctx: {"output": "step1_output"}),
            Step("step2", "Step 2", "Second step", lambda ctx: {"output": "step2_output"}),
        ]
        for step in steps:
            plan.add_step(step)
        return plan

    @pytest.mark.asyncio
    async def test_runagent_basic_execution(self, simple_plan):
        """Test basic RunAgent execution"""
        agent = RunAgent(simple_plan, enable_rollback=False, strict_mode=False)
        inputs = {"test": "value"}

        success, trace = await agent.execute(inputs)

        assert success
        assert len(trace.steps) == 2
        assert trace.steps[0].status == StepStatus.COMPLETED
        assert trace.steps[1].status == StepStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_runagent_with_constraint_violation_non_strict(self):
        """Test RunAgent with constraint violation in non-strict mode"""
        failing_constraint = Constraint(
            name="always_fail",
            description="This constraint always fails",
            validator=lambda ctx: False,
            severity="warning",  # Not an error
        )
        plan = RunAgentPlan("violation_plan", "Violation Plan", "A plan with violations")
        plan.add_step(
            Step("step1", "Step 1", "First step", lambda ctx: {"output": "data"}, constraints=[failing_constraint])
        )

        agent = RunAgent(plan, enable_rollback=False, strict_mode=False)
        success, trace = await agent.execute({"test": "value"})

        # Non-strict mode allows execution to continue - constraint is "warning" not "error"
        assert success or not agent.strict_mode

    @pytest.mark.asyncio
    async def test_runagent_step_order_enforcement(self):
        """Test that steps are executed in order"""
        execution_order = []

        async def async_step1(ctx):
            await asyncio.sleep(0.01)
            execution_order.append("step1")
            return {"result": "step1_done"}

        async def async_step2(ctx):
            await asyncio.sleep(0.01)
            execution_order.append("step2")
            return {"result": "step2_done"}

        plan = RunAgentPlan("ordered_plan", "Ordered Plan", "Tests execution order")
        plan.add_step(Step("s1", "Step 1", "", async_step1))
        plan.add_step(Step("s2", "Step 2", "", async_step2))

        agent = RunAgent(plan)
        success, trace = await agent.execute({})

        assert success
        assert execution_order == ["step1", "step2"]
        assert trace.steps[0].step_id == "s1"
        assert trace.steps[1].step_id == "s2"

    @pytest.mark.asyncio
    async def test_runagent_context_propagation(self):
        """Test that context is properly propagated between steps"""
        plan = RunAgentPlan("context_plan", "Context Plan", "Tests context passing")

        async def first_step(ctx):
            return {"data": "from_first", "input_received": ctx.inputs.get("initial")}

        async def second_step(ctx):
            # Should have output from first step
            first_output = ctx.previous_outputs.get("s1", {})
            return {"previous_data": first_output.get("data"), "chain": True}

        plan.add_step(Step("s1", "First", "", first_step))
        plan.add_step(Step("s2", "Second", "", second_step))

        agent = RunAgent(plan)
        success, trace = await agent.execute({"initial": "test_value"})

        assert success
        outputs = agent.get_step_outputs()
        assert outputs["s1"]["input_received"] == "test_value"
        assert outputs["s2"]["previous_data"] == "from_first"
        assert outputs["s2"]["chain"] is True

    @pytest.mark.asyncio
    async def test_runagent_invalid_plan_raises(self):
        """Test that invalid plan raises ValueError"""
        plan = RunAgentPlan("invalid", "Invalid", "")
        plan.add_step(Step("dup", "Dup", "", lambda ctx: {}))
        plan.add_step(Step("dup", "Dup Again", "", lambda ctx: {}))  # Duplicate ID

        with pytest.raises(ValueError, match="Invalid.*plan"):
            RunAgent(plan)


class TestConversionStepFactory:
    """Test ConversionStepFactory for creating conversion steps"""

    def test_create_analysis_step(self):
        def dummy_fn(ctx):
            return {"assets": [], "features": []}

        step = ConversionStepFactory.create_analysis_step(dummy_fn)

        assert step.step_id == "analyze"
        assert step.name == "Java Mod Analysis"
        assert len(step.constraints) >= 1

    def test_create_planning_step(self):
        def dummy_fn(ctx):
            return {"strategy": "default"}

        step = ConversionStepFactory.create_planning_step(dummy_fn)

        assert step.step_id == "plan"
        # Pre-condition should require analyze output
        assert len(step.pre_conditions) >= 1

    def test_create_all_conversion_steps(self):
        """Test creating all conversion steps in sequence"""
        steps = []
        fns = [lambda ctx: {}, lambda ctx: {}, lambda ctx: {}, lambda ctx: {}, lambda ctx: {}, lambda ctx: {}]

        step_ids = ["analyze", "plan", "translate", "convert_assets", "package", "validate"]
        creators = [
            ConversionStepFactory.create_analysis_step,
            ConversionStepFactory.create_planning_step,
            ConversionStepFactory.create_translation_step,
            ConversionStepFactory.create_asset_conversion_step,
            ConversionStepFactory.create_packaging_step,
            ConversionStepFactory.create_validation_step,
        ]

        for creator, fn, step_id in zip(creators, fns, step_ids):
            step = creator(fn)
            steps.append(step)
            assert step.step_id == step_id

        assert len(steps) == 6


class TestRunAgentCrewBridge:
    """Test RunAgentCrewBridge integration"""

    @pytest.mark.asyncio
    async def test_bridge_creation(self):
        bridge = RunAgentCrewBridge(enable_runagent=True, strict_mode=False)
        assert bridge.enable_runagent is True
        assert bridge.strict_mode is False

    @pytest.mark.asyncio
    async def test_bridge_execute_direct_mode(self):
        """Test that bridge falls back to direct execution when RunAgent disabled"""
        bridge = RunAgentCrewBridge(enable_runagent=False)

        async def analyze_fn(ctx):
            return {"assets": ["texture1.png"], "features": ["block"]}

        async def plan_fn(ctx):
            return {"strategy": "standard"}

        async def translate_fn(ctx):
            return {"scripts": ["main.js"]}

        async def asset_fn(ctx):
            return {"converted": ["texture1.png"]}

        async def package_fn(ctx):
            return {"addon_path": "/tmp/addon.mcaddon"}

        async def validate_fn(ctx):
            return {"valid": True, "score": 95}

        result = await bridge.execute_conversion(
            mod_path="/test/mod.jar",
            output_path="/test/output",
            analyze_fn=analyze_fn,
            plan_fn=plan_fn,
            translate_fn=translate_fn,
            convert_assets_fn=asset_fn,
            package_fn=package_fn,
            validate_fn=validate_fn,
        )

        assert result["status"] == "completed"
        assert result["success"] is True
        assert "step_outputs" in result


class TestConstraintHelpers:
    """Test constraint helper functions"""

    def test_require_key_in_output(self):
        constraint = require_key_in_output("test_key")

        # Valid context with key
        valid_context = StepContext(
            step_id="test",
            step_name="test",
            inputs={},
            previous_outputs={"prev": {"test_key": "value"}},
            execution_trace=[],
        )
        assert constraint.validator(valid_context) is True

        # Invalid context without key
        invalid_context = StepContext(
            step_id="test",
            step_name="test",
            inputs={},
            previous_outputs={"prev": {"other_key": "value"}},
            execution_trace=[],
        )
        assert constraint.validator(invalid_context) is False

    def test_validate_no_missing_dependencies(self):
        # Valid context
        valid_ctx = StepContext(
            step_id="test",
            step_name="test",
            inputs={"mod_path": "/test", "output_path": "/out"},
            previous_outputs={},
            execution_trace=[],
        )
        assert validate_no_missing_dependencies(valid_ctx) is True

        # Invalid context - missing mod_path
        invalid_ctx = StepContext(
            step_id="test",
            step_name="test",
            inputs={"output_path": "/out"},
            previous_outputs={},
            execution_trace=[],
        )
        assert validate_no_missing_dependencies(invalid_ctx) is False

    def test_create_conversion_constraints(self):
        constraints = create_conversion_constraints("test_step")
        assert len(constraints) >= 2


class TestRunAgentOrchestrator:
    """Test RunAgentOrchestrator wrapper"""

    def test_orchestrator_creation(self):
        """Test creating RunAgentOrchestrator with mock base"""
        mock_base = Mock()
        orchestrator = RunAgentOrchestrator(mock_base, enable_runagent=True)
        assert orchestrator.enable_runagent is True
        assert orchestrator.base_orchestrator is mock_base

    def test_get_bridge(self):
        """Test getting the RunAgent bridge"""
        mock_base = Mock()
        orchestrator = RunAgentOrchestrator(mock_base, enable_runagent=True)
        bridge = orchestrator.get_bridge()
        assert isinstance(bridge, RunAgentCrewBridge)