# Pitfalls Research

**Domain:** Multi-Agent QA System for AI-Powered Code Conversion
**Researched:** 2026-03-27
**Confidence:** MEDIUM

## Executive Summary

This document identifies common pitfalls when adding multi-agent QA (Translator, Reviewer, Tester, Semantic Checker) to an existing AI-powered Java→Bedrock mod converter. Research draws from CrewAI, AutoGen, and Semantic Kernel documentation, plus industry patterns for code generation pipelines. The primary risks involve agent coordination failures, non-deterministic behavior, and integration conflicts with existing conversion pipelines.

---

## Critical Pitfalls

### Pitfall 1: Agent Coordination Failure — Circular Dependencies

**What goes wrong:**
The Translator, Reviewer, Tester, and Semantic Checker agents enter a deadlock or infinite loop where each waits for output from another that never completes. For example: Reviewer waits for Translator to finish, but Translator is blocked waiting for Reviewer's feedback on a previous iteration.

**Why it happens:**
- Agents lack clear dependency definitions and execution order
- No timeout mechanism for inter-agent communication
- Circular feedback loops没有被显式处理

**How to avoid:**
1. Define explicit dependency DAG (Directed Acyclic Graph) for agent workflows
2. Implement timeout guards for each agent's response expectations
3. Use sequential task execution for tightly coupled agents (Translator→Reviewer→Tester)
4. Reserve parallel execution for independent checks only (multiple validation agents running simultaneously)

**Warning signs:**
- Agent execution logs showing "waiting for response" lasting >30 seconds
- Multiple agents reporting "blocked by upstream task"
- Conversation history growing without progress

**Phase to address:** Agent Orchestration Phase (Phase 1-2 of QA pipeline)

---

### Pitfall 2: Non-Deterministic Validation Results

**What goes wrong:**
The same code conversion produces different QA results on different runs. A Reviewer agent might flag issues in one run that it misses in another, or Semantic Checker gives contradictory behavior equivalence assessments for identical input.

**Why it happens:**
- LLM providers have temperature/setting variability between calls
- Agent instructions lack specific rubrics with deterministic checks
- Context window variations cause different code portions to be evaluated

**How to avoid:**
1. Set `temperature=0` for all QA agent LLM calls
2. Create explicit validation checklists with binary pass/fail criteria
3. Implement deterministic code analysis (regex, AST parsing) alongside LLM-based checks
4. Cache validation results with content hash keys

**Warning signs:**
- Same code passing Reviewer on one run, failing on another
- Semantic Checker reports different "confidence scores" for identical conversions
- User complaints about inconsistent QA feedback

**Phase to address:** Agent Prompt Engineering Phase (Phase 2 of QA pipeline)

---

### Pitfall 3: Silent Failures — Agent Completes But Output Is Unusable

**What goes wrong:**
Agent reports success (exit code 0) but produces empty, malformed, or nonsense output. For example: Translator generates valid JSON syntax but the content is garbage; Tester produces test files that don't compile.

**Why it happens:**
- Success判定只基于API响应状态，不验证输出质量
- No output validation schema enforcement
- Agent hallucinates compliance when it cannot complete the task

**How to avoid:**
1. Implement output schema validation for every agent
2. Add "sanity check" functions after each agent completes
3. Define minimum quality thresholds (e.g., Tester output must have ≥1 test case)
4. Log raw outputs for debugging even on "success"

**Warning signs:**
- QA pipeline reports "complete" but subsequent phases fail with "empty input"
- Generated test files have syntax errors on import
- Semantic Checker output lacks required fields (confidence_score, behavioral_analysis)

**Phase to address:** Agent Output Validation Phase (Phase 3 of QA pipeline)

---

### Pitfall 4: Context Window Overflow — Early Truncation

**What goes wrong:**
When multiple agents analyze the same code, context accumulates and the LLM truncates important code sections. Later agents (Semantic Checker) only see partial code, leading to incorrect assessments.

**Why it happens:**
- Each agent appends to shared conversation history
- No mechanism to truncate or summarize intermediate results
- Large Java mod files exceed token limits when passed through multiple agents

**How to avoid:**
1. Implement context compression between agent handoffs
2. Pass only relevant code subsets to each agent (e.g., Reviewer gets full code, Tester gets function signatures only)
3. Use structured output (JSON) instead of natural language for inter-agent communication
4. Set hard token budgets per agent with overflow detection

**Warning signs:**
- Logs showing "context truncated" warnings
- Semantic Checker reports "unable to analyze" for certain code sections
- QA feedback only references first 50% of the converted code

**Phase to address:** Agent Memory Management Phase (Phase 2 of QA pipeline)

---

### Pitfall 5: Integration Conflict — QA Pipeline Breaks Existing Conversion

**What goes wrong:**
Adding multi-agent QA breaks the existing conversion pipeline. The new QA layer introduces latency, errors, or incompatible data formats that cascade into the conversion process.

**Why it happens:**
- No clear API boundaries between conversion and QA components
- QA agents expect different input formats than the conversion pipeline produces
- Shared state (database connections, cache) creates race conditions

**How to avoid:**
1. Design QA pipeline as独立的消费者，而非转换管道的侵入式修改
2. Use queue-based architecture: conversion outputs to queue, QA consumes from queue
3. Create adapter layer to normalize data between conversion and QA formats
4. Implement circuit breaker pattern for QA failures (fail gracefully without blocking conversion)

**Warning signs:**
- Conversion成功率在添加QA后下降
- New dependencies conflict with existing requirements
- Database connection errors increase after QA deployment

**Phase to address:** Integration Architecture Phase (Phase 1 of QA pipeline)

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip output validation during MVP | Faster agent deployment | Silent failures undetected until production | Never — always validate outputs |
| Use single shared LLM client across all agents | Reduced resource usage | Rate limiting blocks entire pipeline | Only with explicit rate limit handling |
| Hard-code agent prompts | Simpler initial setup | Every change requires code modification | Only for Phase 1, migrate to config in Phase 2 |
| Skip timeout implementation for "quick" agents | No perceived latency | Infinite hangs in production | Never |
| Reuse conversion's error handling for QA | No new error patterns to learn | QA failures crash entire system | Never — separate error domains |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| CrewAI/LangChain | Not specifying `verbose=True` during development | Enable verbose logging from day 1 for debugging |
| CodeT5+ Translation Output | Assuming translator output format never changes | Version the output schema, validate on both ends |
| PostgreSQL (pgvector) | QA agents make individual DB connections | Use connection pooling, single session for pipeline |
| Redis Cache | Cache invalidation not handled for QA state | Implement TTL or explicit invalidation triggers |
| FastAPI Backend | QA runs synchronously, blocking conversion requests | Run QA asynchronously with webhooks or polling |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| All 4 QA agents run sequentially | 4x latency increase | Use parallel where independent | At >10 conversions/minute |
| Large mod files sent to all agents | Token costs 4x higher | Use context window optimization | Mods >10K lines of code |
| No result caching | Repeated QA on same code | Cache results with content hash | Repeated conversions of same mod |
| Synchronous LLM calls | Blocking I/O slows pipeline | Implement async/await for all LLM calls | >50 concurrent conversions |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Prompt injection via mod code content | Agent executes attacker-controlled prompts | Sanitize code input before prompt insertion |
| Storing intermediate conversion results | Sensitive user code in plaintext DB | Encrypt stored artifacts, auto-purge after 24h |
| No rate limiting on QA endpoints | DoS via repeated QA requests | Implement per-user rate limits |
| Agent tool execution without approval | Unintended system modifications | Require human approval for file system tools |

---

## "Looks Done But Isn't" Checklist

- [ ] **Agent orchestration:** Defined workflow but forgot to handle timeout when agent fails to respond
- [ ] **Validation:** Agent returns "pass" but output schema fields are empty — need schema validation
- [ ] **Semantic Checker:** Claims to validate "behavioral equivalence" but only checks syntax — verify with test execution
- [ ] **Error handling:** QA pipeline fails but no user-facing error message — add error aggregation
- [ ] **Caching:** Implemented cache but didn't handle stale cache for updated conversion models
- [ ] **Logging:** Agent works in dev but no production logs — implement structured logging from start

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Circular dependency deadlock | MEDIUM | Add timeout → kill stuck agent → restart pipeline from last checkpoint |
| Non-deterministic results | HIGH | Re-run with `temperature=0` → audit prompt variations → lock LLM version |
| Silent output failures | LOW | Add output validation in next run → report which agent produced bad output |
| Context overflow | MEDIUM | Identify truncation point → implement context compression → re-run |
| Integration conflict | HIGH | Rollback to pre-QA version → redesign API boundary → re-test integration |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Agent coordination failure | Phase 1: Agent Orchestration Setup | Run 10 parallel conversions, verify no hangs |
| Non-deterministic results | Phase 2: Agent Prompt Engineering | Run same code 3 times, verify identical output |
| Silent failures | Phase 3: Output Validation Layer | Test with intentionally malformed translator output |
| Context overflow | Phase 2: Agent Memory Management | Test with 15K+ line mod files |
| Integration conflict | Phase 1: Integration Architecture | Run full conversion + QA, verify conversion still succeeds |

---

## Sources

- CrewAI documentation: Troubleshooting multi-agent flows, agent performance bottlenecks
- AutoGen issues (2,500+ closed): Non-deterministic interactions, tool argument flow problems
- Semantic Kernel: Multi-agent orchestration patterns, sequential vs concurrent execution
- DeepSeek-Coder: Trust remote code errors, evaluation pipeline challenges
- Industry patterns: Code generation validation, LLM output verification

---

*Pitfalls research for: Multi-Agent QA System Integration*
*Researched: 2026-03-27*