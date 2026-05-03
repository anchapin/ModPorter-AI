# N+1 Query Detection

## Overview

The N+1 Query Detection module monitors database queries to identify performance anti-patterns where a single query is executed multiple times in a loop with different parameters, resulting in unnecessary database round trips.

### The N+1 Problem

```python
# BAD: N+1 Problem
users = session.query(User).all()  # 1 query
for user in users:
    addons = session.query(Addon).filter(Addon.user_id == user.id).all()  # N queries
    # Total: 1 + N queries

# GOOD: Eager Loading
users = session.query(User).options(
    selectinload(User.addons)
).all()
# Total: 2 queries (or 1 with JOIN)
```

## Features

### 1. Automatic Query Monitoring
- Tracks all SQL queries executed through SQLAlchemy
- Records execution time and parameters
- Normalizes queries to group similar patterns

### 2. Pattern Detection
- Identifies queries executed multiple times with different parameters
- Configurable threshold (default: 5 executions)
- Tracks unique parameter sets

### 3. Performance Reporting
- Slowest queries (by total execution time)
- Most frequently executed queries
- Detected N+1 candidates with metrics
- Comprehensive JSON report

### 4. Context Tracking
- Track queries within specific operations
- Nested operation support
- Query count per operation
- Automatic warnings for high-count operations

## Installation

### 1. Add Query Monitoring to Database Setup

```python
# backend/src/db/base.py
from db.query_monitor import setup_query_monitoring

# After creating async_engine
setup_query_monitoring(async_engine, enabled=True)
```

### 2. Add Middleware/Event Hooks

```python
# backend/src/main.py
from db.query_monitor import setup_query_monitoring

@app.on_event("startup")
async def startup():
    setup_query_monitoring(get_db_engine(), enabled=True)
```

## Usage

### Basic Monitoring

Once enabled, the monitor automatically tracks all queries:

```python
from db.query_monitor import get_query_report

# Anywhere in your code
report = get_query_report()
print(report)
```

### Context Tracking

Track queries within a specific operation:

```python
from db.query_monitor import track_query_context

with track_query_context("load_users_with_addons", warn_threshold=5):
    users = await session.execute(
        select(User).options(selectinload(User.addons))
    )
    # All queries within this block are tracked
    # Warning if > 5 queries executed
```

### Function Decorator

```python
from db.query_monitor import track_queries

@track_queries(warn_threshold=10)
async def bulk_import_data(session: AsyncSession):
    # Automatically tracked, warns if > 10 queries
    for row in data:
        await session.execute(...)
```

## Report Format

```python
{
    "summary": {
        "total_unique_queries": 15,
        "total_executions": 247,
        "total_time_seconds": 3.45,
        "n_plus_one_issues": 2
    },
    "n_plus_one_candidates": [
        {
            "query": "SELECT * FROM addons WHERE user_id = ?",
            "execution_count": 1000,
            "total_time": 2.34,
            "avg_time": 0.00234
        }
    ],
    "slowest_queries": [
        {
            "query": "SELECT * FROM conversions WHERE ...",
            "execution_count": 5,
            "total_time": 1.23,
            "avg_time": 0.246,
            "min_time": 0.23,
            "max_time": 0.27
        }
    ],
    "most_executed_queries": [
        {
            "query": "SELECT * FROM users WHERE id = ?",
            "execution_count": 500,
            "total_time": 0.5,
            "avg_time": 0.001
        }
    ]
}
```

## API Reference

### QueryMonitor

```python
class QueryMonitor:
    def __init__(self, enabled: bool = True, threshold: int = 5)
    def record_query(self, sql: str, execution_time: float, params: Optional[Tuple] = None)
    def get_n_plus_one_candidates(self) -> List[Tuple[str, QueryMetrics]]
    def get_slowest_queries(self, limit: int = 10) -> List[Tuple[str, QueryMetrics]]
    def get_most_executed_queries(self, limit: int = 10) -> List[Tuple[str, QueryMetrics]]
    def get_report(self) -> Dict
    def reset(self)
    def enable_monitoring(self)
    def disable_monitoring(self)
```

### Context Functions

```python
# Track a block of code
with track_query_context("operation_name", warn_threshold=10):
    # Code here

# Track a function
@track_queries(warn_threshold=5)
async def my_function():
    pass

# Get report and reset
report = get_query_report()
reset_query_monitor()
```

## Query Normalization

The monitor normalizes queries to group similar patterns:

**Examples:**

```
SELECT * FROM users WHERE id = 123
SELECT * FROM users WHERE id = 456
→ SELECT * FROM users WHERE id = ?

SELECT * FROM users WHERE name = 'Alice'
SELECT * FROM users WHERE name = 'Bob'
→ SELECT * FROM users WHERE name = ?

SELECT * FROM users WHERE id = '550e8400-e29b-41d4-a716-446655440000'
→ SELECT * FROM users WHERE id = ?
```

## Performance Impact

- **Minimal overhead**: ~1-2% performance impact when enabled
- **Thread-safe**: Uses locks for concurrent access
- **Memory efficient**: Stores only aggregated metrics
- **Configurable**: Can be disabled in production if needed

## Best Practices

### 1. Use Eager Loading to Prevent N+1

```python
# Bad
user = session.query(User).filter(User.id == 1).first()
addons = user.addons  # N+1 issue

# Good
user = session.query(User).options(
    selectinload(User.addons)
).filter(User.id == 1).first()
addons = user.addons  # No N+1
```

### 2. Use Context Tracking for Critical Operations

```python
@track_queries(warn_threshold=20)
async def process_bulk_conversion(session: AsyncSession):
    # Warnings if this operation executes > 20 queries
    ...
```

### 3. Monitor Reports Periodically

```python
# In your logging/monitoring system
report = get_query_report()
logger.info(f"N+1 Issues: {report['summary']['n_plus_one_issues']}")

# Reset after analyzing
reset_query_monitor()
```

### 4. Review Slow Queries

```python
report = get_query_report()
for query, metrics in report['slowest_queries']:
    if metrics['total_time'] > 1.0:  # Queries taking > 1 second
        logger.warning(f"Slow query: {query}")
```

## Testing

```python
import pytest
from db.query_monitor import reset_query_monitor, get_query_report

@pytest.fixture
def reset_monitor():
    reset_query_monitor()
    yield
    reset_query_monitor()

def test_n_plus_one_detection(reset_monitor):
    from db.query_monitor import _query_monitor
    
    # Simulate N+1 queries
    for i in range(6):
        _query_monitor.record_query(
            "SELECT * FROM addons WHERE user_id = ?",
            0.01,
            (i,)
        )
    
    report = get_query_report()
    assert report["summary"]["n_plus_one_issues"] >= 1
```

## Troubleshooting

### Monitor Not Recording Queries

1. Ensure `setup_query_monitoring()` was called with the engine
2. Check that `enabled=True` is passed
3. Verify queries are executed after setup

### False Positives for N+1

- Some legitimate patterns may appear as N+1 if:
  - Different parameter sets are used intentionally
  - Batch operations use the same query template
- Use `warn_threshold` to adjust sensitivity

### High Memory Usage

- Call `reset_query_monitor()` periodically in long-running processes
- Disable monitoring during high-traffic periods if needed

## Integration with CI/CD

```bash
# Run tests with query monitoring enabled
pytest --enable-query-monitoring

# Check for N+1 issues in test results
pytest --enable-query-monitoring --fail-on-n-plus-one
```

## Future Enhancements

- [ ] Database-specific optimizations
- [ ] Automatic suggestion of eager loading fixes
- [ ] Integration with APM tools (DataDog, New Relic)
- [ ] Query plan analysis and EXPLAIN ANALYZE integration
- [ ] Prometheus metrics export
- [ ] Dashboard visualization
