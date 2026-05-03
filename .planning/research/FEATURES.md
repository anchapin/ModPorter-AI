# Feature Landscape: Multi-Agent QA System

**Domain:** AI-powered Multi-Agent Code Conversion Validation
**Researched:** 2026-03-27
**Project Context:** Java→Bedrock Minecraft mod conversion (v4.7 milestone)

---

## Executive Summary

This document maps the feature requirements for the Multi-Agent QA System in portkit. The system consists of four specialized agents (Translator, Reviewer, Tester, Semantic Checker) that work in concert to validate and improve Java→Bedrock conversion quality.

**Key Insight:** The multi-agent QA approach follows the software engineering "review cycle" pattern used in production codebases—generation → review → test → semantic validation—with each agent having distinct responsibilities and success criteria.

---

## Agent Overview

| Agent | Primary Role | Input | Output |
|-------|-------------|-------|--------|
| **Translator** | Generate Bedrock code from parsed Java | Parsed Java AST + RAG context | Bedrock JSON/TS code |
| **Reviewer** | Check code quality, style, best practices | Generated Bedrock code | Quality report + fixes |
| **Tester** | Generate unit/integration tests | Bedrock code + context | Test files + execution results |
| **Semantic Checker** | Validate behavior equivalence + API validity | All prior outputs | Equivalence report |

### Agent Dependency Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│ Translator  │────▶│  Reviewer   │────▶│   Tester    │────▶│   Semantic   │
│   Agent     │     │    Agent    │     │    Agent    │     │   Checker    │
└─────────────┘     └─────────────┘     └─────────────┘     └──────────────┘
       │                   │                   │                   │
       └───────────────────┴───────────────────┴───────────────────┘
                                   │
                                   ▼
                          ┌────────────────┐
                          │   QA Report    │
                          │  (Aggregated)  │
                          └────────────────┘
```

---

## Table Stakes Features

Features users expect. Missing = product feels incomplete or unreliable.

### Translator Agent

| Feature | Why Expected | Complexity | Dependencies |
|---------|--------------|------------|--------------|
| **Java AST Parsing** | Must understand Java structure before conversion | HIGH | Existing: javalang/tree-sitter |
| **Pattern Recognition** | Identify Java patterns (generics, lambdas, annotations) | MEDIUM | Existing: RAG system |
| **Bedrock Code Generation** | Generate valid JSON + TypeScript | HIGH | New: Bedrock Script API knowledge |
| **Type Mapping** | Map Java types to TypeScript equivalents | MEDIUM | New: Type mapping rules |
| **Error Handling** | Gracefully handle unsupported features | MEDIUM | New: Feature flagging system |

### Reviewer Agent

| Feature | Why Expected | Complexity | Dependencies |
|---------|--------------|------------|--------------|
| **Syntax Validation** | Ensure valid JSON/TypeScript | LOW | New: Linter integration |
| **Style Checking** | Enforce consistent formatting | LOW | New: ESLint/Prettier rules |
| **Best Practices** | Flag anti-patterns in Bedrock code | MEDIUM | New: RAG knowledge base |
| **API Usage Check** | Verify Script API methods exist | HIGH | New: Bedrock API database |
| **Issue Severity Classification** | Prioritize findings (error/warning/info) | LOW | New: Classification rules |

### Tester Agent

| Feature | Why Expected | Complexity | Dependencies |
|---------|--------------|------------|--------------|
| **Unit Test Generation** | Generate tests for converted functions | HIGH | New: Test template library |
| **Integration Test Generation** | Test component interactions | HIGH | New: Integration patterns |
| **Test Execution** | Run generated tests | MEDIUM | New: pytest/vitest runner |
| **Coverage Reporting** | Show code coverage metrics | LOW | New: pytest-cov integration |
| **Failing Test Diagnosis** | Explain why tests fail | MEDIUM | New: Error analysis engine |

### Semantic Checker Agent

| Feature | Why Expected | Complexity | Dependencies |
|---------|--------------|------------|--------------|
| **Behavior Equivalence** | Verify Java→Bedrock behavior matches | HIGH | New: Behavior comparison engine |
| **API Validity** | Confirm all Script API calls are valid | HIGH | New: Bedrock API validator |
| **Data Flow Analysis** | Trace how data transforms through conversion | HIGH | Existing: validation_agent.py |
| **Incompatibility Detection** | Flag features with no Bedrock equivalent | MEDIUM | New: Incompatibility database |

---

## Differentiator Features

Features that set the product apart. Not expected, but highly valued.

### Translator Agent Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Context-Aware Translation** | Use mod context (dependencies, structure) to improve conversion | HIGH | Leverages existing RAG |
| **Incremental Conversion** | Convert file-by-file with dependency tracking | HIGH | Enables large mod support |
| **Multi-Version Support** | Target specific Bedrock protocol versions | MEDIUM | Future-proofs output |

### Reviewer Agent Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Auto-Fix Suggestions** | Not just flag issues, provide修复方案 | MEDIUM | Reduces developer effort |
| **Performance Hints** | Flag inefficient Bedrock patterns | MEDIUM | Improves runtime performance |
| **Security Review** | Detect unsafe Script API usage | HIGH | Critical for Marketplace |

### Tester Agent Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Property-Based Testing** | Generate random inputs to test invariants | HIGH | Catches edge cases |
| **Snapshot Testing** | Compare outputs against known-good baselines | LOW | Easy to implement |
| **Mutation Testing** | Verify tests actually detect bugs | MEDIUM | Validates test quality |

### Semantic Checker Agent Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Formal Verification** | Mathematically prove equivalence | VERY HIGH | Research-phase |
| **Execution Simulation** | Simulate Bedrock behavior without running | HIGH | Requires Script API mock |
| **Semantic Diff** | Visual diff of behavior, not just code | MEDIUM | UX differentiator |

---

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Agent Handoffs Without Context** | Each agent must have full conversion context | Pass complete context object between agents |
| **Parallel Execution Without Coordination** | Reviewer/Tester needTranslator output first | Use sequential flow or staged parallel |
| **Single-Pass Validation** | One pass cannot catch all issues | Iterative refinement cycles |
| **Black-Box Testing Only** | Need to understand why tests fail | Combine execution + code analysis |
| **Ignoring Incompatibilities** | Users need to know what's not convertible | Explicit incompatibility reporting |

---

## Feature Dependencies

### Critical Path

```
Translator Agent
    │
    ├──▶ Reviewer Agent ──▶ QA Report (basic)
    │
    ├──▶ Tester Agent ────▶ QA Report (with tests)
    │
    └──▶ Semantic Checker ─▶ QA Report (with equivalence)
```

### Data Dependencies

| Agent Produces | Consumed By | Purpose |
|---------------|-------------|---------|
| Parsed Java AST | Translator | Conversion input |
| Generated Bedrock code | Reviewer, Tester, Semantic Checker | Validation input |
| Review report | Translator (if fixes needed) | Iteration feedback |
| Test results | Semantic Checker | Behavior validation |
| Equivalence report | User | Final quality assessment |

### Shared Resources

| Resource | Access Pattern | Purpose |
|----------|---------------|---------|
| RAG Knowledge Base | All agents | Conversion patterns, best practices |
| PostgreSQL | All agents | Store validation results |
| Redis | All agents | Job state, intermediate results |
| Bedrock API Database | Reviewer, Semantic Checker | API validity checking |

---

## MVP Recommendation

For v4.7 milestone, prioritize in this order:

### Phase 1: Core Pipeline (Translator + Reviewer)

1. **Translator Agent** — Basic Java→Bedrock generation
   - Must have: AST parsing, pattern recognition, code generation
   - Nice to have: Context-aware, incremental

2. **Reviewer Agent** — Quality validation
   - Must have: Syntax validation, style checking, issue classification
   - Nice to have: Auto-fix, performance hints

**Rationale:** WithoutTranslator→Reviewer flow, there's no valid Bedrock output to test.

### Phase 2: Testing (Tester Agent)

3. **Tester Agent** — Automated test generation
   - Must have: Unit test generation, test execution, coverage
   - Nice to have: Integration tests, property-based

**Rationale:** Tests prove the converted code works. WithoutTester, users can't verify correctness.

### Phase 3: Semantic Validation (Semantic Checker)

4. **Semantic Checker** — Behavior equivalence
   - Must have: API validity, incompatibility detection
   - Nice to have: Formal verification, execution simulation

**Rationale:** Final validation layer. Catches issues other agents miss.

### Defer

- **Mutation Testing** — Nice to have, not critical for MVP
- **Formal Verification** — Research-phase, too complex for v4.7
- **Security Review** — Can add after basic validation works

---

## Integration with Existing Features

The Multi-Agent QA system builds on existing portkit components:

| Existing Feature | How QA Uses It |
|-----------------|----------------|
| Java Parsing (javalang) | Translator inputs |
| RAG Knowledge Base | All agents consult for patterns |
| Validation (validation_agent.py) | Semantic Checker extends this |
| Self-Learning | QA results feed back into RAG |
| Error Recovery | Agents handle conversion failures |

### Extension Points

- **Existing `qa_agent.py`** → Refactor into Tester Agent
- **Existing `validation_agent.py`** → Refactor into Semantic Checker + Reviewer
- **Existing RAG** → Add QA-specific retrieval tools
- **Existing PostgreSQL** → Add validation_results table

---

## Complexity Notes

| Feature Area | Complexity Driver | Mitigation |
|--------------|------------------|------------|
| Bedrock Code Generation | Script API complexity | Start with simple mods, expand coverage |
| Test Generation | Bedrock testing environment | Mock Script API initially |
| Behavior Equivalence | Java vs Bedrock semantics | Use proxy metrics (API coverage, structure similarity) |
| Inter-Agent Communication | Context passing overhead | Use CrewAI's built-in context sharing |

---

## Sources

- **Project Context:** `.planning/PROJECT.md` (v4.7 Multi-Agent QA Review milestone)
- **Stack Reference:** `.planning/research/STACK.md`
- **Existing Codebase:** `ai-engine/agents/qa_agent.py`, `validation_agent.py`, `testing/qa_framework.py`
- **Multi-Agent Patterns:** CrewAI documentation (sequential, hierarchical workflows)

---

*Feature landscape for: Multi-Agent QA System v4.7*
*Researched: 2026-03-27*