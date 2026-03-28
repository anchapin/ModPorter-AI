---
phase: 16-04-fixer-agent
plan: "01"
subsystem: qa
tags: [qa, fixer, auto-fix, validation, bedrock]
dependency_graph:
  requires:
    - 16-03-reviewer-agent
  provides:
    - FixerAgent
    - fix function
  affects:
    - qa/__init__.py
    - qa/orchestrator
tech_stack:
  added:
    - FixerAgent class
    - FixResult class
  patterns:
    - Same agent pattern as ReviewerAgent
    - ESLint --fix execution
    - JSON schema auto-fix
    - TypeScript type fixes
    - Fix revalidation
    - Fix rate calculation
key_files:
  created:
    - ai-engine/qa/fixer.py
    - ai-engine/tests/test_fixer_agent.py
  modified:
    - ai-engine/qa/__init__.py
decisions:
  - "Used subprocess for ESLint --fix with graceful handling of missing tools"
  - "Implemented fix rate: (fixes_applied / fixes_attempted) * 100"
  - "Created FixResult class for structured fix reporting"
metrics:
  duration: "~3 minutes"
  completed: "2026-03-27"
  tests: 20
  files_created: 2
---

# Phase 16-04 Plan 01: Fixer Agent Summary

## Overview

Implemented Fixer Agent (QA-04) for the QA pipeline - attempts to auto-fix issues found by Reviewer Agent.

## What Was Built

**FixerAgent class** (`ai-engine/qa/fixer.py`):
- Takes QAContext as input (receives from QAOrchestrator after ReviewerAgent)
- Reads review results from context.validation_results['reviewer']
- Attempts auto-fix for ESLint issues using eslint --fix
- Fixes common JSON schema errors (missing keys, invalid values)
- Corrects simple TypeScript type errors
- Validates fixes don't introduce new issues by re-running review
- Reports what was fixed and what couldn't be fixed
- Uses validate_agent_output before returning
- Stores fix results in context.validation_results['fixer']

**Unit tests** (`ai-engine/tests/test_fixer_agent.py`):
- 20 tests covering all core functionality
- Tests verify imports, instantiation, QAContext handling
- Tests for ESLint, JSON schema, TypeScript fixes
- Tests for fix rate calculation and revalidation
- All tests pass

**QA module exports** (`ai-engine/qa/__init__.py`):
- Added FixerAgent and fix to exports

## Key Implementation Details

- **Fix Rate**: `(fixes_applied / fixes_attempted) * 100`
- **Tool Handling**: Gracefully handles missing tools (ESLint, tsc) by skipping checks
- **JSON Schema Fixes**: Adds missing format_version, description, identifier keys
- **TypeScript Fixes**: Fixes import types, null/undefined comparisons
- **Revalidation**: Runs tsc --noEmit to verify fixes don't break compilation

## Verification

All 20 unit tests pass:
```
tests/test_fixer_agent.py - 20 passed
```

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check

- [x] FixerAgent class exists in ai-engine/qa/fixer.py
- [x] Can be imported: `from qa.fixer import FixerAgent`
- [x] Accepts QAContext and returns AgentOutput
- [x] Has execute() method that performs fixes
- [x] Unit tests created and passing (20 tests)
- [x] Integration with QAOrchestrator ready (same interface as Translator/Reviewer)
- [x] ESLint fix attempted
- [x] JSON schema fixes applied
- [x] TypeScript fix attempted
- [x] Fix validation working (revalidation)
- [x] Fix report generated with fix rate

## Self-Check: PASSED