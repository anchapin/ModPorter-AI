# AGENTS.md - ModPorter AI Development Guide

<!-- TODO_MANAGEMENT_INSTRUCTIONS -->

## CRITICAL: Task Management System

**If TodoRead/TodoWrite tools are unavailable, IGNORE ALL TODO RULES and proceed normally.**

### MANDATORY TODO WORKFLOW

**BEFORE responding to ANY request, you MUST:**

1. **Call `TodoRead()` first** - Check current task status before doing ANYTHING
2. **Plan work based on existing todos** - Reference what's already tracked
3. **Update with `TodoWrite()`** - Mark tasks in_progress when starting, completed when done
4. **NEVER work without consulting the todo system first**

### CRITICAL TODO SYSTEM RULES

- **Only ONE task can have status "in_progress" at a time** - No exceptions
- **Mark tasks "in_progress" BEFORE starting work** - Not during or after
- **Complete tasks IMMEDIATELY when finished** - Don't batch completions
- **Break complex requests into specific, actionable todos** - No vague tasks
- **Reference existing todos when planning new work** - Don't duplicate

### MANDATORY VISUAL DISPLAY

**ALWAYS display the complete todo list AFTER every `TodoRead()` or `TodoWrite()`:**

```
Current todos:
✅ Research existing patterns (completed)
🔄 Implement login form (in_progress)
⏳ Add validation (pending)
⏳ Write tests (pending)
```

Icons: ✅ = completed | 🔄 = in_progress | ⏳ = pending

**NEVER just say "updated todos"** - Show the full list every time.

### CRITICAL ANTI-PATTERNS

**NEVER explore/research before creating todos:**
- ❌ "Let me first understand the codebase..." → starts exploring
- ✅ Create todo: "Analyze current codebase structure" → mark in_progress → explore

**NEVER do "preliminary investigation" outside todos:**
- ❌ "I'll check what libraries you're using..." → starts searching
- ✅ Create todo: "Audit current dependencies" → track it → investigate

**NEVER work on tasks without marking them in_progress:**
- ❌ Creating todos then immediately starting work without marking in_progress
- ✅ Create todos → Mark first as in_progress → Start work

**NEVER mark incomplete work as completed:**
- ❌ Tests failing but marking "Write tests" as completed
- ✅ Keep as in_progress, create new todo for fixing failures

### FORBIDDEN PHRASES

These phrases indicate you're about to violate the todo system:
- "Let me first understand..."
- "I'll start by exploring..."
- "Let me check what..."
- "I need to investigate..."
- "Before we begin, I'll..."

**Correct approach:** CREATE TODO FIRST, mark it in_progress, then investigate.

### TOOL REFERENCE

```python
TodoRead()  # No parameters, returns current todos
TodoWrite(todos=[...])  # Replaces entire list

Todo Structure:
{
  "id": "unique-id",
  "content": "Specific task description",
  "status": "pending|in_progress|completed",
  "priority": "high|medium|low"
}
```

<!-- END_TODO_MANAGEMENT_INSTRUCTIONS -->

---

## Build/Test Commands
- `pnpm run dev` - Start all services (frontend:3000, backend:8000)
- `pnpm run test` - Run all tests (frontend + backend)
- `cd frontend && pnpm test -- ConversionUpload.test.tsx` - Single frontend test
- `cd backend && source .venv/bin/activate && python -m pytest tests/test_main.py::test_specific_function` - Single backend test
- `pnpm run lint` - Lint all services (ESLint + Ruff)
- `pnpm run format` - Format code (Prettier + Black)

## Code Style
- **Frontend**: TypeScript + React, Prettier (2 spaces, single quotes), ESLint strict mode
- **Backend**: Python + FastAPI, Black formatter, Ruff linter, type hints required
- **Imports**: Absolute imports preferred, group by: stdlib, third-party, local
- **Naming**: camelCase (TS), snake_case (Python), PascalCase (components/classes)
- **Types**: Strict TypeScript, Pydantic models for API, interface definitions required
- **Error Handling**: Try-catch with specific error types, HTTP status codes, user-friendly messages
- **Testing**: Vitest (frontend), pytest with async support (backend), 80% coverage minimum
- **Comments**: JSDoc for public APIs, docstrings for Python functions, PRD feature references
- **Files**: Component folders with .tsx/.stories.tsx/.test.tsx, Python modules with __init__.py

## Architecture Notes
Multi-service app: React frontend, FastAPI backend, CrewAI engine. Follow existing patterns in components/ and services/.

---

## Advanced Development Guidelines

### Important: AI Coding Agent Guidelines

**CRITICAL FOR AI CODING AGENTS:**
- Always use `python3` command explicitly - never use just `python` or `python3.11` or other version-specific commands
- **Virtual Environment Management**: 
  - Use only `.venv` (dot-venv) directory for the virtual environment
  - Create virtual environment with: `python3 -m venv .venv`
  - Always activate with: `source .venv/bin/activate`
  - **NEVER** create multiple virtual environments (e.g., `venv`, `.venv` simultaneously)
  - **ALWAYS** activate the virtual environment before running any Python commands
- When running Python commands, always prefix with `python3 -m` (e.g., `python3 -m pytest`, `python3 -m black`)
- This ensures compatibility across all development environments and prevents version conflicts

### Core Principle: Test-Driven and Spec-Driven Development

All contributions **must** follow a Test-Driven Development (TDD) or Spec-Driven Development (SDD) approach. This means that for any new feature, tool, or agent, a corresponding test or specification must be written *before* the implementation code.

### ModPorter-AI Technology Stack

**Frontend Stack:**
- **React 19** + TypeScript + Vite + Vitest + Storybook
- Component design with Storybook integration
- TypeScript optimization and type safety
- Vite build optimization and performance

**Backend Stack:**
- **FastAPI** + Python + SQLAlchemy + PostgreSQL + Redis
- RESTful API design and async patterns
- Pydantic models and validation
- Performance and security best practices

**AI Engine Stack:**
- **CrewAI** + LangChain + OpenAI/Anthropic APIs + ChromaDB
- Multi-agent system design
- LangChain integration patterns
- Agent coordination and workflow optimization
- Vector database and RAG implementation

**Infrastructure:**
- **Docker Compose** + Nginx + Multi-service architecture
- Multi-service orchestration
- Container optimization and health checks
- Volume management and networking

### Security and Compliance Framework

#### Zero-Trust Security Model
- **Identity Verification**: Agent identity and permissions verification
- **Data Encryption**: AES-256 at rest, TLS 1.3 in transit
- **Data Classification**: Public, Internal, Confidential, Restricted
- **API Key Management**: Secure credential handling with environment variables

#### Compliance Requirements
- **Audit Trail**: Complete audit logs for all operations
- **Data Protection**: PII anonymization and secure memory handling
- **Regulatory Compliance**: Framework for financial regulations (SOX, MiFID II, GDPR)

### Performance Guidelines

#### Performance Benchmarks
- **Decision Latency**: < 500ms for standard operations
- **Memory Usage**: < 2GB per agent instance
- **CPU Utilization**: < 80% sustained
- **Throughput**: > 100 decisions/minute per agent

#### Caching Architecture
- **Multi-Level Cache**: L1 (in-memory), L2 (Redis), L3 (database)
- **Market-State-Aware Caching**: Minimize LLM inference calls
- **Resource Management**: Dynamic resource allocation based on availability

### Monitoring and Observability

#### Required Metrics
- **Agent Performance**: Decision accuracy, response time, resource utilization
- **Business Metrics**: Success rate, error rates, cost per decision
- **System Health**: Memory usage, CPU utilization, cache hit rates

#### Logging Standards
- **Required Fields**: correlation_id, agent_id, decision_type, confidence_score
- **Structured Logging**: JSON format with correlation IDs
- **Log Aggregation**: Centralized logging with search capabilities

#### Alerting Requirements
- **Critical Alerts**: Response time > 5s, accuracy < 70%, system failures
- **Warning Alerts**: Response time > 2s, accuracy 70-80%, error rate > 5%

### Error Handling and Recovery

#### Error Classification
- **Critical Errors**: Data feed failures, LLM service unavailability, trading execution failures
- **Non-Critical Errors**: Individual decision failures, optional timeouts

#### Resilience Patterns
- **Circuit Breaker**: Automatic failure detection and recovery
- **Graceful Degradation**: Fallback to rule-based decisions
- **Retry with Exponential Backoff**: Handle transient failures

### Git Workflow and Branching Strategy

#### Critical Safety Protocol
- **Branch Verification**: Always check current branch before git operations
- **Feature Branch Requirement**: Never commit directly to main
- **Naming Convention**: feature/, issue/, bugfix/, refactor/

#### Pre-Commit Checklist
- [ ] Session cleanup and artifact removal
- [ ] Duplicate file cleanup
- [ ] Documentation alignment
- [ ] Test coverage verification

### Code Quality Standards

#### Anti-Slop Guidelines
- **Scope Verification**: Match requirements exactly, no over-engineering
- **Duplicate Detection**: Use existing functionality instead of duplicating
- **Complexity Audit**: Ensure abstractions serve clear purposes
- **Session Cleanup**: Remove temporary files and obsolete progress files

#### Quality Requirements
- **Code Coverage**: 80% minimum for all new code
- **Linting**: Black formatting, flake8 linting, mypy type checking
- **Testing**: Parallel execution support, intelligent caching, isolation
- **Documentation**: JSDoc for APIs, docstrings for functions, PRD references

### Project Structure

```
/quantchain/
├── /agents/        # Agent implementations
├── /tools/         # Tool and data library components
├── /connectors/    # Data feed connectors
├── /backtesting/   # Backtesting engine
├── /core/          # Core agent engine and shared utilities
/specs/             # Specification files for components and agents
/tests/             # Test suites, including unit, integration, and backtests
/docs/              # Documentation, including deployment guides
/examples/          # Sample agents and configurations
```

### CI/CD Integration

#### Testing Requirements
- **Parallel Execution**: All tests support parallel execution
- **Fast Feedback**: Full test suite under 5 minutes
- **Intelligent Caching**: Cache pytest data between runs
- **Performance Monitoring**: Track and optimize slow tests

#### Quality Gates
- **Coverage Check**: Fail if below 80% coverage
- **Lint Check**: Automated code formatting and quality checks
- **PR Review**: Mandatory code review before merging
- **Branch Protection**: Prevent direct main branch commits