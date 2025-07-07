# AGENTS.md - ModPorter AI Development Guide

## Build/Test Commands
- `npm run dev` - Start all services (frontend:3000, backend:8000)
- `npm run test` - Run all tests (frontend + backend)
- `cd frontend && npm test -- ConversionUpload.test.tsx` - Single frontend test
- `cd backend && source .venv/bin/activate && python -m pytest tests/test_main.py::test_specific_function` - Single backend test
- `npm run lint` - Lint all services (ESLint + Ruff)
- `npm run format` - Format code (Prettier + Black)

## Code Style
- **Frontend**: TypeScript + React, Prettier (2 spaces, single quotes), ESLint strict mode
- **Backend**: Python + FastAPI, Black formatter, Ruff linter, type hints required
- **Imports**: Absolute imports preferred, group by: stdlib, third-party, local
- **Naming**: camelCase (TS), snake_case (Python), PascalCase (components/classes)
- **Types**: Strict TypeScript, Pydantic models for API, interface definitions required
- **Error Handling**: Try-catch with specific error types, HTTP status codes, user-friendly messages
- **Testing**: Vitest (frontend), pytest with async support (backend), 80% coverage minimum
- **Comments**: JSDoc for public APIs, docstrings for Python functions, PRD feature references
- **Files**: Component folders with .tsx/.stories.tsx/.test.tsx, Python modules with __init__.py

## Architecture Notes
Multi-service app: React frontend, FastAPI backend, CrewAI engine. Follow existing patterns in components/ and services/.