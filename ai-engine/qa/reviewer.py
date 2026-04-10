"""
Reviewer Agent for QA pipeline.

Validates code quality, style, and best practices for Bedrock output.
This is the second QA agent (QA-03) in the multi-agent pipeline.
"""

import json
import subprocess
import time
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

import structlog

from qa.context import QAContext
from qa.validators import AgentOutput, validate_agent_output

logger = structlog.get_logger(__name__)

TEMPERATURE_ZERO = 0.0


SCRIPT_API_METHODS = {
    "Entity",
    "Block",
    "BlockPermutation",
    "BlockVolume",
    "Container",
    "Direction",
    "Effect",
    "EntityInventoryComponent",
    "EquipmentSlot",
    "GameMode",
    "ItemStack",
    "ItemUse",
    "LeverAction",
    "Location",
    "Player",
    "Predicate",
    "Properties",
    "PropertyRule",
    "Raycast",
    "Scoreboard",
    "Timer",
    "Vector",
    "World",
    "addEffect",
    "applyDamage",
    "destroyBlock",
    "getBlock",
    "getComponent",
    "getEntities",
    "getItemStack",
    "getPlayers",
    "getPosition",
    "hasComponent",
    "isValid",
    "kill",
    "playSound",
    "runCommand",
    "sendMessage",
    "setBlock",
    "spawnEntity",
    "triggerEvent",
}


class ValidationIssue:
    def __init__(
        self,
        issue_type: str,
        message: str,
        line: Optional[int] = None,
        column: Optional[int] = None,
        severity: str = "error",
        file_path: Optional[str] = None,
        fix_suggestion: Optional[str] = None,
    ):
        self.issue_type = issue_type
        self.message = message
        self.line = line
        self.column = column
        self.severity = severity
        self.file_path = file_path
        self.fix_suggestion = fix_suggestion

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.issue_type,
            "message": self.message,
            "line": self.line,
            "column": self.column,
            "severity": self.severity,
            "file_path": self.file_path,
            "fix_suggestion": self.fix_suggestion,
        }


class ReviewerAgent:
    """
    Reviewer Agent - validates code quality, style, and best practices for Bedrock output.

    Takes translated output from the Translator Agent and validates it against:
    - ESLint/TSLint style rules
    - Bedrock JSON schema validation
    - TypeScript type checking
    - Script API method usage verification
    """

    def __init__(self, temperature: float = TEMPERATURE_ZERO):
        self.temperature = temperature
        logger.info("ReviewerAgent initialized", temperature=temperature)

    def _run_command(self, cmd: List[str], cwd: Optional[Path] = None) -> tuple:
        """Run a command and return (success, stdout, stderr)."""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.returncode == 0, result.stdout, result.stderr
        except FileNotFoundError:
            return False, "", f"Command not found: {cmd[0]}"
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out: {' '.join(cmd)}"
        except Exception as e:
            return False, "", str(e)

    def _run_eslint(self, ts_path: Path) -> List[ValidationIssue]:
        """Run ESLint on TypeScript files."""
        issues = []

        if not ts_path.exists():
            return [ValidationIssue("missing_file", f"TypeScript file not found: {ts_path}")]

        success, stdout, stderr = self._run_command(
            ["npx", "eslint", str(ts_path), "--format=json"], cwd=ts_path.parent
        )

        if not success:
            output = stdout + stderr

            try:
                eslint_results = json.loads(output) if output.startswith("[") else []
                for file_result in eslint_results:
                    for msg in file_result.get("messages", []):
                        issues.append(
                            ValidationIssue(
                                issue_type="eslint",
                                message=msg.get("message", "ESLint error"),
                                line=msg.get("line"),
                                column=msg.get("column"),
                                severity=msg.get("severity", 1) >= 2 and "error" or "warning",
                                file_path=ts_path.name,
                                fix_suggestion=msg.get("fix", {}).get("range"),
                            )
                        )
            except (json.JSONDecodeError, ValueError):
                for line in output.split("\n"):
                    match = re.search(r"(\d+):(\d+)\s+(error|warning|info)\s+(.+)", line)
                    if match:
                        issues.append(
                            ValidationIssue(
                                issue_type="eslint",
                                message=match.group(4),
                                line=int(match.group(1)),
                                column=int(match.group(2)),
                                severity=match.group(3),
                                file_path=ts_path.name,
                            )
                        )

        return issues

    def _run_tsc(self, ts_path: Path) -> List[ValidationIssue]:
        """Run TypeScript compiler for type checking."""
        issues = []

        if not ts_path.exists():
            return []

        temp_dir = ts_path.parent / ".reviewer_temp"
        temp_dir.mkdir(exist_ok=True)

        tsconfig = temp_dir / "tsconfig.json"
        tsconfig.write_text(
            json.dumps(
                {
                    "compilerOptions": {
                        "strict": True,
                        "noEmit": True,
                        "target": "ES2020",
                        "module": "ESNext",
                        "moduleResolution": "node",
                        "skipLibCheck": True,
                    },
                    "include": [str(ts_path.name)],
                }
            )
        )

        try:
            success, stdout, stderr = self._run_command(
                ["npx", "tsc", "--noEmit", "--project", str(temp_dir)],
                cwd=ts_path.parent,
            )

            if not success:
                output = stdout + stderr
                for line in output.split("\n"):
                    match = re.search(
                        r"(\S+\.ts)\((\d+),(\d+)\):\s+(error|warning)\s+TS\d+:\s+(.+)", line
                    )
                    if match:
                        issues.append(
                            ValidationIssue(
                                issue_type="typescript",
                                message=match.group(5),
                                line=int(match.group(2)),
                                column=int(match.group(3)),
                                severity=match.group(4),
                                file_path=match.group(1),
                            )
                        )
        finally:
            import shutil

            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

        return issues

    def _validate_json_schemas(self, output_dir: Path) -> List[ValidationIssue]:
        """Validate generated JSON files against Bedrock schemas."""
        issues = []

        if not output_dir.exists():
            return [ValidationIssue("missing_dir", f"Output directory not found: {output_dir}")]

        schema_path = output_dir / "blocks"
        item_path = output_dir / "items"
        entity_path = output_dir / "entities"

        for category, category_path, required_keys in [
            ("block", schema_path, ["format_version", "minecraft:block"]),
            ("item", item_path, ["format_version", "minecraft:item"]),
            ("entity", entity_path, ["format_version", "minecraft:entity"]),
        ]:
            if not category_path.exists():
                continue

            for json_file in category_path.glob("*.json"):
                try:
                    data = json.loads(json_file.read_text(encoding="utf-8"))

                    for key in required_keys:
                        if key not in data:
                            issues.append(
                                ValidationIssue(
                                    issue_type="schema",
                                    message=f"Missing required key '{key}' in {category} schema",
                                    severity="error",
                                    file_path=str(json_file.relative_to(output_dir)),
                                )
                            )

                    if category == "block":
                        if "description" not in data.get("minecraft:block", {}):
                            issues.append(
                                ValidationIssue(
                                    issue_type="schema",
                                    message=f"Missing 'description' in block",
                                    severity="error",
                                    file_path=str(json_file.relative_to(output_dir)),
                                )
                            )
                        elif "identifier" not in data["minecraft:block"]["description"]:
                            issues.append(
                                ValidationIssue(
                                    issue_type="schema",
                                    message=f"Missing 'identifier' in block description",
                                    severity="error",
                                    file_path=str(json_file.relative_to(output_dir)),
                                )
                            )

                    if category == "item":
                        if "description" not in data.get("minecraft:item", {}):
                            issues.append(
                                ValidationIssue(
                                    issue_type="schema",
                                    message=f"Missing 'description' in item",
                                    severity="error",
                                    file_path=str(json_file.relative_to(output_dir)),
                                )
                            )

                except json.JSONDecodeError as e:
                    issues.append(
                        ValidationIssue(
                            issue_type="json_parse",
                            message=f"Invalid JSON: {str(e)}",
                            severity="error",
                            file_path=str(json_file.relative_to(output_dir)),
                        )
                    )
                except Exception as e:
                    issues.append(
                        ValidationIssue(
                            issue_type="validation",
                            message=f"Validation error: {str(e)}",
                            severity="warning",
                            file_path=str(json_file.relative_to(output_dir)),
                        )
                    )

        return issues

    def _verify_script_api_usage(self, ts_path: Path) -> List[ValidationIssue]:
        """Verify Script API method usage is valid."""
        issues = []

        if not ts_path.exists():
            return []

        try:
            content = ts_path.read_text(encoding="utf-8")

            known_api_patterns = []
            for method in SCRIPT_API_METHODS:
                if method[0].isupper():
                    known_api_patterns.append(method)

            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                if "import" in line:
                    for api in known_api_patterns:
                        if f"from '{api}'" in line or f'from "{api}"' in line:
                            pass

                if "Minecraft" in line or "minecraft" in line:
                    if not any(
                        api in line
                        for api in ["Entity", "Block", "Item", "World", "Player", "ItemStack"]
                    ):
                        if "Minecraft" in line:
                            issues.append(
                                ValidationIssue(
                                    issue_type="script_api",
                                    message="Non-standard Minecraft API usage detected",
                                    line=i,
                                    severity="warning",
                                    file_path=ts_path.name,
                                    fix_suggestion="Use standard Script API: Entity, Block, ItemStack, Player, World",
                                )
                            )

            identifiers = set(re.findall(r"\b([A-Z][a-zA-Z0-9_]*)\b", content))
            unknown_apis = (
                identifiers
                - SCRIPT_API_METHODS
                - {
                    "console",
                    "JSON",
                    "Math",
                    "Date",
                    "Array",
                    "Object",
                    "String",
                    "Number",
                    "Boolean",
                    "Map",
                    "Set",
                    "Promise",
                    "undefined",
                    "null",
                    "true",
                    "false",
                }
            )

            for api in unknown_apis:
                if any(keyword in api.lower() for keyword in ["minecraft", "bedrock", "mojang"]):
                    issues.append(
                        ValidationIssue(
                            issue_type="script_api",
                            message=f"Unknown API reference: {api}",
                            severity="warning",
                            file_path=ts_path.name,
                            fix_suggestion=f"Verify {api} is a valid Bedrock Script API method",
                        )
                    )

        except Exception as e:
            issues.append(
                ValidationIssue(
                    issue_type="analysis",
                    message=f"Failed to analyze Script API usage: {str(e)}",
                    severity="info",
                )
            )

        return issues

    def _calculate_quality_score(self, issues: List[ValidationIssue]) -> int:
        """Calculate quality score (0-100) based on validation issues."""
        score = 100

        for issue in issues:
            if issue.severity == "error":
                score -= 10
            elif issue.severity == "warning":
                score -= 3
            elif issue.severity == "info":
                score -= 1

        return max(0, score)

    def _generate_fix_suggestions(self, issues: List[ValidationIssue]) -> Dict[str, List[str]]:
        """Generate auto-fix suggestions for common issues."""
        suggestions = {}

        error_counts = {"eslint": 0, "typescript": 0, "schema": 0, "script_api": 0, "json_parse": 0}
        for issue in issues:
            if issue.issue_type in error_counts:
                error_counts[issue.issue_type] += 1

        if error_counts["eslint"] > 0:
            suggestions["eslint"] = [
                "Run 'npx eslint --fix' to auto-fix common style issues",
                "Consider configuring ESLint with project-specific rules",
            ]

        if error_counts["typescript"] > 0:
            suggestions["typescript"] = [
                "Run 'npx tsc --noEmit' to see detailed type errors",
                "Add proper type annotations to resolve type issues",
            ]

        if error_counts["schema"] > 0:
            suggestions["schema"] = [
                "Ensure all Bedrock JSON files have required format_version and minecraft:* keys",
                "Use provided templates from agents/logic_translator.py for valid schemas",
            ]

        if error_counts["script_api"] > 0:
            suggestions["script_api"] = [
                "Verify all Script API method calls are from the official Bedrock API",
                "Check https://docs.microsoft.com/minecraft/creator/scriptapi for valid methods",
            ]

        return suggestions

    def execute(self, context: QAContext) -> AgentOutput:
        """
        Execute the reviewer agent on the given QA context.

        Args:
            context: QA context containing job information and paths

        Returns:
            AgentOutput with review results
        """
        start_time = time.time()

        try:
            logger.info("ReviewerAgent executing", job_id=context.job_id)

            output_dir = context.output_bedrock_path
            ts_files = list(output_dir.rglob("*.ts"))

            all_issues: List[ValidationIssue] = []

            for ts_path in ts_files:
                all_issues.extend(self._run_eslint(ts_path))
                all_issues.extend(self._run_tsc(ts_path))
                all_issues.extend(self._verify_script_api_usage(ts_path))

            if ts_files:
                json_issues = self._validate_json_schemas(output_dir)
                all_issues.extend(json_issues)
            else:
                all_issues.append(
                    ValidationIssue(
                        issue_type="missing_output",
                        message="No TypeScript files found for review",
                        severity="warning",
                    )
                )

            quality_score = self._calculate_quality_score(all_issues)
            fix_suggestions = self._generate_fix_suggestions(all_issues)

            error_count = sum(1 for i in all_issues if i.severity == "error")
            warning_count = sum(1 for i in all_issues if i.severity == "warning")
            info_count = sum(1 for i in all_issues if i.severity == "info")

            result = {
                "quality_score": quality_score,
                "total_issues": len(all_issues),
                "error_count": error_count,
                "warning_count": warning_count,
                "info_count": info_count,
                "issues": [i.to_dict() for i in all_issues],
                "fix_suggestions": fix_suggestions,
                "files_reviewed": [str(p.relative_to(output_dir)) for p in ts_files],
            }

            context.validation_results["reviewer"] = {
                "quality_score": quality_score,
                "passed": quality_score >= 70 and error_count == 0,
            }

            execution_time = int((time.time() - start_time) * 1000)

            output_data = {
                "agent_name": "reviewer",
                "success": quality_score >= 70 and error_count == 0,
                "result": result,
                "errors": [i.message for i in all_issues if i.severity == "error"],
                "execution_time_ms": execution_time,
            }

            validated = validate_agent_output(output_data)

            logger.info(
                "ReviewerAgent completed",
                job_id=context.job_id,
                score=quality_score,
                errors=error_count,
                warnings=warning_count,
            )

            return validated

        except Exception as e:
            logger.error("ReviewerAgent failed", job_id=context.job_id, error=str(e))
            return AgentOutput(
                agent_name="reviewer",
                success=False,
                result={},
                errors=[str(e)],
                execution_time_ms=int((time.time() - start_time) * 1000),
            )


def review(context: QAContext) -> AgentOutput:
    """
    Convenience function to run review.

    Args:
        context: QA context

    Returns:
        AgentOutput with review results
    """
    agent = ReviewerAgent()
    return agent.execute(context)
