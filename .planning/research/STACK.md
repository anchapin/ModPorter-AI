# Stack Research: Multi-Agent QA System

**Domain:** AI-powered Multi-Agent Code Conversion Validation
**Researched:** 2026-03-27
**Confidence:** HIGH

## Executive Summary

The Multi-Agent QA System for portkit requires minimal **new** stack additions because the foundation (CrewAI + LangChain) already exists. The primary work involves **extending existing capabilities** through custom agent tools, validation frameworks, and specialized testing infrastructure for Bedrock output.

**Key Finding:** The existing CrewAI framework already provides the multi-agent orchestration, role-based agents, task delegation, and inter-agent communication patterns needed. What remains is adding specialized validation tools, test execution environments, and semantic analysis capabilities specific to Java→Bedrock conversion validation.

---

## Recommended Stack

### Core Technologies (Already in Use)

| Technology | Current Version | Purpose | Notes |
|------------|-----------------|---------|-------|
| **CrewAI** | >=0.11.0,<1.0.0 | Multi-agent orchestration | Already supports role-based agents, delegation, and crew workflows |
| **LangChain** | >=0.3.0,<1.0.0 | LLM integration | Provides tools, chains, and agent execution |
| **FastAPI** | 0.135.1 | API layer | Serves the multi-agent QA endpoints |
| **Pydantic** | ~=2.11.9 | Data validation | Defines agent input/output schemas |

### New Additions for Multi-Agent QA

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **pytest** | >=8.0.0 | Python test execution | Standard for unit/integration tests; supports async, fixtures, parametrization |
| **pytest-asyncio** | >=0.23.0 | Async test support | Required for testing async agents and concurrent validation |
| **pytest-xdist** | >=3.5.0 | Parallel test execution | Run multiple agent validation tests concurrently |
| **pytest-cov** | >=4.1.0 | Coverage reporting | Track validation coverage across agents |
| **TypeScript** | ^5.4.0 | Type checking Bedrock output | Validate generated TypeScript/JavaScript |
| **tsx** | ^4.7.0 | TypeScript executor | Run and validate TypeScript without compilation |
| **vitest** | ^1.5.0 | JS/TS test framework | Alternative for JavaScript test generation by Tester Agent |
| **esbuild** | ^0.21.0 | Fast TS→JS compilation | Quick validation of generated TypeScript |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **javalang** | 0.13.0 | Java AST parsing | Translator Agent analyzes Java input |
| **pytest-mock** | >=3.12.0 | Test mocking | Mock external services in agent tests |
| **pytest-timeout** | >=2.2.0 | Test timeouts | Prevent hung validation tests |
| **aiocontextvars** | >=0.3.0 | Async context | Required for context preservation in async agents |
| **tree-sitter** | >=0.21.0 | AST generation | Advanced Java parsing (future upgrade) |

---

## Architecture Integration

### How Agents Communicate

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Multi-Agent QA Pipeline                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐           │
│  │  Translator  │───▶│   Reviewer   │───▶│   Tester     │           │
│  │    Agent     │    │    Agent     │    │    Agent     │           │
│  └──────────────┘    └──────────────┘    └──────────────┘           │
│         │                   │                   │                   │
│         └───────────────────┴───────────────────┘                   │
│                             │                                        │
│                             ▼                                        │
│                    ┌────────────────┐                                │
│                    │   Semantic     │                                │
│                    │    Checker     │                                │
│                    └────────────────┘                                │
│                             │                                        │
│                             ▼                                        │
│                    ┌────────────────┐                                │
│                    │  QA Report     │                                │
│                    └────────────────┘                                │
└─────────────────────────────────────────────────────────────────────┘
```

### Inter-Agent Communication Patterns

**1. Sequential Flow (Default)**
- Translator → Reviewer → Tester → Semantic Checker
- Uses CrewAI's task output passing
- Each agent receives previous agent's artifacts

**2. Parallel Validation**
- Multiple agents validate simultaneously
- Reviewer and Semantic Checker can run in parallel
- Use `ProcessPoolExecutor` for parallel agent execution

**3. Feedback Loop**
- Semantic Checker can request re-validation from Reviewer
- CrewAI's delegation tools enable agent-to-agent requests

---

## Agent-Specific Tool Requirements

### Translator Agent
- **Java Parser**: javalang (existing) or tree-sitter (upgrade)
- **Pattern Library**: RAG integration for conversion patterns
- **Code Generator**: LLM (via LangChain)

### Reviewer Agent
- **Linter**: Custom rules for Bedrock Script API
- **Style Checker**: TypeScript ESLint config
- **Best Practices**: RAG knowledge base

### Tester Agent
- **Test Generator**: LLM generates pytest/vitest tests
- **Test Runner**: pytest execution with custom plugins
- **Coverage**: pytest-cov integration

### Semantic Checker
- **Behavior Analyzer**: Compare Java→Bedrock semantics
- **API Validator**: Verify Bedrock Script API usage
- **Equivalence Checker**: Data flow analysis

---

## Installation

```bash
# Core testing additions for ai-engine
cd ai-engine

# Testing framework
pip install pytest>=8.0.0 pytest-asyncio>=0.23.0 pytest-xdist>=3.5.0 pytest-cov>=4.1.0

# Test utilities
pip install pytest-mock>=3.12.0 pytest-timeout>=2.2.0 aiocontextvars>=0.3.0

# TypeScript/JS validation (Node.js)
npm install --save-dev typescript@^5.4.0 tsx@^4.7.0 vitest@^1.5.0 esbuild@^0.21.0

# Java AST (if upgrading from javalang)
pip install tree-sitter>=0.21.0
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| CrewAI (existing) | AutoGen | If Microsoft ecosystem preferred; NOTE: AutoGen being consolidated into new Microsoft Agent Framework (Oct 2025) - avoid for new projects |
| CrewAI (existing) | MetaGPT | If need more structured software engineering workflows |
| pytest (existing in backend) | unittest | Only if strict Python stdlib required |
| pytest (new) | pytest-bdd | If behavior-driven tests needed for acceptance criteria |
| vitest (new) | Jest | If simpler ecosystem preferred; vitest has better TypeScript integration |
| tsx (new) | ts-node | If need TypeScript debugging; tsx is faster for execution |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **AutoGen v0.2** | Being deprecated; Microsoft consolidating into new Agent Framework | CrewAI (stable, active development) |
| **LangChain "Legacy" Agents** | Being replaced by LangGraph; API changes frequent | Use `create_agent()` factory or LangGraph |
| **javalang** (for new code) | Limited AST capabilities; slow | tree-sitter for robust parsing |
| **Plain subprocess for code execution** | Security risk; no isolation | Use containerized execution or code review gates |
| **Synchronous agent execution** | Blocks pipeline; poor resource utilization | Async execution via asyncio + pytest-asyncio |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| pytest>=8.0.0 | Python 3.10+ | Requires Python 3.10+ |
| pytest-asyncio>=0.23.0 | pytest>=7.0.0, Python 3.10+ | Use `pytest_asyncio.fixture` |
| pytest-xdist>=3.5.0 | pytest>=7.0.0 | Parallel test execution |
| crewai>=0.11.0,<1.0.0 | Python 3.10-3.13 | Already in requirements |
| langchain>=0.3.0,<1.0.0 | Python 3.10+ | Already in requirements |
| TypeScript ^5.4.0 | Node.js 18+ | LTS support |
| vitest ^1.5.0 | Node.js 18+ | Compatible with TypeScript 5.4 |

---

## Stack Patterns by Variant

**IfTranslator Agent needs faster Java parsing:**
- Upgrade: javalang → tree-sitter
- Benefit: 100x faster AST extraction
- Integration: Custom CrewAI tool wrapping tree-sitter

**IfSemantic Checker requires deep behavior analysis:**
- Add: graphviz for data flow visualization
- Add: networkx for dependency analysis
- Use: Existing BehaviorAnalysisEngine in validation_agent.py as foundation

**IfTester Agent generates many tests:**
- Enable: pytest-xdist for parallel execution
- Configure: `pytest -n auto` for auto CPU detection
- Monitor: pytest-cov for coverage tracking

**Ifneed real-time validation feedback:**
- Add: WebSocket via FastAPI
- Integrate: Agent streaming with `stream_log()` from CrewAI
- Frontend: Existing React app can consume streaming updates

---

## Sources

- **Context7: CrewAI** — Agent architecture, delegation, tools, telemetry with OpenTelemetry
- **Context7: LangChain** — Multi-agent patterns, LangGraph integration, create_agent() factory
- **Context7: AutoGen** — CodeExecutorAgent for sandboxed execution (NOTE: being consolidated)
- **Context7: Pytest** — Async testing, plugins, fixtures
- **Context7: TypeScript** — Type checking, compiler API
- **Existing Codebase**: ai-engine/agents/qa_agent.py, validation_agent.py, testing/qa_framework.py

---

## Integration Notes

### Extending Existing Agents

The codebase already contains:
- `qa_agent.py` — QA pipeline with TestFramework
- `validation_agent.py` — Semantic analysis, behavior prediction
- `testing/qa_framework.py` — Test scenario execution

**Recommendation:** Extend these existing agents rather than creating new ones. The 4-agent QA system should:

1. **Refactor** `qa_agent.py` → becomes Tester Agent
2. **Refactor** `validation_agent.py` → becomes Semantic Checker + Reviewer
3. **Create** new Translator Agent for code generation
4. **Orchestrate** via CrewAI crew with custom tools

### Shared Context

All agents should share:
- Conversion context (Java input, Bedrock output)
- RAG knowledge base access
- Validation results store (PostgreSQL)
- Job state (Redis)

---

*Stack research for: Multi-Agent QA System*
*Researched: 2026-03-27*