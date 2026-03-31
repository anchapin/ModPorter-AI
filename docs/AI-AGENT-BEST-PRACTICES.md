# AI Agent Software Development Best Practices

**Research Date:** 2026-03-31  
**Purpose:** Research for ModPorter-AI v2.5 automation improvements

---

## 1. Context Management for AI Coding Agents

### 1.1 CLAUDE.md / Context Files

**Best Practice:** Aggressively manage context through project-specific configuration files.

```
Key Patterns:
├── CLAUDE.md          # Project overview, architecture, conventions
├── .claude/           # Agent-specific configurations
├── skills/            # Reusable task patterns
└── memory/            # Cross-session persistent memory
```

**Key Insight:** "Context degradation is the primary failure mode for AI coding agents" - Claude Code Best Practices

**Recommendations:**
- Keep CLAUDE.md concise (<500 lines)
- Include project structure, naming conventions, coding standards
- Document forbidden patterns (e.g., no regex, no vulnerable patterns)
- Use context compression for large codebases

### 1.2 Subagent Architecture

**Best Practice:** Decompose complex tasks into small, focused sub-agents.

From Claude Code subagent documentation:

| Pattern | Use Case | Example |
|---------|----------|---------|
| **Task-specific** | One-off coding tasks | Review PR, Write tests |
| **Role-based** | Specialized expertise | Security auditor, API designer |
| **Orchestrated** | Multi-step workflows | Implement feature E2E |

**Subagent Design Principles:**
1. **Single responsibility** - One clear goal per agent
2. **Explicit inputs/outputs** - Typed interfaces between agents
3. **Token budgets** - Prevent context overflow
4. **Retry logic** - Handle failures gracefully

---

## 2. Multi-Agent Orchestration Patterns

### 2.1 Core Patterns (from Azure AI Architecture)

| Pattern | Description | Best For |
|---------|-------------|----------|
| **Sequential** | Agents execute one after another | Linear workflows (analyze → implement → test) |
| **Parallel** | Multiple agents work simultaneously | Independent tasks (lint, test, build) |
| **Supervisor/Evaluator** | One agent oversees others | Quality control, gatekeeping |
| **Pipeline** | Output of one agent feeds next | Transformations, refinement |
| **Hierarchical** | Manager agents delegate to workers | Large-scale feature development |

### 2.2 ModPorter-AI Relevance

The v2.5 Mode Classification system could use:
- **Pipeline pattern** for classification: Extract → Classify → Route → Process
- **Supervisor pattern** for QA: Classifier validates mode, routes to appropriate pipeline

### 2.3 CrewAI Patterns (Relevant to AI Engine)

```
CrewAI Key Concepts:
├── Agents     # Autonomous workers with specific roles
├── Tasks      # Definable work items with expected output
├── Crews      # Orchestrates agents to complete tasks
└── Processes # Sequential, Parallel, or Hierarchical
```

**Best Practice from CrewAI:** Agents should have:
- Clear role definition
- Specific goal
- Tools appropriate to role
- Backstory for context

---

## 3. CI/CD Integration with AI Agents

### 3.1 AI Agents in Pipeline Stages

| Stage | AI Agent Capability | Benefit |
|-------|---------------------|---------|
| **Pre-commit** | Lint, format, basic tests | Catch issues before PR |
| **Code Review** | Security scan, pattern check | Autonomous review |
| **Build** | Parallel job optimization | Faster builds |
| **Test** | Self-healing tests, auto-analysis | Reduced flakiness |
| **Deploy** | Rollback decision, canary analysis | Safer deployments |

### 3.2 Best Practices for AI + CI/CD

1. **Deterministic Testing** - AI-generated tests must be deterministic
2. **Failure Classification** - AI analyzes failures, routes to appropriate dev
3. **Self-Healing Tests** - AI auto-fixes flaky tests
4. **Autonomous Analysis** - AI investigates failures before human notification

---

## 4. Code Quality with AI Agents

### 4.1 Automated Quality Gates

```
Recommended AI Quality Gates:
├── 1. Pre-commit    → Bandit, formatting, basic lint
├── 2. PR Review     → Security scan, coverage check
├── 3. Merge Gate    → Full test suite, integration tests
├── 4. Production    → Shadow mode, canary analysis
```

### 4.2 Testing Best Practices

| Practice | Implementation |
|----------|---------------|
| **Property-based testing** | AI generates edge cases |
| **Mutation testing** | Verify test quality |
| **Golden path testing** | Cover happy path automatically |
| **Regression detection** | AI identifies affected areas |

---

## 5. Task Management for AI Agents

### 5.1 TODO Management Patterns

**Recommended Pattern (implemented in ModPorter-AI):**
```markdown
# Current Tasks
## In Progress
- 🔄 Task name

## Pending
- ⏳ Task name

## Completed
- ✅ Task name
```

**Key Rules:**
- Only ONE in_progress task at a time
- Mark in_progress BEFORE starting work
- Complete immediately when done
- Break complex tasks into specific actionable items

### 5.2 Anti-Patterns to Avoid

```
FORBIDDEN PHRASES (AI should not say):
❌ "Let me first understand..."
❌ "I'll start by exploring..."
❌ "Let me check what..."
❌ "I need to investigate..."

CORRECT APPROACH:
✅ Create task → Mark in_progress → Investigate → Complete
```

---

## 6. Memory and Continuity

### 6.1 Persistent Memory Systems

| Memory Type | Use Case | Example |
|-------------|----------|---------|
| **Session** | Current task context | Task list, current file |
| **Cross-session** | Long-term facts | User preferences, project conventions |
| **Semantic** | Searchable knowledge | "How did we fix X before?" |
| **Procedural** | How to do things | Skills, workflows |

### 6.2 Best Practices

- Save user preferences proactively
- Document environment facts for future sessions
- Use skills for reusable workflows
- Search session history before asking questions

---

## 7. ModPorter-AI v2.5 Specific Recommendations

Based on research, here's how ModPorter-AI should implement v2.5:

### 7.1 Mode Classification (GAP-2.5-01)

**Recommended Pattern: Pipeline + Supervisor**

```
┌─────────────────────────────────────────────────────────┐
│              Mode Classification Pipeline                 │
├─────────────────────────────────────────────────────────┤
│  1. Feature Extraction Agent (parallel)                │
│     - Count classes, dependencies                      │
│     - Detect complex features                           │
│                                                         │
│  2. Classifier Agent (supervisor)                       │
│     - Apply rules, determine mode                       │
│     - Calculate confidence                              │
│                                                         │
│  3. Router Agent                                        │
│     - Route to appropriate conversion pipeline           │
└─────────────────────────────────────────────────────────┘
```

### 7.2 Smart Defaults (GAP-2.5-03)

**Recommended Pattern: Learning from History**

```
┌─────────────────────────────────────────────────────────┐
│              Smart Defaults Engine                       │
├─────────────────────────────────────────────────────────┤
│  Input:                                                 │
│  - Mod classification (Simple/Standard/Complex/Expert)  │
│  - User preferences (learned over time)                  │
│  - Historical conversion data                            │
│  - Pattern library matches                               │
├─────────────────────────────────────────────────────────┤
│  Processing:                                            │
│  - Rule-based: IF Simple THEN detail_level=standard     │
│  - Pattern-based: Match similar successful conversions   │
│  - ML-based: Predict optimal settings (future)          │
├─────────────────────────────────────────────────────────┤
│  Output: Pre-configured conversion settings             │
└─────────────────────────────────────────────────────────┘
```

### 7.3 Auto-Recovery (GAP-2.5-04)

**Recommended Pattern: Supervisor + Fallback**

```
Error Handling Pipeline:
1. Classify error type (Agent analyzes)
2. Check error pattern library (Known solutions)
3. Attempt recovery strategy (If known)
4. Escalate if failed (Human notification)
```

---

## 8. Key References

| Source | Topic |
|--------|-------|
| Claude Code Docs | Context management, subagents |
| Azure AI Architecture | Multi-agent patterns |
| CrewAI GitHub | Multi-agent orchestration |
| Cursor Best Practices | Agent workflow design |

---

## 9. Summary: Top 10 Best Practices

1. **Context is King** - Aggressively manage, compress, and prioritize context
2. **Single-Responsibility Agents** - Small, focused agents outperform large ones
3. **Pipeline When Possible** - Sequential processing with clear interfaces
4. **Supervisor for Quality** - Evaluator agent gates for quality control
5. **Memory Across Sessions** - Save user preferences, project conventions
6. **TODO Before Action** - Create tasks, mark in_progress, then work
7. **Deterministic CI/CD** - AI + CI requires deterministic outputs
8. **Self-Healing Tests** - AI should fix flaky tests automatically
9. **Skills Over Prompts** - Reusable procedural knowledge beats ad-hoc prompts
10. **Measure and Iterate** - Track automation metrics, improve over time

