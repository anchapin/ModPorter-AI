# Technical Debt Report
Generated: 2026-03-29T20:51:29.882902
## Summary
- **Total Items**: 3
- **By Severity**:
  - Critical: 1
  - High: 1
  - Low: 1
- **By Category**:
  - Reliability: 1
  - Maintainability: 1
  - Other: 1

## Issues by GitHub Issue Number
### #456
- Count: 1
- Items:
  - DEBT(#456): Refactor this [DebtSeverity.LOW/DebtCategory.MAINTAINABILITY] @ src/file1.py:4
### #123
- Count: 2
- Items:
  - TODO(#123): Fix this bug [DebtSeverity.CRITICAL/DebtCategory.RELIABILITY] @ src/file1.py:2
  - FIXME(#123): Another bug [DebtSeverity.HIGH/DebtCategory.OTHER] @ src/file2.py:2

## Detailed View
### CRITICAL
#### TODO(#123)
- **Description**: Fix this bug
- **Location**: `src/file1.py:2`
- **Category**: reliability
- **Severity**: critical
- **GitHub Issue**: https://github.com/anchapin/portkit/issues/123
- **Context**:
```
    1: 
>>> 2: # TODO(#123): Fix this bug [critical/reliability]
    3: print("hello")
    4: # DEBT(#456): Refactor this [low/maintainability]
```
### HIGH
#### FIXME(#123)
- **Description**: Another bug
- **Location**: `src/file2.py:2`
- **Category**: other
- **Severity**: high
- **GitHub Issue**: https://github.com/anchapin/portkit/issues/123
- **Context**:
```
    1: 
>>> 2: # FIXME(#123): Another bug [high]
    3: # Just a comment
```
### LOW
#### DEBT(#456)
- **Description**: Refactor this
- **Location**: `src/file1.py:4`
- **Category**: maintainability
- **Severity**: low
- **GitHub Issue**: https://github.com/anchapin/portkit/issues/456
- **Context**:
```
    2: # TODO(#123): Fix this bug [critical/reliability]
    3: print("hello")
>>> 4: # DEBT(#456): Refactor this [low/maintainability]
```
