# Project Research Summary

**Project:** ModPorter-AI v4.7 — Multi-Agent QA System
**Domain:** AI-powered Multi-Agent Code Conversion Validation
**Researched:** 2026-03-27
**Confidence:** HIGH

## Executive Summary

The Multi-Agent QA System adds four specialized agents (Translator, Reviewer, Tester, Semantic Checker) to the existing ModPorter-AI conversion pipeline for validating Java→Bedrock Minecraft mod conversions. Research confirms this follows the software engineering "review cycle" pattern used in production codebases—generation → review → test → semantic validation—with each agent having distinct responsibilities. The existing CrewAI + LangChain stack already provides the multi-agent orchestration foundation; the primary work involves extending existing agents and adding specialized validation tools for Bedrock output. Key risks include agent coordination failures (circular dependencies), non-deterministic validation results, and integration conflicts with the existing conversion pipeline. The recommended approach is to implement QA as a post-conversion layer that runs asynchronously after packaging completes, ensuring QA doesn't block or disrupt existing conversion workflows.

## Key Findings

### Recommended Stack

The existing stack requires minimal new additions. CrewAI and LangChain already provide multi-agent orchestration, role-based agents, and task delegation. The main extensions involve testing infrastructure and TypeScript validation tools.

**Core technologies (already in use):**
- **CrewAI** (>=0.11.0,<1.0.0) — Multi-agent orchestration with delegation and crew workflows
- **LangChain** (>=0.3.0,<1.0.0) — LLM integration via tools, chains, and agent execution
- **FastAPI** (0.135.1) — API layer for QA endpoints
- **Pydantic** (~=2.11.9) — Data validation for agent input/output schemas

**New additions for Multi-Agent QA:**
- **pytest** (>=8.0.0) + **pytest-asyncio** (>=0.23.0) — Test execution with async support
- **pytest-xdist** (>=3.5.0) + **pytest-cov** (>=4.1.0) — Parallel execution and coverage reporting
- **TypeScript** (^5.4.0) + **tsx** (^4.7.0) — TypeScript validation without compilation
- **vitest** (^1.5.0) + **esbuild** (^0.21.0) — JavaScript test framework and fast compilation

### Expected Features

The 4-agent QA pipeline follows a sequential flow where Translator generates Bedrock code, Reviewer validates quality, Tester creates tests, and Semantic Checker validates behavior equivalence.

**Must have (table stakes):**
- **Java AST Parsing** — Must understand Java structure before conversion
- **Bedrock Code Generation** — Generate valid JSON + TypeScript
- **Syntax/Style Validation** — Ensure valid JSON/TypeScript, consistent formatting
- **Unit Test Generation** — Generate tests for converted functions
- **Behavior Equivalence** — Verify Java→Bedrock behavior matches

**Should have (competitive):**
- **Context-Aware Translation** — Use mod context to improve conversion
- **Auto-Fix Suggestions** — Provide修复方案, not just flag issues
- **Property-Based Testing** — Generate random inputs to test invariants
- **API Validity Checking** — Verify Script API methods exist

**Defer (v2+):**
- **Formal Verification** — Mathematically prove equivalence (too complex for v4.7)
- **Mutation Testing** — Verify tests detect bugs (nice to have)
- **Security Review** — Detect unsafe Script API usage (add after basic validation works)

### Architecture Approach

The QA system integrates as a post-conversion validation layer at the end of the existing conversion pipeline, immediately after the Packaging Agent produces the `.mcaddon` file. This separation ensures QA doesn't disrupt existing conversion flow while providing thorough validation. The architecture supports three data flow patterns: sequential (default), parallel (for Reviewer + Tester), and iterative refinement (for critical issue resolution). All agents share a `QAContext` dataclass containing job ID, paths, metadata, and validation results.

**Major components:**
1. **QAOrchestrator** — Coordinates 4-agent pipeline, manages context, handles execution
2. **Translator/Reviewer/Tester/Semantic Checker Agents** — Specialized validation roles
3. **QAReportGenerator** — Aggregates all agent outputs into final report

### Critical Pitfalls

1. **Agent Coordination Failure (Circular Dependencies)** — Define explicit DAG for workflows, implement timeouts, use sequential execution for coupled agents
2. **Non-Deterministic Validation Results** — Set `temperature=0`, create explicit validation checklists, implement deterministic code analysis alongside LLM checks
3. **Silent Failures (Unusable Output)** — Implement output schema validation, add sanity checks after each agent, define minimum quality thresholds
4. **Context Window Overflow** — Pass only relevant code subsets to each agent, use structured JSON for inter-agent communication
5. **Integration Conflict** — Design QA as independent consumer, use queue-based architecture, implement circuit breaker pattern

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Foundation & Integration Architecture
**Rationale:** Establish integration infrastructure without modifying existing agents. QA must integrate without breaking existing conversion pipeline.
**Delivers:** `QAContext` dataclass, QA endpoints in FastAPI, PostgreSQL schema extension, adapter layer between conversion and QA
**Addresses:** Table stakes — none yet (infrastructure phase)
**Avoids:** Pitfall #5 (Integration Conflict) — design QA as independent post-conversion layer from the start

### Phase 2: Basic QA Pipeline
**Rationale:** Get minimal QA flow working using existing QAValidatorAgent before adding specialized agents.
**Delivers:** Integration of QAValidatorAgent into crew workflow, QA task at end of conversion, basic report aggregation
**Uses:** pytest, pytest-asyncio for test execution
**Implements:** Sequential validation pattern as default
**Avoids:** Pitfall #1 (Circular Dependencies) — use proven sequential flow first

### Phase 3: Specialized QA Agents
**Rationale:** Each agent can be developed independently after Phase 2 establishes integration points. Must ensure deterministic results.
**Delivers:** Translator Agent, Reviewer Agent, Tester Agent (refactored from qa_agent.py), Semantic Checker (extended from validation_agent.py)
**Implements:** Full 4-agent pipeline with context passing
**Avoids:** Pitfall #2 (Non-Deterministic Results) — set temperature=0, implement explicit rubrics

### Phase 4: Advanced Features & Optimization
**Rationale:** Requires basic pipeline to be working first. Adds parallel execution and self-learning.
**Delivers:** Parallel Reviewer+Tester execution, iterative refinement loop, QA results into RAG, performance optimization
**Avoids:** Pitfall #3 (Silent Failures) — add output validation layer; Pitfall #4 (Context Overflow) — implement context compression

### Phase Ordering Rationale

- **Phase 1→2→3** follows build order from ARCHITECTURE.md with clear dependencies
- **Phase 1 addresses integration first** to avoid breaking existing conversion (Pitfall #5)
- **Phase 2 uses existing agents** to validate the flow before building new agents
- **Phase 3 adds agents sequentially** — each builds on previous phase's integration
- **Phase 4 optimizes** only after core pipeline works — avoids premature optimization

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Semantic Checker):** Behavior equivalence validation is complex — may need `/gsd-research-phase` for formal verification or execution simulation approaches

Phases with standard patterns (skip research-phase):
- **Phase 1:** Standard FastAPI + PostgreSQL patterns, well-documented
- **Phase 2:** Uses existing QAValidatorAgent, proven patterns
- **Phase 4:** Standard parallel execution patterns via pytest-xdist

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Existing stack verified; new additions are standard testing tools |
| Features | HIGH | Clear agent roles based on software engineering review patterns |
| Architecture | HIGH | Uses CrewAI native patterns, clear integration points |
| Pitfalls | MEDIUM | Research from CrewAI/AutoGen issues; some inference for mitigation |

**Overall confidence:** HIGH

### Gaps to Address

- **Bedrock Script API knowledge base:** Semantic Checker and Reviewer need accurate API reference — verify this is populated or build during Phase 1
- **Formal verification approach:** If Phase 3 Semantic Checker proves too complex, fallback to proxy metrics (API coverage, structure similarity)
- **Test execution environment:** Tester Agent needs mocked Script API for initial implementation — validate mock completeness

## Sources

### Primary (HIGH confidence)
- **Context7: CrewAI** — Agent architecture, delegation, tools, sequential/hierarchical workflows
- **Context7: LangChain** — Multi-agent patterns, LangGraph integration, create_agent() factory
- **Context7: Pytest** — Async testing, plugins, fixtures, parallel execution
- **Existing Codebase:** ai-engine/agents/qa_agent.py, validation_agent.py, testing/qa_framework.py

### Secondary (MEDIUM confidence)
- **Context7: AutoGen** — CodeExecutorAgent patterns (noting deprecation/consolidation)
- **Context7: TypeScript** — Type checking, compiler API
- **PITFALLS.md sources:** CrewAI/AutoGen issues, Semantic Kernel patterns

### Tertiary (LOW confidence)
- **DeepSeek-Coder** — Trust remote code errors, evaluation pipeline challenges (needs validation)

---
*Research completed: 2026-03-27*
*Ready for roadmap: yes*