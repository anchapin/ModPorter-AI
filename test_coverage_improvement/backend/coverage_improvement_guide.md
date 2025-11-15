# Backend Test Coverage Improvement Guide

This guide provides a comprehensive approach to improving test coverage for the ModPorter AI backend service. It addresses the current issues and provides a structured plan for increasing coverage effectively.

## Current Issues and Solutions

### 1. Dependency Issues

#### Problem
Missing dependencies like `redis.asyncio` and `sklearn.ensemble` are preventing tests from running.

#### Solution
We've created comprehensive mock implementations in `backend/tests/mocks/`:
- `redis_mock.py` - Complete mock Redis implementation
- `sklearn_mock.py` - Mock scikit-learn components
- `__init__.py` - Centralized mock initialization

#### Usage
```python
# In your test files, import the mocks first:
from tests.mocks import setup_test_environment
setup_test_environment()

# Now you can safely import modules that depend on these libraries
```

### 2. Import Conflicts

#### Problem
Conftest.py conflicts between backend and ai-engine test suites.

#### Solution
Use the updated conftest in `backend/tests/conftest_updated.py` which:
- Properly isolates the backend test environment
- Applies all necessary mocks before imports
- Provides clean fixtures for database and test clients

### 3. Syntax Errors

#### Problem
Unterminated string literals in test files.

#### Solution
- Run syntax checks before committing tests
- Use linters and IDE integration to catch errors early
- Implement pre-commit hooks for syntax validation

## Strategic Approach to Improving Coverage

### 1. Focus on Critical Paths

Prioritize testing for:
- API endpoints (request/response validation, error handling)
- Business logic in service classes
- Database operations and transactions
- Integration between components
- Error scenarios and edge cases

### 2. Test Structure Organization

```
backend/tests/
├── unit/                    # Isolated unit tests
│   ├── models/             # Test database models
│   ├── services/           # Test business logic
│   └── api/                # Test API endpoints
├── integration/             # Component integration tests
├── e2e/                    # End-to-end scenarios
├── fixtures/                # Test data and utilities
└── mocks/                   # Mock implementations
```

### 3. Testing Patterns

#### Service Layer Testing
```python
class TestCacheService:
    @pytest.fixture
    def service(self, mock_redis_client):
        with patch('services.cache.aioredis.from_url', return_value=mock_redis_client):
            return CacheService()
    
    @pytest.mark.asyncio
    async def test_set_job_status(self, service):
        job_id = "test-job-123"
        status = {"progress": 50, "status": "processing"}
        
        await service.set_job_status(job_id, status)
        
        # Verify the key was set in Redis
        expected_key = f"conversion_jobs:{job_id}:status"
        cached_data = await service._client.get(expected_key)
        assert json.loads(cached_data) == status
```

#### API Endpoint Testing
```python
class TestConversionAPI:
    def test_create_conversion_job(self, client):
        response = client.post(
            "/api/v1/conversions",
            json={"mod_name": "test_mod", "mod_version": "1.0.0"}
        )
        assert response.status_code == 201
        assert "id" in response.json()
    
    def test_create_conversion_job_invalid_data(self, client):
        response = client.post(
            "/api/v1/conversions",
            json={"mod_name": ""}  # Invalid empty name
        )
        assert response.status_code == 422
```

## Specific Service Coverage Plans

### 1. Conversion Service

#### Key Areas to Test
- Job creation and status tracking
- File upload and validation
- Progress reporting
- Error handling and recovery

#### Recommended Tests
```python
# test_conversion_service.py
@pytest.mark.asyncio
async def test_create_conversion_job(db_session, mock_file_storage):
    service = ConversionService(db_session, file_storage=mock_file_storage)
    job_id = await service.create_conversion_job(
        mod_name="test_mod",
        mod_file=BytesIO(b"test content"),
        user_id="test-user"
    )
    assert job_id is not None
    
    # Verify job was created in database
    job = await service.get_conversion_job(job_id)
    assert job.status == "pending"

@pytest.mark.asyncio
async def test_update_job_progress(db_session):
    service = ConversionService(db_session)
    job_id = "test-job-123"
    
    await service.update_job_progress(job_id, 50)
    job = await service.get_conversion_job(job_id)
    assert job.progress == 50
```

### 2. Asset Conversion Service

#### Key Areas to Test
- Texture conversion (PNG to Bedrock format)
- Model conversion (JSON to Bedrock format)
- Sound conversion (OGG to Bedrock format)
- Error handling for unsupported formats

### 3. Knowledge Graph Service

#### Key Areas to Test
- Node creation and updates
- Relationship management
- Graph traversal queries
- Visualization data generation

## Implementation Steps

### Week 1: Fix Foundation Issues
1. [ ] Apply mocks to resolve dependency issues
2. [ ] Fix all syntax and import errors
3. [ ] Establish baseline coverage report
4. [ ] Set up CI integration for coverage tracking

### Week 2: Core Services
1. [ ] Implement comprehensive tests for conversion service
2. [ ] Add tests for asset conversion service
3. [ ] Test caching layer thoroughly
4. [ ] Verify database model operations

### Week 3: API Layer
1. [ ] Test all REST endpoints
2. [ ] Verify request/response validation
3. [ ] Test error scenarios
4. [ ] Add authentication/authorization tests

### Week 4: Advanced Features
1. [ ] Test knowledge graph functionality
2. [ ] Implement experiment service tests
3. [ ] Add performance monitoring tests
4. [ ] Test WebSocket connections

## Coverage Goals

By the end of this improvement plan, aim for:

- Overall code coverage: **85%**
- API endpoint coverage: **90%**
- Service layer coverage: **85%**
- Database model coverage: **90%**
- Critical paths coverage: **95%**

## Testing Tools and Configuration

### Pytest Configuration
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --cov=src
    --cov-report=term-missing
    --cov-report=html
    --cov-fail-under=80
```

### Coverage Configuration
```ini
[run]
source = src
omit = 
    */tests/*
    */test_*
    */__pycache__/*
    */venv/*
    */env/*
    */migrations/*
    */alembic/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    class .*\bProtocol\):
    @(abc\.)?abstractmethod
```

## Best Practices

1. **Test Isolation**: Ensure tests don't depend on each other
2. **Descriptive Naming**: Use clear test names that describe what is being tested
3. **Arrange-Act-Assert**: Structure tests with clear setup, execution, and verification phases
4. **Mock External Dependencies**: Use mocks for external services to make tests fast and reliable
5. **Test Edge Cases**: Don't just test happy paths; verify error handling
6. **Maintain Test Data**: Keep test data simple and focused on the test scenario

## Running the Tests

### Run All Backend Tests
```bash
cd backend
python -m pytest tests --cov=src --cov-report=html
```

### Run Specific Service Tests
```bash
cd backend
python -m pytest tests/unit/services/test_cache_service.py --cov=src.services.cache
```

### Run Tests with Coverage Threshold
```bash
cd backend
python -m pytest tests --cov=src --cov-fail-under=80
```

## Continuous Integration

Implement coverage reporting in CI to:
1. Prevent coverage regressions
2. Track coverage improvements over time
3. Identify areas that need more testing
4. Generate coverage reports for review

## Conclusion

Improving test coverage is an incremental process that requires consistent effort. By following this structured approach and focusing on critical paths first, we can significantly increase the reliability and maintainability of the ModPorter AI backend service.

The mock implementations and test patterns provided in this guide will help overcome the current dependency issues and establish a solid foundation for comprehensive testing.