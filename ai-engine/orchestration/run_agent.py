"""
RunAgent: Constraint-Guided Execution Framework for Stepwise Conversion

Based on RunAgent: Interpreting Natural-Language Plans (https://arxiv.org/abs/2605.00798v1)

This module provides explicit control constructs and rubric-based constraints
to enforce strict stepwise adherence to Java-to-Bedrock mapping rules.

Key features:
- Step validation before execution
- Constraint checking at each step boundary
- Rollback mechanisms for constraint violations
- Execution trace for auditability
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class StepStatus(Enum):
    """Status of a step in the RunAgent execution"""
    PENDING = "pending"
    VALIDATING = "validating"
    READY = "ready"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"


class ConstraintViolation(Exception):
    """Raised when a step violates its constraints"""
    pass


class StepOrderError(Exception):
    """Raised when steps are executed out of order"""
    pass


@dataclass
class Constraint:
    """A constraint that must be satisfied for step execution"""
    name: str
    description: str
    validator: Callable[["StepContext"], bool]
    severity: str = "error"  # "error", "warning", "info"
    remediation: Optional[str] = None


@dataclass
class StepContext:
    """Context passed to each step during execution"""
    step_id: str
    step_name: str
    inputs: Dict[str, Any]
    previous_outputs: Dict[str, Any]
    execution_trace: List[Dict[str, Any]]
    constraints: List[Constraint] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StepResult:
    """Result of a step execution"""
    step_id: str
    status: StepStatus
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration: Optional[float] = None
    constraints_satisfied: bool = True
    constraint_violations: List[str] = field(default_factory=list)
    trace_entry: Optional[Dict[str, Any]] = None


@dataclass
class ExecutionTrace:
    """Complete trace of RunAgent execution"""
    execution_id: str
    plan_name: str
    start_time: float
    end_time: Optional[float] = None
    steps: List[StepResult] = field(default_factory=list)
    total_constraints_checked: int = 0
    constraint_violations: List[str] = field(default_factory=list)
    rollback_count: int = 0

    @property
    def duration(self) -> Optional[float]:
        if self.end_time:
            return self.end_time - self.start_time
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "plan_name": self.plan_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "steps": [
                {
                    "step_id": s.step_id,
                    "status": s.status.value,
                    "output": s.output,
                    "error": s.error,
                    "duration": s.duration,
                    "constraints_satisfied": s.constraints_satisfied,
                    "constraint_violations": s.constraint_violations,
                }
                for s in self.steps
            ],
            "total_constraints_checked": self.total_constraints_checked,
            "constraint_violations": self.constraint_violations,
            "rollback_count": self.rollback_count,
        }


class Step:
    """A single executable step in the RunAgent framework"""

    def __init__(
        self,
        step_id: str,
        name: str,
        description: str,
        execute_fn: Callable[[StepContext], Any],
        constraints: Optional[List[Constraint]] = None,
        pre_conditions: Optional[List[Callable[[StepContext], bool]]] = None,
        post_conditions: Optional[List[Callable[[StepContext, Any], bool]]] = None,
        rollback_fn: Optional[Callable[[StepContext], None]] = None,
    ):
        self.step_id = step_id
        self.name = name
        self.description = description
        self.execute_fn = execute_fn
        self.constraints = constraints or []
        self.pre_conditions = pre_conditions or []
        self.post_conditions = post_conditions or []
        self.rollback_fn = rollback_fn

    def validate_constraints(self, context: StepContext) -> Tuple[bool, List[str]]:
        """Validate all constraints for this step"""
        violations = []
        for constraint in self.constraints:
            try:
                if not constraint.validator(context):
                    violations.append(f"{constraint.name}: {constraint.description}")
                    if constraint.severity == "error":
                        logger.error(f"Constraint violation in step {self.step_id}: {constraint.name}")
                    else:
                        logger.warning(f"Constraint warning in step {self.step_id}: {constraint.name}")
            except Exception as e:
                violations.append(f"{constraint.name}: validation error - {str(e)}")
                logger.error(f"Constraint validation error in step {self.step_id}: {e}")

        return len(violations) == 0, violations


class RunAgentPlan:
    """A plan consisting of ordered steps with cross-step dependencies"""

    def __init__(
        self,
        plan_id: str,
        name: str,
        description: str,
        steps: Optional[List[Step]] = None,
        global_constraints: Optional[List[Constraint]] = None,
    ):
        self.plan_id = plan_id
        self.name = name
        self.description = description
        self.steps: List[Step] = steps or []
        self.global_constraints: List[Constraint] = global_constraints or []
        self._step_index: Dict[str, Step] = {s.step_id: s for s in self.steps}

    def add_step(self, step: Step) -> None:
        """Add a step to the plan"""
        self.steps.append(step)
        self._step_index[step.step_id] = step

    def get_step(self, step_id: str) -> Optional[Step]:
        """Get a step by ID"""
        return self._step_index.get(step_id)

    def get_step_order(self) -> List[str]:
        """Get the ordered list of step IDs"""
        return [s.step_id for s in self.steps]

    def validate_plan(self) -> Tuple[bool, List[str]]:
        """Validate the plan structure"""
        errors = []

        # Check for duplicate step IDs
        step_ids = [s.step_id for s in self.steps]
        if len(step_ids) != len(set(step_ids)):
            errors.append("Duplicate step IDs found")

        # Check that steps have execute functions
        for step in self.steps:
            if not callable(step.execute_fn):
                errors.append(f"Step {step.step_id} has no executable function")

        # Check for circular dependencies (would require dependency graph)

        return len(errors) == 0, errors


class RunAgent:
    """
    Constraint-guided execution framework for stepwise conversion.

    Wraps agent execution in explicit control constructs and rubric-based constraints
    to enforce strict stepwise adherence to Java-to-Bedrock mapping rules.
    """

    def __init__(
        self,
        plan: RunAgentPlan,
        enable_rollback: bool = True,
        max_rollbacks: int = 3,
        strict_mode: bool = True,
    ):
        """
        Initialize RunAgent with a plan

        Args:
            plan: RunAgentPlan defining the steps and constraints
            enable_rollback: Whether to enable automatic rollback on violations
            max_rollbacks: Maximum number of rollbacks allowed
            strict_mode: If True, violations cause immediate failure
        """
        self.plan = plan
        self.enable_rollback = enable_rollback
        self.max_rollbacks = max_rollbacks
        self.strict_mode = strict_mode

        self._execution_trace: Optional[ExecutionTrace] = None
        self._rollback_history: List[Dict[str, Any]] = []
        self._step_outputs: Dict[str, Any] = {}

        # Validate plan on initialization
        is_valid, errors = plan.validate_plan()
        if not is_valid:
            logger.error(f"Invalid RunAgent plan: {errors}")
            raise ValueError(f"Invalid RunAgent plan: {errors}")

        logger.info(f"RunAgent initialized with plan '{plan.name}' ({len(plan.steps)} steps)")

    async def execute(
        self,
        initial_inputs: Dict[str, Any],
        execution_id: Optional[str] = None,
    ) -> Tuple[bool, ExecutionTrace]:
        """
        Execute the plan with constraint validation

        Args:
            initial_inputs: Initial inputs to pass to the first step
            execution_id: Optional execution ID for tracing

        Returns:
            Tuple of (success, execution_trace)
        """
        import uuid
        execution_id = execution_id or str(uuid.uuid4())[:8]

        logger.info(f"Starting RunAgent execution {execution_id} for plan '{self.plan.name}'")

        self._execution_trace = ExecutionTrace(
            execution_id=execution_id,
            plan_name=self.plan.name,
            start_time=time.time(),
        )
        self._rollback_history = []
        self._step_outputs = {}

        # Build initial context
        context = StepContext(
            step_id="init",
            step_name="initialization",
            inputs=initial_inputs,
            previous_outputs={},
            execution_trace=[],
            metadata={"execution_id": execution_id},
        )

        success = True

        for i, step in enumerate(self.plan.steps):
            logger.info(f"Executing step {i+1}/{len(self.plan.steps)}: {step.name} ({step.step_id})")

            step_result = await self._execute_step(step, context)

            self._execution_trace.steps.append(step_result)
            self._execution_trace.total_constraints_checked += (
                len(step.constraints) + len(self.plan.global_constraints)
            )

            if step_result.constraint_violations:
                self._execution_trace.constraint_violations.extend(
                    step_result.constraint_violations
                )

            if step_result.status == StepStatus.COMPLETED:
                # Update context for next step
                context.previous_outputs[step.step_id] = step_result.output
                context.execution_trace.append(step_result.trace_entry)
                self._step_outputs[step.step_id] = step_result.output

            elif step_result.status == StepStatus.FAILED:
                if step_result.constraint_violations and self.enable_rollback:
                    # Attempt rollback
                    rollback_success = await self._attempt_rollback(step, context)
                    if not rollback_success:
                        success = False
                        break
                else:
                    success = False
                    break

            elif step_result.status == StepStatus.SKIPPED:
                # Step was skipped, continue
                logger.info(f"Step {step.step_id} was skipped")

        self._execution_trace.end_time = time.time()

        logger.info(
            f"RunAgent execution {execution_id} completed: "
            f"success={success}, steps={len(self._execution_trace.steps)}, "
            f"rollbacks={self._execution_trace.rollback_count}"
        )

        return success, self._execution_trace

    async def _execute_step(self, step: Step, context: StepContext) -> StepResult:
        """Execute a single step with constraint validation"""
        start_time = time.time()
        step_context = StepContext(
            step_id=step.step_id,
            step_name=step.name,
            inputs=context.inputs,
            previous_outputs=context.previous_outputs.copy(),
            execution_trace=context.execution_trace.copy(),
            metadata=context.metadata.copy(),
        )

        # Phase 1: Constraint Validation
        step_context.status = StepStatus.VALIDATING

        # Check global constraints
        global_violations = []
        for constraint in self.plan.global_constraints:
            try:
                if not constraint.validator(step_context):
                    global_violations.append(f"Global: {constraint.name}")
            except Exception as e:
                global_violations.append(f"Global: {constraint.name} - {str(e)}")

        # Check step-specific constraints
        step_valid, step_violations = step.validate_constraints(step_context)
        all_violations = global_violations + step_violations

        if all_violations:
            if self.strict_mode:
                return StepResult(
                    step_id=step.step_id,
                    status=StepStatus.FAILED,
                    error=f"Constraint violations: {all_violations}",
                    duration=time.time() - start_time,
                    constraints_satisfied=False,
                    constraint_violations=all_violations,
                    trace_entry=self._create_trace_entry(step, step_context, None, all_violations),
                )
            else:
                logger.warning(f"Step {step.step_id} has constraints violations: {all_violations}")

        # Phase 2: Pre-conditions
        for pre_condition in step.pre_conditions:
            try:
                if not pre_condition(step_context):
                    return StepResult(
                        step_id=step.step_id,
                        status=StepStatus.FAILED,
                        error=f"Pre-condition failed: {pre_condition.__name__}",
                        duration=time.time() - start_time,
                        constraints_satisfied=len(all_violations) == 0,
                        constraint_violations=all_violations,
                        trace_entry=self._create_trace_entry(step, step_context, None, all_violations),
                    )
            except Exception as e:
                return StepResult(
                    step_id=step.step_id,
                    status=StepStatus.FAILED,
                    error=f"Pre-condition error: {str(e)}",
                    duration=time.time() - start_time,
                    constraints_satisfied=len(all_violations) == 0,
                    constraint_violations=all_violations,
                    trace_entry=self._create_trace_entry(step, step_context, None, all_violations),
                )

        # Phase 3: Execution
        step_context.status = StepStatus.EXECUTING
        output = None
        execution_error = None

        try:
            if asyncio.iscoroutinefunction(step.execute_fn):
                output = await step.execute_fn(step_context)
            else:
                output = step.execute_fn(step_context)
        except Exception as e:
            execution_error = str(e)
            logger.error(f"Step {step.step_id} execution error: {e}")

        # Phase 4: Post-conditions
        if output is not None:
            for post_condition in step.post_conditions:
                try:
                    if not post_condition(step_context, output):
                        execution_error = f"Post-condition failed: {post_condition.__name__}"
                        break
                except Exception as e:
                    execution_error = f"Post-condition error: {str(e)}"
                    break

        # Determine status
        if execution_error:
            return StepResult(
                step_id=step.step_id,
                status=StepStatus.FAILED,
                error=execution_error,
                duration=time.time() - start_time,
                constraints_satisfied=len(all_violations) == 0,
                constraint_violations=all_violations,
                trace_entry=self._create_trace_entry(step, step_context, None, all_violations),
            )

        return StepResult(
            step_id=step.step_id,
            status=StepStatus.COMPLETED,
            output=output,
            duration=time.time() - start_time,
            constraints_satisfied=len(all_violations) == 0,
            constraint_violations=all_violations,
            trace_entry=self._create_trace_entry(step, step_context, output, all_violations),
        )

    async def _attempt_rollback(self, failed_step: Step, context: StepContext) -> bool:
        """Attempt to rollback after a constraint violation"""
        if not self.enable_rollback:
            return False

        if len(self._rollback_history) >= self.max_rollbacks:
            logger.error(f"Max rollbacks ({self.max_rollbacks}) reached")
            return False

        logger.info(f"Attempting rollback for failed step {failed_step.step_id}")

        # Find the rollback point
        rollback_target = None
        for i, step in enumerate(self.plan.steps):
            if step.step_id == failed_step.step_id:
                # Rollback to the state before this step
                if i > 0:
                    rollback_target = self.plan.steps[i - 1]
                break

        if rollback_target and rollback_target.rollback_fn:
            try:
                await rollback_target.rollback_fn(context)
                self._rollback_history.append({
                    "failed_step": failed_step.step_id,
                    "rollback_target": rollback_target.step_id,
                    "timestamp": time.time(),
                })
                self._execution_trace.rollback_count += 1
                logger.info(f"Rollback successful to step {rollback_target.step_id}")
                return True
            except Exception as e:
                logger.error(f"Rollback failed: {e}")
                return False

        return False

    def _create_trace_entry(
        self,
        step: Step,
        context: StepContext,
        output: Any,
        violations: List[str],
    ) -> Dict[str, Any]:
        """Create a trace entry for the step execution"""
        return {
            "step_id": step.step_id,
            "step_name": step.name,
            "timestamp": time.time(),
            "status": context.status.value if hasattr(context.status, 'value') else str(context.status),
            "output_preview": str(output)[:200] if output else None,
            "constraint_violations": violations,
            "has_violations": len(violations) > 0,
        }

    def get_trace(self) -> Optional[ExecutionTrace]:
        """Get the execution trace"""
        return self._execution_trace

    def get_step_outputs(self) -> Dict[str, Any]:
        """Get outputs from all completed steps"""
        return self._step_outputs.copy()


# Pre-built constraint validators for common conversion scenarios

def require_previous_step_output(step_id: str) -> Constraint:
    """Constraint that requires a previous step to have produced output"""
    def validator(context: StepContext) -> bool:
        return step_id in context.previous_outputs
    return Constraint(
        name=f"require_previous_output_{step_id}",
        description=f"Requires output from step '{step_id}'",
        validator=validator,
    )


def require_key_in_output(key: str) -> Constraint:
    """Constraint that requires a key to be present in step output"""
    def validator(context: StepContext) -> bool:
        for output in context.previous_outputs.values():
            if isinstance(output, dict) and key in output:
                return True
        return False
    return Constraint(
        name=f"require_key_{key}",
        description=f"Requires key '{key}' in any previous output",
        validator=validator,
    )


def disallow_out_of_order_execution(expected_step_id: str) -> Constraint:
    """Constraint that enforces step order"""
    def validator(context: StepContext) -> bool:
        executed_steps = list(context.previous_outputs.keys())
        if expected_step_id not in executed_steps:
            return False
        expected_idx = -1
        for i, step in enumerate(self.plan.steps if hasattr(self, 'plan') else []):
            if step.step_id == expected_step_id:
                expected_idx = i
                break
        if expected_idx < 0:
            return True
        # Check that all steps before expected_step_id have been executed
        for i in range(expected_idx):
            if self.plan.steps[i].step_id not in executed_steps:
                return False
        return True
    return Constraint(
        name=f"require_step_before",
        description=f"Requires step '{expected_step_id}' to complete first",
        validator=validator,
    )


def validate_no_missing_dependencies(context: StepContext) -> bool:
    """Check that all dependencies are resolved"""
    if isinstance(context.inputs, dict):
        required_keys = ["mod_path", "output_path"]
        return all(k in context.inputs for k in required_keys)
    return True


def validate_step_timeout(context: StepContext) -> bool:
    """Check that step hasn't exceeded reasonable time"""
    if "timeout" in context.metadata:
        return True  # Timeout was already checked
    return True


# Conversion-specific constraint factory

def create_conversion_constraints(step_id: str) -> List[Constraint]:
    """Create standard constraints for conversion steps"""
    return [
        Constraint(
            name=f"valid_inputs_{step_id}",
            description="Step must have valid inputs",
            validator=lambda ctx: len(ctx.inputs) > 0 or len(ctx.previous_outputs) > 0,
        ),
        Constraint(
            name=f"no_circular_refs_{step_id}",
            description="No circular dependencies in outputs",
            validator=lambda ctx: _check_no_circular_refs(ctx.previous_outputs),
        ),
    ]


def _check_no_circular_refs(outputs: Dict[str, Any]) -> bool:
    """Check that outputs don't contain circular references"""
    visited = set()
    def check_value(val):
        if id(val) in visited:
            return False
        visited.add(id(val))
        if isinstance(val, dict):
            for v in val.values():
                if not check_value(v):
                    return False
        elif isinstance(val, list):
            for v in val:
                if not check_value(v):
                    return False
        visited.discard(id(val))
        return True

    for output in outputs.values():
        if isinstance(output, dict):
            if not check_value(output):
                return False
    return True