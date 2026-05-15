# `ai-engine/` vs `ai_engine/` — structural assessment

**TL;DR:** The user's instinct is correct — this was not intentional. `ai_engine/`
is a mostly-empty leftover from an incomplete directory rename. Production
code is currently broken because of it. Consolidation is a ~1-day refactor,
not a multi-week project, and should happen before A-slices A3+ land.

## What's actually in each directory

### `ai-engine/` (hyphenated) — the live service
- **605 tracked files**, 511 of them `.py` source.
- Has Dockerfiles, README, pyproject.toml, setup.py, main.py, conftest.py,
  SKELETON*.md, requirements.txt — the full operational surface.
- `setup.py` declares `name="ai-engine"` and `packages=find_packages(where=".")`,
  which discovers each top-level subdir (`utils/`, `agents/`, `qa/`, etc.) as
  its OWN top-level Python package. This is why production imports look like
  `from utils.* import` and `from agents.* import` — no `ai_engine.` prefix.
- `ai-engine/__init__.py` is just a comment line; the hyphenated dir name
  itself can't be a Python package, only its children are.

### `ai_engine/` (underscored) — incomplete-rename leftover
- **83 tracked files**, **26 of them `.py` source.**
- Tracked content is **only**:
  - `ai_engine/mmsd/` — 77 files (the MMSD pipeline + data backups)
  - `ai_engine/evaluation/` — 5 files (evaluator + tests)
  - `ai_engine/tests/test_premium_client.py` — 1 file
- Everything else is **untracked cruft**:
  - 22 ghost subdirectories (`agents/`, `cli/`, `config/`, `converters/`,
    `crew/`, `engines/`, `indexing/`, `knowledge/`, `learning/`, `models/`,
    `orchestration/`, `qa/`, `rl/`, `schemas/`, `search/`, `templates/`,
    `testing/`, `tools/`, `training_data/`, `utils/`, `mutants/`,
    `agent_metrics/`) — all created on the same day (May 2 11:28) by what
    looks like a copy script that left only `__pycache__/` behind.
  - `ai_engine.egg-info/` — leftover `pip install -e` metadata.
  - `htmlcov/` (154 files) — coverage report HTML.
  - `.venv/`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/` — local tool state.

## How `ai_engine` resolves at runtime

Because `ai_engine/` exists and has no `__init__.py`, Python treats it as a
**PEP 420 implicit namespace package**:

```
>>> import ai_engine
>>> ai_engine.__path__
_NamespacePath(['/home/alex/Projects/portkit/ai_engine'])
```

This means:

| Import | Result | Why |
|---|---|---|
| `from ai_engine.mmsd.premium_client import ...` | ✅ WORKS | `mmsd/__init__.py` exists, source is tracked |
| `from ai_engine.evaluation.evaluator import ...` | ✅ WORKS | same |
| `from ai_engine.utils.texture_metadata_extractor import ...` | ❌ ImportError | `utils/` has only `__pycache__/`, no source |
| `from ai_engine.search.multimodal_search_engine import ...` | ❌ ImportError | same |
| `from ai_engine.agents.* import ...` | ❌ ImportError | same |

## Import-site inventory (22 sites total)

```
6  ai_engine.utils    ← BROKEN (no source files, ghost dir)
5  ai_engine.mmsd     ← WORKS  (real tracked content)
3  ai_engine.search   ← BROKEN
3  ai_engine.agents   ← BROKEN
2  ai_engine.src      ← BROKEN (no `src/` dir at all)
1  ai_engine.tools    ← BROKEN
1  ai_engine.schemas  ← BROKEN
1  ai_engine.qa       ← BROKEN
```

**17 of 22 import sites are broken at runtime.** Three of them are in live
production paths:

1. `backend/src/api/knowledge_base.py:671` — texture upload endpoint.
   Import is in a `try` block but the `except` clause only catches
   `HTTPException`, so an `ImportError` propagates as a 500 error.
2. `backend/src/services/celery_tasks.py:648` — `handle_texture_extraction_task`.
   No try/except at all. Celery task failure on every invocation.
3. `ai-engine/agents/qa_agent.py:27` — explicitly framed as a "last resort"
   fallback after a primary import fails. That fallback also fails. Whatever
   uses this code path is currently broken.

The other 14 sites are similarly unguarded or guarded only against the wrong
exception. They presumably haven't crashed because the code paths haven't
been exercised since the rename — but they are time bombs, not dead code.

## What must have happened

A previous refactor (likely the same era as the LangChain cutover work)
renamed the underscored `ai_engine/` directory to the hyphenated `ai-engine/`,
probably to match Docker / CLI conventions where hyphens are preferred. The
rename was executed via copy + delete (not `git mv`) and was incomplete:

1. Most content moved to `ai-engine/` and was committed there. ✓
2. `ai_engine/mmsd/` and `ai_engine/evaluation/` were either left behind on
   purpose or forgotten — they remain tracked at the old location. ✗
3. Empty husks of the moved subdirs remain in `ai_engine/` because someone
   re-ran a tool there afterwards (pytest, mypy, ruff) and recreated
   `__pycache__/` directories. ✗
4. Most import sites were updated (511 source files in `ai-engine/` import
   from the new flat-top-level paths), but 17 sites were missed and still
   reference `ai_engine.*`. ✗

## Recommended action — consolidate, don't "merge"

The "merge" framing is misleading because there's nothing parallel to merge —
it's mostly-empty vs a live service. The right action is **consolidation**:

### Phase 1 — fix broken production imports (URGENT, ~1 hour)
Independent of any directory restructuring. Just fix the 17 broken sites:

```bash
# All sites importing ai_engine.{utils,search,agents,qa,schemas,tools,src}.* 
# should be rewritten to use the flat-top-level convention used elsewhere
# in ai-engine/. For example:
# 
#   from ai_engine.utils.texture_metadata_extractor import TextureMetadataExtractor
#   →
#   from utils.texture_metadata_extractor import TextureMetadataExtractor
```

For backend/scripts callers, the import shape depends on whether `ai-engine/`
is on `sys.path`. Two options:
- Add `ai-engine/` to `PYTHONPATH` in dev/Docker setup, then use flat imports.
- Or wrap the imports with a small bootstrap that does `sys.path.insert(0,
  'ai-engine')` once.

This phase fixes live bugs and removes the runtime dependency on the ghost
`ai_engine/` directory.

### Phase 2 — relocate the real `ai_engine/` content (~30 min)
Move the only two real subdirectories into `ai-engine/`:

```bash
git mv ai_engine/mmsd        ai-engine/mmsd
git mv ai_engine/evaluation  ai-engine/evaluation
git mv ai_engine/tests/test_premium_client.py  ai-engine/tests/test_premium_client.py

# Update the 5 ai_engine.mmsd.* import sites to mmsd.* (or wherever
# ai-engine's flat layout puts them).
```

Note: `ai-engine/evaluation/` already exists. Need to check for collisions.

### Phase 3 — delete the ghost directory (~5 min)
Once all imports point elsewhere:

```bash
git rm -r ai_engine/  # the few remaining tracked files
rm -rf ai_engine/     # the untracked ghost dirs, .venv, htmlcov, egg-info
```

### Phase 4 (OPTIONAL) — rename `ai-engine/` → `ai_engine/` (~half day)
This would give the project a Python-friendly directory name that matches
the importable namespace, ending the hyphen/underscore confusion forever.
Cost: updating Dockerfiles, docker-compose*.yml, CI workflows, scripts, docs,
README, .github/copilot-instructions.md, and probably AGENTS.md/CLAUDE.md.

Skip this phase if the operational cost (Docker image rebuilds, CI cache
invalidation, deployment coordination) outweighs the symbolic win.

## Sequencing relative to current plan

**Recommend: do Phase 1 immediately (own PR), Phase 2+3 before A3 lands.**

| Plan slice | Interaction with `ai_engine/` consolidation |
|---|---|
| A2.5 (logic_translator/steering_tools) | None — different files |
| A3 (qa/__init__.py) | Touches `agents/qa/` — same package as `ai_engine.qa` ghost. Better to delete the ghost first to avoid reviewer confusion. |
| A4–A6 | Same risk as A3 for their respective subpackages. |
| B+C (chromadb, base image rebuild) | Independent. **NB: chromadb floor is already at `>=1.5.8,<2.0` per `setup.py` and `requirements.txt`. The plan's claim that the floor wasn't bumped is wrong.** Real B+C work is reconciling a 3-way pin mismatch (`pyproject.toml` has `chromadb<1.6.0`; the other two have `<2.0`). |
| D (tracing audit) | Independent. |
| E (skeleton regenerate) | **Depends on consolidation.** Skeletons would otherwise reflect the orphan ghost dirs. |
| F (originally "consolidation later") | This work IS F. It's smaller than originally framed (~1 day, not a "fresh issue when ready"). |

## What the user's question implies for the wider plan

Three plan revisions follow from this finding:

1. **Promote F from #11 ("defer until E is done") to a near-term task.**
   It's actively breaking production code paths and it's a 1-day fix, not
   a multi-week refactor. Earliest slot: between A2.5 and A3.

2. **Correct B+C scope.** The chromadb floor is already at `>=1.5.8`. Real
   work is reconciling 3 pin sources, not bumping a stale floor. Re-grep
   when scoping.

3. **Add a "Phantom imports" cleanup ticket** for the 14 non-production
   sites that also reference `ai_engine.{utils,search,agents,qa,schemas,
   tools,src}.*`. Lower priority than the 3 production sites but should
   land in the same Phase 1 PR for atomicity.
