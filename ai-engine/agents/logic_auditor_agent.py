"""
Adversarial Logic Auditor Agent for QA pipeline.

Detects subtle functional discrepancies — conversions that pass syntax and schema
checks but silently break gameplay behavior. Based on ASMR-Bench framework.

This is the adversarial logic auditor (QA-06) in the multi-agent QA pipeline.
"""

import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import structlog

from qa.context import QAContext
from qa.validators import AgentOutput, validate_agent_output

logger = structlog.get_logger(__name__)

TEMPERATURE_ZERO = 0.0


class Severity(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SemanticType(Enum):
    NUMERIC_FORMULA = "numeric_formula"
    PROBABILITY_RNG = "probability_rng"
    EVENT_HOOK = "event_hook"
    CONDITIONAL = "conditional"
    RESOURCE_ID = "resource_id"
    UNKNOWN = "unknown"


@dataclass
class AuditFinding:
    check_type: str
    severity: Severity
    description: str
    java_snippet: str
    bedrock_snippet: str
    expected_behavior: str = ""
    actual_behavior: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_type": self.check_type,
            "severity": self.severity.value,
            "description": self.description,
            "java_snippet": self.java_snippet,
            "bedrock_snippet": self.bedrock_snippet,
            "expected_behavior": self.expected_behavior,
            "actual_behavior": self.actual_behavior,
        }


@dataclass
class AuditReport:
    findings: List[AuditFinding] = field(default_factory=list)
    high_severity_count: int = 0
    medium_severity_count: int = 0
    low_severity_count: int = 0
    blocked: bool = False
    confidence_impact: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "high_severity_count": self.high_severity_count,
            "medium_severity_count": self.medium_severity_count,
            "low_severity_count": self.low_severity_count,
            "blocked": self.blocked,
            "confidence_impact": self.confidence_impact,
            "total_findings": len(self.findings),
        }


class FormulaDriftChecker:
    """Checks for coefficient drift and operator substitution in numeric formulas."""

    def __init__(self):
        self.check_type = "formula_drift"
        self.operator_patterns = [
            (r"\*\s*(\d+\.?\d*)", "*", "multiplication"),
            (r"\+\s*(\d+\.?\d*)", "+", "addition"),
            (r"-\s*(\d+\.?\d*)", "-", "subtraction"),
            (r"/\s*(\d+\.?\d*)", "/", "division"),
        ]

    def check(self, java_code: str, bedrock_code: str) -> List[AuditFinding]:
        findings = []
        java_formulas = self._extract_formulas(java_code, is_java=True)
        bedrock_formulas = self._extract_formulas(bedrock_code, is_java=False)

        for java_formula in java_formulas:
            for bedrock_formula in bedrock_formulas:
                finding = self._compare_formulas(java_formula, bedrock_formula)
                if finding:
                    findings.append(finding)
        return findings

    def _extract_formulas(self, code: str, is_java: bool) -> List[Dict[str, Any]]:
        formulas = []
        lines = code.split("\n")
        for i, line in enumerate(lines, start=1):
            if is_java:
                matches = re.findall(r"(\w+)\s*=\s*([^;]+);", line)
                for var, expr in matches:
                    if any(op in expr for op in ["*", "+", "-", "/"]):
                        formulas.append({"var": var, "expr": expr.strip(), "line": i})
            else:
                matches = re.findall(r"(\w+)\s*=\s*([^;]+);", line)
                for var, expr in matches:
                    if any(op in expr for op in ["*", "+", "-", "/"]):
                        formulas.append({"var": var, "expr": expr.strip(), "line": i})
        return formulas

    def _compare_formulas(self, java: Dict, bedrock: Dict) -> Optional[AuditFinding]:
        java_expr = java["expr"]
        bedrock_expr = bedrock["expr"]

        if java["var"] != bedrock["var"]:
            return None

        java_has_coef = re.search(r"\*\s*(\d+\.?\d*)", java_expr)
        bedrock_has_addcoef = re.search(r"\+\s*(\d+\.?\d*)", bedrock_expr)

        if java_has_coef and bedrock_has_addcoef:
            java_coef = java_has_coef.group(1)
            bedrock_add = bedrock_has_addcoef.group(1)
            bedrock_ends_with_addcoef = (
                bedrock_expr.strip().rstrip(";").endswith(f"+ {bedrock_add}")
            )
            if java_coef == bedrock_add and bedrock_ends_with_addcoef:
                return AuditFinding(
                    check_type=self.check_type,
                    severity=Severity.HIGH,
                    description=f"Operator substitution detected: multiplication converted to addition for variable '{java['var']}'",
                    java_snippet=f"{java['var']} = {java_expr}",
                    bedrock_snippet=f"{bedrock['var']} = {bedrock_expr}",
                    expected_behavior=f"Java: {java['var']} should scale by {java_coef}x",
                    actual_behavior=f"Bedrock: {bedrock['var']} adds {bedrock_add} instead",
                )

        java_mult_matches = re.findall(r"(\w+)\s*\*\s*(\d+\.?\d*)", java_expr)
        bedrock_add_matches = re.findall(r"(\w+)\s*\+\s*(\d+\.?\d*)", bedrock_expr)
        if java_mult_matches and bedrock_add_matches:
            java_vars = {m[0] for m in java_mult_matches}
            bedrock_vars = {m[0] for m in bedrock_add_matches}
            if java_vars & bedrock_vars:
                return AuditFinding(
                    check_type=self.check_type,
                    severity=Severity.HIGH,
                    description="Coefficient drift: multiplication pattern in Java became addition in Bedrock",
                    java_snippet=f"{java['var']} = {java_expr}",
                    bedrock_snippet=f"{bedrock['var']} = {bedrock_expr}",
                    expected_behavior=f"Value should be multiplied: {java_mult_matches}",
                    actual_behavior=f"Value is being added: {bedrock_add_matches}",
                )

        return None


class ProbabilityInversionChecker:
    """Checks for comparison direction and threshold value errors in probability/RNG code."""

    JAVA_RANDOM_PATTERNS = [
        r"random\.nextDouble\(\)\s*([<>]=?)\s*([\d.]+)",
        r"Math\.random\(\)\s*([<>]=?)\s*([\d.]+)",
        r"Random\(\)\.nextFloat\(\)\s*([<>]=?)\s*([\d.]+)",
        r"random\s*([<>]=?)\s*([\d.]+)",  # bare random variable like "random >= 0.5"
    ]

    BEDROCK_RANDOM_PATTERNS = [
        r"Math\.random\(\)\s*([<>]=?)\s*([\d.]+)",
        r"this\.world\.getRandom\(\)\.nextFloat\(\)\s*([<>]=?)\s*([\d.]+)",
    ]

    def __init__(self):
        self.check_type = "probability_inversion"

    def check(self, java_code: str, bedrock_code: str) -> List[AuditFinding]:
        findings = []
        java_probs = self._extract_probabilities(java_code, is_java=True)
        bedrock_probs = self._extract_probabilities(bedrock_code, is_java=False)

        for java_prob in java_probs:
            for bedrock_prob in bedrock_probs:
                finding = self._compare_probability(java_prob, bedrock_prob)
                if finding:
                    findings.append(finding)
        return findings

    def _extract_probabilities(self, code: str, is_java: bool) -> List[Dict[str, Any]]:
        probabilities = []
        patterns = self.JAVA_RANDOM_PATTERNS if is_java else self.BEDROCK_RANDOM_PATTERNS
        lines = code.split("\n")
        for i, line in enumerate(lines, start=1):
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    operator = match.group(1)
                    threshold = float(match.group(2))
                    context = line.strip()
                    probabilities.append(
                        {
                            "operator": operator,
                            "threshold": threshold,
                            "line": i,
                            "context": context,
                            "inverted": False,
                        }
                    )
        return probabilities

    def _compare_probability(self, java_prob: Dict, bedrock_prob: Dict) -> Optional[AuditFinding]:
        java_op = java_prob["operator"]
        bedrock_op = bedrock_prob["operator"]

        opposites = {"<": ">", ">": "<", "<=": ">=", ">=": "<="}

        if opposites.get(java_op) == bedrock_op:
            return AuditFinding(
                check_type=self.check_type,
                severity=Severity.HIGH,
                description=f"Probability comparison inverted: '{java_op}' in Java became '{bedrock_op}' in Bedrock",
                java_snippet=java_prob["context"],
                bedrock_snippet=bedrock_prob["context"],
                expected_behavior=f"Java triggers when random {java_op} {java_prob['threshold']}",
                actual_behavior=f"Bedrock triggers when random {bedrock_op} {bedrock_prob['threshold']} (inverted!)",
            )

        if abs(java_prob["threshold"] - bedrock_prob["threshold"]) > 0.001:
            return AuditFinding(
                check_type=self.check_type,
                severity=Severity.HIGH,
                description=f"Probability threshold modified: Java uses {java_prob['threshold']}, Bedrock uses {bedrock_prob['threshold']}",
                java_snippet=java_prob["context"],
                bedrock_snippet=bedrock_prob["context"],
                expected_behavior=f"Should trigger at probability {java_prob['threshold']}",
                actual_behavior=f"Triggers at probability {bedrock_prob['threshold']}",
            )

        return None


class EventHookMismatchChecker:
    """Checks for lifecycle stage and trigger condition mismatches between Java and Bedrock."""

    JAVA_EVENT_HOOKS = {
        "BREAK_BLOCK": ["onBlockDestroyed", "onDestroy", "onBreak", "destroyBlock"],
        "INTERACT": ["onInteract", "onUse", "onPlayerInteract", "useItem"],
        "ATTACK": ["onAttack", "onEntityHit", "onHit", "attackEntity"],
        "SPAWN": ["onSpawn", "onCreated", "onInitialize", "onLoad"],
        "TICK": ["onTick", "update", "onUpdate", "tick"],
        "DAMAGE": ["onDamage", "onEntityDamage", "onHurt", "onTakeDamage"],
    }

    BEDROCK_EVENT_HOOKS = {
        "step_on": ["onStepOn", "onPlayerInteractWithBlock"],
        "interact": ["onInteract", "onUseItem", "onItemUse"],
        "attack": ["onAttack", "onHurtEntity", "onEntityAttack"],
        "spawn": ["onSpawn", "initialize", "onInitialize"],
        "tick": ["onTick", "tick", "onTick"],
        "break_block": ["onBlockDestroyed", "onDestroyBlock", "onBreakBlock"],
    }

    JAVA_TO_BEDROCK_HOOK_MAP = {
        "BREAK_BLOCK": "break_block",
        "INTERACT": "interact",
        "ATTACK": "attack",
        "SPAWN": "spawn",
        "TICK": "tick",
        "DAMAGE": "interact",
    }

    def __init__(self):
        self.check_type = "event_hook_mismatch"

    def check(self, java_code: str, bedrock_code: str) -> List[AuditFinding]:
        findings = []
        java_hooks = self._extract_java_hooks(java_code)
        bedrock_hooks = self._extract_bedrock_hooks(bedrock_code)
        bedrock_hook_names = {h for h, _ in bedrock_hooks}

        for java_hook, context in java_hooks:
            java_event_type = self._classify_java_hook(java_hook)
            if java_event_type:
                correct_bedrock_hooks = self.BEDROCK_EVENT_HOOKS.get(
                    self.JAVA_TO_BEDROCK_HOOK_MAP.get(java_event_type, ""), []
                )
                if correct_bedrock_hooks:
                    has_correct_hook = any(
                        correct_hook in bedrock_hook_names for correct_hook in correct_bedrock_hooks
                    )
                    if not has_correct_hook and bedrock_hook_names:
                        wrong_hook = list(bedrock_hook_names)[0]
                        finding = AuditFinding(
                            check_type=self.check_type,
                            severity=Severity.HIGH,
                            description=f"Event hook mismatch: Java uses '{java_hook}' which should map to one of {correct_bedrock_hooks} but Bedrock uses '{wrong_hook}'",
                            java_snippet=context,
                            bedrock_snippet=self._get_bedrock_context(bedrock_code, wrong_hook),
                            expected_behavior=f"Event should trigger on one of {correct_bedrock_hooks}",
                            actual_behavior=f"Event is hooked to {wrong_hook}, which is wrong lifecycle",
                        )
                        findings.append(finding)
        return findings

    def _extract_java_hooks(self, code: str) -> List[Tuple[str, str]]:
        hooks = []
        for event_family, hook_names in self.JAVA_EVENT_HOOKS.items():
            for hook_name in hook_names:
                pattern = rf"public\s+void\s+{hook_name}\s*\("
                for i, line in enumerate(code.split("\n"), start=1):
                    if re.search(pattern, line):
                        hooks.append((hook_name, line.strip()))
        return hooks

    def _extract_bedrock_hooks(self, code: str) -> List[Tuple[str, str]]:
        hooks = []
        for hook_family, hook_names in self.BEDROCK_EVENT_HOOKS.items():
            for hook_name in hook_names:
                hook_name_lower = hook_name.lower()
                for i, line in enumerate(code.split("\n"), start=1):
                    line_lower = line.lower()
                    if (
                        hook_name_lower in line_lower
                        or f"'{hook_name}'" in line
                        or f"this.{hook_name}" in line
                    ):
                        hooks.append((hook_name, line.strip()))
        return hooks

    def _classify_java_hook(self, hook_name: str) -> Optional[str]:
        for event_type, hook_names in self.JAVA_EVENT_HOOKS.items():
            if hook_name in hook_names:
                return event_type
        return None

    def _get_bedrock_context(self, code: str, hook_name: str) -> str:
        for line in code.split("\n"):
            if hook_name in line:
                return line.strip()
        return f"<hook {hook_name} not found in code>"


class ConditionalNegationChecker:
    """Checks for negation drift and operator substitution in conditionals."""

    def __init__(self):
        self.check_type = "conditional_negation"

    def check(self, java_code: str, bedrock_code: str) -> List[AuditFinding]:
        findings = []
        java_conditionals = self._extract_conditionals(java_code, is_java=True)
        bedrock_conditionals = self._extract_conditionals(bedrock_code, is_java=False)

        for java_cond in java_conditionals:
            for bedrock_cond in bedrock_conditionals:
                finding = self._compare_conditionals(java_cond, bedrock_cond)
                if finding:
                    findings.append(finding)
        return findings

    def _extract_conditionals(self, code: str, is_java: bool) -> List[Dict[str, Any]]:
        conditionals = []
        patterns = [
            r"if\s*\(([^)]+)\)",
            r"else\s+if\s*\(([^)]+)\)",
            r"while\s*\(([^)]+)\)",
            r"for\s*\([^)]*;\s*([^;]+);",
        ]

        lines = code.split("\n")
        for i, line in enumerate(lines, start=1):
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    condition = match.group(1).strip()
                    conditionals.append(
                        {
                            "condition": condition,
                            "line": i,
                            "context": line.strip(),
                        }
                    )
        return conditionals

    def _compare_conditionals(self, java_cond: Dict, bedrock_cond: Dict) -> Optional[AuditFinding]:
        java_cond_str = java_cond["condition"]
        bedrock_cond_str = bedrock_cond["condition"]

        java_has_and = "&&" in java_cond_str
        bedrock_has_or = "||" in bedrock_cond_str

        if java_has_and and bedrock_has_or:
            return AuditFinding(
                check_type=self.check_type,
                severity=Severity.HIGH,
                description="Conditional operator drift: '&&' in Java became '||' in Bedrock",
                java_snippet=java_cond["context"],
                bedrock_snippet=bedrock_cond["context"],
                expected_behavior=f"Java: both conditions must be true: {java_cond_str}",
                actual_behavior=f"Bedrock: either condition triggers (changed logic): {bedrock_cond_str}",
            )

        java_operators = re.findall(r"([<>=!]+)", java_cond_str)
        bedrock_operators = re.findall(r"([<>=!]+)", bedrock_cond_str)

        opposites = {"<": ">", ">": "<", "<=": ">=", ">=": "<="}
        for java_op in java_operators:
            if java_op in opposites:
                if opposites[java_op] in bedrock_operators:
                    return AuditFinding(
                        check_type=self.check_type,
                        severity=Severity.HIGH,
                        description=f"Comparison operator inverted: '{java_op}' became '{opposites[java_op]}'",
                        java_snippet=java_cond["context"],
                        bedrock_snippet=bedrock_cond["context"],
                        expected_behavior=f"Java condition: {java_cond_str}",
                        actual_behavior=f"Bedrock condition: {bedrock_cond_str} (inverted!)",
                    )

        return None


class ResourceIDMatchChecker:
    """Checks for namespace match and ID case sensitivity issues."""

    def __init__(self):
        self.check_type = "resource_id_match"

    def check(self, java_code: str, bedrock_code: str) -> List[AuditFinding]:
        findings = []
        java_ids = self._extract_resource_ids(java_code)
        bedrock_ids = self._extract_resource_ids(bedrock_code)

        for java_ns, java_id in java_ids:
            for bedrock_ns, bedrock_id in bedrock_ids:
                if java_id.lower() == bedrock_id.lower() and java_id != bedrock_id:
                    findings.append(
                        AuditFinding(
                            check_type=self.check_type,
                            severity=Severity.MEDIUM,
                            description=f"Resource ID case mismatch: '{java_id}' vs '{bedrock_id}'",
                            java_snippet=f"{java_ns}:{java_id}",
                            bedrock_snippet=f"{bedrock_ns}:{bedrock_id}",
                            expected_behavior=f"ID should be '{java_id}'",
                            actual_behavior=f"ID is '{bedrock_id}' (case difference)",
                        )
                    )
        return findings

    def _extract_resource_ids(self, code: str) -> List[Tuple[str, str]]:
        ids = []
        patterns = [
            r"\"([a-zA-Z_]+):([a-zA-Z_]+)\"",
            r"'([a-zA-Z_]+):([a-zA-Z_]+)'",
            r"identifier\s*:\s*\"([a-zA-Z_]+):([a-zA-Z_]+)\"",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, code)
            for namespace, resource_id in matches:
                ids.append((namespace, resource_id))
        return ids


ADVERSARIAL_CHECKS = {
    SemanticType.NUMERIC_FORMULA: FormulaDriftChecker(),
    SemanticType.PROBABILITY_RNG: ProbabilityInversionChecker(),
    SemanticType.EVENT_HOOK: EventHookMismatchChecker(),
    SemanticType.CONDITIONAL: ConditionalNegationChecker(),
    SemanticType.RESOURCE_ID: ResourceIDMatchChecker(),
}


class LogicAuditorAgent:
    """
    Adversarial Logic Auditor Agent.

    Detects subtle functional discrepancies that pass syntax/schema checks
    but silently break gameplay behavior. Based on ASMR-Bench framework.
    """

    def __init__(self, temperature: float = TEMPERATURE_ZERO):
        self.temperature = temperature
        self.checks = ADVERSARIAL_CHECKS
        logger.info("LogicAuditorAgent initialized", checks=list(self.checks.keys()))

    def _classify_semantic_type(self, code: str) -> List[SemanticType]:
        """Classify which semantic types are present in the code."""
        types = []

        if re.search(r"\*\s*\d+\.?\d*|random.*[<>]", code):
            if "random" in code.lower() or "probability" in code.lower():
                types.append(SemanticType.PROBABILITY_RNG)
            else:
                types.append(SemanticType.NUMERIC_FORMULA)

        if re.search(r"onBlock|onEntity|onPlayer|onInteract|onTick", code, re.IGNORECASE):
            types.append(SemanticType.EVENT_HOOK)

        if re.search(r"if\s*\([^)]*&&", code) or re.search(r"if\s*\([^)]*\|\|", code):
            types.append(SemanticType.CONDITIONAL)

        if re.search(r"[a-z_]+:[a-z_]+", code):
            types.append(SemanticType.RESOURCE_ID)

        return types if types else [SemanticType.UNKNOWN]

    def _run_checks_for_type(
        self, semantic_type: SemanticType, java_code: str, bedrock_code: str
    ) -> List[AuditFinding]:
        """Run checks for a specific semantic type."""
        checker = self.checks.get(semantic_type)
        if checker:
            return checker.check(java_code, bedrock_code)
        return []

    def _generate_audit_report(
        self, findings: List[AuditFinding], semantic_types: List[SemanticType]
    ) -> AuditReport:
        """Generate an audit report from findings."""
        report = AuditReport()

        for finding in findings:
            report.findings.append(finding)
            if finding.severity == Severity.HIGH:
                report.high_severity_count += 1
            elif finding.severity == Severity.MEDIUM:
                report.medium_severity_count += 1
            else:
                report.low_severity_count += 1

        report.blocked = report.high_severity_count > 0

        confidence_impact = (
            report.high_severity_count * 15.0
            + report.medium_severity_count * 5.0
            + report.low_severity_count * 1.0
        )
        report.confidence_impact = min(confidence_impact, 50.0)

        return report

    def execute(self, context: QAContext) -> AgentOutput:
        """
        Execute the adversarial logic auditor on the given QA context.

        Args:
            context: QA context containing job information and paths

        Returns:
            AgentOutput with audit results
        """
        start_time = time.time()

        try:
            logger.info("LogicAuditorAgent executing", job_id=context.job_id)

            java_path = context.source_java_path
            bedrock_path = context.output_bedrock_path

            if not java_path.exists():
                return AgentOutput(
                    agent_name="logic_auditor",
                    success=False,
                    result={},
                    errors=[f"Java source not found: {java_path}"],
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            java_code = java_path.read_text(encoding="utf-8") if java_path.is_file() else ""
            bedrock_code = self._read_bedrock_code(bedrock_path)

            if not java_code and not bedrock_code:
                return AgentOutput(
                    agent_name="logic_auditor",
                    success=False,
                    result={},
                    errors=["No Java or Bedrock code found"],
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            semantic_types = self._classify_semantic_type(java_code)

            all_findings = []
            for sem_type in semantic_types:
                findings = self._run_checks_for_type(sem_type, java_code, bedrock_code)
                all_findings.extend(findings)

            if semantic_types == [SemanticType.UNKNOWN] or not semantic_types:
                for check_type, checker in self.checks.items():
                    findings = checker.check(java_code, bedrock_code)
                    all_findings.extend(findings)

            audit_report = self._generate_audit_report(all_findings, semantic_types)

            result = {
                "audit_report": audit_report.to_dict(),
                "semantic_types_detected": [st.value for st in semantic_types],
                "checks_run": len(semantic_types)
                if semantic_types != [SemanticType.UNKNOWN]
                else len(self.checks),
                "blocked": audit_report.blocked,
                "confidence_impact": audit_report.confidence_impact,
            }

            context.validation_results["logic_auditor"] = {
                "success": not audit_report.blocked,
                "report": audit_report.to_dict(),
                "findings_count": len(all_findings),
                "high_severity": audit_report.high_severity_count,
            }

            execution_time = int((time.time() - start_time) * 1000)

            output_data = {
                "agent_name": "logic_auditor",
                "success": not audit_report.blocked,
                "result": result,
                "errors": [f.description for f in all_findings if f.severity == Severity.HIGH],
                "execution_time_ms": execution_time,
            }

            validated = validate_agent_output(output_data)

            logger.info(
                "LogicAuditorAgent completed",
                job_id=context.job_id,
                findings=len(all_findings),
                blocked=audit_report.blocked,
            )

            return validated

        except Exception as e:
            logger.error("LogicAuditorAgent failed", job_id=context.job_id, error=str(e))
            return AgentOutput(
                agent_name="logic_auditor",
                success=False,
                result={},
                errors=[str(e)],
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    def _read_bedrock_code(self, bedrock_path: Path) -> str:
        """Read all Bedrock code from path (file or directory)."""
        if bedrock_path.is_file():
            return bedrock_path.read_text(encoding="utf-8")
        elif bedrock_path.is_dir():
            code_parts = []
            for f in bedrock_path.rglob("*.ts"):
                code_parts.append(f.read_text(encoding="utf-8"))
            for f in bedrock_path.rglob("*.js"):
                code_parts.append(f.read_text(encoding="utf-8"))
            for f in bedrock_path.rglob("*.json"):
                if "manifest" not in f.name.lower():
                    code_parts.append(f.read_text(encoding="utf-8"))
            return "\n".join(code_parts)
        return ""


def audit_conversion(context: QAContext) -> AgentOutput:
    """
    Convenience function to run adversarial logic audit.

    Args:
        context: QA context

    Returns:
        AgentOutput with audit results
    """
    agent = LogicAuditorAgent()
    return agent.execute(context)


class LLMLogicAuditor:
    """
    LLM-powered adversarial logic auditor for deeper analysis.

    Uses LLM to compare Java source intent with Bedrock output behavior
    for detecting subtle logic errors that pattern-based checks might miss.
    """

    _instance = None

    def __init__(self):
        self._llm = None
        self._initialized = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize(self):
        """Initialize LLM backend."""
        if self._initialized:
            return

        try:
            from utils.rate_limiter import get_llm_backend

            self._llm = get_llm_backend()
            logger.info("LLM initialized for logic auditing")
        except Exception as e:
            logger.warning(f"LLM not available: {e}")
            self._llm = None

        self._initialized = True

    def _call_llm(self, prompt: str, system_prompt: str) -> Optional[str]:
        """Call LLM with prompt."""
        if not self._initialized:
            self.initialize()

        if self._llm is None:
            return None

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
            response = self._llm.invoke(messages)
            content = response.content if hasattr(response, "content") else str(response)
            return str(content) if content else None
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return None

    def deep_audit(
        self, java_source: str, bedrock_output: str, context: str = ""
    ) -> Dict[str, Any]:
        """
        Use LLM to perform deep adversarial audit.

        Args:
            java_source: Original Java source code
            bedrock_output: Generated Bedrock code
            context: Additional context about conversion

        Returns:
            Dict with LLM audit results
        """
        system_prompt = """You are an adversarial logic auditor specializing in detecting subtle bugs
in code conversions between Java Minecraft mods and Bedrock addons.

Your task is to find bugs that:
1. Pass syntax validation
2. Pass schema validation
3. But produce WRONG gameplay behavior

Common patterns to detect:
- Formula errors: `base * 1.5` → `base + 1.5` (multiplication becomes addition)
- Probability inversion: `random < 0.05` → `random > 0.05` (inverted spawn chance)
- Event hook mismatch: `BREAK_BLOCK` → `on_step_on` (wrong lifecycle hook)
- Conditional negation: `a && b` → `a || b` (AND becomes OR)
- Resource ID case: `minecraft:stone` → `minecraft:STONE` (case sensitivity)

Respond with JSON:
{
  "adversarial_findings": [
    {
      "check_type": "formula_drift|probability_inversion|event_hook_mismatch|conditional_negation|resource_id_match",
      "severity": "high|medium|low",
      "description": "What the bug is",
      "java_snippet": "The problematic Java line",
      "bedrock_snippet": "The converted Bedrock line",
      "expected_behavior": "What should happen",
      "actual_behavior": "What actually happens",
      "gameplay_impact": "Why this matters for players"
    }
  ],
  "overall_assessment": "Summary of conversion quality",
  "blocked": true/false,
  "confidence_impact": 0-50
}"""

        prompt = f"""Perform adversarial audit on this conversion:

=== Java Source ===
{java_source[:4000]}

=== Generated Bedrock Output ===
{bedrock_output[:4000]}

=== Context ===
{context or "Java to Bedrock mod conversion"}

Look for subtle bugs that pass validation but break gameplay.
Focus on: formulas, probability comparisons, event hooks, conditionals, resource IDs."""

        response = self._call_llm(prompt, system_prompt)

        if response is None:
            return {
                "success": False,
                "error": "LLM not available",
                "adversarial_findings": [],
            }

        try:
            import json

            analysis = json.loads(response)
            return {
                "success": True,
                "adversarial_findings": analysis.get("adversarial_findings", []),
                "overall_assessment": analysis.get("overall_assessment", ""),
                "blocked": analysis.get("blocked", False),
                "confidence_impact": analysis.get("confidence_impact", 0),
            }
        except json.JSONDecodeError:
            return {
                "success": True,
                "adversarial_findings": [],
                "raw_response": response[:500],
            }


def deep_audit_conversion(
    java_source: str, bedrock_output: str, context: str = ""
) -> Dict[str, Any]:
    """
    Convenience function to run LLM-powered deep audit.

    Args:
        java_source: Original Java source code
        bedrock_output: Generated Bedrock code
        context: Additional context

    Returns:
        Dict with deep audit results
    """
    auditor = LLMLogicAuditor.get_instance()
    return auditor.deep_audit(java_source, bedrock_output, context)
