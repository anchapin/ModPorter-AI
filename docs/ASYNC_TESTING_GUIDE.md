# FastAPI + Async Database Testing Guide

## The Problem

FastAPI's `TestClient` runs synchronously but async database operations need an async context. This creates a compatibility issue where:

1. `TestClient` uses `requests` library internally (synchronous)
2. Async database operations require an event loop
3. The two don't work together seamlessly

## Common Error Patterns

```python
# This WILL FAIL with async database operations
from fastapi.testclient import TestClient

def test_endpoint():
    client = TestClient(app)
    response = client.post("/api/users", json={"name": "test"})
    # If the endpoint uses async database operations, this may hang or fail
```

## How Others Handle This Issue

### 1. **httpx.AsyncClient** (Recommended)
Most modern FastAPI projects use `httpx.AsyncClient` instead of `TestClient`:

```python
import httpx
import pytest
from httpx import ASGITransport

@pytest.mark.asyncio
async def test_endpoint():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/users", json={"name": "test"})
        assert response.status_code == 200
```

### 2. **pytest-asyncio** Configuration
Configure pytest to handle async tests properly:

```ini
# pytest.ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = session
asyncio_default_test_loop_scope = function
```

### 3. **Async Database Fixtures**
Create async database fixtures that work with the same event loop:

```python
@pytest.fixture
async def async_db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
    
    await engine.dispose()
```

## Our Solution

We've implemented a comprehensive solution in `backend/tests/async_test_client.py`:

### AsyncTestClient Class
```python
class AsyncTestClient:
    """Async test client that properly handles async database operations."""
    
    async def __aenter__(self):
        from httpx import ASGITransport
        transport = ASGITransport(app=self.app)
        self._client = httpx.AsyncClient(transport=transport, base_url=self.base_url)
        return self
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self._client.get(url, **kwargs)
```

### Usage Examples

#### Basic Async Test
```python
@pytest.mark.asyncio
async def test_health_endpoint(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200
```

#### Database Integration Test
```python
@pytest.mark.asyncio
async def test_create_user(async_client, async_test_db):
    response = await async_client.post("/api/users", json={"name": "test"})
    assert response.status_code == 201
    
    # Verify in database
    result = await async_test_db.execute(text("SELECT * FROM users WHERE name = 'test'"))
    user = result.fetchone()
    assert user is not None
```

## Best Practices

### 1. Use Async Fixtures
```python
@pytest.fixture
async def async_test_db():
    # Set up async database session
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    # ... setup code
    yield session
    await engine.dispose()
```

### 2. Proper Event Loop Management
```python
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

### 3. Environment Configuration
```python
@pytest.fixture(autouse=True)
def setup_test_env():
    os.environ["TESTING"] = "true"
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    yield
```

## Migration Strategy

### From TestClient to AsyncTestClient

**Before:**
```python
def test_endpoint():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
```

**After:**
```python
@pytest.mark.asyncio
async def test_endpoint(async_client):
    response = await async_client.get("/api/health")
    assert response.status_code == 200
```

### Handling Mixed Sync/Async Tests

You can still use `TestClient` for simple tests that don't use the database:

```python
def test_static_endpoint():
    """Simple test that doesn't use database - can use TestClient."""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_database_endpoint(async_client):
    """Database test - must use AsyncTestClient."""
    response = await async_client.post("/api/users", json={"name": "test"})
    assert response.status_code == 201
```

## Common Pitfalls

### 1. Event Loop Conflicts
**Problem:** Multiple event loops or loop conflicts
**Solution:** Use session-scoped event loop fixture

### 2. Database Connection Issues
**Problem:** Database connections not properly closed
**Solution:** Always use async context managers and dispose engines

### 3. Import Path Issues
**Problem:** Tests can't find modules
**Solution:** Proper `conftest.py` with path setup

## Testing the Solution

Run these commands to verify the async testing setup works:

```bash
# Test basic async functionality
pytest backend/tests/integration/test_async_example.py::test_database_operations_async -v

# Test async client
pytest backend/tests/integration/test_async_example.py::test_health_endpoint_async -v

# Test mixed sync/async
pytest backend/tests/integration/test_async_example.py::test_sync_compatibility -v
```

## References

- [FastAPI Testing Documentation](https://fastapi.tiangolo.com/tutorial/testing/)
- [httpx Async Client Documentation](https://www.python-httpx.org/async/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [SQLAlchemy Async Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)

## Summary

The key insight is that **FastAPI's TestClient is synchronous and doesn't work well with async database operations**. The solution is to:

1. Use `httpx.AsyncClient` with `ASGITransport` for async tests
2. Configure pytest properly for async testing
3. Create async fixtures for database operations
4. Use proper event loop management

This approach is now standard in the FastAPI community and provides reliable, fast tests that work with async database operations.
