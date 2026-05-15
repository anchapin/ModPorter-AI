# Pre-flight findings — 2026-05-14

Status of the four pre-flight items defined in the execution plan.

## P1 — Pydantic `AIMessage` discriminator bug

**Status: NOT REPRODUCED. Promoted-to-blocker downgrade is reversed.**

### Evidence
Tested on both branches with `pydantic 2.12.5` + `langchain_core 1.3.2`:

| Branch | Invocation | Result |
|---|---|---|
| `feature/1201-typed-logic-translator-tool-args` (5d73200c) | `pytest --cov=. tests/test_qa_validator.py` | 29 passed |
| `feature/1201-typed-logic-translator-tool-args` | `pytest --cov=. tests/unit/test_bedrock_architect_coverage.py` | 10 passed |
| `feature/1201-typed-logic-translator-tool-args` | `pytest --cov=. tests/test_qa_validator_tool.py` | 4 passed |
| `feature/1201-typed-logic-translator-tool-args` | `pytest --cov=. --collect-only tests/` | 3373 collected, 0 errors |
| `origin/main` (88adc287) | `pytest --cov=. tests/test_qa_validator.py` | 29 passed |
| `origin/main` | `pytest --cov=. tests/unit/ --ignore=tests/unit/test_mojmap_validator.py` | 823 passed |

### Conclusion
The discriminator bug claim cannot be reproduced. Likely already fixed by a
post-cutover merge (PR #1446 is the most recent candidate). Per-module coverage
workaround is **NOT NEEDED** for A2.5–A6.

### Action
File a "cannot reproduce" close-comment on the cleanup ticket if filed, with
the test matrix above as evidence. If anyone hits this again, capture:
- pytest invocation
- branch/commit
- full traceback (the symptom claim referenced "PydanticUserError" — capture)
- pydantic + langchain_core versions

## P2 — Empty-BaseModel pattern for no-arg tools

**Status: VALIDATED. Pattern 1 recommended.**

All three patterns work with the installed versions:
- `@tool(args_schema=_NoArgs)` + `.invoke({})` ✓ (also accepts `.invoke(None)`)
- Bare `@tool` (auto-generated schema) + `.invoke({})` ✓
- `StructuredTool.from_function(args_schema=_NoArgs)` + `.invoke({})` ✓

**Recommendation:** use Pattern 1 (`class _NoArgs(BaseModel): pass`) for
codebase consistency. Every wrapper gets an explicit `args_schema`.

```python
from pydantic import BaseModel
from langchain_core.tools import tool

class _NoArgs(BaseModel):
    """Empty input schema."""
    pass

@tool(args_schema=_NoArgs)
def get_steering_stats_tool() -> dict:
    """..."""
    ...
```

Affected wrappers in upcoming A-slices:
- A2.5: `get_steering_stats_tool`, `enable_steering_tool`, `disable_steering_tool`
- A3: none (all 6 QA tools take args)
- A4–A6: re-survey at slice time

## P3 — `agents/java_analyzer/tools.py` output-shape inspection

**Status: PURE INPUT-SHAPE MIGRATION. A6 stays last.**

All 6 tools share signature `(mod_data: Union[str, Dict]) -> str`:
- `analyze_mod_structure_tool`
- `extract_mod_metadata_tool`
- `identify_features_tool`
- `analyze_dependencies_tool`
- `extract_assets_tool`
- `analyze_complexity_with_llm_tool` (signature: `(analysis_data: str) -> str`)

Outputs are JSON-serialized strings — downstream A3–A5 consumers don't bind
to output types. Migration only touches input wrappers and call sites.

Side note: each tool currently does manual `if isinstance(mod_data, str):
json.loads(mod_data)` — the typed-input migration removes this duplicated
parsing logic. Quality win on top of the shape change.

## P4 — G-tag commit SHA verification

**Status: SHA VERIFIED.**

```
d7b8941d feat(ai-engine): fully remove CrewAI; AI Engine runs on
                         LangChain/LangGraph only (#1201) (#1445)
```

Commit message references #1445 ✓. Tag `langchain-cutover-complete` pointing
at `d7b8941d` will mirror `pre-langchain-cutover` correctly.

Soak window opens 2026-05-15T17:21Z (24h after merge). Push tag then.

---

## Other findings worth recording

### F item is more urgent than originally framed

`tests/unit/test_mojmap_validator.py` fails to collect on `main` with
`ModuleNotFoundError: No module named 'ai_engine'`. The hyphenated/underscored
namespace inconsistency is a **real, current, broken-on-main** test, not just
structural debt. Two paths:

1. **Quick fix now** — patch the import or skip-mark the file with `# TODO: F-ticket`.
2. **Defer to F** — confirm CI doesn't run this file (or runs it from a different
   working directory where the import resolves). If CI is green, the breakage is
   only local-dev friction.

### A3 prerequisite confirmed

`tests/test_qa_validator.py` already uses `.invoke({...})` for all 6 QA tools.
Migration cost on the test side is zero — only wrapper signatures change.
Deprecation alias at `agents/qa_validator.py` is textbook (warning + re-export
+ `__all__`) — the alias-warning test from the plan will hit it cleanly.

### A3 wrapper signatures (pre-migration)

```
validate_conversion_quality_tool(quality_data: str) -> str
validate_mcaddon_tool(mcaddon_path: str) -> str
run_functional_tests_tool(test_data: str) -> str
analyze_bedrock_compatibility_tool(compatibility_data: str) -> str
assess_performance_metrics_tool(performance_data: str) -> str
generate_qa_report_tool(report_data: str) -> str
```

Note: `validate_mcaddon_tool` already takes a semantic single-string arg
(filesystem path), not a JSON blob — simplest of the six to migrate.
