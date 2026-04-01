# Architecture Decision Records (ADR)

This directory contains Architecture Decision Records for ModPorter-AI.

## Index

| Number | Title | Status | Date |
|--------|-------|--------|------|
| [0001](0001-use-fastapi-as-backend-framework.md) | Use FastAPI as Backend Framework | Accepted | 2024-03-27 |
| [0002](0002-async-postgresql-with-sqlalchemy-async.md) | Async PostgreSQL with SQLAlchemy Async | Accepted | 2024-03-27 |
| [0003](0003-use-redis-for-caching-and-rate-limiting.md) | Use Redis for Caching and Rate Limiting | Accepted | 2024-03-27 |

## Format

ADRs are numbered sequentially (e.g., `0001-`, `0002-`, etc.) and follow this structure:

1. **Title**: Concise description of the decision
2. **Status**: Proposed, Accepted, Deprecated, or Superseded
3. **Date**: When the decision was made
4. **Context**: The situation that prompted the decision
5. **Decision**: What we decided to do
6. **Rationale**: Why this was the right decision
7. **Consequences**: Both positive and negative outcomes
8. **Alternatives Considered**: Other options and why they were rejected

## Creating New ADRs

When making significant architectural decisions:

1. Create a new file with the next sequential number
2. Fill out all sections of the ADR template
3. Update this index
4. Commit with message: `docs(adr): add ADR NNNN for <title>`

## References

- [Documenting Architecture Decisions - Michael Nygard](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
- [ADR Tools](https://github.com/npryce/adr-tools)
