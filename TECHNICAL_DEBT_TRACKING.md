# Technical Debt Tracking System

A comprehensive system for tracking, categorizing, and prioritizing technical debt across the ModPorter-AI codebase.

## Overview

Technical debt represents suboptimal code or architecture decisions that reduce code quality, maintainability, or performance. This tracking system provides:

- **Unified Convention**: Consistent markers in code for debt items
- **Categorization**: Classify debt by type (performance, reliability, security, etc.)
- **Severity Levels**: Prioritize from critical to low
- **GitHub Integration**: Link debt items to GitHub issues
- **Reporting**: Generate reports and summary statistics
- **CLI Tool**: Command-line interface for scanning and analysis

## Debt Marking Convention

Use comment markers in code to track technical debt. Each marker must include a GitHub issue number.

### Syntax

```
# TODO(#<issue-number>): <description>
# FIXME(#<issue-number>): <description>
# DEBT(#<issue-number>): <description>
```

### Optional Annotations

Add severity/category in square brackets:

```
# TODO(#687): Refactor authentication [critical/performance]
# FIXME(#695): Handle edge case [high/reliability]
# DEBT(#700): Replace legacy API [medium/refactoring]
```

### Examples

**Performance improvement:**
```python
# TODO(#691): Optimize query with database index [critical/performance]
def process_conversion(job_id: str):
    results = db.query(Conversion).filter_by(id=job_id).all()
    # Current: O(n) - should be O(1) with index
```

**Reliability issue:**
```python
# FIXME(#695): Handle network timeout gracefully [high/reliability]
try:
    response = requests.get(url, timeout=5)
except requests.Timeout:
    # TODO: Implement retry logic with exponential backoff
    logger.error("Request timeout")
```

**Code refactoring needed:**
```python
# DEBT(#700): Replace BedrockAPI with new SDK [medium/refactoring]
def create_addon(name: str):
    # Using deprecated API - migrate to new SDK v2
    old_api = BedrockAPI_v1(token)
    return old_api.create(name)
```

**Security hardening:**
```python
# FIXME(#702): Validate file upload before processing [critical/security]
def upload_mod(file):
    # BUG: No size check - vulnerable to DoS
    content = file.read()
```

**Test coverage:**
```python
# TODO(#703): Add unit tests for edge cases [high/testing]
def convert_dimensions(java_dim):
    # No tests for null/invalid dimensions
    return bedrock_converter.convert(java_dim)
```

## Severity Levels

| Level | Description | Action |
|-------|-------------|--------|
| **critical** | Blocks production use, security vulnerability, data loss risk | Fix immediately |
| **high** | Significant impact on performance, reliability, or security | Fix in current sprint |
| **medium** | Should be addressed soon, impacts maintainability | Plan for next sprint |
| **low** | Nice-to-have improvements, minor code cleanup | Backlog item |

## Categories

| Category | Description | Examples |
|----------|-------------|----------|
| **performance** | Speed, memory, CPU optimization | Query optimization, caching, algorithm improvements |
| **reliability** | Error handling, stability, resilience | Retry logic, timeout handling, fallbacks |
| **maintainability** | Code quality, readability, structure | Reduce complexity, extract methods, naming |
| **testing** | Test coverage, test quality | Add unit tests, improve assertions, E2E tests |
| **security** | Security vulnerabilities, hardening | Input validation, authentication, encryption |
| **refactoring** | Code structure improvements | Replace deprecated APIs, consolidate code |
| **documentation** | Missing or outdated documentation | Add docstrings, update README, API docs |
| **dependency** | Dependency updates, removal, conflicts | Update packages, remove unused deps |
| **other** | Miscellaneous improvements | Varies |

## CLI Usage

### Installation

```bash
cd backend
pip install -e .
```

### Commands

#### Scan for debt markers

```bash
# Scan current directory
python -m src.utils.debt_cli scan

# Scan specific directory
python -m src.utils.debt_cli scan --path /path/to/code

# Scan specific file pattern
python -m src.utils.debt_cli scan --pattern "**/*.py"

# Output as JSON
python -m src.utils.debt_cli scan --json
```

#### Generate report

```bash
# Generate markdown report to file
python -m src.utils.debt_cli report

# Specify output file
python -m src.utils.debt_cli report --output DEBT_REPORT.md
```

#### Show critical items only

```bash
python -m src.utils.debt_cli critical
```

#### Show items for specific issue

```bash
python -m src.utils.debt_cli issue 687
```

#### Show summary

```bash
python -m src.utils.debt_cli summary
```

## Python API

### Basic Usage

```python
from backend.src.utils.debt_tracker import DebtTracker, DebtSeverity

# Create tracker and scan
tracker = DebtTracker(root_path=".")
items = tracker.scan_directory(pattern="**/*.py")

# Get summary
summary = tracker.get_summary()
print(f"Total items: {summary['total']}")
print(f"Critical items: {summary['by_severity'].get('critical', 0)}")

# Get critical items
critical_items = tracker.get_critical_items()

# Filter by issue
issue_687_items = tracker.filter_by_issue(687)

# Export markdown report
tracker.export_markdown("DEBT_REPORT.md")
```

### Advanced Filtering

```python
from backend.src.utils.debt_tracker import DebtCategory

# Filter by category
perf_items = [
    item for item in tracker.debt_items
    if item.category == DebtCategory.PERFORMANCE
]

# Filter by severity and category
critical_security = [
    item for item in tracker.debt_items
    if item.severity == DebtSeverity.CRITICAL
    and item.category == DebtCategory.SECURITY
]
```

## Workflow Integration

### GitHub Issue Linking

Each debt marker includes a GitHub issue number. This enables:

1. **Bidirectional tracking**: Link code to issues and vice versa
2. **Prioritization**: Use GitHub issue labels for priority
3. **Automation**: Scripts can update issues based on scan results

Example GitHub issue label structure:
- `debt/critical` - Critical debt
- `debt/performance` - Performance-related debt
- `debt/security` - Security-related debt
- `debt/testing` - Testing-related debt

### CI/CD Integration

Integrate debt tracking into CI pipeline:

```yaml
# .github/workflows/tech-debt-check.yml
name: Technical Debt Check

on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - name: Scan for technical debt
        run: |
          python -m src.utils.debt_cli scan --json > debt-report.json
      - name: Check for new critical debt
        run: |
          # Fail if new critical items introduced
          python scripts/check_debt_growth.py debt-report.json
```

## Best Practices

### 1. Use Meaningful Descriptions

✅ **Good:**
```python
# TODO(#687): Implement connection pooling to reduce DB connection overhead [critical/performance]
```

❌ **Bad:**
```python
# TODO(#687): Fix this [critical]
```

### 2. Link to Open Issues

Always reference an open GitHub issue. If one doesn't exist, create it first:

✅ **Good:**
```python
# FIXME(#695): Handle network timeout with exponential backoff retry
```

❌ **Bad:**
```python
# FIXME: Handle network timeout
```

### 3. Include Severity and Category

Annotate markers with severity and category for better tracking:

✅ **Good:**
```python
# TODO(#687): Optimize authentication [critical/performance]
```

❌ **Bad:**
```python
# TODO(#687): Optimize authentication
```

### 4. Add Context

Place markers near the relevant code, not scattered:

✅ **Good:**
```python
def authenticate_user(username, password):
    # FIXME(#695): Input validation missing [high/security]
    # Vulnerable to SQL injection
    query = f"SELECT * FROM users WHERE name='{username}'"
    user = db.execute(query)
```

❌ **Bad:**
```python
# Debt item at top of file with no context

def authenticate_user(username, password):
    query = f"SELECT * FROM users WHERE name='{username}'"
    user = db.execute(query)
```

### 5. Maintain Consistency

Keep markers consistent across the codebase:

```python
# Python files
# TODO(#687): Description

# JavaScript/TypeScript files
// TODO(#687): Description

# Markdown files
<!-- TODO(#687): Description -->
```

## Reporting

### Generated Report Format

The `report` command generates a comprehensive markdown document with:

1. **Summary Section**
   - Total debt items
   - Distribution by severity
   - Distribution by category

2. **Issues Section**
   - Grouped by GitHub issue number
   - Item count per issue
   - All items for that issue

3. **Detailed Section**
   - Sorted by severity (critical → low)
   - Complete details for each item:
     - Description
     - Location (file:line)
     - Category
     - Severity
     - GitHub issue link
     - Code context

### Example Report

```markdown
# Technical Debt Report

Generated: 2025-03-10T14:30:00

## Summary

- **Total Items**: 42
- **By Severity**:
  - Critical: 3
  - High: 8
  - Medium: 18
  - Low: 13

## Issues by GitHub Issue Number

### #687
- Count: 5
- Items:
  - TODO(#687): Optimize authentication [critical/performance] @ backend/src/security/auth.py:145
  ...

## Detailed View

### CRITICAL
#### TODO(#687)
- **Description**: Optimize authentication for production scale
- **Location**: `backend/src/security/auth.py:145`
- **Category**: performance
- **Severity**: critical
- **GitHub Issue**: https://github.com/anchapin/modporter-ai/issues/687
- **Context**:
  ...
```

## Maintenance

### Regular Reviews

Schedule monthly reviews to:

1. **Verify Issue Status**: Check if linked issues are still open
2. **Update Priorities**: Adjust severity based on business needs
3. **Resolve Items**: Remove markers when issues are fixed
4. **Consolidate Duplicates**: Merge related debt items

### Cleanup

When an issue is resolved:

1. Remove the debt marker from code
2. Close the GitHub issue
3. Update the related PR/commit reference

## Troubleshooting

### Markers Not Detected

Ensure format matches exactly:
```python
# Pattern: # TODO(#<number>): <description> [optional tags]
# Correct
# TODO(#687): Description [critical/performance]

# Incorrect - no space after #
#TODO(#687): Description

# Incorrect - missing colon
# TODO(#687) Description
```

### JSON Output Not Working

Ensure all enum values are properly serialized:

```python
# In debt_tracker.py, asdict() handles conversion
import dataclasses
items = [dataclasses.asdict(item) for item in tracker.debt_items]
```

## Future Enhancements

Planned improvements:

1. **GitHub API Integration**: Auto-create/update issues based on scan
2. **Metrics Tracking**: Chart debt trends over time
3. **Team Metrics**: Per-team/per-module debt breakdown
4. **Notification System**: Alert team of critical debt growth
5. **Debt Budget**: Enforce maximum debt per sprint
6. **Auto-closure**: Close debt markers when linked issue closes

## See Also

- [TECHNICAL_CHALLENGES.md](./TECHNICAL_CHALLENGES.md) - Existing challenges documentation
- [GitHub Issues](https://github.com/anchapin/modporter-ai/issues) - Project backlog
- [Contributing Guide](./CONTRIBUTING.md) - Contribution guidelines

## References

- Issue: [#687 - Track technical debt](https://github.com/anchapin/modporter-ai/issues/687)
- Category: Enhancement
- Milestone: Readiness Pillar - Style & Validation
