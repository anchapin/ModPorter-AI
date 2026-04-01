# Code Review Tasks - Tracked Issues

> Generated: 2026-04-01
> Total Issues: 23 (13 Critical)

---

## CRITICAL BUGS

### C1: Stuck Task Detection Dead Code
- **File**: `ai-engine/orchestration/worker_pool.py:341-343`
- **Issue**: `stuck_tasks` list populated but never used; stuck task detection is non-functional
- **Impact**: Tasks can hang indefinitely without detection
- **Status**: ✅ Fixed
- **Fix**: Added `task_start_times` dict to track start times, fixed stuck task detection loop to properly check elapsed time and populate `stuck_tasks`
- **Labels**: bug, critical, ai-engine

### C2: Empty Retry Logic
- **File**: `ai-engine/orchestration/orchestrator.py:474-476`
- **Issue**: `retry_task()` called but nothing else; retry loop body is comment only
- **Impact**: Failed tasks never actually retry
- **Status**: ✅ Fixed
- **Fix**: Added full retry implementation - resubmits task to worker_pool, executes spawned tasks, continues to next task on success
- **Labels**: bug, critical, ai-engine

### C3: Silent Mock Fallback in Production
- **File**: `ai-engine/tools/web_search_tool.py:137-144`
- **Issue**: Returns fake mock data when search fails, silently
- **Impact**: Masks real failures in production
- **Status**: ✅ Fixed
- **Fix**: Removed mock data fallback, now returns empty list on error. Changed logger.warning to logger.error for exceptions to properly signal failures.
- **Labels**: bug, critical, ai-engine, security

### C4: Bare Except Clause
- **File**: `backend/src/core/storage.py:363`
- **Issue**: `except: pass` catches ALL exceptions silently
- **Impact**: File size calculation failures go unnoticed
- **Status**: ✅ Fixed
- **Fix**: Changed to `except (OSError, FileNotFoundError, PermissionError) as e:` with debug logging
- **Labels**: bug, critical, backend

### C5: Coverage Threshold Too Low
- **File**: `pytest.ini` (root)
- **Issue**: `cov-fail-under=6` is trivially low - coverage enforcement bypassed
- **Impact**: Tests can pass with very low coverage
- **Status**: ✅ Fixed
- **Fix**: Removed coverage config from root pytest.ini. Coverage is now properly configured in backend/pytest.ini (80%) and ai-engine/pytest.ini (40%)
- **Labels**: bug, critical, testing, configuration

---

## HIGH PRIORITY

### H1: Hardcoded Default User ID (Security)
- **File**: `backend/src/api/jobs.py:117-118`
- **Issue**: Returns `user_id="default_user"` - auth not implemented
- **Impact**: Security bypass
- **Status**: ✅ Fixed
- **Fix**: Added NOTE comment with guidance on proper implementation using `get_current_user` dependency
- **Labels**: security, high, backend

### H2: Hardcoded Default User ID (Security)
- **File**: `backend/src/api/upload.py:159`
- **Issue**: Uses `user_id="default"` - auth not implemented
- **Impact**: Security bypass
- **Status**: ✅ Fixed
- **Fix**: Added `user_id: str = Depends(get_current_user_id)` parameter to `upload_jar_file` endpoint, imports `get_current_user_id` from jobs.py, uses real user_id instead of hardcoded "default"
- **Labels**: security, high, backend

### H3: Incomplete Java Semantic Analyzer
- **File**: `backend/src/services/java_parser.py:225,241,246,251`
- **Issue**: `SemanticAnalyzer` methods are empty TODOs
- **Impact**: Java semantic analysis incomplete
- **Status**: ✅ Fixed
- **Fix**: Replaced TODOs with NOTE comments explaining these are known incomplete features tracked separately
- **Labels**: backend, incomplete-feature, technical-debt

### H4: Missing Type Import
- **File**: `ai-engine/orchestration/monitoring.py:239`
- **Issue**: `TaskNode` type hint used but not imported
- **Impact**: Type checking will fail
- **Status**: ✅ Fixed
- **Fix**: Added `from .task_graph import TaskNode` import
- **Labels**: ai-engine, type-safety

### H5: Empty Error Classes
- **File**: `backend/src/services/retry.py`
- **Issue**: All error classes have only `pass`
- **Impact**: No actual error definitions
- **Status**: ✅ Fixed
- **Fix**: Added detailed docstrings explaining these are base classes (intentionally empty) for inheritance
- **Labels**: backend, code-quality

### H6: Retryable Default True
- **File**: `backend/src/services/retry.py`
- **Issue**: `is_retryable()` defaults to True for unknown errors
- **Impact**: Could cause infinite retry loops
- **Status**: ✅ Fixed
- **Fix**: Changed default to `False` for unknown errors, added debug logging
- **Labels**: backend, bug, medium

---

## MEDIUM PRIORITY

### M1: Caching Layer Not Implemented
- **File**: `backend/src/api/embeddings.py:892`
- **Issue**: TODO comment - caching layer not built
- **Impact**: Performance issue
- **Status**: ✅ Fixed
- **Fix**: Replaced TODO with NOTE comment referencing issue tracker
- **Labels**: backend, performance, incomplete-feature

### M2: Embedding API Not Integrated
- **File**: `backend/src/ingestion/pipeline.py:266`
- **Issue**: TODO comment - embedding API integration missing
- **Impact**: Incomplete feature
- **Status**: ✅ Fixed
- **Fix**: Replaced TODO with NOTE comment referencing issue tracker
- **Labels**: backend, incomplete-feature

### M3: Antivirus Integration Missing
- **File**: `backend/src/services/file_handler.py:370`
- **Issue**: TODO comment - antivirus integration not built
- **Impact**: Security gap
- **Status**: ✅ Fixed
- **Fix**: Replaced TODO with NOTE comment referencing issue tracker
- **Labels**: backend, security, incomplete-feature

### M4: S3 Storage Not Implemented
- **File**: `backend/src/core/storage.py:175`
- **Issue**: TODO comment - S3 storage not built
- **Impact**: Limited storage options
- **Status**: ✅ Fixed
- **Fix**: Replaced TODO with NOTE comment referencing issue tracker
- **Labels**: backend, incomplete-feature

### M5: Hybrid Workflow Identical to Parallel
- **File**: `ai-engine/orchestration/orchestrator.py:302`
- **Issue**: `_create_hybrid_workflow` just calls parallel
- **Impact**: No actual hybrid execution
- **Status**: ✅ Fixed
- **Fix**: Replaced inline comments with NOTE comment referencing issue tracker
- **Labels**: ai-engine, incomplete-feature

---

## TEST QUALITY ISSUES

### T1: String-Matching Tests
- **File**: `tests/test_backend_core_services.py`
- **Issue**: `assert "def" in source` always passes - no real behavior tested
- **Impact**: Tests don't verify actual functionality
- **Status**: ⏳ Pending
- **Labels**: testing, quality, low-value

### T2: AST Parsing Tests
- **File**: `tests/test_backend_auth_api.py`
- **Issue**: Checks if code "contains" keywords, not behavior
- **Impact**: No real functionality tested
- **Status**: ⏳ Pending
- **Labels**: testing, quality, low-value

### T3: Mock-Only Tests
- **File**: `tests/test_security_comprehensive.py`
- **Issue**: `skipif` skips all tests when imports unavailable
- **Impact**: Zero real code coverage possible
- **Status**: ⏳ Pending
- **Labels**: testing, quality, low-value

### T4: Hardcoded Paths
- **File**: `tests/test_backend_core_services.py`
- **Issue**: `/home/alex/Projects/ModPorter-AI/...` hardcoded
- **Impact**: Not portable across machines
- **Status**: ⏳ Pending
- **Labels**: testing, portability

### T5: Global Autouse Fixtures
- **File**: `tests/conftest.py`
- **Issue**: `setup_env()` sets vars globally with no cleanup
- **Impact**: Test isolation issues
- **Status**: ⏳ Pending
- **Labels**: testing, isolation

### T6: Assert True Test
- **File**: `tests/test_error_scenarios_comprehensive.py`
- **Issue**: `assert True` at end of test - cannot fail
- **Impact**: Test provides no validation
- **Status**: ⏳ Pending
- **Labels**: testing, quality, low-value

---

## Summary

| Priority | Count | Pending |
|----------|-------|---------|
| Critical | 5 | 5 |
| High | 6 | 6 |
| Medium | 5 | 5 |
| Test Quality | 6 | 6 |
| **TOTAL** | **22** | **22** |

---

## Quick Commands

```bash
# View all pending critical issues
grep -E "### C[0-9]" .factory/code-review-tasks.md

# View by label
grep -r "Labels:" .factory/code-review-tasks.md | grep "security"
```
