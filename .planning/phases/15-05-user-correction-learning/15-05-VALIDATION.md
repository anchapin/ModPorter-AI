---
phase: 15-05
slug: user-correction-learning
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 15-05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest / pytest-asyncio |
| **Config file** | `ai-engine/tests/conftest.py` |
| **Quick run command** | `cd ai-engine && python -m pytest tests/test_correction*.py -v` |
| **Full suite command** | `cd ai-engine && python -m pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_correction*.py -v`
- **After every plan wave:** Run `python -m pytest tests/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 15-05-01-01 | 01 | 1 | RAG-5.1 | unit | `python -m pytest tests/test_correction_store.py -v` | ✅ | ⬜ pending |
| 15-05-01-02 | 01 | 1 | RAG-5.1 | integration | `python -m pytest tests/test_feedback_api.py -v` | ✅ | ⬜ pending |
| 15-05-01-03 | 01 | 1 | RAG-5.1 | unit | `python -m pytest tests/test_correction_store.py -v` | ✅ | ⬜ pending |
| 15-05-02-01 | 02 | 2 | RAG-5.2 | unit | `python -m pytest tests/test_validation_workflow.py -v` | ✅ | ⬜ pending |
| 15-05-02-02 | 02 | 2 | RAG-5.2 | unit | `python -m pytest tests/test_feedback_reranker.py -v` | ✅ | ⬜ pending |
| 15-05-02-03 | 02 | 2 | RAG-5.2 | integration | `python -m pytest tests/test_search_integration.py -v` | ✅ | ⬜ pending |
| 15-05-02-04 | 02 | 2 | RAG-5.2 | e2e | `python -m pytest tests/ -v --tb=short` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `ai-engine/tests/test_correction_store.py` — stubs for correction storage tests
- [ ] `ai-engine/tests/test_feedback_api.py` — stubs for feedback API tests
- [ ] `ai-engine/tests/test_validation_workflow.py` — stubs for validation workflow tests
- [ ] `ai-engine/tests/test_feedback_reranker.py` — stubs for feedback re-ranker tests
- [ ] `ai-engine/tests/test_search_integration.py` — stubs for search integration tests
- [ ] `ai-engine/tests/conftest.py` — shared fixtures (may exist)

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| User correction UI submission | RAG-5.1 | Frontend only | Test via browser UI |
| Human review approval workflow | RAG-5.2 | Requires admin access | Test via admin panel |
| Search result improvement perception | RAG-5.2 | Subjective quality | A/B testing with users |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** {pending / approved YYYY-MM-DD}
