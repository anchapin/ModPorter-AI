# Phase 16-08: Iterative Refinement Loop - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning
**Source:** Roadmap requirements extraction

<domain>
## Phase Boundary

**Phase Goal:** Allow iterative refinement when critical issues are found

**What this phase delivers:**
- Detect critical issues requiring re-translation
- Pass error context back to Translator
- Re-run pipeline with corrected context
- Limit refinement iterations (max 3)
- Track refinement history
- Report improvement after refinement

**Dependencies:** Phase 16-01 (QA Context & Orchestration), 16-02 (Translator), 16-03 (Reviewer), 16-04 (Tester), 16-05 (Semantic Checker), 16-06 (QA Report), 16-07 (Parallel Execution)

</domain>

<decisions>
## Implementation Decisions

### Refinement Trigger (Locked)
- Critical issues (severity=CRITICAL) from any agent trigger refinement
- Reviewer syntax errors trigger refinement
- Tester failures on critical paths trigger refinement
- Semantic checker critical mismatches trigger refinement

### Refinement Context (Locked)
- Pass full error context to Translator: original code + issues + suggestions
- Include relevant agent output in refinement prompt
- Preserve successful translations from previous iteration
- Use temperature=0.7 for refinement (some creativity but deterministic)

### Iteration Limits (Locked)
- Maximum 3 refinement iterations per job
- Track iteration count in QAContext
- Stop refinement if: max iterations reached OR score improvement < 5%
- Final report includes all iteration results

### Improvement Tracking (Locked)
- Store initial quality score before first refinement
- Store score after each refinement iteration
- Calculate improvement delta: final_score - initial_score
- Report "improved", "same", or "degraded" status

### the agent's Discretion
- Specific threshold for "critical" (configurable)
- How to merge successful parts with problematic parts
- Whether to use parallel refinement for independent issues

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### QA System Architecture
- `.planning/phases/16-01-qa-context-orchestration/16-01-02-PLAN.md` — QAOrchestrator current implementation
- `.planning/phases/16-02-translator-agent/16-02-01-PLAN.md` — TranslatorAgent implementation
- `.planning/phases/16-06-qa-report-generator/16-06-RESEARCH.md` — Report aggregation patterns

### Project Structure
- `ai-engine/qa/orchestrator.py` — Current orchestrator with parallel execution
- `ai-engine/qa/context.py` — QAContext for passing data
- `ai-engine/qa/translator.py` — Translator agent
- `ai-engine/qa/reviewer.py` — Reviewer agent
- `ai-engine/qa/fixer.py` — Fixer/Tester agent
- `ai-engine/qa/semantic_checker.py` — Semantic Checker agent

</canonical_refs>

<specifics>
## Specific Ideas

- Add `refinement_enabled` config flag to QAOrchestrator
- Add `max_refinement_iterations` (default: 3)
- Add `RefinementHistory` dataclass to track iterations
- Add `run_with_refinement()` method to orchestrator
- Store refinement history in context.metadata
- Calculate and report improvement delta in final QA report
- Use IssueSeverity.CRITICAL as trigger threshold

</specifics>

<deferred>
## Deferred Ideas

- Dynamic iteration limit based on issue complexity (out of scope)
- Automatic prompt optimization via LLM (future phase)
- Cross-job refinement learning (out of scope)

</deferred>

---

*Phase: 16-08-iterative-refinement-loop*
*Context gathered: 2026-03-28 via roadmap requirements*