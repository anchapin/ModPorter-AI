# Health Check Endpoints

This document describes the health check endpoints implemented in the ModPorter AI backend for Kubernetes readiness and liveness probes.

## Overview

The backend provides three health check endpoints:

| Endpoint | Purpose | Use Case |
|----------|---------|-----------|
| `/health` | Basic health check | Simple uptime verification |
| `/health/liveness` | Liveness probe | Kubernetes liveness check |
| `/health/readiness` | Readiness probe | Kubernetes readiness check |

## Endpoints

### 1. Basic Health Check

**Endpoint:** `GET /health`

Returns a basic health status indicating the application is running.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000000",
  "checks": {
    "application": {
      "status": "running",
      "message": "Application process is running"
    }
  }
}
```

### 2. Liveness Probe

**Endpoint:** `GET /health/liveness`

Checks if the application is running and doesn't need to be restarted. This endpoint does NOT check dependencies to avoid restart loops.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000000",
  "checks": {
    "application": {
      "status": "running",
      "message": "Application process is running"
    }
  }
}
```

**Use in Kubernetes:**
```yaml
livenessProbe:
  httpGet:
    path: /health/liveness
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
```

### 3. Readiness Probe

**Endpoint:** `GET /health/readiness`

Checks if the application can serve traffic by verifying all required dependencies are available:
- Database connectivity
- Redis connectivity (optional - results in degraded status if unavailable)

**Response (all healthy):**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000000",
  "checks": {
    "dependencies": {
      "database": {
        "status": "healthy",
        "latency_ms": 5.2,
        "message": "Database connection successful"
      },
      "redis": {
        "status": "healthy",
        "latency_ms": 1.8,
        "message": "Redis connection successful"
      }
    }
  }
}
```

**Response (degraded - Redis unavailable):**
```json
{
  "status": "degraded",
  "timestamp": "2024-01-15T10:30:00.000000",
  "checks": {
    "dependencies": {
      "database": {
        "status": "healthy",
        "latency_ms": 5.2,
        "message": "Database connection successful"
      },
      "redis": {
        "status": "unhealthy",
        "latency_ms": 0.0,
        "message": "Redis is not available or disabled"
      }
    }
  }
}
```

**Response (unhealthy - Database unavailable):**
```json
{
  "status": "unhealthy",
  "timestamp": "2024-01-15T10:30:00.000000",
  "checks": {
    "dependencies": {
      "database": {
        "status": "unhealthy",
        "latency_ms": 5000.0,
        "message": "Database connection failed: connection refused"
      },
      "redis": {
        "status": "healthy",
        "latency_ms": 1.8,
        "message": "Redis connection successful"
      }
    }
  }
}
```

**Use in Kubernetes:**
```yaml
readinessProbe:
  httpGet:
    path: /health/readiness
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

## Status Values

| Status | Meaning |
|--------|---------|
| `healthy` | All checks passed, application can serve traffic |
| `degraded` | Non-critical dependencies unavailable (e.g., Redis), application can serve limited traffic |
| `unhealthy` | Critical dependencies unavailable (e.g., database), application cannot serve traffic |

## Implementation Details

The health check endpoints are implemented in `backend/src/api/health.py` using FastAPI:

- **Database health check:** Executes `SELECT 1` to verify database connectivity
- **Redis health check:** Uses Redis PING command to verify connectivity
- **Latency tracking:** Each dependency check measures response time in milliseconds
- **Graceful degradation:** Redis is treated as optional; database is required

## Related Issues

- Issue #699: [P2] Add health check endpoints
- Readiness Pillar: Debugging & Observability
