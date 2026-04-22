# Architecture Research: Multi-Agent QA Integration

**Domain:** AI-powered Multi-Agent Code Conversion Validation
**Researched:** 2026-03-27
**Confidence:** HIGH
**Context:** v4.7 Multi-Agent QA Review milestone — Adding 4 specialized QA agents to existing portkit

---

## Executive Summary

This document specifies how the Multi-Agent QA system (Translator, Reviewer, Tester, Semantic Checker) integrates with the existing CrewAI + LangChain conversion architecture. The integration requires **minimal new infrastructure** — the existing agent orchestration framework already supports the required patterns. The primary work involves extending existing agents, adding specialized validation tools, and establishing clear data flow contracts between QA agents and the conversion pipeline.

**Key Architectural Decision:** The QA system operates as a **post-conversion validation layer** that receives output from the existing conversion crew, validates it through the 4-agent pipeline, and produces a comprehensive QA report. This separation ensures QA doesn't disrupt the existing conversion flow while providing thorough validation.

---

## System Overview

### Integration Point: QA Pipeline as Post-Conversion Layer

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        portkit Full Architecture                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    EXISTING CONVERSION CREW (v4.6)                      │   │
│  │  ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐    │   │
│  │  │ Java       │──▶│ Bedrock    │──▶│ Logic      │──▶│ Asset      │    │   │
│  │  │ Analyzer   │   │ Architect  │   │ Translator │   │ Converter  │    │   │
│  │  └────────────┘   └────────────┘   └────────────┘   └────────────┘    │   │
│  │        │                                                         │      │   │
│  │        └────────────────────────────────┬────────────────────────┘      │   │
│  │                                         ▼                               │   │
│  │                              ┌─────────────────┐                        │   │
│  │                              │ Packaging Agent │                        │   │
│  │                              └────────┬────────┘                        │   │
│  └───────────────────────────────────────┼─────────────────────────────────┘   │
│                                          │                                     │
│                                          │ .mcaddon output                    │
│                                          ▼                                     │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │                    MULTI-AGENT QA SYSTEM (NEW v4.7)                       │ │
│  │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌────────────┐│ │
│  │  │ Translator   │──▶│   Reviewer   │──▶│   Tester     │──▶│ Semantic   ││ │
│  │  │   Agent      │   │    Agent     │   │    Agent     │   │ Checker    ││ │
│  │  └──────────────┘   └──────────────┘   └──────────────┘   └────────────┘│ │
│  │        │                   │                   │                   │      │ │
│  │        │                   │                   │                   │      │ │
│  │        └───────────────────┴───────────────────┴───────────────────┘      │ │
│  │                                     │                                      │ │
│  │                                     ▼                                      │ │
│  │                            ┌────────────────┐                              │ │
│  │                            │  QA Report     │                              │ │
│  │                            │  Generator     │                              │ │
│  │                            └────────────────┘                              │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Integration Points

### 1. Entry Point: Post-Packaging Hook

The QA system integrates at the **end of the existing conversion pipeline**, immediately after the Packaging Agent produces the `.mcaddon` file.

| Integration Point | Existing Component | New QA Component | Data Flow |
|-------------------|-------------------|------------------|-----------|
| **Input** | `PackagingAgent` output | `QAOrchestrator` | `.mcaddon` path + metadata |
| **Output** | `QAValidatorAgent` (existing) | 4 new QA agents | `ConversionReport` |
| **Config** | Existing crew config | QA-specific config | Shared via `JobContext` |

**Implementation Location:** `ai-engine/crew/conversion_crew.py` — Add QA task at end of task list.

### 2. Shared Context Integration

All QA agents share the same context object that flows through the pipeline:

```python
@dataclass
class QAContext:
    """Shared context passed between QA agents"""
    job_id: str
    original_mod_path: Path
    converted_addon_path: Path  # The .mcaddon file
    conversion_metadata: Dict[str, Any]  # From previous conversion stages
    java_ast: Optional[Any]  # Parsed Java AST for semantic comparison
    bedrock_output: Dict[str, Any]  # Parsed Bedrock JSON structure
    validation_results: List[ValidationResult]  # Accumulated results
    rag_context: Dict[str, Any]  # Retrieved patterns from knowledge base
```

### 3. Data Store Integration

| Store | Purpose | QA Access Pattern |
|-------|---------|-------------------|
| **PostgreSQL** | Store validation results, QA reports | Read/Write via existing `crud` module |
| **Redis** | Job state, intermediate agent results | Read for context, Write for progress |
| **pgvector** (existing RAG) | Retrieve conversion patterns | Read-only for knowledge retrieval |

### 4. API Integration Points

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/convert/{job_id}/qa` | POST | Trigger QA pipeline for completed conversion |
| `/api/v1/convert/{job_id}/qa/status` | GET | Poll QA progress |
| `/api/v1/convert/{job_id}/qa/report` | GET | Retrieve comprehensive QA report |

---

## Data Flow Patterns

### Pattern 1: Sequential Validation (Default)

The primary flow where each agent processes output from the previous agent:

```
Translator Agent Output
        │
        ├── Code output (JSON/TS)
        ├── Conversion notes
        └── Confidence scores
              │
              ▼
Reviewer Agent Output
        │
        ├── Quality issues (categorized)
        ├── Style violations
        └── Auto-fix suggestions (if enabled)
              │
              ▼
Tester Agent Output
        │
        ├── Generated test files
        ├── Test execution results
        └── Coverage report
              │
              ▼
Semantic Checker Output
        │
        ├── Behavior equivalence score
        ├── API validity report
        └── Incompatibility warnings
              │
              ▼
QA Report Generator
        │
        └── Final aggregated report
```

### Pattern 2: Parallel Validation (Optimization)

Reviewer and Tester can run in parallel after Translator completes, as they operate on independent aspects:

```
Translator Output
       │
       ├──▶ Reviewer (code quality)
       │         │
       │         └── Quality Report
       │
       └──▶ Tester (test generation)
                 │
                 └── Test Results
                          │
                          ▼
                 Semantic Checker (receives both)
```

**When to Use:**
- Reviewer and Tester have no data dependencies on each other
- Use when conversion output is large and parallel processing saves time
- Requires `Process.parallel` or thread pool execution

### Pattern 3: Iterative Refinement (Advanced)

When Semantic Checker detects critical issues, request iteration from Translator/Reviewer:

```
Translator → Reviewer → Tester → Semantic Checker
      │                                           │
      │         (if critical issues found)        │
      └───────────────────────────────────────────┘
                    Iteration Request
```

**Implementation:** Semantic Checker tool that creates a new Task with `context=[previous_task]` to request re-validation.

---

## Inter-Agent Communication

### Communication Mechanisms

| Mechanism | Use Case | Implementation |
|-----------|----------|----------------|
| **Task Context** | Pass output from one agent to the next | CrewAI's `context=[previous_task]` |
| **Shared State** | Access common data (metadata, configs) | `QAContext` dataclass in Redis |
| **Tool Calls** | Request specific actions from other agents | CrewAI's delegation tools |
| **Message Passing** | Real-time status updates | WebSocket via FastAPI |

### Agent-to-Agent Tool Contracts

#### Translator Agent → Reviewer Agent

```python
# Translator produces this output:
@dataclass
class TranslatorOutput:
    generated_files: Dict[str, str]  # filename → content
    conversion_notes: List[str]
    confidence_map: Dict[str, float]  # feature → confidence
    unsupported_features: List[str]
```

#### Reviewer Agent → Tester Agent

```python
# Reviewer produces this output:
@dataclass
class ReviewerOutput:
    quality_issues: List[QualityIssue]  # severity, category, location, message
    style_violations: List[StyleViolation]
    auto_fixes_applied: List[str]
    code_score: float  # 0-100
```

#### Tester Agent → Semantic Checker

```python
# Tester produces this output:
@dataclass  
class TesterOutput:
    test_files: Dict[str, str]  # test name → test code
    execution_results: Dict[str, TestResult]  # test name → pass/fail
    coverage_report: CoverageReport
    failed_tests: List[str]
```

#### Semantic Checker → QA Report

```python
# Semantic Checker produces this output:
@dataclass
class SemanticCheckerOutput:
    equivalence_score: float  # 0-100
    api_validity: Dict[str, bool]  # api_name → is_valid
    incompatibility_report: List[Incompatibility]
    behavior_analysis: BehaviorReport
```

---

## Build Order Considerations

### Phase 1: Foundation (Weeks 1-2)

**Goal:** Establish the integration infrastructure without changing existing agents

| Task | Dependency | Changes Required |
|------|------------|------------------|
| Create `QAContext` dataclass | None | New file: `qa_context.py` |
| Add QA endpoints to FastAPI | None | Modify: `backend/src/main.py` |
| Extend PostgreSQL schema | None | Add: `validation_results` table |
| Create QA task template | None | New: Template in conversion_crew.py |

**Rationale:** These tasks have no dependencies on each other and don't modify existing agent behavior.

### Phase 2: Basic Pipeline (Weeks 3-4)

**Goal:** Get a minimal QA flow working with existing agents

| Task | Dependency | Changes Required |
|------|------------|------------------|
| Integrate QAValidatorAgent into crew | Phase 1 | Modify: `conversion_crew.py` |
| Add QA task to existing crew workflow | Phase 1 | Modify: `conversion_crew.py` task list |
| Create QA report aggregation | Phase 1 | New: `qa_report_generator.py` |
| End-to-end test with mock agents | Phase 1 | New: Integration test |

**Rationale:** Uses existing QAValidatorAgent (which already validates .mcaddon files) to establish the flow.

### Phase 3: Specialized QA Agents (Weeks 5-8)

**Goal:** Add the 4 specialized agents

| Task | Dependency | Changes Required |
|------|------------|------------------|
| Create Translator Agent | Phase 2 | New: `qa_translator_agent.py` |
| Create Reviewer Agent | Phase 2 | New: `qa_reviewer_agent.py` |
| Create Tester Agent | Phase 2 | Refactor: `qa_agent.py` → Tester Agent |
| Create Semantic Checker | Phase 2 | Extend: `validation_agent.py` |

**Rationale:** Each agent can be developed independently after Phase 2 establishes the integration points.

### Phase 4: Advanced Features (Weeks 9-12)

**Goal:** Add parallel execution, iterative refinement, and self-learning

| Task | Dependency | Changes Required |
|------|------------|------------------|
| Implement parallel agent execution | Phase 3 | Modify: Task execution logic |
| Add iterative refinement loop | Phase 3 | New: Feedback loop tools |
| Integrate QA results into RAG | Phase 3 | Modify: RAG ingestion |
| Performance optimization | Phase 3 | Profiling + tuning |

**Rationale:** These require the basic pipeline to be working first.

---

## Component Boundaries

### New Components

| Component | Responsibility | Location |
|-----------|---------------|----------|
| `QAOrchestrator` | Coordinates 4-agent pipeline, manages context | `ai-engine/crew/qa_orchestrator.py` |
| `TranslatorAgent` | Generates Bedrock code from Java (for re-validation) | `ai-engine/agents/qa_translator.py` |
| `ReviewerAgent` | Code quality validation | `ai-engine/agents/qa_reviewer.py` |
| `TesterAgent` | Test generation + execution | `ai-engine/agents/qa_tester.py` (refactor qa_agent.py) |
| `SemanticCheckerAgent` | Behavior equivalence validation | `ai-engine/agents/qa_semantic.py` (extend validation_agent.py) |
| `QAReportGenerator` | Aggregates all agent outputs | `ai-engine/services/qa_report.py` |

### Modified Components

| Component | Changes | Reason |
|-----------|---------|--------|
| `conversion_crew.py` | Add QA task at end | Integrate QA pipeline |
| `main.py` (backend) | Add QA endpoints | Expose QA status/report |
| `crud.py` | Add validation_results table | Store QA results |
| `validation_agent.py` | Extend for semantic checking | Become Semantic Checker |

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: QA as Gatekeeper (Blocking Conversion)

**What:** Waiting for full QA before allowing conversion to complete.

**Why Bad:** QA takes time; blocking conversion delays user feedback.

**Instead:** QA runs asynchronously after conversion completes. User gets conversion result immediately, QA report follows.

### Anti-Pattern 2: Large Context Passing

**What:** Passing entire conversion history to each agent.

**Why Bad:** Context window limits, increased latency, higher LLM costs.

**Instead:** Pass only relevant context. Use RAG to retrieve needed information.

### Anti-Pattern 3: Tight Coupling Between Agents

**What:** Agents directly calling each other's methods.

**Why Bad:** Hard to modify one agent without breaking others.

**Instead:** Use CrewAI's task-based communication. Agents communicate through task outputs, not direct calls.

### Anti-Pattern 4: Ignoring Existing Validation

**What:** Building new QA from scratch without using existing QAValidatorAgent.

**Why Bad:** Reinventing the wheel; existing validator already checks .mcaddon structure.

**Instead:** Extend existing QAValidatorAgent rather than replacing it.

---

## Scalability Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| **0-50 conversions/day** | Single-threaded sequential QA pipeline is sufficient |
| **50-500 conversions/day** | Add parallel execution for Reviewer+Tester; Redis caching |
| **500+ conversions/day** | Horizontal scaling with queue-based job distribution; dedicated QA workers |

### First Bottleneck: LLM Rate Limits

**Problem:** 4 agents × multiple LLM calls per agent = rate limit exhaustion

**Mitigation:**
- Use CrewAI's built-in retry with exponential backoff
- Implement request queuing with priority
- Cache validation results for identical inputs

### Second Bottleneck: Test Execution Time

**Problem:** Running pytest for each conversion can be slow

**Mitigation:**
- Parallel test execution with pytest-xdist
- Incremental test runs (only test changed files)
- Timeout limits per test suite

---

## Integration Checklist

Before implementing the QA system, verify:

- [ ] Existing conversion crew executes successfully
- [ ] PostgreSQL schema can be extended
- [ ] Redis is accessible for job state
- [ ] RAG knowledge base is populated
- [ ] WebSocket infrastructure exists for progress updates
- [ ] QAValidatorAgent is integrated and tested

---

## Sources

- **Existing Codebase:** `ai-engine/crew/conversion_crew.py`, `ai-engine/agents/qa_validator.py`, `ai-engine/agents/qa_agent.py`
- **Project Context:** `.planning/PROJECT.md` (v4.7 milestone)
- **Stack Reference:** `.planning/research/STACK.md`
- **Features Reference:** `.planning/research/FEATURES.md`
- **CrewAI Documentation:** Sequential task execution, context passing, delegation patterns

---

*Architecture research for: Multi-Agent QA System v4.7*
*Researched: 2026-03-27*