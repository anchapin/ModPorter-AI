"""
Semantic Checker Agent for QA pipeline.

Validates behavioral equivalence between Java source and Bedrock output.
This is the fifth QA agent (QA-05) in the multi-agent pipeline.
"""

import json
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple

import structlog

from qa.context import QAContext
from qa.validators import AgentOutput, validate_agent_output

logger = structlog.get_logger(__name__)

TEMPERATURE_ZERO = 0.0

SCRIPT_API_METHODS = {
    "Entity",
    "Player",
    "World",
    "Block",
    "ItemStack",
    "Container",
    "Dimension",
    "Location",
    "Vector3",
    "EntityQueryOptions",
    "EntityQueryScoreOptions",
}

JAVA_TO_BEDROCK_TYPES = {
    "int": "number",
    "long": "number",
    "float": "number",
    "double": "number",
    "boolean": "boolean",
    "String": "string",
    "byte": "number",
    "short": "number",
    "char": "string",
    "List": "Array",
    "Map": "Object",
    "Set": "Array",
    "Optional": "?",
}


class DataFlowNode:
    def __init__(
        self,
        name: str,
        node_type: str,
        line: int,
        definitions: List[str] = None,
        uses: List[str] = None,
    ):
        self.name = name
        self.node_type = node_type
        self.line = line
        self.definitions = definitions or []
        self.uses = uses or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.node_type,
            "line": self.line,
            "definitions": self.definitions,
            "uses": self.uses,
        }


class ControlFlowNode:
    def __init__(
        self,
        node_type: str,
        line: int,
        condition: Optional[str] = None,
        body: List[int] = None,
    ):
        self.node_type = node_type
        self.line = line
        self.condition = condition
        self.body = body or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.node_type,
            "line": self.line,
            "condition": self.condition,
            "body": self.body,
        }


class SemanticDrift:
    def __init__(
        self,
        drift_type: str,
        severity: str,
        message: str,
        java_location: Optional[str] = None,
        bedrock_location: Optional[str] = None,
    ):
        self.drift_type = drift_type
        self.severity = severity
        self.message = message
        self.java_location = java_location
        self.bedrock_location = bedrock_location

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.drift_type,
            "severity": self.severity,
            "message": self.message,
            "java_location": self.java_location,
            "bedrock_location": self.bedrock_location,
        }


class SemanticCheckerAgent:
    """
    Semantic Checker Agent - validates behavioral equivalence between Java and Bedrock.

    Compares:
    - Data flow graphs
    - Control flow equivalence
    - Script API method validity
    - Variable/type mappings
    """

    def __init__(self, temperature: float = TEMPERATURE_ZERO):
        self.temperature = temperature
        logger.info("SemanticCheckerAgent initialized", temperature=temperature)

    def _extract_java_data_flow(self, java_path: Path) -> List[DataFlowNode]:
        nodes = []
        try:
            content = java_path.read_text(encoding="utf-8")
            lines = content.split("\n")

            for i, line in enumerate(lines, start=1):
                line = line.strip()

                var_match = re.match(
                    r"(int|long|float|double|boolean|String|var)\s+(\w+)\s*=", line
                )
                if var_match:
                    var_type, var_name = var_match.groups()
                    nodes.append(
                        DataFlowNode(
                            name=var_name,
                            node_type=var_type,
                            line=i,
                            definitions=[f"line_{i}"],
                        )
                    )

                assignment_match = re.match(r"(\w+)\s*=", line)
                if assignment_match and nodes:
                    var_name = assignment_match.group(1)
                    for node in nodes:
                        if node.name == var_name:
                            node.uses.append(f"line_{i}")

        except Exception as e:
            logger.warning("Failed to extract Java data flow", error=str(e))

        return nodes

    def _extract_bedrock_data_flow(self, bedrock_path: Path) -> List[DataFlowNode]:
        nodes = []
        try:
            if bedrock_path.is_file():
                if bedrock_path.suffix == ".json":
                    content = json.loads(bedrock_path.read_text(encoding="utf-8"))
                    nodes.extend(self._extract_json_data_flow(content, str(bedrock_path)))
                elif bedrock_path.suffix == ".ts":
                    content = bedrock_path.read_text(encoding="utf-8")
                    nodes.extend(self._extract_ts_data_flow(content, str(bedrock_path)))
            elif bedrock_path.is_dir():
                for json_file in bedrock_path.rglob("*.json"):
                    content = json.loads(json_file.read_text(encoding="utf-8"))
                    nodes.extend(self._extract_json_data_flow(content, str(json_file)))

        except Exception as e:
            logger.warning("Failed to extract Bedrock data flow", error=str(e))

        return nodes

    def _extract_json_data_flow(self, data: Dict[str, Any], source: str) -> List[DataFlowNode]:
        nodes = []

        def extract_recursive(obj: Any, path: str = ""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    extract_recursive(value, f"{path}.{key}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    extract_recursive(item, f"{path}[{i}]")

        extract_recursive(data)
        return nodes

    def _extract_ts_data_flow(self, content: str, source: str) -> List[DataFlowNode]:
        nodes = []
        lines = content.split("\n")

        for i, line in enumerate(lines, start=1):
            line = line.strip()

            var_match = re.match(r"(const|let|var)\s+(\w+)\s*[=:]", line)
            if var_match:
                var_type, var_name = var_match.groups()
                nodes.append(
                    DataFlowNode(
                        name=var_name,
                        node_type="variable",
                        line=i,
                        definitions=[f"line_{i}"],
                    )
                )

        return nodes

    def _compare_data_flow(
        self, java_nodes: List[DataFlowNode], bedrock_nodes: List[DataFlowNode]
    ) -> Tuple[float, List[SemanticDrift]]:
        if not java_nodes:
            return 100.0, []

        java_vars = {n.name for n in java_nodes}
        bedrock_vars = {n.name for n in bedrock_nodes}

        matched = java_vars & bedrock_vars
        missing = java_vars - bedrock_vars

        score = (len(matched) / len(java_vars)) * 100 if java_vars else 100.0

        drifts = []
        for var in missing:
            java_node = next((n for n in java_nodes if n.name == var), None)
            if java_node:
                drifts.append(
                    SemanticDrift(
                        drift_type="data_flow",
                        severity="high",
                        message=f"Variable '{var}' from Java not found in Bedrock output",
                        java_location=f"line {java_node.line}",
                    )
                )

        return score, drifts

    def _extract_java_control_flow(self, java_path: Path) -> List[ControlFlowNode]:
        nodes = []
        try:
            content = java_path.read_text(encoding="utf-8")
            lines = content.split("\n")

            for i, line in enumerate(lines, start=1):
                line = line.strip()

                if re.match(r"if\s*\(", line):
                    condition = re.search(r"if\s*\((.*)\)", line)
                    nodes.append(
                        ControlFlowNode(
                            node_type="if",
                            line=i,
                            condition=condition.group(1) if condition else None,
                        )
                    )
                elif re.match(r"for\s*\(", line):
                    nodes.append(ControlFlowNode(node_type="for", line=i))
                elif re.match(r"while\s*\(", line):
                    nodes.append(ControlFlowNode(node_type="while", line=i))
                elif re.match(r"switch\s*\(", line):
                    nodes.append(ControlFlowNode(node_type="switch", line=i))

        except Exception as e:
            logger.warning("Failed to extract Java control flow", error=str(e))

        return nodes

    def _extract_bedrock_control_flow(self, bedrock_path: Path) -> List[ControlFlowNode]:
        nodes = []
        try:
            for ts_file in bedrock_path.rglob("*.ts"):
                content = ts_file.read_text(encoding="utf-8")
                lines = content.split("\n")

                for i, line in enumerate(lines, start=1):
                    line = line.strip()

                    if re.match(r"if\s*\(", line):
                        condition = re.search(r"if\s*\((.*)\)", line)
                        nodes.append(
                            ControlFlowNode(
                                node_type="if",
                                line=i,
                                condition=condition.group(1) if condition else None,
                            )
                        )
                    elif re.match(r"for\s*\(", line) or re.match(r"for\s+\w+\s+of", line):
                        nodes.append(ControlFlowNode(node_type="for", line=i))
                    elif re.match(r"while\s*\(", line):
                        nodes.append(ControlFlowNode(node_type="while", line=i))

        except Exception as e:
            logger.warning("Failed to extract Bedrock control flow", error=str(e))

        return nodes

    def _compare_control_flow(
        self, java_nodes: List[ControlFlowNode], bedrock_nodes: List[ControlFlowNode]
    ) -> Tuple[float, List[SemanticDrift]]:
        if not java_nodes:
            return 100.0, []

        java_types = [n.node_type for n in java_nodes]
        bedrock_types = [n.node_type for n in bedrock_nodes]

        java_if_count = java_types.count("if")
        bedrock_if_count = bedrock_types.count("if")

        drift_score = (
            min(java_if_count, bedrock_if_count) / max(java_if_count, bedrock_if_count)
            if java_if_count > 0
            else 1.0
        )
        score = drift_score * 100

        drifts = []
        if java_if_count > bedrock_if_count:
            drifts.append(
                SemanticDrift(
                    drift_type="control_flow",
                    severity="medium",
                    message=f"Missing {java_if_count - bedrock_if_count} conditional branches in Bedrock",
                )
            )

        return score, drifts

    def _check_script_api_validity(self, bedrock_path: Path) -> Tuple[float, List[SemanticDrift]]:
        drifts = []
        valid_count = 0
        total_count = 0

        try:
            for ts_file in bedrock_path.rglob("*.ts"):
                content = ts_file.read_text(encoding="utf-8")

                api_calls = re.findall(r"(\w+)\.(\w+)\(", content)
                for obj, method in api_calls:
                    total_count += 1
                    if obj in SCRIPT_API_METHODS:
                        valid_count += 1
                    else:
                        drifts.append(
                            SemanticDrift(
                                drift_type="api_validity",
                                severity="medium",
                                message=f"Unknown Script API object: '{obj}'",
                                bedrock_location=str(ts_file),
                            )
                        )

        except Exception as e:
            logger.warning("Failed to check Script API validity", error=str(e))

        score = (valid_count / total_count * 100) if total_count > 0 else 100.0

        return score, drifts

    def _check_type_mappings(
        self, java_path: Path, bedrock_path: Path
    ) -> Tuple[float, List[SemanticDrift]]:
        drifts = []
        java_types_found = set()
        bedrock_types_found = set()

        try:
            java_content = java_path.read_text(encoding="utf-8")
            for java_type, bedrock_type in JAVA_TO_BEDROCK_TYPES.items():
                if java_type in java_content:
                    java_types_found.add(java_type)

            for ts_file in bedrock_path.rglob("*.ts"):
                content = ts_file.read_text(encoding="utf-8")
                for java_type, bedrock_type in JAVA_TO_BEDROCK_TYPES.items():
                    if bedrock_type in content:
                        bedrock_types_found.add(bedrock_type)

        except Exception as e:
            logger.warning("Failed to check type mappings", error=str(e))

        mapped_count = len(java_types_found & bedrock_types_found)
        total_java_types = len(java_types_found)

        score = (mapped_count / total_java_types * 100) if total_java_types > 0 else 100.0

        if mapped_count < total_java_types:
            missing = java_types_found - bedrock_types_found
            for missing_type in missing:
                drifts.append(
                    SemanticDrift(
                        drift_type="type_mapping",
                        severity="low",
                        message=f"Java type '{missing_type}' has no corresponding Bedrock type in output",
                        java_location=str(java_path),
                    )
                )

        return score, drifts

    def _calculate_semantic_score(
        self,
        data_flow_score: float,
        control_flow_score: float,
        api_validity_score: float,
        type_mapping_score: float,
    ) -> float:
        weights = {
            "data_flow": 0.30,
            "control_flow": 0.25,
            "api_validity": 0.25,
            "type_mapping": 0.20,
        }

        weighted_score = (
            data_flow_score * weights["data_flow"]
            + control_flow_score * weights["control_flow"]
            + api_validity_score * weights["api_validity"]
            + type_mapping_score * weights["type_mapping"]
        )

        return round(weighted_score, 1)

    def _classify_semantic_drift(self, score: float) -> str:
        if score >= 70:
            return "minor"
        elif score >= 40:
            return "moderate"
        else:
            return "major"

    def execute(self, context: QAContext) -> AgentOutput:
        """
        Execute the semantic checker agent on the given QA context.

        Args:
            context: QA context containing job information and paths

        Returns:
            AgentOutput with semantic analysis results
        """
        start_time = time.time()

        try:
            logger.info("SemanticCheckerAgent executing", job_id=context.job_id)

            java_path = context.source_java_path
            bedrock_path = context.output_bedrock_path

            if not java_path.exists():
                return AgentOutput(
                    agent_name="semantic",
                    success=False,
                    result={},
                    errors=[f"Java source not found: {java_path}"],
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            if not bedrock_path.exists():
                return AgentOutput(
                    agent_name="semantic",
                    success=False,
                    result={},
                    errors=[f"Bedrock output not found: {bedrock_path}"],
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            java_data_flow = self._extract_java_data_flow(java_path)
            bedrock_data_flow = self._extract_bedrock_data_flow(bedrock_path)

            data_flow_score, data_flow_drifts = self._compare_data_flow(
                java_data_flow, bedrock_data_flow
            )

            java_control_flow = self._extract_java_control_flow(java_path)
            bedrock_control_flow = self._extract_bedrock_control_flow(bedrock_path)

            control_flow_score, control_flow_drifts = self._compare_control_flow(
                java_control_flow, bedrock_control_flow
            )

            api_validity_score, api_drifts = self._check_script_api_validity(bedrock_path)

            type_mapping_score, type_drifts = self._check_type_mappings(java_path, bedrock_path)

            all_drifts = data_flow_drifts + control_flow_drifts + api_drifts + type_drifts

            semantic_score = self._calculate_semantic_score(
                data_flow_score, control_flow_score, api_validity_score, type_mapping_score
            )

            drift_classification = self._classify_semantic_drift(semantic_score)

            result = {
                "semantic_score": semantic_score,
                "drift_classification": drift_classification,
                "data_flow_score": round(data_flow_score, 1),
                "control_flow_score": round(control_flow_score, 1),
                "api_validity_score": round(api_validity_score, 1),
                "type_mapping_score": round(type_mapping_score, 1),
                "java_variables_found": len(java_data_flow),
                "bedrock_variables_found": len(bedrock_data_flow),
                "java_control_structures": len(java_control_flow),
                "bedrock_control_structures": len(bedrock_control_flow),
                "drifts_detected": len(all_drifts),
                "drifts": [d.to_dict() for d in all_drifts],
            }

            context.validation_results["semantic"] = {
                "score": semantic_score,
                "classification": drift_classification,
                "passed": semantic_score >= 70,
            }

            execution_time = int((time.time() - start_time) * 1000)

            output_data = {
                "agent_name": "semantic",
                "success": semantic_score >= 70,
                "result": result,
                "errors": [d.message for d in all_drifts if d.severity == "high"],
                "execution_time_ms": execution_time,
            }

            validated = validate_agent_output(output_data)

            logger.info(
                "SemanticCheckerAgent completed",
                job_id=context.job_id,
                score=semantic_score,
                drifts=len(all_drifts),
            )

            return validated

        except Exception as e:
            logger.error("SemanticCheckerAgent failed", job_id=context.job_id, error=str(e))
            return AgentOutput(
                agent_name="semantic",
                success=False,
                result={},
                errors=[str(e)],
                execution_time_ms=int((time.time() - start_time) * 1000),
            )


def check_semantics(context: QAContext) -> AgentOutput:
    """
    Convenience function to run semantic check.

    Args:
        context: QA context

    Returns:
        AgentOutput with semantic analysis results
    """
    agent = SemanticCheckerAgent()
    return agent.execute(context)
