---
name: automation-index
description: Master index of all automation scripts, skills, and workflows for ModPorter-AI.
version: 1.0.0
---

# ModPorter-AI Automation Index

This document provides quick access to all automation infrastructure for AI agent development.

## 📁 Directory Structure

```
scripts/automation/
├── run-pre-commit.sh      # Pre-commit quality gates
├── auto-test.sh          # Intelligent test runner
├── setup-git-hooks.sh     # Git hooks setup
├── run-ai-agent.sh       # AI agent runner (this file)
└── ...

.claude/
├── commands/             # Slash commands
│   └── gsd/             # GSD workflow commands
├── skills/              # Claude Code skills
└── hooks/               # Claude hooks

.skills/                  # ModPorter-AI custom skills
├── implement-v2.5-gaps/ # v2.5 implementation workflow
├── auto-code-review/    # Automated code review
└── tdd-workflow/        # Test-driven development

.github/workflows/
├── ai-quality-gates.yml  # Full CI/CD with AI quality gates
└── ...
```

## 🚀 Quick Start

### For New Developers

```bash
# 1. Setup git hooks (one-time)
./scripts/automation/setup-git-hooks.sh

# 2. Install dependencies
cd backend && pip install -r requirements.txt

# 3. Run tests
./scripts/automation/auto-test.sh unit-fast

# 4. Verify everything works
./scripts/automation/auto-test.sh full
```

### For AI Agents

```bash
# Read CLAUDE.md first (MANDATORY)
cat CLAUDE.md

# Read current tasks
cat .factory/tasks.md

# Run pre-commit checks
./scripts/automation/run-pre-commit.sh

# Run tests
./scripts/automation/auto-test.sh unit
```

## 🎯 Available Skills

### Custom Skills (`.skills/`)

| Skill | Purpose | When to Use |
|-------|--------|-------------|
| `implement-v2.5-gaps` | Implement v2.5 automation gaps | Working on GAP-2.5-01 through GAP-2.5-06 |
| `auto-code-review` | Automated code review | Reviewing PRs or code changes |
| `tdd-workflow` | Test-driven development | Implementing new features with TDD |

### Claude Code Skills (bundled)

| Skill | Purpose | When to Use |
|-------|--------|-------------|
| `plan` | Plan mode | When user wants a plan instead of execution |
| `code-review` | Code review | Reviewing code for quality/security |
| `subagent-driven` | Multi-agent orchestration | Complex tasks needing parallel work |
| `systematic-debugging` | Debug workflow | Investigating bugs or failures |
| `test-driven-development` | TDD workflow | Implementing with tests first |

## 🔧 Scripts

### Test Scripts

```bash
# Fast unit tests (no coverage) - for quick feedback
./scripts/automation/auto-test.sh unit-fast

# Unit tests with coverage gate (80%)
./scripts/automation/auto-test.sh unit

# Integration tests
./scripts/automation/auto-test.sh integration

# Full test suite
./scripts/automation/auto-test.sh full

# Split batches (for CI memory optimization)
./scripts/automation/auto-test.sh split
```

### Pre-Commit Script

```bash
# Run all quality gates manually
./scripts/automation/run-pre-commit.sh

# This includes:
# - Ruff format check
# - Ruff lint check
# - Bandit security scan
# - Gitleaks secrets detection
# - Quick unit test pass
```

### Git Hooks

```bash
# Install/update git hooks
./scripts/automation/setup-git-hooks.sh

# Installs:
# - pre-commit: Quality gates before commit
# - commit-msg: Conventional commit validation
# - post-checkout: Environment reminders
```

## 📋 CI/CD Pipeline

### Quality Gates (Automated)

```
┌─────────────────────────────────────────────────────────┐
│                    CI/CD Pipeline                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. Pre-Commit (local)                                  │
│     - Format check (ruff)                               │
│     - Lint check (ruff)                                 │
│     - Security scan (bandit)                             │
│     - Secrets detection (gitleaks)                       │
│     - Quick unit tests                                   │
│                                                         │
│  2. PR Checks (CI)                                      │
│     - Unit tests (split batches)                        │
│     - Coverage gate (80%)                               │
│     - Integration tests                                 │
│     - Security scan (Trivy, Bandit)                      │
│                                                         │
│  3. AI Code Review                                      │
│     - Automated pattern review                          │
│     - Security analysis                                 │
│     - Performance analysis                              │
│                                                         │
│  4. Merge Gate                                          │
│     - All green                                         │
│     - 1+ approval                                       │
│     - Coverage maintained                               │
└─────────────────────────────────────────────────────────┘
```

### GitHub Actions Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ai-quality-gates.yml` | PR/push | Full CI/CD with AI gates |
| `ci-tests.yml` | PR/push | Test execution |
| `ci-security.yml` | PR/push | Security scanning |
| `ci-lint.yml` | PR/push | Code quality |
| `deploy-staging.yml` | Push to develop | Staging deploy |
| `deploy-prod.yml` | Release tag | Production deploy |

## 🎓 Best Practices Patterns

### Pipeline Pattern
```
Input → Agent 1 → Agent 2 → Agent 3 → Output
              ↓
         Supervisor (evaluates, routes)
```

### Supervisor Pattern
```
Supervisor Agent
    ├── Sub-Agent 1 (specialized task)
    ├── Sub-Agent 2 (specialized task)
    └── Sub-Agent 3 (specialized task)
```

### Fallback Pattern
```
Try → Catch Error → Classify → Recover → Fallback
```

## 📖 Documentation

| Document | Purpose |
|----------|---------|
| `CLAUDE.md` | Project conventions, patterns, rules for AI agents |
| `docs/GAP-ANALYSIS-v2.5.md` | v2.5 gaps tracking |
| `docs/AI-AGENT-BEST-PRACTICES.md` | AI agent development research |
| `.planning/REQUIREMENTS.md` | Project requirements |
| `.planning/ROADMAP.md` | Project roadmap |

## 🔄 Workflow Templates

### TDD Workflow
```bash
# 1. Create task
# 2. Mark in_progress
# 3. Write RED test (failing)
# 4. Write GREEN code (passing)
# 5. REFACTOR code (improving)
# 6. Run tests
# 7. Complete task
```

### Code Review Workflow
```bash
# 1. Run auto-code-review skill
# 2. Address findings
# 3. Human review
# 4. Approve/Request changes
```

### Bug Fix Workflow
```bash
# 1. Create task
# 2. Write failing test (reproduces bug)
# 3. Fix bug
# 4. Verify test passes
# 5. Complete task
```

## ⚠️ Anti-Patterns (Forbidden)

AI agents must NOT say:
```
❌ "Let me first understand..."
❌ "I'll start by exploring..."
❌ "Let me check what..."
❌ "I need to investigate..."

CORRECT: Create task → Mark in_progress → Investigate → Implement → Complete
```

AI agents must NOT:
```
❌ Use sed/awk for edits → Use patch tool
❌ Return code inline → Write to file
❌ Use cat/head/tail for reading → Use read_file tool
❌ Start work without .factory/tasks.md → ALWAYS read first
```

## 📞 Support

- **CI Issues:** Check GitHub Actions logs
- **Test Failures:** Run `./scripts/automation/auto-test.sh full` locally
- **Hook Issues:** Run `./scripts/automation/run-pre-commit.sh` manually to debug
- **Skills Questions:** See individual SKILL.md files

---

**Last Updated:** 2026-03-31
