---
name: run-tests
description: Run PortKit's test suite — full, targeted, or by module
---

# Running PortKit Tests

## Full test suite
```bash
# ai-engine
cd /workspace/ai-engine && python -m pytest tests/ -v

# backend
cd /workspace/backend && python -m pytest tests/ -v

# frontend
cd /workspace/frontend && npm test -- --watchAll=false
```

## Run tests for a specific module
```bash
# Specific converter
cd /workspace/ai-engine && python -m pytest tests/converters/test_<name>_converter.py -v

# Specific backend route
cd /workspace/backend && python -m pytest tests/routes/test_<name>.py -v

# By keyword
cd /workspace/ai-engine && python -m pytest tests/ -k "brewing" -v
```

## Run with coverage
```bash
cd /workspace/ai-engine && python -m pytest tests/ --cov=. --cov-report=term-missing
cd /workspace/backend && python -m pytest tests/ --cov=. --cov-report=term-missing
```

## Key test directories
```
ai-engine/tests/
├── converters/         # One test file per converter
├── pipeline/           # End-to-end conversion pipeline tests
├── agents/             # CrewAI agent unit tests
└── integration/        # Full mod conversion integration tests

backend/tests/
├── routes/             # FastAPI endpoint tests (use TestClient)
├── tasks/              # Celery task unit tests
└── integration/        # DB + Redis integration tests
```

## Environment setup (if tests fail with import errors)
```bash
cd /workspace/ai-engine && pip install -e ".[dev]"
cd /workspace/backend && pip install -e ".[dev]"
```

## Known issues
- `javalang` tests may fail on Java 17 syntax — use tree-sitter based tests instead (#1096)
- Integration tests require Redis running locally: `docker run -p 6379:6379 redis:alpine`
- Set `TESTING=1` env var to skip Celery broker connections in unit tests
