---
phase: 16
slug: 16-06-qa-report-generator
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 16-06 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x+ |
| Config file | `pytest.ini` or `pyproject.toml` |
| Quick run command | `pytest tests/test_qa_report.py -x` |
| Full suite command | `pytest tests/qa/` |
| Estimated runtime | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_qa_report.py -x`
- **After every plan wave:** Run `pytest tests/qa/`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 16-06-01 | 01 | 1 | QA-06.1 (Aggregate results) | unit | `pytest tests/test_aggregator.py -x` | ✅ W0 | ⬜ pending |
| 16-06-02 | 01 | 1 | QA-06.2 (Weighted score) | unit | `pytest tests/test_scorer.py -x` | ✅ W0 | ⬜ pending |
| 16-06-03 | 01 | 1 | QA-06.3 (JSON export) | integration | `pytest tests/test_json_exporter.py -x` | ✅ W0 | ⬜ pending |
| 16-06-04 | 02 | 2 | QA-06.4 (HTML export) | integration | `pytest tests/test_html_exporter.py -x` | ✅ W0 | ⬜ pending |
| 16-06-05 | 02 | 2 | QA-06.5 (Markdown export) | integration | `pytest tests/test_markdown_exporter.py -x` | ✅ W0 | ⬜ pending |
| 16-06-06 | 02 | 2 | QA-06.6 (Color-coded severity) | unit | `pytest tests/test_templates.py -x` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_aggregator.py` — stubs for QA-06.1
- [ ] `tests/test_scorer.py` — stubs for QA-06.2
- [ ] `tests/test_json_exporter.py` — stubs for QA-06.3
- [ ] `tests/test_html_exporter.py` — stubs for QA-06.4
- [ ] `tests/test_markdown_exporter.py` — stubs for QA-06.5
- [ ] `tests/test_templates.py` — stubs for QA-06.6
- [ ] `tests/conftest.py` — shared fixtures (if needed)

*Note: These test files should be created in Wave 0 as part of task setup.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Report download via API | QA-06 | Requires running server | Start server, call GET /api/qa/report/{job_id}, verify 200 response |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending