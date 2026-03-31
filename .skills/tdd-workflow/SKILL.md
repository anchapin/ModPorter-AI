---
name: tdd-workflow
description: Test-Driven Development workflow for ModPorter-AI. Follows RED-GREEN-REFACTOR cycle with explicit task tracking.
version: 1.0.0
author: ModPorter-AI Team
---

# TDD Workflow for ModPorter-AI

Test-Driven Development following best-practice AI agent patterns.

## RED-GREEN-REFACTOR Cycle

```
┌─────────────────────────────────────────────────────────┐
│                    TDD Cycle                                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐           │
│   │   RED   │ → │  GREEN   │ →  │ REFACTOR │ → loop    │
│   └─────────┘    └─────────┘    └─────────┘           │
│                                                         │
│   Write      Make it       Improve                        │
│   failing   pass          code                          │
│   test                                                   │
└─────────────────────────────────────────────────────────┘
```

## Workflow Steps

### 1. READ Task State (MANDATORY)

```bash
cat .factory/tasks.md
```

### 2. CREATE Task (if not exists)

Add to `.factory/tasks.md`:
```markdown
## In Progress
- 🔄 TDD: Implement {feature_name}

## Pending
- ⏳ TDD: Write RED test for {feature}
- ⏳ TDD: Implement GREEN code for {feature}
- ⏳ TDD: REFACTOR code for {feature}
```

### 3. RED Phase - Write Failing Test

```python
# tests/unit/test_<feature>.py

class TestFeatureName:
    """RED: Write test BEFORE implementation."""
    
    async def test_<scenario>_<expected>(self):
        """Test that feature does X when Y."""
        # ARRANGE - Set up test data
        # ACT - Call the function
        # ASSERT - Verify expected behavior
        
        # Start with the SIMPLEST passing case
        # Then add edge cases
        assert result == expected
```

**Key Rules for RED:**
- Write test that describes WHAT you want, not HOW
- Test behavior, not implementation
- Include edge cases: empty, null, max values
- Use descriptive names: `test_user_create_duplicate_email_raises_error`

### 4. GREEN Phase - Make Test Pass

**Rule:** Write MINIMUM code to make test pass. No optimization yet.

```python
# Implementation - Keep it SIMPLE
async def process_feature(input_data: InputModel) -> OutputModel:
    # Direct implementation, no over-engineering
    return OutputModel(result=input_data.value)
```

**Anti-patterns in GREEN:**
```
❌ Don't add logging yet
❌ Don't add validation yet (unless test requires it)
❌ Don't optimize - just make it work
❌ Don't add features not tested
```

### 5. REFACTOR Phase - Improve Code

Now that tests exist, you CAN:
- Add logging
- Add validation
- Optimize
- Simplify

```python
async def process_feature(input_data: InputModel) -> OutputModel:
    # Now add proper error handling
    if not input_data.value:
        raise ValueError("Value cannot be empty")
    
    # Add logging
    logger.info(f"Processing feature: {input_data.value}")
    
    # Return result
    return OutputModel(result=input_data.value)
}
```

## Test Structure

### Required Test File Header

```python
"""
Unit tests for {module_name}.

Tests follow TDD RED-GREEN-REFACTOR cycle.
See: .skills/tdd-workflow/SKILL.md
"""
import pytest
from src.services.example import ExampleService


class TestExampleService:
    """Tests for ExampleService."""
    
    @pytest.fixture
    def service(self):
        """Service instance with mocked dependencies."""
        return ExampleService()
```

### Test Naming Convention

```
test_<feature>_<scenario>_<expected>

Examples:
- test_user_create_success_returns_user
- test_user_create_duplicate_email_raises_conflict
- test_user_get_by_id_not_found_returns_none
- test_conversion_job_timeout_triggers_retry
```

### Mock Patterns

```python
# ✅ CORRECT - Mock at dependency boundary
@pytest.fixture
def mock_db():
    with patch("src.services.user_service.get_db") as mock:
        yield mock

# ❌ WRONG - Mock implementation internals
@pytest.fixture  
def mock_user():
    with patch("src.models.user.User.name", "test"):
        yield mock_user
```

## Running Tests

```bash
# Run tests for a module (TDD loop)
cd backend && python3 -m pytest src/tests/unit/test_<module>.py -v

# Run single test
cd backend && python3 -m pytest src/tests/unit/test_<module>.py::TestClass::test_name -v

# Run with coverage
cd backend && python3 -m pytest src/tests/unit/test_<module>.py --cov=src.services.<module>

# Run all unit tests (before commit)
cd backend && python3 -m pytest src/tests/unit/ -q --tb=no
```

## Validation Checklist

Before marking task complete:
- [ ] All tests in RED (failing before implementation)
- [ ] All tests pass in GREEN (no skipping)
- [ ] Tests pass in REFACTOR
- [ ] Coverage maintained (--cov-fail-under=80)
- [ ] No new lint errors
- [ ] Task marked complete in .factory/tasks.md

## Anti-Patterns

```
❌ Write implementation BEFORE tests (Test-After)
❌ Skip tests to "save time"
❌ Test implementation details (brittle tests)
❌ Mock everything (integration test for complex flows)
❌ Single massive test (split into focused tests)
```

## File Changes

When implementing with TDD:

**Create:**
- `src/tests/unit/test_<feature>.py` - Tests
- `src/services/<feature>.py` - Implementation

**Modify:**
- `src/services/__init__.py` - Export new service
- `src/api/<feature>.py` - API endpoints (after tests pass)
- `.factory/tasks.md` - Update task status
