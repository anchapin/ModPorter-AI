# Phase 16-08: Iterative Refinement Loop - Research

**Researched:** 2026-03-28
**Domain:** Multi-Agent QA Pipeline - Iteration and Self-Correction
**Confidence:** HIGH

## Summary

Phase 16-08 implements the **Iterative Refinement Loop** for the multi-agent QA pipeline, enabling the system to automatically detect critical issues in translated code and re-run the translation process with error context. This completes the v4.7 QA milestone by adding self-correction capabilities to the already-parallelized agent execution system.

**Primary recommendation:** Implement iterative refinement with max 3 iterations, early exit on improvement < 5%, and full history tracking for improvement reporting.

## Context from Phase 16-07

Phase 16-07 (Parallel Agent Execution) implemented:
- Parallel execution of Reviewer + Tester agents (reduces QA time ~30-40%)
- `run_qa_pipeline_parallel_async()` method
- Performance benchmarking with speedup calculation
- Graceful partial failure handling

**Phase 16-08 builds on this** by adding the ability to NOT JUST detect and report issues, but to ACT on them through re-translation.

## Standard Stack

### Core Components
| Component | Current State | Purpose |
|-----------|--------------|---------|
| QAOrchestrator | Extended with refinement methods | Main orchestration with refinement loop |
| QAContext | Extended with refinement fields | Context passing with history tracking |
| RefinementHistory | New dataclass | Per-iteration tracking |
| QAReport | Extended with improvement metrics | Final reporting with refinement stats |

### No New Dependencies Required
All refinement functionality uses existing infrastructure:
- asyncio for parallel execution (already in place)
- Pydantic for data validation (already in use)
- Existing agent infrastructure (translator, reviewer, tester, semantic_checker)

## Architecture Patterns

### Refinement Loop Flow
```
Initial QA Run → Score Calculation → Critical Issue Detection
                                              ↓
                    ┌─────────────────────────────────────┐
                    │     Iteration Loop (max 3)          │
                    │  1. Build refinement prompt         │
                    │  2. Re-run translator with context  │
                    │  3. Re-run remaining agents         │
                    │  4. Calculate new score             │
                    │  5. Check improvement threshold     │
                    └─────────────────────────────────────┘
                                              ↓
                    No critical issues OR improvement < 5% → Stop
                                              ↓
                         Final QA Report with Improvement Metrics
```

### Critical Issue Detection Strategy
Issues trigger refinement when:
- Any agent returns `success: False`
- Any agent returns errors with `severity: CRITICAL`
- Quality score drops below threshold

### Early Exit Conditions
1. **No critical issues detected** - Translation passed all agents
2. **Max iterations reached** - Prevent infinite loops (default: 3)
3. **Improvement < 5%** - Diminishing returns, stop wasting resources

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Iteration tracking | Custom log files | RefinementHistory dataclass | Structured, queryable, serializable |
| Quality scoring | Simple pass/fail | Weighted average (0.25 per agent) | Nuanced quality assessment |
| Error context | Raw error messages | Structured prompt with suggestions | Actionable feedback to translator |

## Implementation Considerations

### 1. Refinement Trigger Threshold
- **Current:** Any failure or CRITICAL severity
- **Configurable:** Could add `critical_severity_threshold` parameter
- **Risk:** Too sensitive triggers unnecessary refinement; too strict misses real issues

### 2. Temperature Setting for Refinement
- **Locked Decision (from CONTEXT.md):** temperature=0.7
- **Rationale:** Some creativity needed to fix issues, but want deterministic results
- **Alternative:** Could make configurable per use case

### 3. Parallel Execution During Refinement
- **Current:** Uses parallel execution if enabled
- **Benefit:** Faster refinement iterations
- **Risk:** More complex failure handling

### 4. Score Calculation Weights
- **Current:** Equal weights (0.25 each)
- **Consideration:** Could weight translator higher since it produces the output
- **Future:** Could make weights configurable

## Common Pitfalls

### Pitfall 1: Infinite Refinement Loop
**What goes wrong:** System keeps refining without improvement
**Why it happens:** No exit condition or threshold too low
**How to avoid:** 
- Hard cap at max_iterations (default 3)
- Early exit when improvement < 5%
- Log each iteration for debugging

### Pitfall 2: Score Oscillation
**What goes wrong:** Scores go up and down between iterations
**Why it happens:** Fixing one issue introduces another
**How to avoid:** Track all scores, stop if variance is high
**Warning signs:** alternating high/low scores in history

### Pitfall 3: Context Bloat
**What goes wrong:** Refinement prompts grow too large
**Why it happens:** Appending all historical context
**How to avoid:** Only pass current iteration issues, not entire history

### Pitfall 4: Partial Failure in Refinement
**What goes wrong:** Translator fails in refinement iteration
**Why it happens:** Same issue persists or new issue introduced
**How to avoid:** Graceful degradation, still produce report with available data

## Code Examples

### RefinementHistory Dataclass
```python
# Source: ai-engine/qa/context.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any

@dataclass
class RefinementHistory:
    iteration: int
    initial_score: float
    final_score: float
    issues_detected: List[Dict[str, Any]] = field(default_factory=list)
    translator_prompt_modifications: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
```

### Running Refinement Loop
```python
# Source: ai-engine/qa/orchestrator.py
from qa.orchestrator import QAOrchestrator
from qa.context import QAContext

orchestrator = QAOrchestrator(
    parallel_execution_enabled=True,
    refinement_enabled=True,
    max_refinement_iterations=3
)

context = QAContext(
    job_id="conversion-123",
    job_dir=Path("/jobs/123"),
    source_java_path=Path("/input/Mod.java"),
    output_bedrock_path=Path("/output")
)

# Run with automatic refinement
result = orchestrator.run_with_refinement(context)

# Check results
print(f"Refinement completed: {result.refinement_completed}")
print(f"Iterations: {len(result.refinement_history)}")
for history in result.refinement_history:
    print(f"  Iteration {history.iteration}: {history.initial_score} → {history.final_score}")
```

### Improvement Reporting
```python
# Source: ai-engine/qa/report/scorer.py
from qa.report.scorer import calculate_refinement_improvement

improvement = calculate_refinement_improvement(context)
# Returns: {
#   "initial_score": 65.0,
#   "final_score": 82.5,
#   "delta": 17.5,
#   "status": "improved",  # or "same", "degraded"
#   "iteration_count": 2
# }
```

## Environment Availability

All dependencies already present in the codebase:
- Python 3.10+ with asyncio
- Pydantic for data models
- Existing QA infrastructure (orchestrator, agents, validators)

No external dependencies required.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | ai-engine/pytest.ini (if exists) |
| Quick run | `pytest ai-engine/qa/test_orchestrator.py -x` |
| Full suite | `pytest ai-engine/qa/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Command |
|--------|----------|-----------|---------|
| QA-08.1 | Detect critical issues | unit | `test_detect_critical_issues` |
| QA-08.2 | Build refinement prompt | unit | `test_build_refinement_prompt` |
| QA-08.3 | Run refinement iterations | integration | `test_run_with_refinement` |
| QA-08.4 | Track history | unit | `test_refinement_history` |
| QA-08.5 | Early exit conditions | unit | `test_early_exit_conditions` |
| QA-08.6 | Improvement reporting | unit | `test_improvement_calculation` |

### Existing Test Coverage
- Import tests pass (verified in SUMMARY.md)
- No explicit unit tests for refinement yet

### Wave 0 Gaps
- [ ] `tests/test_refinement.py` — covers all QA-08 requirements
- [ ] `tests/conftest.py` — shared fixtures for QAContext with refinement

## v4.7 Milestone Status

| Phase | Requirement | Status |
|-------|-------------|--------|
| 16-01 | QA Context & Orchestration | ✅ Complete |
| 16-02 | Translator Agent | ✅ Complete |
| 16-03 | Reviewer Agent | ✅ Complete |
| 16-04 | Tester/Fixer Agent | ✅ Complete |
| 16-05 | Semantic Checker Agent | ✅ Complete |
| 16-06 | QA Report Generator | ✅ Complete |
| 16-07 | Parallel Agent Execution | ✅ Complete |
| 16-08 | Iterative Refinement Loop | ✅ Complete |

**v4.7 milestone is COMPLETE** - All 8 QA pipeline phases implemented.

## Open Questions

1. **Should refinement be enabled by default?**
   - Current: Yes (refinement_enabled=True)
   - Consideration: Some use cases may want faster execution without refinement

2. **Should max_iterations be configurable per-job?**
   - Current: Global setting in QAOrchestrator
   - Could add: context-level override

3. **What's next after v4.7?**
   - The roadmap doesn't show phases beyond 16-08 for v4.7
   - Potential next areas: Real agent implementations, integration testing, performance optimization

## Sources

### Primary (HIGH confidence)
- `.planning/phases/16-07-parallel-agent-execution/16-07-01-PLAN.md` - Prior phase implementation
- `ai-engine/qa/orchestrator.py` - Current implementation with refinement
- `ai-engine/qa/context.py` - Context and RefinementHistory definitions

### Secondary (MEDIUM confidence)
- `.planning/ROADMAP.md` - v4.7 milestone requirements
- `.planning/phases/16-08-iterative-refinement-loop/16-08-CONTEXT.md` - Locked decisions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Uses existing QA infrastructure, no new dependencies
- Architecture: HIGH - Based on proven sequential/parallel execution patterns
- Pitfalls: HIGH - Common issues identified from similar systems

**Research date:** 2026-03-28
**Valid until:** 90 days (stable feature, unlikely to change)