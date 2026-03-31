# ADR 0002: Async PostgreSQL with SQLAlchemy Async

**Status:** Accepted  
**Date:** 2024-03-27  
**Deciders:** Alex Chapin

## Context

We needed to choose a database strategy that could handle:
- High-concurrency workloads with many simultaneous connections
- Efficient connection pooling
- Support for vector similarity search (pgvector)
- Complex queries for analytics and reporting

## Decision

We will use **PostgreSQL with SQLAlchemy async** as our primary database, with **pgvector** for vector embeddings.

## Rationale

- **Async compatibility**: SQLAlchemy async allows non-blocking database operations
- **Connection pooling**: Built-in async pool with configurable size for high concurrency
- **pgvector support**: Native vector similarity search for RAG functionality
- **PostgreSQL features**: Full-text search, JSONB, and robust indexing options
- **Maturity**: Battle-tested database with excellent tooling

## Consequences

### Positive
- High concurrency with minimal connection overhead
- Native vector search for AI-powered features
- Rich query capabilities (CTEs, window functions, JSON operations)
- Excellent tooling (pgAdmin, DBeaver, etc.)

### Negative
- Requires managing PostgreSQL infrastructure
- Connection string management for async vs sync contexts
- Some SQLAlchemy async quirks with transactions

## Alternatives Considered

### SQLite with aiosqlite
- Simpler deployment but limited concurrency
- No native vector support
- Decision: Needed pgvector for RAG features

### MongoDB
- Flexible schema but weaker query capabilities
- Less mature async driver support
- Decision: PostgreSQL's relational model better fits our domain

### Supabase / Firebase
- Vendor lock-in concerns
- Decision: Self-hosted PostgreSQL gives more control
