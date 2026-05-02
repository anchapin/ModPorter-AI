#!/usr/bin/env python3
"""
PortKit Skill Auto-Eval (Karpathy-style improvement loop evaluator)

Usage:
    python flue/eval/eval.py <skill_name>
    python flue/eval/eval.py add-converter
    python flue/eval/eval.py add-api-endpoint

The script:
1. Loads fixed test prompts from flue/eval/test_cases/<skill>.json
2. Runs each prompt through the Flue agent (portkit-coder)
3. Grades each output against binary criteria using an LLM judge
4. Appends the scored result to flue/eval/run_log.jsonl
5. Prints the overall score (0.0 - 1.0)
"""

import json
import sys
import subprocess
import datetime
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Binary eval criteria - 3-6 per skill (Karpathy rule: binary only, no scales)
# Each criterion is a yes/no question the LLM judge can answer from the output.
# ---------------------------------------------------------------------------
CRITERIA: dict[str, list[str]] = {
    "add-converter": [
        "Does the output place converter code in ai-engine/converters/ (not elsewhere)?",
        "Does the converter function use the @tool decorator from crewai.tools?",
        "Does the converter have a docstring explaining when an agent should use it?",
        "Does the output include a pytest test file with at least two test cases?",
        "Does the output register the new converter in an __init__.py?",
        "Does the output avoid placing large data dicts inline (uses JSON files for >10 entries)?",
    ],
    "add-api-endpoint": [
        "Does the endpoint use FastAPI APIRouter with a /api/v1/ prefix?",
        "Are request and response Pydantic models defined?",
        "Does the endpoint dispatch work to a Celery task (not block synchronously)?",
        "Is the router registered in main.py?",
        "Does the output include a FastAPI TestClient-based test?",
    ],
    "crewai-tool": [
        "Does the tool function use the @tool decorator from crewai.tools?",
        "Is the docstring written as agent-facing instructions (when to use / not use)?",
        "Does the tool return a string on bad input instead of raising?",
        "Is real logic extracted into a private _do_* helper function?",
        "Is the tool added to the relevant agent's tools list?",
    ],
    "extract-hardcoded-data": [
        "Is the data written to ai-engine/data/*.json (not ai-engine/converters/)?",
        "Is a _load_*() private function used (not inline open() call)?",
        "Does the loader include a return type hint?",
        "Does the output verify nothing broke (import check or test run)?",
    ],
}

REPO_ROOT = Path(__file__).parent.parent.parent  # portkit repo root


def run_agent(prompt: str) -> str:
    """Run the Flue portkit-coder agent with a prompt and return its output."""
    try:
        result = subprocess.run(
            ["npx", "@flue/cli", "run", "flue/agents/portkit-coder.ts",
             "--prompt", prompt],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(REPO_ROOT),
        )
        if result.returncode != 0:
            return f"AGENT_ERROR: {result.stderr[:500]}"
        return result.stdout
    except subprocess.TimeoutExpired:
        return "AGENT_ERROR: timeout after 180s"
    except FileNotFoundError:
        # flue cli not installed - return placeholder for dry-run testing
        return f"DRY_RUN: would run agent with prompt: {prompt[:100]}"


def judge_criterion(criterion: str, output: str) -> bool:
    """Use an LLM to judge whether output satisfies a binary criterion."""
    prompt = (
        f"Does the following code/output satisfy this criterion?\n"
        f"Answer with exactly YES or NO, nothing else.\n\n"
        f"Criterion: {criterion}\n\n"
        f"Output:\n{output[:3000]}\n\n"
        f"Answer (YES or NO):"
    )
    try:
        # For local use, replace this with your preferred LLM call:
        # e.g., openai.chat.completions.create(...) or anthropic.messages.create(...)
        result = subprocess.run(
            ["surething", "web", "research", prompt],
            capture_output=True, text=True, timeout=30,
        )
        text = result.stdout.strip().upper()
        return text.startswith("YES")
    except Exception:
        # Fallback: simple keyword heuristic (not as reliable)
        keywords = criterion.lower().split()
        matches = sum(1 for kw in keywords if kw in output.lower() and len(kw) > 4)
        return matches >= 2


def score_output(skill: str, output: str) -> tuple[float, list[dict]]:
    """Score one agent output against all criteria for the skill."""
    criteria = CRITERIA.get(skill, [])
    if not criteria:
        print(f"  Warning: no criteria defined for skill '{skill}'")
        return 0.0, []

    results = []
    passed = 0
    for criterion in criteria:
        ok = judge_criterion(criterion, output)
        passed += int(ok)
        results.append({"criterion": criterion, "passed": ok})
        print(f"  {'V' if ok else 'X'} {criterion[:70]}")

    score = passed / len(criteria)
    return score, results


def main() -> None:
    skill = sys.argv[1] if len(sys.argv) > 1 else "add-converter"
    test_cases_path = REPO_ROOT / "flue" / "eval" / "test_cases" / f"{skill}.json"

    if not test_cases_path.exists():
        print(f"No test cases found at {test_cases_path}")
        print(f"Create {test_cases_path} with format: [{{\"prompt\": \"...\"}}]")
        sys.exit(1)

    with open(test_cases_path) as f:
        test_cases: list[dict] = json.load(f)

    if not test_cases:
        print("No test cases in file.")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"Evaluating skill: {skill}  ({len(test_cases)} test cases)")
    print(f"{'='*60}\n")

    total_score = 0.0
    all_results = []

    for i, tc in enumerate(test_cases, 1):
        prompt = tc["prompt"]
        print(f"[{i}/{len(test_cases)}] {prompt[:70]}...")
        output = run_agent(prompt)
        score, criteria_results = score_output(skill, output)
        total_score += score
        all_results.append({
            "prompt": prompt,
            "score": score,
            "criteria": criteria_results,
        })
        print(f"  -> Score: {score:.2f}\n")

    avg_score = total_score / len(test_cases)
    print(f"{'='*60}")
    print(f"FINAL SCORE: {avg_score:.3f}  ({int(avg_score * 100)}%)")
    print(f"{'='*60}\n")

    # Append to run log
    log_path = REPO_ROOT / "flue" / "eval" / "run_log.jsonl"
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "skill": skill,
        "score": avg_score,
        "test_cases": len(test_cases),
        "results": all_results,
    }
    with open(log_path, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    print(f"Score logged to {log_path}")


if __name__ == "__main__":
    main()
