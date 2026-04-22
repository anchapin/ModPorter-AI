# portkit Codebase Improvement Opportunities

## Summary by Category

| Category | Count |
|----------|-------|
| Security | 4 |
| Reliability | 5 |
| Maintainability | 4 |
| Performance | 2 |
| **Total** | **15** |

---

## Security (4 issues)

### 1. Authentication Stub Returns Hardcoded User ID
- **Files:** `backend/src/api/jobs.py:122`
- **Description:** `get_current_user_id()` returns hardcoded `"default_user"` instead of extracting from auth context. Comment says "TODO: Implement proper auth" but this is called across multiple endpoints.
- **Impact:** All job/convert endpoints that rely on `get_current_user_id` operate as a single shared user. No user isolation, no audit trail per user, access control bypass.
- **Suggested Fix:** Complete auth implementation using `Depends(get_current_user)` from `api.auth`, return actual `user.id`.
- **Priority:** Critical

### 2. Mock Data Fallback Silences Real Failures
- **Files:** `ai-engine/tools/web_search_tool.py:129-141`
- **Description:** When DuckDuckGo search fails, code returns `[]` and logs a warning, but the caller may interpret this as valid empty results rather than a service failure. The comment "Do NOT return mock data" is good but the empty list still masks failures.
- **Impact:** AI conversion may proceed with incomplete context, producing incorrect bedrock addons without any error indication to the user.
- **Suggested Fix:** Return an explicit error structure or raise an exception so callers can handle search failures explicitly rather than treating empty results as valid.
- **Priority:** High

### 3. Insecure Default Database URL in Config Comments
- **Files:** `backend/src/config.py:9-11`
- **Description:** Default database_url_raw contains credential placeholder in comment `postgresql://supabase_user:***@db.supabase_project_id.supabase.co:5432/postgres`. If this default ever activates due to config loading failure, the system connects to a real Supabase instance.
- **Impact:** Potential unauthorized database access if env vars misconfigured in production.
- **Suggested Fix:** Use a clearly invalid default like `"postgresql://INVALID_CONFIG"` that cannot connect to any real database.
- **Priority:** High

### 4. S3 Storage Falls Back Silently Without User Notification
- **Files:** `backend/src/core/storage.py:171-179`
- **Description:** When `STORAGE_BACKEND=s3` is set, the `_save_s3` and `_get_s3` methods just log a warning and fall back to local storage. No indication to caller that their data is NOT in S3.
- **Impact:** Users expecting S3 durability/availability may have data stored locally only, with no visibility into this misconfiguration.
- **Suggested Fix:** Either implement S3 properly or raise `NotImplementedError` when S3 backend is selected, forcing explicit configuration.
- **Priority:** Medium

---

## Reliability (5 issues)

### 5. Overly Broad Exception Catching Throughout Backend
- **Files:** `backend/src/websocket/enhanced_manager.py:558, 564, 595` + 40+ locations in ai-engine
- **Description:** Pattern of `except Exception:` that catches all exceptions including `asyncio.CancelledError`, `KeyboardInterrupt`, `ValueError`, `TypeError`, etc. Some instances silently pass without logging.
- **Impact:** Cancelled tasks appear to succeed. Invalid state transitions are swallowed. Errors in background loops don't surface. Debugging production issues becomes extremely difficult.
- **Suggested Fix:** Catch specific exceptions. Always log errors with context. Never silently `pass` in exception blocks without explanation.
- **Priority:** High

### 6. Retry Logic Blocks Event Loop
- **Files:** `ai-engine/orchestration/orchestrator.py:480-481`
- **Description:** `retry_future.result(timeout=self.current_config.task_timeout)` is a blocking call inside async code. This blocks the entire event loop during the retry wait.
- **Impact:** While one task retries, no other concurrent tasks can make progress. Severely degrades async concurrency benefits.
- **Suggested Fix:** Use `asyncio.wrap_future()` to convert the concurrent.futures.Future to an asyncio.Future, then `await` it with proper cancellation support.
- **Priority:** High

### 7. File Handles Not Always Closed with Context Manager
- **Files:** `backend/src/file_processor.py:557`
- **Description:** `open(potential_manifest_path, "r").read()` opens a file without a context manager. If read() fails or is interrupted, the fd leaks.
- **Impact:** File descriptor exhaustion on high-load or error-prone paths. fd leaks in long-running workers.
- **Suggested Fix:** Use `with open(...) as f: return f.read()` pattern.
- **Priority:** Medium

### 8. No Async Session Commit Pattern Consistency
- **Files:** `backend/src/db/base.py` + various API endpoints
- **Description:** Some endpoints use `session.commit()` explicitly after operations, others rely on `expire_on_commit=False` with automatic behavior. Inconsistency in how transactions are handled across the codebase.
- **Impact:** Some operations may not persist properly if they rely on implicit commit behavior. Race conditions possible on concurrent access.
- **Suggested Fix:** Standardize on explicit commit patterns with proper error rollback. Add a database utility decorator or base method for transactional operations.
- **Priority:** Medium

### 9. Incomplete Stub Functionality
- **Files:** `backend/src/api/jobs.py:122`
- **Description:** Stub `get_current_user_id()` has a comment saying it should use `get_current_user` but instead returns a hardcoded string. Multiple endpoints depend on it.
- **Impact:** Same as issue #1 but affects the jobs subsystem specifically. Jobs created by anyone are attributed to "default_user".
- **Suggested Fix:** Implement or remove the stub. Don't leave security-critical code paths as stubs.
- **Priority:** Critical

---

## Maintainability (4 issues)

### 10. Central Exception Handler Framework Underutilized
- **Files:** `backend/src/services/error_handler.py`
- **Description:** Well-designed centralized error handling framework exists with `ConversionError`, `retry_with_backoff`, `categorize_error`, but most of the codebase uses raw `except Exception:` directly in endpoints rather than this framework.
- **Impact:** Inconsistent error categorization. Retry logic not applied. Error statistics tracking not populated. User-facing error messages inconsistent.
- **Suggested Fix:** Integrate endpoints with `ErrorHandler` and custom exception types. Audit all bare `except Exception:` for replacement with specific error types.
- **Priority:** Medium

### 11. TODO References Without Issue Numbers
- **Files:** Multiple files reference `https://github.com/anchapin/portkit/issues/TODO`
- **Description:** References like `# See https://github.com/anchapin/portkit/issues/TODO for tracking` point to a literal TODO issue placeholder, not specific tracked issues.
- **Impact:** No way to follow up on these items. Dead links. Technical debt invisible in issue tracker.
- **Suggested Fix:** Replace all TODO references with specific issue numbers or create tracked issues for each placeholder.
- **Priority:** Medium

### 12. Extremely Large Modules
- **Files:** `backend/src/main.py` (1516 lines), `ai-engine/agents/asset_converter.py` (4300+ lines)
- **Description:** `main.py` contains app setup, lifespan, 20+ routers, conversion logic, and worker threads all in one file. `asset_converter.py` is similarly massive with 40+ similar error handling blocks.
- **Impact:** Cognitive overload for code review. Hard to navigate. Difficult to test in isolation. High coupling.
- **Suggested Fix:** Break into focused modules: separate routers into `api/v1/` directory, extract conversion workflow into dedicated module, split `asset_converter.py` by responsibility.
- **Priority:** Medium

### 13. Inconsistent Logging Levels and Formats
- **Files:** Throughout codebase
- **Description:** Mix of `logger.info`, `logger.warning`, `logger.error` without consistent policy. Some errors logged with `f"string"`, others with separate message formatting. No structured logging in many places despite `structured_logging.py` existing.
- **Impact:** Difficult to filter/search logs. Inconsistent alerting. Metrics aggregation challenging.
- **Suggested Fix:** Use structured logging (`structlog`) consistently. Establish log level policy. Audit all `logger.error` for whether they should be `logger.exception` to include stack traces.
- **Priority:** Medium

---

## Performance (2 issues)

### 14. Blocking Calls in Async Contexts
- **Files:** `backend/src/services/batch_queuing.py:718`, `backend/src/services/resource_allocator.py:917`
- **Description:** `asyncio.run(_batch_queue.close())` and `asyncio.run(_resource_allocator.close())` are called where an async event loop may already be running. This is not allowed and will raise an error.
- **Impact:** If these shutdown methods are called when an event loop is running (common in uvicorn/FastAPI), it will crash with "asyncio.run() cannot be called from a running event loop".
- **Suggested Fix:** Use `await queue.aclose()` if the queue supports it, or use `asyncio.get_event_loop().run_until_complete()` pattern for cleanup in existing loop context.
- **Priority:** High

### 15. Worker Pool Stuck Task Detection Dead Code
- **Files:** `ai-engine/orchestration/worker_pool.py:91` + task_start_times tracking
- **Description:** `_task_start_times` dict is populated but never actually checked for stuck tasks. The monitoring thread monitors queue size and worker stats but never compares task duration against timeout.
- **Impact:** Stuck tasks are never detected or recovered. Tasks that hang indefinitely will block the workflow forever.
- **Suggested Fix:** Implement actual stuck task detection: compare `time.time() - task_start_times[task_id]` against `task_timeout`, cancel and reschedule stuck tasks.
- **Priority:** High

---

## Total by Priority

| Priority | Count |
|----------|-------|
| Critical | 2 |
| High | 6 |
| Medium | 7 |
