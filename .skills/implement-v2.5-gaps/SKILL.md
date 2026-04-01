---
name: implement-v2.5-gaps
description: Implement v2.5 automation gaps for ModPorter-AI using Pipeline + Supervisor patterns. Use when implementing GAP-2.5-01 through GAP-2.5-06 from docs/GAP-ANALYSIS-v2.5.md.
version: 1.0.0
author: ModPorter-AI Team
metadata:
  modporter:
    milestone: v2.5
    gaps: [GAP-2.5-01, GAP-2.5-02, GAP-2.5-03, GAP-2.5-04, GAP-2.5-05, GAP-2.5-06]
    patterns: [pipeline, supervisor, fallback, learning-from-history]
---

# Implement v2.5 Gaps

Implement automation features for ModPorter-AI Milestone v2.5 following best-practice AI agent patterns.

## Gap Priority Order

Implement in this order (dependencies):

1. **GAP-2.5-01: Mode Classification System** (BLOCKS all others)
2. **GAP-2.5-02: One-Click Conversion** (depends on 2.5-01)
3. **GAP-2.5-03: Smart Defaults Engine** (depends on 2.5-01)
4. **GAP-2.5-04: Enhanced Auto-Recovery** (depends on 2.5-01)
5. **GAP-2.5-05: Intelligent Batch Queuing** (depends on 2.5-01)
6. **GAP-2.5-06: Automation Metrics Dashboard** (depends on 2.5-02-05)

## Pattern: Mode Classification Pipeline

```
┌─────────────────────────────────────────────────────────┐
│           Mode Classification Pipeline                    │
├─────────────────────────────────────────────────────────┤
│  1. Feature Extraction Agent (parallel)                │
│     - Count classes, dependencies                        │
│     - Detect complex features                            │
│     - Analyze mod structure                              │
│                                                         │
│  2. Classifier Agent (supervisor)                       │
│     - Apply rules, determine mode                        │
│     - Calculate confidence                               │
│     - Classify: Simple|Standard|Complex|Expert           │
│                                                         │
│  3. Router Agent                                         │
│     - Route to appropriate conversion pipeline           │
│     - Select mode-specific settings                      │
└─────────────────────────────────────────────────────────┘
```

## Pattern: Smart Defaults Engine

```
┌─────────────────────────────────────────────────────────┐
│              Smart Defaults Engine                       │
├─────────────────────────────────────────────────────────┤
│  INPUT:                                                  │
│  - Mod classification (Simple/Standard/Complex/Expert)   │
│  - User preferences (learned over time)                  │
│  - Historical conversion data                             │
│  - Pattern library matches                               │
├─────────────────────────────────────────────────────────┤
│  PROCESSING:                                             │
│  - Rule-based: IF Simple THEN detail_level=standard      │
│  - Pattern-based: Match similar successful conversions   │
│  - ML-based: Predict optimal settings (future)           │
├─────────────────────────────────────────────────────────┤
│  OUTPUT: Pre-configured conversion settings              │
└─────────────────────────────────────────────────────────┘
```

## Pattern: Auto-Recovery with Supervisor

```
Error Handling Pipeline:
1. Error occurs → Supervisor Agent catches
2. Classify error type (Agent analyzes)
3. Check error pattern library (Known solutions)
4. Attempt recovery strategy (If known)
5. Fallback to degraded mode if recovery fails
6. Escalate to human if all recovery attempts fail
```

## Implementation Files

### GAP-2.5-01: Mode Classification

Create:
- `backend/src/services/mode_classifier.py` - Classification engine
- `backend/src/models/conversion_mode.py` - Mode enum and models
- `backend/src/api/mode_classification.py` - Classification endpoints
- `backend/tests/unit/test_mode_classifier.py` - Tests

### GAP-2.5-02: One-Click Conversion

Create:
- `backend/src/services/smart_defaults.py` - Defaults engine
- `backend/src/services/one_click_converter.py` - One-click workflow
- `backend/tests/unit/test_one_click_converter.py` - Tests

### GAP-2.5-03: Smart Defaults Engine

Enhance smart_defaults.py with:
- Pattern matching from historical conversions
- User preference learning
- Rule-based default selection

### GAP-2.5-04: Auto-Recovery

Create:
- `backend/src/services/error_recovery.py` - Recovery strategies
- `backend/src/services/error_classifier.py` - Error classification
- `backend/src/db/error_patterns.py` - Known error patterns
- `backend/tests/unit/test_error_recovery.py` - Tests

### GAP-2.5-05: Batch Intelligence

Enhance:
- `backend/src/services/batch_queuing.py` - Smart queue management
- `backend/src/services/resource_allocator.py` - GPU/memory tracking
- `backend/tests/unit/test_batch_intelligence.py` - Tests

### GAP-2.5-06: Metrics Dashboard

Create:
- `backend/src/services/automation_metrics.py` - Metrics collection
- `backend/src/api/metrics.py` - Metrics endpoints
- `backend/tests/unit/test_automation_metrics.py` - Tests

## Validation

After implementing each gap:
1. Run unit tests: `cd backend && python3 -m pytest src/tests/unit/test_mode_classifier.py -v`
2. Run integration tests: `cd backend && python3 -m pytest src/tests/integration/ -v`
3. Verify coverage maintained: `cd backend && python3 -m pytest src/tests/unit/ --cov=src --cov-fail-under=80`

## Anti-Patterns to Avoid

```
❌ "Let me first understand..." → Create task, mark in_progress, THEN investigate
❌ Start work without .factory/tasks.md → Always read first
❌ Use sed/awk for edits → Use patch tool
❌ Return code inline → Write to file, return path
❌ Multiple in_progress tasks → Only one at a time
```

## References

- Gap Analysis: `docs/GAP-ANALYSIS-v2.5.md`
- Best Practices: `docs/AI-AGENT-BEST-PRACTICES.md`
- Requirements: `.planning/REQUIREMENTS.md`
