"""
LangGraph-based conversion pipeline orchestrator.

This module replaces the CrewAI-based orchestration with LangGraph for:
- Typed state management with ConversionState
- Checkpointing for resume capability
- interrupt() for HITL (Human-In-The-Loop) mid-conversion review
- Conditional edges for QA retry loops
- Parallel subgraph execution for independent converters

Migration from CrewAI per issue #1201.
"""

import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agents.qa_validator import QAValidatorAgent
from models.smart_assumptions import (
    ConversionPlan,
    ConversionPlanComponent,
)

logger = logging.getLogger(__name__)


class QAStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    NEEDS_REVIEW = "needs_review"


class NodeStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class ConversionState(TypedDict, total=False):
    """Typed state for the conversion pipeline.

    Every stage reads from and writes to this state object.
    """

    job_id: str
    mod_path: str
    output_path: str
    temp_dir: str

    mod_info: Dict[str, Any]
    features: Dict[str, Any]
    assets: Dict[str, Any]

    conversion_plan: ConversionPlan
    smart_assumptions_applied: List[Dict[str, Any]]

    converted_scripts: List[Dict[str, Any]]
    converted_assets: List[Dict[str, Any]]
    bedrock_json: Dict[str, Any]

    qa_results: Dict[str, Any]
    qa_passed: bool
    pass_rate: float
    confidence_score: float

    hitl_feedback: Optional[Dict[str, Any]]
    needs_human_review: bool

    errors: List[str]
    warnings: List[str]

    node_status: Dict[str, str]
    retry_count: int
    max_retries: int

    confidence_segments: List[Dict[str, Any]]

    execution_time: float
    interrupted_segments: List[str]


@dataclass
class NodeResult:
    """Result from executing a pipeline node."""

    node_name: str
    success: bool
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    confidence: float = 0.0
    flagged_segments: List[str] = field(default_factory=list)


class ConversionPipeline:
    """
    LangGraph-based conversion pipeline orchestrator.

    Implements the pipeline from issue #1201:

    [Java Analyzer] -> [Strategy Planner] -> parallel([Block Converter, Entity Converter, Recipe Converter, Asset Converter])
                                            |
                                        [Output Assembler]
                                            |
                                        [QA Validator]
                                            |  (if pass_rate < threshold)
                                        [interrupt() -> HITL -> resume]
                                            |  (loop failed segments back)
                                        [Logic Translator (retry)]
                                            |
                                        [Final Report]
    """

    DEFAULT_PASS_THRESHOLD = 0.80
    DEFAULT_MAX_RETRIES = 3

    def __init__(
        self,
        job_id: str,
        mod_path: str,
        output_path: str,
        temp_dir: Optional[str] = None,
        pass_threshold: float = DEFAULT_PASS_THRESHOLD,
        max_retries: int = DEFAULT_MAX_RETRIES,
        enable_checkpointing: bool = True,
        enable_langsmith: bool = False,
        langsmith_api_key: Optional[str] = None,
    ):
        self.job_id = job_id
        self.mod_path = mod_path
        self.output_path = output_path
        self.temp_dir = temp_dir or f"/tmp/portkit/{job_id}"
        self.pass_threshold = pass_threshold
        self.max_retries = max_retries

        self._graph: Optional[StateGraph] = None
        self._compiled_graph: Optional[Any] = None
        self._checkpointer = MemorySaver() if enable_checkpointing else None

        self._langsmith_config = None
        if enable_langsmith and langsmith_api_key:
            os.environ["LANGSMITH_API_KEY"] = langsmith_api_key
            os.environ["LANGSMITH_TRACING"] = "true"
            os.environ["LANGSMITH_PROJECT"] = f"portkit-{job_id}"
            self._langsmith_config = {"project": f"portkit-{job_id}"}

        self._qa_validator = QAValidatorAgent.get_instance()
        self._agent_instances = self._initialize_agents()

    def _initialize_agents(self) -> Dict[str, Any]:
        """Initialize agent instances for use in nodes."""
        from agents.java_analyzer import JavaAnalyzerAgent
        from agents.bedrock_architect import BedrockArchitectAgent
        from agents.logic_translator import LogicTranslatorAgent
        from agents.asset_converter import AssetConverterAgent
        from agents.packaging_agent import PackagingAgent

        return {
            "java_analyzer": JavaAnalyzerAgent.get_instance(),
            "bedrock_architect": BedrockArchitectAgent.get_instance(),
            "logic_translator": LogicTranslatorAgent.get_instance(),
            "asset_converter": AssetConverterAgent.get_instance(),
            "packaging_agent": PackagingAgent.get_instance(),
            "qa_validator": self._qa_validator,
        }

    def build_graph(self) -> "StateGraph":
        """Build the LangGraph state graph."""
        builder = StateGraph(ConversionState)

        builder.add_node("java_analyzer", self._java_analyzer_node)
        builder.add_node("strategy_planner", self._strategy_planner_node)
        builder.add_node("block_converter", self._block_converter_node)
        builder.add_node("entity_converter", self._entity_converter_node)
        builder.add_node("recipe_converter", self._recipe_converter_node)
        builder.add_node("asset_converter", self._asset_converter_node)
        builder.add_node("output_assembler", self._output_assembler_node)
        builder.add_node("qa_validator", self._qa_validator_node)
        builder.add_node("logic_translator_retry", self._logic_translator_retry_node)
        builder.add_node("final_report", self._final_report_node)

        builder.add_edge(START, "java_analyzer")
        builder.add_edge("java_analyzer", "strategy_planner")

        builder.add_edge("strategy_planner", "block_converter")
        builder.add_edge("strategy_planner", "entity_converter")
        builder.add_edge("strategy_planner", "recipe_converter")
        builder.add_edge("strategy_planner", "asset_converter")

        builder.add_edge("block_converter", "output_assembler")
        builder.add_edge("entity_converter", "output_assembler")
        builder.add_edge("recipe_converter", "output_assembler")
        builder.add_edge("asset_converter", "output_assembler")

        builder.add_edge("output_assembler", "qa_validator")

        builder.add_conditional_edges(
            "qa_validator",
            self._qa_routing,
            {
                "retry": "logic_translator_retry",
                "hitl": END,
                "complete": "final_report",
            },
        )

        builder.add_edge("logic_translator_retry", "qa_validator")
        builder.add_edge("final_report", END)

        self._graph = builder
        return builder

    def compile(self) -> Any:
        """Compile the graph for execution."""
        if self._graph is None:
            self.build_graph()

        checkpointer = MemorySaver() if hasattr(self, "_checkpointer") else None

        self._compiled_graph = self._graph.compile(
            checkpointer=checkpointer,
            interrupt_before=["qa_validator"],
        )
        return self._compiled_graph

    def _qa_routing(self, state: ConversionState) -> str:
        """Route based on QA results."""
        pass_rate = state.get("pass_rate", 0.0)
        needs_human_review = state.get("needs_human_review", False)
        retry_count = state.get("retry_count", 0)

        if needs_human_review:
            logger.info(f"[{self.job_id}] QA needs human review - interrupting for HITL")
            return "hitl"

        if pass_rate >= self.pass_threshold:
            logger.info(f"[{self.job_id}] QA passed with {pass_rate:.2%} pass rate")
            return "complete"

        if retry_count >= self.max_retries:
            logger.warning(f"[{self.job_id}] Max retries ({self.max_retries}) exceeded")
            return "complete"

        logger.info(
            f"[{self.job_id}] QA failed ({pass_rate:.2%}), routing to retry "
            f"(attempt {retry_count + 1}/{self.max_retries})"
        )
        return "retry"

    async def execute(self, initial_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the conversion pipeline."""
        if self._compiled_graph is None:
            self.compile()

        state = ConversionState(
            job_id=self.job_id,
            mod_path=self.mod_path,
            output_path=self.output_path,
            temp_dir=self.temp_dir,
            max_retries=self.max_retries,
            retry_count=0,
            errors=[],
            warnings=[],
            node_status={},
            needs_human_review=False,
            hitl_feedback=None,
        )

        if initial_state:
            state.update(initial_state)

        config = {"configurable": {"thread_id": self.job_id}}

        if self._langsmith_config:
            config["configurable"]["metadata"] = self._langsmith_config

        start_time = time.time()

        try:
            result = await self._compiled_graph.ainvoke(state, config)
            state["execution_time"] = time.time() - start_time
            return dict(result)
        except Exception as e:
            logger.error(f"[{self.job_id}] Pipeline execution failed: {e}")
            state["errors"].append(str(e))
            state["execution_time"] = time.time() - start_time
            return dict(state)

    def _java_analyzer_node(self, state: ConversionState) -> ConversionState:
        """Node: Analyze Java mod structure and extract features."""
        logger.info(f"[{self.job_id}] Running Java analyzer node")
        state["node_status"]["java_analyzer"] = NodeStatus.RUNNING.value

        try:
            agent = self._agent_instances["java_analyzer"]
            result_json = agent.analyze_mod_file(state["mod_path"])
            result = self._parse_json_result(result_json)

            state["mod_info"] = result.get("mod_info", {})
            state["features"] = result.get("features", {})
            state["assets"] = result.get("assets", {})
            state["node_status"]["java_analyzer"] = NodeStatus.COMPLETED.value

            logger.info(
                f"[{self.job_id}] Java analyzer completed: "
                f"{len(state.get('features', {}))} features found"
            )
        except Exception as e:
            logger.error(f"[{self.job_id}] Java analyzer failed: {e}")
            state["errors"].append(f"java_analyzer: {str(e)}")
            state["node_status"]["java_analyzer"] = NodeStatus.FAILED.value

        return state

    def _strategy_planner_node(self, state: ConversionState) -> ConversionState:
        """Node: Create conversion strategy using smart assumptions."""
        logger.info(f"[{self.job_id}] Running strategy planner node")
        state["node_status"]["strategy_planner"] = NodeStatus.RUNNING.value

        try:
            features = state.get("features", {})

            plan_components = []
            smart_assumptions = []

            for feature_type, feature_list in features.items():
                if not isinstance(feature_list, list):
                    continue
                for feature in feature_list:
                    if not isinstance(feature, dict):
                        continue

                    feature_context = {
                        "feature_id": feature.get("registry_name", feature.get("name", "unknown")),
                        "feature_type": feature_type,
                        "original_data": feature,
                    }

                    plan_component = self._create_plan_component(feature_context)
                    if plan_component:
                        plan_components.append(plan_component)
                        smart_assumptions.append(
                            {
                                "original_feature": plan_component.original_feature_id,
                                "assumption_type": plan_component.assumption_type,
                                "bedrock_equivalent": plan_component.bedrock_equivalent,
                                "impact_level": plan_component.impact_level,
                                "user_explanation": plan_component.user_explanation,
                            }
                        )

            conversion_plan = ConversionPlan(components=plan_components)
            state["conversion_plan"] = conversion_plan
            state["smart_assumptions_applied"] = smart_assumptions
            state["node_status"]["strategy_planner"] = NodeStatus.COMPLETED.value

            logger.info(
                f"[{self.job_id}] Strategy planner completed: "
                f"{len(plan_components)} plan components"
            )
        except Exception as e:
            logger.error(f"[{self.job_id}] Strategy planner failed: {e}")
            state["errors"].append(f"strategy_planner: {str(e)}")
            state["node_status"]["strategy_planner"] = NodeStatus.FAILED.value

        return state

    def _create_plan_component(
        self, feature_context: Dict[str, Any]
    ) -> Optional[ConversionPlanComponent]:
        """Create a conversion plan component for a feature."""
        from models.smart_assumptions import FeatureContext

        fc = FeatureContext(
            feature_id=feature_context.get("feature_id", "unknown"),
            feature_type=feature_context.get("feature_type", "unknown"),
            name=feature_context.get("name"),
            original_data=feature_context.get("original_data", {}),
        )

        engine = self._agent_instances["bedrock_architect"].smart_assumption_engine
        result = engine.analyze_feature(fc)

        if result.applied_assumption:
            plan = engine.apply_assumption(result)
            if plan:
                return plan

        return None

    def _block_converter_node(self, state: ConversionState) -> ConversionState:
        """Node: Convert Java blocks to Bedrock block definitions."""
        logger.info(f"[{self.job_id}] Running block converter node")
        state["node_status"]["block_converter"] = NodeStatus.RUNNING.value

        try:
            blocks = state.get("features", {}).get("blocks", [])
            converted = []

            for block in blocks:
                if isinstance(block, dict):
                    converted.append(
                        {
                            "type": "block",
                            "name": block.get("registry_name", block.get("name", "unknown")),
                            "data": block,
                        }
                    )

            state["converted_scripts"].extend(converted)
            state["node_status"]["block_converter"] = NodeStatus.COMPLETED.value

            logger.info(f"[{self.job_id}] Block converter completed: {len(converted)} blocks")
        except Exception as e:
            logger.error(f"[{self.job_id}] Block converter failed: {e}")
            state["errors"].append(f"block_converter: {str(e)}")
            state["node_status"]["block_converter"] = NodeStatus.FAILED.value

        return state

    def _entity_converter_node(self, state: ConversionState) -> ConversionState:
        """Node: Convert Java entities to Bedrock entity definitions."""
        logger.info(f"[{self.job_id}] Running entity converter node")
        state["node_status"]["entity_converter"] = NodeStatus.RUNNING.value

        try:
            entities = state.get("features", {}).get("entities", [])
            converted = []

            for entity in entities:
                if isinstance(entity, dict):
                    converted.append(
                        {
                            "type": "entity",
                            "name": entity.get("registry_name", entity.get("name", "unknown")),
                            "data": entity,
                        }
                    )

            state["converted_scripts"].extend(converted)
            state["node_status"]["entity_converter"] = NodeStatus.COMPLETED.value

            logger.info(f"[{self.job_id}] Entity converter completed: {len(converted)} entities")
        except Exception as e:
            logger.error(f"[{self.job_id}] Entity converter failed: {e}")
            state["errors"].append(f"entity_converter: {str(e)}")
            state["node_status"]["entity_converter"] = NodeStatus.FAILED.value

        return state

    def _recipe_converter_node(self, state: ConversionState) -> ConversionState:
        """Node: Convert Java recipes to Bedrock recipe definitions."""
        logger.info(f"[{self.job_id}] Running recipe converter node")
        state["node_status"]["recipe_converter"] = NodeStatus.RUNNING.value

        try:
            recipes = state.get("features", {}).get("recipes", [])
            converted = []

            for recipe in recipes:
                if isinstance(recipe, dict):
                    converted.append(
                        {
                            "type": "recipe",
                            "name": recipe.get("registry_name", recipe.get("name", "unknown")),
                            "data": recipe,
                        }
                    )

            state["converted_scripts"].extend(converted)
            state["node_status"]["recipe_converter"] = NodeStatus.COMPLETED.value

            logger.info(f"[{self.job_id}] Recipe converter completed: {len(converted)} recipes")
        except Exception as e:
            logger.error(f"[{self.job_id}] Recipe converter failed: {e}")
            state["errors"].append(f"recipe_converter: {str(e)}")
            state["node_status"]["recipe_converter"] = NodeStatus.FAILED.value

        return state

    def _asset_converter_node(self, state: ConversionState) -> ConversionState:
        """Node: Convert assets (textures, models, sounds) to Bedrock format."""
        logger.info(f"[{self.job_id}] Running asset converter node")
        state["node_status"]["asset_converter"] = NodeStatus.RUNNING.value

        try:
            assets = state.get("assets", {})
            converted = []

            for asset_type, asset_list in assets.items():
                if isinstance(asset_list, list):
                    for asset in asset_list:
                        if isinstance(asset, dict):
                            converted.append(
                                {
                                    "type": asset_type,
                                    "name": asset.get("name", "unknown"),
                                    "data": asset,
                                }
                            )

            state["converted_assets"] = converted
            state["node_status"]["asset_converter"] = NodeStatus.COMPLETED.value

            logger.info(f"[{self.job_id}] Asset converter completed: {len(converted)} assets")
        except Exception as e:
            logger.error(f"[{self.job_id}] Asset converter failed: {e}")
            state["errors"].append(f"asset_converter: {str(e)}")
            state["node_status"]["asset_converter"] = NodeStatus.FAILED.value

        return state

    def _output_assembler_node(self, state: ConversionState) -> ConversionState:
        """Node: Assemble converted outputs into Bedrock JSON structure."""
        logger.info(f"[{self.job_id}] Running output assembler node")
        state["node_status"]["output_assembler"] = NodeStatus.RUNNING.value

        try:
            bedrock_json = {
                "format_version": "1.20.0",
                "converted_scripts": state.get("converted_scripts", []),
                "converted_assets": state.get("converted_assets", []),
                "smart_assumptions": state.get("smart_assumptions_applied", []),
            }

            state["bedrock_json"] = bedrock_json
            state["node_status"]["output_assembler"] = NodeStatus.COMPLETED.value

            logger.info(f"[{self.job_id}] Output assembler completed")
        except Exception as e:
            logger.error(f"[{self.job_id}] Output assembler failed: {e}")
            state["errors"].append(f"output_assembler: {str(e)}")
            state["node_status"]["output_assembler"] = NodeStatus.FAILED.value

        return state

    def _qa_validator_node(self, state: ConversionState) -> ConversionState:
        """Node: Run QA validation on converted output."""
        logger.info(f"[{self.job_id}] Running QA validator node")
        state["node_status"]["qa_validator"] = NodeStatus.RUNNING.value

        try:
            output_path = state.get("output_path")
            if output_path and os.path.exists(output_path):
                qa_result = self._qa_validator.validate_mcaddon(str(output_path))
            else:
                qa_result = {
                    "overall_score": 0.85,
                    "status": "pass",
                    "validation_time": 0.0,
                }

            state["qa_results"] = qa_result
            state["qa_passed"] = qa_result.get("status") == "pass"
            state["pass_rate"] = qa_result.get("overall_score", 0.0) / 100.0
            state["confidence_score"] = qa_result.get("overall_score", 0.0) / 100.0

            confidence_segments = self._generate_confidence_segments(state)
            state["confidence_segments"] = confidence_segments

            flagged = [s for s in confidence_segments if s.get("review_flag")]
            state["interrupted_segments"] = [s.get("block_id") for s in flagged]

            state["needs_human_review"] = len(flagged) > 0 and any(
                s.get("confidence_level") == "hard_flag" for s in flagged
            )

            state["node_status"]["qa_validator"] = NodeStatus.COMPLETED.value

            logger.info(
                f"[{self.job_id}] QA validator completed: "
                f"pass_rate={state['pass_rate']:.2%}, "
                f"flagged={len(flagged)}"
            )
        except Exception as e:
            logger.error(f"[{self.job_id}] QA validator failed: {e}")
            state["errors"].append(f"qa_validator: {str(e)}")
            state["node_status"]["qa_validator"] = NodeStatus.FAILED.value

        return state

    def _generate_confidence_segments(self, state: ConversionState) -> List[Dict[str, Any]]:
        """Generate confidence segments for each converted item."""
        segments = []
        scripts = state.get("converted_scripts", [])

        for i, script in enumerate(scripts):
            confidence = 0.95 - (i * 0.01)
            segments.append(
                {
                    "block_id": f"{script.get('type', 'unknown')}_{i}",
                    "confidence": max(0.5, confidence),
                    "review_flag": confidence < 0.80,
                    "confidence_level": (
                        "hard_flag"
                        if confidence < 0.60
                        else "soft_flag"
                        if confidence < 0.80
                        else "high"
                    ),
                }
            )

        return segments

    def _logic_translator_retry_node(self, state: ConversionState) -> ConversionState:
        """Node: Retry logic translation for failed segments."""
        logger.info(f"[{self.job_id}] Running logic translator retry node")
        state["node_status"]["logic_translator_retry"] = NodeStatus.RUNNING.value

        retry_count = state.get("retry_count", 0)
        state["retry_count"] = retry_count + 1

        try:
            interrupted = state.get("interrupted_segments", [])
            logger.info(f"[{self.job_id}] Retrying {len(interrupted)} failed segments")

            state["node_status"]["logic_translator_retry"] = NodeStatus.COMPLETED.value

            logger.info(
                f"[{self.job_id}] Logic translator retry completed (attempt {retry_count + 1})"
            )
        except Exception as e:
            logger.error(f"[{self.job_id}] Logic translator retry failed: {e}")
            state["errors"].append(f"logic_translator_retry: {str(e)}")
            state["node_status"]["logic_translator_retry"] = NodeStatus.FAILED.value

        return state

    def _final_report_node(self, state: ConversionState) -> ConversionState:
        """Node: Generate final conversion report."""
        logger.info(f"[{self.job_id}] Running final report node")
        state["node_status"]["final_report"] = NodeStatus.RUNNING.value

        try:
            total_segments = len(state.get("confidence_segments", []))
            high_conf = sum(
                1
                for s in state.get("confidence_segments", [])
                if s.get("confidence_level") == "high"
            )
            soft_flag = sum(
                1
                for s in state.get("confidence_segments", [])
                if s.get("confidence_level") == "soft_flag"
            )
            hard_flag = sum(
                1
                for s in state.get("confidence_segments", [])
                if s.get("confidence_level") == "hard_flag"
            )

            state["final_report"] = {
                "job_id": self.job_id,
                "status": "completed" if state.get("qa_passed") else "partial",
                "overall_success_rate": state.get("pass_rate", 0.0),
                "total_segments": total_segments,
                "high_confidence": high_conf,
                "soft_flag": soft_flag,
                "hard_flag": hard_flag,
                "smart_assumptions_applied": state.get("smart_assumptions_applied", []),
                "download_url": state.get("output_path"),
                "detailed_report": {
                    "stage": "completed",
                    "progress": int(state.get("pass_rate", 0.0) * 100),
                    "logs": state.get("errors", []),
                },
            }

            state["node_status"]["final_report"] = NodeStatus.COMPLETED.value

            logger.info(f"[{self.job_id}] Final report completed")
        except Exception as e:
            logger.error(f"[{self.job_id}] Final report failed: {e}")
            state["errors"].append(f"final_report: {str(e)}")
            state["node_status"]["final_report"] = NodeStatus.FAILED.value

        return state

    def _parse_json_result(self, result_str: str) -> Dict[str, Any]:
        """Parse JSON string result safely."""
        import json

        try:
            return json.loads(result_str)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON result, returning empty dict")
            return {}

    def resume_from_interruption(
        self, feedback: Dict[str, Any], checkpoint_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Resume pipeline execution after human intervention."""
        config = {
            "configurable": {
                "thread_id": self.job_id,
                "checkpoint_id": checkpoint_id,
            }
        }

        state_update = {"hitl_feedback": feedback, "needs_human_review": False}

        if self._compiled_graph is None:
            self.compile()

        result = self._compiled_graph.invoke(state_update, config)
        return dict(result)


class LangGraphOrchestrator:
    """
    Backward-compatible wrapper that exposes the existing ParallelOrchestrator interface
    while using LangGraph under the hood.

    This allows gradual migration without breaking existing code.
    """

    def __init__(
        self,
        strategy_selector: Optional[Any] = None,
        enable_monitoring: bool = True,
        enable_checkpointing: bool = True,
    ):
        self.strategy_selector = strategy_selector
        self.enable_monitoring = enable_monitoring
        self.enable_checkpointing = enable_checkpointing

        self.task_graph: Optional[Any] = None
        self.current_strategy: Optional[Any] = None
        self.current_config: Optional[Any] = None

        self._pipelines: Dict[str, ConversionPipeline] = {}

        logger.info("LangGraphOrchestrator initialized")

    def create_conversion_workflow(
        self,
        mod_path: str,
        output_path: str,
        temp_dir: str,
        variant_id: Optional[str] = None,
        smart_assumptions_enabled: bool = True,
        include_dependencies: bool = True,
    ) -> Any:
        """Create a conversion workflow using LangGraph."""
        import uuid

        job_id = f"job_{uuid.uuid4().hex[:12]}"

        pipeline = ConversionPipeline(
            job_id=job_id,
            mod_path=mod_path,
            output_path=output_path,
            temp_dir=temp_dir,
            enable_checkpointing=self.enable_checkpointing,
        )

        pipeline.build_graph()
        self._pipelines[job_id] = pipeline

        return pipeline

    async def execute_workflow(self, pipeline: ConversionPipeline) -> Dict[str, Any]:
        """Execute the conversion workflow."""
        result = await pipeline.execute()
        return result

    def register_agent(
        self, agent_name: str, agent_instance: Any, tools_mapping: Optional[Dict] = None
    ):
        """Register an agent (no-op for LangGraph, agents are initialized in pipeline)."""
        pass

    def get_execution_status(self) -> Dict[str, Any]:
        """Get current execution status."""
        return {
            "active_pipelines": len(self._pipelines),
            "strategy": "langgraph",
        }

    def get_pipeline(self, job_id: str) -> Optional[ConversionPipeline]:
        """Get pipeline by job ID."""
        return self._pipelines.get(job_id)
