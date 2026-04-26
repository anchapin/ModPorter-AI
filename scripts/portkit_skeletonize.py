#!/usr/bin/env python3
"""
PortKit Code Skeletonizer
========================
Generates AI-optimized code skeletons and architecture manifests for the PortKit repo.

Outputs:
  CLAUDE.md              - Updated AI directive file for Claude Code
  ARCHITECTURE.md        - Architecture overview with module map
  .cursorrules           - Cursor / Cline / Windsurf directive
  ai-engine/SKELETON.md  - AI engine module skeleton
  backend/SKELETON.md    - Backend module skeleton
  frontend/SKELETON.md   - Frontend module skeleton

Usage:
  python3 portkit_skeletonize.py <repo_dir>
"""

import ast
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ─────────────────────────── CONFIG ────────────────────────────────────────

# Dirs to skip entirely
SKIP_DIRS = {
    "__pycache__", ".git", "node_modules", ".venv", "venv", "dist", "build",
    ".next", "coverage", ".nyc_output", "htmlcov", ".pytest_cache", ".ruff_cache",
    "pytest-of-alex", "training_data", "6ByLntZdir8UwV2KplisY", "notebooks",
    "examples", "prototyping", "research",
}

# Subdirs per module to include in skeletons
AI_ENGINE_MODULES = [
    "agents", "converters", "search", "orchestration", "qa",
    "crew", "knowledge", "engines", "learning", "models", "tools", "utils",
]
BACKEND_MODULES = [
    "src/api", "src/services", "src/models", "src/db", "src/security",
]
FRONTEND_MODULES = [
    "src/components", "src/pages", "src/api", "src/services", "src/hooks",
    "src/types", "src/contexts",
]

MAX_SKELETON_FILES_PER_MODULE = 60  # avoid runaway output

# ─────────────────────────── PYTHON AST EXTRACTION ─────────────────────────

def extract_python_skeleton(filepath: Path, repo_root: Path) -> str | None:
    """Extract class/function signatures from a Python file using AST."""
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return None

    rel = filepath.relative_to(repo_root)
    lines = []
    lines.append(f"### `{rel}`")

    # Module docstring
    mod_doc = ast.get_docstring(tree)
    if mod_doc:
        first_line = mod_doc.strip().split("\n")[0][:120]
        lines.append(f"> {first_line}")

    # Key third-party imports (skip stdlib + relative)
    stdlib = {
        "os", "sys", "re", "io", "json", "time", "math", "abc", "enum",
        "typing", "pathlib", "datetime", "logging", "hashlib", "base64",
        "collections", "functools", "itertools", "dataclasses", "contextlib",
        "asyncio", "threading", "subprocess", "shutil", "tempfile", "uuid",
        "copy", "warnings", "inspect", "textwrap", "struct", "array", "pickle",
        "traceback", "weakref", "gc", "platform", "signal", "socket",
        "http", "urllib", "email", "html", "xml", "csv", "sqlite3",
        "unittest", "types", "operator", "string", "random", "secrets",
        "multiprocessing", "concurrent", "queue", "heapq", "bisect",
    }
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top not in stdlib:
                    imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                top = node.module.split(".")[0]
                if top not in stdlib:
                    imports.append(node.module)
    if imports:
        unique_imports = sorted(set(imports))[:8]
        lines.append(f"*deps: {', '.join(unique_imports)}*")

    found_any = False
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            found_any = True
            # Class signature
            bases = [ast.unparse(b) for b in node.bases] if node.bases else []
            base_str = f"({', '.join(bases)})" if bases else ""
            lines.append(f"\n**class {node.name}{base_str}:**")
            class_doc = ast.get_docstring(node)
            if class_doc:
                doc_first = class_doc.strip().split("\n")[0][:100]
                lines.append(f"  *{doc_first}*")
            # Methods
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    sig = _format_function_sig(item)
                    lines.append(f"  {sig}")
                    fdoc = ast.get_docstring(item)
                    if fdoc:
                        fdoc_first = fdoc.strip().split("\n")[0][:90]
                        lines.append(f"    *{fdoc_first}*")

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found_any = True
            sig = _format_function_sig(node)
            lines.append(f"\n{sig}")
            fdoc = ast.get_docstring(node)
            if fdoc:
                fdoc_first = fdoc.strip().split("\n")[0][:100]
                lines.append(f"  *{fdoc_first}*")

    if not found_any:
        return None  # Skip empty/init files with no classes or functions

    return "\n".join(lines)


def _format_function_sig(node) -> str:
    """Format a function/method as a signature string."""
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    args = []
    fn_args = node.args

    # positional args
    n_defaults = len(fn_args.defaults)
    n_args = len(fn_args.args)
    for i, arg in enumerate(fn_args.args):
        default_offset = i - (n_args - n_defaults)
        ann = f": {ast.unparse(arg.annotation)}" if arg.annotation else ""
        if default_offset >= 0:
            default = f" = {ast.unparse(fn_args.defaults[default_offset])}"
        else:
            default = ""
        args.append(f"{arg.arg}{ann}{default}")

    # *args
    if fn_args.vararg:
        ann = f": {ast.unparse(fn_args.vararg.annotation)}" if fn_args.vararg.annotation else ""
        args.append(f"*{fn_args.vararg.arg}{ann}")

    # keyword-only
    for i, arg in enumerate(fn_args.kwonlyargs):
        ann = f": {ast.unparse(arg.annotation)}" if arg.annotation else ""
        default = ""
        if fn_args.kw_defaults[i] is not None:
            default = f" = {ast.unparse(fn_args.kw_defaults[i])}"
        args.append(f"{arg.arg}{ann}{default}")

    # **kwargs
    if fn_args.kwarg:
        ann = f": {ast.unparse(fn_args.kwarg.annotation)}" if fn_args.kwarg.annotation else ""
        args.append(f"**{fn_args.kwarg.arg}{ann}")

    # Return type
    ret = f" -> {ast.unparse(node.returns)}" if node.returns else ""

    arg_str = ", ".join(args)
    # Trim very long signatures
    if len(arg_str) > 120:
        arg_str = arg_str[:117] + "..."

    return f"`{prefix} {node.name}({arg_str}){ret}`"


# ─────────────────────────── TYPESCRIPT EXTRACTION ─────────────────────────

def extract_typescript_skeleton(filepath: Path, repo_root: Path) -> str | None:
    """Extract interfaces, types, and function signatures from TypeScript files."""
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    rel = filepath.relative_to(repo_root)
    lines = []
    lines.append(f"### `{rel}`")
    found_any = False

    # Interface definitions
    iface_pattern = re.compile(
        r"(?:export\s+)?interface\s+(\w+)(?:<[^{]*>)?\s*(?:extends\s+[^{]+)?\{([^}]*)\}",
        re.DOTALL,
    )
    for m in iface_pattern.finditer(source):
        found_any = True
        name = m.group(1)
        body = m.group(2).strip()
        # Extract field names (first 8)
        fields = re.findall(r"(\w+\??)\s*:\s*([^;,\n]+)", body)[:8]
        field_str = "; ".join(f"{f}: {t.strip()}" for f, t in fields)
        lines.append(f"\n**interface {name}** `{{ {field_str[:150]} }}`")

    # Type aliases
    type_pattern = re.compile(r"export\s+type\s+(\w+)\s*=\s*([^;]+);")
    for m in type_pattern.finditer(source):
        found_any = True
        name = m.group(1)
        val = m.group(2).strip()[:100]
        lines.append(f"\n**type {name}** = `{val}`")

    # Enum
    enum_pattern = re.compile(r"(?:export\s+)?(?:const\s+)?enum\s+(\w+)\s*\{([^}]*)\}")
    for m in enum_pattern.finditer(source):
        found_any = True
        name = m.group(1)
        members = re.findall(r"(\w+)\s*=?\s*['\"]?[\w.]+['\"]?", m.group(2))[:6]
        lines.append(f"\n**enum {name}** `{{ {', '.join(members)} }}`")

    # React components (function components)
    comp_pattern = re.compile(
        r"(?:export\s+(?:default\s+)?)?(?:const|function)\s+([A-Z]\w+)\s*[=:]?\s*(?:React\.FC|FC|React\.FunctionComponent|\([^)]*\)\s*(?::\s*(?:JSX|ReactNode|ReactElement|React\.ReactElement)[^=]*)?\s*=>|\s*\()"
    )
    for m in comp_pattern.finditer(source):
        found_any = True
        name = m.group(1)
        # Find props type
        props_m = re.search(rf"(?:interface|type)\s+{name}Props\s*[={{]", source)
        props = f" (props: {name}Props)" if props_m else ""
        lines.append(f"\n**component {name}**{props}")

    # Exported hooks
    hook_pattern = re.compile(r"export\s+(?:const\s+|function\s+)(use[A-Z]\w+)")
    for m in hook_pattern.finditer(source):
        found_any = True
        name = m.group(1)
        lines.append(f"\n**hook {name}()**")

    # Exported async functions (API calls etc.)
    fn_pattern = re.compile(
        r"export\s+(?:async\s+)?(?:const\s+(\w+)\s*=\s*async|function\s+(\w+))\s*\(([^)]{0,120})\)"
    )
    for m in fn_pattern.finditer(source):
        found_any = True
        name = m.group(1) or m.group(2)
        if name and name[0].islower() and not name.startswith("use"):
            params = m.group(3).strip()[:80]
            lines.append(f"\n**fn {name}**({params})")

    if not found_any:
        return None

    return "\n".join(lines)


# ─────────────────────────── MODULE SKELETON BUILDER ───────────────────────

def build_module_skeleton(
    repo_root: Path, rel_dirs: list[str], label: str, max_files: int = MAX_SKELETON_FILES_PER_MODULE
) -> str:
    """Build a skeleton document for a module (list of relative subdirectories)."""
    sections = []
    file_count = 0

    for rel_dir in rel_dirs:
        module_path = repo_root / rel_dir
        if not module_path.exists():
            continue

        py_files = sorted(module_path.rglob("*.py"))
        ts_files = sorted(module_path.rglob("*.ts")) + sorted(module_path.rglob("*.tsx"))

        all_files = [(f, "py") for f in py_files] + [(f, "ts") for f in ts_files]

        for filepath, lang in all_files:
            if file_count >= max_files:
                break
            # Skip dirs in SKIP_DIRS
            if any(part in SKIP_DIRS for part in filepath.parts):
                continue
            if filepath.name.startswith("test_") or "/tests/" in str(filepath) or "/testing/" in str(filepath):
                continue
            if filepath.name == "__init__.py" and filepath.stat().st_size < 200:
                continue

            if lang == "py":
                skeleton = extract_python_skeleton(filepath, repo_root)
            else:
                skeleton = extract_typescript_skeleton(filepath, repo_root)

            if skeleton:
                sections.append(skeleton)
                file_count += 1

    now = datetime.now().strftime("%Y-%m-%d")
    header = f"""# {label} — Code Skeleton
<!-- AUTO-GENERATED by scripts/portkit_skeletonize.py on {now} -->
<!-- DO NOT EDIT MANUALLY — run the skeletonizer to update -->

This file provides a structural map of the {label} module for AI coding agents.
It contains class/function signatures, type definitions, and docstrings — **no implementation bodies**.

**Files indexed:** {file_count}

---

"""
    return header + "\n\n---\n\n".join(sections)


# ─────────────────────────── ARCHITECTURE.md ──────────────────────────────

ARCHITECTURE_MD = """\
# PortKit — Architecture Overview
<!-- AUTO-GENERATED section markers present. Update static sections manually; module map regenerates weekly. -->

## Vision
AI-powered "conversion accelerator" that converts Minecraft Java Edition mods to Bedrock Edition add-ons.
Target: automate 60-80% of a mod creator's conversion effort (B2B positioning).

---

## System Architecture

```
                        ┌─────────────────────────────────────────────────────┐
                        │                   User / Client                      │
                        └────────────────────┬────────────────────────────────┘
                                             │ HTTPS
                        ┌────────────────────▼────────────────────────────────┐
                        │           Frontend  (React + TypeScript + Vite)      │
                        │           Nginx proxy — localhost:3000               │
                        └────────────────────┬────────────────────────────────┘
                                             │ REST API
                        ┌────────────────────▼────────────────────────────────┐
                        │           Backend  (FastAPI + Python 3.12+)          │
                        │           localhost:8080                             │
                        │  ┌──────────────────────────────────────────────┐   │
                        │  │  src/api/          HTTP route handlers        │   │
                        │  │  src/services/     Business logic             │   │
                        │  │  src/models/       Pydantic schemas           │   │
                        │  │  src/db/           SQLAlchemy async ORM       │   │
                        │  │  src/security/     Upload sandbox, rate limits│   │
                        │  └──────────────────────────────────────────────┘   │
                        └───┬────────────────────┬───────────────────────┬────┘
                            │ HTTP               │ Celery                │
               ┌────────────▼──────┐  ┌─────────▼────────┐  ┌──────────▼────────┐
               │   AI Engine        │  │   PostgreSQL 15   │  │    Redis 7         │
               │   FastAPI:8001     │  │   + pgvector      │  │    Celery broker  │
               │   CrewAI + RAG    │  │   port:5433       │  │    port:6379      │
               └────────────────────┘  └──────────────────┘  └───────────────────┘
```

---

## Service Directory

| Service | Technology | Port | Key Files |
|---------|-----------|------|-----------|
| **Frontend** | React 18 + TypeScript + Vite + Nginx | 3000 | `frontend/src/` |
| **Backend** | FastAPI + SQLAlchemy (async) + Celery | 8080 | `backend/src/` |
| **AI Engine** | FastAPI + CrewAI + LangChain | 8001 | `ai-engine/` |
| **PostgreSQL** | PostgreSQL 15 + pgvector | 5433 | `database/` |
| **Redis** | Redis 7 | 6379 | Celery broker + session cache |

---

## AI Engine — Module Map

```
ai-engine/
├── main.py                    # FastAPI app entrypoint (port 8001)
├── agents/                    # Conversion agent implementations
│   ├── java_analyzer/         # Java mod parsing (tree-sitter, AST analysis)
│   ├── logic_translator/      # Java→Bedrock logic translation
│   ├── texture_converter/     # Texture atlas + image conversion
│   ├── model_converter/       # 3D model format conversion
│   ├── recipe_converter.py    # Crafting/custom recipe conversion
│   ├── entity_converter.py    # Entity behavior + spawn rules
│   ├── bedrock_builder.py     # Bedrock add-on package assembly
│   ├── bedrock_architect.py   # Manifest + structure generation
│   └── ...                    # 20+ specialized agents
├── converters/                # Standalone converter utilities
│   ├── advancement_converter.py
│   ├── loot_table_generator.py
│   ├── sound_converter.py
│   └── ...
├── crew/                      # CrewAI crew definitions
│   ├── conversion_crew.py     # Main PortkitConversionCrew
│   └── rag_crew.py
├── orchestration/             # Parallel task orchestration
│   ├── orchestrator.py        # ParallelOrchestrator (main entry)
│   ├── strategy_selector.py   # Chooses sequential/parallel/hybrid
│   ├── task_graph.py          # DAG of conversion tasks
│   └── worker_pool.py
├── search/                    # RAG + hybrid search
│   ├── rag_pipeline.py        # Main RAG pipeline
│   ├── hybrid_search_engine.py # BM25 + vector hybrid
│   ├── reranking_engine.py    # Cross-encoder reranking
│   └── ...
├── qa/                        # Quality assurance pipeline
│   ├── orchestrator.py        # QA workflow coordinator
│   ├── multi_candidate.py     # DPC-style consistency selection
│   ├── validators.py
│   └── logic_auditor_agent.py # Adversarial functional testing
├── knowledge/                 # Domain knowledge base
│   ├── cross_reference.py
│   └── schema.py
└── models/                    # Pydantic models + ML model wrappers
    └── smart_assumptions.py   # SmartAssumptionEngine
```

### Conversion Data Flow

```
JAR Upload
    │
    ▼
java_analyzer/ ──── tree-sitter AST ──→ JavaModAnalysis
    │                                        │
    ▼                                        ▼
PortkitConversionCrew (CrewAI)          RAG Pipeline
    │  Agents run in parallel:          (pgvector + hybrid search)
    │  - entity_converter                    │
    │  - recipe_converter               Bedrock pattern retrieval
    │  - texture_converter/                  │
    │  - logic_translator/              ◄────┘
    │  - model_converter/
    │  - sound_converter
    │  - ...
    ▼
bedrock_builder → .mcaddon package
    │
    ▼
QA Pipeline (multi_candidate + logic_auditor)
    │
    ▼
ConversionReport → Frontend
```

---

## Backend — Module Map

```
backend/src/
├── main.py                    # FastAPI app entrypoint (port 8080)
├── api/                       # Route handlers (thin layer, delegates to services)
│   ├── conversions.py         # POST /api/v1/convert, GET /api/v1/conversions/{id}
│   ├── auth.py                # OAuth routes (Discord/GitHub/Google)
│   ├── billing.py             # Stripe webhook + subscription routes
│   ├── analytics.py           # Usage analytics endpoints
│   └── ...
├── services/                  # Business logic
│   ├── celery_tasks.py        # Async task definitions
│   ├── celery_config.py       # Celery + Redis configuration
│   ├── ai_engine_client.py    # HTTP client for AI Engine (port 8001)
│   ├── asset_conversion_service.py  # Coordinates asset conversion
│   ├── comprehensive_report_generator.py
│   └── ...
├── models/                    # Pydantic request/response schemas
│   ├── addon_models.py
│   └── embedding_models.py
├── db/                        # Database layer
│   ├── models.py              # SQLAlchemy ORM models
│   ├── crud.py                # CRUD operations
│   ├── base.py                # async engine + get_db dependency
│   └── init_db.py
├── security/                  # Security hardening
│   └── ...                    # Upload sandbox, ClamAV, rate limiting
└── errors/                    # Centralized error handling package
```

---

## Frontend — Module Map

```
frontend/src/
├── App.tsx                    # Root component, router setup
├── main.tsx                   # Vite entrypoint
├── api/                       # API client functions (axios/fetch wrappers)
├── components/                # Reusable UI components
├── pages/                     # Route-level page components
├── hooks/                     # Custom React hooks
├── contexts/                  # React context providers
├── services/                  # Frontend business logic
├── types/                     # TypeScript type definitions
└── utils/                     # Utility functions
```

---

## Key Design Patterns

| Pattern | Where Used | Notes |
|---------|-----------|-------|
| **Async-first** | Backend + AI Engine | All I/O is `async def` + `await` |
| **CrewAI agents** | `ai-engine/crew/` | Each converter is a CrewAI agent with tools |
| **RAG retrieval** | `ai-engine/search/` | pgvector + BM25 hybrid; reranked by cross-encoder |
| **Smart assumptions** | `ai-engine/models/smart_assumptions.py` | Fills Java→Bedrock gaps automatically |
| **Celery queuing** | `backend/src/services/celery_tasks.py` | Long conversions run async; Redis broker |
| **Dependency injection** | Backend | `Depends(get_db)` for DB sessions |
| **Per-segment confidence** | `ai-engine/qa/` | Each converted segment gets a conformal reliability score |

---

## Critical "Do Not Touch" Zones

| File/Module | Reason |
|-------------|--------|
| `ai-engine/search/rag_pipeline.py` | Tightly coupled with CrewAI + Minecraft knowledge; LangChain/LlamaIndex swap would break agent tool interfaces |
| `ai-engine/knowledge/patterns/` | Domain-specific Java→Bedrock pattern mappings; no external library covers these |
| `ai-engine/orchestration/strategy_selector.py` | PortKit-specific orchestration logic; not generic |
| `backend/src/db/models.py` | Core ORM models; schema changes require migrations |

---

## Environment Variables (Required)

```bash
OPENAI_API_KEY=           # Required for embeddings + LLM
ANTHROPIC_API_KEY=        # Required for Claude-based agents
DATABASE_URL=             # postgresql+asyncpg://...
REDIS_URL=redis://redis:6379
STRIPE_SECRET_KEY=        # Billing
STRIPE_WEBHOOK_SECRET=    # Billing webhook validation
```

---

## Development Commands

```bash
# Start all services
docker compose up -d

# Dev mode (hot reload)
docker compose -f docker-compose.dev.yml up -d

# Run tests
pnpm run test                          # All tests
cd backend && pytest src/tests/unit/ -q  # Backend unit (fast)
cd ai-engine && pytest                 # AI engine tests

# Linting / formatting
pnpm run lint
pnpm run format

# Code quality
cd backend && ruff check src/
cd ai-engine && ruff check .
```

---

## Auto-Generated Skeleton Files

The following files are **auto-generated weekly** by `scripts/portkit_skeletonize.py`.
Do not edit them manually — commit the generator script changes instead.

- `ai-engine/SKELETON.md`
- `backend/SKELETON.md`
- `frontend/SKELETON.md`

*Last generated: {DATESTAMP}*
"""

CLAUDE_MD = """\
# CLAUDE.md — PortKit Agent Handbook
<!-- AUTO-GENERATED by scripts/portkit_skeletonize.py on {DATESTAMP} -->
<!-- Update static sections in the generator script; module map regenerates weekly -->

**Version:** 2.0  
**Updated:** {DATESTAMP}

---

## Project Overview

**PortKit** is an AI-powered tool that converts Minecraft Java Edition mods (.jar) to Bedrock Edition add-ons (.mcaddon).

**Business model:** B2B "conversion accelerator" — automates 60-80% of a mod creator's conversion.  
**Domain:** modporter.ai  
**GitHub:** github.com/anchapin/ModPorter-AI (→ PortKit)

**Stack:**
- **Frontend:** React 18 + TypeScript + Vite (Nginx, port 3000)
- **Backend:** FastAPI + Python 3.12+ + SQLAlchemy (async) + Celery (port 8080)
- **AI Engine:** FastAPI + CrewAI + LangChain + RAG (port 8001)
- **Database:** PostgreSQL 15 + pgvector (port 5433)
- **Cache/Queue:** Redis 7 + Celery (port 6379)
- **Auth:** OAuth (Discord / GitHub / Google)
- **Billing:** Stripe

---

## Quick Navigation

| Want to... | Go to |
|-----------|-------|
| Add a conversion agent | `ai-engine/agents/` — copy an existing agent |
| Modify conversion pipeline | `ai-engine/crew/conversion_crew.py` |
| Add a backend API endpoint | `backend/src/api/` + `backend/src/services/` |
| Change database schema | `backend/src/db/models.py` + write a migration |
| Add a frontend page | `frontend/src/pages/` + add route in `App.tsx` |
| Add a custom recipe converter | `ai-engine/agents/recipe_converter.py` |
| Tune RAG retrieval | `ai-engine/search/rag_pipeline.py` |
| Add QA check | `ai-engine/qa/validators.py` |
| Modify Celery tasks | `backend/src/services/celery_tasks.py` |

**Skeleton files for structural context (generated weekly):**
- `ai-engine/SKELETON.md` — all AI engine class/function signatures
- `backend/SKELETON.md` — all backend class/function signatures
- `frontend/SKELETON.md` — all frontend component/hook signatures

---

## Mandatory Rules for AI Agents

### MUST DO

1. **Read `ARCHITECTURE.md` for system overview** before starting any cross-service task.
2. **Read the relevant `SKELETON.md`** before editing a module — understand existing interfaces.
3. **Async-first:** All I/O in backend and AI engine MUST be `async def` + `await`.
4. **Type hints required:** All function signatures in Python must have type hints.
5. **Run tests after changes:** `cd backend && pytest src/tests/unit/ -q --tb=short`
6. **Pydantic V2:** Use `model_config = ConfigDict(from_attributes=True)`.
7. **Ruff format before commit:** `cd backend && ruff format . && ruff check --fix .`

### NEVER DO

```
❌ time.sleep() in any async context — use asyncio.sleep()
❌ requests.get() — use httpx.AsyncClient
❌ Global mutable state in agents
❌ Hardcoded item/block ID mappings — use minecraft-data JSON
❌ Edit ai-engine/SKELETON.md, backend/SKELETON.md, frontend/SKELETON.md directly
❌ Skip type hints on new functions
❌ Use javalang for Java parsing — use tree-sitter
```

---

## Coding Conventions

**Python (Backend + AI Engine)**
- Linter: `ruff` (line-length: 100, target: py312)
- Enabled rules: E, F, W, I, Q, N, D, UP, C901, SIM
- Async: All I/O must be async
- Forbidden: `time.sleep()`, `requests.get()`, global state

**TypeScript (Frontend)**
- Strict mode enabled
- All components must have typed props interfaces
- API calls go in `src/api/` — not inline in components

**Commit format:** `<type>(<scope>): <description>`  
Types: `feat|fix|docs|style|refactor|test|chore|ci`  
Scopes: `api|backend|ai-engine|tests|docs|ci|frontend`

**Test naming:** `test_<feature>_<scenario>_<expected>`  
Test markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.asyncio`

---

## Architecture Summary

See `ARCHITECTURE.md` for the full diagram. Key data flow:

```
JAR Upload → java_analyzer/ (tree-sitter) → PortkitConversionCrew (CrewAI)
  → [entity|recipe|texture|logic|model|sound converters run in parallel]
  → bedrock_builder → .mcaddon
  → QA Pipeline (multi_candidate + logic_auditor)
  → ConversionReport → Frontend
```

Backend handles auth, billing, file upload/storage, and delegates conversion work to AI Engine via HTTP + Celery tasks.

---

## Do Not Touch

| Module | Reason |
|--------|--------|
| `ai-engine/search/rag_pipeline.py` | Core RAG — tightly coupled with CrewAI tool interfaces |
| `ai-engine/knowledge/patterns/` | Domain-specific mappings; no external library substitute |
| `ai-engine/orchestration/strategy_selector.py` | PortKit-specific; not generic |
| `backend/src/db/models.py` | Schema changes require migrations |

---

## Testing

```bash
# All tests
pnpm run test

# Backend unit (fast, parallel)
cd backend && pytest src/tests/unit/ -q --tb=short

# Backend serial (state-sensitive)
cd backend && pytest -n0 -m serial

# AI Engine
cd ai-engine && pytest

# Frontend
cd frontend && pnpm test
```

Coverage: 80%+ required for merges.

---

## Environment Setup

```bash
cp .env.example .env
# Add: OPENAI_API_KEY, ANTHROPIC_API_KEY, STRIPE_SECRET_KEY

docker compose up -d         # All services
docker compose ps            # Check status
docker compose logs backend  # Debug
```

Health checks:
- Frontend: `curl http://localhost:3000/health`
- Backend: `curl http://localhost:8080/health/readiness`
- AI Engine: `curl http://localhost:8001/api/v1/health`
"""

CURSORRULES = """\
# PortKit — Cursor / Cline / Windsurf Rules
# AUTO-GENERATED by scripts/portkit_skeletonize.py on {DATESTAMP}

## Project: PortKit — Minecraft Java→Bedrock AI Mod Converter

### Architecture (read first)
- See ARCHITECTURE.md for system diagram and data flow
- See CLAUDE.md for full agent handbook
- See ai-engine/SKELETON.md for AI engine class/function map
- See backend/SKELETON.md for backend class/function map
- See frontend/SKELETON.md for frontend component/hook map

### Service Ports
- Frontend (React+Nginx): 3000
- Backend (FastAPI): 8080
- AI Engine (FastAPI+CrewAI): 8001
- PostgreSQL: 5433
- Redis: 6379

### Key Entry Points
- Backend API: backend/src/main.py
- AI Engine API: ai-engine/main.py
- Conversion crew: ai-engine/crew/conversion_crew.py
- Orchestrator: ai-engine/orchestration/orchestrator.py
- Frontend root: frontend/src/App.tsx

### Mandatory Coding Rules
1. All I/O in Python MUST be async (async def + await)
2. Use httpx.AsyncClient, NOT requests
3. Type hints on ALL function signatures
4. Pydantic V2: model_config = ConfigDict(from_attributes=True)
5. Java parsing: use tree-sitter (NOT javalang)
6. Item/block IDs: use minecraft-data JSON (NOT hardcoded dicts)
7. Never edit *SKELETON.md files — they are auto-generated
8. Run: cd backend && ruff format . && ruff check --fix . before committing

### Forbidden Patterns
- time.sleep() in async context → asyncio.sleep()
- requests.get() → httpx.AsyncClient
- Hardcoded JAVA_TO_BEDROCK_ITEM_MAP entries → minecraft-data
- Global mutable state in agents
- Inline code blobs in API route handlers (delegate to services/)

### Test Commands
  cd backend && pytest src/tests/unit/ -q --tb=short
  cd ai-engine && pytest
  cd frontend && pnpm test

### Commit Format
  <type>(<scope>): <description>
  types: feat|fix|docs|style|refactor|test|chore|ci
  scopes: api|backend|ai-engine|tests|docs|ci|frontend

### Do Not Touch
- ai-engine/search/rag_pipeline.py (RAG — tied to CrewAI tool interfaces)
- ai-engine/knowledge/patterns/ (domain-specific; no substitute)
- ai-engine/orchestration/strategy_selector.py (PortKit-specific logic)
- backend/src/db/models.py (schema changes need migrations)
"""

# ─────────────────────────── MAIN ─────────────────────────────────────────

def main():
    repo_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/portkit")
    if not repo_dir.exists():
        print(f"ERROR: repo dir not found: {repo_dir}")
        sys.exit(1)

    now = datetime.now().strftime("%Y-%m-%d")

    output_files = {}

    # 1. ARCHITECTURE.md
    print("Generating ARCHITECTURE.md...")
    output_files["ARCHITECTURE.md"] = ARCHITECTURE_MD.replace("{DATESTAMP}", now)

    # 2. CLAUDE.md (replace stale version)
    print("Generating CLAUDE.md...")
    output_files["CLAUDE.md"] = CLAUDE_MD.replace("{DATESTAMP}", now)

    # 3. .cursorrules
    print("Generating .cursorrules...")
    output_files[".cursorrules"] = CURSORRULES.replace("{DATESTAMP}", now)

    # 4. ai-engine/SKELETON.md
    print("Generating ai-engine/SKELETON.md...")
    output_files["ai-engine/SKELETON.md"] = build_module_skeleton(
        repo_dir, [f"ai-engine/{m}" for m in AI_ENGINE_MODULES], "AI Engine"
    )

    # 5. backend/SKELETON.md
    print("Generating backend/SKELETON.md...")
    output_files["backend/SKELETON.md"] = build_module_skeleton(
        repo_dir, [f"backend/{m}" for m in BACKEND_MODULES], "Backend"
    )

    # 6. frontend/SKELETON.md
    print("Generating frontend/SKELETON.md...")
    output_files["frontend/SKELETON.md"] = build_module_skeleton(
        repo_dir, [f"frontend/{m}" for m in FRONTEND_MODULES], "Frontend"
    )

    # Write locally
    print("\nWriting output files...")
    for rel_path, content in output_files.items():
        out_path = repo_dir / rel_path
        out_path.write_text(content, encoding="utf-8")
        size_kb = len(content) / 1024
        print(f"  ✓ {rel_path} ({size_kb:.1f} KB)")

    print(f"\nDone. {len(output_files)} files written to {repo_dir}")
    return output_files


if __name__ == "__main__":
    main()
