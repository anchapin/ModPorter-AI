"""
Fixer Agent for QA pipeline.

Attempts to auto-fix issues found by Reviewer Agent.
This is the third QA agent (QA-04) in the multi-agent pipeline.
"""

import json
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import structlog

from qa.context import QAContext
from qa.validators import AgentOutput, validate_agent_output

logger = structlog.get_logger(__name__)

TEMPERATURE_ZERO = 0.0


class FixResult:
    def __init__(
        self,
        issue_type: str,
        original_message: str,
        fix_applied: bool,
        fix_description: Optional[str] = None,
        file_path: Optional[str] = None,
        line: Optional[int] = None,
    ):
        self.issue_type = issue_type
        self.original_message = original_message
        self.fix_applied = fix_applied
        self.fix_description = fix_description
        self.file_path = file_path
        self.line = line

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_type": self.issue_type,
            "original_message": self.original_message,
            "fix_applied": self.fix_applied,
            "fix_description": self.fix_description,
            "file_path": self.file_path,
            "line": self.line,
        }


class FixerAgent:
    """
    Fixer Agent - attempts to auto-fix issues found by Reviewer Agent.

    Takes review results from the Reviewer Agent and attempts to automatically fix:
    - ESLint/TSLint issues
    - JSON schema errors
    - TypeScript type errors
    """

    def __init__(self, temperature: float = TEMPERATURE_ZERO):
        self.temperature = temperature
        logger.info("FixerAgent initialized", temperature=temperature)

    def _run_command(self, cmd: List[str], cwd: Optional[Path] = None) -> Tuple[bool, str, str]:
        """Run a command and return (success, stdout, stderr)."""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            return result.returncode == 0, result.stdout, result.stderr
        except FileNotFoundError:
            return False, "", f"Command not found: {cmd[0]}"
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out: {' '.join(cmd)}"
        except Exception as e:
            return False, "", str(e)

    def _fix_eslint_issues(self, output_dir: Path) -> List[FixResult]:
        """Attempt to fix ESLint issues using eslint --fix."""
        results = []
        ts_files = list(output_dir.rglob("*.ts"))

        if not ts_files:
            return [FixResult("eslint", "No TypeScript files found", False)]

        for ts_file in ts_files:
            success, stdout, stderr = self._run_command(
                ["npx", "eslint", "--fix", str(ts_file)],
                cwd=ts_file.parent,
            )

            if "No eslint found" in stderr or "command not found" in stderr.lower():
                results.append(FixResult("eslint", "ESLint not available", False, "Install eslint"))
                break

            if "error" not in stderr.lower() and "warning" not in stderr.lower():
                results.append(
                    FixResult("eslint", f"Fixed {ts_file.name}", True, "ESLint --fix applied")
                )
            elif shutil.which("eslint") is None and shutil.which("npx") is None:
                results.append(FixResult("eslint", "ESLint not installed", False, "Install eslint"))
            else:
                errors = len(re.findall(r"error", stderr.lower()))
                warnings = len(re.findall(r"warning", stderr.lower())) - errors
                results.append(
                    FixResult(
                        "eslint",
                        f"Partial fix: {errors} errors, {warnings} warnings remain",
                        errors == 0,
                        "ESLint --fix applied",
                    )
                )

        return results

    def _fix_json_schema_issues(self, output_dir: Path) -> List[FixResult]:
        """Fix common JSON schema errors in Bedrock JSON files."""
        results = []

        for category, category_path, required_keys in [
            ("block", output_dir / "blocks", ["format_version", "minecraft:block"]),
            ("item", output_dir / "items", ["format_version", "minecraft:item"]),
            ("entity", output_dir / "entities", ["format_version", "minecraft:entity"]),
        ]:
            if not category_path.exists():
                continue

            for json_file in category_path.glob("*.json"):
                try:
                    data = json.loads(json_file.read_text(encoding="utf-8"))
                    modified = False

                    if "format_version" not in data:
                        data["format_version"] = "1.20.10"
                        modified = True

                    main_key = f"minecraft:{category}"
                    if main_key not in data:
                        results.append(
                            FixResult(
                                "schema",
                                f"Missing {main_key} in {json_file.name}",
                                False,
                                f"Cannot add {main_key} - no template",
                                str(json_file.relative_to(output_dir)),
                            )
                        )
                        continue

                    if "description" not in data[main_key]:
                        data[main_key]["description"] = {
                            "identifier": f"modporter:{json_file.stem}"
                        }
                        modified = True

                    if "identifier" in data[main_key].get("description", {}):
                        identifier = data[main_key]["description"]["identifier"]
                        if not identifier or ":" not in identifier:
                            data[main_key]["description"]["identifier"] = (
                                f"modporter:{json_file.stem}"
                            )
                            modified = True

                    if modified:
                        json_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
                        results.append(
                            FixResult(
                                "schema",
                                f"Fixed {json_file.name}",
                                True,
                                "Added missing required keys",
                                str(json_file.relative_to(output_dir)),
                            )
                        )

                except json.JSONDecodeError as e:
                    results.append(
                        FixResult(
                            "json_parse",
                            f"Invalid JSON in {json_file.name}",
                            False,
                            str(e),
                            str(json_file.relative_to(output_dir)),
                        )
                    )
                except Exception as e:
                    results.append(
                        FixResult(
                            "schema",
                            f"Error processing {json_file.name}",
                            False,
                            str(e),
                            str(json_file.relative_to(output_dir)),
                        )
                    )

        if not results:
            results.append(FixResult("schema", "No JSON schema issues found", True))

        return results

    def _fix_typescript_issues(self, output_dir: Path) -> List[FixResult]:
        """Attempt to fix TypeScript issues."""
        results = []
        ts_files = list(output_dir.rglob("*.ts"))

        if not ts_files:
            return [FixResult("typescript", "No TypeScript files found", False)]

        for ts_file in ts_files:
            content = ts_file.read_text(encoding="utf-8")
            modified = False
            fixes = []

            lines = content.split("\n")
            new_lines = []

            for i, line in enumerate(lines):
                new_line = line

                if "import " in line and "from" in line:
                    import_match = re.search(
                        r"import\s+\{([^}]+)\}\s+from\s+['\"]([^'\"]+)['\"]", line
                    )
                    if import_match:
                        names = import_match.group(1)
                        path = import_match.group(2)
                        if "@minecraft/server" in path:
                            names_list = [n.strip() for n in names.split(",")]
                            fixed_names = []
                            for name in names_list:
                                if name in ["Entity", "Block", "ItemStack", "Player", "World"]:
                                    fixed_names.append(name)
                                else:
                                    fixed_names.append("any")
                            if fixed_names != names_list:
                                new_line = f"import {{{', '.join(fixed_names)}}} from '{path}'"
                                modified = True
                                fixes.append(
                                    f"Fixed import type: {names} -> {', '.join(fixed_names)}"
                                )

                if "== null" in line or "== undefined" in line:
                    new_line = line.replace("== null", "== null").replace(
                        "== undefined", "=== undefined"
                    )
                    if new_line != line:
                        modified = True

                new_lines.append(new_line)

            if modified:
                ts_file.write_text("\n".join(new_lines), encoding="utf-8")
                results.append(
                    FixResult(
                        "typescript",
                        f"Fixed {ts_file.name}",
                        True,
                        "; ".join(fixes),
                        str(ts_file.relative_to(output_dir)),
                    )
                )

        if not results:
            results.append(FixResult("typescript", "No TypeScript fixes needed", True))

        return results

    def _revalidate_fixes(self, output_dir: Path) -> Dict[str, Any]:
        """Re-run review to validate fixes didn't break anything."""
        revalidation = {
            "files_checked": 0,
            "new_issues": 0,
            "validation_passed": True,
        }

        ts_files = list(output_dir.rglob("*.ts"))
        revalidation["files_checked"] = len(ts_files)

        for ts_file in ts_files:
            success, stdout, stderr = self._run_command(
                ["npx", "tsc", "--noEmit", str(ts_file)],
                cwd=ts_file.parent,
            )
            if not success:
                revalidation["new_issues"] += 1
                revalidation["validation_passed"] = False

        return revalidation

    def execute(self, context: QAContext) -> AgentOutput:
        """
        Execute the fixer agent on the given QA context.

        Args:
            context: QA context containing job information and paths

        Returns:
            AgentOutput with fix results
        """
        start_time = time.time()

        try:
            logger.info("FixerAgent executing", job_id=context.job_id)

            review_results = context.validation_results.get("reviewer", {})

            if not review_results:
                return AgentOutput(
                    agent_name="fixer",
                    success=False,
                    result={},
                    errors=["No review results found in context - run ReviewerAgent first"],
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            output_dir = context.output_bedrock_path
            all_fixes: List[FixResult] = []

            error_count = review_results.get("error_count", 0)
            warning_count = review_results.get("warning_count", 0)

            if error_count > 0 or warning_count > 0:
                all_fixes.extend(self._fix_eslint_issues(output_dir))
                all_fixes.extend(self._fix_json_schema_issues(output_dir))
                all_fixes.extend(self._fix_typescript_issues(output_dir))
            else:
                all_fixes.append(FixResult("general", "No issues to fix", True))

            revalidation = self._revalidate_fixes(output_dir)

            fixed_count = sum(1 for f in all_fixes if f.fix_applied)
            failed_count = sum(1 for f in all_fixes if not f.fix_applied)

            fix_rate = (fixed_count / len(all_fixes) * 100) if all_fixes else 100

            result = {
                "issues_identified": error_count + warning_count,
                "fixes_attempted": len(all_fixes),
                "fixes_applied": fixed_count,
                "fixes_failed": failed_count,
                "fix_rate_percent": round(fix_rate, 1),
                "fixes": [f.to_dict() for f in all_fixes],
                "revalidation": revalidation,
            }

            context.validation_results["fixer"] = {
                "fixes_applied": fixed_count,
                "fix_rate": fix_rate,
                "passed": revalidation["validation_passed"],
            }

            execution_time = int((time.time() - start_time) * 1000)

            output_data = {
                "agent_name": "fixer",
                "success": revalidation["validation_passed"],
                "result": result,
                "errors": [f.original_message for f in all_fixes if not f.fix_applied],
                "execution_time_ms": execution_time,
            }

            validated = validate_agent_output(output_data)

            logger.info(
                "FixerAgent completed",
                job_id=context.job_id,
                fixed=fixed_count,
                failed=failed_count,
            )

            return validated

        except Exception as e:
            logger.error("FixerAgent failed", job_id=context.job_id, error=str(e))
            return AgentOutput(
                agent_name="fixer",
                success=False,
                result={},
                errors=[str(e)],
                execution_time_ms=int((time.time() - start_time) * 1000),
            )


def fix(context: QAContext) -> AgentOutput:
    """
    Convenience function to run fix.

    Args:
        context: QA context

    Returns:
        AgentOutput with fix results
    """
    agent = FixerAgent()
    return agent.execute(context)
