"""
RunAgent Integration with CrewAI Conversion System

This module integrates the RunAgent constraint-guided execution framework
with the existing multi-agent conversion pipeline.
"""

import logging
from typing import Any, Dict, Optional

from .run_agent import (
    Constraint,
    RunAgent,
    RunAgentPlan,
    Step,
    StepContext,
    validate_no_missing_dependencies,
)

logger = logging.getLogger(__name__)


class ConversionStepFactory:
    """Factory for creating conversion workflow steps with proper constraints"""

    @staticmethod
    def create_analysis_step(
        execute_fn: callable,
        rollback_fn: Optional[callable] = None,
    ) -> Step:
        """Create the Java mod analysis step"""
        constraints = [
            Constraint(
                name="valid_mod_path",
                description="Mod path must be provided and exist",
                validator=lambda ctx: "mod_path" in ctx.inputs and ctx.inputs["mod_path"],
            ),
            Constraint(
                name="no_previous_outputs",
                description="Analysis must be first - no previous outputs allowed",
                validator=lambda ctx: len(ctx.previous_outputs) == 0,
            ),
        ]
        return Step(
            step_id="analyze",
            name="Java Mod Analysis",
            description="Analyze Java mod structure, dependencies, and features",
            execute_fn=execute_fn,
            constraints=constraints,
            rollback_fn=rollback_fn,
        )

    @staticmethod
    def create_planning_step(
        execute_fn: callable,
        rollback_fn: Optional[callable] = None,
    ) -> Step:
        """Create the conversion planning step"""
        constraints = [
            Constraint(
                name="requires_analysis_output",
                description="Must have analysis output from previous step",
                validator=lambda ctx: "analyze" in ctx.previous_outputs,
            ),
            Constraint(
                name="has_conversion_targets",
                description="Must have features identified for conversion",
                validator=lambda ctx: _check_has_features(ctx.previous_outputs.get("analyze")),
            ),
        ]

        def pre_condition(ctx: StepContext) -> bool:
            return "analyze" in ctx.previous_outputs

        return Step(
            step_id="plan",
            name="Conversion Planning",
            description="Design conversion strategy with smart assumptions",
            execute_fn=execute_fn,
            constraints=constraints,
            pre_conditions=[pre_condition],
            rollback_fn=rollback_fn,
        )

    @staticmethod
    def create_translation_step(
        execute_fn: callable,
        rollback_fn: Optional[callable] = None,
    ) -> Step:
        """Create the code translation step"""
        constraints = [
            Constraint(
                name="requires_plan_output",
                description="Must have planning output from previous step",
                validator=lambda ctx: "plan" in ctx.previous_outputs,
            ),
            Constraint(
                name="conversion_plan_valid",
                description="Conversion plan must be valid and complete",
                validator=lambda ctx: _check_plan_valid(ctx.previous_outputs.get("plan")),
            ),
        ]

        def pre_condition(ctx: StepContext) -> bool:
            return "plan" in ctx.previous_outputs

        return Step(
            step_id="translate",
            name="Code Translation",
            description="Convert Java code to Bedrock JavaScript",
            execute_fn=execute_fn,
            constraints=constraints,
            pre_conditions=[pre_condition],
            rollback_fn=rollback_fn,
        )

    @staticmethod
    def create_asset_conversion_step(
        execute_fn: callable,
        rollback_fn: Optional[callable] = None,
    ) -> Step:
        """Create the asset conversion step"""
        constraints = [
            Constraint(
                name="requires_analysis_for_assets",
                description="Must have analysis for asset requirements",
                validator=lambda ctx: "analyze" in ctx.previous_outputs,
            ),
            Constraint(
                name="plan_specifies_assets",
                description="Plan must specify asset conversion strategy",
                validator=lambda ctx: _check_has_asset_plan(ctx.previous_outputs.get("plan")),
            ),
        ]

        def pre_condition(ctx: StepContext) -> bool:
            return "analyze" in ctx.previous_outputs

        return Step(
            step_id="convert_assets",
            name="Asset Conversion",
            description="Convert textures, models, and audio assets",
            execute_fn=execute_fn,
            constraints=constraints,
            pre_conditions=[pre_condition],
            rollback_fn=rollback_fn,
        )

    @staticmethod
    def create_packaging_step(
        execute_fn: callable,
        rollback_fn: Optional[callable] = None,
    ) -> Step:
        """Create the packaging step"""
        constraints = [
            Constraint(
                name="requires_translation_output",
                description="Must have translated code from previous step",
                validator=lambda ctx: "translate" in ctx.previous_outputs,
            ),
            Constraint(
                name="requires_asset_output",
                description="Must have converted assets from previous step",
                validator=lambda ctx: "convert_assets" in ctx.previous_outputs,
            ),
            Constraint(
                name="has_valid_structure",
                description="All components must be ready for packaging",
                validator=lambda ctx: _check_components_ready(ctx.previous_outputs),
            ),
        ]

        def pre_condition(ctx: StepContext) -> bool:
            return "translate" in ctx.previous_outputs and "convert_assets" in ctx.previous_outputs

        return Step(
            step_id="package",
            name="Package Assembly",
            description="Assemble converted components into .mcaddon",
            execute_fn=execute_fn,
            constraints=constraints,
            pre_conditions=[pre_condition],
            rollback_fn=rollback_fn,
        )

    @staticmethod
    def create_validation_step(
        execute_fn: callable,
        rollback_fn: Optional[callable] = None,
    ) -> Step:
        """Create the QA validation step"""
        constraints = [
            Constraint(
                name="requires_packaged_output",
                description="Must have packaged addon from previous step",
                validator=lambda ctx: "package" in ctx.previous_outputs,
            ),
            Constraint(
                name="addon_structure_valid",
                description="Packaged addon must have valid structure",
                validator=lambda ctx: _check_addon_valid(ctx.previous_outputs.get("package")),
            ),
        ]

        def pre_condition(ctx: StepContext) -> bool:
            return "package" in ctx.previous_outputs

        return Step(
            step_id="validate",
            name="Quality Validation",
            description="Validate conversion quality and completeness",
            execute_fn=execute_fn,
            constraints=constraints,
            pre_conditions=[pre_condition],
            rollback_fn=rollback_fn,
        )


def _check_has_features(analysis_output: Any) -> bool:
    """Check if analysis output contains features"""
    if not analysis_output:
        return False
    if isinstance(analysis_output, dict):
        return "features" in analysis_output or "assets" in analysis_output
    return True


def _check_plan_valid(plan_output: Any) -> bool:
    """Check if plan output is valid"""
    if not plan_output:
        return False
    if isinstance(plan_output, dict):
        return "conversion_plan" in plan_output or "strategy" in plan_output
    return True


def _check_has_asset_plan(plan_output: Any) -> bool:
    """Check if plan includes asset conversion strategy"""
    if not plan_output:
        return False
    if isinstance(plan_output, dict):
        return True  # Asset plan is assumed if plan exists
    return False


def _check_components_ready(outputs: Dict[str, Any]) -> bool:
    """Check if all required components are ready for packaging"""
    required_steps = ["translate", "convert_assets"]
    return all(step_id in outputs for step_id in required_steps)


def _check_addon_valid(package_output: Any) -> bool:
    """Check if packaged addon is valid"""
    if not package_output:
        return False
    if isinstance(package_output, dict):
        return "addon_path" in package_output or "status" in package_output
    return True


class RunAgentCrewBridge:
    """
    Bridge between RunAgent framework and CrewAI conversion crew.

    Wraps the standard CrewAI conversion process with constraint validation
    and step-wise enforcement.
    """

    def __init__(self, enable_runagent: bool = True, strict_mode: bool = True):
        """
        Initialize the bridge

        Args:
            enable_runagent: Whether to enforce RunAgent constraints
            strict_mode: If True, constraint violations cause failure
        """
        self.enable_runagent = enable_runagent
        self.strict_mode = strict_mode
        self._last_trace = None
        logger.info(f"RunAgentCrewBridge initialized (enabled={enable_runagent}, strict={strict_mode})")

    def create_conversion_plan(
        self,
        analyze_fn: callable,
        plan_fn: callable,
        translate_fn: callable,
        convert_assets_fn: callable,
        package_fn: callable,
        validate_fn: callable,
    ) -> RunAgentPlan:
        """Create a RunAgent plan from conversion functions"""
        steps = [
            ConversionStepFactory.create_analysis_step(analyze_fn),
            ConversionStepFactory.create_planning_step(plan_fn),
            ConversionStepFactory.create_translation_step(translate_fn),
            ConversionStepFactory.create_asset_conversion_step(convert_assets_fn),
            ConversionStepFactory.create_packaging_step(package_fn),
            ConversionStepFactory.create_validation_step(validate_fn),
        ]

        # Add global constraints
        global_constraints = [
            Constraint(
                name="valid_base_paths",
                description="Base paths for mod and output must be valid",
                validator=validate_no_missing_dependencies,
            ),
        ]

        plan = RunAgentPlan(
            plan_id="conversion_workflow",
            name="Java-to-Bedrock Conversion Workflow",
            description="Standard conversion workflow with constraint validation",
            steps=steps,
            global_constraints=global_constraints,
        )

        return plan

    async def execute_conversion(
        self,
        mod_path: str,
        output_path: str,
        analyze_fn: callable,
        plan_fn: callable,
        translate_fn: callable,
        convert_assets_fn: callable,
        package_fn: callable,
        validate_fn: callable,
    ) -> Dict[str, Any]:
        """
        Execute conversion using RunAgent constraint-guided framework

        Args:
            mod_path: Path to Java mod
            output_path: Path for output
            Conversion functions for each step

        Returns:
            Conversion result with trace information
        """
        if not self.enable_runagent:
            logger.info("RunAgent disabled, executing conversion directly")
            return await self._execute_direct(
                mod_path, output_path,
                analyze_fn, plan_fn, translate_fn, convert_assets_fn, package_fn, validate_fn
            )

        # Create RunAgent plan
        plan = self.create_conversion_plan(
            analyze_fn, plan_fn, translate_fn, convert_assets_fn, package_fn, validate_fn
        )

        # Create RunAgent instance
        run_agent = RunAgent(
            plan=plan,
            enable_rollback=True,
            max_rollbacks=3,
            strict_mode=self.strict_mode,
        )

        # Execute with initial inputs
        initial_inputs = {
            "mod_path": mod_path,
            "output_path": output_path,
        }

        success, trace = await run_agent.execute(initial_inputs)

        self._last_trace = trace

        # Format result
        result = {
            "status": "completed" if success else "failed",
            "success": success,
            "execution_trace": trace.to_dict(),
            "step_outputs": run_agent.get_step_outputs(),
        }

        if not success and trace.constraint_violations:
            result["constraint_violations"] = trace.constraint_violations

        return result

    async def _execute_direct(
        self,
        mod_path: str,
        output_path: str,
        analyze_fn: callable,
        plan_fn: callable,
        translate_fn: callable,
        convert_assets_fn: callable,
        package_fn: callable,
        validate_fn: callable,
    ) -> Dict[str, Any]:
        """Execute conversion without RunAgent constraints"""
        context = StepContext(
            step_id="init",
            step_name="direct_conversion",
            inputs={"mod_path": mod_path, "output_path": output_path},
            previous_outputs={},
            execution_trace=[],
        )

        results = {}
        step_order = ["analyze", "plan", "translate", "convert_assets", "package", "validate"]
        step_fns = [analyze_fn, plan_fn, translate_fn, convert_assets_fn, package_fn, validate_fn]

        for step_id, step_fn in zip(step_order, step_fns):
            try:
                context.step_id = step_id
                context.step_name = step_id

                if asyncio.iscoroutinefunction(step_fn):
                    result = await step_fn(context)
                else:
                    result = step_fn(context)

                results[step_id] = result
                context.previous_outputs[step_id] = result
            except Exception as e:
                logger.error(f"Step {step_id} failed: {e}")
                results[step_id] = {"error": str(e), "status": "failed"}
                break

        return {
            "status": "completed" if "error" not in str(results.get("validate", {})) else "failed",
            "success": "error" not in str(results.get("validate", {})),
            "step_outputs": results,
        }

    def get_last_trace(self):
        """Get the last execution trace"""
        return self._last_trace


class RunAgentOrchestrator:
    """
    Orchestrator that wraps the existing ParallelOrchestrator with RunAgent.

    This provides constraint validation on top of the existing orchestration
    while maintaining backward compatibility.
    """

    def __init__(
        self,
        base_orchestrator: Any,
        enable_runagent: bool = True,
        strict_mode: bool = False,
    ):
        """
        Initialize RunAgent orchestrator

        Args:
            base_orchestrator: The underlying ParallelOrchestrator
            enable_runagent: Enable RunAgent constraint validation
            strict_mode: If True, violations cause immediate failure
        """
        self.base_orchestrator = base_orchestrator
        self.enable_runagent = enable_runagent
        self.strict_mode = strict_mode
        self._bridge = RunAgentCrewBridge(enable_runagent=enable_runagent, strict_mode=strict_mode)
        logger.info("RunAgentOrchestrator initialized")

    def create_constrained_workflow(
        self,
        mod_path: str,
        output_path: str,
        temp_dir: str,
        variant_id: Optional[str] = None,
    ):
        """
        Create a task graph with RunAgent constraint validation

        Args:
            mod_path: Path to Java mod
            output_path: Output path
            temp_dir: Temporary directory
            variant_id: A/B testing variant

        Returns:
            TaskGraph with constraint metadata
        """
        # First create the base workflow
        task_graph = self.base_orchestrator.create_conversion_workflow(
            mod_path=mod_path,
            output_path=output_path,
            temp_dir=temp_dir,
            variant_id=variant_id,
        )

        if self.enable_runagent:
            # Add constraint metadata to each task node
            task_constraints = {
                "analyze": {
                    "required_predecessors": [],
                    "required_inputs": ["mod_path"],
                },
                "plan": {
                    "required_predecessors": ["analyze"],
                    "required_outputs": ["analysis_data"],
                },
                "translate": {
                    "required_predecessors": ["plan"],
                    "required_outputs": ["conversion_plan"],
                },
                "convert_assets": {
                    "required_predecessors": ["plan"],
                    "required_outputs": ["asset_requirements"],
                },
                "package": {
                    "required_predecessors": ["translate", "convert_assets"],
                    "required_outputs": ["translated_code", "converted_assets"],
                },
                "validate": {
                    "required_predecessors": ["package"],
                    "required_outputs": ["addon_package"],
                },
            }

            for task_id, constraints in task_constraints.items():
                if task_id in task_graph.nodes:
                    node = task_graph.nodes[task_id]
                    node.metadata["runagent_constraints"] = constraints
                    node.metadata["runagent_enabled"] = True

        return task_graph

    async def execute_with_constraints(
        self,
        task_graph: Any,
        agent_executors: Dict[str, callable],
    ) -> Dict[str, Any]:
        """
        Execute workflow with constraint validation at each step boundary

        Args:
            task_graph: TaskGraph to execute
            agent_executors: Map of agent names to executor functions

        Returns:
            Execution results
        """
        if not self.enable_runagent:
            return await self.base_orchestrator.execute_workflow(task_graph)

        # Execute with constraint validation
        results = {}
        completed_steps = set()

        for task_id, node in task_graph.nodes.items():
            constraints = node.metadata.get("runagent_constraints", {})

            # Check predecessor constraints
            required_preds = constraints.get("required_predecessors", [])
            if not all(pred in completed_steps for pred in required_preds):
                logger.error(f"Step {task_id} violated: predecessors {required_preds} not completed")
                if self.strict_mode:
                    return {"status": "failed", "error": f"Constraint violation at {task_id}"}
                continue

            # Execute the task
            if node.agent_name in agent_executors:
                try:
                    result = await agent_executors[node.agent_name](node)
                    results[task_id] = result
                    completed_steps.add(task_id)

                    # Validate output constraints
                    required_outputs = constraints.get("required_outputs", [])
                    if isinstance(result, dict):
                        for output_key in required_outputs:
                            if output_key not in result:
                                logger.warning(f"Step {task_id} missing output: {output_key}")

                except Exception as e:
                    logger.error(f"Step {task_id} failed: {e}")
                    if self.strict_mode:
                        return {"status": "failed", "error": str(e), "failed_step": task_id}

        return {"status": "completed", "results": results, "completed_steps": list(completed_steps)}

    def get_bridge(self) -> RunAgentCrewBridge:
        """Get the RunAgent bridge for direct constraint-guided execution"""
        return self._bridge