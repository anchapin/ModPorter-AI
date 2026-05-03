# Phase 16-01: QA Context & Orchestration - Research

**Researched:** 2026-03-27
**Domain:** Multi-agent QA orchestration, workflow coordination, context passing
**Confidence:** HIGH

## Summary

Phase 16-01 establishes the core infrastructure for the multi-agent QA system. This phase builds on existing patterns in the codebase (qa_agent.py, RAGPipeline, error_recovery.py) to create a unified orchestration layer that coordinates 4 specialized QA agents (Translator, Reviewer, Tester, Semantic Checker).

**Primary recommendation:** Reuse existing CircuitBreaker from `utils/error_recovery.py`, follow RAGPipeline's stage-based architecture pattern, and integrate as a post-packaging hook in the existing agent pipeline.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| crewai | >=0.11.0 | Agent framework with @tool decorators | Already in project, provides structured agent execution |
| pydantic | >=2.0.0 | Data validation and QAContext dataclass | Type-safe context passing between agents |
| pytest | (dev dep) | Test framework | Already configured in pyproject.toml |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| structlog | >=24.0.0 | Structured logging | Already used throughout project |
| asyncio | stdlib | Async agent execution | For parallel agent execution in Phase 16-07 |
| uuid | stdlib | Unique job IDs | For context tracking |

### Existing Components to Reuse
| Component | Location | Purpose |
|-----------|----------|---------|
| CircuitBreaker | `utils/error_recovery.py:87` | Circuit breaker for failed agents |
| RAGPipeline | `search/rag_pipeline.py:289` | Reference for orchestration pattern |
| TestFramework | `testing/qa_framework.py:44` | Test execution pattern |
| PackagingAgent | `agents/packaging_agent.py` | Post-conversion hook target |

## Architecture Patterns

### Recommended Project Structure
```
ai-engine/src/
├── agents/
│   ├── qa_orchestrator.py      # NEW: QAOrchestrator class
│   └── ...
├── qa/                         # NEW: QA module
│   ├── __init__.py
│   ├── context.py              # NEW: QAContext dataclass
│   ├── orchestrator.py         # NEW: QAOrchestrator
│   ├── hooks.py                # NEW: Post-conversion integration
│   └── validators.py           # NEW: Output schema validation
└── testing/
    └── qa_framework.py         # Existing - extend if needed
```

### Pattern 1: QAContext as Dataclass
**What:** Context object carrying job metadata through the QA pipeline
**When to use:** All agent communications
**Example:**
```python
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class QAContext(BaseModel):
    job_id: str
    job_dir: Path
    source_java_path: Path
    output_bedrock_path: Path
    metadata: Dict[str, Any] = {}
    validation_results: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.now)
    current_agent: Optional[str] = None
```

### Pattern 2: Stage-Based Orchestration (from RAGPipeline)
**What:** Sequential execution with context passing between stages
**When to use:** Coordinating multiple agents in order
**Reference:** `search/rag_pipeline.py:289-411`

### Pattern 3: Circuit Breaker Integration
**What:** Wrap each agent call with CircuitBreaker to handle failures gracefully
**When to use:** Each agent execution
**Reference:** `utils/error_recovery.py:87-226`
```python
from utils.error_recovery import CircuitBreaker, CircuitBreakerOpenError

breaker = CircuitBreaker(name="translator_agent", fail_max=3, reset_timeout=300)
try:
    result = breaker.execute(translator_agent.run, context)
except CircuitBreakerOpenError:
    logger.error("Translator agent circuit open, skipping QA")
```

### Anti-Patterns to Avoid
- **Building custom CircuitBreaker:** Use existing implementation in `utils/error_recovery.py`
- **Hardcoding agent order:** Make pipeline configurable for parallel execution (Phase 16-07)
- **Monolithic orchestrator:** Separate concerns into context, orchestrator, and hooks

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Circuit breaker | Custom implementation | `utils.error_recovery.CircuitBreaker` | Already implemented, tested, and used in project |
| Agent tools | Custom decorators | crewai `@tool` decorator | Consistent with existing agents |
| Logging | Print statements | structlog | Already configured project-wide |
| Configuration | Hardcoded values | pydantic Settings | Type-safe, env var support |

## Common Pitfalls

### Pitfall 1: Context Not Passed Between Agents
**What goes wrong:** Each agent receives fresh context without previous results
**Why it happens:** Not updating QAContext after each agent completes
**How to avoid:** Always return updated context with validation_results merged
**Warning signs:** Agent 2 doesn't know what Agent 1 found

### Pitfall 2: Timeout Not Enforced
**What goes wrong:** Long-running agents block the pipeline indefinitely
**Why it happens:** Not using asyncio.wait_for or timeout decorators
**How to avoid:** Apply timeout at orchestrator level (5 min default)
```python
async def run_agent(agent, context, timeout=300):
    return await asyncio.wait_for(agent.run(context), timeout=timeout)
```

### Pitfall 3: Integration Hook Missing
**What goes wrong:** QA pipeline never gets invoked after conversion
**Why it happens:** Not integrated with PackagingAgent
**How to avoid:** Add post-conversion hook in packaging_agent.py or main pipeline
**Warning signs:** QA only runs when manually triggered

## Code Examples

### Hook Integration Pattern (from Packaging Agent)
```python
# In agents/packaging_agent.py or main pipeline
from agents.qa_orchestrator import QAOrchestrator

def build_mcaddon(self, build_data):
    # ... existing packaging logic ...
    
    # Post-packaging QA hook
    if settings.QA_ENABLED:
        qa_orchestrator = QAOrchestrator()
        qa_result = qa_orchestrator.run_qa_pipeline(job_id, temp_dir)
        # Attach QA result to output
```

### Sequential Execution with Context Passing
```python
async def run_qa_pipeline(self, context: QAContext) -> QAContext:
    agents = ["translator", "reviewer", "tester", "semantic_checker"]
    
    for agent_name in agents:
        context.current_agent = agent_name
        try:
            context = await self.run_agent(agent_name, context)
        except Exception as e:
            if self.circuit_breaker_open(agent_name):
                logger.warning(f"Circuit open for {agent_name}, skipping")
                continue
            raise
    
    return context
```

### Output Schema Validation
```python
from pydantic import BaseModel, ValidationError

class AgentOutput(BaseModel):
    agent_name: str
    success: bool
    result: Dict[str, Any]
    errors: List[str] = []
    execution_time_ms: int

def validate_agent_output(output: Dict) -> AgentOutput:
    try:
        return AgentOutput(**output)
    except ValidationError as e:
        logger.error(f"Agent output validation failed: {e}")
        raise
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| QAAgent runs all tests | 4 specialized agents with context | This phase | Better separation of concerns |
| Synchronous execution | Async pipeline with circuit breaker | This phase + 16-07 | Graceful failure handling |
| No validation between agents | Schema validation after each agent | This phase | Fail fast, better debugging |

## Open Questions

1. **Where exactly should the QA hook integrate?**
   - What we know: After PackagingAgent completes
   - What's unclear: Main pipeline entry point location
   - Recommendation: Add to orchestrator/main.py after packaging, make configurable

2. **Should QA run synchronously or async?**
   - What we know: RAGPipeline is sync, but agent execution could benefit from async
   - What's unclear: Production async requirements
   - Recommendation: Start sync (simpler), add async wrapper for Phase 16-07

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (with pytest-asyncio, pytest-mock, pytest-cov, pytest-timeout) |
| Config file | pyproject.toml [tool.pytest] (defaults) |
| Quick run command | `pytest ai-engine/tests/test_qa_orchestrator.py -x` |
| Full suite command | `pytest ai-engine/tests/ -k "orchestrator or qa_context" --cov=ai-engine/src/qa` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QA-01.1 | QAContext dataclass | unit | `pytest tests/test_qa_context.py -x` | ❌ Wave 0 |
| QA-01.2 | QAOrchestrator class | unit | `pytest tests/test_qa_orchestrator.py -x` | ❌ Wave 0 |
| QA-01.3 | Post-conversion hook | integration | `pytest tests/test_qa_integration.py -x` | ❌ Wave 0 |
| QA-01.4 | Sequential execution | unit | `pytest tests/test_qa_orchestrator.py::test_sequential -x` | ❌ Wave 0 |
| QA-01.5 | Schema validation | unit | `pytest tests/test_qa_validators.py -x` | ❌ Wave 0 |
| QA-01.6 | Timeout handling | integration | `pytest tests/test_qa_timeout.py -x` | ❌ Wave 0 |
| QA-01.7 | Circuit breaker | integration | `pytest tests/test_qa_circuit_breaker.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest ai-engine/tests/test_qa_orchestrator.py -x`
- **Per wave merge:** `pytest ai-engine/tests/test_qa_*.py --cov=ai-engine/src/qa`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `ai-engine/tests/test_qa_context.py` — covers QA-01.1
- [ ] `ai-engine/tests/test_qa_orchestrator.py` — covers QA-01.2, QA-01.4
- [ ] `ai-engine/tests/test_qa_integration.py` — covers QA-01.3
- [ ] `ai-engine/tests/test_qa_validators.py` — covers QA-01.5
- [ ] `ai-engine/tests/test_qa_timeout.py` — covers QA-01.6
- [ ] `ai-engine/tests/test_qa_circuit_breaker.py` — covers QA-01.7
- [ ] `ai-engine/src/qa/` — module directory with __init__.py
- [ ] Framework install: `pip install ai-engine[dev]` — if not already

## Sources

### Primary (HIGH confidence)
- `agents/qa_agent.py` - Existing QA agent patterns
- `search/rag_pipeline.py:289` - RAGPipeline orchestration reference
- `utils/error_recovery.py:87` - CircuitBreaker implementation
- `pyproject.toml` - Test framework configuration

### Secondary (MEDIUM confidence)
- crewai documentation - Agent tool patterns

### Tertiary (LOW confidence)
- N/A - Strong internal patterns available

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in project
- Architecture: HIGH - Reuses existing patterns from RAGPipeline and error_recovery
- Pitfalls: MEDIUM - Based on existing codebase patterns and general best practices

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (30 days - stable domain)