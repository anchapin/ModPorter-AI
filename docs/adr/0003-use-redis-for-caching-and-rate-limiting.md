# ADR 0003: Use Redis for Caching and Rate Limiting

**Status:** Accepted  
**Date:** 2024-03-27  
**Deciders:** Alex Chapin

## Context

We needed a solution for:
- Session and token caching
- Rate limiting with distributed counter support
- Temporary file metadata storage
- Job queue support

## Decision

We will use **Redis** as our caching and rate-limiting layer, with a local fallback for single-instance deployments.

## Rationale

- **Speed**: In-memory data store with sub-millisecond latency
- **Distributed counters**: Atomic operations for rate limiting across multiple instances
- **TTL support**: Automatic expiration for temporary data
- **Pub/Sub**: Useful for real-time features and job processing
- **Local fallback**: Rate limiter degrades gracefully to in-memory when Redis unavailable

## Consequences

### Positive
- Sub-millisecond cache lookups
- Atomic rate limiting across distributed deployments
- Automatic cache expiration with TTL
- Rich data structures (lists, sets, hashes, sorted sets)

### Negative
- Additional infrastructure to maintain
- Redis connection management complexity
- Potential for cache stampede without proper key strategies

## Alternatives Considered

### Memcached
- Simpler but fewer features
- No atomic rate limiting operations
- Decision: Redis's data structures and atomic operations were valuable

### In-memory only
- No persistence across restarts
- No distributed rate limiting
- Decision: Needed Redis for multi-instance deployments

### Database-based caching
- Slower than Redis
- Additional load on primary database
- Decision: Redis offloads caching from PostgreSQL
