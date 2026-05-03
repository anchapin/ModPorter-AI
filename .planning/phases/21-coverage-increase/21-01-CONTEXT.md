# Phase 21: Coverage Optimization Context

## Vision
The goal of this phase is to increase the overall test coverage of portkit from approximately 57% to over 80%. This involves adding tests for approximately 19,000 lines of code, focusing on high-impact, low-coverage areas in both the `backend` and `ai-engine` services.

## Scope
- **Target services**: `backend/src` and `ai-engine/`
- **Goal**: >80% coverage in each targeted module.
- **Priority**: High-impact logic files, core agents, and predictive services.
- **Types of tests**:
  - **Unit tests**: For pure logic, data transformations, and utility functions.
  - **Integration tests**: For agent interactions, database operations, and API endpoints.
  - **Mocking**: Use `unittest.mock` or `pytest-mock` to isolate components, especially external LLM calls and third-party APIs.

## Decisions
- **D-01: Framework**: Use `pytest` for all new Python tests (standard for the project).
- **D-02: Strategy**: Focus on "fat" files first (highest number of missing lines) as they provide the best ROI for coverage.
- **D-03: Quality**: Coverage is the metric, but *meaningful* tests are the requirement. Avoid "coverage-only" tests that don't assert behavior.
- **D-04: Mocking**: All LLM calls (OpenAI, Ollama, etc.) MUST be mocked to ensure tests are fast, deterministic, and cost-effective.
- **D-05: Parallelization**: Plans are structured to allow parallel execution where possible (e.g., ai-engine tests and backend tests in separate plans).

## Success Criteria
- [ ] Overall coverage reaches 80% as reported by `coverage.py`.
- [ ] No regression in existing functionality.
- [ ] Test execution time remains under 10 minutes for the full suite.
- [ ] All new tests pass in CI/CD.
