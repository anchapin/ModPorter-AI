# PortKit Skill Improvement Loop (Karpathy-style)

## Goal
Iteratively improve a single PortKit skill file by testing it against real coding
tasks and measuring output quality with binary criteria. One skill per session.

## Files
- `flue/eval/eval.py`             — scoring script; run this to measure current skill quality
- `.agents/skills/<skill>.md`     — the ONE skill file being improved this session
- `flue/eval/test_cases/<skill>.json` — fixed test prompts (never modify these)
- `flue/eval/run_log.jsonl`       — append-only score history

## The Loop (repeat until no improvement or 20 iterations)

### Each iteration
1. Read `.agents/skills/<skill>.md` — understand the current state
2. Make **ONE targeted change** — pick the single weakest part:
   - Missing step that caused agents to skip something
   - Ambiguous instruction that led to wrong output
   - Missing example that would clarify the pattern
   - Wrong command that doesn't match PortKit's actual structure
3. Run `python flue/eval/eval.py <skill>` to score
4. **If score improved**: keep the change, continue to next iteration
5. **If score same or worse**: revert the change, try a different single edit
6. Repeat

## Convergence criteria
- Score reaches 1.0 → done
- No single change improves the score across 5 consecutive attempts → done
- 20 iterations reached → done, log findings

## Hard rules
- Change exactly ONE thing per iteration (not a rewrite)
- Never touch `flue/eval/test_cases/` — those are ground truth
- Never touch `flue/eval/eval.py` — that's the fixed evaluator
- Log EVERY change and score in `flue/eval/run_log.jsonl`
- At the end of the session, write a one-paragraph summary of what changed and why

## What "one change" means
Good: Add a missing checklist item
Good: Rewrite one ambiguous step for clarity
Good: Add a code example to a step that lacked one
Good: Fix a wrong file path reference
Bad: Rewrite the entire skill from scratch
Bad: Add three new sections at once
Bad: Change the eval criteria to make the score easier
