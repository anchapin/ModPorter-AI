---
name: auto-code-review
description: Automated code review agent for PortKit. Use when reviewing PRs or code changes. Follows Pipeline pattern: Security → Quality → Performance → Patterns.
version: 1.0.0
author: PortKit Team
---

# Auto Code Review Agent

Automated code review following best-practice AI agent patterns.

## Review Pipeline

```
┌─────────────────────────────────────────────────────────┐
│              Code Review Pipeline                         │
├─────────────────────────────────────────────────────────┤
│  1. Security Scan (parallel)                            │
│     - Secrets detection (gitleaks patterns)              │
│     - SQL injection patterns                             │
│     - XSS patterns                                      │
│     - Insecure dependencies                             │
│                                                         │
│  2. Quality Check (parallel)                           │
│     - Type safety (mypy patterns)                       │
│     - Error handling completeness                       │
│     - Test coverage impact                              │
│                                                         │
│  3. Performance Review                                  │
│     - N+1 query patterns                                │
│     - Missing indexes                                   │
│     - Inefficient algorithms                             │
│                                                         │
│  4. Pattern Compliance                                  │
│     - CLAUDE.md conventions                             │
│     - Pythonic patterns                                 │
│     - API design patterns                               │
└─────────────────────────────────────────────────────────┘
```

## Input

```yaml
files: List of files to review
branch: Branch name
base_branch: Target branch (usually main)
commit_sha: Specific commit (optional)
```

## Output

```markdown
# Code Review: {BRANCH}

## Summary
{Number} files changed, {additions} additions, {deletions} deletions

## Security Issues
| Severity | File | Line | Issue | Fix |
|----------|------|------|-------|-----|

## Quality Issues  
| Severity | File | Line | Issue | Suggestion |

## Performance Concerns
| Impact | File | Line | Issue | Recommendation |

## Pattern Violations
| File | Expected | Found | Suggestion |

## Recommendations
1. {Priority action}
2. {Secondary action}

## Approval Status
- [ ] Security: PASS/FAIL
- [ ] Quality: PASS/FAIL
- [ ] Performance: PASS/FAIL
- [ ] Patterns: PASS/FAIL

**Overall: APPROVE / REQUEST_CHANGES / BLOCK**
```

## Review Checklist

### Security
- [ ] No hardcoded secrets/API keys
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities (user input sanitized)
- [ ] No path traversal vulnerabilities
- [ ] Dependencies are secure (no known CVEs)

### Quality
- [ ] Type hints on all public functions
- [ ] Pydantic models for all API inputs/outputs
- [ ] Async/await for all I/O operations
- [ ] Proper error handling (no bare except)
- [ ] Logging for errors and important events

### Performance
- [ ] No N+1 queries (use joinedload/selectinload)
- [ ] Pagination on list endpoints
- [ ] Connection pooling configured
- [ ] Indexes on frequently queried columns

### Patterns
- [ ] Follows CLAUDE.md conventions
- [ ] Uses dependency injection
- [ ] Proper separation of concerns (api/service/db)
- [ ] Tests follow naming: test_<feature>_<scenario>_<expected>

## Anti-Patterns to Flag

```
❌ time.sleep() → Use asyncio.sleep()
❌ requests.get() → Use httpx async
❌ dict.get() with default → Use pydantic validation
❌ global state → Use dependency injection
❌ string concatenation for SQL → Use parameterized queries
❌ print() for debugging → Use logging
```

## Usage

```bash
# Review a PR
/auto-code-review --pr=123

# Review specific files
/auto-code-review --files=src/api/users.py src/services/user_service.py

# Review and post comment
/auto-code-review --pr=123 --post-comment
```
